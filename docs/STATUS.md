# NexStream implementation status

Updated: 2026-11-22

| Workstream | Status | Evidence |
|---|---|---|
| Six independent local Git repositories | VERIFIED | each repository has local `main` metadata; no remotes changed |
| Canonical system documentation | VERIFIED | this `docs/` tree and `DOCUMENTATION_OWNERSHIP.md` |
| Sprint 01 Protobuf contracts | VERIFIED | `nexstream-contracts/tests/results/2026-11-06-sprint-01/` |
| Sprint 01 Debug tests | VERIFIED | 6 PASS, 0 FAIL |
| Sprint 01 ASan/UBSan tests | VERIFIED | 2/2 CTest executables PASS |
| Sprint 02 TCP Gateway Core | VERIFIED | `nexstream-ingest/tests/results/2026-11-11-sprint-02/` |
| Sprint 02 tests | VERIFIED | 11 PASS, 0 FAIL, 0 BLOCKED, 0 NOT RUN |
| Sprint 03 TCP Publisher Transport | VERIFIED | `nexstream-publisher/tests/results/2026-11-13-sprint-03/` |
| Sprint 03 tests | VERIFIED | 10 PASS, 0 FAIL, 0 BLOCKED, 0 NOT RUN |
| Sprint 04 Kafka async producer | VERIFIED | `nexstream-ingest/tests/results/2026-11-14-sprint-04/` |
| Sprint 04 tests | VERIFIED | 12 PASS, 0 FAIL, 0 BLOCKED, 0 NOT RUN |
| Real Kafka-compatible delivery | VERIFIED LOCAL | Redpanda delivery report, consume evidence, outage/restart scenario |
| Sprint 05 PostgreSQL authentication | VERIFIED LOCAL | real PostgreSQL integration and outage/restart |
| Sprint 05 HAProxy TLS termination | VERIFIED LOCAL | TLS 1.3 chain/hostname positive and negative tests |
| Sprint 05 tests | PARTIAL | 16 PASS, 0 FAIL, 1 BLOCKED, 1 NOT RUN |
| Sprint 06 durable Linux Agent | VERIFIED LOCAL | TLS/SQLite/collector/retry and full local pipeline |
| Sprint 06 tests | PARTIAL | 17 PASS, 0 FAIL, 0 BLOCKED, 1 NOT RUN |
| External schema registry/buf gate | BLOCKED | dependency/baseline unavailable |
| Sprint 07 analytics pipeline | PARTIAL, VERIFIED LOCAL CORE | ClickHouse, Query, Processor and Agent E2E; reports/SPRINT-07-REPORT.md |
| Sprint 07 test inventory | PARTIAL | 22 PASS, 0 FAIL, 0 BLOCKED, 2 NOT RUN |
| Sprint 07 hardening | VERIFIED LOCAL, BOUNDED RECOVERY | reports/SPRINT-07-HARDENING-REPORT.md; ADR-017 |
| Hardening acceptance / supplementary tests | VERIFIED / NOT RUN | 31 PASS, 0 FAIL, 0 BLOCKED; 1 optional TSan NOT RUN |
| Long-history/fleet recovery | P1 OPERATIONAL LIMIT | retained offset-zero prefix, 100000-offset ceiling; durable partition snapshots need review |
| Sprint 08 and later | NOT STARTED | outside scope |
| Benchmarks | NOT RUN | no performance claim made |
| Public deployment | NOT RUN | not authorized |

See `reports/SPRINT-01-REPORT.md` for commands, defects, decisions, and file inventory.
