-- Setup migration log for existing production SQLite database
-- Run this script manually on your production database to initialize the migration system
-- This marks migrations 001 and 002 as already applied

-- Create migration tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at INTEGER NOT NULL
);

-- Mark initial schema migration as applied (version 001)
-- Checksum: SHA256 of 001_initial_schema_sqlite.sql
INSERT OR IGNORE INTO schema_migrations(version, name, checksum, applied_at)
VALUES(
    '001',
    'initial_schema',
    '4ec34620b21eb2dd21d660359f0baa6f4ec92fb7dc62ec0b7d66dcf5ed19175c',
    strftime('%s', 'now')
);

-- Mark language column migration as applied (version 002)
-- Checksum: SHA256 of 002_add_language_column_sqlite.sql
-- This assumes your production database already has the language column
INSERT OR IGNORE INTO schema_migrations(version, name, checksum, applied_at)
VALUES(
    '002',
    'add_language_column',
    '695f4051ed6d96119b24f26c71dacc134bcd39d4ab20ef28c55ecff846f03cb1',
    strftime('%s', 'now')
);

-- Verify the setup
SELECT * FROM schema_migrations ORDER BY version;
