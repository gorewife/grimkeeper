"""Voice management commands cog (*call, *mute, *unmute)."""
from __future__ import annotations

import logging
import discord
from discord.ext import commands

from botc.constants import DELETE_DELAY_NORMAL, DELETE_DELAY_ERROR

logger = logging.getLogger('botc_bot')


class VoiceCommands(commands.Cog):
    """Handles voice management commands: *call, *mute, *unmute.
    
    Expects bot to expose:
      - bot.is_storyteller(member)
      - bot.call_townspeople(guild, category_id)
      - bot.session_manager
      - bot.timer_manager
      - bot.db
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _require_active_game(self, message: discord.Message, session=None) -> bool:
        """Check if there's an active game in the session."""
        if not session:
            get_session_func = getattr(self.bot, "get_session_from_channel", None)
            if get_session_func:
                session = await get_session_func(message.channel, self.bot.session_manager)
        
        if not session:
            logger.info(f"Voice command used but no session found in channel {message.channel.name}")
            msg = await message.channel.send("⚠️ No session found. Use `/setbotc` to create one.")
            await msg.delete(delay=DELETE_DELAY_ERROR)
            return False
        
        db = getattr(self.bot, "db", None)
        if db:
            active_game = await db.get_active_game(message.guild.id, session.category_id)
            if not active_game:
                logger.info(f"Voice command used but no active game in session {session.category_id}")
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

        # *call - move all players to town square
        if content_lower.startswith("*call"):
            if not getattr(self.bot, "is_storyteller", lambda m: False)(author):
                msg = await message.channel.send("Only storytellers can call townspeople.")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                return
            
            if not message.channel.category:
                msg = await message.channel.send("⚠️ This command must be run in a channel within a session category.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            session_manager = getattr(self.bot, "session_manager", None)
            if session_manager:
                session = await session_manager.get_session(message.guild.id, message.channel.category.id)
                if not session:
                    msg = await message.channel.send("⚠️ This category isn't linked to a session yet. Run `/setbotc` to set it up.")
                    await msg.delete(delay=DELETE_DELAY_ERROR)
                    return

            get_session_func = getattr(self.bot, "get_session_from_channel", None)
            category_id = None
            if get_session_func:
                session = await get_session_func(message.channel, self.bot.session_manager)
                if session:
                    category_id = session.category_id
            
            if not await self._require_active_game(message):
                return

            timer_manager = getattr(self.bot, "timer_manager", None)
            if timer_manager:
                try:
                    info = timer_manager.scheduled_timers.get(message.guild.id)
                    if info:
                        try:
                            info["task"].cancel()
                        except Exception:
                            logger.exception("Failed to cancel existing timer task")
                        try:
                            if info.get("announce_msg"):
                                await info["announce_msg"].delete()
                        except Exception:
                            logger.exception("Failed to delete existing timer announce message")
                        timer_manager.scheduled_timers.pop(message.guild.id, None)
                        await timer_manager.save_timers()
                        m = await message.channel.send("⏱️ Existing timer cancelled; executing call now.")
                        await m.delete(delay=DELETE_DELAY_NORMAL)
                except Exception:
                    logger.exception("Error while attempting to cancel and execute existing timer")

            try:
                call_func = getattr(self.bot, "call_townspeople", None)
                if call_func:
                    moved_count, dest_channel = await call_func(message.guild, category_id)
                    msg = await message.channel.send(f"✅ Called {moved_count} townspeople to {dest_channel.mention}")
                    await msg.delete(delay=DELETE_DELAY_NORMAL)
                else:
                    msg = await message.channel.send("❌ Call townspeople function not available.")
                    await msg.delete(delay=DELETE_DELAY_NORMAL)
            except ValueError as e:
                msg = await message.channel.send(str(e))
                await msg.delete(delay=DELETE_DELAY_NORMAL)
            return

        # *mute - server mute all players except storytellers
        if content_lower.startswith("*mute"):
            if not getattr(self.bot, "is_storyteller", lambda m: False)(author):
                msg = await message.channel.send("Only storytellers can use mute.")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                return
            
            if not message.channel.category:
                msg = await message.channel.send("⚠️ This command must be run in a channel within a session category.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            session_manager = getattr(self.bot, "session_manager", None)
            if session_manager:
                session = await session_manager.get_session(message.guild.id, message.channel.category.id)
                if not session:
                    msg = await message.channel.send("⚠️ This category isn't linked to a session yet. Run `/setbotc` to set it up.")
                    await msg.delete(delay=DELETE_DELAY_ERROR)
                    return
            
            if not await self._require_active_game(message):
                return

            try:
                guild = message.guild
                bot_member = guild.get_member(self.bot.user.id)
                if not bot_member.guild_permissions.mute_members:
                    msg = await message.channel.send("❌ Bot lacks 'Mute Members' permission.")
                    await msg.delete(delay=DELETE_DELAY_ERROR)
                    return
                
                category = message.channel.category
                muted_count = 0
                is_storyteller = getattr(self.bot, "is_storyteller", lambda m: False)
                
                for voice_channel in category.voice_channels:
                    for member in voice_channel.members:
                        if member.bot or is_storyteller(member):
                            continue
                        if member.voice and member.voice.mute:
                            continue
                        
                        try:
                            await member.edit(mute=True)
                            muted_count += 1
                        except discord.HTTPException as e:
                            logger.warning(f"Failed to mute {member.display_name}: {e}")
                        except Exception as e:
                            logger.error(f"Unexpected error muting {member.display_name}: {e}")
                
                if muted_count > 0:
                    msg = await message.channel.send(f"🔇 Muted {muted_count} player{'s' if muted_count != 1 else ''} (storytellers excluded)")
                else:
                    msg = await message.channel.send("🔇 No players to mute (all either storytellers or already muted)")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                
            except Exception as e:
                logger.exception(f"Error in *mute command: {e}")
                msg = await message.channel.send("❌ Failed to mute players.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
            return

        # *unmute - unmute all players
        if content_lower.startswith("*unmute"):
            if not getattr(self.bot, "is_storyteller", lambda m: False)(author):
                msg = await message.channel.send("Only storytellers can use unmute.")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                return
            
            if not message.channel.category:
                msg = await message.channel.send("⚠️ This command must be run in a channel within a category.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            try:
                guild = message.guild
                bot_member = guild.get_member(self.bot.user.id)
                if not bot_member.guild_permissions.mute_members:
                    msg = await message.channel.send("❌ Bot lacks 'Mute Members' permission.")
                    await msg.delete(delay=DELETE_DELAY_ERROR)
                    return
                
                category = message.channel.category
                unmuted_count = 0
                
                for voice_channel in category.voice_channels:
                    for member in voice_channel.members:
                        if member.bot:
                            continue
                        if member.voice and not member.voice.mute:
                            continue
                        
                        try:
                            await member.edit(mute=False)
                            unmuted_count += 1
                        except discord.HTTPException as e:
                            logger.warning(f"Failed to unmute {member.display_name}: {e}")
                        except Exception as e:
                            logger.error(f"Unexpected error unmuting {member.display_name}: {e}")
                
                if unmuted_count > 0:
                    msg = await message.channel.send(f"🔊 Unmuted {unmuted_count} player{'s' if unmuted_count != 1 else ''}")
                else:
                    msg = await message.channel.send("🔊 No players to unmute (all already unmuted)")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                
            except Exception as e:
                logger.exception(f"Error in *unmute command: {e}")
                msg = await message.channel.send("❌ Failed to unmute players.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
            return


async def setup(bot):
    await bot.add_cog(VoiceCommands(bot))
