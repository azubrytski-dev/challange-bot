-- Setup migration log for existing production PostgreSQL database
-- Run this script manually on your production database to initialize the migration system
-- This marks migrations 001 and 002 as already applied

-- Create migration tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at BIGINT NOT NULL
);

-- Mark initial schema migration as applied (version 001)
-- Checksum: SHA256 of 001_initial_schema_postgres.sql
INSERT INTO schema_migrations(version, name, checksum, applied_at)
VALUES(
    '001',
    'initial_schema',
    '73a829afcf9882f8f79fe2dee61b8e12d97cfa58e32fec483be9373c9cc7f6af',
    EXTRACT(EPOCH FROM NOW())::BIGINT
)
ON CONFLICT (version) DO NOTHING;

-- Mark language column migration as applied (version 002)
-- Checksum: SHA256 of 002_add_language_column_postgres.sql
-- This assumes your production database already has the language column
INSERT INTO schema_migrations(version, name, checksum, applied_at)
VALUES(
    '002',
    'add_language_column',
    '238920afe473908e51e5cfa09514b8049d087e462b801a91e4c88768ba2c474a',
    EXTRACT(EPOCH FROM NOW())::BIGINT
)
ON CONFLICT (version) DO NOTHING;

-- Verify the setup
SELECT * FROM schema_migrations ORDER BY version;
