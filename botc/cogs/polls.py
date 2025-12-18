from __future__ import annotations

import asyncio
import logging
import discord
from discord.ext import commands

from botc.polls import create_poll_internal, _end_poll
from botc.constants import DELETE_DELAY_ERROR, DELETE_DELAY_NORMAL

logger = logging.getLogger('botc_bot')


class Polls(commands.Cog):
    """Cog that handles message-based poll commands (e.g., `*poll`).

    This cog expects the main `bot` to expose the following attributes:
      - bot.get_active_players(guild) -> list[str]
      - bot.is_storyteller(member) -> bool

    The heavy lifting for poll creation and ending lives in `botc.polls`.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Keep out of other bots' messages
        if message.author.bot:
            return

        content = (message.content or "").strip()
        content_lower = content.lower()
        author = message.author

        if not content:
            return

        # Handle *poll only; other command handling remains in main
        if content_lower.startswith("*poll"):
            # Allow storytellers (ST/Co-ST prefix) or admins to create polls
            is_st = getattr(self.bot, "is_storyteller", lambda m: False)(author)
            is_admin_user = author.guild_permissions.administrator if hasattr(author, 'guild_permissions') else False
            
            if not (is_st or is_admin_user):
                msg = await message.channel.send("⚠️ Only users with ST/Co-ST prefix or server admins can create polls. Use `*st` or `*cost` to add the prefix.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return

            # Validate channel is in a BOTC category
            if not message.channel.category:
                msg = await message.channel.send("⚠️ Polls must be run in a channel within a session category.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return

            # Validate session exists
            session_manager = getattr(self.bot, "session_manager", None)
            if session_manager:
                session = await session_manager.get_session(message.guild.id, message.channel.category.id)
                if not session:
                    msg = await message.channel.send("⚠️ This category isn't linked to a session yet. Run `/setbotc` to set it up.")
                    await msg.delete(delay=DELETE_DELAY_ERROR)
                    return

            parts = message.content.split(maxsplit=2)
            if len(parts) < 2:
                msg = await message.channel.send("Usage: `*poll [123ch] <time>` - Include options and optional time (default: 5m)")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return

            options = parts[1].lower().strip()
            duration_str = parts[2] if len(parts) > 2 else "5m"

            try:
                # Create async wrapper that passes the channel
                async def get_players_with_channel(guild):
                    get_active_players = getattr(self.bot, "get_active_players", None)
                    if not get_active_players:
                        logger.error("get_active_players not found on bot")
                        return []
                    return await get_active_players(guild, message.channel)
                
                poll_msg, unique_options, emoji_map, script_map, poll_duration = await create_poll_internal(
                    message.guild,
                    message.channel,
                    options,
                    duration_str,
                    author,
                    get_players_with_channel
                )

                # Schedule poll end task
                asyncio.create_task(_end_poll(poll_duration, poll_msg, unique_options, emoji_map, script_map, author.id))

            except ValueError as e:
                msg = await message.channel.send(str(e))
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            except Exception as e:
                logger.exception(f"Unexpected error creating poll: {e}")
                msg = await message.channel.send("❌ Failed to create poll. Please check your options and duration format.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls(bot))
