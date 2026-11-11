# Sprint 02 Report — C++20 TCP Gateway Core

Date: 2026-11-11  
Scope: Sprint 02 only

## Outcome

`nexstream-ingest` now builds a C++20 loopback TCP Gateway Core with bounded incremental framing,
Protobuf v1 decoding, protocol state validation, RAII socket ownership, and a single-threaded Linux
epoll Level-Triggered Reactor. It handles fragmented/coalesced frames, nonblocking partial I/O,
EINTR/EAGAIN, disconnects, deadlines, fd reuse, bounded batches, and 100 concurrent functional
clients.

Authentication and delivery are explicitly test stubs. The delivery stub returns `UNKNOWN`, never
`SUCCESS`; no result in this report proves Kafka, PostgreSQL, or TLS operation.

## Implemented components

- `FrameDecoder`: `[uint32_be length][Protobuf Frame]`, partial header/payload, coalescing, zero/
  oversize/malformed rejection, allocation only after bounded length validation.
- `UniqueFd` and `TcpAcceptor`: movable RAII file descriptors, `SOCK_NONBLOCK`, `SOCK_CLOEXEC`,
  `accept4`, loopback bind.
- `EpollReactor`: Level-Triggered EPOLLIN/EPOLLOUT/ERR/HUP/RDHUP, eventfd shutdown, accept/read/
  write budgets, connection limit, deadline scan.
- `TcpConnection`: bounded decoder and send queue, short read/write handling, stable ID/generation
  token, no raw callback pointers.
- `ProtocolSession`: AuthRequest → BatchStart → Telemetry* → BatchEnd, host/batch/count/byte checks,
  deterministic auth stub and non-Kafka delivery stub.
- Gateway executable and four CTest executables (three unit, one integration).

## Resource limits

| Resource | Default |
|---|---:|
| Connections | 1,024 |
| Frame payload | 65,536 bytes |
| Decoder buffered bytes | 65,540 bytes/connection |
| Send buffer | 131,072 bytes/connection |
| Batch payload | 1,048,576 bytes |
| Samples/batch | 50 |
| Read budget | 65,536 bytes/tick |
| Frame budget | 32/tick |
| Write budget | 65,536 bytes/tick |
| Session deadline | 10 seconds |

## Files created or modified

### `nexstream-ingest`

- Modified: `.gitignore`, `README.md`, `docs/PROCESS.md`
- Created build/docs: `CMakeLists.txt`, `BUILDING.md`, `docs/STATUS.md`,
  `docs/sprints/SPRINT-02-TCP-GATEWAY.md`
- Created headers: `include/nexstream/ingest/application/protocol_session.hpp`,
  `include/nexstream/ingest/infrastructure/{unique_fd,frame_decoder,tcp_acceptor,tcp_connection,epoll_reactor}.hpp`
- Created sources: `src/application/protocol_session.cpp`,
  `src/infrastructure/{frame_decoder,tcp_acceptor,tcp_connection,epoll_reactor}.cpp`,
  `src/bootstrap/main.cpp`
- Created tests: `tests/test_harness.hpp`, `tests/unit/{frame_decoder_tests,protocol_session_tests,tcp_connection_io_tests}.cpp`,
  `tests/integration/tcp_gateway_tests.cpp`, `tests/TEST_CASES.md`
- Created evidence: `tests/results/README.md` and
  `tests/results/2026-11-11-sprint-02/{summary.md,commands.txt,environment.json,raw.log}`

### `nexstream-deploy`

- Modified: `docs/README.md`, `docs/STATUS.md`
- Created: `docs/reports/SPRINT-02-REPORT.md`

No Protobuf v1 contract file, remote, or other service repository was changed.

## Commands executed

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON \
  -DNEXSTREAM_CONTRACTS_ROOT=~/nexstream/nexstream-contracts
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
ctest --test-dir build -R tcp_gateway_integration --repeat until-fail:5 --output-on-failure

cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  -DNEXSTREAM_CONTRACTS_ROOT=~/nexstream/nexstream-contracts
cmake --build build-release --parallel 2
ctest --test-dir build-release --output-on-failure

cmake -S . -B build-sanitize -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON \
  -DNEXSTREAM_CONTRACTS_ROOT=~/nexstream/nexstream-contracts \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer' \
  -DCMAKE_EXE_LINKER_FLAGS='-fsanitize=address,undefined'
cmake --build build-sanitize --parallel 2
ctest --test-dir build-sanitize --output-on-failure
```

Contract source hashes were captured with `sha256sum`; see the test summary.

## Actual results

| Classification | Count | Scope |
|---|---:|---|
| PASS | 11 | TC-TCP-001 through TC-TCP-011 |
| FAIL | 0 | final runs |
| BLOCKED | 0 | Sprint 02 test cases |
| NOT RUN | 0 | Sprint 02 test cases |

Debug, Release, and ASan/UBSan each passed 4/4 CTest executables. Integration passed five repeated
Debug runs. TC-TCP-008 exercised 100 concurrent clients; this is not a capacity benchmark.
Separately from test-case counts, one release-readiness item is **BLOCKED**: no tagged/installable
contract artifact exists, so the local build currently requires an explicit contracts checkout.

## Errors found and fixed

1. CMake's implicit Protobuf generation could not infer a proto root outside the repository. It was
   replaced with an explicit `protoc --proto_path=<contracts-root>` custom command, preserving the
   canonical contract import path and build-tree generation.
2. Test code initially ignored `[[nodiscard]]` session results. Results are now captured and the
   warning-free build rerun.
3. A strict slow-loopback EAGAIN assertion failed: Linux buffered the full ACK, so the test did not
   prove the intended branch. The expected behavior was retained and moved to a deterministic
   nonblocking socketpair test that fills the actual send queue until `EAGAIN`, then verifies pending
   output remains buffered.
4. Fairness review found a coalesced recv could decode more than the intended frame budget. Recv
   size is now bounded by remaining byte and minimum-wire frame budgets per tick.
5. Final review found BatchEnd bytes were omitted from the aggregate batch limit. They are now
   included before accepting completion.

All fixes were followed by Debug, Release, and sanitizer reruns. No expected result was weakened.

## Technical decisions

- epoll is Level-Triggered per ADR-010; all accepted/client/epoll/event fds are nonblocking and
  RAII-owned.
- epoll stores a 64-bit ID/generation token. Closed/stale tokens miss the connection map, preventing
  fd reuse from selecting a newer connection.
- Reactor and connections are cohesive infrastructure hot-path code; protocol sequence policy is a
  separate application class. Domain code has no Linux/Protobuf dependency because no telemetry
  domain use case is introduced in this sprint.
- Test auth is synchronous and deterministic because PostgreSQL workers are Sprint 05. Its detail
  string labels the stub.
- Stub BatchAck is `UNKNOWN`, ensuring it cannot be interpreted as Kafka-confirmed delivery.
- Generated Protobuf C++ remains in the build tree and uses the unchanged canonical Sprint 01
  schemas. Their SHA-256 hashes are recorded with evidence.

## Limitations and blockers

- Contracts have no tagged/installable CMake package. The workspace build therefore requires an
  explicit reviewed source checkout path. This does not block local Sprint 02 tests, but blocks an
  independently releasable Ingest artifact until contract packaging/version pinning is resolved.
- Listener is plaintext loopback by default; TLS/HAProxy and production exposure are not present.
- Auth and delivery are stubs; there is no PostgreSQL, Kafka producer, JSON event output, durable
  ACK, retry registry, metrics endpoint, or production configuration loader.
- Timeout scanning is O(number of active connections), suitable for the current baseline but not
  benchmark-validated.
- The 100-client run proves functional progress only. 1,000-client, sustained-load, RSS/CPU, latency
  percentiles, noisy-client fairness measurement, and TSan were not run and no performance target
  is claimed.

## Next proposed work

Review and package/tag contracts before dependent release. The next implementation sprint should be
Sprint 03 publisher transport only after review of Sprint 02 wire/state behavior. Kafka remains a
later dedicated sprint and must replace the `UNKNOWN` delivery stub with broker-confirmed outcomes.
