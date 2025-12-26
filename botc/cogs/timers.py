from __future__ import annotations

import time
import logging
import asyncio
import discord
from discord.ext import commands

from botc.constants import (
    DELETE_DELAY_CONFIRMATION,
    DELETE_DELAY_NORMAL,
    DELETE_DELAY_INFO,
    DELETE_DELAY_ERROR,
    MAX_DURATION_SECONDS,
)
from botc.utils import parse_duration, humanize_seconds, format_end_time

logger = logging.getLogger('botc_bot')


class Timers(commands.Cog):
    """Cog that handles timer-related commands.

    Handles:
    - /timer slash command (set timers with optional descriptions)
    - *timer prefix command (set timers with duration and optional description)
    - Shorthand timers (*3m, *5m, *1h, etc.) - requires ST and active game
    - Timer deletion and status checking
    
    Voice commands (*call, *mute, *unmute) are now handled by the VoiceCommands cog.

    Expects main `bot` to expose:
      - bot.is_storyteller(member)
      - bot.timer_manager (TimerManager instance) or None
      - bot.get_session_from_channel(channel) -> Session | None
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _require_active_game(self, message: discord.Message, session=None) -> bool:
        """Check if there's an active game in the session, send error if not.
        
        Args:
            message: The Discord message for context
            session: Optional Session object (will be fetched if not provided)
            
        Returns:
            True if active game exists, False otherwise
        """
        # Get session if not provided
        if not session:
            get_session_func = getattr(self.bot, "get_session_from_channel", None)
            if get_session_func:
                session = await get_session_func(message.channel, self.bot.session_manager)
        
        if not session:
            logger.info(f"Timer command used but no session found in channel {message.channel.name}")
            msg = await message.channel.send("⚠️ No session found. This command must be used in a session category. Use `/setbotc` to create one.")
            await msg.delete(delay=DELETE_DELAY_ERROR)
            return False
        
        # Check for active game
        db = getattr(self.bot, "db", None)
        if db:
            active_game = await db.get_active_game(message.guild.id, session.category_id)
            if not active_game:
                logger.info(f"Timer command used but no active game in session {session.category_id}")
                msg = await message.channel.send("❌ No active game found. Use `/startgame` first!")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return False
        
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        content = (message.content or "").strip()
        content_lower = content.lower()
        author = message.author
        if not content:
            return

        # Shorthand timer: *3m, *5m, *1h, *4:30, *5m30s, etc.
        # NOTE: *call, *mute, *unmute are now handled by VoiceCommands cog
        if content_lower.startswith("*") and len(content) > 1 and not content_lower.startswith(("*timer", "*poll")):
            # Check if it's a duration shorthand (e.g., *3m, *5m, *1h30m, *4:30)
            potential_duration = content[1:].strip()
            # Try to parse as a duration - let parse_duration handle validation
            if potential_duration:
                # Try to parse it as a duration
                try:
                    seconds = parse_duration(potential_duration)
                except Exception:
                    # Not a valid duration, continue to other command handlers
                    return
                
                if seconds > 0 and seconds <= MAX_DURATION_SECONDS:
                    # This is a valid duration shorthand!
                    # Must be storyteller
                    if not getattr(self.bot, "is_storyteller", lambda m: False)(author):
                        # Silently ignore - could be another command
                        logger.info(f"Shorthand timer ignored - {author.name} is not a storyteller")
                        return
                    
                    # Validate channel is in a BOTC category with a session
                    if not message.channel.category:
                        logger.info(f"Shorthand timer failed - no category for channel {message.channel.name}")
                        msg = await message.channel.send("⚠️ This command must be run in a channel within a category.")
                        await msg.delete(delay=DELETE_DELAY_ERROR)
                        return
                    
                    session_manager = getattr(self.bot, "session_manager", None)
                    if session_manager:
                        session = await session_manager.get_session(message.guild.id, message.channel.category.id)
                        if not session:
                            logger.info(f"Shorthand timer failed - no session for category {message.channel.category.name}")
                            msg = await message.channel.send("⚠️ This category isn't linked to a session yet. Run `/setbotc` to set it up.")
                            await msg.delete(delay=DELETE_DELAY_ERROR)
                            return
                    
                    # Get category and check for active game
                    category_id = None
                    get_session_func = getattr(self.bot, "get_session_from_channel", None)
                    if get_session_func:
                        session = await get_session_func(message.channel, self.bot.session_manager)
                        if session:
                            category_id = session.category_id
                    
                    # Require active game
                    if not await self._require_active_game(message):
                        return
                    
                    timer_manager = getattr(self.bot, "timer_manager", None)
                    if not timer_manager:
                        return
                    
                    # Cancel previous timer if exists
                    prev = timer_manager.scheduled_timers.get(message.guild.id)
                    if prev:
                        try:
                            prev["task"].cancel()
                        except Exception:
                            pass
                        try:
                            if prev.get("announce_msg"):
                                await prev["announce_msg"].delete()
                        except Exception:
                            pass
                        timer_manager.scheduled_timers.pop(message.guild.id, None)
                        await timer_manager.save_timers()
                    
                    # Set new timer
                    end_time = time.time() + seconds
                    human = humanize_seconds(seconds)
                    endt = format_end_time(end_time)
                    announce_msg = await message.channel.send(f"⏰ Timer set for {human} (ends at {endt}). Use `*timer` or `*timer cancel`.")
                    timer_manager.start_timer(seconds, message.guild, message.channel, message.author.id, announce_msg=announce_msg, category_id=category_id)
                    await timer_manager.save_timers()
                    return

        # *timer handling
        if content_lower.startswith("*timer"):
            timer_manager = getattr(self.bot, "timer_manager", None)
            
            # status check
            if content_lower == "*timer":
                if not timer_manager:
                    msg = await message.channel.send("⚠️ Timer manager not available.")
                    await msg.delete(delay=DELETE_DELAY_ERROR)
                    return
                    
                info = timer_manager.scheduled_timers.get(message.guild.id)
                if not info:
                    msg = await message.channel.send("⏱️ No timer currently running.")
                    await msg.delete(delay=DELETE_DELAY_INFO)
                    return
                remaining = int(info["end_time"] - time.time())
                if remaining < 0:
                    remaining = 0
                human = humanize_seconds(remaining)
                endt = format_end_time(info["end_time"])
                msg = await message.channel.send(f"⏳ Active timer: {human} remaining (ends at {endt}).")
                await msg.delete(delay=DELETE_DELAY_INFO)
                return

            args = content.split(maxsplit=1)
            arg = args[1].strip() if len(args) > 1 else ""

            # Allow anyone to cancel timers, only storytellers can set them
            if arg and arg.lower() not in ("cancel", "stop"):
                if not getattr(self.bot, "is_storyteller", lambda m: False)(author):
                    msg = await message.channel.send("Only storytellers can set timers for townspeople.")
                    await msg.delete(delay=DELETE_DELAY_NORMAL)
                    return
            
            # Validate channel is in a BOTC category with a session (only for setting timers, not checking status)
            if arg and arg.lower() not in ("cancel", "stop"):
                if not message.channel.category:
                    msg = await message.channel.send("⚠️ This command must be run in a channel within a category.")
                    await msg.delete(delay=DELETE_DELAY_ERROR)
                    return
                
                session_manager = getattr(self.bot, "session_manager", None)
                if session_manager:
                    session = await session_manager.get_session(message.guild.id, message.channel.category.id)
                    if not session:
                        msg = await message.channel.send("⚠️ This category isn't configured for BOTC yet. Run `/setbotc` to set it up.")
                        await msg.delete(delay=DELETE_DELAY_ERROR)
                        return

            if arg.lower() in ("cancel", "stop"):
                if not timer_manager:
                    msg = await message.channel.send("Timer manager not available.")
                    await msg.delete(delay=DELETE_DELAY_CONFIRMATION)
                    return
                
                success, response = timer_manager.stop_timer(message.guild.id)
                msg = await message.channel.send(response)
                await msg.delete(delay=DELETE_DELAY_CONFIRMATION)
                
                if success:
                    await timer_manager.save_timers()
                return
            
            if arg.lower() == "pause":
                if not timer_manager:
                    msg = await message.channel.send("Timer manager not available.")
                    await msg.delete(delay=DELETE_DELAY_CONFIRMATION)
                    return
                
                success, response = timer_manager.pause_timer(message.guild.id)
                msg = await message.channel.send(response)
                await msg.delete(delay=DELETE_DELAY_CONFIRMATION)
                
                if success:
                    await timer_manager.save_timers()
                return
            
            if arg.lower() == "resume":
                if not timer_manager:
                    msg = await message.channel.send("Timer manager not available.")
                    await msg.delete(delay=DELETE_DELAY_CONFIRMATION)
                    return
                
                success, response = timer_manager.resume_timer(message.guild.id, message.channel)
                msg = await message.channel.send(response)
                await msg.delete(delay=DELETE_DELAY_CONFIRMATION)
                
                if success:
                    await timer_manager.save_timers()
                return

            # set duration
            dur = arg
            try:
                seconds = parse_duration(dur)
                if seconds <= 0:
                    raise ValueError()
                if seconds > MAX_DURATION_SECONDS:
                    seconds = MAX_DURATION_SECONDS
            except Exception:
                msg = await message.channel.send("Invalid duration. Use seconds, colon format, or combined units (e.g. `30`, `5m`, `1h30m`, `1:30`).")
                await msg.delete(delay=DELETE_DELAY_CONFIRMATION)
                return

            if not timer_manager:
                msg = await message.channel.send("Timer manager not available.")
                await msg.delete(delay=DELETE_DELAY_CONFIRMATION)
                return

            # Get category_id from current channel context
            category_id = None
            get_session_func = getattr(self.bot, "get_session_from_channel", None)
            if get_session_func:
                session = await get_session_func(message.channel, self.bot.session_manager)
                if session:
                    category_id = session.category_id
            
            # Require active game
            if not await self._require_active_game(message):
                return
                
            prev = timer_manager.scheduled_timers.get(message.guild.id)
            if prev:
                try:
                    prev["task"].cancel()
                except Exception:
                    logger.exception("Failed to cancel previous timer task")
                try:
                    if prev.get("announce_msg"):
                        await prev["announce_msg"].delete()
                except Exception:
                    logger.exception("Failed to delete previous timer announce message")
                timer_manager.scheduled_timers.pop(message.guild.id, None)
                await timer_manager.save_timers()
                cancel_msg = await message.channel.send("⏱️ Previous timer cancelled - setting new timer...")
                await cancel_msg.delete(delay=DELETE_DELAY_NORMAL)

            end_time = time.time() + seconds
            human = humanize_seconds(seconds)
            endt = format_end_time(end_time)
            announce_msg = await message.channel.send(f"⏰ Timer set for {human} (ends at {endt}). Use `*timer` or `*timer cancel`.")
            timer_manager.start_timer(seconds, message.guild, message.channel, message.author.id, announce_msg=announce_msg, category_id=category_id)
            await timer_manager.save_timers()
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Timers(bot))
