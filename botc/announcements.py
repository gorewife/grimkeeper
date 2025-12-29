"""Website announcement processor.

Monitors the announcements table for website-triggered game events
and sends Discord notifications using the existing handler embeds.
"""
from __future__ import annotations

import asyncio
import logging
import json
from typing import TYPE_CHECKING
import discord
import time

if TYPE_CHECKING:
    from botc.database import Database
    from botc.session import SessionManager

logger = logging.getLogger('botc_bot')


class AnnouncementProcessor:
    """Processes website-triggered announcements from the queue."""
    
    def __init__(self, bot: discord.Client, db: 'Database', session_manager: 'SessionManager'):
        self.bot = bot
        self.db = db
        self.session_manager = session_manager
        self.running = False
        self.task = None
    
    def start(self):
        """Start the announcement processor background task."""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._process_loop())
            logger.info("Announcement processor started")
    
    def stop(self):
        """Stop the announcement processor."""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("Announcement processor stopped")
    
    async def _process_loop(self):
        """Main loop that checks for and processes announcements."""
        while self.running:
            try:
                await self._process_pending_announcements()
            except Exception:
                logger.exception("Error processing announcements")
            
            # Check every 5 seconds
            await asyncio.sleep(5)
    
    async def _process_pending_announcements(self):
        """Check for and process pending announcements."""
        try:
            # Get pending announcements
            async with self.db.pool.acquire() as conn:
                announcements = await conn.fetch(
                    """SELECT id, guild_id, category_id, announcement_type, game_id, data
                       FROM announcements 
                       WHERE processed = FALSE 
                       ORDER BY created_at ASC
                       LIMIT 10"""
                )
                
                for announcement in announcements:
                    try:
                        await self._process_announcement(announcement)
                        
                        # Mark as processed
                        await conn.execute(
                            "UPDATE announcements SET processed = TRUE, processed_at = $1 WHERE id = $2",
                            int(time.time()), announcement['id']
                        )
                    except Exception:
                        logger.exception(f"Error processing announcement {announcement['id']}")
        
        except Exception:
            logger.exception("Error fetching pending announcements")
    
    async def _process_announcement(self, announcement):
        """Process a single announcement by reusing existing handler functions."""
        from botc.handlers import start_game_handler, end_game_handler
        
        guild_id = announcement['guild_id']
        category_id = announcement['category_id']
        ann_type = announcement['announcement_type']
        game_id = announcement.get('game_id')
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            logger.warning(f"Guild {guild_id} not found for announcement")
            return
        
        # Handle mute/unmute announcements (no game_id needed)
        if ann_type == 'mute':
            from botc.handlers import mute_from_website
            await mute_from_website(guild_id, category_id, self.bot, self.db)
            return
        elif ann_type == 'unmute':
            from botc.handlers import unmute_from_website
            await unmute_from_website(guild_id, category_id, self.bot, self.db)
            return
        elif ann_type == 'timer_start':
            await self._handle_timer_announcement(guild, category_id, announcement)
            return
        elif ann_type == 'call':
            from botc.handlers import call_from_website
            try:
                moved_count, dest_channel = await call_from_website(guild, category_id)
                # Get announce channel
                session = None
                if category_id:
                    session = await self.session_manager.get_session(guild_id, category_id)
                announce_channel = await self._get_announce_channel(guild, session, category_id)
                if announce_channel:
                    embed = discord.Embed(
                        title="📣 Townspeople Called",
                        color=discord.Color.gold()
                    )
                    embed.add_field(
                        name=f"{moved_count} players moved",
                        value=f"Everyone has been moved to {dest_channel.mention}",
                        inline=False
                    )
                    embed.set_footer(text="Called from website")
                    await announce_channel.send(embed=embed)
            except ValueError as e:
                logger.warning(f"Call failed: {e}")
            return
        
        # Game-related announcements require game_id
        if not game_id:
            logger.warning(f"No game_id provided for {ann_type} announcement")
            return
        
        session = None
        if category_id:
            session = await self.session_manager.get_session(guild_id, category_id)
        
        announce_channel = await self._get_announce_channel(guild, session, category_id)
        if not announce_channel:
            logger.warning(f"No announce channel found for guild {guild_id}, category {category_id}")
            return
        
        async with self.db.pool.acquire() as conn:
            game = await conn.fetchrow(
                "SELECT * FROM games WHERE game_id = $1",
                game_id
            )
        
        if not game:
            logger.warning(f"Game {game_id} not found")
            return
        
        # Call existing handler functions to create embeds
        if ann_type == 'game_start':
            # Import and call existing game start embed creation
            embed = await self._create_game_start_embed_from_website(guild, game, session)
        elif ann_type == 'game_end':
            embed = await self._create_game_end_embed_from_website(guild, game, session)
        elif ann_type == 'game_cancel':
            embed = await self._create_game_cancel_embed_from_website(guild, game, session)
        else:
            logger.warning(f"Unknown announcement type: {ann_type}")
            return
        
        if embed:
            await announce_channel.send(embed=embed)
            logger.info(f"Sent {ann_type} announcement for game {game_id} in guild {guild.id}")
    
    async def _handle_timer_announcement(self, guild: discord.Guild, category_id: int, announcement):
        """Handle timer start announcement - actually starts a timer that will call townspeople."""
        import json
        
        # Get announce channel
        session = await self.session_manager.get_session(guild.id, category_id)
        announce_channel = await self._get_announce_channel(guild, session, category_id)
        
        if not announce_channel:
            logger.warning(f"No announce channel found for timer in guild {guild.id}, category {category_id}")
            return
        
        # Parse duration from data
        data = announcement.get('data')
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                logger.error(f"Failed to parse data: {data}")
                return
        
        duration = data.get('duration', 0)
        
        # Get timer manager from bot
        timer_manager = getattr(self.bot, 'timer_manager', None)
        if not timer_manager:
            logger.error("Timer manager not found on bot")
            return
        
        # Start the actual timer (which will call townspeople when it expires)
        try:
            await timer_manager.start_timer(
                guild=guild,
                delay_seconds=duration,
                creator_name="Website",
                announce_channel=announce_channel,
                category_id=category_id
            )
            logger.info(f"Started {duration}s timer from website for guild {guild.id}, will call townspeople on completion")
        except Exception as e:
            logger.exception(f"Failed to start timer from website: {e}")
            await announce_channel.send(f"❌ Failed to start timer: {e}")
    
    async def _get_announce_channel(self, guild: discord.Guild, session, category_id: int):
        """Get the announcement channel for a session."""
        if session and session.announce_channel_id:
            channel = guild.get_channel(session.announce_channel_id)
            if channel:
                return channel
        
        if category_id:
            category = guild.get_channel(category_id)
            if category and isinstance(category, discord.CategoryChannel):
                for channel in category.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        return channel
        
        return None
    
    async def _create_game_start_embed_from_website(self, guild: discord.Guild, game, session):
        """Create game start embed."""
        from botc.constants import EMOJI_TOWN_SQUARE, EMOJI_SCRIPT, EMOJI_PLAYERS, EMOJI_CANDLE, VERSION
        from botc.utils import strip_st_prefix, add_script_emoji
        
        storyteller = guild.get_member(game['storyteller_id'])
        if not storyteller:
            return None
        
        st_name = strip_st_prefix(storyteller.display_name)
        script = game['script']
        custom_name = game.get('custom_name', '')
        display_name = custom_name if custom_name else script
        
        # Parse players
        players_data = game['players']
        if isinstance(players_data, str):
            try:
                players_list = json.loads(players_data)
            except:
                players_list = []
        elif isinstance(players_data, list):
            players_list = players_data
        else:
            players_list = []
        
        embed = discord.Embed(
            title=f"{EMOJI_TOWN_SQUARE} A New Tale Begins",
            description=f"The grimoire opens as shadows gather in the town square...",
            color=discord.Color.dark_gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"Storyteller: {st_name}", icon_url=storyteller.display_avatar.url)
        
        embed.add_field(
            name=f"**{EMOJI_SCRIPT} Script**",
            value=f"{add_script_emoji(display_name)}",
            inline=True
        )
        
        embed.add_field(
            name=f"**{EMOJI_PLAYERS} Players**",
            value=f"{len(players_list)}",
            inline=True
        )
        
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        if players_list and len(players_list) <= 25:
            valid_players = [p for p in players_list if p]
            if valid_players:
                players_text = ", ".join(valid_players)
                embed.add_field(
                    name=f"{EMOJI_CANDLE} Gathered in the Square",
                    value=players_text,
                    inline=False
                )
        
        if session and session.session_code:
            embed.add_field(
                name="🔗 Session Code",
                value=f"`{session.session_code}` - Linked from grim.hystericca.dev",
                inline=False
            )
        
        embed.set_footer(text=f"Grimkeeper v{VERSION} • Started from website")
        
        return embed
    
    async def _create_game_end_embed_from_website(self, guild: discord.Guild, game, session):
        """Create game end embed (simplified from handlers.py)."""
        from botc.constants import (
            EMOJI_GOOD_WIN, EMOJI_EVIL_WIN, EMOJI_SCRIPT, EMOJI_CLOCK, 
            EMOJI_PLAYERS, VERSION, ICON_GOOD, ICON_EVIL
        )
        from botc.utils import strip_st_prefix, add_script_emoji
        import random
        
        GOOD_WIN_MESSAGES = [
            "The last whispers of the Demon's manipulation fade away as the sun rises once more.",
            "As dawn breaks, the townspeople stand victorious. The shadows retreat.",
            "The Demon's reign of terror ends. Good triumphs."
        ]
        
        EVIL_WIN_MESSAGES = [
            "Darkness descends as the Demon's victory is complete.",
            "Evil has triumphed. The town square falls silent.",
            "The Demon laughs in the shadows. Deceit has won the day."
        ]
        
        storyteller = guild.get_member(game['storyteller_id'])
        if not storyteller:
            return None
        
        st_name = strip_st_prefix(storyteller.display_name)
        script = game['script']
        custom_name = game.get('custom_name', '')
        display_name = custom_name if custom_name else script
        script_display = add_script_emoji(display_name)
        winner = game['winner']

        duration_seconds = int(game['end_time'] - game['start_time'])
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        if winner == "Good":
            embed = discord.Embed(
                title=f"{EMOJI_GOOD_WIN} The Dawn Breaks",
                description=f"*{random.choice(GOOD_WIN_MESSAGES)}*",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=ICON_GOOD)
            embed.add_field(name=f"**🏆 Victor**", value="Good", inline=True)
        elif winner == "Evil":
            embed = discord.Embed(
                title=f"{EMOJI_EVIL_WIN} Eternal Night Falls",
                description=f"*{random.choice(EVIL_WIN_MESSAGES)}*",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=ICON_EVIL)
            embed.add_field(name=f"**🏆 Victor**", value="Evil", inline=True)
        else:
            embed = discord.Embed(
                title=f"{EMOJI_SCRIPT} The Grimoire Closes",
                description=f"*The tale ends...*",
                color=discord.Color.dark_gray(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name=f"**Result**", value=f"{winner}", inline=True)
        
        embed.set_author(name=st_name, icon_url=storyteller.display_avatar.url)
        embed.add_field(name=f"**{EMOJI_SCRIPT} Script**", value=script_display, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name=f"**{EMOJI_CLOCK} Duration**", value=duration_str, inline=True)
        embed.add_field(name=f"**{EMOJI_PLAYERS} Players**", value=f"{game['player_count']}", inline=True)
        
        start_timestamp = int(game['start_time'])
        embed.add_field(name=f"**{EMOJI_CLOCK} Began**", value=f"<t:{start_timestamp}:t>", inline=True)
        
        footer_text = f"Grimkeeper v{VERSION} • Ended from website"
        if session and session.session_code:
            footer_text += f" • Session: {session.session_code}"
        embed.set_footer(text=footer_text)
        
        return embed
    
    async def _create_game_cancel_embed_from_website(self, guild: discord.Guild, game, session):
        """Create game cancel embed."""
        from botc.constants import EMOJI_SCRIPT, EMOJI_PLAYERS, EMOJI_CLOCK, VERSION
        
        storyteller = None
        if game.get('storyteller_id'):
            storyteller = guild.get_member(game['storyteller_id'])
        
        st_name = storyteller.display_name if storyteller else "Unknown Storyteller"
        script_name = game.get('custom_name') or game.get('script', 'Unknown Script')
        script_display = script_name if script_name else "Custom Script"
        
        embed = discord.Embed(
            title="📕 Game Canceled",
            description="*The grimoire closes, the tale untold...*",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.set_author(name=st_name, icon_url=storyteller.display_avatar.url if storyteller else None)
        embed.add_field(name=f"**{EMOJI_SCRIPT} Script**", value=script_display, inline=True)
        embed.add_field(name=f"**{EMOJI_PLAYERS} Players**", value=f"{game.get('player_count', 0)}", inline=True)
        
        if game.get('start_time'):
            start_timestamp = int(game['start_time'])
            embed.add_field(name=f"**{EMOJI_CLOCK} Started**", value=f"<t:{start_timestamp}:R>", inline=True)
        
        footer_text = f"Grimkeeper v{VERSION} • Canceled from website"
        if session and session.session_code:
            footer_text += f" • Session: {session.session_code}"
        embed.set_footer(text=footer_text)
        
        return embed

