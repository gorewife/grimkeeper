-- Migration: Add session codes for bot-website integration
-- Session codes provide human-friendly identifiers for API access and website linking

-- Add session_code column (nullable initially for existing sessions)
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS session_code VARCHAR(8);

-- Create unique index for session codes
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_code ON sessions(session_code);

-- Generate codes for existing sessions (simple sequential format per guild)
-- This will be handled by the bot on first access, but we set up the structure here
