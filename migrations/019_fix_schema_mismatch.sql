-- Fix schema mismatches between migration 012 and code expectations
-- Safe to run multiple times (all operations use IF EXISTS/IF NOT EXISTS)

-- ============================================================
-- Fix guilds table: add missing columns
-- ============================================================
ALTER TABLE guilds ADD COLUMN IF NOT EXISTS botc_category_id BIGINT;

-- ============================================================
-- Fix games table: rename columns to match code expectations
-- ============================================================

-- Rename started_at -> start_time (as DOUBLE PRECISION / unix timestamp)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'games' AND column_name = 'started_at') THEN
        -- Add new column, migrate data, drop old
        ALTER TABLE games ADD COLUMN IF NOT EXISTS start_time DOUBLE PRECISION;
        UPDATE games SET start_time = EXTRACT(EPOCH FROM started_at) WHERE start_time IS NULL AND started_at IS NOT NULL;
        ALTER TABLE games DROP COLUMN started_at;
    END IF;
END $$;

-- Rename ended_at -> end_time (as DOUBLE PRECISION / unix timestamp)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'games' AND column_name = 'ended_at') THEN
        ALTER TABLE games ADD COLUMN IF NOT EXISTS end_time DOUBLE PRECISION;
        UPDATE games SET end_time = EXTRACT(EPOCH FROM ended_at) WHERE end_time IS NULL AND ended_at IS NOT NULL;
        ALTER TABLE games DROP COLUMN ended_at;
    END IF;
END $$;

-- Rename winning_team -> winner
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'games' AND column_name = 'winning_team') THEN
        ALTER TABLE games ADD COLUMN IF NOT EXISTS winner TEXT;
        UPDATE games SET winner = winning_team WHERE winner IS NULL AND winning_team IS NOT NULL;
        ALTER TABLE games DROP COLUMN winning_team;
    END IF;
END $$;

-- Rename num_players -> player_count
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'games' AND column_name = 'num_players') THEN
        ALTER TABLE games ADD COLUMN IF NOT EXISTS player_count INTEGER DEFAULT 0;
        UPDATE games SET player_count = num_players WHERE player_count = 0 AND num_players IS NOT NULL;
        ALTER TABLE games DROP COLUMN num_players;
    END IF;
END $$;

-- Add missing columns
ALTER TABLE games ADD COLUMN IF NOT EXISTS custom_name TEXT;
ALTER TABLE games ADD COLUMN IF NOT EXISTS players JSONB DEFAULT '[]'::jsonb;
ALTER TABLE games ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT FALSE;
ALTER TABLE games ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;

-- Drop duration_minutes if it exists (code calculates from start_time/end_time)
ALTER TABLE games DROP COLUMN IF EXISTS duration_minutes;

CREATE INDEX IF NOT EXISTS idx_games_is_active ON games(is_active);

-- ============================================================
-- Fix shadow_followers table: recreate with correct schema
-- ============================================================

-- Drop old table and recreate with correct columns
DROP TABLE IF EXISTS shadow_followers;

CREATE TABLE shadow_followers (
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    follower_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (follower_id, guild_id)
);

CREATE INDEX IF NOT EXISTS idx_shadow_followers_guild_id ON shadow_followers(guild_id);
CREATE INDEX IF NOT EXISTS idx_shadow_followers_target_id ON shadow_followers(target_id);
