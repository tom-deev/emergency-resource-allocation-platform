"""
Stage 8C + 8E Automated Tests — Resource Operator Two-Step OTP Authentication,
Gmail SMTP Delivery (Mocked) & Public Registration Lockdown.

NOTE: All SMTP tests mock `smtplib.SMTP` / `send_operator_otp_email`.
No real emails are sent during the automated test suite.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
import sys
import threading

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import local_server
import handler
from services.email_service import EmailDeliveryError, send_operator_otp_email
import services.user_service as user_service_module
from test_auth_helpers import (
    login_operator_step1,
    login_operator_with_otp,
    provision_operator,
)


def call_api(method, path, body=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    event = {
        "httpMethod": method,
        "path": path,
        "headers": headers,
        "body": json.dumps(body) if body is not None else None,
    }
    resp = handler.lambda_handler(event, None)
    parsed = json.loads(resp["body"]) if resp.get("body") else None
    return resp["statusCode"], parsed


def test_gmail_smtp_service_mocked():
    """Verify Gmail SMTP STARTTLS, login, subject, and safe body using a mocked SMTP server."""
    events_log = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=15):
            events_log.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ehlo(self):
            events_log.append(("ehlo",))

        def starttls(self, context=None):
            assert context is not None
            events_log.append(("starttls",))

        def login(self, user, pwd):
            events_log.append(("login", user))

        def send_message(self, msg):
            events_log.append(("send_message", msg["Subject"], msg["From"], msg["To"], msg.get_content()))

    env_backup = {
        k: os.environ.get(k)
        for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "OTP_EMAIL_FROM", "OTP_EMAIL_TO")
    }
    try:
        os.environ["SMTP_HOST"] = "smtp.gmail.com"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USERNAME"] = "tom.axeron@gmail.com"
        os.environ["SMTP_PASSWORD"] = "mock-app-password-only"
        os.environ["OTP_EMAIL_FROM"] = "tom.axeron@gmail.com"
        os.environ["OTP_EMAIL_TO"] = "tom.axeron@gmail.com"

        send_operator_otp_email("operator1", "482913", ttl_seconds=300, smtp_factory=FakeSMTP)

        assert ("connect", "smtp.gmail.com", 587) in events_log
        assert ("starttls",) in events_log
        assert ("login", "tom.axeron@gmail.com") in events_log

        sent = [e for e in events_log if e[0] == "send_message"][0]
        _, subject, sender, recipient, body = sent
        assert subject == "Emergency Response Platform — Your Login OTP"
        assert sender == "tom.axeron@gmail.com"
        assert recipient == "tom.axeron@gmail.com"
        assert "482913" in body
        assert "5 minutes" in body
        assert "single-use" in body.lower()
        assert "do not share" in body.lower()
        assert "mock-app-password-only" not in body
    finally:
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print("Gmail SMTP STARTTLS email formatting & security (mocked): PASSED")


def test_registration_lockdown_and_dispatcher_no_email():
    local_server.install_in_memory_backend()
    email_calls = []
    original_sender = user_service_module.send_operator_otp_email
    user_service_module.send_operator_otp_email = lambda **kw: email_calls.append(kw)

    try:
        # Public RESOURCE_OPERATOR & arbitrary role registration -> 403
        assert call_api("POST", "/auth/register", {
            "username": "rogue_op",
            "password": "secret",
            "role": "RESOURCE_OPERATOR",
        })[0] == 403

        assert call_api("POST", "/auth/register", {
            "username": "rogue_admin",
            "password": "secret",
            "role": "ADMIN",
        })[0] == 403

        # Missing role defaults to DISPATCHER
        status, created = call_api("POST", "/auth/register", {
            "username": "disp_default",
            "password": "secret",
        })
        assert status == 201
        assert created["role"] == "DISPATCHER"

        # Dispatcher 1-step login issues operational ACCESS token directly and sends NO email
        status, login = call_api("POST", "/auth/login", {
            "username": "disp_default",
            "password": "secret",
        })
        assert status == 200
        assert login.get("token")
        assert not login.get("otpRequired")
        assert len(email_calls) == 0
        assert call_api("GET", "/incidents", token=login["token"])[0] == 200
    finally:
        user_service_module.send_operator_otp_email = original_sender

    print("Registration lockdown & Dispatcher 1-step login (zero emails sent): PASSED")


def test_operator_otp_gmail_mode_no_terminal_leak_and_failure_invalidation():
    tables = local_server.install_in_memory_backend()
    provision_operator("op_otp1", "secret123", user_id="OP-OTP-001")

    # 1. In Gmail mode, OTP is NOT printed to stdout and NOT in HTTP response
    stdout_buf = io.StringIO()
    with redirect_stdout(stdout_buf):
        status, step1, otp1 = login_operator_step1("op_otp1", "secret123")
    assert status == 200
    assert step1["otpRequired"] is True
    assert "token" not in step1
    assert "otp" not in step1
    assert otp1 not in json.dumps(step1)
    assert otp1 not in stdout_buf.getvalue(), "OTP must NEVER be printed in gmail mode!"

    # 2. Failed email delivery -> 503, NO access token, and challenge is invalidated
    original_sender = user_service_module.send_operator_otp_email
    prev_mode = os.environ.get("OTP_DELIVERY_MODE")
    os.environ["OTP_DELIVERY_MODE"] = "gmail"

    def failing_sender(**kwargs):
        raise EmailDeliveryError("Simulated SMTP failure")

    user_service_module.send_operator_otp_email = failing_sender
    try:
        status_fail, fail_body = call_api("POST", "/auth/login", {
            "username": "op_otp1",
            "password": "secret123",
        })
        assert status_fail == 503
        assert "token" not in fail_body
        assert "challengeToken" not in fail_body

        # Stored challenge must be invalidated (otpUsed=True, otpHash=None)
        user_rec = tables["EmergencyUsers"].items["OP-OTP-001"]
        assert user_rec.get("otpUsed") is True
        assert user_rec.get("otpHash") is None
    finally:
        user_service_module.send_operator_otp_email = original_sender
        if prev_mode is None:
            os.environ.pop("OTP_DELIVERY_MODE", None)
        else:
            os.environ["OTP_DELIVERY_MODE"] = prev_mode

    # 3. Challenge token CANNOT access operational routes (401)
    status_fresh, step_fresh, otp_fresh = login_operator_step1("op_otp1", "secret123")
    assert status_fresh == 200
    challenge1 = step_fresh["challengeToken"]
    assert call_api("GET", "/incidents", token=challenge1)[0] == 401
    assert call_api("GET", "/incidents/queue", token=challenge1)[0] == 401
    assert call_api("GET", "/dashboard/summary", token=challenge1)[0] == 401

    # 4. Invalid challenge token rejected (401)
    assert call_api("POST", "/auth/verify-otp", {
        "challengeToken": "not.a.valid.token",
        "otp": otp_fresh,
    })[0] == 401

    # 5. Requesting a new OTP invalidates the previous challenge
    status2, step2, otp2 = login_operator_step1("op_otp1", "secret123")
    assert status2 == 200
    challenge2 = step2["challengeToken"]
    assert call_api("POST", "/auth/verify-otp", {
        "challengeToken": challenge1,
        "otp": otp_fresh,
    })[0] == 401

    # 6. 5 incorrect attempts invalidate the challenge
    wrong_otp = "000000" if otp2 != "000000" else "999999"
    for _ in range(5):
        s_bad, _ = call_api("POST", "/auth/verify-otp", {
            "challengeToken": challenge2,
            "otp": wrong_otp,
        })
        assert s_bad == 401
    assert call_api("POST", "/auth/verify-otp", {
        "challengeToken": challenge2,
        "otp": otp2,
    })[0] == 401

    # 7. Expired OTP is rejected (401)
    _, step_exp, otp_exp = login_operator_step1("op_otp1", "secret123")
    user_rec = tables["EmergencyUsers"].items["OP-OTP-001"]
    user_rec["otpExpiresAt"] = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    assert call_api("POST", "/auth/verify-otp", {
        "challengeToken": step_exp["challengeToken"],
        "otp": otp_exp,
    })[0] == 401

    # 8. Valid OTP grants ACCESS token; reusing same OTP is rejected (401)
    _, step_ok, otp_ok = login_operator_step1("op_otp1", "secret123")
    status_ok, ok_body = call_api("POST", "/auth/verify-otp", {
        "challengeToken": step_ok["challengeToken"],
        "otp": otp_ok,
    })
    assert status_ok == 200
    access_token = ok_body["token"]
    assert call_api("GET", "/incidents/queue", token=access_token)[0] == 200

    assert call_api("POST", "/auth/verify-otp", {
        "challengeToken": step_ok["challengeToken"],
        "otp": otp_ok,
    })[0] == 401

    print("Gmail OTP mode (no terminal leak, failure invalidation, expiry, lockout, single-use): PASSED")


def test_concurrent_otp_verification_single_winner():
    local_server.install_in_memory_backend()
    provision_operator("op_race", "secret123")

    _, step1, otp_code = login_operator_step1("op_race", "secret123")
    challenge_token = step1["challengeToken"]

    barrier = threading.Barrier(2)

    def verify():
        barrier.wait()
        return call_api("POST", "/auth/verify-otp", {
            "challengeToken": challenge_token,
            "otp": otp_code,
        })

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(verify)
        f2 = pool.submit(verify)
        r1, r2 = f1.result(), f2.result()

    assert sorted([r1[0], r2[0]]) == [200, 401]
    print("Concurrent OTP verification single-use race protection: PASSED")


def test_seeded_demo_operator_login():
    local_server.install_in_memory_backend()
    local_server.seed_demo_data()

    token, user = login_operator_with_otp("operator1", "operator123")
    assert user["role"] == "RESOURCE_OPERATOR"
    assert call_api("GET", "/dashboard/summary", token=token)[0] == 200
    print("Seeded demo operator (operator1) two-step Gmail OTP login (mocked): PASSED")


if __name__ == "__main__":
    test_gmail_smtp_service_mocked()
    test_registration_lockdown_and_dispatcher_no_email()
    test_operator_otp_gmail_mode_no_terminal_leak_and_failure_invalidation()
    test_concurrent_otp_verification_single_winner()
    test_seeded_demo_operator_login()
    print("\nALL STAGE 8E GMAIL SMTP OTP & REGISTRATION LOCKDOWN TESTS PASSED")
