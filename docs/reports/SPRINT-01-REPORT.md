# Sprint 01 Report — Protobuf Contracts

Date: 2026-11-07  
Scope: Sprint 01 only

## Outcome

The six-repository workspace was initialized as six independent local Git repositories on branch
`main`, with no remotes, pushes, secrets, or public deployments. Cross-service architecture remains
canonical in `nexstream-deploy/docs`; contract-specific guidance and evidence are owned by
`nexstream-contracts`.

Sprint 01 now provides C++20/CMake Protobuf generation, versioned transport and minimal telemetry
schemas, semantic bounds validation, a checked-in binary golden vector, and executable unit and
integration tests. Debug, Release, and ASan/UBSan builds passed.

## Implemented components

- `nexstream.transport.v1.Frame` oneof with AuthRequest, AuthResult, BatchStart, Telemetry,
  BatchEnd, BatchAck, and ProtocolError.
- Separate AuthCode and delivery ResultCode enums, including SUCCESS, RETRYABLE_FAILURE,
  PERMANENT_FAILURE, UNKNOWN, and RETRY_LATER.
- `nexstream.telemetry.v1.SystemMetricsSnapshot` with host/message identity, sample timestamp,
  CPU usage, and memory values.
- Build-tree C++ code generation; generated code is not committed.
- Semantic validation for protocol version, required fields, metric ranges, IDs, secret/detail
  sizes, frame/auth sizes, enum validity, and batch count.
- Golden vector, forward-compatible unknown-field test, unknown-enum semantic rejection, malformed
  wire rejection, retry identity, oneof distinction, and bounds tests.

## Files created or modified

### `nexstream-contracts`

- Modified: `.gitignore`, `README.md`, `docs/PROCESS.md`
- Created: `CMakeLists.txt`, `BUILDING.md`, `docs/PROTOCOL.md`, `docs/STATUS.md`,
  `docs/sprints/SPRINT-01-CONTRACTS.md`
- Created schemas: `proto/nexstream/telemetry/v1/telemetry.proto`,
  `proto/nexstream/transport/v1/transport.proto`
- Created validation: `include/nexstream/contracts/v1/validation.hpp`, `src/validation.cpp`
- Created tests/tools: `tests/test_harness.hpp`, `tests/unit/contract_tests.cpp`,
  `tests/integration/golden_vector_tests.cpp`, `tests/tools/generate_golden.cpp`,
  `tests/vectors/telemetry_frame_v1.bin`, `tests/TEST_CASES.md`
- Created evidence: `tests/results/README.md` and all files under
  `tests/results/2026-11-06-sprint-01/`

### `nexstream-deploy`

- Modified: `README.md`, `docs/README.md`, `docs/15-project-status.md`
- Created: `docs/DOCUMENTATION_OWNERSHIP.md`, `docs/STATUS.md`,
  `docs/reports/SPRINT-01-REPORT.md`

Git metadata was initialized in all six repository directories. Existing starter scaffolds in the
four runtime repositories were not changed because runtime implementation belongs to later sprints.

## Commands executed

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON
cmake --build build --parallel 2 --target nexstream_contracts_generate_golden
./build/nexstream_contracts_generate_golden tests/vectors/telemetry_frame_v1.bin
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure

cmake -S . -B build-sanitize -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer' \
  -DCMAKE_EXE_LINKER_FLAGS='-fsanitize=address,undefined'
cmake --build build-sanitize --parallel 2
ctest --test-dir build-sanitize --output-on-failure

protoc --proto_path=. --include_imports \
  --descriptor_set_out=/tmp/nexstream-sprint01.pb \
  proto/nexstream/telemetry/v1/telemetry.proto \
  proto/nexstream/transport/v1/transport.proto
cmake -S . -B build-final -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build-final --parallel 2
ctest --test-dir build-final --output-on-failure
buf --version
```

Repository initialization used `git -C <repo> init -b main` for each of the six repositories.

## Actual test result

| Classification | Count | Detail |
|---|---:|---|
| PASS | 6 | TC-PROTO-001 through TC-PROTO-006 |
| FAIL | 0 | none |
| BLOCKED | 1 | optional external `buf`/schema-registry compatibility gate unavailable |
| NOT RUN | 0 | no Sprint 01 test case omitted |

CTest reported 2/2 executable tests passing in Debug, Release, and ASan/UBSan configurations.
No benchmark was run and no performance result is claimed.

## Defects found and fixed

1. `protoc` could not resolve the imported telemetry schema. The import and generation roots were
   aligned so both generated descriptor symbols refer to the same canonical proto path.
2. Generated sources used both `proto/...` and package-relative includes. Both build-tree include
   roots were exposed on the generated target.
3. The integration test used a non-existent two-argument `ParseFromString` overload. The malformed
   byte sequence is now passed as an explicit-length `std::string`.

All fixes were followed by a rebuild and test rerun; expected results were not weakened.

## Technical decisions

- Generated C++ remains in the build tree to prevent generated-source drift.
- Semantic constraints are enforced outside `.proto`, because proto3 cannot express length/range
  validation; callers must parse then validate.
- Authentication and batch-delivery outcomes use separate enums to prevent ambiguous success.
- Unknown fields are accepted for additive compatibility, while unknown result enums are rejected
  semantically to avoid unsafe delivery decisions.
- A committed deterministic binary vector provides local compatibility evidence without adding an
  unavailable dependency. This does not replace a future registry/breaking-change gate.
- No ADR baseline was changed; Sprint 01 resolves the schema artifact within accepted boundaries.

## Limitations and unfinished work

- `buf` is not installed and no previous registry descriptor exists, so cross-release breaking
  analysis is BLOCKED. Install/pin `buf`, commit a versioned baseline, then add a CI gate.
- CMake install/export/package-consumer flows are not implemented; they should be defined before
  publishing a contract release.
- Aggregate batch byte enforcement requires session state and belongs to Sprint 02; only the
  constant and per-frame semantic limits exist in Sprint 01.
- No TCP framing, service runtime, Kafka, TLS/auth backend, deployment, or benchmark was started.

## Proposed next sprint

After human review and a pinned/tagged v1 contract, proceed to Sprint 02 in `nexstream-ingest`:
bounded incremental four-byte big-endian frame decoding, state validation, and level-triggered
`epoll` integration tests. Do not begin Kafka or production authentication in that increment.
