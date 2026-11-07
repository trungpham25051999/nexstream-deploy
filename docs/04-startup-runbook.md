# Local startup & smoke-test runbook

> **PLANNED ONLY.** This starter does not yet contain running C++ binaries, valid Compose manifests, Kafka topics or ClickHouse DDL.

## Startup order

1. Checkout a pinned version of `nexstream-contracts`; generate Protobuf code in dependent services.
2. In `nexstream-deploy`, start local Redpanda and ClickHouse after Compose configs exist.
3. Confirm Kafka topic `telemetry.events.v1`, partitions, retention and broker reachability.
4. Provision ClickHouse MergeTree table, Kafka Engine table, and Materialized View matching the chosen JSON event schema.
5. Build/start `nexstream-ingest`, confirm TCP listener, health and Kafka producer connectivity.
6. Run `nexstream-publisher` with a single message; inspect ACK, Kafka record and ClickHouse persistence.
7. Run `nexstream-processor` and inspect analytics output/alerts separately.
8. Start `nexstream-query`; verify HTTP query for a known event ID.

## Verify / record

- Record UTC time, Git SHAs and schema version, compiler/Docker versions.
- Capture exact commands and exit codes, redacting credentials.
- Compare publisher sent/ACKed/failed counts with Kafka and ClickHouse observations.
- Document delays between ACK and ClickHouse row visibility.

## Shutdown plan

Stop publisher; drain outstanding Gateway ACK/publish state; stop processor/query; stop infrastructure. Mark graceful drain as unverified until tested.

## Evidence template

| Date UTC | Component versions | Command | Expected | Observed | Pass/Fail |
|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | Not run | Not run |
