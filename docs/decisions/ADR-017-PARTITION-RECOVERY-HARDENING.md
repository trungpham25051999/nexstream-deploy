# ADR-017 — Partition ownership and bounded committed-prefix recovery

Date: 2026-11-22. Status: implemented for bounded development operation; production-scale review required.
This records the implementation choice authorized by Sprint 07 Hardening. Accepted baseline ADRs and
Protobuf/Kafka event/alert v1 schemas are unchanged.

## Problem

The previous local evaluator checkpoint had no authoritative association with group/topic/partition/
offset. Restoring it after reassignment could use another partition's state or a cursor inconsistent
with Kafka. Sharing a local file/volume between replicas also created lock contention, not state transfer.

## Decision

Maintain one application `PartitionState` per assigned `(topic,partition)`. On assignment resolve the
group's committed **next** offset and replay source offsets `[0,committed_next)` in order, without
publishing alerts/DLQ or committing during replay. Live records then publish all required outputs,
write a diagnostic file and await commit of their next offset on an owned result queue (three-second
application deadline). The local file is never loaded
as a recovery authority. Revocation drops the entire former assignment; reassignment rebuilds it.

Kafka offset metadata contains a printable hex encoding of algorithm version and threshold profile.
An existing nonzero cursor with unknown/different metadata fails closed. Kafka itself scopes offsets
by consumer group/topic/partition. Every instance of a deployment group must use the same profile;
this is not a distributed consensus protocol for simultaneous brand-new conflicting configurations.

All state and consumer callbacks run on one polling thread. Delivery callbacks are dispatched by its
producer flush/poll calls and own independent correlation data. A lost assignment prevents commit;
generation/coordinator rejection also stops the worker. An idle member with zero partitions remains
healthy. Owned partition count is bounded to 16, state to 128 hosts and 16 recent IDs per host/partition.

## Preconditions and bounds

- Source topic is the v1 nontransactional, noncompacted, host-key-affine log; partition count is stable.
- Prefix must be retained from offset zero. Missing prefix or an offset gap fails closed.
- At most 100000 committed-prefix offsets and 30 seconds of recovery per partition are supported.
- Assignment establishment, stalled input progress and reconnect attempts have bounded time budgets.
- Different owners may publish the same uncommitted alert during failure windows. Stable alert IDs
  support downstream deduplication; delivery is at-least-once, not exactly-once.

## Alternatives and production limit

A compacted Kafka state changelog plus fenced ownership/atomic state-cursor publication would support
longer retained histories. Shared files alone do not solve fencing/cursor atomicity. Bounded replay was
chosen here to obtain a deterministic, dependency-free correctness baseline with real multi-instance
tests. It is intentionally fail-closed rather than silently resetting state when history is missing.
Before prolonged/high-rate deployment, design and review durable partition snapshots/changelog and
compaction recovery. The 100000-offset/retention limits are an open **P1 operational constraint**.

Legacy groups need a reviewed migration: preserve old offsets/files for audit and choose a new group
for deliberate replay, or implement a reviewed state migration. No script automatically resets offsets.
Do not change thresholds in an active group or increase source partition count without migration review.

## Evidence

`../reports/SPRINT-07-HARDENING-REPORT.md`: two active owners, a third idle member, SIGKILL takeover,
config mismatch, output-success/checkpoint-failure duplicates, missing-prefix rejection and real broker faults.
[librdkafka API](https://docs.confluent.io/platform/current/clients/librdkafka/html/rdkafka_8h.html)
documents assignment callbacks, committed next offsets and synchronous commits; behavior was exercised
with local librdkafka 2.0.2/Redpanda v24.3.18.
