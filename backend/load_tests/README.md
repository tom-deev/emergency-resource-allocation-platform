# Load Testing Suite (Locust)

This directory contains an isolated Locust load-testing suite for the **Emergency Response & Resource Allocation Platform**.

> **IMPORTANT — Local Mock vs. AWS:**
> Running these load tests against `backend/local_server.py` measures the throughput and latency of the **local Python `ThreadingHTTPServer` + in-memory mock DynamoDB** only. It does **not** establish AWS Lambda concurrency, Amazon API Gateway throughput, or Amazon DynamoDB production capacity. Never run aggressive load tests against production AWS resources without separate approval.

## Setup (Development Environment Only)

Locust is installed only in `backend/.venv` and is **not** included in `backend/requirements.txt` or the AWS Lambda deployment package.

```powershell
.\backend\.venv\Scripts\pip.exe install locust
```

## Safe Test Data Policy

- Dedicated load-test accounts (`lt_dispatcher`, `lt_operator`) are registered automatically on test start without modifying shared demo users.
- By default (`LOAD_TEST_ENABLE_MUTATIONS=false`), all tasks are **read-only** (`POST /auth/login`, `GET /dashboard/summary`, `GET /incidents/queue`, `GET /incidents/{id}`, `GET /incidents/{id}/candidates`, `GET /ambulances`, `GET /hospitals`).
- When `LOAD_TEST_ENABLE_MUTATIONS=true` is explicitly opted in:
  - Only clearly tagged `[LOAD_TEST]` incidents are created and reviewed/verified.
  - Shared demo incidents, ambulance assignments, and hospital bed counts are **never** mutated.

## Running Headless Progressive Load Tests (PowerShell)

1. Start a fresh local simulated API server in Terminal 1:
   ```powershell
   .\backend\.venv\Scripts\python.exe backend\local_server.py
   ```
2. Run progressive load levels in Terminal 2 from the repository root:
   ```powershell
   # Level 1: 10 users
   .\backend\.venv\Scripts\locust.exe -f backend\load_tests\locustfile.py --host http://127.0.0.1:8000 --headless -u 10 -r 5 -t 15s --csv backend\load_tests\results\level1_10u

   # Level 2: 25 users
   .\backend\.venv\Scripts\locust.exe -f backend\load_tests\locustfile.py --host http://127.0.0.1:8000 --headless -u 25 -r 10 -t 15s --csv backend\load_tests\results\level2_25u

   # Level 3: 50 users
   .\backend\.venv\Scripts\locust.exe -f backend\load_tests\locustfile.py --host http://127.0.0.1:8000 --headless -u 50 -r 15 -t 15s --csv backend\load_tests\results\level3_50u

   # Level 4: 100 users
   .\backend\.venv\Scripts\locust.exe -f backend\load_tests\locustfile.py --host http://127.0.0.1:8000 --headless -u 100 -r 25 -t 15s --csv backend\load_tests\results\level4_100u

   # Level 5: 200 users (only if Levels 1-4 remain stable)
   .\backend\.venv\Scripts\locust.exe -f backend\load_tests\locustfile.py --host http://127.0.0.1:8000 --headless -u 200 -r 40 -t 15s --csv backend\load_tests\results\level5_200u
   ```

See [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md) for recorded benchmark results and analysis.
