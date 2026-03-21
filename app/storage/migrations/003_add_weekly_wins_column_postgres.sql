-- Add weekly_wins column to users table (PostgreSQL)
-- This migration is idempotent using DO block

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'weekly_wins'
    ) THEN
        ALTER TABLE users ADD COLUMN weekly_wins INT NOT NULL DEFAULT 0;
    END IF;
END $$;
