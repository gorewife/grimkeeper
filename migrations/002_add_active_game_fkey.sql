-- Migration: Add foreign key constraint for active_game_id with ON DELETE SET NULL
-- This ensures that when a game is deleted, any session referencing it will have active_game_id set to NULL automatically
-- Prevents foreign key constraint violations

-- First, check if the constraint already exists and drop it if needed
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'sessions_active_game_id_fkey' 
        AND table_name = 'sessions'
    ) THEN
        ALTER TABLE sessions DROP CONSTRAINT sessions_active_game_id_fkey;
    END IF;
END $$;

-- Add the foreign key constraint with ON DELETE SET NULL
ALTER TABLE sessions 
ADD CONSTRAINT sessions_active_game_id_fkey 
FOREIGN KEY (active_game_id) 
REFERENCES games(game_id) 
ON DELETE SET NULL;

-- Clean up any orphaned active_game_id references
UPDATE sessions 
SET active_game_id = NULL 
WHERE active_game_id IS NOT NULL 
AND active_game_id NOT IN (SELECT game_id FROM games);
