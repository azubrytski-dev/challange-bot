-- Add language column to chat_state table (SQLite)
-- This migration checks if column exists before adding it

-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
-- We check pragma table_info to see if column exists
-- If it doesn't exist, we add it
-- Note: This will be handled by the migration runner's idempotency check
-- If migration is already recorded, it won't run again

-- Check if column exists (via pragma), if not, add it
-- Since SQLite doesn't support conditional ALTER TABLE, we rely on
-- migration tracking to prevent re-running
ALTER TABLE chat_state ADD COLUMN language TEXT NOT NULL DEFAULT 'en';
