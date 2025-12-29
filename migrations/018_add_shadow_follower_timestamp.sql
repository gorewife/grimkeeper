-- Add timestamp to shadow_followers for cleanup
ALTER TABLE shadow_followers 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();

-- Create index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_shadow_followers_created_at ON shadow_followers(created_at);
