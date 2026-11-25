# Emergency Response & Resource Allocation Platform

Cloud-native final-year academic **Minor Project** prototype for emergency incident reporting, severity-based priority queuing, map-assisted inspection, and human-controlled ambulance dispatch and hospital bed reservation.

> **Disclaimer:** This is an academic simulation/prototype and is **not** a production emergency-services dispatch system. It does **not** perform live ambulance GPS tracking or automatic emergency dispatch.

---

## 1. Architecture (Minor Project)

```
React 19 + Vite + Leaflet / OpenStreetMap Frontend
                    ↓ (HTTPS / JSON + Bearer HMAC Token)
        Amazon API Gateway (REST / HTTP API)
                    ↓
       AWS Lambda (Python — handler.lambda_handler)
       ├── utils/auth.py (HMAC-SHA256 tokens + RBAC)
       ├── services/incident_service.py (priority queue, review, verify)
       ├── services/coordination_service.py (atomic dispatch, bed reservation, dashboard)
       ├── services/ambulance_service.py & hospital_service.py & user_service.py
       └── allocation/engine.py (Haversine distance & suitability ranking)
                    ↓
         Amazon DynamoDB (ap-south-1 — 4 Tables)
         ├── EmergencyUsers       (PK: userId)
         ├── EmergencyIncidents   (PK: incidentId, embedded bedReservation & bounded history)
         ├── EmergencyAmbulances  (PK: ambulanceId)
         └── EmergencyHospitals   (PK: hospitalId)
```

- **Local Development Bridge**: `backend/local_server.py` runs the exact same `handler.lambda_handler`, services, and repositories against a thread-safe **in-memory mock DynamoDB** for local testing and demonstrations. It does **not** connect to live AWS.
- **Load Testing Suite**: `backend/load_tests/` uses Locust (dev-only; excluded from Lambda `requirements.txt`).

---

## 2. Approved Two-Role Model & Security Controls

| Role | Responsibilities & Restrictions |
|---|---|
| **`DISPATCHER`** | Publicly registrable (1-step username/password login). Reports emergency incidents (interactive Leaflet map picker, browser geolocation, or manual coordinates) and views **only their own reported incidents** with sanitized basic fields (`incidentId`, `type`/`emergencyType`, `description`, `severity`, `priority`, `status`, `createdAt`, `updatedAt`, `latitude`, `longitude`, `peopleAffected`, `isArchived`). Receives `404` on other users' or legacy incidents, and `403 Forbidden` on global queue, dashboard, ambulances, hospitals, archived list, and all operational actions. |
| **`RESOURCE_OPERATOR`** | Internally provisioned only (public `RESOURCE_OPERATOR` signup returns `403`). Requires **two-step login** (password + single-use 6-digit OTP expiring in 5 minutes, max 5 attempts; printed to local terminal only when `LOCAL_OTP_CONSOLE=true`). Manages full operational workflow: Dashboard, P1–P4 Priority Queue, Incident Inspection/Review/Verification, Atomic Ambulance Dispatch, Atomic Multi-Bed Hospital Reservation/Decision/Cancellation, Patient Transport, Incident Completion, Completed Incident Archiving (`Archived Incidents` view), and Ambulance/Hospital management. |

---

## 3. Complete Human-Controlled Workflow

1. **Incident Registration (`CREATED`)** — Dispatcher submits incident type, severity, people affected, description, required equipment, and coordinates (map click, draggable marker, browser geolocation, or manual entry). Backend generates authoritative UTC ISO-8601 `createdAt`/`updatedAt` and derives priority (`CRITICAL→P1`, `HIGH→P2`, `MEDIUM→P3`, `LOW→P4`).
2. **Priority Queue & Inspection (`UNDER_REVIEW`)** — Queue sorts deterministically by `P1 → P4`, then oldest `createdAt` first; UI displays `Asia/Kolkata` (IST) times, elapsed waiting time, and configurable overdue alerts (`P1: 5m, P2: 15m, P3: 30m, P4: 60m`). Resource Operator starts review.
3. **Verification / Rejection (`VERIFIED` or `REJECTED`)** — Resource Operator verifies (records `verifiedAt`) or rejects with remarks. Unverified incidents cannot receive ambulances.
4. **Atomic Manual Ambulance Dispatch (`AMBULANCE_ASSIGNED`)** — Backend ranks candidates by suitability (availability + required equipment + unassigned) and Haversine distance. Resource Operator manually selects an ambulance; atomic 2-item transaction sets ambulance `BUSY` + `assignedIncidentId` and incident `AMBULANCE_ASSIGNED` + `ambulanceAssignedAt` (`409 Conflict` on race). **Navigate to Incident** external Google Maps button becomes available.
5. **Hospital Selection & Atomic Multi-Bed Reservation (`HOSPITAL_REQUESTED`)** — Default `requiredBeds = peopleAffected` (operator-adjustable positive integer). Atomic 2-item transaction checks hospital `ACTIVE` + `availableBeds >= bedsRequested`, decrements `availableBeds`, creates embedded `bedReservation` (`RESERVED`), and updates the incident (`409` on insufficient capacity or race).
6. **Hospital Decision / Cancellation (`HOSPITAL_ACCEPTED`, `HOSPITAL_REJECTED`, or `AMBULANCE_ASSIGNED`)**:
   - **Accept (`CONFIRMED`)**: Records `hospitalAcceptedAt`, transitions `bedReservation` to `CONFIRMED` (**no second bed decrement**), and unlocks **Navigate to Hospital** external Google Maps directions using actual stored hospital coordinates.
   - **Reject (`REJECTED`) / Cancel (`RELEASED`)**: Atomically returns reserved beds **exactly once** (conditional check on `bedReservation.status == RESERVED` prevents duplicate releases), appends to bounded `reservationHistory` (capped at 20 entries), and allows selecting another hospital while keeping the ambulance assigned.
7. **Patient Transport (`PATIENT_TRANSPORTED`)** — Resource Operator records transport (`transportedAt`).
8. **Completion (`COMPLETED`) & Archiving (`isArchived`)** — Atomic 2-item transaction records `completedAt` and releases the assigned ambulance back to `AVAILABLE` (`assignedIncidentId = None`) while retaining the confirmed hospital reservation, history, and bed count. Resource Operators can then archive `COMPLETED` incidents (`POST /incidents/{id}/archive`), preserving `status = COMPLETED` and full history while moving them from active lists/queue into **Archived Incidents** (`GET /incidents/archived`).

---

## 4. Local Load Testing Summary (Mock Server Only)

> **Disclaimer:** Benchmarks were executed with Locust `2.47.0` against `backend/local_server.py` (in-memory mock DynamoDB) on Windows 11 Pro (AMD Athlon Silver 3050U, 2 logical cores, 5.94 GB RAM). These numbers do **not** establish AWS Lambda, API Gateway, or DynamoDB production capacity.

| Level | Users | Duration | Total Reqs | Failed | Failure % | RPS | Avg (ms) | Med (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Level 1 | 10 | 15s | 242 | 0 | 0.00% | 18.97 | 13.0 | 9 | 32 | 89 | 97.0 |
| Level 2 | 25 | 15s | 517 | 0 | 0.00% | 39.81 | 44.5 | 15 | 180 | 530 | 1059.8 |
| Level 3 | 50 | 15s | 916 | 2 | 0.22% | 70.92 | 126.1 | 14 | 660 | 1600 | 2231.9 |
| Level 4 | 100 | 15s | 1,814 | 0 | 0.00% | 141.73 | 101.0 | 19 | 550 | 1100 | 1642.4 |
| Level 5 | 200 | 15s | 2,551 | 71 | 2.78% | 192.36 | 290.9 | 110 | 1200 | 2100 | 2173.3 |

Full CSV outputs and bottleneck analysis (including Windows `ThreadingHTTPServer` TCP listen-backlog `10061` refusals and resulting `401` rejections at 200 users): [backend/load_tests/PERFORMANCE_REPORT.md](backend/load_tests/PERFORMANCE_REPORT.md).

---

## 5. Running Locally (PowerShell)

### 1. Run Complete Backend Test Suite (27 Suites)
```powershell
.\backend\.venv\Scripts\python.exe backend\src\run_all_tests.py
```

### 2. Start Local Simulated API Server (Terminal 1)
```powershell
.\backend\.venv\Scripts\python.exe backend\local_server.py
```
Seeded local demo accounts:
- **Dispatcher (1-step login)**: `dispatcher1` / `dispatcher123`
- **Resource Operator (2-step login — 6-digit OTP printed in local terminal)**: `operator1` / `operator123`

### 3. Start React Frontend (Terminal 2)
```powershell
cd frontend
npm run dev
```
Open `http://localhost:5173`. To point at AWS API Gateway after deployment, copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_BASE_URL`.

---

## 6. Documentation
- [docs/PROJECT_MASTER_SPEC.md](docs/PROJECT_MASTER_SPEC.md) — Canonical specification & Minor Project reconciliation
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Implemented Minor architecture & planned Major evolution
- [docs/DATABASE_AND_API_SPEC.md](docs/DATABASE_AND_API_SPEC.md) — Final 4-table DynamoDB schema & complete REST API contract
- [docs/DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md) — Chronological engineering & verification log
- [backend/load_tests/PERFORMANCE_REPORT.md](backend/load_tests/PERFORMANCE_REPORT.md) — Local Locust benchmark report
