"""
Stage 5 Automated Tests — Transport, Completion, Ambulance Release,
Hospital Reservation Integrity & Dashboard Summary Metrics.

Runs against the in-memory mock DynamoDB store (`backend/local_server.py`).
"""

from datetime import datetime, timedelta, timezone
import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import local_server
import handler
from test_auth_helpers import login_operator_with_otp, provision_operator


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


def setup_users():
    local_server.install_in_memory_backend()
    call_api("POST", "/auth/register", {"username": "disp_s5", "password": "secret", "role": "DISPATCHER"})
    provision_operator("op_s5", "secret")
    _, d = call_api("POST", "/auth/login", {"username": "disp_s5", "password": "secret"})
    op_token, _ = login_operator_with_otp("op_s5", "secret")
    return d["token"], op_token


def test_transport_completion_and_dashboard_metrics():
    disp_token, op_token = setup_users()

    # Empty dashboard: Dispatcher is blocked (403); Resource Operator gets 200 with Unavailable avg
    assert call_api("GET", "/dashboard/summary", token=disp_token)[0] == 403

    status, empty_dash = call_api("GET", "/dashboard/summary", token=op_token)
    assert status == 200
    assert empty_dash["totalIncidents"] == 0
    assert empty_dash["averageResponseTimeSeconds"] is None
    assert empty_dash["responseTimeSampleCount"] == 0

    # Register ambulance & hospital
    _, amb = call_api("POST", "/ambulances", {
        "registrationNumber": "MH12S5001",
        "latitude": 18.5210,
        "longitude": 73.8560,
        "status": "AVAILABLE",
        "equipment": ["OXYGEN"],
    }, token=op_token)
    amb_id = amb["ambulanceId"]

    _, hosp = call_api("POST", "/hospitals", {
        "name": "Stage 5 Hospital",
        "latitude": 18.5350,
        "longitude": 73.8490,
        "totalBeds": 20,
        "availableBeds": 10,
        "facilities": ["EMERGENCY", "ICU"],
        "status": "ACTIVE",
    }, token=op_token)
    hosp_id = hosp["hospitalId"]

    # Create 2 incidents: one will complete, one stays CREATED (incomplete)
    _, inc1 = call_api("POST", "/incidents", {
        "type": "ROAD_ACCIDENT",
        "description": "Stage 5 complete flow",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "CRITICAL",
        "peopleAffected": 2,
        "requiredEquipment": ["OXYGEN"],
    }, token=disp_token)
    inc1_id = inc1["incidentId"]

    _, inc2 = call_api("POST", "/incidents", {
        "type": "MEDICAL",
        "description": "Still waiting",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "HIGH",
        "peopleAffected": 1,
    }, token=disp_token)

    # Invalid transport before HOSPITAL_ACCEPTED -> 409
    assert call_api("POST", f"/incidents/{inc1_id}/transport", token=op_token)[0] == 409
    # Invalid complete before PATIENT_TRANSPORTED -> 409
    assert call_api("POST", f"/incidents/{inc1_id}/complete", token=op_token)[0] == 409

    # Walk inc1 through review -> verify -> dispatch -> reserve -> confirm
    call_api("POST", f"/incidents/{inc1_id}/review", token=op_token)
    call_api("POST", f"/incidents/{inc1_id}/verify", {"decision": "VERIFIED"}, token=op_token)
    call_api("POST", f"/incidents/{inc1_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)

    # Still cannot transport before hospital acceptance -> 409
    assert call_api("POST", f"/incidents/{inc1_id}/transport", token=op_token)[0] == 409

    call_api("POST", f"/incidents/{inc1_id}/request-hospital", {"hospitalId": hosp_id, "bedsRequested": 2}, token=op_token)
    # Still cannot transport while only HOSPITAL_REQUESTED -> 409
    assert call_api("POST", f"/incidents/{inc1_id}/transport", token=op_token)[0] == 409

    call_api("POST", f"/incidents/{inc1_id}/hospital-decision", {"decision": "ACCEPTED"}, token=op_token)

    # Cannot complete before transport -> 409
    assert call_api("POST", f"/incidents/{inc1_id}/complete", token=op_token)[0] == 409

    # Record transport -> PATIENT_TRANSPORTED with backend transportedAt
    status, tr = call_api("POST", f"/incidents/{inc1_id}/transport", token=op_token)
    assert status == 200
    assert tr["incident"]["status"] == "PATIENT_TRANSPORTED"
    assert tr["incident"]["transportedAt"] is not None

    # Duplicate transport -> 409
    assert call_api("POST", f"/incidents/{inc1_id}/transport", token=op_token)[0] == 409

    # Complete incident -> COMPLETED with backend completedAt, ambulance released, beds intact
    status, comp = call_api("POST", f"/incidents/{inc1_id}/complete", token=op_token)
    assert status == 200
    assert comp["incident"]["status"] == "COMPLETED"
    assert comp["incident"]["completedAt"] is not None
    assert comp["incident"]["bedReservation"]["status"] == "CONFIRMED"
    assert comp["incident"]["bedReservation"]["bedsReserved"] == 2
    assert len(comp["incident"]["reservationHistory"]) == 1
    assert comp["ambulance"]["status"] == "AVAILABLE"
    assert comp["ambulance"]["assignedIncidentId"] is None

    # Hospital beds must STILL be 8 (NOT incremented on completion!)
    _, hospitals = call_api("GET", "/hospitals", token=op_token)
    h = next(item for item in hospitals if item["hospitalId"] == hosp_id)
    assert h["availableBeds"] == 8
    assert h["latitude"] == 18.5350 and h["longitude"] == 73.8490

    # Duplicate completion -> 409
    assert call_api("POST", f"/incidents/{inc1_id}/complete", token=op_token)[0] == 409

    # Verify dashboard summary (Resource Operator only) excludes incomplete inc2 from avg response time
    status, dash = call_api("GET", "/dashboard/summary", token=op_token)
    assert status == 200
    assert dash["totalIncidents"] == 2
    assert dash["criticalIncidents"] == 1
    assert dash["highPriorityIncidents"] == 1
    assert dash["pendingVerification"] == 1
    assert dash["completedIncidents"] == 1
    assert dash["availableAmbulances"] == 1
    assert dash["busyAmbulances"] == 0
    assert dash["totalAvailableBeds"] == 8
    assert dash["totalReservedBeds"] == 2
    assert dash["responseTimeSampleCount"] == 1
    assert dash["averageResponseTimeSeconds"] is not None
    assert dash["averageResponseTimeSeconds"] >= 0
    assert len(dash["recentActivity"]) >= 7

    print("Transport, completion, ambulance release, bed retention & dashboard summary: PASSED")


if __name__ == "__main__":
    test_transport_completion_and_dashboard_metrics()
    print("\nALL STAGE 5 TRANSPORT, COMPLETION & DASHBOARD TESTS PASSED")
