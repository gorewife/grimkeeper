-- Add admin_roles table to store custom admin roles per guild
-- This allows server owners to designate specific roles as having admin privileges
-- for bot commands, without requiring Discord's Administrator permission

CREATE TABLE IF NOT EXISTS admin_roles (
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_admin_roles_guild_id ON admin_roles(guild_id);
CREATE INDEX IF NOT EXISTS idx_admin_roles_role_id ON admin_roles(role_id);

-- Update storyteller_profiles table: replace favorite_script and style with custom_title
ALTER TABLE storyteller_profiles DROP COLUMN IF EXISTS favorite_script;
ALTER TABLE storyteller_profiles DROP COLUMN IF EXISTS style;
ALTER TABLE storyteller_profiles ADD COLUMN IF NOT EXISTS custom_title VARCHAR(15);
