# ACK / retry / ordering / idempotency

**State:** design policy; full contract pending.

## Three different success signals

1. Socket send successful: local kernel accepted bytes; not application delivery.
2. Gateway ACK: Kafka accepted record under configured producer durability (`acks=all` intended).
3. ClickHouse persisted: asynchronous downstream outcome, **not** implied by Gateway ACK.

## Message states

`CREATED -> SENT -> WAIT_ACK -> ACKED` or `WAIT_ACK -> RETRY -> SENT` or `FAILED`.

- Pending messages are bounded by bytes and count per connection.
- Device reconnect may resend same `message_id` on lost ACK; this can produce duplicates.
- Kafka idempotent producer doesn't deduplicate device-level retransmissions.
- Worker concurrency must preserve required per-device order; key-based partitioning gives **per-partition log** order, not global order.
- Changing partition count may remap keys; preserve `sequence_number` for diagnostics.
- Plan stable business identity `(device_id, message_id)`, with explicit ClickHouse/query dedup policy.

## Open decisions to record as ADR

- ACK/NACK Protobuf envelope, status codes, timeouts, max retries.
- Frame length prefix format (proposed 4-byte big-endian), max size (proposed 64 KiB).
- Kafka producer retry/backoff and overloaded Gateway behavior.
- Exact ClickHouse duplicate handling and invalid-record/DLQ policy.
