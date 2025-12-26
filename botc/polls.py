"""Poll creation and poll-end handling extracted from main.py.

create_poll_internal now requires a get_active_players callable to avoid
import cycles with main.py.
"""
from __future__ import annotations

import time
import logging
import asyncio
import discord
from typing import Callable, List, Tuple, Dict, Awaitable

from botc.constants import POLL_EMOJI_MAP, POLL_SCRIPT_MAP, POLL_VALID_OPTIONS, MAX_POLL_DURATION, EMOJI_SCROLL
from botc.utils import parse_duration, humanize_seconds, format_end_time

logger = logging.getLogger('botc_bot')


async def _end_poll(delay_seconds: int, poll_message: discord.Message, options: List[str], emoji_map: Dict[str, str], script_map: Dict[str, str], creator_id: int) -> None:
    """Wait for poll to finish, then announce results."""
    try:
        await asyncio.sleep(delay_seconds)

        channel = poll_message.channel
        guild = channel.guild
        try:
            poll_message = await channel.fetch_message(poll_message.id)
        except Exception as e:
            logger.info(f"Poll message was deleted before results could be announced: {e}")
            return

        creator = guild.get_member(creator_id)
        creator_mention = creator.mention if creator else ""

        vote_counts = {}
        for opt in options:
            emoji = emoji_map[opt]
            for reaction in poll_message.reactions:
                if str(reaction.emoji) == emoji:
                    vote_counts[opt] = reaction.count - 1
                    break
            else:
                vote_counts[opt] = 0
        if not vote_counts or max(vote_counts.values()) == 0:
            result_embed = discord.Embed(
                title="Poll Ended",
                description="No votes were cast!",
                color=discord.Color.light_gray()
            )
        else:
            max_votes = max(vote_counts.values())
            winners = [opt for opt, count in vote_counts.items() if count == max_votes]

            if len(winners) == 1:
                winner_opt = winners[0]
                winner_name = script_map[winner_opt]
                winner_emoji = emoji_map[winner_opt]

                result_embed = discord.Embed(
                    title="Poll Results",
                    description=f"## {winner_emoji} **{winner_name}** wins\n\n**{max_votes}** vote{'s' if max_votes != 1 else ''}",
                    color=discord.Color.gold()
                )
            else:
                winner_names = [f"{emoji_map[opt]} {script_map[opt]}" for opt in winners]
                result_embed = discord.Embed(
                    title="Poll Results",
                    description=f"## Tie between:\n\n{' and '.join(winner_names)}\n\n**{max_votes}** vote{'s' if max_votes != 1 else ''} each",
                    color=discord.Color.gold()
                )

            breakdown = ""
            for opt in options:
                count = vote_counts.get(opt, 0)
                breakdown += f"{emoji_map[opt]} {script_map[opt]}: **{count}** vote{'s' if count != 1 else ''}\n"
            result_embed.add_field(name="Full Results", value=breakdown, inline=False)

        result_embed.set_footer(text="Poll ended")

        # Send result mentioning the poll creator
        if creator_mention:
            await channel.send(content=creator_mention, embed=result_embed)
        else:
            await channel.send(embed=result_embed)

    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("Poll end error")


async def create_poll_internal(
    guild: discord.Guild,
    channel: discord.TextChannel,
    options: str,
    duration_str: str,
    creator: discord.Member,
    get_active_players: Callable[[discord.Guild], Awaitable[list]]
) -> Tuple[discord.Message, list, dict, dict, int]:
    """Shared poll creation logic."""
    options = options.lower().strip()
    if not all(char in POLL_VALID_OPTIONS for char in options):
        raise ValueError("❌ Invalid poll options. Please use only: **1** (Trouble Brewing), **2** (Sects & Violets), **3** (Bad Moon Rising), **c** (Custom), **h** (Homebrew)")

    if not options:
        raise ValueError("Please include at least one option (1, 2, 3, c, h)")

    poll_duration = parse_duration(duration_str)
    if poll_duration <= 0:
        raise ValueError("❌ Poll duration must be positive. Use formats like `5m`, `1h`, `30s`, `1h30m`, or `1:30`.")

    if poll_duration > MAX_POLL_DURATION:
        poll_duration = MAX_POLL_DURATION

    seen = set()
    unique_options = []
    for char in options:
        if char not in seen:
            seen.add(char)
            unique_options.append(char)

    end_time = time.time() + poll_duration
    human_duration = humanize_seconds(poll_duration)
    end_time_str = format_end_time(end_time)

    embed = discord.Embed(
        title=f"{EMOJI_SCROLL} Script Poll",
        description=f"React to vote for which script to play!\n\n⏱️ Ends in **{human_duration}** ({end_time_str})",
        color=discord.Color.from_rgb(138, 43, 226)
    )

    embed.set_author(name=creator.display_name, icon_url=creator.display_avatar.url)

    field_text = ""
    for opt in unique_options:
        field_text += f"{POLL_EMOJI_MAP[opt]} {POLL_SCRIPT_MAP[opt]}\n"

    embed.add_field(name="Options", value=field_text, inline=False)
    embed.set_footer(text="React to cast your vote")

    # Use provided active player getter (now async)
    try:
        active_player_mentions = await get_active_players(guild)
    except Exception as e:
        logger.exception(f"Failed to get active players for poll: {e}")
        active_player_mentions = []

    try:
        if active_player_mentions:
            mention_text = " ".join(active_player_mentions)
            poll_msg = await channel.send(content=mention_text, embed=embed)
        else:
            poll_msg = await channel.send(embed=embed)
    except Exception as e:
        logger.exception(f"Failed to send poll message: {e}")
        raise

    try:
        for opt in unique_options:
            await poll_msg.add_reaction(POLL_EMOJI_MAP[opt])
    except Exception as e:
        logger.exception(f"Failed to add reaction to poll: {e}")
        raise

    return (poll_msg, unique_options, POLL_EMOJI_MAP, POLL_SCRIPT_MAP, poll_duration)
