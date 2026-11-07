# Observability and operational signals

**State:** proposed instrumentation.

| Metric name | Type | Meaning |
|---|---|---|
| `nexstream_ingest_connections_active` | gauge | open TCP connections |
| `nexstream_ingest_messages_received_total` | counter | frames received |
| `nexstream_ingest_messages_rejected_total{reason}` | counter | invalid/oversize frames |
| `nexstream_ingest_pending_bytes` | gauge | buffered/in-flight bytes |
| `nexstream_ingest_kafka_delivery_total{result}` | counter | delivery results |
| `nexstream_ingest_ack_duration_seconds` | histogram | time to device ACK |
| `nexstream_processor_records_processed_total{result}` | counter | processor outcomes |
| `nexstream_query_request_duration_seconds` | histogram | HTTP request latency |

Avoid high-cardinality Prometheus labels such as `device_id`, `message_id` or client IP.

## Logs

Emit structured events for `connection_open`, `connection_close`, `frame_rejected`, `decode_failed`, `kafka_failed`, `ack_sent`, `shutdown`. Include component version and bounded error codes. Sanitize credentials/private telemetry.

## Alerts to design

Kafka failure rate, buffer pressure, ClickHouse ingestion lag versus topic retention, Gateway unavailability, query latency.
