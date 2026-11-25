"""
Stage 3 Automated Tests — Ambulance Suitability & Concurrent Atomic Dispatch.

NOTE: These tests run against the thread-safe in-memory mock DynamoDB store
(`backend/local_server.py`). They verify atomic transaction logic and conflict
handling locally, and do NOT substitute for live AWS DynamoDB integration tests.
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
    call_api("POST", "/auth/register", {
        "username": "disp_s3",
        "password": "secret",
        "role": "DISPATCHER",
    })
    provision_operator("op_s3", "secret")
    _, d = call_api("POST", "/auth/login", {"username": "disp_s3", "password": "secret"})
    op_token, _ = login_operator_with_otp("op_s3", "secret")
    return d["token"], op_token


def create_verified_incident(disp_token, op_token, equipment=None):
    _, inc = call_api("POST", "/incidents", {
        "type": "ROAD_ACCIDENT",
        "description": "Stage 3 test incident",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "CRITICAL",
        "peopleAffected": 2,
        "requiredResources": ["AMBULANCE"],
        "requiredEquipment": equipment or ["OXYGEN", "DEFIBRILLATOR"],
    }, token=disp_token)
    inc_id = inc["incidentId"]
    call_api("POST", f"/incidents/{inc_id}/review", token=op_token)
    call_api("POST", f"/incidents/{inc_id}/verify", {"decision": "VERIFIED"}, token=op_token)
    return inc_id


def create_ambulance(op_token, reg, equipment=None, lat=18.5210, lng=73.8560):
    _, amb = call_api("POST", "/ambulances", {
        "registrationNumber": reg,
        "latitude": lat,
        "longitude": lng,
        "status": "AVAILABLE",
        "equipment": equipment if equipment is not None else ["OXYGEN", "DEFIBRILLATOR"],
    }, token=op_token)
    return amb["ambulanceId"]


def test_suitability_and_validation():
    disp_token, op_token = setup_users()
    inc_id = create_verified_incident(disp_token, op_token, ["OXYGEN", "DEFIBRILLATOR"])

    # Unsuitable ambulance (missing DEFIBRILLATOR)
    amb_missing = create_ambulance(op_token, "MH12NO001", ["OXYGEN"])
    # Suitable ambulance
    amb_good = create_ambulance(op_token, "MH12OK001", ["OXYGEN", "DEFIBRILLATOR", "TRAUMA_KIT"])

    # Candidates list clearly identifies missing equipment and orders suitable first
    status, cands = call_api("GET", f"/incidents/{inc_id}/candidates", token=op_token)
    assert status == 200
    assert cands["ambulances"][0]["ambulance"]["ambulanceId"] == amb_good
    assert cands["ambulances"][0]["eligible"] is True
    assert cands["ambulances"][1]["ambulance"]["ambulanceId"] == amb_missing
    assert cands["ambulances"][1]["eligible"] is False
    assert cands["ambulances"][1]["missingEquipment"] == ["DEFIBRILLATOR"]

    # Attempting to assign unsuitable ambulance -> 400
    status, body = call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_missing}, token=op_token)
    assert status == 400
    assert "DEFIBRILLATOR" in body["error"]

    # Missing ambulance -> 404
    status, _ = call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": "AMB-DOES-NOT-EXIST"}, token=op_token)
    assert status == 404

    # Missing incident -> 404
    status, _ = call_api("POST", "/incidents/INC-MISSING/assign-ambulance", {"ambulanceId": amb_good}, token=op_token)
    assert status == 404

    # Successful assignment records ambulanceAssignedAt and updates both records atomically
    status, res = call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_good}, token=op_token)
    assert status == 200
    assert res["incident"]["status"] == "AMBULANCE_ASSIGNED"
    assert res["incident"]["assignedAmbulanceId"] == amb_good
    assert res["incident"]["ambulanceAssignedAt"] is not None
    assert res["ambulance"]["status"] == "BUSY"
    assert res["ambulance"]["assignedIncidentId"] == inc_id

    print("Ambulance suitability, missing equipment & atomic timestamp checks: PASSED")


def test_concurrent_two_incidents_same_ambulance():
    disp_token, op_token = setup_users()
    inc1 = create_verified_incident(disp_token, op_token)
    inc2 = create_verified_incident(disp_token, op_token)
    amb_id = create_ambulance(op_token, "MH12RACE1")

    barrier = threading.Barrier(2)

    def attempt(inc_id):
        barrier.wait()
        return call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(attempt, inc1)
        f2 = pool.submit(attempt, inc2)
        r1, r2 = f1.result(), f2.result()

    statuses = sorted([r1[0], r2[0]])
    assert statuses == [200, 409], f"Expected [200, 409], got {statuses}"

    winner_inc = inc1 if r1[0] == 200 else inc2
    loser_inc = inc2 if r1[0] == 200 else inc1

    _, loser_data = call_api("GET", f"/incidents/{loser_inc}", token=op_token)
    assert loser_data["status"] == "VERIFIED"
    assert loser_data["assignedAmbulanceId"] is None

    _, all_ambs = call_api("GET", "/ambulances", token=op_token)
    amb = next(a for a in all_ambs if a["ambulanceId"] == amb_id)
    assert amb["status"] == "BUSY"
    assert amb["assignedIncidentId"] == winner_inc

    print("Concurrency A (2 incidents -> 1 ambulance simultaneously): PASSED")


def test_concurrent_two_ambulances_same_incident():
    disp_token, op_token = setup_users()
    inc_id = create_verified_incident(disp_token, op_token)
    amb1 = create_ambulance(op_token, "MH12RACE2A")
    amb2 = create_ambulance(op_token, "MH12RACE2B")

    barrier = threading.Barrier(2)

    def attempt(amb_id):
        barrier.wait()
        return call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(attempt, amb1)
        f2 = pool.submit(attempt, amb2)
        r1, r2 = f1.result(), f2.result()

    statuses = sorted([r1[0], r2[0]])
    assert statuses == [200, 409], f"Expected [200, 409], got {statuses}"

    winner_amb = amb1 if r1[0] == 200 else amb2
    loser_amb = amb2 if r1[0] == 200 else amb1

    _, inc_data = call_api("GET", f"/incidents/{inc_id}", token=op_token)
    assert inc_data["status"] == "AMBULANCE_ASSIGNED"
    assert inc_data["assignedAmbulanceId"] == winner_amb

    _, all_ambs = call_api("GET", "/ambulances", token=op_token)
    loser_data = next(a for a in all_ambs if a["ambulanceId"] == loser_amb)
    assert loser_data["status"] == "AVAILABLE"
    assert loser_data["assignedIncidentId"] is None

    print("Concurrency B (2 ambulances -> 1 incident simultaneously): PASSED")


def test_concurrent_duplicate_same_request():
    disp_token, op_token = setup_users()
    inc_id = create_verified_incident(disp_token, op_token)
    amb_id = create_ambulance(op_token, "MH12RACE3")

    barrier = threading.Barrier(2)

    def attempt():
        barrier.wait()
        return call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(attempt)
        f2 = pool.submit(attempt)
        r1, r2 = f1.result(), f2.result()

    assert sorted([r1[0], r2[0]]) == [200, 409]
    print("Concurrency C (duplicate simultaneous assignment request): PASSED")


def test_stale_candidate_and_invalid_incident():
    disp_token, op_token = setup_users()
    inc_id = create_verified_incident(disp_token, op_token)
    amb_id = create_ambulance(op_token, "MH12STALE1")

    # Fetch candidates while ambulance is AVAILABLE
    status, cands = call_api("GET", f"/incidents/{inc_id}/candidates", token=op_token)
    assert status == 200
    assert cands["ambulances"][0]["eligible"] is True

    # Ambulance becomes BUSY before assignment
    call_api("PUT", f"/ambulances/{amb_id}", {"status": "BUSY"}, token=op_token)

    status, _ = call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_token)
    assert status == 409

    # Incident remains VERIFIED and unassigned
    _, inc_data = call_api("GET", f"/incidents/{inc_id}", token=op_token)
    assert inc_data["status"] == "VERIFIED"
    assert inc_data["assignedAmbulanceId"] is None

    # Incident becomes CANCELLED before assignment to another available ambulance
    amb2 = create_ambulance(op_token, "MH12STALE2")
    call_api("PUT", f"/incidents/{inc_id}/status", {"status": "CANCELLED"}, token=op_token)
    status, _ = call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb2}, token=op_token)
    assert status == 409

    _, all_ambs = call_api("GET", "/ambulances", token=op_token)
    amb2_data = next(a for a in all_ambs if a["ambulanceId"] == amb2)
    assert amb2_data["status"] == "AVAILABLE"
    assert amb2_data["assignedIncidentId"] is None

    print("Concurrency D & E (stale BUSY ambulance & cancelled incident): PASSED")


if __name__ == "__main__":
    test_suitability_and_validation()
    test_concurrent_two_incidents_same_ambulance()
    test_concurrent_two_ambulances_same_incident()
    test_concurrent_duplicate_same_request()
    test_stale_candidate_and_invalid_incident()
    print("\nALL STAGE 3 AMBULANCE SUITABILITY & CONCURRENCY TESTS PASSED")
