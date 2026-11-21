# ADR-016 — Sprint 07 analytics implementation decisions

Date: 2026-11-21. Status: implemented development choices; architecture review pending.
Existing accepted ADRs and Protobuf v1 are unchanged.

The explicit Sprint 07 objective selects Kafka Engine/MV ingestion and host/time Query APIs.
Use raw MergeTree plus deterministic query-time identity grouping instead of relying on background
ReplacingMergeTree uniqueness. Preserve sampled_at milliseconds and separate ingested_at.
Experimental raw retention is seven days by sample time, enforced during merges.

Use Kafka stream-error mode and a separate quarantine MV for syntactic JSON failures, preserving
source offsets and bounded error/payload prefixes. This keeps valid subsequent records moving.
MV writes are at-least-once and quarantine duplicates remain possible.

Query uses ClickHouse HTTP typed parameters, a synchronous bounded HTTP adapter, and explicit time,
row and memory limits. This favors a testable small service over unmeasured HTTP concurrency.

Processor tracks bounded local streak/identity state. Successful alert/DLQ delivery precedes atomic
checkpoint and input commit. Local checkpoint simplifies one-worker restart; distributed partition
state migration is deferred and not claimed. Length-prefixed alert identity prevents delimiter collisions.

Evidence and incomplete fault checks: `../reports/SPRINT-07-REPORT.md`.
