# Sprint 07 Hardening & Distributed Correctness

Date: 2026-11-22. Scope: Sprint 07 only. Result: required local acceptance cases pass under the
explicitly bounded replay design. **Production-scale readiness is not claimed**; the recovery-history
constraint below remains P1. No Protobuf/Kafka event/alert v1 fields, remotes or public deployment changed.

## Results and evidence

| Catalog | PASS | FAIL | BLOCKED | NOT RUN |
|---|---:|---:|---:|---:|
| Processor H-P01..H-P16 | 16 | 0 | 0 | 0 |
| Query H-Q01..H-Q09 | 9 | 0 | 0 | 0 |
| Deploy H-D01..H-D06 | 6 | 0 | 0 | 0 |
| Supplementary H-QX1: TSan | 0 | 0 | 0 | 1 |
| Total catalog | **31** | **0** | **0** | **1** |

Counts describe distinct documented cases, not assertions, retries or repeated build configurations.
The supplementary TSan job was not run; ASan+UBSan were run. No NOT RUN case is labeled PASS.
Catalogs: each repository's `tests/TEST_CASES.md`. Actual evidence is in each corresponding
`tests/results/2026-11-22-sprint-07-hardening/` directory.

- Debug, Release and Debug+ASan/UBSan: Query 1/1 CTest executable and Processor 1/1 passed per mode.
- Real Kafka: two active owners, three members/two partitions including an idle member, reassignment,
  SIGKILL takeover, profile mismatch, checkpoint-write failure, alert/DLQ transport faults and restarts.
- Real ClickHouse: duplicate/conflict/replay behavior, short fixture TTL and defined dedup measurement.
- Real HTTP: escaped IDs, malformed inputs, slow/oversized headers, 200 requests at concurrency 16,
  a 64-client admission burst, and ASan-backed concurrent integration with clean shutdown.
- Regressions: Contracts/golden vectors 2/2, Publisher 7/7, Gateway/real PostgreSQL 8/8 passed.
- Full Compose: Agent TLS → HAProxy → PG-authenticated Gateway → Kafka → ClickHouse → Query passed
  with two Processor replicas running. Topic bootstrap was repeated successfully.

Final log names: Processor `build-matrix-final.log`, `rebalance-final.log`,
`release-rebalance-final.log`, `memory-final.log`, `memory.json`, `deadline-final.log`, `dlq-outage.log`,
`alert-outage-and-retention.log`, `asan-integration-final.log`, `commit-outage.log`,
`asan-commit-outage.log`; Query `build-matrix-final.log`,
`http-final.log`, `latency.json`, `asan-http.log`, `asan-server.log`, `legacy-integration.log`;
Deploy `analytics-final.log`, `dedup-measurements.json`, `regressions.log`, `compose-e2e-final.log`,
`compose-build.log`, `compose-build-processor-final.log`, `environment.log`, `source-sha256.txt`.

## Processor state, ownership and offset policy

The former local snapshot was not bound to a consumer group/topic/partition/offset and could not be
transferred safely to another owner. It is now a diagnostic artifact only and is never loaded.
Authoritative state recovery is the Kafka committed prefix, described in ADR-017.

1. Assignment resolves each assigned partition's committed **next** offset, checks watermarks and
   validates printable algorithm/rule-profile metadata stored with an existing nonzero cursor.
2. It allocates an independent `PartitionState`, assigns offset zero and reconstructs
   `[0,committed_next)` in order. Historical committed records update state but emit no alert/DLQ.
3. Live input must match the next offset. Valid telemetry must have Kafka key equal to `host_id`.
   Malformed/version/identity failures produce metadata-only DLQ records under the same delivery policy.
4. All necessary alert/DLQ delivery reports must succeed before diagnostic fsync/rename and confirmed
   Kafka offset commit. Commit results use an owned SDK queue with a three-second application deadline;
   unresolved commits stop processing conservatively. OOM is not classified as malformed input.
5. Revocation clears former partition ownership. Idle members accept zero partitions. Assignment loss
   before commit or coordinator/generation commit rejection stops processing. No delivery callback holds
   a pointer into partition state; callbacks dispatch on the worker thread and own correlation data.
6. Every exception/normal exit closes consumer ownership via RAII while callback context is still alive.

The same-group two-instance test preserved CPU/RAM streaks across assignment changes. Killing one
owner caused the survivor to reconstruct and process the next samples without republishing the
already-committed prefix. Three members over two partitions also stayed healthy and advanced offsets.
Tests ran in Debug and Release against actual Redpanda; this is not consumer behavior inferred from mocks.

Crash/delivery windows remain at-least-once:

| Window | Recovery behavior |
|---|---|
| Output fails/is uncertain | Input is not committed; retry may repeat an uncertain delivery |
| CPU alert succeeds, later output fails | Input remains pending; earlier output may duplicate with the same ID |
| All output succeeds, diagnostic checkpoint fails | No commit; confirmed output repeats on retry |
| Diagnostic succeeds, offset commit fails | Diagnostic is ignored for recovery; committed prefix is replayed |
| Offset commit succeeds, process crashes | Committed prefix reconstructs state without re-emitting its output |
| Owner loses assignment during work | It stops committing; output already delivered can still duplicate |

The `/dev/full` diagnostic-write fixture observed four output records representing two stable alert IDs,
each delivered twice, while the failed attempt did not advance input. This explicitly disproves any
end-to-end exactly-once interpretation. Kafka alerts still require downstream identity deduplication.

The separate OffsetCommit fault test dropped API-key-8 requests after both output confirmations and
the diagnostic write. The worker stopped within its bounded commit/close policy; the group still had
lag one and no committed input cursor. Retry delivered the same two IDs again. Debug and ASan cases
passed (`commit-outage.log`, `asan-commit-outage.log`). An unacknowledged commit in general remains
uncertain: it can have reached Kafka. Recovery reads Kafka's cursor rather than assuming every timeout
means no commit. Consumer close serves its callback queue for six seconds then forces local destruction;
coordinator membership may persist until session expiry after that fallback.

## Bounds and scale constraints

| Resource/policy | Bound |
|---|---:|
| Assigned partitions per worker | 16 |
| Hosts per partition | 128 |
| Recent message IDs per host | 16 |
| Parsed event / JSON nesting | 64 KiB / 4 levels |
| Consumer local queue / fetch / receive response | 1 MiB / 1 MiB / 2 MiB |
| Producer queue | 100 records / 1 MiB |
| Producer message timeout | 5 seconds; bounded flush/purge |
| Diagnostic snapshot | 512 KiB, private per instance |
| Offset commit wait / consumer close-queue drain | 3 seconds / 6 seconds before forced local teardown |
| Development Processor/Query container memory / pids | 256 MiB / 64 |
| Committed prefix replay | 100000 offsets and 30 seconds per partition |
| Initial assignment / stalled progress / reconnect budgets | 30 seconds, observed at bounded polling/probe intervals |
| Kafka socket timeout / periodic health probe | 3 seconds / 5 seconds with 500 ms metadata/watermark calls |

Probe cadence, current bounded I/O and group-close time add to a reconnect/shutdown wall-clock interval.
The final unavailable-loopback test exited in 30.134 seconds. The final live-consumer shutdown fixture
observed 63.578 ms; that idle result is not a universal shutdown SLO.

**P1 remaining operational constraint:** source history must be retained from offset zero, noncompacted,
nontransactional and gap-free; partition count/key affinity must be stable. Missing history fails closed,
as tested by trimming only an ephemeral broker's fixture prefix. A running process may continue with
in-memory state after old history expires, but subsequent restart/rebalance then needs a reviewed
durable snapshot/changelog strategy. A 100000-offset replay ceiling can be reached quickly at fleet
rates. This implementation is a bounded correctness baseline, not a general large-history solution.

Existing groups with legacy offset metadata or changed CPU/RAM/sample profiles fail closed. Do not reset
their offsets automatically. Use a reviewed new-group replay (duplicates expected) or a reviewed state
migration. All deployment instances must use a uniform profile; the code validates persisted partition
metadata, not simultaneous brand-new configuration consensus. Topic recreation/partition expansion
also requires migration review. Config version must change with evaluator semantics.

Compose now uses a container-private `/tmp/processor.checkpoint` rather than one shared snapshot lock.
The old named volume is not mounted or deleted by this change. Kafka offsets/history own recovery.

## ClickHouse correctness and measurements

Raw MergeTree retains replayed rows. Query-time grouping by `(host_id,message_id)` selects the earliest
`ingested_at`, with a deterministic whole-payload tuple tie-breaker. Tests verified identical duplicates,
different-payload identity conflicts, exact ties, and a time predicate applied to the canonical winner.
Actual Kafka replay produced three raw records and one logical row with the expected original value.
No immediate ReplacingMergeTree uniqueness assumption is made.

Conflict policy applies to currently retained raw rows. Identity reuse with a different payload is a
producer violation; if retention later removes the former winner, the retained winner may change.
This is not a permanent first-seen identity registry. Production conflict alert/quarantine policy needs review.

The retention test created a dedicated `nexstream_hardening_fixture.ttl_<id>` table with a five-second
TTL, one expired and one live row, then materialized TTL synchronously. Only the live row remained.
`SHOW CREATE TABLE nexstream.telemetry_raw` was identical before/after: the seven-day raw policy was
never changed. This proves the mechanism with fixture time, not an elapsed seven-day soak or a maximum
background deletion lag. Test datasets/tables remain in the dedicated fixture container for review.

Local dedup workload: one generated host, **100000 raw rows / 50000 identities**, two identical-payload
copies per identity, two warmups, twenty HTTP SQL executions per variant, concurrency one. The aggregate
uses count and CPU/memory sums so winner evaluation is exercised. Times include the local HTTP path.

| Query variant | p50 ms | p95 ms | p99 ms | Last reported rows/bytes read |
|---|---:|---:|---:|---|
| Raw aggregate | 6.67 | 7.56 | 25.97 | 100000 / 4700000 |
| Identity-deduplicated aggregate | 53.15 | 82.15 | 126.79 | 100000 / 8677780 |

Full samples and ClickHouse summary headers are in `dedup-measurements.json`. These are descriptive
single-host observations, not capacity/HA claims or a latency target achievement.

## Query API hardening and measurements

The former single-client handler let a slow client delay all traffic. There are now four fixed workers,
a 32-entry pending queue, bounded kernel socket buffer requests, 8192-byte headers, acceptance-relative
read/send deadlines and nonblocking overload rejection/close. Every storage request owns a CURL handle;
the repository port now explicitly requires thread-safe concurrent calls. The API remains loopback-only.
A signal-wait thread stops and joins workers without invoking condition variables from signal handlers.

Host path segments decode once and accept printable UTF-8, quotes, slashes and percent characters within
128 bytes. Invalid percent escapes, invalid/overlong/surrogate UTF-8, controls and numeric overflows are
400. Timestamps are positive Unix milliseconds through 2100-01-01 with a maximum seven-day range.
This is an additive host-acceptance policy and an explicit timestamp validation policy, not a Protobuf
change. The former quote-host 400 expectation was intentionally revised; the real injection-like literal
is parameterized and returns no unrelated rows. A control-byte ID is still rejected. Expectations were
not weakened just to obtain green tests.

Stored NaN/invalid CPU or inconsistent memory is rejected; the old silent conversion of nonfinite CPU
to zero is removed. Real corrupt-row lookup returned 503. Empty valid results remain schema-v1 arrays.

Final local HTTP workload: Debug, `/latest`, one result over the 100000-row/50000-ID fixture, 10 warmups,
200 requests, 16 concurrent clients, no keepalive, on a shared workstation with background load not isolated:
**p50 316.63 ms, p95 347.99 ms, p99 355.78 ms**. Full samples: Query `latency.json`.
All 200 requests succeeded; no percentile SLO was defined. A 64-client incomplete-header burst observed
six threads (main, signal waiter, four workers) and forty descriptors, followed by successful recovery.
Two slow clients did not monopolize all workers. Saturating all four workers can still delay others;
bounded resource use is not a complete anti-DoS/fairness or public-authentication solution.

A slow response-reader additionally forced partial writes: 10844 body bytes arrived out of a declared
192712 before the send deadline closed the connection, while another health request succeeded.
ASan-backed HTTP ran separately, including concurrency/slow clients and clean SIGINT shutdown with no
sanitizer report. Its separate latency samples must not be compared as if CPU/load conditions matched.

## Kafka worker malformed input and safety evidence

The real workload injected 100 records of 60001 bytes with deep JSON nesting and 20 records of 262159
bytes. All 120 produced confirmed metadata-only DLQ records. Final observed RSS was 10846208 bytes
baseline and 12619776 bytes peak, below the fixture's additional 64 MiB ceiling. This is observed RSS for this
defined workload, not a proof of every allocator or compression-bomb behavior. Fetch/receive/parser/
state bounds and no-progress deadlines are separate controls. SDK transport limits do not establish
an absolute decompression bound. Compose additionally applies a 256 MiB / 64-pid envelope, inspected
for both live Processor replicas in the final E2E. Native production execution also needs an explicit
cgroup/process budget. Adversarial compression amplification/OOM behavior was not exercised by this
plain-record workload; a hard process kill must leave uncommitted input for recovery.

A Kafka-aware loopback proxy dropped only alert or DLQ Produce requests to a separate real broker.
Unconfirmed delivery stopped without checkpoint/commit; consumer/broker restart retried the original
identity or source offset. ASan+UBSan with leak detection exercised delivery ownership, purge, restart,
shutdown and missing-prefix rejection. Broker-restart and group-recovery tests use actual Redpanda,
not stub acknowledgements. No PostgreSQL/Kafka success is inferred from a mock.

## Findings by severity

| Priority | Finding | Disposition |
|---|---|---|
| P0 correctness risk | Unscoped local state could restore a cursor/partition unrelated to Kafka ownership | Removed as authority; committed-prefix recovery and profile-bound offsets |
| P1 | Rebalance/takeover/idle-owner lifecycle previously unverified | Real two/three-instance tests; zero-assignment handler and ownership checks |
| P1 | Recovery/connection/poison progress could retry without a useful bound | Explicit replay/assignment/progress/reconnect limits and fail-closed exits |
| P1 remaining | Replay from zero/100000-offset ceiling limits prolonged fleet operation | ADR-017 production gate; durable distributed snapshots/changelog review required |
| P2 | Sequential HTTP, restricted escaped IDs, overflow timestamps | Bounded worker pool, typed parameters, strict UTF-8/path/numeric policy |
| P2 | Nonfinite stored CPU could become fabricated zero | Reject invalid stored values; unit + real storage test |
| P2 | Rule uniformity, legacy-group migration and source topic lifecycle | Explicit deployment preconditions/migration review; no automatic offset reset |
| P2 | Third-party decompression is not bounded solely by wire response limits | Container budget applied/inspected; native production isolation required; compression amplification not measured |
| P2 test hygiene | Fixed-name ephemeral broker cleanup could remove a pre-existing container / retain anonymous volume | Track successful fixture creation; remove only its own container with attached fixture volumes |

During implementation, a raw newline in offset metadata caused Redpanda control-character RPC rejection.
The fingerprint is now printable hex; final rebalance/config tests passed. The first TTL assertion failed
because ClickHouse JSON renders UInt64 as a decimal string; normalization preserves the expected surviving
ID 2. An early HTTP run stopped because the preceding analytics fixture had not produced its measurement
file after that assertion. Those failed attempts are retained in `rebalance.log`, `analytics.log`, `http.log`;
final files show corrected successful runs. No desired result was relaxed.

## Environment and actual command families

Debian Linux 6.1.0-40-amd64; GCC 12.2.0; CMake 3.25.1; Intel i7-8550U (4 cores/8 logical CPUs);
RAM 16626888704 bytes. libcurl 7.88.1, librdkafka 2.0.2, nlohmann JSON 3.11.2. Redpanda v24.3.18
uses one shard/512 MiB; ClickHouse 24.3.18.7 is a single local server. Docker 20.10.24, local Compose
2.29.7, PostgreSQL 16-bookworm and HAProxy 2.9.12-alpine. Details: `environment.log`.

Commands were run from the six-repository workspace. Existing build caches retained explicit local
dependency prefixes `.deps/librdkafka-2.0.2` and `.deps/s07-json/usr/include`.

```sh
cmake -S nexstream-query -B nexstream-query/build-s07-Debug -DCMAKE_BUILD_TYPE=Debug -DNEXSTREAM_ENABLE_SANITIZERS=OFF
cmake --build nexstream-query/build-s07-Debug -j2
ctest --test-dir nexstream-query/build-s07-Debug --output-on-failure
# Both services also configured Release and Debug+NEXSTREAM_ENABLE_SANITIZERS=ON in build-s07-Sanitize.
cmake --build nexstream-processor/build-s07-Debug -j2
ctest --test-dir nexstream-processor/build-s07-Debug --output-on-failure
python3 nexstream-processor/tests/hardening_rebalance_test.py
NEXSTREAM_PROCESSOR_BINARY=$PWD/nexstream-processor/build-s07-Release/nexstream-processor python3 nexstream-processor/tests/hardening_rebalance_test.py
python3 nexstream-processor/tests/hardening_memory_test.py
python3 nexstream-processor/tests/hardening_deadline_test.py
python3 nexstream-processor/tests/delivery_outage_test.py --trim-history
python3 nexstream-processor/tests/delivery_outage_test.py --commit
python3 nexstream-processor/tests/delivery_outage_test.py --dlq --oversized --broker-restart
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 NEXSTREAM_PROCESSOR_BINARY=$PWD/nexstream-processor/build-s07-Sanitize/nexstream-processor python3 nexstream-processor/tests/delivery_outage_test.py --dlq --oversized --broker-restart --trim-history
docker exec -i nexstream-s07h-clickhouse clickhouse-client --multiquery < nexstream-deploy/clickhouse/001_telemetry.sql
python3 nexstream-deploy/tests/hardening_analytics_test.py
nexstream-query/build-s07-Debug/nexstream-query http://hardening_reader@127.0.0.1:28123
python3 nexstream-query/tests/hardening_http_test.py
python3 nexstream-query/tests/integration_test.py
# Query sanitizer server was also launched; NEXSTREAM_QUERY_BUILD=ASan selected separate HTTP evidence.
ctest --test-dir nexstream-contracts/build-package-v2 --output-on-failure
ctest --test-dir nexstream-publisher/build-s06 --output-on-failure
ctest --test-dir nexstream-ingest/build-s05-pg --output-on-failure
NEXSTREAM_COMPOSE_PROCESSORS=2 python3 nexstream-deploy/tests/compose_e2e.py
```

Compose image builds used `.deps/docker-compose-s07 -f nexstream-deploy/docker-compose.sprint07.yml build
query processor` and a final Processor rebuild. Secret-path variables were `/dev/null` only for build/
config evaluation; the E2E fixture generated runtime-only test secrets and certificates. No private key
was placed in repository source. No Git push or remote edit occurred.

## Files and review notes

Processor: application/partition_state.hpp/.cpp; infrastructure/kafka_worker.cpp; domain/evaluator.cpp;
CMakeLists.txt; processor_tests.cpp; hardening_rebalance_test.py; hardening_memory_test.py;
hardening_deadline_test.py; delivery_outage_test.py; README/PROCESS/STATUS/test catalogs and evidence.
Query: infrastructure/http_server.hpp/.cpp; domain/query_model.cpp; application/query_service.hpp;
bootstrap/main.cpp; CMakeLists.txt; query_tests.cpp; integration_test.py; hardening_http_test.py;
README/PROCESS/STATUS/test catalogs and evidence.
Deploy: docker-compose.sprint07.yml; tests/compose_e2e.py; tests/hardening_analytics_test.py; ADR-017;
README/status/analytics/test documentation, evidence and both required hardening reports.

Hardening made no source changes to Gateway, Publisher, Contracts or accepted baseline ADRs. Historical
Sprint 07 reports remain historical. Source checksums accompany evidence. Dedicated hardening data
containers are retained for review; disposable broker fault/Compose/PG fixtures are cleaned by exact
fixture targets. No broad Docker prune or unrelated retention/data change was performed.

Do not accept any claim beyond bounded local operation without further review.
No Sprint 08 work started.
