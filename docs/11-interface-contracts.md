# Interface & Data Contracts — Draft

## Device ↔ Ingest TCP wire protocol
- **Proposed**: 4-byte **big-endian unsigned frame length** followed by exactly N bytes Protobuf envelope; maximum frame length 64 KiB (subject to ADR).
- Client sends telemetry envelope with stable `message_id`, `device_id`, `sequence_number`, `event_timestamp_ms`, payload and protocol version.
- Server sends versioned `ACK(message_id)` or `NACK(message_id, error_code)` when identity is recoverable. Heartbeat/HELLO options remain open.
- One TCP `recv()` does not correspond to a message: support fragmented and coalesced frames, partial writes, disconnect mid-frame and request limits.
- ACK means successful Kafka producer delivery under broker configuration; not ClickHouse visibility.
- In v1, `BatchStart.expected_count = 0` means unspecified. `BatchEnd.sent_count` remains the
  actual count and is checked against frames received and any non-zero expected count.
- Malformed framing (zero/oversized prefix or invalid Protobuf) causes immediate connection close.
  ProtocolError is for a structurally decoded frame that fails session/semantic rules.
- `BatchAck.UNKNOWN` is not success; the publisher retains stable record identity for retry.

## Ingest ↔ Kafka
- Topic `telemetry.events.v1`, key `host_id` (current Gateway Sprint 04–07 implementation).
- **Value format: single JSON object per Kafka record**, compatible with ClickHouse `JSONEachRow` decoding. Topic name suffix `v1` is contract major version, not service release number.
- Canonical current fields and types: `nexstream-contracts/docs/KAFKA-JSON-V1.md`. Older device_id /
  sequence_number baseline examples are illustrative, not the emitted event schema.
- Producer idempotence and `acks=all` are intended settings but must be verified for actual broker version and durability topology.

## Kafka ↔ ClickHouse
- ClickHouse Kafka Engine table consumes the topic; MV projects into MergeTree table.
- Table schema/type compatibility must be tested; Kafka record may be replayed after failure.
- Do not claim uniqueness without documented dedup/query policy.

## Processor and Query
- Processor emits `telemetry.alerts.v1` as documented in contracts `docs/KAFKA-JSON-V1.md`.
- Sprint 07 Query endpoints and bounded results are specified in `nexstream-query/README.md`.
  Endpoint selection follows the explicit Sprint 07 request. Pagination beyond bounded limit is absent.

## Cross-version change procedure
Contract proposal -> compatibility tests -> tagged release -> pin dependent service versions -> staged integration -> deploy repo version updates -> rollback plan.
