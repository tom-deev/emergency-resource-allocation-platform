# Local Load Testing Performance Report (Locust)

> **CRITICAL DISCLAIMER — LOCAL MOCK SERVER ONLY**
>
> All measurements in this report were captured against the **local Python `ThreadingHTTPServer` + in-memory mock DynamoDB** (`backend/local_server.py`) on a single developer laptop.
>
> These results do **NOT** measure or guarantee:
> - AWS Lambda concurrency or cold-start behavior
> - Amazon API Gateway throughput or throttling limits
> - Amazon DynamoDB read/write capacity units (RCU/WCU) or transaction latency
> - Production emergency-services scalability
>
> Actual AWS load testing requires a separately approved plan in a controlled AWS environment.

---

## 1. Test Environment

| Property | Value |
|---|---|
| Operating System | Microsoft Windows 11 Pro |
| CPU | AMD Athlon Silver 3050U (2 logical cores) |
| RAM | 5.94 GB |
| Python | 3.14.4 (`backend\.venv`) |
| Locust | 2.47.0 (dev-only; excluded from Lambda `requirements.txt`) |
| Target URL | `http://127.0.0.1:8000` (`backend/local_server.py`) |
| Test Mode | Safe Read-Only (`LOAD_TEST_ENABLE_MUTATIONS=false`) with dedicated load-test accounts (`lt_dispatcher`, `lt_operator`) |
| Duration per Level | 15 seconds (progressive ramp-up, 2s cooldown between levels) |

### Mock Database Limitations
- `backend/local_server.py` uses a single-process Python `ThreadingHTTPServer` (default TCP listen backlog `request_queue_size = 5`) and a single `threading.RLock()` around in-memory dictionaries.
- Both Locust (load generator) and the target API server competed for the same 2 logical CPU cores on this machine.
- In-memory reads avoid real network/DynamoDB I/O, while Python GIL + TCP backlog saturation create local-only bottlenecks at high concurrency.

---

## 2. Progressive Load Test Summary (Actual CSV Results)

| Level | Concurrent Users | Spawn Rate | Duration | Total Reqs | Success | Failed | Failure % | RPS | Avg (ms) | Median (ms) | p95 (ms) | p99 (ms) | Max (ms) | CSV Artifact |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Level 1 | 10 | 5/s | 15s | 242 | 242 | 0 | 0.00% | 18.97 | 13.0 | 9 | 32 | 89 | 97.0 | `results/level1_10u_stats.csv` |
| Level 2 | 25 | 10/s | 15s | 517 | 517 | 0 | 0.00% | 39.81 | 44.5 | 15 | 180 | 530 | 1059.8 | `results/level2_25u_stats.csv` |
| Level 3 | 50 | 15/s | 15s | 916 | 914 | 2 | 0.22% | 70.92 | 126.1 | 14 | 660 | 1600 | 2231.9 | `results/level3_50u_stats.csv` |
| Level 4 | 100 | 25/s | 15s | 1,814 | 1,814 | 0 | 0.00% | 141.73 | 101.0 | 19 | 550 | 1100 | 1642.4 | `results/level4_100u_stats.csv` |
| Level 5 | 200 | 40/s | 15s | 2,551 | 2,480 | 71 | 2.78% | 192.36 | 290.9 | 110 | 1200 | 2100 | 2173.3 | `results/level5_200u_stats.csv` |

**Total across all 5 levels**: 6,040 requests, **0 HTTP 500 Internal Server Errors**.

---

## 3. Endpoint Breakdown at Peak Load (Level 5 — 200 Users)

| Endpoint | Requests | Failures | Median (ms) | Avg (ms) | p95 (ms) | p99 (ms) | Max (ms) | RPS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `GET /incidents/queue` | 734 | 24 | 110 | 260.3 | 1100 | 1700 | 2136.6 | 55.35 |
| `GET /dashboard/summary` | 509 | 16 | 110 | 256.6 | 1100 | 2000 | 2131.6 | 38.38 |
| `GET /ambulances` | 329 | 14 | 110 | 267.5 | 1100 | 1900 | 2144.0 | 24.81 |
| `GET /hospitals` | 308 | 8 | 110 | 295.0 | 1100 | 2100 | 2135.9 | 23.22 |
| `GET /incidents/{id}` | 274 | 0 | 110 | 234.9 | 1000 | 1700 | 2070.1 | 20.66 |
| `POST /auth/login` | 200 | 8 | 230 | 609.5 | 2100 | 2100 | 2173.3 | 15.08 |
| `GET /incidents/{id}/candidates` | 197 | 1 | 110 | 280.2 | 1100 | 2000 | 2111.2 | 14.85 |

---

## 4. Failure Analysis & Bottlenecks

### Observed Failures
- **Level 3 (50 users)**: 2 failures (`0.22%`) — both were `ConnectionRefusedError(10061)` on `GET /hospitals` and `GET /incidents/{id}/candidates` during initial burst.
- **Level 5 (200 users)**: 71 failures (`2.78%`):
  - **15 TCP socket refusals** (`ConnectionRefusedError(10061)` / `HTTP 0`, including 8 on `POST /auth/login` during the 40 users/sec ramp-up).
  - **56 `HTTP 401 Unauthorized`** responses caused directly by the 8 virtual users whose initial login connection was refused, leaving them without a Bearer token for subsequent requests. (This confirms route-level authentication remained strictly enforced under load.)
- **Zero `HTTP 500` errors** occurred at any load level.

### Root Causes & Recommendations
1. **Local Dev Server TCP Backlog & GIL Contention (Local-only)**: Python's `ThreadingHTTPServer` defaults to `request_queue_size = 5` and shares 2 CPU cores with Locust. In AWS deployment, Amazon API Gateway + AWS Lambda handle connection pooling and horizontal concurrency automatically.
2. **Full Table Scans on Read Endpoints (`GET /incidents/queue`, `GET /dashboard/summary`, `GET /incidents/{id}/candidates`)**:
   - Currently each read calls `table.scan()`, which is appropriate for small Minor Project academic datasets.
   - **Major Project Recommendation**: Add DynamoDB Global Secondary Indexes (e.g., `status-createdAt-index` or `severity-createdAt-index`), pagination, and short-TTL caching for `/dashboard/summary` before scaling to large datasets.
3. **Login Lookup Uses Table Scan (`UserRepository.find_by_username`)**:
   - At 200 concurrent logins, `POST /auth/login` had the highest average latency (`609.5 ms`).
   - **Major Project Recommendation**: Add a DynamoDB GSI on `username` (or migrate to Amazon Cognito as planned for the Major Project).


---

## 5. Stage 8 Alignment Note (2026-11-25)

The 5-level benchmark results above were captured in Stage 6 prior to Stage 8B/8C role isolation and two-step operator OTP authentication. In Stage 8D, `backend/load_tests/locustfile.py` was updated so that:
- `DispatcherUser` calls only Dispatcher-permitted ownership-scoped endpoints (`POST /auth/login`, `GET /incidents`, `GET /incidents/{id}`, and opt-in `POST /incidents [load-test]`).
- `ResourceOperatorUser` uses a pre-authenticated `LOAD_TEST_OPERATOR_TOKEN` (obtained via the two-step OTP login flow) and includes `GET /incidents/archived`.
