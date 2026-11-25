"""
Stage 8B Automated Tests — Dispatcher Ownership, Privacy & Strict Role Isolation.

Tests:
1. Dispatcher A can register an incident (createdBy stamped from token).
2. Dispatcher A sees their own incident.
3. Dispatcher B cannot see Dispatcher A's incident in GET /incidents.
4. Dispatcher B receives 404 when directly requesting Dispatcher A's incident.
5. Legacy incidents without ownership are hidden from Dispatchers (list & 404 detail).
6. Resource Operators can still view and manage legacy incidents.
7. Dispatcher receives 403 from queue, dashboard, ambulance, and hospital endpoints.
8. Resource Operator retains access to queue, dashboard, ambulance, and hospital endpoints.
9. Client-supplied createdBy / createdByUsername cannot impersonate another user.
10. Dispatcher responses do not expose operational resource, reviewer, or reservation details.
"""

from datetime import datetime, timezone
import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import local_server
import handler
from models.incident import Incident
from test_auth_helpers import login_operator_with_otp, provision_operator


ALLOWED_DISPATCHER_FIELDS = {
    "incidentId",
    "type",
    "emergencyType",
    "description",
    "severity",
    "priority",
    "status",
    "createdAt",
    "updatedAt",
    "latitude",
    "longitude",
    "peopleAffected",
    "isArchived",
}


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


def test_ownership_privacy_and_isolation():
    local_server.install_in_memory_backend()

    # Register Dispatcher A & B publicly; provision Resource Operator internally
    call_api("POST", "/auth/register", {"username": "disp_a", "password": "secret", "role": "DISPATCHER"})
    call_api("POST", "/auth/register", {"username": "disp_b", "password": "secret", "role": "DISPATCHER"})
    provision_operator("op_8b", "secret")

    _, login_a = call_api("POST", "/auth/login", {"username": "disp_a", "password": "secret"})
    _, login_b = call_api("POST", "/auth/login", {"username": "disp_b", "password": "secret"})
    tok_op, _ = login_operator_with_otp("op_8b", "secret")

    tok_a = login_a["token"]
    tok_b = login_b["token"]
    uid_a = login_a["user"]["userId"]
    uid_b = login_b["user"]["userId"]

    # Seed a legacy incident with NO createdBy ownership metadata
    now = datetime.now(timezone.utc).isoformat()
    inc_service = handler.get_incident_service()
    inc_service.create_incident(Incident(
        incidentId="INC-LEGACY-001",
        type="FIRE",
        description="Legacy incident without owner",
        latitude=18.52,
        longitude=73.85,
        severity="HIGH",
        peopleAffected=2,
        status="CREATED",
        createdAt=now,
        updatedAt=now,
        createdBy=None,
        createdByUsername=None,
    ))

    # 1 & 9. Dispatcher A creates incident while attempting to spoof createdBy = Dispatcher B
    status, created_a = call_api("POST", "/incidents", {
        "type": "ROAD_ACCIDENT",
        "description": "Dispatcher A incident",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "CRITICAL",
        "peopleAffected": 2,
        "createdBy": uid_b,
        "createdByUsername": "disp_b",
        "requiredEquipment": ["OXYGEN"],
    }, token=tok_a)
    assert status == 201
    inc_a_id = created_a["incidentId"]
    assert set(created_a.keys()).issubset(ALLOWED_DISPATCHER_FIELDS)

    # Verify stored record has authoritative createdBy == uid_a (spoofing ignored!)
    status, op_view_a = call_api("GET", f"/incidents/{inc_a_id}", token=tok_op)
    assert status == 200
    assert op_view_a["createdBy"] == uid_a
    assert op_view_a["createdByUsername"] == "disp_a"

    # 2. Dispatcher A sees only their own incident (NOT legacy)
    status, list_a = call_api("GET", "/incidents", token=tok_a)
    assert status == 200
    assert [i["incidentId"] for i in list_a] == [inc_a_id]
    assert set(list_a[0].keys()).issubset(ALLOWED_DISPATCHER_FIELDS)

    # 3 & 5. Dispatcher B sees empty list (neither Dispatcher A's nor legacy)
    status, list_b = call_api("GET", "/incidents", token=tok_b)
    assert status == 200
    assert list_b == []

    # 4 & 5. Dispatcher B gets 404 on Dispatcher A's incident AND legacy incident
    assert call_api("GET", f"/incidents/{inc_a_id}", token=tok_b)[0] == 404
    assert call_api("GET", "/incidents/INC-LEGACY-001", token=tok_b)[0] == 404
    assert call_api("GET", "/incidents/INC-LEGACY-001", token=tok_a)[0] == 404

    # 6. Resource Operator sees both Dispatcher A's incident and legacy incident
    status, list_op = call_api("GET", "/incidents", token=tok_op)
    assert status == 200
    op_ids = {i["incidentId"] for i in list_op}
    assert inc_a_id in op_ids and "INC-LEGACY-001" in op_ids
    assert call_api("GET", "/incidents/INC-LEGACY-001", token=tok_op)[0] == 200

    # 7. Dispatcher receives 403 on global queue, dashboard, ambulances, and hospitals
    assert call_api("GET", "/incidents/queue", token=tok_a)[0] == 403
    assert call_api("GET", "/dashboard/summary", token=tok_a)[0] == 403
    assert call_api("GET", "/ambulances", token=tok_a)[0] == 403
    assert call_api("GET", "/hospitals", token=tok_a)[0] == 403

    # 8. Resource Operator retains 200 access to those endpoints
    assert call_api("GET", "/incidents/queue", token=tok_op)[0] == 200
    assert call_api("GET", "/dashboard/summary", token=tok_op)[0] == 200
    assert call_api("GET", "/ambulances", token=tok_op)[0] == 200
    assert call_api("GET", "/hospitals", token=tok_op)[0] == 200

    # 10. Advance Dispatcher A's incident through operational steps; verify Dispatcher A
    #     sees updated status ONLY and NEVER sees ambulance/hospital/reservation/reviewer internals
    _, amb = call_api("POST", "/ambulances", {
        "registrationNumber": "MH12PRIV1",
        "latitude": 18.52,
        "longitude": 73.85,
        "status": "AVAILABLE",
        "equipment": ["OXYGEN"],
    }, token=tok_op)
    _, hosp = call_api("POST", "/hospitals", {
        "name": "Private Test Hospital",
        "latitude": 18.52,
        "longitude": 73.85,
        "totalBeds": 10,
        "availableBeds": 5,
        "facilities": ["EMERGENCY"],
        "status": "ACTIVE",
    }, token=tok_op)

    call_api("POST", f"/incidents/{inc_a_id}/review", token=tok_op)
    call_api("POST", f"/incidents/{inc_a_id}/verify", {"decision": "VERIFIED", "remarks": "Internal note"}, token=tok_op)
    call_api("POST", f"/incidents/{inc_a_id}/assign-ambulance", {"ambulanceId": amb["ambulanceId"]}, token=tok_op)
    call_api("POST", f"/incidents/{inc_a_id}/request-hospital", {"hospitalId": hosp["hospitalId"], "bedsRequested": 2}, token=tok_op)

    status, disp_detail = call_api("GET", f"/incidents/{inc_a_id}", token=tok_a)
    assert status == 200
    assert disp_detail["status"] == "HOSPITAL_REQUESTED"
    assert set(disp_detail.keys()).issubset(ALLOWED_DISPATCHER_FIELDS)
    for forbidden_key in (
        "assignedAmbulanceId",
        "assignedHospitalId",
        "bedReservation",
        "reservationHistory",
        "reviewedBy",
        "verificationRemarks",
        "ambulanceAssignedAt",
        "hospitalRequestedAt",
    ):
        assert forbidden_key not in disp_detail, f"Leaked {forbidden_key} to Dispatcher!"

    print("All 10 Stage 8B ownership, privacy & isolation assertions: PASSED")


if __name__ == "__main__":
    test_ownership_privacy_and_isolation()
    print("\nALL STAGE 8B OWNERSHIP & PRIVACY TESTS PASSED")
