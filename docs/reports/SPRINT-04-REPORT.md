# Sprint 04 Report — Kafka Async Producer & Delivery Tracking

Date: 2026-11-14  
Scope: Sprint 04 only

## Outcome

`nexstream-ingest` now uses a bounded asynchronous librdkafka producer. Kafka is never polled or
flushed on the epoll Reactor thread. Delivery callbacks publish correlation-only completion values
to a bounded queue and wake the Reactor with `eventfd`. The Gateway sends `BatchAck.SUCCESS` only
after every record receives a successful Kafka delivery report. Timeout/uncertainty remains
`UNKNOWN`; overload is rejected without unbounded retries or buffering.

Real local Redpanda integration succeeded, including Publisher → Gateway → broker delivery,
consumption of the stored key/value, broker outage, and restart recovery. Mock results are reported
separately and are not presented as Kafka confirmation.

## Implemented components

- Versioned `nexstream_contracts` 0.1.0 CMake install/export package and downstream consumer test.
- Shared async producer port with correlation ID, bounded event payload and explicit enqueue result.
- librdkafka C adapter with `acks=all`, idempotence, bounded pending records/bytes, finite retries,
  message timeout, `host_id` key and dedicated poll thread.
- Bounded thread-safe completion queue and nonblocking `eventfd` Reactor notification.
- Batch delivery tracker supporting out-of-order completion, partial results, UNKNOWN and
  RETRY_LATER; no raw `TcpConnection*` crosses callback threads.
- Stable connection token/generation lookup for disconnect and fd-reuse safety.
- Queue-full admission control and immediate rejection.
- Mock, unavailable-broker, real-broker, restart and Publisher/Gateway integration coverage.

## Files created or modified

### `nexstream-contracts`

- Modified: `CMakeLists.txt`, `README.md`, `docs/STATUS.md`
- Created: `cmake/nexstream_contractsConfig.cmake.in`,
  `tests/package_consumer/{CMakeLists.txt,main.cpp}`

### `nexstream-ingest`

- Modified: `CMakeLists.txt`, `README.md`, `docs/STATUS.md`, `tests/TEST_CASES.md`,
  `tests/results/README.md`, `src/bootstrap/main.cpp`,
  `src/application/protocol_session.cpp`, `src/infrastructure/{tcp_connection,epoll_reactor}.cpp`,
  and corresponding headers/tests
- Created: `include/nexstream/ingest/application/event_producer.hpp`,
  `include/nexstream/ingest/infrastructure/{completion_channel,kafka_producer}.hpp`,
  `src/infrastructure/{completion_channel,kafka_producer}.cpp`, `tests/mock_producer.hpp`,
  `tests/unit/delivery_tracking_tests.cpp`,
  `tests/integration/{kafka_adapter_tests,kafka_real_integration_tests}.cpp`, and
  `tests/results/2026-11-14-sprint-04/*`

### Other repositories/documentation

- Modified Publisher CMake/README/status to consume the installed contracts package.
- Modified deploy `docs/STATUS.md`, `docs/15-project-status.md`.
- Created this report.

No `.proto`, golden vector, ADR, Git remote, Sprint 05 component, TLS, PostgreSQL or public
deployment was changed.

## Build and test commands

The exact local prefixes and command transcript are in
`nexstream-ingest/tests/results/2026-11-14-sprint-04/commands.txt`. Principal commands were:

```sh
cmake -S nexstream-contracts -B nexstream-contracts/build-s04 -DBUILD_TESTING=ON \
  -DCMAKE_INSTALL_PREFIX=.../.local/nexstream-contracts-0.1.0-package
cmake --build nexstream-contracts/build-s04 --parallel 2
ctest --test-dir nexstream-contracts/build-s04 --output-on-failure
cmake --install nexstream-contracts/build-s04

cmake -S nexstream-ingest -B nexstream-ingest/build-s04 -DCMAKE_BUILD_TYPE=Debug \
  -DBUILD_TESTING=ON -DCMAKE_PREFIX_PATH=.../.local/nexstream-contracts-0.1.0-package \
  -DRDKAFKA_ROOT=.../.deps/librdkafka-2.0.2
cmake --build nexstream-ingest/build-s04 --parallel 2
ctest --test-dir nexstream-ingest/build-s04 --output-on-failure
```

Equivalent Release and `-fsanitize=address,undefined` builds were executed. Redpanda v24.3.18 was
started locally on port 19092, stopped between Publisher calls, restarted, then removed.

## Actual results

| Classification | Count | Scope |
|---|---:|---|
| PASS | 12 | TC-KAFKA-001 through TC-KAFKA-012 |
| FAIL | 0 | final runs |
| BLOCKED | 0 | Sprint 04 test cases |
| NOT RUN | 0 | Sprint 04 test cases |

- Debug: 6/6; Release: 6/6; ASan/UBSan: 6/6 CTest executables passed.
- Contracts: 2/2, including unchanged golden vectors; package consumer passed.
- Publisher regression: 4/4 passed.
- Real Redpanda test passed. The consumed Gateway record used topic `telemetry.events.v1`, key
  `publisher-cli-host`, and a v1 JSON value containing the original host/message identity.
- Broker stopped: Publisher returned exit 3, `delivery unresolved or retryable`.
- Broker restarted: Publisher returned exit 0, `delivery success`.
- TLS, PostgreSQL and performance benchmark: NOT RUN as out of scope; not included in the test-case
  count.

## Errors found and fixed

1. The first package install rule also copied generated `.pb.cc` into the include tree. Install
   matching was narrowed to headers and package consumption was rerun.
2. A late delivery completion initially lacked a targeted disconnect/timeout regression. TCP
   integration coverage was extended to prove closed/stale connection tokens are ignored safely.
3. One evidence command used the wrong package-consumer executable path. The correct generated path
   was run successfully; this was a command typo, not a product defect.

No expected result was weakened and no failing test was skipped.

## Technical decisions

- The application owns an `IAsyncEventProducer`; librdkafka stays behind an infrastructure adapter,
  preserving Clean Architecture and allowing deterministic tests.
- Callback opaque data owns only correlation and byte accounting. It never stores a connection
  pointer, preventing cross-thread lifetime coupling.
- `eventfd` integrates completions into normal Reactor ordering without blocking epoll.
- Completion overflow drops notification data rather than manufacturing success; the session
  deadline safely resolves such uncertainty as non-success.
- `acks=all` and idempotence reduce duplicate risk inside one producer session. Publisher retry
  still preserves record identity because an UNKNOWN delivery can have reached Kafka.
- The Protobuf v1 wire contract and golden vectors remain unchanged. The Kafka value is an internal
  v1 JSON event representation; no transport schema change was needed.

## Limits and unresolved issues

- Authentication remains a test stub; TLS and PostgreSQL registry are absent.
- Local Redpanda is valid functional evidence, not production-cluster durability evidence.
- There is no durable disk spool, automatic retry scheduler, dead-letter policy or cross-process
  recovery. UNKNOWN is returned to the caller for identity-preserving retry.
- Completion queue overflow is bounded and safe but may convert a delivered record into UNKNOWN.
- No schema registry, multi-broker fault test, authentication/authorization, TLS/SASL, throughput,
  latency, CPU or memory benchmark was run.
- Contracts are installable/versioned locally but are not tagged or published; no remote operation
  was authorized.

## Proposed next sprint

After review, Sprint 05 should follow the approved roadmap. Recommended prerequisites are a review
of UNKNOWN/idempotency policy, durable retry ownership, Kafka security/configuration ownership and
production observability. This Sprint did not begin Sprint 05.
