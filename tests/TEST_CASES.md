# Sprint 07 test inventory

| ID | Case | Final status | Evidence |
|---|---|---|---|
| D01 | DDL executed on ClickHouse 24.3.18.7 | PASS | SQL execution recorded in report |
| D02 | Repeat same bootstrap SQL | PASS | second successful invocation |
| D03 | Kafka Engine/MV replay mapping: 3 raw / 2 identities | PASS | duplicate-counts.json |
| D04 | Agent TLS → PG auth → Kafka → CH → Query | PASS | agent-e2e.log |
| D05 | Compose build/up and full Agent pipeline | PASS | compose-build-final.log, compose-e2e-final.log |
| D06 | Syntactically malformed JSON quarantine/recovery in CH | PASS | malformed-recovery.log |
| D07 | Seven-day TTL elapsed retention experiment | NOT RUN | not observed over seven days |
| D08 | Topic bootstrap script rerun inside Compose | PASS | compose-e2e-final.log |

7 PASS, 0 FAIL, 0 BLOCKED, 1 NOT RUN. Compose v2.29.7 was downloaded locally and used for the final run.

## Sprint 07 hardening

| ID | Case | Status | Actual evidence in results/2026-11-22-sprint-07-hardening/ |
|---|---|---|---|
| H-D01 | Identical duplicate, payload conflict, tie and canonical time predicate | PASS | analytics-final.log |
| H-D02 | Actual Kafka replay: 3 physical records / 1 canonical identity | PASS | analytics-final.log |
| H-D03 | Five-second fixture TTL: expired removed/live retained; raw seven-day policy unchanged | PASS | analytics-final.log |
| H-D04 | Defined 100000-row/50000-ID dedup cost, raw comparison and real timings | PASS | dedup-measurements.json |
| H-D05 | Contracts 2/2, Publisher 7/7, Gateway/real PG 8/8 regressions | PASS | regressions.log |
| H-D06 | Full Compose, two live Processor replicas, inspected memory/pid budgets | PASS | compose-build.log, compose-e2e-final.log |

6 PASS, 0 FAIL, 0 BLOCKED, 0 NOT RUN. H-D03 exercises the retention mechanism using the explicitly
authorized short fixture; it does not claim an elapsed seven-day soak or background-deletion SLO.
Across repositories: 31 required PASS; supplementary H-QX1 TSan remains NOT RUN.
