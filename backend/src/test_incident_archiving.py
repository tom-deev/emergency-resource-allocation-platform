"""
Stage 8D Automated Tests — Completed Incident Archiving, Archived View,
Concurrency Protection, Ownership Transparency & Dashboard Accounting.

Covers all 17 required scenarios.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
import threading
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import local_server
import handler
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


def setup_users():
    local_server.install_in_memory_backend()
    call_api("POST", "/auth/register", {"username": "disp_8d", "password": "secret", "role": "DISPATCHER"})
    call_api("POST", "/auth/register", {"username": "disp_8d_other", "password": "secret", "role": "DISPATCHER"})
    provision_operator("op_8d", "secret", user_id="OP-8D-001")

    _, d1 = call_api("POST", "/auth/login", {"username": "disp_8d", "password": "secret"})
    _, d2 = call_api("POST", "/auth/login", {"username": "disp_8d_other", "password": "secret"})
    op_tok, _ = login_operator_with_otp("op_8d", "secret")
    return d1["token"], d2["token"], op_tok


def run_incident_to_completed(disp_tok, op_tok, amb_id, hosp_id, desc):
    _, inc = call_api("POST", "/incidents", {
        "type": "ROAD_ACCIDENT",
        "description": desc,
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "HIGH",
        "peopleAffected": 1,
        "requiredEquipment": ["OXYGEN"],
    }, token=disp_tok)
    inc_id = inc["incidentId"]
    call_api("POST", f"/incidents/{inc_id}/review", token=op_tok)
    call_api("POST", f"/incidents/{inc_id}/verify", {"decision": "VERIFIED"}, token=op_tok)
    call_api("POST", f"/incidents/{inc_id}/assign-ambulance", {"ambulanceId": amb_id}, token=op_tok)
    call_api("POST", f"/incidents/{inc_id}/request-hospital", {"hospitalId": hosp_id, "bedsRequested": 1}, token=op_tok)
    call_api("POST", f"/incidents/{inc_id}/hospital-decision", {"decision": "ACCEPTED"}, token=op_tok)
    call_api("POST", f"/incidents/{inc_id}/transport", token=op_tok)
    status, _ = call_api("POST", f"/incidents/{inc_id}/complete", token=op_tok)
    assert status == 200
    return inc_id


def test_archiving_workflow_permissions_and_history():
    d1_tok, d2_tok, op_tok = setup_users()

    _, amb = call_api("POST", "/ambulances", {
        "registrationNumber": "MH12ARC1",
        "latitude": 18.52,
        "longitude": 73.85,
        "status": "AVAILABLE",
        "equipment": ["OXYGEN"],
    }, token=op_tok)
    amb_id = amb["ambulanceId"]

    _, hosp = call_api("POST", "/hospitals", {
        "name": "Archive Test Hospital",
        "latitude": 18.52,
        "longitude": 73.85,
        "totalBeds": 10,
        "availableBeds": 10,
        "facilities": ["EMERGENCY"],
        "status": "ACTIVE",
    }, token=op_tok)
    hosp_id = hosp["hospitalId"]

    # Create an incomplete incident (CREATED)
    _, inc_open = call_api("POST", "/incidents", {
        "type": "MEDICAL",
        "description": "Still open",
        "latitude": 18.52,
        "longitude": 73.85,
        "severity": "MEDIUM",
        "peopleAffected": 1,
    }, token=d1_tok)
    open_id = inc_open["incidentId"]

    # 3. Incomplete incident cannot be archived -> 409
    assert call_api("POST", f"/incidents/{open_id}/archive", token=op_tok)[0] == 409
    # Nonexistent incident -> 404
    assert call_api("POST", "/incidents/INC-NOPE/archive", token=op_tok)[0] == 404

    # Complete two incidents
    inc1_id = run_incident_to_completed(d1_tok, op_tok, amb_id, hosp_id, "Completed #1")
    inc2_id = run_incident_to_completed(d1_tok, op_tok, amb_id, hosp_id, "Completed #2")

    # 2. Dispatcher cannot archive or view /incidents/archived -> 403
    assert call_api("POST", f"/incidents/{inc1_id}/archive", token=d1_tok)[0] == 403
    assert call_api("GET", "/incidents/archived", token=d1_tok)[0] == 403

    # 1, 6, 7, 8. Resource Operator archives inc1; spoofed archivedBy/archivedAt ignored
    fake_ts = "2020-01-01T00:00:00+00:00"
    status, arch1 = call_api("POST", f"/incidents/{inc1_id}/archive", {
        "archivedBy": "FAKE_USER",
        "archivedAt": fake_ts,
    }, token=op_tok)
    assert status == 200
    a_inc1 = arch1["incident"]
    assert a_inc1["status"] == "COMPLETED"
    assert a_inc1["isArchived"] is True
    assert a_inc1["archivedBy"] == "OP-8D-001"
    assert a_inc1["archivedAt"] is not None and a_inc1["archivedAt"] != fake_ts

    # 15. Original workflow timestamps & reservation history preserved
    assert a_inc1["createdAt"] is not None
    assert a_inc1["verifiedAt"] is not None
    assert a_inc1["ambulanceAssignedAt"] is not None
    assert a_inc1["hospitalRequestedAt"] is not None
    assert a_inc1["hospitalAcceptedAt"] is not None
    assert a_inc1["transportedAt"] is not None
    assert a_inc1["completedAt"] is not None
    assert a_inc1["bedReservation"]["status"] == "CONFIRMED"
    assert len(a_inc1["reservationHistory"]) == 1

    # 4. Duplicate archive -> 409
    assert call_api("POST", f"/incidents/{inc1_id}/archive", token=op_tok)[0] == 409

    # 5. Concurrent archive on inc2 -> exactly one 200 and one 409
    time.sleep(0.02)  # ensure distinct archivedAt ordering vs inc1
    barrier = threading.Barrier(2)

    def archive_inc2():
        barrier.wait()
        return call_api("POST", f"/incidents/{inc2_id}/archive", token=op_tok)

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(archive_inc2)
        f2 = pool.submit(archive_inc2)
        r1, r2 = f1.result(), f2.result()

    assert sorted([r1[0], r2[0]]) == [200, 409]

    # 9 & 10. Archived incidents disappear from Resource Operator active list & priority queue
    _, op_active = call_api("GET", "/incidents", token=op_tok)
    assert [i["incidentId"] for i in op_active] == [open_id]

    _, op_queue = call_api("GET", "/incidents/queue", token=op_tok)
    assert [i["incidentId"] for i in op_queue["incidents"]] == [open_id]

    # 11 & 12. Archived incidents appear in GET /incidents/archived sorted newest archivedAt first
    status, archived_list = call_api("GET", "/incidents/archived", token=op_tok)
    assert status == 200
    assert [i["incidentId"] for i in archived_list] == [inc2_id, inc1_id]

    # 13 & 14. Dispatcher 1 still sees all 3 own incidents (including archived), sanitized!
    _, d1_list = call_api("GET", "/incidents", token=d1_tok)
    assert {i["incidentId"] for i in d1_list} == {open_id, inc1_id, inc2_id}
    for item in d1_list:
        assert set(item.keys()).issubset(ALLOWED_DISPATCHER_FIELDS)
        assert "archivedBy" not in item
        assert "archivedAt" not in item
        assert "bedReservation" not in item
    archived_in_d1 = {i["incidentId"]: i["isArchived"] for i in d1_list}
    assert archived_in_d1[inc1_id] is True
    assert archived_in_d1[open_id] is False

    # Dispatcher 2 still sees 0 incidents
    _, d2_list = call_api("GET", "/incidents", token=d2_tok)
    assert d2_list == []

    # 16. Dashboard metrics stay historically accurate without double-counting
    _, dash = call_api("GET", "/dashboard/summary", token=op_tok)
    assert dash["totalIncidents"] == 3
    assert dash["completedIncidents"] == 2
    assert dash["archivedIncidents"] == 2

    print("All Stage 8D archiving, concurrency, privacy & dashboard tests: PASSED")


if __name__ == "__main__":
    test_archiving_workflow_permissions_and_history()
    print("\nALL STAGE 8D INCIDENT ARCHIVING TESTS PASSED")
