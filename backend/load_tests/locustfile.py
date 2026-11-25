"""
Locust Load Testing Suite — Emergency Response & Resource Allocation Platform.

Aligned with Stage 8 role isolation and two-step operator OTP:
- DispatcherUser ONLY calls Dispatcher-permitted endpoints:
  POST /auth/login, GET /incidents, GET /incidents/{id}, and opt-in
  POST /incidents [load-test]. Never calls /incidents/queue, /dashboard/summary,
  /ambulances, or /hospitals.
- ResourceOperatorUser uses a pre-provisioned operator ACCESS token supplied
  via LOAD_TEST_OPERATOR_TOKEN (since operator login requires two-step OTP).
- Default mode is READ-ONLY (`LOAD_TEST_ENABLE_MUTATIONS=false`).
- Running against `backend/local_server.py` measures LOCAL IN-MEMORY MOCK
  performance only and does NOT measure AWS Lambda, API Gateway, or DynamoDB
  production capacity.
"""

import os
import random
import uuid

from locust import HttpUser, between, events, task


DISPATCHER_USER = os.environ.get("LOAD_TEST_DISPATCHER_USER", "lt_dispatcher")
DISPATCHER_PASS = os.environ.get("LOAD_TEST_DISPATCHER_PASS", "lt_disp_pass_2026")
OPERATOR_ACCESS_TOKEN = os.environ.get("LOAD_TEST_OPERATOR_TOKEN", "")
ENABLE_MUTATIONS = os.environ.get("LOAD_TEST_ENABLE_MUTATIONS", "false").lower() == "true"
LOAD_TEST_TAG = "[LOAD_TEST]"


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Ensure the dedicated load-test DISPATCHER account exists.
    Public registration is DISPATCHER-only; RESOURCE_OPERATOR accounts are
    provisioned internally and authenticated via two-step OTP.
    """
    import json
    import urllib.error
    import urllib.request

    host = (environment.host or os.environ.get("LOAD_TEST_HOST", "http://127.0.0.1:8000")).rstrip("/")
    payload = json.dumps({
        "username": DISPATCHER_USER,
        "password": DISPATCHER_PASS,
        "role": "DISPATCHER",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/auth/register",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except urllib.error.HTTPError:
        pass
    except Exception:
        pass


class DispatcherUser(HttpUser):
    """Simulates a DISPATCHER using only ownership-scoped Dispatcher endpoints."""

    weight = 1
    wait_time = between(0.2, 0.8)

    def on_start(self):
        self.headers = {"Content-Type": "application/json"}
        self.own_incident_ids = []
        with self.client.post(
            "/auth/login",
            json={"username": DISPATCHER_USER, "password": DISPATCHER_PASS},
            name="POST /auth/login (DISPATCHER)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.json().get("token"):
                self.headers["Authorization"] = f"Bearer {resp.json()['token']}"
                resp.success()
            else:
                resp.failure(f"Dispatcher login failed: HTTP {resp.status_code}")

    @task(5)
    def view_own_incidents(self):
        with self.client.get(
            "/incidents",
            headers=self.headers,
            name="GET /incidents (DISPATCHER own)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                items = resp.json()
                if isinstance(items, list):
                    self.own_incident_ids = [
                        i["incidentId"] for i in items[:15] if isinstance(i, dict) and i.get("incidentId")
                    ]
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def view_own_incident_detail(self):
        if not self.own_incident_ids:
            return
        inc_id = random.choice(self.own_incident_ids)
        self.client.get(
            f"/incidents/{inc_id}",
            headers=self.headers,
            name="GET /incidents/{id} (DISPATCHER own)",
        )

    @task(1)
    def create_isolated_test_incident(self):
        if not ENABLE_MUTATIONS:
            return
        payload = {
            "type": "MEDICAL",
            "description": f"{LOAD_TEST_TAG} Load-test incident {uuid.uuid4().hex[:8]}",
            "latitude": round(18.50 + random.uniform(0.0, 0.05), 5),
            "longitude": round(73.82 + random.uniform(0.0, 0.06), 5),
            "severity": random.choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
            "peopleAffected": random.randint(1, 3),
            "requiredResources": ["AMBULANCE"],
            "requiredEquipment": ["OXYGEN"],
        }
        self.client.post(
            "/incidents",
            json=payload,
            headers=self.headers,
            name="POST /incidents [load-test]",
        )


class ResourceOperatorUser(HttpUser):
    """
    Simulates a RESOURCE_OPERATOR inspecting the global queue, dashboard,
    ambulances, hospitals, archived list, and resource candidates.

    Requires LOAD_TEST_OPERATOR_TOKEN (obtained via two-step OTP sign-in).
    """

    weight = 2
    wait_time = between(0.2, 0.8)

    def on_start(self):
        self.headers = {"Content-Type": "application/json"}
        self.known_incident_ids = []
        if OPERATOR_ACCESS_TOKEN:
            self.headers["Authorization"] = f"Bearer {OPERATOR_ACCESS_TOKEN}"

    @task(5)
    def view_priority_queue(self):
        if not OPERATOR_ACCESS_TOKEN:
            return
        with self.client.get(
            "/incidents/queue",
            headers=self.headers,
            name="GET /incidents/queue",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                items = resp.json().get("incidents", [])
                self.known_incident_ids = [
                    i["incidentId"] for i in items[:15] if isinstance(i, dict) and i.get("incidentId")
                ]
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(3)
    def view_dashboard(self):
        if not OPERATOR_ACCESS_TOKEN:
            return
        self.client.get("/dashboard/summary", headers=self.headers, name="GET /dashboard/summary")

    @task(3)
    def inspect_incident(self):
        if not OPERATOR_ACCESS_TOKEN or not self.known_incident_ids:
            return
        inc_id = random.choice(self.known_incident_ids)
        self.client.get(f"/incidents/{inc_id}", headers=self.headers, name="GET /incidents/{id}")

    @task(3)
    def fetch_resource_candidates(self):
        if not OPERATOR_ACCESS_TOKEN or not self.known_incident_ids:
            return
        inc_id = random.choice(self.known_incident_ids)
        self.client.get(
            f"/incidents/{inc_id}/candidates",
            headers=self.headers,
            name="GET /incidents/{id}/candidates",
        )

    @task(2)
    def view_ambulances(self):
        if not OPERATOR_ACCESS_TOKEN:
            return
        self.client.get("/ambulances", headers=self.headers, name="GET /ambulances")

    @task(2)
    def view_hospitals(self):
        if not OPERATOR_ACCESS_TOKEN:
            return
        self.client.get("/hospitals", headers=self.headers, name="GET /hospitals")

    @task(1)
    def view_archived_incidents(self):
        if not OPERATOR_ACCESS_TOKEN:
            return
        self.client.get("/incidents/archived", headers=self.headers, name="GET /incidents/archived")
