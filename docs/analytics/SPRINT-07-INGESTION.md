# Sprint 07 analytics storage and delivery

Current hardening evidence and priority findings: `../reports/SPRINT-07-HARDENING-REPORT.md`.
Duplicate/conflicting identity, exact tie, time predicate, actual Kafka replay and short fixture TTL
were verified. Dedup cost was measured on 100000 physical rows / 50000 identities; full samples are
in `tests/results/2026-11-22-sprint-07-hardening/dedup-measurements.json` from repository root.
TTL changes were confined to `nexstream_hardening_fixture`; seven-day raw retention was unchanged.
Processor recovery now follows ADR-017; diagnostic files are not a distributed checkpoint authority.

Kafka JSON v1 is documented in `nexstream-contracts/docs/KAFKA-JSON-V1.md` from the existing
Gateway serializer. Earlier architecture examples using device_id/sequence_number are illustrative,
not the deployed v1 event. Current Kafka key and API identity are host_id.

`clickhouse/001_telemetry.sql` creates Kafka Engine → materialized view → raw MergeTree and a
query-time dedup view. Run with `clickhouse-client --multiquery < clickhouse/001_telemetry.sql`.
CREATE IF NOT EXISTS is repeatable initialization, not an automatic migration of existing objects.
Future changes need numbered ALTER/recreation migrations and consumer-offset review.

Storage uses DateTime64(3, UTC), Float64 CPU, UInt64 memory. Millisecond source time is preserved;
ingested_at records view insertion time. Daily partitions and `(host_id,sampled_at,message_id)` order
support host/time scans. Experimental TTL is seven days after sample time; merge-driven deletion
does not guarantee an exact wall-clock removal boundary. Old arriving data may expire immediately.

Raw duplicates remain observable. The dedup view groups `(host_id,message_id)` and picks the earliest
ingested row, breaking ties by the complete data tuple. Stable identity must mean identical payload.
Conflicting identity reuse is a producer violation; query dedup has a deterministic winner.
No ReplacingMergeTree immediate uniqueness assumption is used. Grouping has bounded query memory
and execution time but may be expensive for a large retained history; benchmark before scaling.

Kafka group `nexstream.clickhouse.v1` is independent from `nexstream.processor.v1`.
ClickHouse ingestion can replay after failure. Gateway SUCCESS proves Kafka delivery under producer
configuration, not ClickHouse visibility. Single-node Redpanda evidence is not production HA evidence.

Semantic-invalid events are filtered from raw; Processor independently emits metadata DLQ events.
Syntactically malformed JSON uses `kafka_handle_error_mode=stream`. A second MV writes bounded
error/raw-prefix and source topic/partition/offset into `telemetry_parse_errors`, while the raw MV
excludes `_error` rows. Test offset 12 (`not-json`) was quarantined and offset 13 ingested normally.
Error prefix is capped at 64 KiB and error detail at 4096 bytes; Kafka retains the full source record.
Quarantine TTL is seven days after ingestion. Replays may duplicate quarantine rows.

Development topology: `docker-compose.sprint07.yml`, build from parent six-repo workspace with
`Dockerfile.sprint07`. Provide all runtime secret files referenced by the manifest. Provision dev-agent /
dev-host / dev-key in PostgreSQL using a generated verifier; no sample production secret is supplied.
The Query binary binds loopback inside its container; inspect through `docker exec` until a reviewed
listen-address configuration is added. The bootstrap query_dev account is development-only and needs
a dedicated least-privilege reader before production. Compose build and complete E2E passed with
locally downloaded v2.29.7. Secret PG passfile is copied with mode 0600 inside Gateway before launch.
Gateway uses explicit `NEXSTREAM_LISTEN_ADDRESS=0.0.0.0` only on isolated internal networks.

References: [ClickHouse Kafka Engine guide](https://github.com/ClickHouse/clickhouse-docs/blob/main/docs/integrations/data-ingestion/kafka/kafka-table-engine.md),
[HTTP interface](https://clickhouse.com/docs/interfaces/http). Version-specific behavior was checked
against the local 24.3.18.7 server; current documentation alone is not runtime proof.
