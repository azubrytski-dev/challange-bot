"""
Database migration system with migration log tracking.

Tracks applied migrations in a `schema_migrations` table to ensure
idempotent and ordered migration execution.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Migration:
    """Represents a database migration."""

    version: str
    name: str
    sql: str

    @property
    def checksum(self) -> str:
        """Calculate SHA256 checksum of migration SQL."""
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


class MigrationRunner(Protocol):
    """Protocol for database-specific migration runners."""

    def ensure_migrations_table(self) -> None:
        """Create migrations tracking table if it doesn't exist."""
        ...

    def get_applied_migrations(self) -> Sequence[str]:
        """Get list of applied migration versions."""
        ...

    def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration and record it in the log."""
        ...


class SQLiteMigrationRunner:
    """Migration runner for SQLite databases."""

    def __init__(self, connection) -> None:
        self._con = connection

    def ensure_migrations_table(self) -> None:
        """Create migrations tracking table if it doesn't exist."""
        self._con.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT NOT NULL PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at INTEGER NOT NULL
            )
            """
        )
        self._con.commit()

    def get_applied_migrations(self) -> Sequence[str]:
        """Get list of applied migration versions."""
        rows = self._con.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        return [row["version"] for row in rows]

    def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration and record it in the log."""
        logger.info("Applying migration: %s (%s)", migration.version, migration.name)

        try:
            # Execute migration SQL
            self._con.executescript(migration.sql)
        except Exception as e:
            # SQLite-specific: Check if error is about duplicate column
            error_msg = str(e).lower()
            if "duplicate column" in error_msg or "already exists" in error_msg:
                logger.warning(
                    "Migration %s appears to have already been applied (column/object exists). "
                    "Recording in migration log anyway.",
                    migration.version,
                )
            else:
                # Re-raise if it's a different error
                raise

        # Record migration
        applied_at = int(datetime.utcnow().timestamp())
        self._con.execute(
            """
            INSERT INTO schema_migrations(version, name, checksum, applied_at)
            VALUES(?, ?, ?, ?)
            """,
            (migration.version, migration.name, migration.checksum, applied_at),
        )
        self._con.commit()
        logger.info("Migration %s applied successfully", migration.version)


class PostgresMigrationRunner:
    """Migration runner for PostgreSQL databases."""

    def __init__(self, connection) -> None:
        self._con = connection

    def ensure_migrations_table(self) -> None:
        """Create migrations tracking table if it doesn't exist."""
        with self._con.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT NOT NULL PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at BIGINT NOT NULL
                )
                """
            )
        self._con.commit()

    def get_applied_migrations(self) -> Sequence[str]:
        """Get list of applied migration versions."""
        with self._con.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations ORDER BY version")
            rows = cur.fetchall()
        return [row["version"] for row in rows]

    def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration and record it in the log."""
        logger.info("Applying migration: %s (%s)", migration.version, migration.name)

        with self._con.cursor() as cur:
            # Execute migration SQL
            cur.execute(migration.sql)

            # Record migration
            applied_at = int(datetime.utcnow().timestamp())
            cur.execute(
                """
                INSERT INTO schema_migrations(version, name, checksum, applied_at)
                VALUES(%s, %s, %s, %s)
                """,
                (migration.version, migration.name, migration.checksum, applied_at),
            )
        self._con.commit()
        logger.info("Migration %s applied successfully", migration.version)


def load_migration_from_file(file_path: Path) -> Migration:
    """
    Load a migration from a SQL file.

    Migration files should be named: `{version}_{name}_{db_type}.sql`
    Example: `001_initial_schema_sqlite.sql` or `002_add_language_column_postgres.sql`

    Args:
        file_path: Path to the migration SQL file

    Returns:
        Migration object with version, name, and SQL content
    """
    filename = file_path.stem  # e.g., "001_initial_schema_sqlite"
    # Split into version and rest (name_dbtype)
    parts = filename.split("_", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid migration filename format: {file_path.name}. "
            f"Expected: VERSION_NAME_DBTYPE.sql (e.g., 001_initial_schema_sqlite.sql)"
        )

    version = parts[0]
    # Remove db_type suffix (last part after underscore)
    name_parts = parts[1].rsplit("_", 1)
    if len(name_parts) == 2:
        name = name_parts[0]  # e.g., "initial_schema" from "initial_schema_sqlite"
    else:
        name = parts[1]  # Fallback if no db_type suffix

    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()

    return Migration(version=version, name=name, sql=sql)


def run_migrations(
    *,
    runner: MigrationRunner,
    migrations_dir: Path,
    initial_schema_path: Path | None = None,
    db_type: str = "sqlite",
) -> None:
    """
    Run all pending migrations in order.

    Args:
        runner: Migration runner for the database type
        migrations_dir: Directory containing migration SQL files
        initial_schema_path: Optional path to initial schema SQL (runs first if migrations table is empty)
        db_type: Database type ('sqlite' or 'postgres') to filter migration files

    Raises:
        ValueError: If migration files are invalid or out of order
    """
    runner.ensure_migrations_table()
    applied = set(runner.get_applied_migrations())

    # If no migrations have been applied and we have an initial schema, apply it first
    if not applied and initial_schema_path and initial_schema_path.exists():
        logger.info("Applying initial schema from %s", initial_schema_path)
        with open(initial_schema_path, "r", encoding="utf-8") as f:
            initial_sql = f.read()

        # Create a synthetic migration for the initial schema
        initial_migration = Migration(version="000", name="initial_schema", sql=initial_sql)
        runner.apply_migration(initial_migration)
        applied.add("000")

    # Load and sort migration files, filtering by database type
    # Migration files should be named: {version}_{name}_{db_type}.sql
    # e.g., 001_initial_schema_sqlite.sql or 001_initial_schema_postgres.sql
    pattern = f"[0-9]*_{db_type}.sql"
    migration_files = sorted(migrations_dir.glob(pattern))
    if not migration_files:
        logger.info("No migration files found in %s matching pattern %s", migrations_dir, pattern)
        return

    # Apply migrations in order
    for migration_file in migration_files:
        migration = load_migration_from_file(migration_file)

        if migration.version in applied:
            logger.debug("Migration %s already applied, skipping", migration.version)
            continue

        # Verify migration order (all previous migrations should be applied)
        version_num = int(migration.version)
        for prev_version in range(1, version_num):
            prev_version_str = f"{prev_version:03d}"
            if prev_version_str not in applied:
                # Check if previous migration exists for this DB type
                prev_pattern = f"{prev_version_str}_*_{db_type}.sql"
                prev_files = list(migrations_dir.glob(prev_pattern))
                if prev_files:
                    raise ValueError(
                        f"Migration {migration.version} cannot be applied: "
                        f"previous migration {prev_version_str} is missing"
                    )

        runner.apply_migration(migration)
        applied.add(migration.version)

    logger.info("All migrations applied successfully")
