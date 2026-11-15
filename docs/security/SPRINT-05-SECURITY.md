# Sprint 05 security architecture

## Trust boundaries

`verified TLS client → HAProxy TLS 1.3 → private backend network → Gateway → PostgreSQL registry`

HAProxy owns server TLS termination. Clients must validate both certificate chain and hostname;
there is no insecure-skip mode. The plaintext Gateway port is an internal backend and must not be
published. API credentials provide application identity after TLS; neither layer replaces the
other.

## Credential model

Each Agent has a unique `agent_id`, authorized `host_id`, and one or more `key_id` credentials.
PostgreSQL stores a random salt and PBKDF2-HMAC-SHA256 verifier (minimum 100,000 iterations), never
the API secret. Auth requires exact key, agent and host binding plus active/not-before/expiry checks.
Rotation inserts a second active key and revokes the old key after the transition window.

Provisioning is deliberately not implemented in the Gateway. A trusted enrollment system must
generate a high-entropy secret, derive the verifier, deliver the secret once, and protect audit and
operator access. Sample values in tests are non-production fixtures.

## Nonblocking Gateway path

The Reactor performs bounded cache lookup only. Cold misses enter a bounded queue by count and
secret bytes. Worker threads perform libpq calls and PBKDF2 checks. A bounded completion queue plus
`eventfd` returns `(connection_id,generation)` and result to the Reactor; workers never retain raw
connection pointers. Queue exhaustion returns AUTH_RETRY_LATER. Registry outage permits only a
fresh cache hit; cold or expired entries fail closed.

## Revocation

Credential mutations append a durable monotonic `credential_change_events.version`. A trigger sends
`NOTIFY credential_changes` with `key_id:version`. The listener invalidates the matching cache key;
periodic max-version reconciliation clears all cached entries after missed notifications. The local
fixture observed propagation below 500 ms, but this is not a production SLO or benchmark.

## Bounds

| Resource | Default |
|---|---:|
| Auth workers | 4 |
| Queued cache misses | 1,024 |
| Queued secret bytes | 512 KiB |
| Cache entries | 4,096 |
| Cache TTL | 5 seconds |
| Reconciliation interval | 1 second |
| Auth completion entries | 4,096 |
| HAProxy connections | 2,048 global / 1,024 frontend |
| HAProxy client/server deadline | 12 seconds |

## Current limitations

- Monitoring Agent code does not exist; OpenSSL was the verified TLS reference client.
- Development HAProxy uses a single instance and runtime-provided certificate; no ACME/HSM/secret
  manager integration exists.
- PostgreSQL client connections are opened per lookup. The queue is bounded, but a production pool,
  query cancellation and server-side statement timeout need review.
- No production authorization admin API, audit export, rate limiter, TLS client certificate,
  certificate rotation automation or public endpoint exists.
