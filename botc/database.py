"""Database connection and query management for Grimkeeper.

This module provides async PostgreSQL database operations using asyncpg.
"""
from __future__ import annotations

import asyncpg
import logging
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from .exceptions import DatabaseError

logger = logging.getLogger('botc_bot')

# Database configuration constants (can be overridden in __init__)
DEFAULT_POOL_MIN_SIZE = 2
DEFAULT_POOL_MAX_SIZE = 10
DEFAULT_COMMAND_TIMEOUT = 60


class Database:
    """Async PostgreSQL database connection pool manager.
    
    Provides high-level methods for all database operations with proper
    error handling and connection pooling.
    
    Attributes:
        connection_string: PostgreSQL connection string
        pool: asyncpg connection pool (None until connect() is called)
    """
    
    def __init__(
        self, 
        connection_string: str,
        min_size: int = DEFAULT_POOL_MIN_SIZE,
        max_size: int = DEFAULT_POOL_MAX_SIZE,
        timeout: int = DEFAULT_COMMAND_TIMEOUT
    ):
        """Initialize database manager.
        
        Args:
            connection_string: PostgreSQL connection URL
            min_size: Minimum connection pool size (default: 2)
            max_size: Maximum connection pool size (default: 10)
            timeout: Command timeout in seconds (default: 60)
        """
        self.connection_string = connection_string
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Create database connection pool.
        
        Raises:
            DatabaseError: If connection fails
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=self.timeout
            )
            logger.info(f"Database connection pool created (min={self.min_size}, max={self.max_size})")
        except (asyncpg.PostgresError, OSError) as e:
            logger.error(f"Failed to connect to database: {e}")
            raise DatabaseError(f"Database connection failed: {e}") from e
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def initialize_schema(self) -> None:
        """Initialize database schema from consolidated migration file."""
        migrations_dir = Path(__file__).parent.parent / "migrations"
        
        # Check if schema already exists (check for guilds table)
        try:
            async with self.pool.acquire() as conn:
                schema_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'guilds')"
                )
                
                if schema_exists:
                    logger.info("Database schema already exists, running additional migrations")
                    # Run additional migrations
                    await self._run_migrations(migrations_dir, conn)
                    return
        except Exception as e:
            logger.warning(f"Error checking schema existence: {e}")
        
        # Run consolidated schema
        schema_file = migrations_dir / "001_complete_schema.sql"
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return
        
        try:
            async with self.pool.acquire() as conn:
                with open(schema_file, 'r') as f:
                    schema_sql = f.read()
                
                await conn.execute(schema_sql)
                logger.info("Database schema initialized successfully")
                
                # Run additional migrations
                await self._run_migrations(migrations_dir, conn)
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            # Don't raise - allow bot to continue
    
    async def _run_migrations(self, migrations_dir: Path, conn) -> None:
        """Run numbered migration files that haven't been applied yet."""
        # Get list of migration files (002+, since 001 is the base schema)
        migration_files = sorted([
            f for f in migrations_dir.glob("*.sql")
            if f.name.startswith(("002_", "003_", "004_", "005_", "006_", "007_", "008_", "009_"))
        ])
        
        for migration_file in migration_files:
            try:
                # Check if this migration's table already exists
                # For 003_add_admin_roles.sql, check if admin_roles table exists
                table_name = None
                if "admin_roles" in migration_file.name:
                    table_name = "admin_roles"
                
                if table_name:
                    table_exists = await conn.fetchval(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                        table_name
                    )
                    if table_exists:
                        logger.debug(f"Migration {migration_file.name} already applied, skipping")
                        continue
                
                # Run the migration
                with open(migration_file, 'r') as f:
                    migration_sql = f.read()
                
                await conn.execute(migration_sql)
                logger.info(f"Applied migration: {migration_file.name}")
            except Exception as e:
                logger.error(f"Failed to apply migration {migration_file.name}: {e}")
                # Continue with other migrations
    
    # Guild operations
    async def get_guild(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get guild configuration."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM guilds WHERE guild_id = $1",
                guild_id
            )
            return dict(row) if row else None
    
    async def upsert_guild(self, guild_id: int, **kwargs) -> None:
        """Insert or update guild configuration.
        
        Only accepts guild-level settings:
        - botc_category_id: Default category for legacy commands
        
        All session-specific config (channels, grimoire links) should be
        stored in the sessions table via SessionManager.
        """
        fields = ['botc_category_id']
        
        # Filter to only fields provided in kwargs
        provided_fields = [field for field in fields if field in kwargs]
        values = [kwargs[field] for field in provided_fields]
        
        if not provided_fields:
            # Just ensure guild exists
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO guilds (guild_id) VALUES ($1) ON CONFLICT DO NOTHING",
                    guild_id
                )
            return
        
        # Build INSERT clause with only provided fields
        insert_fields = ', '.join(provided_fields)
        insert_placeholders = ', '.join(f'${i+2}' for i in range(len(values)))
        
        # Build UPDATE clause
        update_set = ', '.join(f"{field} = ${i+2}" for i, field in enumerate(provided_fields))
        
        query = f"""
            INSERT INTO guilds (guild_id, {insert_fields})
            VALUES ($1, {insert_placeholders})
            ON CONFLICT (guild_id) DO UPDATE SET {update_set}
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(query, guild_id, *values)
    
    # Shadow follower operations
    async def get_followers(self, target_id: int, guild_id: int) -> List[int]:
        """Get all followers for a target user in a guild."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT follower_id FROM shadow_followers WHERE target_id = $1 AND guild_id = $2",
                target_id, guild_id
            )
            return [row['follower_id'] for row in rows]
    
    async def get_follow_target(self, follower_id: int, guild_id: int) -> Optional[int]:
        """Get the target that a follower is following."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT target_id FROM shadow_followers WHERE follower_id = $1 AND guild_id = $2",
                follower_id, guild_id
            )
            return row['target_id'] if row else None
    
    async def add_follower(self, follower_id: int, target_id: int, guild_id: int) -> None:
        """Add a shadow follower relationship."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO shadow_followers (follower_id, target_id, guild_id)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (follower_id, guild_id) DO UPDATE SET target_id = $2""",
                follower_id, target_id, guild_id
            )
    
    async def remove_follower(self, follower_id: int, guild_id: int) -> None:
        """Remove a shadow follower relationship."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM shadow_followers WHERE follower_id = $1 AND guild_id = $2",
                follower_id, guild_id
            )
    
    async def get_all_followers_for_guild(self, guild_id: int) -> Dict[int, List[int]]:
        """Get all shadow follower relationships for a guild. Returns {target_id: [follower_ids]}."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT target_id, follower_id FROM shadow_followers WHERE guild_id = $1",
                guild_id
            )
            result = {}
            for row in rows:
                target_id = row['target_id']
                if target_id not in result:
                    result[target_id] = []
                result[target_id].append(row['follower_id'])
            return result
    
    # DND operations
    async def is_dnd(self, user_id: int) -> bool:
        """Check if user has DND enabled."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM dnd_users WHERE user_id = $1",
                user_id
            )
            return row is not None
    
    async def set_dnd(self, user_id: int, enabled: bool) -> None:
        """Enable or disable DND for a user."""
        async with self.pool.acquire() as conn:
            if enabled:
                await conn.execute(
                    "INSERT INTO dnd_users (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                    user_id
                )
            else:
                await conn.execute(
                    "DELETE FROM dnd_users WHERE user_id = $1",
                    user_id
                )
    
    async def get_all_dnd_users(self) -> List[int]:
        """Get all users with DND enabled."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM dnd_users")
            return [row['user_id'] for row in rows]
    
    # Timer operations
    async def get_timer(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get active timer for a guild."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM timers WHERE guild_id = $1",
                guild_id
            )
            return dict(row) if row else None
    
    async def save_timer(self, guild_id: int, end_time: float, creator_id: int, category_id: int = None) -> None:
        """Save or update timer for a guild.
        
        Args:
            guild_id: Discord guild ID
            end_time: Unix timestamp when timer expires
            creator_id: User ID who created the timer
            category_id: Optional category ID for session-scoped timers
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO timers (guild_id, end_time, creator_id, category_id)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (guild_id) DO UPDATE SET end_time = $2, creator_id = $3, category_id = $4""",
                guild_id, end_time, creator_id, category_id
            )
    
    async def delete_timer(self, guild_id: int) -> None:
        """Delete timer for a guild."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM timers WHERE guild_id = $1",
                guild_id
            )
    
    async def get_all_timers(self) -> List[Dict[str, Any]]:
        """Get all active timers."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM timers")
            return [dict(row) for row in rows]
    
    # Game operations
    async def start_game(self, guild_id: int, script: str, custom_name: str, 
                        start_time: float, players: List[str], storyteller_id: int = None, category_id: int = None) -> int:
        """Start a new game and return game_id.
        
        Args:
            guild_id: Discord guild ID
            script: Script name
            custom_name: Custom script name (if applicable)
            start_time: Unix timestamp when game started
            players: List of player user IDs
            storyteller_id: User ID of storyteller
            category_id: Optional category ID for session-scoped games
        
        Returns:
            game_id of the created game
        """
        async with self.pool.acquire() as conn:
            # End any existing active game in this session
            if category_id:
                await conn.execute(
                    """UPDATE games SET is_active = FALSE 
                       WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE""",
                    guild_id, category_id
                )
            else:
                await conn.execute(
                    "UPDATE games SET is_active = FALSE WHERE guild_id = $1 AND is_active = TRUE",
                    guild_id
                )
            
            # Create new game - convert players list to JSON for JSONB column
            row = await conn.fetchrow(
                """INSERT INTO games (guild_id, category_id, script, custom_name, start_time, players, player_count, is_active, storyteller_id)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, TRUE, $8)
                   RETURNING game_id""",
                guild_id, category_id, script, custom_name or None, start_time, json.dumps(players), len(players), storyteller_id
            )
            return row['game_id']
    
    async def end_game(self, guild_id: int, end_time: float, winner: str, category_id: int = None) -> Optional[Dict[str, Any]]:
        """End active game and return the game record.
        
        Args:
            guild_id: Discord guild ID
            end_time: Unix timestamp when game ended
            winner: 'Good', 'Evil', or 'Tie'
            category_id: Optional category ID for session-scoped games
        
        Returns:
            Game record dict if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            if category_id:
                row = await conn.fetchrow(
                    """UPDATE games 
                       SET end_time = $2, winner = $3, is_active = FALSE, completed_at = NOW()
                       WHERE guild_id = $1 AND category_id = $4 AND is_active = TRUE
                       RETURNING *""",
                    guild_id, end_time, winner, category_id
                )
            else:
                row = await conn.fetchrow(
                    """UPDATE games 
                       SET end_time = $2, winner = $3, is_active = FALSE, completed_at = NOW()
                       WHERE guild_id = $1 AND is_active = TRUE
                       RETURNING *""",
                    guild_id, end_time, winner
                )
            game = dict(row) if row else None
            
            # Clear active_game_id from session (match pattern in cancel_game/delete_game)
            if game:
                await conn.execute(
                    "UPDATE sessions SET active_game_id = NULL WHERE guild_id = $1 AND active_game_id = $2",
                    guild_id, game['game_id']
                )
            
            # Update storyteller stats if game completed successfully and has storyteller
            if game and winner in ('Good', 'Evil') and game.get('storyteller_id'):
                # Calculate game duration in seconds
                game_duration = int(end_time - game.get('start_time', end_time))
                
                # Get player count from players list
                players_data = game.get('players', [])
                if isinstance(players_data, str):
                    try:
                        import json
                        players_list = json.loads(players_data)
                    except:
                        players_list = []
                elif isinstance(players_data, list):
                    players_list = players_data
                else:
                    players_list = []
                
                player_count = len(players_list)
                
                await self._update_storyteller_stats(
                    guild_id=guild_id,
                    storyteller_id=game['storyteller_id'],
                    script=game['script'],
                    winner=winner,
                    game_duration=game_duration,
                    player_count=player_count
                )
            
            return game
    
    async def cancel_game(self, guild_id: int, category_id: int = None) -> None:
        """Cancel (delete) active game without recording in history.
        
        Args:
            guild_id: Discord guild ID
            category_id: Optional category ID for session-scoped games
        """
        async with self.pool.acquire() as conn:
            # First get the game_id(s) we're about to delete
            if category_id:
                game_ids = await conn.fetch(
                    "SELECT game_id FROM games WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
                    guild_id, category_id
                )
            else:
                game_ids = await conn.fetch(
                    "SELECT game_id FROM games WHERE guild_id = $1 AND is_active = TRUE",
                    guild_id
                )
            
            # Clear active_game_id from any sessions referencing these games
            for row in game_ids:
                await conn.execute(
                    "UPDATE sessions SET active_game_id = NULL WHERE guild_id = $1 AND active_game_id = $2",
                    guild_id, row['game_id']
                )
            
            # Now delete the games
            if category_id:
                await conn.execute(
                    "DELETE FROM games WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
                    guild_id, category_id
                )
            else:
                await conn.execute(
                    "DELETE FROM games WHERE guild_id = $1 AND is_active = TRUE",
                    guild_id
                )
    
    async def get_active_game(self, guild_id: int, category_id: int = None) -> Optional[Dict[str, Any]]:
        """Get the active game for a guild or session.
        
        Args:
            guild_id: Discord guild ID
            category_id: Optional category ID for session-scoped games
        
        Returns:
            Active game record dict if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            if category_id:
                row = await conn.fetchrow(
                    "SELECT * FROM games WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
                    guild_id, category_id
                )
            else:
                row = await conn.fetchrow(
                    "SELECT * FROM games WHERE guild_id = $1 AND is_active = TRUE",
                    guild_id
                )
            return dict(row) if row else None
    
    async def update_game_players(self, guild_id: int, player_ids: List[int], category_id: int = None) -> bool:
        """Update the player list for an active game.
        
        Args:
            guild_id: Discord guild ID
            player_ids: List of player user IDs
            category_id: Optional category ID for session-scoped games
            
        Returns:
            True if successful, False if no active game found
        """
        async with self.pool.acquire() as conn:
            if category_id:
                result = await conn.execute(
                    """UPDATE games 
                       SET players = $1, player_count = $2 
                       WHERE guild_id = $3 AND category_id = $4 AND is_active = TRUE""",
                    json.dumps(player_ids), len(player_ids), guild_id, category_id
                )
            else:
                result = await conn.execute(
                    """UPDATE games 
                       SET players = $1, player_count = $2 
                       WHERE guild_id = $3 AND is_active = TRUE""",
                    json.dumps(player_ids), len(player_ids), guild_id
                )
            
            # Check if any row was updated
            return result.split()[-1] != '0'
    
    async def get_game_history(self, guild_id: int, limit: int = None, category_id: int = None) -> List[Dict[str, Any]]:
        """Get game history for a guild, optionally filtered by category.
        
        Args:
            guild_id: Discord guild ID
            limit: Maximum number of games to return (None = all games)
            category_id: Optional category ID to filter session-specific history
            
        Returns:
            List of game records, newest first
        """
        async with self.pool.acquire() as conn:
            if category_id is not None:
                # Session-scoped history
                if limit is not None:
                    rows = await conn.fetch(
                        """SELECT * FROM games 
                           WHERE guild_id = $1 AND category_id = $2 AND is_active = FALSE 
                           ORDER BY completed_at DESC 
                           LIMIT $3""",
                        guild_id, category_id, limit
                    )
                else:
                    rows = await conn.fetch(
                        """SELECT * FROM games 
                           WHERE guild_id = $1 AND category_id = $2 AND is_active = FALSE 
                           ORDER BY completed_at DESC""",
                        guild_id, category_id
                    )
            else:
                # All games across all sessions
                if limit is not None:
                    rows = await conn.fetch(
                        """SELECT * FROM games 
                           WHERE guild_id = $1 AND is_active = FALSE 
                           ORDER BY completed_at DESC 
                           LIMIT $2""",
                        guild_id, limit
                    )
                else:
                    rows = await conn.fetch(
                        """SELECT * FROM games 
                           WHERE guild_id = $1 AND is_active = FALSE 
                           ORDER BY completed_at DESC""",
                        guild_id
                    )
            return [dict(row) for row in rows]
    
    async def get_game_stats(self, guild_id: int) -> Dict[str, Any]:
        """Get game statistics for a guild."""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow(
                """SELECT 
                    COUNT(*) as total_games,
                    COUNT(*) FILTER (WHERE winner = 'Good') as good_wins,
                    COUNT(*) FILTER (WHERE winner = 'Evil') as evil_wins
                   FROM games 
                   WHERE guild_id = $1 AND is_active = FALSE AND winner IN ('Good', 'Evil')""",
                guild_id
            )
            
            # Get most played scripts
            scripts = await conn.fetch(
                """SELECT script, COUNT(*) as count
                   FROM games 
                   WHERE guild_id = $1 AND is_active = FALSE
                   GROUP BY script
                   ORDER BY count DESC
                   LIMIT 3""",
                guild_id
            )
            
            return {
                'total_games': stats['total_games'],
                'good_wins': stats['good_wins'],
                'evil_wins': stats['evil_wins'],
                'scripts': [(row['script'], row['count']) for row in scripts]
            }
    
    async def delete_game(self, guild_id: int, index: int) -> Optional[Dict[str, Any]]:
        """Delete a specific game by index (1-based, newest first). Returns deleted game."""
        async with self.pool.acquire() as conn:
            # Get the game_id at that index
            row = await conn.fetchrow(
                """SELECT game_id FROM games 
                   WHERE guild_id = $1 AND is_active = FALSE
                   ORDER BY completed_at DESC
                   OFFSET $2 LIMIT 1""",
                guild_id, index - 1
            )
            
            if not row:
                return None
            
            game_id = row['game_id']
            
            # Clear active_game_id from any sessions referencing this game
            await conn.execute(
                "UPDATE sessions SET active_game_id = NULL WHERE guild_id = $1 AND active_game_id = $2",
                guild_id, game_id
            )
            
            # Delete and return the game
            deleted = await conn.fetchrow(
                "DELETE FROM games WHERE game_id = $1 RETURNING *",
                game_id
            )
            return dict(deleted) if deleted else None
    
    async def delete_game_by_id(self, game_id: int, guild_id: int) -> bool:
        """Delete a specific game by game_id for a specific guild. Returns True if deleted.
        
        Also updates storyteller stats by subtracting the deleted game's contribution.
        
        Args:
            game_id: The game ID to delete
            guild_id: The guild ID (ensures game belongs to this server)
        """
        async with self.pool.acquire() as conn:
            # First, get the game data before deleting to update stats
            game = await conn.fetchrow(
                "SELECT * FROM games WHERE game_id = $1 AND guild_id = $2",
                game_id, guild_id
            )
            
            if not game:
                return False
            
            # Clear active_game_id from any sessions referencing this game
            await conn.execute(
                "UPDATE sessions SET active_game_id = NULL WHERE guild_id = $1 AND active_game_id = $2",
                guild_id, game_id
            )
            
            # Delete the game
            result = await conn.execute(
                "DELETE FROM games WHERE game_id = $1 AND guild_id = $2",
                game_id, guild_id
            )
            
            deleted = int(result.split()[-1]) > 0 if result else False
            
            # If deletion succeeded and game has storyteller stats, update them
            if deleted and game['storyteller_id'] and game['winner'] in ('Good', 'Evil'):
                # Calculate game duration
                game_duration = 0
                if game['end_time'] and game['start_time']:
                    game_duration = int(game['end_time'] - game['start_time'])
                
                player_count = game.get('player_count', 0) or 0
                
                # Subtract from storyteller stats
                await self._decrement_storyteller_stats(
                    guild_id,
                    game['storyteller_id'],
                    game['script'],
                    game['winner'],
                    game_duration,
                    player_count
                )
            
            return deleted
    
    async def clear_game_history(self, guild_id: int) -> int:
        """Clear all game history for a guild. Returns count of deleted games."""
        async with self.pool.acquire() as conn:
            # Clear active_game_id from any sessions referencing games in this guild
            # (only clears references to completed games that are about to be deleted)
            await conn.execute(
                """UPDATE sessions 
                   SET active_game_id = NULL 
                   WHERE guild_id = $1 
                   AND active_game_id IN (
                       SELECT game_id FROM games 
                       WHERE guild_id = $1 AND is_active = FALSE
                   )""",
                guild_id
            )
            
            result = await conn.execute(
                "DELETE FROM games WHERE guild_id = $1 AND is_active = FALSE",
                guild_id
            )
            # Parse "DELETE N" response
            return int(result.split()[-1]) if result else 0
    
    # Storyteller stats operations
    async def _update_storyteller_stats(self, guild_id: int, storyteller_id: int, 
                                       script: str, winner: str, game_duration: int = 0, 
                                       player_count: int = 0) -> None:
        """Internal method to update storyteller statistics after a game.
        
        Args:
            guild_id: Discord guild ID
            storyteller_id: Discord user ID of storyteller
            script: Script name
            winner: 'Good' or 'Evil'
            game_duration: Game duration in seconds
            player_count: Number of players in the game
        """
        async with self.pool.acquire() as conn:
            # Determine script category
            script_lower = script.lower()
            if 'trouble' in script_lower and 'brewing' in script_lower:
                script_type = 'tb'
            elif 'sects' in script_lower or 'violet' in script_lower:
                script_type = 'snv'
            elif 'bad' in script_lower and 'moon' in script_lower:
                script_type = 'bmr'
            else:
                script_type = None
            
            # Build the update query dynamically
            if script_type:
                await conn.execute(f"""
                    INSERT INTO storyteller_stats (
                        guild_id, storyteller_id, storyteller_name,
                        total_games, good_wins, evil_wins,
                        {script_type}_games, {script_type}_good_wins, {script_type}_evil_wins,
                        total_game_duration, total_player_count,
                        last_game_at
                    ) VALUES (
                        $1, $2, '', 1,
                        CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END,
                        CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END,
                        1,
                        CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END,
                        CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END,
                        $4, $5,
                        NOW()
                    )
                    ON CONFLICT (guild_id, storyteller_id) DO UPDATE SET
                        total_games = storyteller_stats.total_games + 1,
                        good_wins = storyteller_stats.good_wins + CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END,
                        evil_wins = storyteller_stats.evil_wins + CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END,
                        {script_type}_games = storyteller_stats.{script_type}_games + 1,
                        {script_type}_good_wins = storyteller_stats.{script_type}_good_wins + CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END,
                        {script_type}_evil_wins = storyteller_stats.{script_type}_evil_wins + CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END,
                        total_game_duration = storyteller_stats.total_game_duration + $4,
                        total_player_count = storyteller_stats.total_player_count + $5,
                        last_game_at = NOW(),
                        updated_at = NOW()
                """, guild_id, storyteller_id, winner, game_duration, player_count)
            else:
                # No specific script tracking
                await conn.execute("""
                    INSERT INTO storyteller_stats (
                        guild_id, storyteller_id, storyteller_name,
                        total_games, good_wins, evil_wins,
                        total_game_duration, total_player_count,
                        last_game_at
                    ) VALUES ($1, $2, '', 1,
                        CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END,
                        CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END,
                        $4, $5,
                        NOW()
                    )
                    ON CONFLICT (guild_id, storyteller_id) DO UPDATE SET
                        total_games = storyteller_stats.total_games + 1,
                        good_wins = storyteller_stats.good_wins + CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END,
                        evil_wins = storyteller_stats.evil_wins + CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END,
                        total_game_duration = storyteller_stats.total_game_duration + $4,
                        total_player_count = storyteller_stats.total_player_count + $5,
                        last_game_at = NOW(),
                        updated_at = NOW()
                """, guild_id, storyteller_id, winner, game_duration, player_count)
    
    async def _decrement_storyteller_stats(self, guild_id: int, storyteller_id: int,
                                          script: str, winner: str, game_duration: int = 0,
                                          player_count: int = 0) -> None:
        """Internal method to decrement storyteller statistics when a game is deleted.
        
        Args:
            guild_id: Discord guild ID
            storyteller_id: Discord user ID of storyteller
            script: Script name
            winner: 'Good' or 'Evil'
            game_duration: Game duration in seconds
            player_count: Number of players in the game
        """
        async with self.pool.acquire() as conn:
            # Determine script category
            script_lower = script.lower()
            if 'trouble' in script_lower and 'brewing' in script_lower:
                script_type = 'tb'
            elif 'sects' in script_lower or 'violet' in script_lower:
                script_type = 'snv'
            elif 'bad' in script_lower and 'moon' in script_lower:
                script_type = 'bmr'
            else:
                script_type = None
            
            # Check if stats exist for this storyteller
            stats = await conn.fetchrow(
                "SELECT * FROM storyteller_stats WHERE guild_id = $1 AND storyteller_id = $2",
                guild_id, storyteller_id
            )
            
            if not stats:
                return  # No stats to update
            
            # Decrement stats (ensure we don't go below 0)
            if script_type:
                await conn.execute(f"""
                    UPDATE storyteller_stats SET
                        total_games = GREATEST(total_games - 1, 0),
                        good_wins = GREATEST(good_wins - CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END, 0),
                        evil_wins = GREATEST(evil_wins - CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END, 0),
                        {script_type}_games = GREATEST({script_type}_games - 1, 0),
                        {script_type}_good_wins = GREATEST({script_type}_good_wins - CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END, 0),
                        {script_type}_evil_wins = GREATEST({script_type}_evil_wins - CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END, 0),
                        total_game_duration = GREATEST(total_game_duration - $4, 0),
                        total_player_count = GREATEST(total_player_count - $5, 0),
                        updated_at = NOW()
                    WHERE guild_id = $1 AND storyteller_id = $2
                """, guild_id, storyteller_id, winner, game_duration, player_count)
            else:
                await conn.execute("""
                    UPDATE storyteller_stats SET
                        total_games = GREATEST(total_games - 1, 0),
                        good_wins = GREATEST(good_wins - CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END, 0),
                        evil_wins = GREATEST(evil_wins - CASE WHEN $3 = 'Evil' THEN 1 ELSE 0 END, 0),
                        total_game_duration = GREATEST(total_game_duration - $4, 0),
                        total_player_count = GREATEST(total_player_count - $5, 0),
                        updated_at = NOW()
                    WHERE guild_id = $1 AND storyteller_id = $2
                """, guild_id, storyteller_id, winner, game_duration, player_count)
    
    async def get_storyteller_stats(self, guild_id: int = None) -> List[Dict[str, Any]]:
        """Get storyteller statistics, optionally filtered by guild.
        
        Args:
            guild_id: Optional guild ID to filter by. If None, returns bot-wide stats.
            
        Returns:
            List of storyteller stats dictionaries, ordered by total games.
        """
        async with self.pool.acquire() as conn:
            if guild_id is None:
                # Bot-wide stats - aggregate across all guilds for each storyteller
                rows = await conn.fetch(
                    """SELECT 
                        storyteller_id,
                        MAX(storyteller_name) as storyteller_name,
                        SUM(total_games) as total_games,
                        SUM(good_wins) as good_wins,
                        SUM(evil_wins) as evil_wins,
                        SUM(tb_games) as tb_games,
                        SUM(tb_good_wins) as tb_good_wins,
                        SUM(tb_evil_wins) as tb_evil_wins,
                        SUM(snv_games) as snv_games,
                        SUM(snv_good_wins) as snv_good_wins,
                        SUM(snv_evil_wins) as snv_evil_wins,
                        SUM(bmr_games) as bmr_games,
                        SUM(bmr_good_wins) as bmr_good_wins,
                        SUM(bmr_evil_wins) as bmr_evil_wins,
                        SUM(total_game_duration) as total_game_duration,
                        SUM(total_player_count) as total_player_count,
                        MAX(last_game_at) as last_game_at
                    FROM storyteller_stats
                    GROUP BY storyteller_id
                    ORDER BY SUM(total_games) DESC, MAX(last_game_at) DESC"""
                )
            else:
                # Guild-specific stats
                rows = await conn.fetch(
                    """SELECT * FROM storyteller_stats 
                       WHERE guild_id = $1 
                       ORDER BY total_games DESC, last_game_at DESC""",
                    guild_id
                )
            return [dict(row) for row in rows]
    
    async def update_storyteller_name(self, guild_id: int, storyteller_id: int, name: str) -> None:
        """Update storyteller display name."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE storyteller_stats SET storyteller_name = $3, updated_at = NOW()
                   WHERE guild_id = $1 AND storyteller_id = $2""",
                guild_id, storyteller_id, name
            )
    
    # Session operations
    async def create_session(self, session) -> None:
        """Create a new session.
        
        Args:
            session: Session object to create
        """
        import json
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO sessions (
                    guild_id, category_id, destination_channel_id, grimoire_link,
                    exception_channel_id, announce_channel_id, active_game_id,
                    storyteller_user_id, created_at, last_active, vc_caps, session_code
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (guild_id, category_id) DO UPDATE SET
                    last_active = $10,
                    vc_caps = $11,
                    session_code = COALESCE(sessions.session_code, $12)""",
                session.guild_id, session.category_id, session.destination_channel_id,
                session.grimoire_link, session.exception_channel_id, session.announce_channel_id,
                session.active_game_id, session.storyteller_user_id, session.created_at, session.last_active,
                json.dumps(session.vc_caps), session.session_code
            )
    
    async def get_session(self, guild_id: int, category_id: int):
        """Get a session by guild and category ID.
        
        Args:
            guild_id: Discord guild ID
            category_id: Discord category ID
            
        Returns:
            Session object if found, None otherwise
        """
        from botc.session import Session
        import json
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM sessions 
                   WHERE guild_id = $1 AND category_id = $2""",
                guild_id, category_id
            )
            if row:
                data = dict(row)
                # Parse vc_caps from JSON
                if 'vc_caps' in data:
                    if data['vc_caps'] is None:
                        data['vc_caps'] = {}
                    elif isinstance(data['vc_caps'], str):
                        data['vc_caps'] = json.loads(data['vc_caps']) if data['vc_caps'] else {}
                        # Convert string keys to int keys
                        if data['vc_caps']:
                            data['vc_caps'] = {int(k): v for k, v in data['vc_caps'].items()}
                    elif isinstance(data['vc_caps'], dict):
                        # asyncpg returns JSONB as dict, convert keys to int
                        data['vc_caps'] = {int(k): v for k, v in data['vc_caps'].items()} if data['vc_caps'] else {}
                    else:
                        data['vc_caps'] = {}
                else:
                    data['vc_caps'] = {}
                return Session(**data)
            return None
    
    async def get_session_by_code(self, guild_id: int, session_code: str):
        """Get a session by guild ID and session code.
        
        Args:
            guild_id: Discord guild ID
            session_code: Session code (e.g., "s1", "s2")
            
        Returns:
            Session object if found, None otherwise
        """
        from botc.session import Session
        import json
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM sessions 
                   WHERE guild_id = $1 AND session_code = $2""",
                guild_id, session_code
            )
            if row:
                data = dict(row)
                # Parse vc_caps from JSON
                if 'vc_caps' in data:
                    if data['vc_caps'] is None:
                        data['vc_caps'] = {}
                    elif isinstance(data['vc_caps'], str):
                        data['vc_caps'] = json.loads(data['vc_caps']) if data['vc_caps'] else {}
                        if data['vc_caps']:
                            data['vc_caps'] = {int(k): v for k, v in data['vc_caps'].items()}
                    elif isinstance(data['vc_caps'], dict):
                        data['vc_caps'] = {int(k): v for k, v in data['vc_caps'].items()} if data['vc_caps'] else {}
                    else:
                        data['vc_caps'] = {}
                else:
                    data['vc_caps'] = {}
                return Session(**data)
            return None
    
    async def update_session(self, session) -> None:
        """Update an existing session.
        
        Args:
            session: Session object with updated values
        """
        import json
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE sessions SET
                    destination_channel_id = $3,
                    grimoire_link = $4,
                    exception_channel_id = $5,
                    announce_channel_id = $6,
                    active_game_id = $7,
                    storyteller_user_id = $8,
                    last_active = $9,
                    vc_caps = $10,
                    session_code = $11
                WHERE guild_id = $1 AND category_id = $2""",
                session.guild_id, session.category_id, session.destination_channel_id,
                session.grimoire_link, session.exception_channel_id, session.announce_channel_id,
                session.active_game_id, session.storyteller_user_id, session.last_active,
                json.dumps(session.vc_caps), session.session_code
            )
    
    async def delete_session(self, guild_id: int, category_id: int) -> bool:
        """Delete a session.
        
        Args:
            guild_id: Discord guild ID
            category_id: Discord category ID
            
        Returns:
            True if session was deleted, False if it didn't exist
        """
        async with self.pool.acquire() as conn:
            # First, get game_ids to clear from sessions table
            game_ids = await conn.fetch(
                "SELECT game_id FROM games WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
                guild_id, category_id
            )
            
            # Clear active_game_id from any sessions referencing these games
            for row in game_ids:
                await conn.execute(
                    "UPDATE sessions SET active_game_id = NULL WHERE guild_id = $1 AND active_game_id = $2",
                    guild_id, row['game_id']
                )
            
            # Delete active games entirely (consistent with /endgame Cancel behavior)
            await conn.execute(
                "DELETE FROM games WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
                guild_id, category_id
            )
            
            # Now delete the session
            result = await conn.execute(
                """DELETE FROM sessions WHERE guild_id = $1 AND category_id = $2""",
                guild_id, category_id
            )
            
            # Check if any rows were deleted
            rows_deleted = int(result.split()[-1]) if result else 0
            return rows_deleted > 0
    
    async def get_all_sessions_for_guild(self, guild_id: int) -> List:
        """Get all sessions for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of Session objects
        """
        from botc.session import Session
        import json
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM sessions WHERE guild_id = $1
                   ORDER BY last_active DESC""",
                guild_id
            )
            sessions = []
            for row in rows:
                data = dict(row)
                # Parse vc_caps from JSON
                if 'vc_caps' in data:
                    if data['vc_caps'] is None:
                        data['vc_caps'] = {}
                    elif isinstance(data['vc_caps'], str):
                        data['vc_caps'] = json.loads(data['vc_caps']) if data['vc_caps'] else {}
                        # Convert string keys to int keys
                        if data['vc_caps']:
                            data['vc_caps'] = {int(k): v for k, v in data['vc_caps'].items()}
                    elif isinstance(data['vc_caps'], dict):
                        # asyncpg returns JSONB as dict, convert keys to int
                        data['vc_caps'] = {int(k): v for k, v in data['vc_caps'].items()} if data['vc_caps'] else {}
                    else:
                        data['vc_caps'] = {}
                else:
                    data['vc_caps'] = {}
                sessions.append(Session(**data))
            return sessions
    
    async def delete_inactive_sessions(self, cutoff_timestamp: float) -> int:
        """Delete sessions that haven't been active since cutoff.
        
        Args:
            cutoff_timestamp: Unix timestamp - delete sessions older than this
            
        Returns:
            Number of sessions deleted
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """DELETE FROM sessions WHERE last_active < $1""",
                cutoff_timestamp
            )
            # Extract number from "DELETE N" response
            return int(result.split()[-1]) if result else 0

    # ========================================================================
    # Storyteller Profile Methods
    # ========================================================================

    async def get_storyteller_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get storyteller profile for a user (bot-wide).
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dict with profile fields or None if not found
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT pronouns, custom_title, color_theme, created_at, updated_at
                   FROM storyteller_profiles_global
                   WHERE user_id = $1""",
                user_id
            )
            return dict(row) if row else None

    async def set_storyteller_profile(
        self,
        user_id: int,
        pronouns: Optional[str] = None,
        custom_title: Optional[str] = None,
        color_theme: Optional[str] = None
    ) -> bool:
        """Create or update storyteller profile (bot-wide).
        
        Args:
            user_id: Discord user ID
            pronouns: User pronouns
            custom_title: Custom title for card (e.g., "Gamer", "Farmer")
            color_theme: Color theme name (gold, silver, crimson, etc.)
            
        Returns:
            True if successful
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO storyteller_profiles_global (user_id, pronouns, custom_title, color_theme, updated_at)
                   VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                   ON CONFLICT (user_id)
                   DO UPDATE SET
                       pronouns = COALESCE($2, storyteller_profiles_global.pronouns),
                       custom_title = COALESCE($3, storyteller_profiles_global.custom_title),
                       color_theme = COALESCE($4, storyteller_profiles_global.color_theme),
                       updated_at = CURRENT_TIMESTAMP""",
                user_id, pronouns, custom_title, color_theme
            )
            return True

    async def clear_storyteller_profile_field(self, user_id: int, field: str) -> bool:
        """Clear a specific field from storyteller profile (bot-wide).
        
        Args:
            user_id: Discord user ID
            field: Field name to clear (pronouns, custom_title, or color_theme)
            
        Returns:
            True if successful
        """
        if field not in ['pronouns', 'custom_title', 'color_theme']:
            return False
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""UPDATE storyteller_profiles_global
                    SET {field} = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = $1""",
                user_id
            )
            return True
    
    async def set_guild_language(self, guild_id: int, language: str) -> None:
        """Set the language for a guild.
        
        Args:
            guild_id: Discord guild ID
            language: Language code (e.g., 'en', 'es', 'pl', 'ru')
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE guilds
                   SET language = $2
                   WHERE guild_id = $1""",
                guild_id, language
            )
    
    async def get_guild_language(self, guild_id: int) -> str:
        """Get the language for a guild.
        
        Args:
            guild_id: Discord guild ID
        
        Returns:
            Language code (default: 'en')
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT language FROM guilds WHERE guild_id = $1",
                guild_id
            )
            return row['language'] if row else 'en'

    # Admin roles management
    async def get_admin_roles(self, guild_id: int) -> List[int]:
        """Get all admin role IDs for a guild.
        
        Args:
            guild_id: Discord guild ID
        
        Returns:
            List of role IDs that have admin privileges
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role_id FROM admin_roles WHERE guild_id = $1",
                guild_id
            )
            return [row['role_id'] for row in rows]
    
    async def add_admin_role(self, guild_id: int, role_id: int) -> bool:
        """Add a role as an admin role for a guild.
        
        Args:
            guild_id: Discord guild ID
            role_id: Discord role ID to add as admin
        
        Returns:
            True if role was added, False if it already existed
        """
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """INSERT INTO admin_roles (guild_id, role_id)
                       VALUES ($1, $2)
                       ON CONFLICT (guild_id, role_id) DO NOTHING""",
                    guild_id, role_id
                )
                # Check if the insert actually happened
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM admin_roles WHERE guild_id = $1 AND role_id = $2",
                    guild_id, role_id
                )
                return result > 0
            except Exception as e:
                logger.error(f"Error adding admin role {role_id} for guild {guild_id}: {e}")
                return False
    
    async def remove_admin_role(self, guild_id: int, role_id: int) -> bool:
        """Remove an admin role from a guild.
        
        Args:
            guild_id: Discord guild ID
            role_id: Discord role ID to remove from admin list
        
        Returns:
            True if role was removed, False if it didn't exist
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM admin_roles WHERE guild_id = $1 AND role_id = $2",
                guild_id, role_id
            )
            # Check if any rows were deleted
            return result.split()[-1] != '0'
    
    async def is_admin_role(self, guild_id: int, role_id: int) -> bool:
        """Check if a role is an admin role for a guild.
        
        Args:
            guild_id: Discord guild ID
            role_id: Discord role ID to check
        
        Returns:
            True if the role is an admin role, False otherwise
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM admin_roles WHERE guild_id = $1 AND role_id = $2",
                guild_id, role_id
            )
            return result > 0



# Global database instance
db: Optional[Database] = None


def get_db() -> Database:
    """Get the global database instance."""
    if db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return db


async def init_db(connection_string: str) -> Database:
    """Initialize the global database instance."""
    global db
    db = Database(connection_string)
    await db.connect()
    await db.initialize_schema()
    return db


async def close_db() -> None:
    """Close the global database instance."""
    global db
    if db:
        await db.close()
        db = None
