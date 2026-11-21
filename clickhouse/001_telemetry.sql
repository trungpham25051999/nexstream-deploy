CREATE DATABASE IF NOT EXISTS nexstream;

-- Experimental raw retention. TTL deletion occurs during merges, not at an exact deadline.
CREATE TABLE IF NOT EXISTS nexstream.telemetry_raw
(
    schema_version UInt8,
    host_id String,
    message_id String,
    sampled_at DateTime64(3, 'UTC'),
    ingested_at DateTime64(3, 'UTC') DEFAULT now64(3),
    cpu_usage_percent Float64,
    memory_used_bytes UInt64,
    memory_total_bytes UInt64
)
ENGINE = MergeTree
PARTITION BY toDate(sampled_at)
ORDER BY (host_id, sampled_at, message_id)
TTL toDateTime(sampled_at) + INTERVAL 7 DAY DELETE;

-- Raw rows preserve replays. Query-time grouping provides logical identity deduplication.
-- Earliest ingestion wins if an invalid producer reuses identity with different values.
CREATE VIEW IF NOT EXISTS nexstream.telemetry_deduplicated AS
SELECT host_id, message_id, winner.1 AS sampled_at, winner.2 AS ingested_at,
    winner.3 AS cpu_usage_percent, winner.4 AS memory_used_bytes,
    winner.5 AS memory_total_bytes
FROM (SELECT host_id, message_id,
    argMin(tuple(sampled_at, ingested_at, cpu_usage_percent, memory_used_bytes, memory_total_bytes),
           tuple(ingested_at, sampled_at, cpu_usage_percent, memory_used_bytes, memory_total_bytes)) AS winner
    FROM nexstream.telemetry_raw GROUP BY host_id, message_id);

CREATE TABLE IF NOT EXISTS nexstream.telemetry_kafka
(
    schema_version UInt8, host_id String, message_id String,
    sample_timestamp_ms Int64, cpu_usage_percent Float64,
    memory_used_bytes UInt64, memory_total_bytes UInt64
)
ENGINE = Kafka SETTINGS
    kafka_broker_list = 'redpanda:9092',
    kafka_topic_list = 'telemetry.events.v1',
    kafka_group_name = 'nexstream.clickhouse.v1',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_max_block_size = 1000,
    kafka_handle_error_mode = 'stream',
    kafka_skip_broken_messages = 0;

CREATE TABLE IF NOT EXISTS nexstream.telemetry_parse_errors
(
    ingested_at DateTime64(3, 'UTC'), source_topic String, source_partition UInt64,
    source_offset UInt64, error String, raw_prefix String
)
ENGINE = MergeTree ORDER BY (source_topic, source_partition, source_offset)
TTL toDateTime(ingested_at) + INTERVAL 7 DAY DELETE;

CREATE MATERIALIZED VIEW IF NOT EXISTS nexstream.telemetry_error_ingestion
TO nexstream.telemetry_parse_errors AS
SELECT now64(3) AS ingested_at, _topic AS source_topic, _partition AS source_partition,
    _offset AS source_offset, substring(_error, 1, 4096) AS error,
    substring(_raw_message, 1, 65536) AS raw_prefix
FROM nexstream.telemetry_kafka WHERE _error != '';

CREATE MATERIALIZED VIEW IF NOT EXISTS nexstream.telemetry_ingestion TO nexstream.telemetry_raw AS
SELECT schema_version, host_id, message_id,
    fromUnixTimestamp64Milli(sample_timestamp_ms, 'UTC') AS sampled_at,
    now64(3) AS ingested_at, cpu_usage_percent, memory_used_bytes, memory_total_bytes
FROM nexstream.telemetry_kafka
WHERE _error = '' AND schema_version = 1 AND length(host_id) BETWEEN 1 AND 128
    AND length(message_id) BETWEEN 1 AND 128 AND sample_timestamp_ms > 0
    AND isFinite(cpu_usage_percent) AND cpu_usage_percent BETWEEN 0 AND 100
    AND memory_total_bytes > 0 AND memory_used_bytes <= memory_total_bytes;
