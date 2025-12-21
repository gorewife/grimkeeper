-- Complete database schema for GrimKeeper bot
-- Consolidates migrations 001-010 into single file
-- Run this on fresh PostgreSQL database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Guilds table
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    grimoire_link TEXT,
    active_session_id UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
    language VARCHAR(5) DEFAULT 'en' NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_guilds_language ON guilds(language);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL,
    town_square_channel_id BIGINT,
    grimoire_link TEXT,
    destination_channel_id BIGINT,
    announce_channel_id BIGINT,
    exception_channel_id BIGINT,
    active_game_id INTEGER,  -- FK added after games table is created
    storyteller_user_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vc_caps JSONB DEFAULT '{}'::jsonb,
    UNIQUE(guild_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_guild_id ON sessions(guild_id);
CREATE INDEX IF NOT EXISTS idx_sessions_category_id ON sessions(category_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active_game_id ON sessions(active_game_id);

-- Games table (tracks individual game instances)
CREATE TABLE IF NOT EXISTS games (
    game_id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
    category_id BIGINT,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    script TEXT,
    num_players INTEGER,
    storyteller_id BIGINT,
    winning_team TEXT CHECK (winning_team IN ('good', 'evil')),
    duration_minutes INTEGER
);

CREATE INDEX IF NOT EXISTS idx_games_guild_id ON games(guild_id);
CREATE INDEX IF NOT EXISTS idx_games_storyteller_id ON games(storyteller_id);
CREATE INDEX IF NOT EXISTS idx_games_started_at ON games(started_at);
CREATE INDEX IF NOT EXISTS idx_games_session_id ON games(session_id);
CREATE INDEX IF NOT EXISTS idx_games_category_id ON games(category_id);

-- Storyteller stats table (aggregate statistics)
CREATE TABLE IF NOT EXISTS storyteller_stats (
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    storyteller_id BIGINT NOT NULL,
    games_run INTEGER DEFAULT 0,
    total_minutes INTEGER DEFAULT 0,
    good_wins INTEGER DEFAULT 0,
    evil_wins INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, storyteller_id)
);

CREATE INDEX IF NOT EXISTS idx_storyteller_stats_guild_id ON storyteller_stats(guild_id);
CREATE INDEX IF NOT EXISTS idx_storyteller_stats_storyteller_id ON storyteller_stats(storyteller_id);

-- Storyteller profiles table
CREATE TABLE IF NOT EXISTS storyteller_profiles (
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    storyteller_id BIGINT NOT NULL,
    favorite_script TEXT,
    fun_fact TEXT,
    PRIMARY KEY (guild_id, storyteller_id)
);

-- Storyteller tracking metrics
CREATE TABLE IF NOT EXISTS storyteller_metrics (
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    storyteller_id BIGINT NOT NULL,
    metric_date DATE NOT NULL,
    games_count INTEGER DEFAULT 0,
    total_minutes INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, storyteller_id, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_storyteller_metrics_date ON storyteller_metrics(metric_date);

-- Timers table
CREATE TABLE IF NOT EXISTS timers (
    timer_id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    category_id BIGINT,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL UNIQUE,
    phase TEXT NOT NULL CHECK (phase IN ('nomination', 'discussion', 'private', 'unknown')),
    duration_seconds INTEGER NOT NULL,
    end_time TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_timers_guild_id ON timers(guild_id);
CREATE INDEX IF NOT EXISTS idx_timers_end_time ON timers(end_time);
CREATE INDEX IF NOT EXISTS idx_timers_is_active ON timers(is_active);
CREATE INDEX IF NOT EXISTS idx_timers_category_id ON timers(category_id);

-- Shadow followers table (players who shadow-follow discussion channels)
CREATE TABLE IF NOT EXISTS shadow_followers (
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    discussion_channel_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, user_id, discussion_channel_id)
);

CREATE INDEX IF NOT EXISTS idx_shadow_followers_guild_id ON shadow_followers(guild_id);
CREATE INDEX IF NOT EXISTS idx_shadow_followers_user_id ON shadow_followers(user_id);

-- DND users table (do-not-disturb for @everyone pings)
CREATE TABLE IF NOT EXISTS dnd_users (
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_dnd_users_guild_id ON dnd_users(guild_id);

-- Channel limits table (max players per discussion channel)
CREATE TABLE IF NOT EXISTS channel_limits (
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL,
    max_players INTEGER NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE INDEX IF NOT EXISTS idx_channel_limits_guild_id ON channel_limits(guild_id);

-- Add foreign key constraints after both sessions and games tables exist
-- This handles the circular reference between sessions and games
DO $$ 
BEGIN
    -- Add FK for sessions.active_game_id -> games.game_id with ON DELETE SET NULL
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'sessions_active_game_id_fkey' 
        AND table_name = 'sessions'
    ) THEN
        ALTER TABLE sessions 
        ADD CONSTRAINT sessions_active_game_id_fkey 
        FOREIGN KEY (active_game_id) 
        REFERENCES games(game_id) 
        ON DELETE SET NULL;
    END IF;
END $$;
