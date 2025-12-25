-- Add announcements queue for website-triggered events
CREATE TABLE IF NOT EXISTS announcements (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    category_id BIGINT,
    announcement_type VARCHAR(50) NOT NULL, -- 'game_start', 'game_end'
    game_id INTEGER REFERENCES games(game_id),
    data JSONB, -- Additional data (script, players, winner, etc.)
    created_at BIGINT NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at BIGINT
);

CREATE INDEX idx_announcements_pending ON announcements(guild_id, processed) WHERE processed = FALSE;
