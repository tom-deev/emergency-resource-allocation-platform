"""
End-to-end handler tests for:
- HMAC token creation, verification, expiry, and tampering rejection
- Stage 2 approved role-based authorization (DISPATCHER vs RESOURCE_OPERATOR)
- CORS preflight (OPTIONS)
- Workflow bypass protection on PUT /incidents/{id}/status
- Complete manual incident workflow controlled by RESOURCE_OPERATOR
- Concurrency/duplicate action protection (409 Conflict)
- Hospital & ambulance update validation

Uses the in-memory mock DynamoDB store (NOT live AWS DynamoDB).
"""

import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import local_server
import handler
from test_auth_helpers import login_operator_with_otp, provision_operator
from utils.auth import AuthError, create_token, verify_token


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
    parsed_body = json.loads(resp["body"]) if resp.get("body") else None
    return resp["statusCode"], resp.get("headers", {}), parsed_body


def test_token_security():
    token = create_token({"userId": "U1", "username": "disp", "role": "DISPATCHER"}, ttl_seconds=60)
    claims = verify_token(token)
    assert claims["sub"] == "U1"
    assert claims["role"] == "DISPATCHER"

    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    try:
        verify_token(tampered)
        raise AssertionError("Tampered token should fail")
    except AuthError:
        pass

    expired = create_token({"userId": "U1", "username": "disp", "role": "DISPATCHER"}, ttl_seconds=-1)
    try:
        verify_token(expired)
        raise AssertionError("Expired token should fail")
    except AuthError:
        pass

    print("Token creation, tamper detection, and expiry: PASSED")


def test_cors_and_auth_enforcement():
    local_server.install_in_memory_backend()

    # CORS preflight
    status, headers, _ = call_api("OPTIONS", "/incidents")
    assert status == 200
    assert headers.get("Access-Control-Allow-Origin") == "*"

    # Unauthenticated & invalid token -> 401
    status, _, _ = call_api("GET", "/incidents")
    assert status == 401
    status, _, _ = call_api("GET", "/incidents/queue", token="invalid.token")
    assert status == 401

    # Register dispatcher publicly; provision operator internally (public operator signup -> 403)
    status, _, _ = call_api("POST", "/auth/register", {
        "username": "disp1",
        "password": "secret",
        "role": "DISPATCHER",
    })
    assert status == 201

    status, _, _ = call_api("POST", "/auth/register", {
        "username": "op1",
        "password": "secret",
        "role": "RESOURCE_OPERATOR",
    })
    assert status == 403

    provision_operator("op1", "secret")

    # Invalid login -> 401
    status, _, _ = call_api("POST", "/auth/login", {
        "username": "disp1",
        "password": "wrong",
    })
    assert status == 401

    # Valid logins: Dispatcher 1-step, Resource Operator 2-step OTP
    status, _, disp_login = call_api("POST", "/auth/login", {
        "username": "disp1",
        "password": "secret",
    })
    assert status == 200
    disp_token = disp_login["token"]

    op_token, _ = login_operator_with_otp("op1", "secret")

    # Resource Operator cannot create incidents -> 403
    status, _, _ = call_api("POST", "/incidents", {
        "type": "FIRE",
        "description": "Test",
        "latitude": 18.52,
        "longitude": 73.85,
        "severity": "HIGH",
        "peopleAffected": 1,
    }, token=op_token)
    assert status == 403

    # Dispatcher cannot register ambulances or hospitals -> 403
    status, _, _ = call_api("POST", "/ambulances", {
        "registrationNumber": "MH12XX0001",
        "latitude": 18.52,
        "longitude": 73.85,
        "status": "AVAILABLE",
    }, token=disp_token)
    assert status == 403

    status, _, _ = call_api("POST", "/hospitals", {
        "name": "Blocked Hospital",
        "latitude": 18.52,
        "longitude": 73.85,
        "totalBeds": 10,
        "availableBeds": 5,
    }, token=disp_token)
    assert status == 403

    print("CORS & role-based authorization (401/403): PASSED")
    return disp_token, op_token


def test_full_manual_workflow_with_stage2_roles():
    disp_token, op_token = test_cors_and_auth_enforcement()

    # Register ambulance & hospital as RESOURCE_OPERATOR
    status, _, amb = call_api("POST", "/ambulances", {
        "registrationNumber": "MH12AB9999",
        "latitude": 18.5200,
        "longitude": 73.8550,
        "status": "AVAILABLE",
        "equipment": ["OXYGEN", "TRAUMA_KIT"],
    }, token=op_token)
    assert status == 201
    amb_id = amb["ambulanceId"]

    status, _, hosp = call_api("POST", "/hospitals", {
        "name": "Metro Trauma Hospital",
        "latitude": 18.5230,
        "longitude": 73.8500,
        "totalBeds": 10,
        "availableBeds": 2,
        "facilities": ["EMERGENCY", "ICU"],
        "status": "ACTIVE",
    }, token=op_token)
    assert status == 201
    hosp_id = hosp["hospitalId"]

    # Update validation: availableBeds > totalBeds must fail (400)
    status, _, _ = call_api("PUT", f"/hospitals/{hosp_id}", {"availableBeds": 99}, token=op_token)
    assert status == 400

    # Create incident as DISPATCHER
    status, _, inc = call_api("POST", "/incidents", {
        "type": "ROAD_ACCIDENT",
        "description": "Highway collision",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "CRITICAL",
        "peopleAffected": 2,
        "requiredResources": ["AMBULANCE"],
        "requiredEquipment": ["OXYGEN"],
    }, token=disp_token)
    assert status == 201
    inc_id = inc["incidentId"]
    assert inc["status"] == "CREATED"
    assert inc["priority"] == "P1"

    # DISPATCHER can read their own incident details, but receives 403 on global operational reads
    assert call_api("GET", f"/incidents/{inc_id}", token=disp_token)[0] == 200
    assert call_api("GET", "/incidents/queue", token=disp_token)[0] == 403
    assert call_api("GET", "/ambulances", token=disp_token)[0] == 403
    assert call_api("GET", "/hospitals", token=disp_token)[0] == 403
    assert call_api("GET", "/dashboard/summary", token=disp_token)[0] == 403

    # DISPATCHER receives 403 on ALL Resource Operator workflow actions
    assert call_api("POST", f"/incidents/{inc_id}/review", token=disp_token)[0] == 403
    assert call_api("POST", f"/incidents/{inc_id}/verify", {"decision": "VERIFIED"}, token=disp_token)[0] == 403
    assert call_api("GET", f"/incidents/{inc_id}/candidates", token=disp_token)[0] == 403
    assert call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=disp_token)[0] == 403
    assert call_api("POST", f"/incidents/{inc_id}/request-hospital", {"hospitalId": hosp_id}, token=disp_token)[0] == 403
    assert call_api("POST", f"/incidents/{inc_id}/hospital-decision", {"decision": "ACCEPTED"}, token=disp_token)[0] == 403
    assert call_api("POST", f"/incidents/{inc_id}/transport", token=disp_token)[0] == 403
    assert call_api("POST", f"/incidents/{inc_id}/complete", token=disp_token)[0] == 403

    # Generic status update cannot bypass verification even for RESOURCE_OPERATOR
    status, _, _ = call_api("PUT", f"/incidents/{inc_id}/status", {"status": "VERIFIED"}, token=op_token)
    assert status == 400

    # Cannot assign ambulance before verification -> 409
    status, _, _ = call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)
    assert status == 409

    # RESOURCE_OPERATOR starts review -> UNDER_REVIEW
    status, _, res = call_api("POST", f"/incidents/{inc_id}/review", token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "UNDER_REVIEW"

    # Duplicate review -> 409
    status, _, _ = call_api("POST", f"/incidents/{inc_id}/review", token=op_token)
    assert status == 409

    # RESOURCE_OPERATOR verifies -> VERIFIED
    status, _, res = call_api("POST", f"/incidents/{inc_id}/verify", {
        "decision": "VERIFIED",
        "remarks": "Confirmed via caller",
    }, token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "VERIFIED"
    assert res["incident"]["reviewedBy"] == "op1"
    assert res["incident"]["verifiedAt"] is not None

    # Duplicate verification -> 409
    status, _, _ = call_api("POST", f"/incidents/{inc_id}/verify", {"decision": "VERIFIED"}, token=op_token)
    assert status == 409

    # Candidates lookup by RESOURCE_OPERATOR
    status, _, cands = call_api("GET", f"/incidents/{inc_id}/candidates", token=op_token, query={"facilities": "ICU"})
    assert status == 200
    assert len(cands["ambulances"]) == 1
    assert cands["ambulances"][0]["eligible"] is True
    assert len(cands["hospitals"]) == 1
    assert cands["hospitals"][0]["suitable"] is True

    # Manual ambulance assignment -> AMBULANCE_ASSIGNED, ambulance BUSY
    status, _, res = call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "AMBULANCE_ASSIGNED"
    assert res["ambulance"]["status"] == "BUSY"

    # Second incident cannot claim BUSY ambulance -> 409
    _, _, inc2 = call_api("POST", "/incidents", {
        "type": "MEDICAL",
        "description": "Second incident",
        "latitude": 18.52,
        "longitude": 73.85,
        "severity": "HIGH",
        "peopleAffected": 1,
    }, token=disp_token)
    inc2_id = inc2["incidentId"]
    call_api("POST", f"/incidents/{inc2_id}/review", token=op_token)
    call_api("POST", f"/incidents/{inc2_id}/verify", {"decision": "VERIFIED"}, token=op_token)
    status, _, _ = call_api("POST", f"/incidents/{inc2_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)
    assert status == 409

    # Request hospital admission -> HOSPITAL_REQUESTED, beds atomically reserved (2 -> 0)
    status, _, res = call_api("POST", f"/incidents/{inc_id}/request-hospital", {"hospitalId": hosp_id}, token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "HOSPITAL_REQUESTED"
    assert res["reservation"]["bedsReserved"] == 2
    assert res["hospital"]["availableBeds"] == 0

    # Reject -> HOSPITAL_REJECTED, reserved beds released back (0 -> 2)
    status, _, res = call_api("POST", f"/incidents/{inc_id}/hospital-decision", {
        "decision": "REJECTED",
        "reason": "Trauma bay temporarily full",
    }, token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "HOSPITAL_REJECTED"
    assert res["hospital"]["availableBeds"] == 2

    # Re-request hospital (1 bed adjusted) -> HOSPITAL_REQUESTED (2 -> 1)
    status, _, res = call_api("POST", f"/incidents/{inc_id}/request-hospital", {"hospitalId": hosp_id, "bedsRequested": 1}, token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "HOSPITAL_REQUESTED"
    assert res["hospital"]["availableBeds"] == 1

    # Accept -> HOSPITAL_ACCEPTED, beds stay 1 (no double decrement)
    status, _, res = call_api("POST", f"/incidents/{inc_id}/hospital-decision", {"decision": "ACCEPTED"}, token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "HOSPITAL_ACCEPTED"
    assert res["hospital"]["availableBeds"] == 1

    # Duplicate accept -> 409
    status, _, _ = call_api("POST", f"/incidents/{inc_id}/hospital-decision", {"decision": "ACCEPTED"}, token=op_token)
    assert status == 409

    # Record transport -> PATIENT_TRANSPORTED
    status, _, res = call_api("POST", f"/incidents/{inc_id}/transport", token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "PATIENT_TRANSPORTED"

    # Complete incident -> COMPLETED, ambulance released to AVAILABLE
    status, _, res = call_api("POST", f"/incidents/{inc_id}/complete", token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "COMPLETED"
    assert res["ambulance"]["status"] == "AVAILABLE"
    assert res["ambulance"]["assignedIncidentId"] is None

    print("Stage 2 role enforcement & full manual incident workflow: PASSED")


if __name__ == "__main__":
    test_token_security()
    test_full_manual_workflow_with_stage2_roles()
    print("\nALL WORKFLOW AND AUTH TESTS PASSED")
