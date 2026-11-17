# Sprint 05 Report — TLS, Authentication & Credential Registry

Date: 2026-11-17  
Scope: Sprint 05 only

## Outcome

The Gateway authentication stub was replaced by PostgreSQL-backed asynchronous authentication.
The epoll Reactor performs no database I/O: bounded workers handle cache misses, and bounded
`eventfd` completions use stable connection tokens. Credentials are bound to agent/host/key and
stored as salted PBKDF2-HMAC-SHA256 verifiers, not plaintext.

HAProxy 2.9.12 terminated TLS 1.3 with runtime-only test certificate material. Correct chain and
hostname verification passed; wrong hostname and TLS 1.2 failed. A real PostgreSQL 16 instance
passed migration, authentication, revocation, outage and restart tests.

This Sprint is partial overall: no Monitoring Agent implementation repository exists, so OpenSSL
was the verified TLS client; the full Compose topology was not run because no Compose plugin exists.

## Required Sprint 04 review

- Completion overflow remains bounded and cannot create SUCCESS. A lost completion resolves only by
  timeout/non-success; existing overflow and late-token tests pass.
- Kafka timeout/uncertainty remains UNKNOWN. No ACK contract or Protobuf schema changed.
- Kafka pending memory remains bounded at 4,096 records/16 MiB plus librdkafka configured queue.
- No test proved a Sprint 04 defect, so Kafka behavior was not changed.

## Implemented

- Registry schema: `agents`, `agent_credentials`, durable `credential_change_events`, constrained
  states and trigger-based `NOTIFY`.
- Active/revoked/expired/not-before checks, exact agent/host binding and constant-time verifier
  comparison.
- Bounded LRU/TTL credential cache; bounded worker queue by attempts and secret bytes.
- Fresh-cache outage policy; cold/expired miss fail-closed.
- Separate bounded auth completion queue + eventfd and connection generation token.
- Dual-key rotation, LISTEN/NOTIFY invalidation and durable version reconciliation.
- HAProxy TLS 1.3-only development config, limits/deadlines and internal Compose networks.
- Unit, TCP, real PostgreSQL, outage/restart, concurrency and TLS positive/negative tests.

## Files created or modified

### `nexstream-ingest`

- Modified: `CMakeLists.txt`, `README.md`, `docs/{PROCESS,STATUS}.md`,
  `include/.../protocol_session.hpp`, `src/application/protocol_session.cpp`, Reactor/connection
  headers and sources, `src/bootstrap/main.cpp`, existing tests and test catalog.
- Created application ports: `application/{authenticator,credential_registry}.hpp`.
- Created infrastructure: `auth_completion_channel`, `credential_cache`,
  `authentication_service`, `postgres_credential_registry` headers/sources.
- Created tests: `tests/mock_authenticator.hpp`,
  `tests/unit/authentication_service_tests.cpp`,
  `tests/integration/postgres_registry_tests.cpp` and Sprint 05 evidence.

### `nexstream-deploy`

- Created migrations `postgres/migrations/{001_credential_registry,002_registry_role}.sql`.
- Created `haproxy/haproxy.cfg`, `docker-compose.sprint05.yml`, and
  `docs/security/SPRINT-05-SECURITY.md`.
- Updated README/status/project-status and created this report.

No Protobuf schema, ADR, Kafka ACK contract, remote or Sprint 06 code changed. No private key or
production credential was committed.

## Commands and evidence

Exact redacted commands are in
`nexstream-ingest/tests/results/2026-11-17-sprint-05/commands.txt`. Main commands:

```sh
cmake -S nexstream-ingest -B nexstream-ingest/build-s05-pg \
  -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON \
  -DCMAKE_PREFIX_PATH=<contracts> -DRDKAFKA_ROOT=<rdkafka> -DLIBPQ_ROOT=<libpq> \
  -DNEXSTREAM_POSTGRES_TEST_CONN=<redacted-local-conninfo>
cmake --build nexstream-ingest/build-s05-pg --parallel 2
ctest --test-dir nexstream-ingest/build-s05-pg --output-on-failure

docker stop nexstream-s05-postgres
NEXSTREAM_EXPECT_POSTGRES_UNAVAILABLE=1 ./nexstream_ingest_postgres_tests
docker start nexstream-s05-postgres
./nexstream_ingest_postgres_tests

docker run --rm haproxy:2.9.12-alpine haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg
openssl s_client ... -verify_hostname localhost -tls1_3
openssl s_client ... -verify_hostname wrong.example -verify_return_error -tls1_3
openssl s_client ... -tls1_2
```

Equivalent Release and ASan/UBSan builds were run. Temporary containers and TLS files were removed.

## Results

| Classification | Count | Detail |
|---|---:|---|
| PASS | 16 | TC-AUTH-001..016 |
| FAIL | 0 | final runs |
| BLOCKED | 1 | TC-AUTH-017 Monitoring Agent TLS client absent |
| NOT RUN | 1 | TC-AUTH-018 complete Compose topology |

- Debug: 8/8; Release: 8/8; ASan/UBSan: 8/8 CTest executables passed.
- PostgreSQL real integration passed; stopped DB fail-closed test and restart rerun passed.
- TLS valid verification exit 0; wrong hostname exit 1; TLS 1.2 exit 1.
- 100 concurrent cache-hit auth operations passed. This is not a benchmark.

## Errors found and fixed

1. Initial compile exposed a missing `<thread>` include and misleading single-line statements; they
   were corrected without changing behavior.
2. First auth unit run failed because the fixture TTL expired before the “fresh-cache outage” step
   and a cold 100-request PBKDF stress exceeded its fixture deadline. The test now refreshes the
   cache immediately before outage and warms the stress credential; production semantics were not
   weakened.
3. HAProxy validation first failed because the runtime PEM mode denied the container user and the
   standalone backend name was unresolved. Runtime test permissions were corrected; `init-addr`
   now permits config validation while Compose DNS still resolves the real backend.
4. Compose initially used an invalid libpq `password_file` keyword. It now uses a runtime
   `passfile=/run/secrets/pgpass` secret.

## Decisions

- PBKDF2-HMAC-SHA256 with per-key salt and minimum 100,000 iterations is available in the current
  OpenSSL dependency and avoids plaintext/reversible storage. Production may adopt Argon2id only
  through a reviewed ADR/dependency change.
- Fresh cached credentials may work during DB outage per ADR-015; misses and expired cache fail
  closed. Revocation is bounded by notification/reconciliation latency, not instantaneous.
- Notification payload contains key ID/version only, never secret/verifier. Durable versions repair
  missed NOTIFY events.
- Auth backpressure returns AUTH_RETRY_LATER and closes after response. It never falls back to a
  stub or permits pre-auth telemetry.
- PostgreSQL work is blocking only on bounded worker threads. Reactor ownership remains unchanged.

## Limits and incomplete items

- No Monitoring Agent code exists. OpenSSL verifies the TLS policy, but this is not proof of a
  production Agent implementation.
- Docker Compose plugin was unavailable, so the complete topology is NOT RUN. Config and boundaries
  were tested independently.
- PostgreSQL opens one connection per lookup; production pooling, statement timeout/cancellation,
  least-privilege login provisioning and HA require follow-up.
- No admin enrollment API, CSPRNG secret delivery workflow, audit export, rate limiting, TLS
  certificate automation, SASL Kafka, mTLS or public endpoint exists.
- Local revocation lag under 500 ms is fixture evidence, not a benchmark/SLO.
- Development HAProxy is a single point of failure. Backend isolation is represented by internal
  Compose networks but was not externally penetration-tested.

## Proposed next step

Do not begin Sprint 06 implicitly. First review the missing Agent TLS implementation, production
credential provisioning, PG pool/timeouts, revocation SLO and a host with Docker Compose. Then
follow the approved roadmap under a separately authorized Sprint.
