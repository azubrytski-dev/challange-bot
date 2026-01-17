# Production Migration Setup Guide

Since your production database is already initialized, you need to manually set up the migration log table to mark existing migrations as applied.

## Steps

### 1. Remove Old Files (Optional)

The following files are no longer needed and can be removed:
- `app/storage/mg_postgre_init.sql` (replaced by migration system)
- `app/storage/mg_sqllite_init.sql` (replaced by migration system)
- `app/storage/migrate_add_language_sqlite.sql` (replaced by migration system)
- `app/storage/migrate_add_language_postgres.sql` (replaced by migration system)

### 2. Calculate Migration Checksums

Before running the setup scripts, you need to calculate the SHA256 checksums of your migration files:

**For SQLite:**
```bash
# Calculate checksum for 001_initial_schema_sqlite.sql
sha256sum app/storage/migrations/001_initial_schema_sqlite.sql

# Calculate checksum for 002_add_language_column_sqlite.sql
sha256sum app/storage/migrations/002_add_language_column_sqlite.sql
```

**For PostgreSQL:**
```bash
# Calculate checksum for 001_initial_schema_postgres.sql
sha256sum app/storage/migrations/001_initial_schema_postgres.sql

# Calculate checksum for 002_add_language_column_postgres.sql
sha256sum app/storage/migrations/002_add_language_column_postgres.sql
```

Or use Python:
```python
import hashlib
with open('app/storage/migrations/001_initial_schema_sqlite.sql', 'r') as f:
    print(hashlib.sha256(f.read().encode('utf-8')).hexdigest())
```

### 3. Update Setup Scripts

Edit the setup scripts and replace `CALCULATE_FROM_FILE` placeholders with the actual checksums:

- `app/storage/migrations/setup_production_migration_log_sqlite.sql`
- `app/storage/migrations/setup_production_migration_log_postgres.sql`

### 4. Run Setup Script on Production

**For SQLite:**
```bash
sqlite3 /path/to/production/bot.db < app/storage/migrations/setup_production_migration_log_sqlite.sql
```

**For PostgreSQL:**
```bash
psql $DATABASE_URL -f app/storage/migrations/setup_production_migration_log_postgres.sql
```

### 5. Verify Setup

Check that migrations are recorded:

**SQLite:**
```sql
SELECT * FROM schema_migrations ORDER BY version;
```

**PostgreSQL:**
```sql
SELECT * FROM schema_migrations ORDER BY version;
```

You should see:
- `001` - `initial_schema`
- `002` - `add_language_column`

### 6. Deploy Updated Code

After setting up the migration log, deploy the updated code. The migration system will:
- Detect that migrations 001 and 002 are already applied
- Skip them automatically
- Apply any future migrations (003, 004, etc.) in order

## Important Notes

1. **Backup First**: Always backup your production database before running any migration setup scripts.

2. **Checksum Verification**: The migration system uses checksums to verify migration integrity. Make sure the checksums in the setup scripts match the actual migration files.

3. **Language Column**: Ensure your production database already has the `language` column in the `chat_state` table. If not, add it manually before running the setup script.

4. **No Downtime**: This setup process doesn't require downtime. The migration log table is created and populated, but no schema changes are made.

## Troubleshooting

If you see errors about migrations already being applied:
- Check the `schema_migrations` table
- Verify the version numbers match
- Ensure checksums are correct

If the language column doesn't exist:
- Add it manually: `ALTER TABLE chat_state ADD COLUMN language TEXT NOT NULL DEFAULT 'en';`
- Then run the setup script
