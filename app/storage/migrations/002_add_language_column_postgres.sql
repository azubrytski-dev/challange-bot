-- Add language column to chat_state table (PostgreSQL)
-- This migration is idempotent using DO block

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat_state' AND column_name = 'language'
    ) THEN
        ALTER TABLE chat_state ADD COLUMN language TEXT NOT NULL DEFAULT 'en';
    END IF;
END $$;
