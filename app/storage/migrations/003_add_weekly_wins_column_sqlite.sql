-- Add weekly_wins column to users table (SQLite)
ALTER TABLE users ADD COLUMN weekly_wins INTEGER NOT NULL DEFAULT 0;
