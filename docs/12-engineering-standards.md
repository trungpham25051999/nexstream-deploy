# Engineering Standards — All Repositories

## Naming
| Scope | Pattern | Example |
|---|---|---|
| Repo | `nexstream-<capability>` | `nexstream-ingest` |
| Executable | `nexstream-<capability>` | `nexstream-query` |
| Docker | `ghcr.io/<owner>/nexstream-<capability>:<semver>` | `ghcr.io/acme/nexstream-ingest:1.0.0` (placeholder) |
| C++ namespace | `nexstream::<service>::<layer>` | `nexstream::ingest::domain` |
| CMake target | `nexstream_<service>_<module>` | `nexstream_ingest_core` |
| Protobuf | `nexstream.<domain>.vN` | `nexstream.telemetry.v1` |
| Kafka topic | `<domain>.<event>.vN` | `telemetry.events.v1` |
| Consumer group | `nexstream.<service>.vN` | `nexstream.processor.v1` |
| Metric | `nexstream_<service>_<metric>_<unit>` | `nexstream_ingest_ack_duration_seconds` |

## C++ style
C++20; `PascalCase` types; `snake_case` functions/locals; `member_`; `kConstantName`; `.hpp`/`.cpp`; four-space indents; 100-column guide. RAII and explicit ownership; avoid raw owning pointers and unchecked allocations; document thread-safety and errors.

## Toolchain
CMake target-based build with compiler and dependency versions pinned; `clang-format`, `clang-tidy`, CTest/GoogleTest; GCC and Clang; sanitizers. Keep generated code out of domain core.

## Git and CI
Short-lived branches `feat/...`, `fix/...`, `docs/...`; PR describes issue, ADR, tests, observed result. `main` protected; separate releases with `vMAJOR.MINOR.PATCH` and immutable Docker tags/digests. No direct source copy between repos. Versioned contracts must be pinned.

## Security
Never commit credentials, personal device IDs, production IP addresses, unredacted debug dumps. Validate untrusted frame lengths before allocating. Use TLS/authentication as a separate explicitly scoped deployment decision before public exposure.
