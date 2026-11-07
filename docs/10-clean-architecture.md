# Clean / Hexagonal Architecture Standard

## Allowed compile-time dependencies
- `domain` -> standard C++ only (and carefully accepted pure utility libraries).
- `application` -> `domain`; defines input use cases and output ports/interfaces.
- `infrastructure/adapters` -> application ports and domain types; may use platform/API dependencies.
- `bootstrap` -> all needed targets; constructs and connects dependencies.
- No `domain` include of `librdkafka`, Protobuf generated classes, Linux fd headers, ClickHouse, HTTP frameworks.

## Example of gateway boundaries
| Layer | Example | Should not do |
|---|---|---|
| Domain | `TelemetryRecord`, `TelemetryValidator` | TCP parsing or direct Kafka sends |
| Application | `IngestTelemetry`, `MessageProducer` port | instantiate Kafka concrete client |
| Adapters | `TcpTelemetryReceiver`, `ProtobufTelemetryDecoder`, `KafkaMessageProducer` | hold business policy inside transport code |
| Bootstrap | `main.cpp`, configs, wiring | add business rule logic |

## Performance escape hatch
Hot-path buffers, fd ownership and `epoll` mechanics can remain cohesive in infrastructure; do not add heap allocations or virtual dispatch per packet solely for architectural purity. If measurements justify a special path, document it in an ADR with profiling evidence.

## Error and ownership policy
- File descriptors are RAII-owned and explicitly movable, not copied.
- Bounded buffers are mandatory, measured in **bytes**.
- Async callbacks must not outlive connection state (use IDs / safe lifetime policy).
- Every port declares failure, cancellation and thread-safety semantics.
- Prefer value types; use `unique_ptr` for exclusive dynamic ownership; shared ownership only when demonstrated.

## Testing layers
Domain/application: unit and fake port tests; adapters: integration tests against real dependencies; end-to-end in Deploy repo. Run ASan/UBSan and TSan in suitable separate CI jobs.
