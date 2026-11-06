# NexStream — Requirements Baseline v1.0

**Status:** Accepted as project requirements baseline (design targets, not measured performance)  
**Date:** 2026-11-06  
**Positioning:** C++ Systems + Distributed Systems  
**Project:** High-Performance Distributed Telemetry Ingestion Platform

## 1. Project objective

Design, implement, benchmark, and explain a C++20/Linux ingestion pipeline that receives short-lived TCP telemetry batches, decodes framed Protobuf messages, asynchronously publishes individual validated records to Kafka/Redpanda, and exposes persisted data through ClickHouse. Prioritize correctness, bounded resource usage, failure handling, measurable performance, and reproducible engineering evidence over unnecessary technology breadth.

## 2. Success goals

| ID | Goal | Verification |
|---|---|---|
| G01 | Nonblocking TCP ingestion | Reproducible TCP batch integration tests |
| G02 | Bounded resource consumption | Configured limits, overload tests, RSS/queue measurement |
| G03 | Reliable delivery contract | Kafka delivery reports before success ACK, retry tests |
| G04 | Horizontal Gateway scaling | Two replicas tested with independent connections |
| G05 | Analytics ingestion | Kafka → ClickHouse records verifiable by stable message IDs |
| G06 | Observability and profiling | CPU, RSS, throughput, p50/p95/p99, queue measurements |
| G07 | Maintainable C++ code | Clean architecture boundaries, CI, tests, ADRs |

G01–G03 and basic evidence for G05/G06/G07 take priority for the MVP.

## 3. Architecture baseline

- One **short-lived TCP connection carries one batch** of multiple Protobuf telemetry messages.
- Device sends `BatchStart`, multiple framed telemetry messages, then `BatchEnd` (exact wire schema pending).
- Gateway **streams each valid complete frame** into an async Kafka producer without waiting for the entire batch.
- Gateway runs **A1 baseline**: nonblocking `epoll` reactor; framing, Protobuf decoding, validation and async producer enqueue in reactor thread. No dedicated decode worker pool initially.
- Aggregate `BatchAck` is produced only after `BatchEnd` and after all message delivery outcomes for that batch are resolved under the agreed deadline policy.
- ACK success means Kafka delivery confirmation under configured broker policy, **not ClickHouse persistence**.
- Kafka topic `telemetry.events.v1` is keyed by `device_id`; ClickHouse Kafka Engine/Materialized View ingests records; independent processor may consume the same topic.
- End-to-end exactly-once and all-or-nothing batch atomicity are **not** project guarantees.
- Kafka producer batching may occur internally even though Gateway calls asynchronous produce per record.

## 4. Functional requirements

| ID | Requirement | Primary repository |
|---|---|---|
| FR-01 | Define versioned Protobuf and framed TCP batch contract | nexstream-contracts |
| FR-02 | Generate telemetry, connect, send batch, receive aggregate ACK, close | nexstream-publisher |
| FR-03 | Nonblocking accept/read/write and partial frame assembly | nexstream-ingest |
| FR-04 | Decode, validate, normalize and asynchronously publish individual messages | nexstream-ingest |
| FR-05 | Correlate delivery results, aggregate per-message outcomes, send BatchAck | nexstream-ingest |
| FR-06 | Timeouts, bounded buffers, overload/backpressure and graceful shutdown | nexstream-ingest |
| FR-07 | Retry unconfirmed messages with stable identity and document duplicates | publisher, ingest, downstream |
| FR-08 | Provision Kafka/Redpanda, ClickHouse Kafka Engine/MV/storage schema | nexstream-deploy |
| FR-09 | Read persisted telemetry using safe HTTP endpoints | nexstream-query (post-MVP) |
| FR-10 | Compute derived analytics/alerts from Kafka | nexstream-processor (post-MVP) |
| FR-11 | Load generation, integration testing and performance reporting | publisher, deploy, ingest |

## 5. Proposed performance goals (not yet achieved)

**Canonical workload:** 50 messages per TCP batch, average payload 512 B. Reproducible hardware/software configuration required.

| Metric | MVP | V1 target | Stretch |
|---|---:|---:|---:|
| Ingest throughput | 1,000 msg/s | 10,000 msg/s | 50,000 msg/s |
| TCP session start rate | 20/s | 200/s | 1,000/s |
| Concurrent established TCP sessions (separate burst test) | 100 | 1,000 | 5,000 |
| Batch size in canonical test | 50 | 50 | 50 |
| Average Protobuf payload | 512 B | 512 B | 512 B |
| Gateway BatchAck p99 | Establish baseline | <300 ms in healthy-Kafka canonical load | Report measured result |
| CPU | Measure | Stable within declared CPU quota | Profile |
| RSS | Measure | No unbounded growth; report configured budgets and observed peak | Profile |

**Latency definitions:** Primary Gateway BatchAck p99 is elapsed time from the Gateway's receipt of the full `BatchEnd` frame to enqueueing/writing the final ACK bytes to its socket under a healthy broker. This is **not** device-observed delivery and excludes TCP connection setup and client upload time. Also report Publisher end-to-end time from connect initiation until receipt of full ACK. For accuracy, distinguish ACK queued versus fully written to the kernel send buffer in instrumentation.

**Benchmark method:** At least 10-minute sustained load for each stable tier, multiple repeated runs, warm-up, same schema/configuration and hardware. Report offered rate, success rate, Kafka delivery errors, CPU/core, RSS, producer queue occupancy, p50/p95/p99 and environment. Different broker replication/durability configurations must not be compared as if equivalent.

Performance targets are hypotheses for evaluation, **not prerequisites for claiming functional MVP success**. Any miss must include observed bottleneck and evidence.

## 6. Non-functional requirements

| ID | Constraint | Acceptance evidence |
|---|---|---|
| NFR-01 | Reactor must not synchronously wait for Kafka/network persistence | Code review and stalled-broker test |
| NFR-02 | Frame, session, pending bytes, output buffers and Kafka queue bounded | Flood tests and metrics |
| NFR-03 | At-least-once-oriented retry with stable message identity, conditional on retained client data | ACK-loss/reconnect tests |
| NFR-04 | Never report successful Kafka delivery before confirmation | Delivery injection tests |
| NFR-05 | No callbacks use stale TCP connections or reused file descriptors | Disconnect/race tests, sanitizers as applicable |
| NFR-06 | TCP disconnect and Kafka outage must not crash Gateway | Fault injection |
| NFR-07 | Bounded graceful-shutdown drain; unresolved outcomes explicitly reported | Shutdown integration test |
| NFR-08 | Logs/metrics provide delivery, queue, latency and errors without high-cardinality device labels | Dashboard/metrics checks |
| NFR-09 | Unit and integration suites repeatable in CI | CI evidence |
| NFR-10 | Multiple independent Gateway replicas supported | Replicated deployment test |

**Delivery caveat:** At-least-once requires client persistence/retry and eventual broker service; no unconditional no-loss claim. Duplicates may enter Kafka/ClickHouse. Producer-level idempotence does not deduplicate application retries.

## 7. MVP scope

**Included:** `nexstream-contracts`, `nexstream-publisher`, `nexstream-ingest`, and minimal `nexstream-deploy` (single-node local Redpanda + ClickHouse). End-to-end single-batch pipeline; schema tests; partial read/frame tests; ACK behavior; failures; bounded memory; baseline performance capture.

**Deferred:** `nexstream-processor`, `nexstream-query`, Kubernetes, production HA/multi-DC, full security platform, service mesh, custom message broker, and lock-free micro-optimizations. Basic SQL query is sufficient to verify ClickHouse MVP persistence.

## 8. Definition of Done

### Milestone M1 — Functional MVP
- [ ] C++20 builds on Linux with documented commands.
- [ ] One 50-message batch goes Publisher → Gateway → Kafka → ClickHouse.
- [ ] Aggregate ACK correctly reflects Kafka delivery outcomes.
- [ ] Partial frame, oversize, invalid Protobuf, incomplete batch, timeout and disconnect cases tested.
- [ ] Kafka outage/queue full handled without false success ACK or crash.
- [ ] Basic ASan/UBSan and leak checks used where practicable; exact results documented.
- [ ] Reproducible local runbook with exact versions and observed test output.

### Milestone M2 — Performance & Reliability
- [ ] 10,000 msg/s target tested with fair baseline methodology (result may be pass/fail with explanation).
- [ ] Measured p50/p95/p99, offered/success rates, CPU, RSS and queue depth.
- [ ] Backpressure, ACK-loss/retry, duplicate and graceful shutdown behavior demonstrated.
- [ ] Two Gateway replicas integrated and capacity comparison reported.
- [ ] Profiling report plus at least one measured before/after improvement.

### Milestone M3 — Interview-Ready Portfolio
- [ ] Processor and Query API implemented with documented scope.
- [ ] C4, ADRs, failure matrix, coding standards and operational runbook current.
- [ ] CI builds, static checks and tests for changed modules.
- [ ] Honest performance report including limitations and reproducibility artifacts.
- [ ] Can explain TCP lifetime, epoll fairness, Kafka callbacks, ACK contract, ordering and dedup tradeoffs.

## 9. Open architectural decisions — not approved by this baseline

1. Exact Protobuf envelope and versioning, frame header and batch error codes.
2. Aggregate ACK encoding, partial success/unknown representation and retry granularity.
3. Deduplication mechanism in Analytics/ClickHouse and query correctness.
4. Reactor readiness mode (LT vs ET), fairness and callback polling implementation.
5. Per-session/global memory limits, watermarks, producer queue configuration and deadlines.
6. Security/TLS/auth beyond local MVP.
7. Whether to add Multi-Reactor or worker pool based on measured limitations.

No implementation should silently treat these as already decided. Record resolutions in versioned ADRs.

## 10. Document governance

- **Owner of system-wide baseline:** `nexstream-deploy/docs/requirements/REQUIREMENTS_BASELINE_v1.0.md`.
- **Changes:** Revision + rationale + impact assessment; significant changes require ADR and updated tests.
- **Source of truth:** wire schema in tagged `nexstream-contracts`; service-specific implementation details in each repo.
- **Status tracking:** mark each requirement `not started`, `in progress`, `verified`, or `blocked`, and cite concrete command/test/benchmark evidence.
