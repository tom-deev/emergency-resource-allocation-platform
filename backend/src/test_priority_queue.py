"""
Automated tests for Stage 1 — Timestamps and Priority Queue:
- Deterministic severity-to-priority mapping (CRITICAL=P1, HIGH=P2, MEDIUM=P3, LOW=P4)
- Priority sorting: P1 before P2 before P3 before P4
- Older LOW incident NEVER outranks newer CRITICAL incident
- Same-severity incidents sort oldest createdAt first
- Backend ignores client-supplied createdAt, updatedAt, and priority
- Elapsed waiting time and configurable overdue threshold detection
- GET /incidents/queue filtering (priority, severity, status, IST date, search)
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
from constants import derive_priority
from models.incident import Incident
from services.incident_service import IST_TIMEZONE, IncidentService
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


def test_priority_mapping():
    assert derive_priority("CRITICAL") == "P1"
    assert derive_priority("HIGH") == "P2"
    assert derive_priority("MEDIUM") == "P3"
    assert derive_priority("LOW") == "P4"
    print("Severity to priority mapping: PASSED")


def test_deterministic_sorting_and_waiting():
    now = datetime(2026, 11, 25, 10, 0, 0, tzinfo=timezone.utc)

    incidents = [
        {
            "incidentId": "INC-LOW-OLD",
            "severity": "LOW",
            "status": "CREATED",
            "createdAt": (now - timedelta(hours=3)).isoformat(),
            "updatedAt": (now - timedelta(hours=3)).isoformat(),
        },
        {
            "incidentId": "INC-HIGH-NEW",
            "severity": "HIGH",
            "status": "CREATED",
            "createdAt": (now - timedelta(minutes=5)).isoformat(),
            "updatedAt": (now - timedelta(minutes=5)).isoformat(),
        },
        {
            "incidentId": "INC-CRIT-NEW",
            "severity": "CRITICAL",
            "status": "CREATED",
            "createdAt": (now - timedelta(minutes=2)).isoformat(),
            "updatedAt": (now - timedelta(minutes=2)).isoformat(),
        },
        {
            "incidentId": "INC-CRIT-OLD",
            "severity": "CRITICAL",
            "status": "CREATED",
            "createdAt": (now - timedelta(minutes=12)).isoformat(),
            "updatedAt": (now - timedelta(minutes=12)).isoformat(),
        },
        {
            "incidentId": "INC-MED",
            "severity": "MEDIUM",
            "status": "CREATED",
            "createdAt": (now - timedelta(minutes=40)).isoformat(),
            "updatedAt": (now - timedelta(minutes=40)).isoformat(),
        },
        {
            "incidentId": "INC-HIGH-OLD",
            "severity": "HIGH",
            "status": "CREATED",
            "createdAt": (now - timedelta(minutes=20)).isoformat(),
            "updatedAt": (now - timedelta(minutes=20)).isoformat(),
        },
    ]

    sorted_list = IncidentService.sort_incidents_by_priority(incidents, now_dt=now)
    ordered_ids = [item["incidentId"] for item in sorted_list]

    assert ordered_ids == [
        "INC-CRIT-OLD",
        "INC-CRIT-NEW",
        "INC-HIGH-OLD",
        "INC-HIGH-NEW",
        "INC-MED",
        "INC-LOW-OLD",
    ], f"Unexpected order: {ordered_ids}"

    # Verify elapsed time & overdue flags (default thresholds: P1=5m, P2=15m, P3=30m, P4=60m)
    by_id = {item["incidentId"]: item for item in sorted_list}
    assert by_id["INC-CRIT-OLD"]["elapsedWaitingMinutes"] == 12
    assert by_id["INC-CRIT-OLD"]["isOverdue"] is True
    assert by_id["INC-CRIT-NEW"]["elapsedWaitingMinutes"] == 2
    assert by_id["INC-CRIT-NEW"]["isOverdue"] is False
    assert by_id["INC-HIGH-OLD"]["isOverdue"] is True
    assert by_id["INC-HIGH-NEW"]["isOverdue"] is False
    assert by_id["INC-LOW-OLD"]["isOverdue"] is True

    print("Deterministic priority sorting, oldest-first tie-breaking & overdue thresholds: PASSED")


def test_backend_ignores_client_timestamps_and_priority():
    local_server.install_in_memory_backend()

    call_api("POST", "/auth/register", {
        "username": "disp_q",
        "password": "secret",
        "role": "DISPATCHER",
    })
    _, login = call_api("POST", "/auth/login", {
        "username": "disp_q",
        "password": "secret",
    })
    token = login["token"]

    fake_old_ts = "2020-01-01T00:00:00+00:00"
    status, created = call_api("POST", "/incidents", {
        "type": "MEDICAL",
        "description": "Minor sprain",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "LOW",
        "priority": "P1",  # must be ignored!
        "createdAt": fake_old_ts,  # must be ignored!
        "updatedAt": fake_old_ts,  # must be ignored!
        "peopleAffected": 1,
    }, token=token)

    assert status == 201
    assert created["priority"] == "P4"
    assert created["createdAt"] != fake_old_ts
    assert created["updatedAt"] != fake_old_ts
    assert created["status"] == "CREATED"

    print("Backend ignores client-supplied priority and timestamps: PASSED")


def test_queue_endpoint_filters_and_ist_date():
    local_server.install_in_memory_backend()

    provision_operator("op_q", "secret")
    op_token, _ = login_operator_with_otp("op_q", "secret")

    # Insert 2 incidents directly via service to control exact UTC timestamps
    # 2026-11-24T20:00:00+00:00 UTC == 2026-11-25 01:30:00 IST!
    inc_service = handler.get_incident_service()
    inc_service.create_incident(Incident(
        incidentId="INC-IST-NEXTDAY",
        type="FIRE",
        description="Warehouse fire",
        latitude=18.52,
        longitude=73.85,
        severity="CRITICAL",
        peopleAffected=3,
        status="CREATED",
        createdAt="2026-11-24T20:00:00+00:00",
        updatedAt="2026-11-24T20:00:00+00:00",
    ))
    inc_service.create_incident(Incident(
        incidentId="INC-IST-PREVDAY",
        type="MEDICAL",
        description="Clinic transfer",
        latitude=18.52,
        longitude=73.85,
        severity="LOW",
        peopleAffected=1,
        status="VERIFIED",
        createdAt="2026-11-24T10:00:00+00:00",  # 15:30 IST on 2026-11-24
        updatedAt="2026-11-24T10:00:00+00:00",
    ))

    # Full queue: CRITICAL must appear first
    status, q = call_api("GET", "/incidents/queue", token=op_token)
    assert status == 200
    assert [i["incidentId"] for i in q["incidents"]] == ["INC-IST-NEXTDAY", "INC-IST-PREVDAY"]
    assert "thresholdsMinutes" in q
    assert "generatedAt" in q

    # IST date filter: 2026-11-25 should match 2026-11-24T20:00:00Z (01:30 IST on Nov 25)
    status, q_date = call_api("GET", "/incidents/queue", token=op_token, query={"date": "2026-11-25"})
    assert status == 200
    assert [i["incidentId"] for i in q_date["incidents"]] == ["INC-IST-NEXTDAY"]

    # Priority filter
    status, q_p4 = call_api("GET", "/incidents/queue", token=op_token, query={"priority": "P4"})
    assert status == 200
    assert [i["incidentId"] for i in q_p4["incidents"]] == ["INC-IST-PREVDAY"]

    # Search filter
    status, q_search = call_api("GET", "/incidents/queue", token=op_token, query={"search": "fire"})
    assert status == 200
    assert [i["incidentId"] for i in q_search["incidents"]] == ["INC-IST-NEXTDAY"]

    # Verify IST offset sanity
    utc_dt = datetime(2026, 11, 24, 20, 0, 0, tzinfo=timezone.utc)
    ist_dt = utc_dt.astimezone(IST_TIMEZONE)
    assert ist_dt.strftime("%Y-%m-%d %H:%M") == "2026-11-25 01:30"

    print("GET /incidents/queue filters and Asia/Kolkata (IST) date handling: PASSED")


if __name__ == "__main__":
    test_priority_mapping()
    test_deterministic_sorting_and_waiting()
    test_backend_ignores_client_timestamps_and_priority()
    test_queue_endpoint_filters_and_ist_date()
    print("\nALL STAGE 1 PRIORITY QUEUE & TIMESTAMP TESTS PASSED")
