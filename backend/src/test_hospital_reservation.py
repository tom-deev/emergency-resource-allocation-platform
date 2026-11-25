"""
Stage 4 Automated Tests — Atomic Hospital Bed Reservation, Confirmation,
Rejection, Cancellation, Bounded History & Concurrency.

NOTE: These tests run against the thread-safe in-memory mock DynamoDB store
(`backend/local_server.py`). They verify transaction conditions and conflict
handling locally, and do NOT substitute for live AWS DynamoDB tests.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
import threading

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import local_server
import handler
from constants import MAX_RESERVATION_HISTORY
from test_auth_helpers import login_operator_with_otp, provision_operator


def call_api(method, path, body=None, token=None, query=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    event = {
        "httpMethod": method,
        "path": path,
        "headers": headers,
        "queryStringParameters": query,
        "body": json.dumps(body) if body is not None else None,
    }
    resp = handler.lambda_handler(event, None)
    parsed = json.loads(resp["body"]) if resp.get("body") else None
    return resp["statusCode"], parsed


def setup_users():
    local_server.install_in_memory_backend()
    call_api("POST", "/auth/register", {"username": "disp_s4", "password": "secret", "role": "DISPATCHER"})
    provision_operator("op_s4", "secret")
    _, d = call_api("POST", "/auth/login", {"username": "disp_s4", "password": "secret"})
    op_token, _ = login_operator_with_otp("op_s4", "secret")
    return d["token"], op_token


def create_dispatched_incident(disp_token, op_token, people_affected=3, reg_suffix="1"):
    _, inc = call_api("POST", "/incidents", {
        "type": "ROAD_ACCIDENT",
        "description": "Stage 4 bed test",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "HIGH",
        "peopleAffected": people_affected,
        "requiredEquipment": ["OXYGEN"],
    }, token=disp_token)
    inc_id = inc["incidentId"]
    _, amb = call_api("POST", "/ambulances", {
        "registrationNumber": f"MH12S4{reg_suffix}",
        "latitude": 18.5210,
        "longitude": 73.8560,
        "status": "AVAILABLE",
        "equipment": ["OXYGEN"],
    }, token=op_token)
    amb_id = amb["ambulanceId"]

    call_api("POST", f"/incidents/{inc_id}/review", token=op_token)
    call_api("POST", f"/incidents/{inc_id}/verify", {"decision": "VERIFIED"}, token=op_token)
    status, _ = call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)
    assert status == 200
    return inc_id, amb_id


def create_hospital(op_token, name, total_beds=20, avail_beds=5, status_val="ACTIVE"):
    _, h = call_api("POST", "/hospitals", {
        "name": name,
        "latitude": 18.5230,
        "longitude": 73.8500,
        "totalBeds": total_beds,
        "availableBeds": avail_beds,
        "facilities": ["EMERGENCY", "ICU"],
        "status": status_val,
    }, token=op_token)
    return h["hospitalId"]


def test_default_adjusted_invalid_and_inactive_reservations():
    disp_token, op_token = setup_users()
    inc_id, amb_id = create_dispatched_incident(disp_token, op_token, people_affected=3, reg_suffix="A")
    hosp_active = create_hospital(op_token, "Active Care", total_beds=20, avail_beds=5)
    hosp_inactive = create_hospital(op_token, "Closed Clinic", total_beds=20, avail_beds=10, status_val="INACTIVE")

    # Invalid bed counts -> 400
    for bad in (0, -2, "3", True):
        status, _ = call_api(
            "POST",
            f"/incidents/{inc_id}/request-hospital",
            {"hospitalId": hosp_active, "bedsRequested": bad},
            token=op_token,
        )
        assert status == 400, f"Expected 400 for bedsRequested={bad!r}, got {status}"

    # Inactive hospital -> 400
    status, _ = call_api(
        "POST",
        f"/incidents/{inc_id}/request-hospital",
        {"hospitalId": hosp_inactive},
        token=op_token,
    )
    assert status == 400

    # Insufficient capacity (requesting 6 when 5 available) -> 409, no partial update
    status, _ = call_api(
        "POST",
        f"/incidents/{inc_id}/request-hospital",
        {"hospitalId": hosp_active, "bedsRequested": 6},
        token=op_token,
    )
    assert status == 409
    _, inc_check = call_api("GET", f"/incidents/{inc_id}", token=op_token)
    assert inc_check["status"] == "AMBULANCE_ASSIGNED"

    # Default bedsRequested == peopleAffected (3) -> 200, beds drop 5 -> 2
    status, res = call_api(
        "POST",
        f"/incidents/{inc_id}/request-hospital",
        {"hospitalId": hosp_active},
        token=op_token,
    )
    assert status == 200
    assert res["reservation"]["bedsReserved"] == 3
    assert res["reservation"]["status"] == "RESERVED"
    assert res["hospital"]["availableBeds"] == 2
    assert res["incident"]["status"] == "HOSPITAL_REQUESTED"

    # Accept -> CONFIRMED, hospitalAcceptedAt set, beds STILL 2 (no double decrement!)
    status, acc = call_api(
        "POST",
        f"/incidents/{inc_id}/hospital-decision",
        {"decision": "ACCEPTED"},
        token=op_token,
    )
    assert status == 200
    assert acc["incident"]["status"] == "HOSPITAL_ACCEPTED"
    assert acc["incident"]["hospitalAcceptedAt"] is not None
    assert acc["reservation"]["status"] == "CONFIRMED"
    assert acc["hospital"]["availableBeds"] == 2
    assert acc["incident"]["assignedAmbulanceId"] == amb_id

    # Operator-adjusted bed count (peopleAffected=4, operator adjusts to 2)
    inc2_id, _ = create_dispatched_incident(disp_token, op_token, people_affected=4, reg_suffix="B")
    status, res2 = call_api(
        "POST",
        f"/incidents/{inc2_id}/request-hospital",
        {"hospitalId": hosp_active, "bedsRequested": 2},
        token=op_token,
    )
    assert status == 200
    assert res2["reservation"]["bedsReserved"] == 2
    assert res2["hospital"]["availableBeds"] == 0

    print("Default/adjusted/invalid beds, inactive hospital, insufficient capacity & confirm without double decrement: PASSED")


def test_rejection_cancellation_switch_and_duplicate_release_protection():
    disp_token, op_token = setup_users()
    inc_id, amb_id = create_dispatched_incident(disp_token, op_token, people_affected=2, reg_suffix="C")
    hosp1 = create_hospital(op_token, "Hospital One", total_beds=10, avail_beds=4)
    hosp2 = create_hospital(op_token, "Hospital Two", total_beds=10, avail_beds=6)

    # Reserve 2 beds at hosp1 (4 -> 2)
    status, _ = call_api("POST", f"/incidents/{inc_id}/request-hospital", {"hospitalId": hosp1, "bedsRequested": 2}, token=op_token)
    assert status == 200

    # Concurrent duplicate rejection: only 1 succeeds, beds return 2 -> 4 (NEVER 6!)
    barrier = threading.Barrier(2)

    def reject_req():
        barrier.wait()
        return call_api("POST", f"/incidents/{inc_id}/hospital-decision", {"decision": "REJECTED", "reason": "Full"}, token=op_token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        r1 = pool.submit(reject_req)
        r2 = pool.submit(reject_req)
        res1, res2 = r1.result(), r2.result()

    assert sorted([res1[0], res2[0]]) == [200, 409]
    _, hospitals = call_api("GET", "/hospitals", token=op_token)
    h1 = next(h for h in hospitals if h["hospitalId"] == hosp1)
    assert h1["availableBeds"] == 4

    # Ambulance remained assigned during rejection; switch directly to hosp2
    _, inc_after_rej = call_api("GET", f"/incidents/{inc_id}", token=op_token)
    assert inc_after_rej["status"] == "HOSPITAL_REJECTED"
    assert inc_after_rej["assignedAmbulanceId"] == amb_id

    # Reserve 2 beds at hosp2 (6 -> 4)
    status, _ = call_api("POST", f"/incidents/{inc_id}/request-hospital", {"hospitalId": hosp2, "bedsRequested": 2}, token=op_token)
    assert status == 200

    # Concurrent cancel vs reject: only 1 succeeds, beds return 4 -> 6 (NEVER 8!)
    barrier2 = threading.Barrier(2)

    def cancel_req():
        barrier2.wait()
        return call_api("POST", f"/incidents/{inc_id}/cancel-reservation", {"reason": "Rerouting"}, token=op_token)

    def reject_req2():
        barrier2.wait()
        return call_api("POST", f"/incidents/{inc_id}/hospital-decision", {"decision": "REJECTED", "reason": "Busy"}, token=op_token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        c_res = pool.submit(cancel_req)
        j_res = pool.submit(reject_req2)
        out1, out2 = c_res.result(), j_res.result()

    assert sorted([out1[0], out2[0]]) == [200, 409]
    _, hospitals2 = call_api("GET", "/hospitals", token=op_token)
    h2 = next(h for h in hospitals2 if h["hospitalId"] == hosp2)
    assert h2["availableBeds"] == 6

    # Explicit single cancellation returns incident to AMBULANCE_ASSIGNED
    inc_cancel, amb_cancel = create_dispatched_incident(disp_token, op_token, people_affected=1, reg_suffix="D")
    call_api("POST", f"/incidents/{inc_cancel}/request-hospital", {"hospitalId": hosp2, "bedsRequested": 1}, token=op_token)
    status, c_out = call_api("POST", f"/incidents/{inc_cancel}/cancel-reservation", {"reason": "Operator switch"}, token=op_token)
    assert status == 200
    assert c_out["incident"]["status"] == "AMBULANCE_ASSIGNED"
    assert c_out["incident"]["assignedAmbulanceId"] == amb_cancel
    assert c_out["reservation"]["status"] == "RELEASED"
    assert c_out["hospital"]["availableBeds"] == 6

    # Second cancel fails with 409 and beds stay 6
    status, _ = call_api("POST", f"/incidents/{inc_cancel}/cancel-reservation", token=op_token)
    assert status == 409

    print("Rejection, cancellation, hospital switch & duplicate release prevention: PASSED")


def test_concurrent_reservations_cannot_oversubscribe():
    disp_token, op_token = setup_users()
    inc1, _ = create_dispatched_incident(disp_token, op_token, people_affected=3, reg_suffix="E1")
    inc2, _ = create_dispatched_incident(disp_token, op_token, people_affected=3, reg_suffix="E2")
    # Hospital only has 4 beds: two simultaneous requests for 3 beds MUST NOT both succeed!
    hosp = create_hospital(op_token, "Tight Capacity Hospital", total_beds=10, avail_beds=4)

    barrier = threading.Barrier(2)

    def reserve(inc_id):
        barrier.wait()
        return call_api("POST", f"/incidents/{inc_id}/request-hospital", {"hospitalId": hosp, "bedsRequested": 3}, token=op_token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(reserve, inc1)
        f2 = pool.submit(reserve, inc2)
        r1, r2 = f1.result(), f2.result()

    assert sorted([r1[0], r2[0]]) == [200, 409]
    _, hospitals = call_api("GET", "/hospitals", token=op_token)
    h = next(item for item in hospitals if item["hospitalId"] == hosp)
    assert h["availableBeds"] == 1

    print("Concurrent reservations cannot oversubscribe remaining beds: PASSED")


def test_bounded_reservation_history():
    disp_token, op_token = setup_users()
    inc_id, _ = create_dispatched_incident(disp_token, op_token, people_affected=1, reg_suffix="H")
    hosp = create_hospital(op_token, "History Hospital", total_beds=10, avail_beds=5)

    for idx in range(MAX_RESERVATION_HISTORY + 5):
        s1, _ = call_api("POST", f"/incidents/{inc_id}/request-hospital", {"hospitalId": hosp, "bedsRequested": 1}, token=op_token)
        assert s1 == 200
        s2, _ = call_api("POST", f"/incidents/{inc_id}/cancel-reservation", {"reason": f"Try {idx}"}, token=op_token)
        assert s2 == 200

    _, inc = call_api("GET", f"/incidents/{inc_id}", token=op_token)
    assert len(inc["reservationHistory"]) == MAX_RESERVATION_HISTORY
    assert inc["reservationHistory"][-1]["reason"] == f"Try {MAX_RESERVATION_HISTORY + 4}"

    _, hospitals = call_api("GET", "/hospitals", token=op_token)
    h = next(item for item in hospitals if item["hospitalId"] == hosp)
    assert h["availableBeds"] == 5

    print(f"Bounded reservationHistory (capped at {MAX_RESERVATION_HISTORY} entries) & exact bed accounting: PASSED")


if __name__ == "__main__":
    test_default_adjusted_invalid_and_inactive_reservations()
    test_rejection_cancellation_switch_and_duplicate_release_protection()
    test_concurrent_reservations_cannot_oversubscribe()
    test_bounded_reservation_history()
    print("\nALL STAGE 4 HOSPITAL BED RESERVATION TESTS PASSED")
