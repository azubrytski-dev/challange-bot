# Database Migrations

This directory contains database migration scripts that are automatically applied when the application starts.

## Migration System

The migration system tracks applied migrations in a `schema_migrations` table in the database, ensuring:

- **Idempotency**: Migrations are only applied once
- **Ordering**: Migrations are applied in version order
- **Audit Trail**: All migrations are logged with version, name, checksum, and timestamp

## Migration File Naming

Migration files must follow this naming convention:

```
{version}_{name}_{db_type}.sql
```

Examples:
- `001_initial_schema_sqlite.sql` - Initial schema for SQLite
- `001_initial_schema_postgres.sql` - Initial schema for PostgreSQL
- `002_add_language_column_sqlite.sql` - Add language column for SQLite
- `002_add_language_column_postgres.sql` - Add language column for PostgreSQL

### Version Format
- Use 3-digit zero-padded numbers: `001`, `002`, `003`, etc.
- Versions must be sequential (no gaps)

### Database Type
- `sqlite` - For SQLite databases
- `postgres` - For PostgreSQL databases

## Migration Table Schema

The `schema_migrations` table is automatically created and has the following structure:

```sql
CREATE TABLE schema_migrations (
    version TEXT NOT NULL PRIMARY KEY,  -- e.g., "001"
    name TEXT NOT NULL,                  -- e.g., "initial_schema"
    checksum TEXT NOT NULL,              -- SHA256 of migration SQL
    applied_at INTEGER NOT NULL          -- Unix timestamp
);
```

## How It Works

1. On application startup, the repository initializes the migration system
2. The `schema_migrations` table is created if it doesn't exist
3. All migration files matching the database type are loaded and sorted by version
4. Each migration is checked against the `schema_migrations` table
5. Pending migrations are applied in order
6. Applied migrations are recorded in `schema_migrations`

## Creating New Migrations

1. Create a new SQL file following the naming convention
2. Use the next sequential version number
3. Create separate files for SQLite and PostgreSQL if needed
4. Write idempotent SQL (use `IF NOT EXISTS` where possible)
5. Test the migration on a development database

### Example: Adding a New Column

**SQLite:**
```sql
-- 003_add_new_column_sqlite.sql
ALTER TABLE users ADD COLUMN new_field TEXT;
```

**PostgreSQL:**
```sql
-- 003_add_new_column_postgres.sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'new_field'
    ) THEN
        ALTER TABLE users ADD COLUMN new_field TEXT;
    END IF;
END $$;
```

## Backward Compatibility

For existing databases that were initialized with the old schema files (`mg_sqllite_init.sql` or `mg_postgre_init.sql`), the system will:

1. Apply the initial schema as migration `000` if no migrations have been applied
2. Then apply all numbered migrations in order

This ensures smooth transition from the old initialization system to the new migration system.

## Manual Migration Execution

If you need to check migration status or manually run migrations:

**Check applied migrations (SQLite):**
```sql
SELECT * FROM schema_migrations ORDER BY version;
```

**Check applied migrations (PostgreSQL):**
```sql
SELECT * FROM schema_migrations ORDER BY version;
```

## Troubleshooting

### Migration Already Applied Error
If you see an error about a migration already being applied, check the `schema_migrations` table. The migration system uses this table to track what's been applied.

### Column Already Exists (SQLite)
SQLite doesn't support `IF NOT EXISTS` for `ALTER TABLE ADD COLUMN`. The migration system handles this by:
1. Checking the migration log first (prevents re-running)
2. Catching "duplicate column" errors and logging them as warnings

### Migration Order Issues
Migrations must be applied in order. If migration `003` is applied but `002` is missing, the system will raise an error. Ensure all migration files are present and properly numbered.
