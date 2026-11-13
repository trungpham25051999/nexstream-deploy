# Sprint 03 Report — TCP Publisher Transport

Date: 2026-11-13  
Scope: Sprint 03 only

## Outcome

`nexstream-publisher` now implements a single-transaction C++20 nonblocking IPv4 TCP client using
length-prefixed Protobuf v1 frames and one monotonic 10-second deadline across connect,
authentication, batch upload, and ACK receipt. It handles partial I/O, EINTR, EAGAIN, disconnect,
timeout, malformed responses, bounded frames/batches, and every v1 ResultCode.

Integration with the real Sprint 02 Gateway verifies that its test-stub `BatchAck.UNKNOWN` is not
delivery success and that original record identities remain available for retry.

## Protocol clarification completed before code

Without modifying `.proto` schemas, canonical docs now specify:

- `expected_count=0` means unspecified while limits still apply.
- BatchEnd carries and validates actual record count.
- malformed framing closes immediately.
- UNKNOWN is not delivery success and requires identity-preserving retry.

## Implemented components

- Immutable `Batch`/`TelemetryRecord` domain values.
- ACK interpreter for SUCCESS, UNKNOWN, RETRYABLE_FAILURE, PERMANENT_FAILURE, and RETRY_LATER,
  including aggregate/per-record consistency and identity validation.
- Bounded incremental response decoder and big-endian frame encoder.
- RAII `UniqueFd` and `NonblockingStream` with nonblocking connect, `poll`, partial send/recv,
  EINTR/EAGAIN handling, disconnect and deadline outcomes.
- `TcpPublisherClient` implementing AuthRequest/AuthResult, BatchStart, Telemetry, BatchEnd,
  BatchAck, limits, and stable retry results.
- CLI fixture plus four CTest executables (three unit, one Gateway integration).

## Limits and result policy

| Resource/policy | Value |
|---|---|
| Overall transaction deadline | 10 seconds |
| Frame payload | 65,536 bytes |
| Aggregate batch wire bytes | 1,048,576 bytes |
| Records/batch | 50 |
| Identifier | 128 bytes |
| Secret | 512 bytes |
| Addressing | numeric IPv4 only |
| UNKNOWN/retryable/timeout/disconnect | retain stable IDs; retry |
| PERMANENT_FAILURE | do not auto-retry |
| SUCCESS | release only with consistent per-record SUCCESS |

## Files created or modified

### `nexstream-publisher`

- Modified: `.gitignore`, `README.md`, `docs/PROCESS.md`
- Created build/docs: `CMakeLists.txt`, `BUILDING.md`, `docs/STATUS.md`,
  `docs/sprints/SPRINT-03-TCP-PUBLISHER.md`
- Created domain/application headers: `include/nexstream/publisher/domain/batch.hpp`,
  `include/nexstream/publisher/application/publish_outcome.hpp`
- Created infrastructure headers: `include/nexstream/publisher/infrastructure/{unique_fd,frame_codec,nonblocking_stream,tcp_publisher_client}.hpp`
- Created sources: `src/application/ack_interpreter.cpp`,
  `src/infrastructure/{frame_codec,nonblocking_stream,tcp_publisher_client}.cpp`,
  `src/bootstrap/main.cpp`
- Created tests: `tests/test_harness.hpp`,
  `tests/unit/{ack_interpreter_tests,publisher_validation_tests,nonblocking_io_tests}.cpp`,
  `tests/integration/gateway_integration_tests.cpp`, `tests/TEST_CASES.md`
- Created evidence: `tests/results/README.md` and
  `tests/results/2026-11-13-sprint-03/{summary.md,commands.txt,environment.json,raw.log}`

### Protocol/system documentation

- Modified: `nexstream-contracts/docs/PROTOCOL.md`, `nexstream-contracts/docs/STATUS.md`
- Modified: `nexstream-deploy/README.md`, `docs/README.md`, `docs/STATUS.md`,
  `docs/11-interface-contracts.md`, `docs/15-project-status.md`
- Created: `nexstream-deploy/docs/reports/SPRINT-03-REPORT.md`

No `.proto`, Gateway source, remote, or other service implementation was changed.

## Commands executed

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON \
  -DNEXSTREAM_CONTRACTS_ROOT=~/nexstream/nexstream-contracts \
  -DNEXSTREAM_INGEST_BINARY=~/nexstream/nexstream-ingest/build/nexstream-ingest
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure

cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  -DNEXSTREAM_CONTRACTS_ROOT=~/nexstream/nexstream-contracts \
  -DNEXSTREAM_INGEST_BINARY=~/nexstream/nexstream-ingest/build-release/nexstream-ingest
cmake --build build-release --parallel 2
ctest --test-dir build-release --output-on-failure

cmake -S . -B build-sanitize -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON \
  -DNEXSTREAM_CONTRACTS_ROOT=~/nexstream/nexstream-contracts \
  -DNEXSTREAM_INGEST_BINARY=~/nexstream/nexstream-ingest/build-sanitize/nexstream-ingest \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer' \
  -DCMAKE_EXE_LINKER_FLAGS='-fsanitize=address,undefined'
cmake --build build-sanitize --parallel 2
ctest --test-dir build-sanitize --output-on-failure
```

## Actual results

| Classification | Count | Scope |
|---|---:|---|
| PASS | 10 | TC-PUB-001 through TC-PUB-010 |
| FAIL | 0 | final runs |
| BLOCKED | 0 | Sprint 03 test cases |
| NOT RUN | 0 | Sprint 03 test cases |

Debug, Release, and ASan/UBSan each passed 4/4 CTest executables; Gateway integration passed five
consecutive Debug repetitions. No benchmark ran. A separate
release-readiness item remains BLOCKED: contracts and Gateway are local paths, not tagged/installable
artifacts.

## Errors found and fixed

1. Initial compile failed due to a missing closing brace in a `ReceiveResult` return expression.
   The syntax was fixed and the build rerun.
2. Review found received protocol version and unknown/unspecified AuthCode were not validated.
   Responses now fail safe before state progression.
3. Timeout was initially tested only at stream level. A full publisher transaction fixture now
   withholds AuthResult, exercises the deadline, and asserts both message IDs remain unchanged.
4. Additional review added malformed server framing and aggregate batch-byte coverage.

No expected result was weakened to pass tests.

## Technical decisions

- `poll()` is used for a single nonblocking transaction. epoll/concurrent load generation is not
  needed for this first Publisher increment and would add premature complexity.
- A single `steady_clock` deadline is passed through every operation, preventing each phase from
  resetting the 10-second budget.
- The caller retains immutable Batch data. Publisher returns per-record retry decisions and never
  mutates message IDs; persistence/automatic retry belongs to a later durable-agent sprint.
- Aggregate SUCCESS is accepted only when all expected IDs appear exactly once with SUCCESS.
  Mismatch or conflict is a protocol failure that retains records for safe review/retry.
- Numeric IPv4 avoids accidental blocking DNS in the transport path.
- Protobuf C++ is generated from unchanged canonical v1 sources into the build tree.

## Limitations and blockers

- No automatic retry scheduler, exponential backoff/jitter, SQLite persistence, crash recovery, or
  durable retention. The caller must retain retry records.
- No TLS, hostname validation, PostgreSQL auth, Kafka delivery, or real metrics collectors.
- The CLI uses documented local test fixtures and is not a production credential/configuration
  interface.
- Only numeric IPv4 and one connection/batch are supported; no DNS, IPv6, concurrency, rate control,
  latency statistics, or load generation yet.
- Contracts/Gateway dependencies are explicit local paths because packaged pinned artifacts do not
  exist. This blocks independent release packaging, not local Sprint 03 verification.
- No performance, throughput, latency percentile, CPU, or RSS measurements were made.

## Next step

Do not start Kafka implicitly. First review Sprint 03 retry/per-record behavior and establish tagged
contract/Gateway artifacts. The next planned sprint should follow the approved roadmap and keep
durable persistence/retry semantics separately scoped from Kafka delivery integration.
