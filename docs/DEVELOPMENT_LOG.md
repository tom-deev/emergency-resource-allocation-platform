DEVELOPMENT LOG

Emergency Response & Resource Allocation Platform Using Cloud-Native Architecture

Project: Emergency Response & Resource Allocation Platform Using
Cloud-Native Architecture
Stage: Minor Project
Repository: emergency-resource-allocation-platform
Development Environment: Windows + VS Code
Frontend: React + Vite
Backend: AWS API Gateway + AWS Lambda
Database: Amazon DynamoDB

1. Purpose

This document records the actual development history of the project.

It is a living engineering log and will be updated throughout
development.

It records:

implementation work

technical decisions

changes

errors

debugging

fixes

verification

milestones

important development observations

This document must reflect actual work performed.

No fabricated commits, contributors, implementation history, or test
results should be added.

2. Project Starting State

The project planning and design phase was completed before backend
implementation began.

Completed Project Documents

PROJECT_MASTER_SPEC.md

ARCHITECTURE.md

DATABASE_AND_API_SPEC.md

DEVELOPMENT_LOG.md

Approved Project Direction

The project is being developed as a Minor Project that will later be
extended into the Major Project.

The Major Project will extend the same working Minor system rather than
rebuilding it from scratch.

3. Approved Minor Architecture

The approved Minor architecture is:

React Frontend
      ↓
Amazon API Gateway
      ↓
AWS Lambda
      ↓
Amazon DynamoDB
      ↓
Resource Allocation Logic

The Minor does not require third-party mapping or routing APIs.

Incident, ambulance, and hospital locations use latitude and longitude.

Approximate geographical distance will be calculated inside the backend
using the stored coordinates.

4. Approved Minor Roles

The Minor contains exactly two roles:

DISPATCHER
RESOURCE_OPERATOR

There is no separate Admin role in the Minor.

5. Approved Minor Entities

The Minor uses four logical DynamoDB entities:

Users
Incidents
Ambulances
Hospitals

6. Approved API Contract

The initial approved API contract is:

POST /auth/register
POST /auth/login

POST /incidents
GET /incidents
GET /incidents/{id}
PUT /incidents/{id}/status

POST /ambulances
GET /ambulances
PUT /ambulances/{id}

POST /hospitals
GET /hospitals
PUT /hospitals/{id}

POST /incidents/{id}/allocate

The allocation endpoint is a core part of the Minor Project.

7. Development Environment

The project is being developed on Windows using VS Code.

The known development versions at the start of the implementation phase
are:

Git: 2.54.0.windows.1
Node: v24.15.0
npm: 11.12.1
Vite: v8.2.2

Project location:

C:\Users\tomax\Projects\emergency-resource-allocation-platform

8. Repository Setup

The GitHub repository is:

emergency-resource-allocation-platform

The repository is public and has been cloned locally.

The working branch is:

main

At the documentation baseline, the working tree was clean and
synchronized with the remote repository.

Git history must represent actual work performed.

9. Frontend Setup

The React frontend was created using Vite.

Frontend location:

frontend

The frontend was created with:

npm create vite@latest frontend -- --template react

ESLint was selected during setup.

Dependencies were installed successfully.

The frontend was successfully tested using:

http://localhost:5173/

The Vite development server worked successfully.

Important Development Rule

The working React frontend must not be unnecessarily recreated,
reinstalled, or replaced.

10. Project Folder Structure

The planned project structure is:

emergency-resource-allocation-platform
│
├── backend
│   └── functions
│       ├── auth
│       ├── incidents
│       ├── ambulances
│       ├── hospitals
│       └── allocation
│
├── docs
│   ├── PROJECT_MASTER_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE_AND_API_SPEC.md
│   └── DEVELOPMENT_LOG.md
│
├── frontend
│   ├── src
│   ├── public
│   ├── package.json
│   └── ...
│
├── infrastructure
│
└── README.md

At the folder-structure stage, implementation files were intentionally
not created before their implementation phase.

11. Development History

2026-09-04 --- Project Documentation and Development Baseline

Objective

Complete the project documentation baseline and establish the starting
point for implementation.

Work Completed

Project concept finalized.

Minor → Major strategy finalized.

Minor roles finalized.

Minor feature scope finalized.

Minor architecture finalized.

API strategy clarified.

Third-party API policy clarified.

Database entities finalized.

Initial API list finalized.

Incident lifecycle finalized.

Resource Allocation Engine concept finalized.

Local development environment established.

Git installed/configured.

GitHub repository created and cloned.

React/Vite frontend created.

Frontend dependencies installed.

Frontend successfully tested.

Project folder structure created.

Documentation strategy finalized.

PROJECT_MASTER_SPEC.md completed.

ARCHITECTURE.md completed.

DATABASE_AND_API_SPEC.md completed.

DEVELOPMENT_LOG.md created.

Important Decisions Recorded

Minor contains only Dispatcher and Resource Operator roles.

Minor uses Users, Incidents, Ambulances, and Hospitals as logical
entities.

Minor architecture uses React, API Gateway, Lambda, and DynamoDB.

Minor does not require a third-party external API.

Latitude and longitude are stored for relevant resources.

Approximate distance is calculated by backend logic.

Major will extend the Minor rather than rebuild it.

Allocation scoring will be designed and finalized when allocation
implementation begins.

Verification

Frontend development server successfully opened at:

http://localhost:5173/

The frontend was confirmed working before moving toward backend
implementation.

Status

COMPLETED

12. Future Development Entry Format

Every significant future development activity should be recorded using
this structure:

YYYY-MM-DD --- Milestone/Task Name

Objective

What we intended to accomplish.

Work Completed

What was actually implemented.

Files Changed

Files created, modified, or deleted.

Technical Decisions

Important decisions made during implementation.

Issues

Actual errors or unexpected behavior encountered.

Fix

How the issue was diagnosed and resolved.

Verification

How the implementation was tested and the observed result.

Status

COMPLETED

or:

IN PROGRESS

or:

BLOCKED

13. Engineering Rules for Development

The following rules apply throughout implementation:

Work incrementally.

Verify meaningful changes.

Do not rebuild working components unnecessarily.

Diagnose actual errors before changing working architecture.

Do not expose secrets.

Keep AWS costs low.

Keep the Minor implementation understandable.

Preserve the approved architecture unless a change is explicitly
justified.

Ensure the Major extends the Minor.

Record important technical decisions honestly.

Do not fabricate development history.

Do not claim a feature is complete until it has been implemented and
verified.

14. Major Project Extension

The Major Project may extend the Minor with services and capabilities
such as:

Amazon EventBridge

Amazon SQS

Dead Letter Queue

AWS Step Functions

Amazon SNS

Amazon Cognito

CloudWatch

Amazon S3

AWS Glue

Amazon Athena

historical analytics

audit logging

optional routing/mapping integration

These services must only be introduced when there is a clear technical
purpose.

The Major should build on the Minor's existing working components.

15. Current Project Status

Project planning                  COMPLETE
Architecture definition           COMPLETE
Database/API specification        COMPLETE
Frontend setup                    COMPLETE
Frontend verification             COMPLETE
Development log                   COMPLETE
Backend implementation            NOT STARTED
DynamoDB implementation           NOT STARTED
API Gateway implementation        NOT STARTED
Authentication implementation     NOT STARTED
Incident API implementation       NOT STARTED
Ambulance API implementation      NOT STARTED
Hospital API implementation       NOT STARTED
Allocation engine implementation  NOT STARTED
Frontend-backend integration      NOT STARTED
End-to-end testing                NOT STARTED
AWS deployment                    NOT STARTED

16. Next Development Milestone

The next milestone is:

Backend development foundation

Implementation will proceed one verified step at a time.

17. Change Control

Changes that affect the approved architecture or API contract should be
recorded and discussed before implementation.

Examples include:

adding or removing a core entity

changing an approved endpoint

changing required API fields

changing role definitions

changing status values

replacing DynamoDB

adding a third-party API

introducing additional AWS services into the Minor

substantially changing the allocation engine

Implementation-level fixes that improve correctness, security, or
maintainability may be made without redesigning the project.

18. Documentation Relationship

The four project documents have different purposes:

| Document | Purpose |
|---|---|
| `PROJECT_MASTER_SPEC.md` | Defines what the project is |
| `ARCHITECTURE.md` | Defines how the system is architected |
| `DATABASE_AND_API_SPEC.md` | Defines the database model and API contracts |
| `DEVELOPMENT_LOG.md` | Records what was actually built and verified |

These documents should remain consistent with one another.

`DEVELOPMENT_LOG.md` should record implementation reality rather than becoming another planning document.


---

2026-11-25 --- Backend Cleanup, Auth, Manual Workflow & React Dashboard (Local Verification)

Objective

Clean up critical backend handler issues, implement lightweight HMAC token authentication and role-based access control for the two approved roles (DISPATCHER, RESOURCE_OPERATOR), implement the complete human-controlled incident coordination workflow, build the React Emergency Operations Dashboard, and verify the complete application locally before AWS deployment.

Work Completed

- Removed duplicate imports, duplicate service factories, and duplicate route blocks from `backend/src/handler.py`.
- Added CORS headers and `OPTIONS` preflight support in `backend/src/utils/response.py` and `backend/src/handler.py`.
- Removed temporary diagnostic `describe_table()` calls from `backend/src/services/allocation_service.py`.
- Added field and capacity validation (`0 <= availableBeds <= totalBeds`) to `AmbulanceService.update_ambulance` and `HospitalService.update_hospital`.
- Restricted `IncidentService.update_status` so protected workflow states cannot bypass incident verification.
- Implemented lightweight HMAC-SHA256 bearer token authentication with expiry and environment-variable secret (`AUTH_TOKEN_SECRET`) in `backend/src/utils/auth.py`.
- Implemented `CoordinationService` (`backend/src/services/coordination_service.py`) for Haversine candidate ranking, atomic manual ambulance assignment, hospital admission requests, explicit hospital accept/reject decisions (atomic bed decrement only on accept), patient transport, and incident completion (releasing the ambulance back to AVAILABLE).
- Wired all verification and manual coordination routes into `backend/src/handler.py` with proper HTTP status codes (`200`, `201`, `400`, `401`, `403`, `404`, `409`, `500`).
- Created `backend/local_server.py` (in-memory mock DynamoDB HTTP bridge to `handler.lambda_handler`) strictly for local testing and demo.
- Updated `backend/src/run_all_tests.py` to execute all 20 backend test suites, including new `backend/src/test_workflow_and_auth.py`.
- Built the complete React + Vite Emergency Operations Dashboard in `frontend/src/` (`AuthPage`, `DashboardView`, `IncidentsView`, `CoordinationView`, `AmbulancesView`, `HospitalsView`, centralized `api/client.js`, and `frontend/.env.example`).

Verification

- Backend unit & mock-based workflow test runner (`backend/src/run_all_tests.py`): **20/20 test suites PASSED** (all mock/in-memory; live AWS DynamoDB not yet tested).
- Local HTTP server smoke test against `backend/local_server.py`: PASSED (`GET /`, `POST /auth/login`, `GET /incidents`, `GET /ambulances`, `GET /hospitals`).
- Frontend lint (`npm run lint`) and production build (`npm run build`): verified in `frontend/`.

Status

LOCAL APPLICATION COMPLETE — READY FOR PHASE 5 STEP-BY-STEP AWS VERIFICATION (`ap-south-1`).


---

2026-11-25 --- Stages 1–7: Maps, Priority Queue, Role Reassignment, Atomic Dispatch, Bed Reservation, Dashboard, Locust & Documentation

Objective

Extend the verified local Minor Project with Leaflet/OpenStreetMap mapping and Google Maps external navigation, authoritative UTC timestamps and deterministic P1–P4 priority queue (IST display), reconciled two-role permissions, atomic ambulance dispatch with suitability checks, atomic multi-bed hospital reservation with duplicate-safe release and bounded history, expanded live dashboard metrics, isolated Locust local load testing, and synchronized project documentation.

Work Completed

- **Maps & External Navigation**: Installed `leaflet@^1.9.4` and `react-leaflet@^5.0.0` in `frontend/`. Added `frontend/src/utils/maps.js`, `MapHelpers.jsx`, `LocationPickerMap.jsx` (click-to-select, draggable marker, Browser Geolocation API, manual coordinate sync, Pune default center), `IncidentLocationMap.jsx`, `CoordinationMap.jsx` (color-coded Incident/Available Ambulance/Assigned Ambulance/Hospital markers), and external Google Maps driving directions buttons ("Navigate to Incident" and "Navigate to Hospital").
- **Stage 1 (Timestamps & Priority Queue)**: Updated `constants.py`, `models/incident.py`, `incident_repository.py`, `incident_service.py`, `handler.py`, `frontend/src/utils/time.js`, and `PriorityQueueView.jsx`. Backend generates all authoritative UTC ISO-8601 timestamps and derives `P1–P4` from severity; `GET /incidents/queue` provides deterministic sorting (`P1→P4`, oldest `createdAt` first), IST date filtering, and configurable waiting thresholds (`5m/15m/30m/60m`). Added `test_priority_queue.py`.
- **Stage 2 (Roles & Inspection)**: Enforced reconciled two-role RBAC in `handler.py` (`DISPATCHER` reports incidents & monitors; `RESOURCE_OPERATOR` inspects, verifies/rejects, dispatches, reserves beds, records transport & completes). Updated `IncidentsView.jsx`, `CoordinationView.jsx`, `AuthPage.jsx`, and `test_workflow_and_auth.py`.
- **Stage 3 (Atomic Ambulance Dispatch)**: Enforced required equipment suitability, valid coordinates, unassigned status, backend `ambulanceAssignedAt`, and atomic 2-item DynamoDB transaction in `coordination_service.py`. Added 5 multi-threaded concurrency scenarios in `test_ambulance_dispatch.py`.
- **Stage 4 (Hospital Bed Reservation)**: Implemented embedded `bedReservation` (`RESERVED`/`CONFIRMED`/`REJECTED`/`RELEASED`) and bounded `reservationHistory` (capped at `MAX_RESERVATION_HISTORY = 20`) inside `EmergencyIncidents` (preserving 4 DynamoDB tables). Added atomic reservation (`default = peopleAffected`, adjustable), confirm without second decrement, atomic duplicate-safe release on rejection or `POST /incidents/{id}/cancel-reservation`, and `test_hospital_reservation.py`.
- **Stage 5 (Transport, Completion & Dashboard)**: Recorded backend `transportedAt` and `completedAt`, atomic ambulance release on completion (preserving hospital reservation and bed count), `GET /dashboard/summary` with live KPIs, `averageResponseTimeSeconds` (`"Unavailable"` when insufficient data), and IST activity timeline. Added "Navigate to Hospital" and `test_transport_completion_dashboard.py`.
- **Stage 6 (Locust Load Testing)**: Installed `locust==2.47.0` in `backend/.venv` only (excluded from Lambda `requirements.txt`). Created `backend/load_tests/` (`locustfile.py`, `config.example.env`, `README.md`, `PERFORMANCE_REPORT.md`) and executed progressive local mock-server tests (10, 25, 50, 100, 200 concurrent users; 6,040 total requests, 0 HTTP 500 errors, 2.78% failure rate at 200 users due to Windows `ThreadingHTTPServer` TCP backlog `10061` + resulting `401` on unauthenticated retries).
- **Stage 7 (Documentation)**: Synchronized `README.md`, `docs/PROJECT_MASTER_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE_AND_API_SPEC.md`, and `docs/DEVELOPMENT_LOG.md`.

Verification

- Backend test suite (`.\backend\.venv\Scripts\python.exe backend\src\run_all_tests.py`): **24 / 24 test suites PASSED** (all unit/mock/in-memory; live AWS DynamoDB not yet verified).
- Frontend lint (`npm run lint`) and production build (`npm run build`): **PASSED**.
- Local HTTP smoke tests against `backend/local_server.py`: **PASSED**.
- Locust progressive load tests (10 → 200 users) against `backend/local_server.py`: **COMPLETED** (CSVs saved in `backend/load_tests/results/`).

Status

LOCAL MINOR PROJECT COMPLETE AND VERIFIED — READY FOR STEP-BY-STEP AWS DEPLOYMENT & LIVE VERIFICATION (`ap-south-1`).


---

2026-11-25 --- Stages 8A–8D: Ownership & Privacy, Operator Two-Step OTP, Registration Lockdown & Completed Incident Archiving

Objective

Harden authentication and data privacy for the two-role model (Dispatcher ownership isolation, Resource Operator two-step OTP, public registration lockdown) and add completed incident archiving with a dedicated archived-incidents view.

Work Completed

- **Stage 8B (Ownership & Privacy)**: Added backend-stamped `createdBy`/`createdByUsername`, Dispatcher response sanitizer (`_sanitize_incident_for_dispatcher`), `404` hiding for cross-user/legacy incidents, `RESOURCE_OPERATOR`-only restriction (`403` for Dispatchers) on `/incidents/queue`, `/dashboard/summary`, `/ambulances`, `/hospitals`, role-isolated Dispatcher UI (**My Reported Incidents**), and `test_ownership_and_privacy.py`.
- **Stage 8C (Operator OTP & Registration Lockdown)**: Added `ACCESS` vs `OTP_CHALLENGE` token purposes in `utils/auth.py`, atomic conditional OTP methods on `UserRepository`, 6-digit `secrets` OTP + 5-min expiry + 5-attempt lockout + single-use consumption in `UserService`, `POST /auth/verify-otp`, `LOCAL_OTP_CONSOLE=true` terminal delivery in `local_server.py`, public `POST /auth/register` lockdown (`DISPATCHER` only, `403` for `RESOURCE_OPERATOR`), two-step OTP UI in `AuthPage.jsx`, and `test_operator_otp_auth.py`.
- **Stage 8D (Completed Incident Archiving & Docs Sync)**: Added `isArchived`, `archivedAt`, `archivedBy` on `EmergencyIncidents`, atomic conditional `POST /incidents/{id}/archive` (only `COMPLETED`, status preserved), `GET /incidents/archived` (newest first, operator-only), excluded archived items from operator active list & priority queue while keeping Dispatcher's own archived items visible with an `ARCHIVED` badge, added `ArchivedIncidentsView.jsx`, updated `locustfile.py` for Stage 8 role permissions, added `test_incident_archiving.py`, and synchronized all project docs.

Verification

- Backend test suite (`backend/src/run_all_tests.py`): **27 / 27 test suites PASSED** (local mock/in-memory; live AWS not yet verified).
- Frontend lint (`npm run lint`) and production build (`npm run build`): **PASSED**.
- Local HTTP smoke tests (Dispatcher ownership, Operator 2-step OTP, archiving & archived list): **PASSED**.

Status

LOCAL MINOR PROJECT COMPLETE WITH STAGE 8 SECURITY & ARCHIVING — READY FOR PHASE 5 AWS DEPLOYMENT (`ap-south-1`).
