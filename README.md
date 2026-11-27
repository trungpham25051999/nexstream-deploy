# nexstream-deploy

[![CI](https://github.com/trungpham25051999/nexstream-deploy/actions/workflows/ci.yml/badge.svg)](https://github.com/trungpham25051999/nexstream-deploy/actions/workflows/ci.yml) ![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

NexStream architecture, deployment and operational repository. Six local repositories have been
initialized; Sprint 01 contracts, Sprint 02 Gateway Core, Sprint 03 Publisher Transport and Sprint
04 asynchronous Kafka delivery and Sprint 05 registry authentication/TLS termination are
implemented and tested locally. Sprint 06 Agent and Sprint 07 analytics extend that path;
see current status and per-sprint reports for verified behavior and limitations.

Read [`docs/README.md`](docs/README.md) first. All design-only capabilities remain proposed until supported by test evidence.

Current implementation status: [`docs/STATUS.md`](docs/STATUS.md). Sprint report:
[`docs/reports/SPRINT-01-REPORT.md`](docs/reports/SPRINT-01-REPORT.md).
Sprint 02: [`docs/reports/SPRINT-02-REPORT.md`](docs/reports/SPRINT-02-REPORT.md).
Sprint 03: [`docs/reports/SPRINT-03-REPORT.md`](docs/reports/SPRINT-03-REPORT.md).
Sprint 04: [`docs/reports/SPRINT-04-REPORT.md`](docs/reports/SPRINT-04-REPORT.md).
Sprint 05: [`docs/reports/SPRINT-05-REPORT.md`](docs/reports/SPRINT-05-REPORT.md).
Sprint 06: [`docs/reports/SPRINT-06-REPORT.md`](docs/reports/SPRINT-06-REPORT.md).
Sprint 07: [`docs/reports/SPRINT-07-REPORT.md`](docs/reports/SPRINT-07-REPORT.md).

Sprint 07 adds local Kafka Engine/MV/MergeTree ingestion, a bounded C++20 Query API, and a
C++20 threshold Processor with real broker delivery/offset handling and local restart checkpoint.
Real Agent TLS → PostgreSQL-authenticated Gateway → Kafka → ClickHouse → Query passed.
The complete Compose topology also passed using locally downloaded Compose v2.29.7.
See [`docs/analytics/SPRINT-07-INGESTION.md`](docs/analytics/SPRINT-07-INGESTION.md),
[`tests/TEST_CASES.md`](tests/TEST_CASES.md) and the Sprint 07 report for incomplete checks.

Current review: [`SPRINT-07-HARDENING-REPORT.md`](docs/reports/SPRINT-07-HARDENING-REPORT.md).
Thirty-one required cases passed; supplementary TSan is NOT RUN. Multi-owner Kafka recovery and short
fixture TTL have real evidence. ADR-017 documents the remaining bounded-history P1 operational limit.
