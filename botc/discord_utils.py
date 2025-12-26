"""Discord interaction and message utilities.

Helper functions to reduce duplication when working with Discord.py interactions.
"""
from __future__ import annotations

import logging
from typing import Optional

import discord

logger = logging.getLogger('botc_bot')


async def safe_send_interaction(
    interaction: discord.Interaction,
    content: str = None,
    embed: discord.Embed = None,
    ephemeral: bool = True
) -> bool:
    """Safely send interaction response, handling already-responded cases."""
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
        return True
    except discord.HTTPException as e:
        logger.debug(f"Could not send interaction response: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending interaction response: {e}")
        return False


async def safe_defer(interaction: discord.Interaction, ephemeral: bool = False) -> bool:
    """Safely defer an interaction response."""
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)
            return True
        return False
    except discord.HTTPException as e:
        logger.debug(f"Could not defer interaction: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deferring interaction: {e}")
        return False


async def safe_send_message(
    channel: discord.TextChannel,
    content: str = None,
    embed: discord.Embed = None,
    delete_after: float = None
) -> Optional[discord.Message]:
    """Safely send a message to a channel, handling errors gracefully."""
    try:
        return await channel.send(content=content, embed=embed, delete_after=delete_after)
    except discord.Forbidden:
        logger.warning(f"Missing permission to send message in {channel.name}")
        return None
    except discord.HTTPException as e:
        logger.error(f"HTTP error sending message to {channel.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending message to {channel.name}: {e}")
        return None
