# Scaling & benchmark methodology

**State:** capacity estimates, not measured performance.

- Offered message rate `M = devices × messages_per_device_per_second`.
- Application payload bandwidth `B ≈ M × avg_payload_bytes` (wire, replication, storage overhead excluded).
- Example: 10,000 devices × 0.2 msg/s = 2,000 messages/s; at 512 bytes payload ≈ 1.024 MB/s payload-only.

| Layer | Scale axis | Key limit |
|---|---|---|
| Publisher | more test processes | test client CPU/network |
| Gateway | more independent replicas behind L4 LB | FD/RAM/CPU, TCP connection distribution |
| Kafka | more brokers and partition balancing | disk/network/replication |
| Processor | more consumers in same group | partitions/hot keys |
| ClickHouse Kafka Engine + MV | tuning consumers/ingestion | database CPU/memory/merge pressure |
| Query | more stateless replicas | ClickHouse query cost |

## Benchmark protocol

1. Pin hardware, kernel, compiler, dependency versions and test data schema.
2. Sweep connections (100, 1k, 10k only as supported), payload size and message rates separately.
3. Report offered and successful msg/s, p50/p95/p99 ACK latency, timeouts, Kafka lag and CH insert delay.
4. Record CPU, memory, file descriptors and network throughput per component.
5. Repeat runs and compare 1/2/3 Gateway instances with downstream capacity controlled.
6. Document point of saturation and bottleneck evidence. **Do not invent benchmark results.**
