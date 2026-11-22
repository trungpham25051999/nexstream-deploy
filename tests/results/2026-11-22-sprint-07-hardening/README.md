# Actual hardening evidence

H-D01..H-D06: 6 PASS. `analytics-final.log` covers retained-row identity policy, Kafka replay and a
short fixture TTL without changing normal retention. `dedup-measurements.json` preserves all timings.
`regressions.log`: Contracts 2/2, Publisher 7/7, Gateway/real PostgreSQL 8/8.
`compose-build.log`, `compose-build-processor-final.log`, `compose-e2e-final.log`: actual image builds,
full Agent TLS/auth/Kafka/ClickHouse/Query topology, two running Processor replicas and repeat bootstrap.
`environment.log`, `source-sha256.txt`: machine/tool metadata and final relevant source checksums.
Earlier `analytics.log` retains the UInt64 JSON-string assertion failure; final normalization preserves
the same expected surviving ID 2. Fixture datasets are retained for review; no production data was used.
