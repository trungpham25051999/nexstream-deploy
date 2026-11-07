# Implementation Roadmap & Definition of Done

## Milestone 0 — Architecture and contracts (contracts/deploy)
- [ ] ADRs and wire envelope approved; semantic versioning policy.
- [ ] Protobuf generated C++ build reproducible; compatibility tests.
- [ ] Local deployment prerequisites documented.

## Milestone 1 — Vertical TCP slice (publisher/ingest)
- [ ] Publisher sends one framed Protobuf telemetry record.
- [ ] Ingest parses fragmented and merged frames, validates and returns a simulated ACK in test-only mode.
- [ ] Unit tests for frame logic and malformed inputs; CI build.

## Milestone 2 — Kafka integration (ingest/deploy)
- [ ] Ingest async producer, bounded queue, Kafka delivery reports and production ACK semantics.
- [ ] Integration test with Redpanda and error/reconnect handling.

## Milestone 3 — ClickHouse ingestion (deploy)
- [ ] Kafka Engine + MV + MergeTree schema for `telemetry.events.v1`.
- [ ] Verified end-to-end record by `message_id`; measure visibility delay.

## Milestone 4 — Processor / Query
- [ ] Worker independent consumer group and derived alert event.
- [ ] Query API with limits, error handling and integration tests.

## Milestone 5 — Failure and scaling experiments
- [ ] Kafka outage, ClickHouse outage, gateway restart, malformed Protobuf, reconnect storms.
- [ ] 1/2/3 gateway replica comparison; throughput, latency and memory metrics.
- [ ] Reproducible benchmark methodology and measurements published.

## Service-level Definition of Done
Architecture alignment, pinned contracts, passing builds/tests, documented handling of errors and backpressure, logs/metrics, reproducible runbook, reviewed change and CI evidence. Never mark tests run if they were not run.
