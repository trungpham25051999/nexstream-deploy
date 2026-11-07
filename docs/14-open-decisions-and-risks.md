# Architecture Decisions & Risk Register

## Accepted decisions
| ID | Decision |
|---|---|
| ADR-001 | Multi-repository services, independent release lifecycle |
| ADR-002 | Clean/Hexagonal code boundaries per service |
| ADR-003 | C++20 for applications, CMake target-based builds |
| ADR-004 | Gateway decodes Protobuf and outputs Kafka JSON events |
| ADR-005 | ClickHouse consumes Kafka directly using Kafka Engine + MV |
| ADR-006 | NexStream naming conventions |
| ADR-007 | Short-lived branches and per-repo CI |

## Proposed, not final
| Item | Consequence / validation |
|---|---|
| Length-prefix = uint32 BE, max 64 KiB | Cross-language framing tests and allocation controls |
| TCP handshake / auth / TLS | Needed for any untrusted device deployments |
| ACK/NACK schema / timeouts / limits | Required for reliable client retransmission |
| Broker topic partitions and RF | Select from load benchmark and HA requirements |
| Kafka/ClickHouse format and parse failures | Verify behavior with pinned ClickHouse version |
| Dedup at ClickHouse query layer | Ensure retransmission does not distort reporting |
| Processor outputs and alert schema | Define meaningful anomaly case first |

## Top risks
1. Unbounded queues or pending Kafka producer messages -> process OOM.
2. ACK incorrectly tied to socket write, rather than broker delivery.
3. Duplicate data from producer replay or ClickHouse Kafka consumer retries.
4. Multi-worker out-of-order completion per device.
5. Misconfigured ClickHouse table/JSON conversion or deserialization errors.
6. Scaling load generator on same host as targets contaminating performance results.
7. Architecture drift across six independently versioned repositories.

## ADR state discipline
Use `proposed`, `accepted`, `superseded` and record date, context, alternatives, impacts and validation plan. An architecture diagram alone is not sufficient approval.

## Sprint 07 hardening implementation review

ADR-017 records implemented bounded partition recovery. Local multi-owner correctness is exercised;
retained offset-zero history and the 100000-offset ceiling remain a P1 operational gate before fleet use.
This does not amend the accepted baseline ADRs or claim architecture review sign-off for production.
