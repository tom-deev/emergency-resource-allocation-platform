"""
Shared test helpers for internal RESOURCE_OPERATOR provisioning and real
two-step OTP login using a mocked Gmail email sender (no real emails sent).
"""

import json
import os
from uuid import uuid4

import handler
from models.user import User
import services.user_service as user_service_module


def provision_operator(username: str, password: str, user_id: str | None = None) -> dict:
    """Provision a RESOURCE_OPERATOR internally via UserService (not public /auth/register)."""
    service = handler.get_user_service()
    return service.create_user(
        User(
            userId=user_id or f"OP-{uuid4().hex[:8].upper()}",
            username=username,
            role="RESOURCE_OPERATOR",
            passwordHash=User.hash_password(password),
        )
    )


def login_operator_step1(username: str, password: str):
    """
    Run POST /auth/login for a RESOURCE_OPERATOR in `gmail` mode with a mocked
    email sender (captures the generated 6-digit OTP without sending real email).
    """
    prev_mode = os.environ.get("OTP_DELIVERY_MODE")
    prev_console = os.environ.get("LOCAL_OTP_CONSOLE")
    original_sender = user_service_module.send_operator_otp_email

    captured = {"otp": None, "calls": 0}

    def fake_email_sender(username, otp_code, ttl_seconds=300):
        captured["otp"] = otp_code
        captured["calls"] += 1

    os.environ["OTP_DELIVERY_MODE"] = "gmail"
    os.environ["LOCAL_OTP_CONSOLE"] = "false"
    user_service_module.send_operator_otp_email = fake_email_sender

    try:
        event = {
            "httpMethod": "POST",
            "path": "/auth/login",
            "body": json.dumps({"username": username, "password": password}),
        }
        resp = handler.lambda_handler(event, None)
        parsed = json.loads(resp["body"]) if resp.get("body") else None
        return resp["statusCode"], parsed, captured["otp"]
    finally:
        user_service_module.send_operator_otp_email = original_sender
        if prev_mode is None:
            os.environ.pop("OTP_DELIVERY_MODE", None)
        else:
            os.environ["OTP_DELIVERY_MODE"] = prev_mode
        if prev_console is None:
            os.environ.pop("LOCAL_OTP_CONSOLE", None)
        else:
            os.environ["LOCAL_OTP_CONSOLE"] = prev_console


def login_operator_with_otp(username: str, password: str) -> tuple[str, dict]:
    """Complete the real two-step RESOURCE_OPERATOR login and return (access_token, user)."""
    status, step1, otp_code = login_operator_step1(username, password)
    assert status == 200, f"Step 1 operator login failed: {status} {step1}"
    assert step1.get("otpRequired") is True
    assert "token" not in step1
    assert otp_code is not None and len(otp_code) == 6

    event = {
        "httpMethod": "POST",
        "path": "/auth/verify-otp",
        "body": json.dumps({
            "challengeToken": step1["challengeToken"],
            "otp": otp_code,
        }),
    }
    resp = handler.lambda_handler(event, None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200, f"Step 2 OTP verify failed: {resp['statusCode']} {body}"
    return body["token"], body["user"]
