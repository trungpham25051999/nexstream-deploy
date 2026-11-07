# Failure & recovery test plan

**State:** intended; fault injection results not available yet.

| Failure | Expected control | Verification |
|---|---|---|
| TCP disconnect mid-frame | release FD, drop partial buffer | reconnect with same message ID if unacked |
| malformed Protobuf | reject without crash | NACK if message identity is available |
| frame length too large | bound memory before allocation | correct close/reject behavior |
| Kafka down | bounded producer queue, backpressure, no false ACK | restore broker and inspect retries |
| Kafka commit but device ACK lost | duplicate possible after resend | measure duplicate IDs |
| ClickHouse down | consumer lag grows; recover while Kafka retains records | restore CH; inspect missing/duplicate IDs |
| Kafka partition leader transition | producer retry with configured semantics | no ACK before delivery success |
| processor crash | group rebalance; possible replay | validate alert idempotency |
| gateway crash | client connection drops | reconnect and replay unacked IDs |
| hot Kafka partition | uneven lag | inspect partition distribution |

## Required metrics per scenario

`sent`, `acked`, `nacked`, `retried`, `dropped`, `ClickHouse visible`, `duplicate IDs`, `Kafka lag`, `p95/p99 ACK latency`, `RSS`, `CPU`.

No claims of high availability or zero loss until tests demonstrate recovery within documented fault model.
