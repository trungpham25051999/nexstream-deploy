BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nexstream_registry_reader') THEN
        CREATE ROLE nexstream_registry_reader NOLOGIN;
    END IF;
END $$;
GRANT USAGE ON TYPE credential_status TO nexstream_registry_reader;
GRANT SELECT ON agents, agent_credentials, credential_change_events TO nexstream_registry_reader;
COMMIT;
