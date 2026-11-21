# Actual Sprint 07 evidence

`agent-e2e.log`: manual Docker full Agent TLS/PG/Kafka/ClickHouse/Query path.
`compose-build-final.log`, `compose-processor-final.log`, `compose-e2e-final.log`: actual images and full topology.
`malformed-recovery.log`: quarantine at source offset 12 and subsequent valid identity.
`duplicate-counts.json`: 3 raw rows versus 2 logical identities.
`gateway-regression-final.log`: final 8/8 Gateway regression (after restoring local PG fixture).
Earlier Compose failure is retained in `compose-e2e.log`.
Case inventory: ../../TEST_CASES.md (7 PASS, 1 NOT RUN).
