"""Utility helpers extracted from main.py.

Functions here are pure helpers (parsing/formatting) to keep main.py smaller
and easier to test.
"""
from __future__ import annotations

import re
import os
import json
import logging
import tempfile
from typing import Union, Optional
from pathlib import Path

import discord
from botc.constants import PREFIX_ST, PREFIX_COST, PREFIX_BRB, PREFIX_SPEC
from botc.database import DatabaseError

logger = logging.getLogger("botc_bot")


def parse_duration(duration_str: str) -> int:
    """Parse a flexible duration string into seconds.

    Supports colon formats (MM:SS, HH:MM:SS), and sequences like '1h30m'.
    Raises ValueError for invalid formats.
    """
    s = (duration_str or "").strip().lower()
    if not s:
        raise ValueError("empty duration")

    # Colon formats: H:M:S or M:S
    if ':' in s:
        parts = s.split(':')
        if not all(p.isdigit() for p in parts):
            raise ValueError("invalid colon duration")
        parts = [int(p) for p in parts]
        if len(parts) == 2:
            minutes, secs = parts
            return minutes * 60 + secs
        if len(parts) == 3:
            hours, minutes, secs = parts
            return hours * 3600 + minutes * 60 + secs
        raise ValueError("invalid colon duration")

    # Match number+unit segments, e.g. '1h', '30m', '90s', allowing multiple segments
    total = 0
    any_match = False
    for m in re.finditer(r"(\d+)\s*(d|h|m|s)?", s):
        any_match = True
        val = int(m.group(1))
        unit = m.group(2)
        if not unit:
            # unitless numbers treated as seconds
            total += val
        elif unit == 'd':
            total += val * 86400
        elif unit == 'h':
            total += val * 3600
        elif unit == 'm':
            total += val * 60
        elif unit == 's':
            total += val

    if any_match and total > 0:
        return total

    # fallback: if the whole string is digits, treat as seconds
    if s.isdigit():
        return int(s)

    raise ValueError("could not parse duration")


def humanize_seconds(seconds: Union[int, float]) -> str:
    """Return a human-friendly duration like '1h 30m'."""
    parts = []
    secs = int(seconds)
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    minutes, secs = divmod(secs, 60)
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return ' '.join(parts)


def format_end_time(epoch_seconds: float) -> str:
    """Return Discord-friendly timestamp markup for a given epoch seconds.

    Example: <t:1615555200:T>
    """
    return f"<t:{int(epoch_seconds)}:T>"


def write_json_atomic(path: Path | str, data, *, indent: int = 2, ensure_ascii: bool = False) -> None:
    """Write JSON to `path` atomically.

    - Writes to a temporary file in the same directory, fsyncs, then atomically
      replaces the target file. This avoids corrupting the file if the process
      is killed mid-write.
    - Uses json.dump with the given indent and ensure_ascii options.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name, dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        # Atomic replace
        os.replace(tmp, str(p))
    except Exception:
        # If anything goes wrong, ensure temp file removed
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise


# ============================================================================
# Discord Member & Guild Utilities
# ============================================================================

async def get_botc_category(guild: discord.Guild, db) -> Optional[discord.CategoryChannel]:
    """
    Get the BOTC category for a guild.
    First tries configured category ID from database, then falls back to name matching.
    
    Args:
        guild: Discord guild to search
        db: Database connection
        
    Returns:
        CategoryChannel if found, None otherwise
    """
    guild_id = guild.id
    botc_category = None
    
    # Try configured category ID first
    guild_config = await db.get_guild(guild_id)
    if guild_config and guild_config.get("botc_category_id"):
        cfg_cat_id = guild_config["botc_category_id"]
        botc_category = next((c for c in guild.categories if c.id == cfg_cat_id), None)
    
    # Fallback to name matching
    if not botc_category:
        for category in guild.categories:
            if category.name and category.name.lower() in ["botc", "bot c", "🩸• blood on the clocktower", "blood on the clocktower"]:
                botc_category = category
                break
    
    return botc_category


async def get_session_from_channel(channel: discord.abc.GuildChannel, session_manager):
    """
    Get the session for a channel based on its category.
    
    Args:
        channel: Discord channel to resolve session for
        session_manager: Session manager instance
        
    Returns:
        Session object if found, None otherwise
    """
    if not session_manager or not channel.category:
        return None
    
    guild = channel.guild
    return await session_manager.get_session_from_channel(channel, guild)


async def get_exception_channel_ids(guild: discord.Guild, db) -> set[int]:
    """Get set of voice channel IDs that should be excluded from *call operations.
    
    These channels will be skipped when performing `*call` or timer-driven calls.
    Typically used for storyteller consultation rooms.
    
    Args:
        guild: Discord guild to check
        db: Database connection
        
    Returns:
        Set of channel IDs to exclude from mass moves
    """
    guild_id = guild.id
    ids: set[int] = set()
    try:
        guild_config = await db.get_guild(guild_id)
        if guild_config and guild_config.get("exception_channel_id"):
            ids.add(int(guild_config["exception_channel_id"]))
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid exception_channel_id for guild {guild_id}: {e}")
    except DatabaseError as e:
        logger.error(f"Database error fetching exception channels for guild {guild_id}: {e}")
    return ids


def is_storyteller(member: discord.Member) -> bool:
    """Check if a member is a storyteller (ST or Co-ST).
    
    Checks if member has ST/Co-ST prefix in their nickname.
    Both ST and Co-ST have equal command permissions.
    
    Args:
        member: Discord member to check
        
    Returns:
        True if member has ST/Co-ST prefix, False otherwise
    """
    if not member:
        return False
    
    # Check nickname prefix (both ST and Co-ST)
    if member.nick:
        nick = strip_brb_prefix(member.nick)
        return (nick.startswith(PREFIX_ST) or nick.startswith(PREFIX_COST))
    
    return False


def is_main_storyteller(member: discord.Member) -> bool:
    """Check if a member is the MAIN storyteller (ST, not Co-ST).
    
    Used for stat tracking - only main ST gets credit for games.
    
    Args:
        member: Discord member to check
        
    Returns:
        True if member has ST prefix (not Co-ST), False otherwise
    """
    if not member or not member.nick:
        return False
    
    nick = strip_brb_prefix(member.nick)
    return nick.startswith(PREFIX_ST)


def strip_st_prefix(display_name: str) -> str:
    """Remove storyteller prefix from display name if present.
    
    Args:
        display_name: The member's display name
        
    Returns:
        Display name without (ST) or (Co-ST) prefix
    """
    name = display_name
    if name.startswith(PREFIX_ST):
        name = name[len(PREFIX_ST):]
    elif name.startswith(PREFIX_COST):
        name = name[len(PREFIX_COST):]
    return name


def strip_brb_prefix(nickname: str) -> str:
    """Remove BRB prefix from nickname if present.
    
    Args:
        nickname: The member's nickname
        
    Returns:
        Nickname without (BRB) prefix
    """
    if nickname.startswith(PREFIX_BRB):
        return nickname[len(PREFIX_BRB):]
    return nickname


def get_member_name(member: discord.Member) -> str:
    """
    Get the display name for a member (nick if available, else display_name).
    
    Args:
        member: Discord member
        
    Returns:
        Member's nickname if set, otherwise display_name, or empty string
    """
    return member.nick or member.display_name or ""


def get_player_role(member: discord.Member) -> tuple[str, bool]:
    """
    Extract player name and determine if member is a player (not ST/Co-ST/Spectator).
    
    Args:
        member: Discord member to check
        
    Returns:
        Tuple of (player_name, is_player)
        - player_name: Display name with prefixes stripped
        - is_player: True if member should count as player (not ST/spectator)
    """
    display_name = get_member_name(member)
    player_name = display_name
    
    # Remove all prefixes to get base name
    for prefix in [PREFIX_BRB, PREFIX_ST, PREFIX_COST, PREFIX_SPEC]:
        if player_name.startswith(prefix):
            player_name = player_name[len(prefix):]
    
    # Determine if this is actually a player (not ST or spectator)
    is_player = True
    stripped_nick = strip_brb_prefix(display_name)
    if stripped_nick.startswith(PREFIX_ST) or \
       stripped_nick.startswith(PREFIX_COST) or \
       stripped_nick.startswith(PREFIX_SPEC):
        is_player = False
    
    return player_name, is_player


def is_admin(member: Optional[discord.Member]) -> bool:
    """Check if a member has administrator permissions.
    
    Args:
        member: Discord member to check
        
    Returns:
        True if member has administrator permissions, False otherwise
    """
    return member is not None and member.guild_permissions.administrator
