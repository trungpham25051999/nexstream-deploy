# Sprint 07 — ClickHouse, Query API and Analytics Processor

Date: 2026-11-21. Overall: **PARTIAL**. Local core and real full telemetry path work;
the complete requested fault/quality matrix is not fully verified. Complete Compose E2E passed.

## Implemented and observed

- CPU/RAM JSON v1 → Kafka Engine → MV → raw MergeTree, DateTime64 millisecond sampling and ingestion
  times, UInt64 memory, host/time ordering and experimental seven-day merge-driven TTL.
- Read-time `(host_id,message_id)` dedup view; test observed three raw rows and two logical identities.
- C++20 Query HTTP liveness/readiness, host range/latest, typed query parameters, bounds and timeouts.
- C++20 Processor JSON parsing, configurable consecutive CPU/RAM thresholds, bounded host/recent-ID
  state, async librdkafka delivery reports, manual input commits and metadata-only DLQ delivery.
- Atomic local checkpoint after successful output and before commit preserves streak across restart.
- Development Dockerfile/Compose and repeatable SQL/topic bootstrap assets.
- Real Agent TLS → HAProxy → Gateway PostgreSQL auth → Kafka → ClickHouse → Query passed. Captured
  row: host `agent-119f4815ad6c`, message `57f8fa52eaa64f789a8f672e5fda8aff`, CPU 2.53165%,
  memory 7106609152/16626888704 bytes. These are functional sample values, not benchmark results.
- Actual CPU and RAM alerts consumed from `telemetry.alerts.v1`; restart fixture also emitted both.

No Protobuf schema/golden-vector change, existing ADR rewrite, Git push/remote change or public endpoint.

## Test classification

| Repository | PASS | FAIL | BLOCKED | NOT RUN |
|---|---:|---:|---:|---:|
| query | 7 | 0 | 0 | 0 |
| processor | 8 | 0 | 0 | 1 |
| deploy | 7 | 0 | 0 | 1 |
| Total distinct documented cases | 22 | 0 | 0 | 2 |

Case definitions are in each repository's `tests/TEST_CASES.md`; assertions/configuration reruns are
not added to that count. Debug, Release and ASan/UBSan each passed 1/1 CTest executable per application
(six final successful CTest executions). External integrations ran in Debug, not in all build modes.
Additional regressions: Gateway 8/8, Publisher 7/7, Contracts/golden vectors 2/2 passed.
An intermediate Gateway stress test failed its 100-auth completion assertion; an unchanged rerun
passed. Follow-up inspection found the fixture had 100 simultaneous consumers polling/draining one
eventfd completion queue. They can wake for the same completion and race to drain it. The fixture now
uses 100 producers and one completion dispatcher, matching the Reactor ownership model, and verifies
each correlation ID exactly once. The same 100-success expectation and two-second completion deadline
remain. Repeated final execution is captured in `auth-stress-harness-final.log`.

Evidence directories: each participating repository's `tests/results/2026-11-21-sprint-07/`.
`final-build-matrix.log`, `http-integration-final.log`, `restart-integration-final.log`, `alerts.json`,
`dlq.log`, `group-offsets.log`, `duplicate-counts.json`, `agent-e2e.log`, `compose-build-final.log`,
`compose-e2e-final.log`, `malformed-recovery.log` contain actual outputs.
Some manual checks below were recorded in tool output rather than separate raw log files.

## Environment and commands actually run

Debian Linux 6.1.0-40-amd64, GCC 12.2.0, CMake 3.25.1, libcurl 7.88.1, nlohmann JSON 3.11.2-2
(apt package extracted locally), librdkafka 2.0.2, Docker 20.10.24, PyYAML 6.0.
ClickHouse image 24.3, server 24.3.18.7; Redpanda v24.3.18; PostgreSQL 16-bookworm; HAProxy 2.9.12-alpine.

From workspace root:

```sh
cmake -S nexstream-query -B nexstream-query/build-s07 -DCMAKE_BUILD_TYPE=Debug
cmake --build nexstream-query/build-s07 -j2
ctest --test-dir nexstream-query/build-s07 --output-on-failure
cmake -S nexstream-processor -B nexstream-processor/build-s07 -DCMAKE_BUILD_TYPE=Debug \
  -DJSON_INCLUDE_DIR=$PWD/.deps/s07-json/usr/include -DRDKAFKA_ROOT=$PWD/.deps/librdkafka-2.0.2
cmake --build nexstream-processor/build-s07 -j2
ctest --test-dir nexstream-processor/build-s07 --output-on-failure
```

Also configured/built/tested `build-s07-Debug`, `build-s07-Release`, `build-s07-Sanitize` in both repos.
Sanitize uses `NEXSTREAM_ENABLE_SANITIZERS=ON` and address/undefined flags; its initial CMake build type
was named Sanitize (not the Debug optimization preset). Final log records rebuild after source fixes.

```sh
docker run -d --name nexstream-s07-clickhouse -p 127.0.0.1:18123:8123 \
  --ulimit nofile=262144:262144 clickhouse/clickhouse-server:24.3
docker exec -i nexstream-s07-clickhouse clickhouse-client --multiquery \
  < nexstream-deploy/clickhouse/001_telemetry.sql
# Repeated same SQL: exit 0.
docker network create nexstream-s07-net
docker network connect --alias clickhouse nexstream-s07-net nexstream-s07-clickhouse
docker run -d --name nexstream-s07-redpanda --network nexstream-s07-net --network-alias redpanda \
  -p 127.0.0.1:19092:19092 docker.redpanda.com/redpandadata/redpanda:v24.3.18 \
  redpanda start --overprovisioned --smp 1 --memory 512M --reserve-memory 0M --node-id 0 \
  --check=false --kafka-addr internal://0.0.0.0:9092,external://0.0.0.0:19092 \
  --advertise-kafka-addr internal://redpanda:9092,external://127.0.0.1:19092
docker exec nexstream-s07-redpanda rpk topic create telemetry.events.v1 telemetry.alerts.v1 telemetry.dlq.v1
# Created local fixture user s07_query with SELECT on nexstream.* and no password;
# reachable only through the test container network/loopback published port.
nexstream-query/build-s07/nexstream-query http://s07_query@127.0.0.1:18123
python3 nexstream-query/tests/integration_test.py
python3 nexstream-processor/tests/real_kafka_test.py
python3 nexstream-deploy/tests/agent_e2e.py
docker stop nexstream-s07-redpanda
docker start nexstream-s07-redpanda
docker restart nexstream-s07-clickhouse
python3 nexstream-query/tests/integration_test.py
sh -n nexstream-deploy/scripts/bootstrap-topics.sh
docker compose version
# Initial plugin command unavailable. Downloaded standalone Compose v2.29.7 into .deps/docker-compose-s07.
python3 nexstream-deploy/tests/compose_e2e.py
```

Initial fixture injected three events (m1, m2, duplicate m2), sampled at 1793650000000/1793650001000,
CPU 95/96 and memory 90/91 of 100. Query tests verify exact millisecond mapping and distinct count.
Processor DLQ test injected schema_version=2: consumed metadata reported partition 0 offset 11;
group committed offset 12, lag 0. Broker stopped/restarted while worker was idle: worker reported
disconnect/refused connection and remained alive until explicit SIGINT. That idle test alone did not
exercise in-flight failure.
The later `delivery_outage_test.py` closes alert Produce requests through a Kafka-aware loopback proxy
to a separate real Redpanda broker. Worker exited 2 without checkpointing, then retried the same input
after fault removal and delivered both CPU/RAM alerts. This proves retry/no premature commit for that
transport-failure model; it does not prove every broker crash/durable-ack-loss scenario. Evidence:
`nexstream-processor/tests/results/2026-11-21-sprint-07/delivery-outage-final.log`.
ClickHouse stopped: `/health` 200, `/health/ready` 503, `/latest` 503 within the bounded request;
restart followed by HTTP integration passed. Incomplete HTTP headers closed at 3 seconds; >8 KiB
headers closed immediately. Compose config validation, all four application image builds, eight live
services, complete Agent pipeline and repeated topic bootstrap passed. Initial Compose test failed
because Gateway bound container loopback; explicit internal listen address fixed it. Test credentials,
certificate/private key and disposable Compose volumes were removed by the fixture cleanup.

## Errors found and fixes

1. ClickHouse rejected cyclic aggregate aliases in first dedup view. Changed to an argMin tuple in
   a subquery; SQL and repeated bootstrap then succeeded.
2. Query initial 503 came from default ClickHouse remote authentication. Provisioned a local fixture
   reader; added runtime credential-file configuration for Compose.
3. Processor compile missed `<optional>`; added include and rebuilt.
4. Compiler misleading-indentation warnings were corrected in touched Query/JSON code.
5. Restart initially lost threshold state. Added atomic fsynced local checkpoint and unit/real restart tests.
6. First real restart assertion read historical alerts from start of shared topic. Fixture now opens an
   end-offset reader before the new event and checks the generated host. Expected CPU/RAM behavior unchanged.
7. Query TSV parsing could misread whitespace identifiers or incomplete rows. SQL now hex-encodes IDs;
   adapter decodes them and rejects incomplete/extra columns.
8. Producer callback correlation moved from stack lifetime to shared state owned through callback completion.
9. Colon-separated alert IDs collided for colon-containing source identities. Length-prefixed IDs and
   a collision regression now cover that case. This refines the new unreleased alert topic representation.
10. Compose exposed a pre-existing Gateway loopback-only CLI limitation. Added optional listen-address
    environment configuration, kept the default loopback and published no Gateway port.
11. Initial legacy Gateway regression could not connect after its old PostgreSQL fixture was removed.
    Recreated an isolated local regression database rather than weakening or skipping the test.
12. Gateway auth stress harness had concurrent completion-queue consumers; changed only the fixture
    to single-consumer dispatch with per-token verification, preserving expectations/deadline.
13. First outage fixture omitted Docker stdin forwarding, so no input record reached the broker.
    Added `docker run -i`; final proxy fault test passed with unchanged delivery/offset assertions.

## Technical choices and limits

- Raw MergeTree plus read-time grouping makes duplicates observable and avoids false immediate uniqueness.
- Earliest-ingested identity wins; ties break deterministically by full data tuple. Identity reuse with
  different payload is a producer violation. Large dedup queries may hit configured time/memory bounds.
- HTTP server services one connection at a time with bounded backlog/header/body/result/deadlines.
  It has no throughput claim, HTTP authentication, external listen configuration or async query concurrency.
- Processor currently runs one worker with a local checkpoint. Rebalance across replicas does not transfer
  state. Full snapshots per input are simple but expensive; checkpoint/group ownership must remain stable.
- Restart after delivered output but before checkpoint can repeat alerts. No end-to-end exactly-once claim.
- Alert IDs now length-prefix source identifiers; earlier development evidence contains the initial
  colon-only IDs. Protobuf and telemetry event formats remain unchanged.
- Syntactically malformed JSON is quarantined with source offset using Kafka stream-error mode and
  a second MV. Semantic-invalid events are filtered while independent Processor emits metadata DLQ.
- TTL is configurable by SQL ALTER, experimental seven days; no elapsed retention test was performed.
- Standalone Compose v2.29.7 resolved the initial dependency gap; build/up/full path passed. Query binds
  container loopback and is inspected via exec. Network isolation has configuration evidence, not a
  penetration test. Runtime credentials are development-only.
- Missing checks: multi-worker rebalance and elapsed seven-day TTL.
  No benchmark ran. Slow/oversized headers, malformed ClickHouse recovery and repeat bootstrap passed.
- Sprint 05/06 Agent and Compose gaps now have actual full topology evidence in this sprint.

## Files added/modified

Query: CMakeLists.txt; README.md; four include headers (domain/query_model, application/query_service,
infrastructure/clickhouse_client, infrastructure/http_server); corresponding four sources; bootstrap/main.cpp;
unit/query_tests.cpp; integration_test.py; TEST_CASES.md; docs/PROCESS.md; docs/STATUS.md; result logs.

Processor: CMakeLists.txt; README.md; domain/evaluator.hpp/.cpp; infrastructure/json_codec.hpp/.cpp;
bootstrap/main.cpp; processor_tests.cpp; real_kafka_test.py; TEST_CASES.md; docs/PROCESS.md; docs/STATUS.md;
result logs. Kafka worker is separated into infrastructure/kafka_worker.hpp/.cpp; bootstrap calls it.

Deploy: clickhouse/001_telemetry.sql; Dockerfile.sprint07; docker-compose.sprint07.yml;
scripts/bootstrap-topics.sh; tests/agent_e2e.py; tests/TEST_CASES.md; results; docs/analytics/SPRINT-07-INGESTION.md;
README.md; docs/STATUS.md; docs/15-project-status.md; docs/PROCESS.md; this report.
Contracts: docs/KAFKA-JSON-V1.md only. No generated wire artifacts changed.
Ingest: src/bootstrap/main.cpp and README.md (optional internal listen address),
tests/unit/authentication_service_tests.cpp (correct single-consumer stress harness).
Workspace: .dockerignore. Deploy also adds tests/compose_e2e.py.

Next work stays within Sprint 07: review partition-state ownership
before broader deployment. Seven-day elapsed TTL is a duration-dependent check. Sprint 08 not started.
