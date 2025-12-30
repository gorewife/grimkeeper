"""CSV export functionality for game stats."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from botc.database import Database


async def generate_player_csv(db: 'Database', player_discord_id: int, game_id: int = None, limit: int = None) -> io.StringIO:
    """Generate CSV export for a player's games.
    
    Args:
        db: Database instance
        player_discord_id: Discord ID of the player
        game_id: Optional specific game ID. If None, exports all games.
        limit: Optional limit on number of games to export (most recent first)
    
    Returns:
        StringIO buffer containing CSV data
    """
    async with db.pool.acquire() as conn:
        if game_id:
            # Single game export - try game_players first, then fall back to games.players for legacy games
            query = """
                SELECT 
                    g.start_time,
                    COALESCE(g.custom_name, g.script) as script,
                    g.storyteller_id,
                    g.guild_id,
                    g.player_count,
                    g.winner,
                    gp.starting_role_name,
                    gp.starting_team,
                    gp.final_role_name,
                    gp.final_team
                FROM games g
                LEFT JOIN game_players gp ON g.game_id = gp.game_id AND gp.discord_id = $2
                WHERE g.game_id = $1
                ORDER BY g.start_time DESC
            """
            rows = await conn.fetch(query, game_id, player_discord_id)
            
            # For legacy games without game_players entries, check if player was in the game
            if rows and not rows[0]['starting_role_name']:
                game = rows[0]
                players_json = await conn.fetchval(
                    "SELECT players FROM games WHERE game_id = $1",
                    game_id
                )
                if players_json:
                    import json
                    players = json.loads(players_json) if isinstance(players_json, str) else players_json
                    if player_discord_id not in players:
                        rows = []  # Player wasn't in this game
        else:
            # All games export - include both game_players entries and legacy games
            query = """
                SELECT 
                    g.start_time,
                    COALESCE(g.custom_name, g.script) as script,
                    g.storyteller_id,
                    g.guild_id,
                    g.player_count,
                    g.winner,
                    g.players,
                    gp.starting_role_name,
                    gp.starting_team,
                    gp.final_role_name,
                    gp.final_team
                FROM games g
                LEFT JOIN game_players gp ON g.game_id = gp.game_id AND gp.discord_id = $1
                WHERE (gp.discord_id = $1 OR (g.players IS NOT NULL AND g.players::jsonb @> to_jsonb($1::bigint)))
                AND g.is_active = FALSE
                ORDER BY g.start_time DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            rows = await conn.fetch(query, player_discord_id)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Date',
        'Script',
        'Storyteller (say "me" if it was you)',
        'Online/In Person',
        'Location (if in person)',
        'Community',
        'Player count',
        'Traveler count',
        'Game Result (win/loss)',
        'Starting Role',
        'Starting Related Role',
        'Starting Alignment (if not default)',
        'Ending Role (if different)',
        'Ending Related Role',
        'Ending Alignment (if not default)',
        'Notes'
    ])
    
    # Write game rows
    for row in rows:
        date = datetime.fromtimestamp(row['start_time']).strftime('%Y-%m-%d')
        script = row['script'] or 'Unknown Script'
        storyteller = 'me' if row['storyteller_id'] == player_discord_id else 'Storyteller'
        player_count = row['player_count'] or ''
        
        # Determine game result from player's perspective
        winner = row['winner']
        final_team = row['final_team'] or row['starting_team']
        
        if winner and final_team:
            result = 'win' if winner.lower() == final_team.lower() else 'loss'
        else:
            result = ''
        
        starting_role = row['starting_role_name'] or ''
        starting_team = row['starting_team'] or ''
        final_role = row['final_role_name'] or ''
        final_team_val = row['final_team'] or ''
        
        # Check if alignment changed
        starting_alignment = '' if starting_team.lower() in ['townsfolk', 'outsider', 'minion', 'demon'] else starting_team
        ending_alignment = '' if final_team_val.lower() in ['townsfolk', 'outsider', 'minion', 'demon'] else final_team_val
        
        # Only include ending role if it changed
        ending_role = final_role if final_role and final_role != starting_role else ''
        
        writer.writerow([
            date,
            script,
            storyteller,
            'Online',
            '',  # Location (N/A for online)
            'Discord',  # Community
            player_count,
            '',  # Traveler count (not tracked)
            result,
            starting_role,
            '',  # Starting Related Role (not tracked)
            starting_alignment,
            ending_role,
            '',  # Ending Related Role (not tracked)
            ending_alignment,
            ''   # Notes
        ])
    
    output.seek(0)
    return output


async def generate_all_players_csvs(db: 'Database', game_id: int) -> dict[int, io.StringIO]:
    """Generate CSV exports for all players in a game.
    
    Args:
        db: Database instance
        game_id: Game ID to export
    
    Returns:
        Dictionary mapping discord_id to CSV StringIO buffer
    """
    async with db.pool.acquire() as conn:
        # Get all players in the game
        players = await conn.fetch(
            "SELECT DISTINCT discord_id FROM game_players WHERE game_id = $1 AND discord_id IS NOT NULL",
            game_id
        )
    
    exports = {}
    for player in players:
        discord_id = player['discord_id']
        exports[discord_id] = await generate_player_csv(db, discord_id, game_id)
    
    return exports
