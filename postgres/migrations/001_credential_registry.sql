BEGIN;

CREATE TYPE credential_status AS ENUM ('active', 'revoked', 'expired');

CREATE TABLE agents (
    id uuid PRIMARY KEY,
    agent_id text NOT NULL UNIQUE CHECK (length(agent_id) BETWEEN 1 AND 128),
    host_id text NOT NULL CHECK (length(host_id) BETWEEN 1 AND 128),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (agent_id, host_id)
);

CREATE TABLE credential_change_events (
    version bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key_id text NOT NULL CHECK (length(key_id) BETWEEN 1 AND 128),
    event_type text NOT NULL CHECK (event_type IN ('created', 'rotated', 'revoked', 'expired')),
    changed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE agent_credentials (
    key_id text PRIMARY KEY CHECK (length(key_id) BETWEEN 1 AND 128),
    agent_id uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    secret_salt bytea NOT NULL CHECK (octet_length(secret_salt) >= 16),
    secret_verifier bytea NOT NULL CHECK (octet_length(secret_verifier) = 32),
    iterations integer NOT NULL CHECK (iterations BETWEEN 100000 AND 2000000),
    status credential_status NOT NULL DEFAULT 'active',
    not_before timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    change_version bigint NOT NULL REFERENCES credential_change_events(version),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (expires_at > not_before)
);

CREATE INDEX agent_credentials_agent_idx ON agent_credentials(agent_id);
CREATE INDEX agent_credentials_active_idx ON agent_credentials(key_id)
    WHERE status = 'active';

CREATE FUNCTION notify_credential_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify('credential_changes', NEW.key_id || ':' || NEW.change_version::text);
    RETURN NEW;
END;
$$;

CREATE TRIGGER agent_credentials_notify
AFTER INSERT OR UPDATE OF status, secret_verifier, not_before, expires_at, change_version
ON agent_credentials FOR EACH ROW EXECUTE FUNCTION notify_credential_change();

COMMIT;

-- Provisioning is intentionally outside the Gateway. Generate a random secret in a trusted
-- enrollment tool, store only PBKDF2-HMAC-SHA256(salt, secret, iterations), and reveal the secret
-- once. Rotation inserts a second active key_id; revoke the old key after the transition window.
