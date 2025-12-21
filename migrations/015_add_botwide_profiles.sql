-- Add bot-wide storyteller profiles table
-- This is separate from the guild-specific storyteller_profiles table
-- and allows users to have a global profile across all servers

CREATE TABLE IF NOT EXISTS storyteller_profiles_global (
    user_id BIGINT PRIMARY KEY,
    pronouns VARCHAR(15),
    custom_title VARCHAR(15),
    color_theme VARCHAR(20) DEFAULT 'gold',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_storyteller_profiles_global_user_id ON storyteller_profiles_global(user_id);

-- Add color_theme column to existing guild-specific profiles as well (optional)
ALTER TABLE storyteller_profiles ADD COLUMN IF NOT EXISTS color_theme VARCHAR(20) DEFAULT 'gold';
