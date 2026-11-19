# Sprint 06 Report — Durable Linux Monitoring Agent

Date: 2026-11-19  
Scope: Sprint 06 only

## Outcome

`nexstream-publisher` now also builds `nexstream-agent`: a C++20 Linux Agent with verified
nonblocking TLS 1.3, durable SQLite WAL queue, real CPU/RAM sampling, stable record identity and
bounded backlog retry. The existing Protobuf v1 contract is unchanged.

A complete local functional path succeeded:

`Agent → TLS HAProxy → Gateway → PostgreSQL authentication → Redpanda`

Eight records reached `telemetry.events.v1` with Kafka key `pg-host`; a consumed record contained a
stable CSPRNG message ID and real CPU/RAM values. The Agent queue was empty after confirmed SUCCESS.

## Implemented components

- OpenSSL TLS 1.3 client with CA-chain and hostname verification, SNI, nonblocking handshake,
  SSL WANT_READ/WANT_WRITE handling and the original overall 10-second deadline.
- SQLite WAL queue with `synchronous=FULL`, atomic outcome application, stable IDs, maximum 24-hour
  retention, configurable logical quota/filesystem headroom and drop-oldest pending policy.
- SUCCESS deletion, UNKNOWN/timeout/retry retention and permanent-failure quarantine.
- Crash recovery test using SIGKILL during an uncommitted transaction and `/dev/full` failure test.
- Real `/proc/stat` CPU and `/proc/meminfo` memory collector on a steady-clock sampling thread.
- GPU/Disk/Network adapters explicitly report `UNSUPPORTED` because contracts v1 has no fields.
- Separate sampling and publishing threads, one active batch, maximum 50 records, minimum drain
  interval, capped exponential backoff and jitter.
- Runtime CLI reads API secret from a file and never prints it.

## Files created or modified

### `nexstream-publisher`

- Modified: `CMakeLists.txt`, `README.md`, `docs/{PROCESS,STATUS}.md`, `tests/TEST_CASES.md`,
  `tests/results/README.md`, nonblocking stream and TCP publisher sources/headers.
- Created application: `agent_ports.hpp`, `retry_policy.{hpp,cpp}`, `durable_agent.{hpp,cpp}`.
- Created infrastructure: `durable_queue.{hpp,cpp}`, `linux_collector.{hpp,cpp}`.
- Created executable: `src/bootstrap/agent_main.cpp` (`nexstream-agent`).
- Created tests: `durable_queue_tests.cpp`, `collector_retry_tests.cpp`,
  `durable_agent_tests.cpp`, `tests/tools/measurement_probe.cpp` and Sprint 06 evidence.

### `nexstream-deploy`

- Updated report/status indexes and created this report.

No `.proto`, golden vector, ADR, Git remote, public endpoint or Sprint 07 component changed.

## Commands and actual evidence

Redacted commands are recorded in
`nexstream-publisher/tests/results/2026-11-19-sprint-06/commands.txt`. Principal commands:

```sh
cmake -S nexstream-publisher -B nexstream-publisher/build-s06 \
  -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON \
  -DCMAKE_PREFIX_PATH=<contracts> -DSQLITE3_ROOT=<sqlite> \
  -DNEXSTREAM_INGEST_BINARY=<gateway>
cmake --build nexstream-publisher/build-s06 --parallel 2
ctest --test-dir nexstream-publisher/build-s06 --output-on-failure

cmake --build nexstream-publisher/build-s06-release --parallel 2
ctest --test-dir nexstream-publisher/build-s06-release --output-on-failure

cmake --build nexstream-publisher/build-s06-sanitize --parallel 2
ctest --test-dir nexstream-publisher/build-s06-sanitize --output-on-failure

./build-s06/nexstream_publisher_measurement_probe
```

The E2E run used local PostgreSQL 16, Redpanda v24.3.18, Gateway Sprint 05 and HAProxy 2.9.12.
Temporary credentials/certificates, SQLite files and containers were removed afterward.

## Results

| Classification | Count | Detail |
|---|---:|---|
| PASS | 17 | TC-AGENT-001..017 |
| FAIL | 0 | final runs |
| BLOCKED | 0 | none |
| NOT RUN | 1 | TC-AGENT-018 Docker Compose CLI topology |

- Debug: 7/7 PASS.
- Release: 7/7 PASS.
- Final ASan/UBSan: 7/7 PASS.
- Positive TLS/PG/Kafka integration: PASS; Kafka high watermark 8, successful queue count 0.
- Wrong hostname: TLS failed, 3 pending records retained.
- Untrusted CA: TLS failed, 11 pending records retained.
- Compose plugin remained unavailable. Equivalent services were run manually, but the Compose
  invocation itself is honestly NOT RUN.

## Measurement

On the recorded local Debug environment, 1,000 immediate collector calls took 14,132 µs total
(14.132 µs mean); 12 produced CPU deltas because calls intentionally had no one-second spacing.
SQLite with 1,000 records occupied 4,304,448 bytes including DB/WAL/SHM under FULL sync. These are
actual local micro-measurements, not capacity or production benchmark claims.

## Errors found and fixed

1. Initial TLS implementation produced misleading-indentation warnings around WANT_READ/WRITE;
   control flow was made explicit and rebuilt warning-free.
2. Initial SQLite quota used physical file size. SQLite page reuse meant drop-oldest might not make
   the file shrink. Quota now bounds logical queued bytes and independently checks filesystem
   headroom; a test proves oldest-pending eviction.
3. Initial ASan run detected a 102,408-byte leak when SQLite initialization threw after opening a
   handle (`/dev/full`). Constructor failure cleanup now closes partial handles; final sanitizer
   tests passed.
4. A missing brace in the publishing-loop success branch caused a compile failure. It was corrected
   without changing expected behavior.
5. Final review found the 24-hour cleanup API was tested but not invoked by the production sampling
   path. Retention enforcement now runs before each sample enqueue, with a dedicated assertion and
   complete Debug/Release/sanitizer rerun.

No expected result was weakened and no failed test was skipped.

## Technical decisions

- TLS is enabled by the Agent composition root and has no insecure verification option. Numeric
  transport address avoids blocking DNS while the independently configured hostname is verified.
- Sampling and publishing use separate threads so a 10-second network transaction cannot delay the
  one-second steady-clock schedule.
- SQLite identity is the CSPRNG `message_id` primary key. Reopening, timeout and UNKNOWN reuse the
  same stored row; no retry generates a new identity.
- Quarantine is durable and excluded from fetch/drop-oldest retry selection. Operator export/removal
  is future operational tooling, not an infinite retry.
- One publisher thread is the concurrency guard for one active batch. Backlog draining is bounded
  by batch size and minimum interval.
- GPU/Disk/Network were not added to Protobuf v1 without compatibility review. Reporting
  `UNSUPPORTED` is safer than fake or hidden values.

## Limits and incomplete items

- Full Docker Compose command remains NOT RUN because the plugin is absent, despite equivalent
  manual E2E success.
- Only numeric IPv4 transport is supported; no asynchronous DNS or IPv6.
- Queue quota uses estimated logical record bytes plus filesystem available-space headroom. It is
  not a hard filesystem project quota.
- No quarantine administration CLI, service manager unit, package installer, automatic certificate
  rotation, hardware-backed secret storage or remote configuration exists.
- Collector currently covers only v1 CPU/RAM. GPU/Disk/Network require a versioned additive contract
  review before production serialization.
- No sustained one-second, 24-hour, power, CPU-percent, RSS percentile or outage-drain benchmark ran.

## Proposed next step

Do not begin Sprint 07 implicitly. First review queue quota semantics, quarantine operations,
service packaging, collector contract evolution and run the Compose topology on a supported host.
