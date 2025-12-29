"""Timer manager for scheduled 'call townspeople' tasks.

Provides a TimerManager class that encapsulates scheduling, persistence, and
the background timer task. This avoids keeping timer globals in main.py and
makes testing and reuse easier.
"""
from __future__ import annotations

import asyncio
import time
import aiohttp
from typing import Callable, TYPE_CHECKING
import logging
import discord

from botc.constants import DELETE_DELAY_DRAMATIC, DELETE_DELAY_ERROR

if TYPE_CHECKING:
    from botc.database import Database

logger = logging.getLogger('botc_bot')

GRIMLIVE_API_URL = "https://api.hystericca.dev"


class TimerManager:
    def __init__(self, bot: discord.Client, db: 'Database', call_townspeople: Callable[[discord.Guild, int | None], tuple[int, discord.VoiceChannel]]):
        self.bot = bot
        self.db = db
        self.call_townspeople = call_townspeople
        # guild_id (int) -> {task, end_time, creator, announce_msg, category_id, is_paused, paused_remaining}
        self.scheduled_timers: dict[int, dict] = {}
    
    async def _call_grimlive_api(self, endpoint: str, data: dict) -> bool:
        """Call grimlive API to sync timer state."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{GRIMLIVE_API_URL}/{endpoint}", json=data, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        logger.info(f"Successfully synced {endpoint} to grimlive API")
                        return True
                    else:
                        logger.warning(f"Grimlive API {endpoint} returned status {response.status}")
                        return False
        except asyncio.TimeoutError:
            logger.warning(f"Timeout calling grimlive API {endpoint}")
            return False
        except Exception as e:
            logger.error(f"Error calling grimlive API {endpoint}: {e}")
            return False
    
    async def _get_session_code(self, guild_id: int, category_id: int | None) -> str | None:
        """Get session code for guild and category from database."""
        try:
            if not category_id:
                return None
            result = await self.db.pool.fetchrow(
                'SELECT session_code FROM sessions WHERE guild_id = $1 AND category_id = $2',
                guild_id, category_id
            )
            return result['session_code'] if result else None
        except Exception as e:
            logger.error(f"Error getting session code: {e}")
            return None

    async def save_timers(self) -> None:
        """Save all active timers to database"""
        try:
            for guild_id, info in self.scheduled_timers.items():
                await self.db.save_timer(
                    guild_id=guild_id,
                    end_time=int(info["end_time"]),
                    creator_id=info["creator"],
                    category_id=info.get("category_id")
                )
        except Exception:
            logger.exception("Error saving timers to database")

    async def load_timers(self) -> None:
        """Load and restore timers from database on bot restart"""
        try:
            timers = await self.db.get_all_timers()
            now = time.time()
            
            for timer in timers:
                guild_id = timer["guild_id"]
                end_time = timer["end_time"]
                remaining = end_time - now
                
                if remaining > 0:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        # Get session-scoped announce channel
                        category_id = timer.get("category_id")
                        announce_channel = None
                        
                        # Try to get session announce channel first
                        session_manager = getattr(self.bot, "session_manager", None)
                        if session_manager and category_id:
                            session = await session_manager.get_session(guild_id, category_id)
                            if session and session.announce_channel_id:
                                announce_channel = guild.get_channel(session.announce_channel_id)
                        
                        # Fallback to guild system channel
                        if not announce_channel:
                            announce_channel = guild.system_channel
                        
                        if announce_channel:
                            task = asyncio.create_task(self._timer_and_call(remaining, guild, announce_channel, category_id))
                            self.scheduled_timers[guild_id] = {
                                "task": task,
                                "end_time": end_time,
                                "creator": timer.get("creator_id"),
                                "announce_msg": None,
                                "category_id": category_id
                            }
                            logger.info(f"Restored timer for guild {guild.name} with {int(remaining)}s remaining")
                else:
                    # Timer expired while bot was offline, remove it
                    await self.db.delete_timer(guild_id)
        except Exception:
            logger.exception("Error loading timers from database")

    async def _timer_and_call(self, delay_seconds: int, guild: discord.Guild, announce_channel: discord.TextChannel, category_id: int | None = None) -> None:
        try:
            await asyncio.sleep(delay_seconds)

            # Immediately announce timer completion
            await announce_channel.send("# ⏰ TIME'S UP!")

            # Then try to call townspeople and announce results
            try:
                moved_count, dest_channel = await self.call_townspeople(guild, category_id)

                embed = discord.Embed(
                    title="📣 Townspeople Called",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name=f"{moved_count} players moved",
                    value=f"Everyone has been moved to {dest_channel.mention}",
                    inline=False
                )
                embed.set_footer(text="Called by timer")

                msg = await announce_channel.send(embed=embed)
                await msg.delete(delay=DELETE_DELAY_DRAMATIC)
            except ValueError as e:
                msg = await announce_channel.send(f"❌ {e}")
                await msg.delete(delay=DELETE_DELAY_ERROR)
            except Exception as e:
                logger.error(f"Timer call error: {e}")
                msg = await announce_channel.send("❌ An error occurred while calling townspeople.")
                await msg.delete(delay=DELETE_DELAY_ERROR)

        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Timer error")
            try:
                msg = await announce_channel.send("⏰ Timer expired, but an error occurred.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
            except Exception as e:
                logger.error(f"Could not send timer error message: {e}")
        finally:
            try:
                gid = guild.id
                info = self.scheduled_timers.pop(gid, None)
                if info and info.get("announce_msg"):
                    try:
                        await info["announce_msg"].delete()
                    except Exception:
                        logger.exception("Failed to delete announce_msg during timer cleanup")
                # Remove timer from database
                await self.db.delete_timer(gid)
            except Exception:
                logger.exception("Error during timer cleanup in finally block")

    def start_timer(self, seconds: int, guild: discord.Guild, announce_channel: discord.TextChannel, creator: int, announce_msg: discord.Message | None = None, category_id: int | None = None) -> asyncio.Task:
        # If a timer is already scheduled for this guild, cancel it first to
        # avoid multiple overlapping timers for the same guild.
        try:
            prev = self.scheduled_timers.get(guild.id)
            if prev and prev.get("task"):
                try:
                    prev["task"].cancel()
                except Exception:
                    logger.exception("Failed to cancel previous timer task in start_timer")
                # remove previous entry; it will be cleaned up in the task's finally block
                self.scheduled_timers.pop(guild.id, None)
        except Exception:
            logger.exception("Error while cleaning up previous timer in start_timer")

        end_time = time.time() + seconds
        # Use the event loop's create_task so tests (which may not have a
        # running loop) can still create Task objects without raising a
        # 'no running event loop' RuntimeError.
        loop = asyncio.get_event_loop()
        task = loop.create_task(self._timer_and_call(seconds, guild, announce_channel, category_id))
        # store the scheduled timer info
        self.scheduled_timers[guild.id] = {
            "task": task, 
            "end_time": end_time, 
            "creator": creator, 
            "announce_msg": announce_msg, 
            "category_id": category_id,
            "is_paused": False,
            "paused_remaining": 0
        }
        
        # Sync to grimlive API
        asyncio.create_task(self._sync_timer_start(guild.id, seconds, category_id, creator))
        
        return task
    
    async def _sync_timer_start(self, guild_id: int, duration: int, category_id: int | None, creator: int):
        """Sync timer start to grimlive API."""
        session_code = await self._get_session_code(guild_id, category_id)
        if session_code:
            await self._call_grimlive_api('api/timer/start', {
                'sessionCode': session_code,
                'duration': duration,
                'discordUserId': creator
            })

    def pause_timer(self, guild_id: int) -> tuple[bool, str]:
        """Pause an active timer for a guild.
        
        Returns:
            (success, message) tuple
        """
        info = self.scheduled_timers.get(guild_id)
        if not info:
            return (False, "No active timer to pause.")
        
        if info.get("is_paused"):
            return (False, "Timer is already paused.")
        
        # Calculate remaining time
        remaining = int(info["end_time"] - time.time())
        if remaining <= 0:
            return (False, "Timer has already expired.")
        
        # Cancel the current task
        try:
            info["task"].cancel()
        except Exception as e:
            logger.error(f"Error canceling timer task: {e}")
        
        # Store pause state
        info["is_paused"] = True
        info["paused_remaining"] = remaining
        logger.info(f"Timer paused for guild {guild_id} with {remaining}s remaining")
        
        # Sync to grimlive API
        category_id = info.get("category_id")
        asyncio.create_task(self._sync_timer_pause(guild_id, category_id))
        
        return (True, f"⏸️ Timer paused with {remaining}s remaining.")
    
    async def _sync_timer_pause(self, guild_id: int, category_id: int | None):
        """Sync timer pause to grimlive API."""
        session_code = await self._get_session_code(guild_id, category_id)
        if session_code:
            await self._call_grimlive_api('api/timer/pause', {
                'sessionCode': session_code
            })

    def resume_timer(self, guild_id: int, announce_channel: discord.TextChannel) -> tuple[bool, str]:
        """Resume a paused timer for a guild.
        
        Returns:
            (success, message) tuple
        """
        info = self.scheduled_timers.get(guild_id)
        if not info:
            return (False, "No timer to resume.")
        
        if not info.get("is_paused"):
            return (False, "Timer is not paused.")
        
        remaining = info.get("paused_remaining", 0)
        if remaining <= 0:
            return (False, "No remaining time to resume.")
        
        # Get guild and category_id
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return (False, "Guild not found.")
        
        category_id = info.get("category_id")
        
        # Create new task with remaining time
        loop = asyncio.get_event_loop()
        task = loop.create_task(self._timer_and_call(remaining, guild, announce_channel, category_id))
        
        # Update timer info
        info["task"] = task
        info["end_time"] = time.time() + remaining
        info["is_paused"] = False
        info["paused_remaining"] = 0
        
        logger.info(f"Timer resumed for guild {guild_id} with {remaining}s remaining")
        
        # Sync to grimlive API
        asyncio.create_task(self._sync_timer_resume(guild_id, category_id))
        
        return (True, f"▶️ Timer resumed with {remaining}s remaining.")
    
    async def _sync_timer_resume(self, guild_id: int, category_id: int | None):
        """Sync timer resume to grimlive API."""
        session_code = await self._get_session_code(guild_id, category_id)
        if session_code:
            await self._call_grimlive_api('api/timer/resume', {
                'sessionCode': session_code
            })
    
    def stop_timer(self, guild_id: int) -> tuple[bool, str]:
        """Stop/cancel an active timer for a guild.
        
        Returns:
            (success, message) tuple
        """
        info = self.scheduled_timers.get(guild_id)
        if not info:
            return (False, "No active timer to stop.")
        
        # Cancel the task
        try:
            info["task"].cancel()
        except Exception as e:
            logger.error(f"Error canceling timer task: {e}")
        
        # Delete announce message if exists
        try:
            if info.get("announce_msg"):
                asyncio.create_task(info["announce_msg"].delete())
        except Exception as e:
            logger.error(f"Error deleting announce message: {e}")
        
        category_id = info.get("category_id")
        
        # Remove from scheduled timers
        self.scheduled_timers.pop(guild_id, None)
        
        # Sync to grimlive API
        asyncio.create_task(self._sync_timer_stop(guild_id, category_id))
        
        logger.info(f"Timer stopped for guild {guild_id}")
        
        return (True, "❌ Timer cancelled.")
    
    async def _sync_timer_stop(self, guild_id: int, category_id: int | None):
        """Sync timer stop to grimlive API."""
        session_code = await self._get_session_code(guild_id, category_id)
        if session_code:
            await self._call_grimlive_api('api/timer/stop', {
                'sessionCode': session_code
            })
