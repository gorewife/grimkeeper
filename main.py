import asyncio
import os
import json
import time
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import logging
import discord
from typing import Optional, List, Dict, Any
from discord.ext import commands, tasks

from botc.config import get_settings
from botc.discord_utils import safe_send_interaction, safe_defer, safe_send_message
from botc.utils import (
    get_botc_category,
    get_exception_channel_ids,
    is_storyteller,
    is_main_storyteller,
    is_admin,
    strip_st_prefix,
    strip_brb_prefix,
    get_member_name,
    get_player_role,
)
from botc.constants import (
    EMOJI_PEN,
    VERSION,
    PREFIX_ST,
    PREFIX_COST,
    PREFIX_SPEC,
    PREFIX_BRB,
    DELETE_DELAY_QUICK,
    DELETE_DELAY_NORMAL,
    DELETE_DELAY_ERROR,
    DELETE_DELAY_LONG,
    COMMAND_COOLDOWN_SECONDS,
    COMMAND_COOLDOWN_LONG,
    DELETABLE_COMMANDS,
    MAX_NICK_LENGTH,
    SCRIPT_EMOJI_TB,
    SCRIPT_EMOJI_SNV,
    SCRIPT_EMOJI_BMR,
    ICON_GOOD,
    ICON_EVIL,
    EMOJI_SECTS_AND_VIOLETS,
    EMOJI_BAD_MOON_RISING,
    EMOJI_TOWN_SQUARE,
    EMOJI_SWORD,
    EMOJI_SCRIPT,
    EMOJI_PLAYERS,
    EMOJI_GOOD,
    EMOJI_GOOD_WIN,
    EMOJI_EVIL,
    EMOJI_EVIL_WIN,
    EMOJI_CLOCK,
    EMOJI_CANDLE,
    EMOJI_TROUBLE_BREWING,
    EMOJI_SCROLL,
    EMOJI_BALANCE,
    EMOJI_QUESTION,
    EMOJI_STAR,
    DATABASE_POOL_MIN_SIZE,
    DATABASE_POOL_MAX_SIZE,
    DATABASE_COMMAND_TIMEOUT,
    MAX_CHANGELOG_VERSIONS,
    DISCORD_NICKNAME_MAX_LENGTH,
)
from botc.exceptions import (
    GrimkeeperError,
    ConfigurationError,
    PermissionError as GrimkeeperPermissionError,
    DatabaseError,
    ValidationError,
)
from botc.utils import write_json_atomic, add_script_emoji
from botc.timers import TimerManager
from botc.database import Database
from botc.session import SessionManager
from botc.announcements import AnnouncementProcessor
from botc.cleanup import CleanupTask

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

settings = get_settings()
token = settings.discord_token
database_url = settings.database_url

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('botc_bot')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='*', intents=intents, help_command=None)

db = Database(database_url)

follower_targets: dict[int, int] = {}
last_player_snapshots: dict[tuple[int, Optional[int]], set[str]] = {}
command_cooldowns: dict[int, dict[str, float]] = {}
bot_initiated_nick_changes: set[tuple[int, str]] = set()

timer_manager: Optional[TimerManager] = None
session_manager: Optional[SessionManager] = None

async def get_active_players(guild: discord.Guild, channel: discord.TextChannel = None) -> list:
    active_player_mentions = []
    
    try:
        botc_category = None
        if channel and bot.session_manager and channel.category:
            session = await bot.session_manager.get_session_from_channel(channel, channel.guild)
            if session and session.category_id:
                botc_category = guild.get_channel(session.category_id)
        
        if botc_category and isinstance(botc_category, discord.CategoryChannel):
            for vc in botc_category.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    
                    _, is_player = get_player_role(member)
                    if not is_player:
                        continue
                    
                    active_player_mentions.append(member.mention)
    except Exception as e:
        logger.warning(f"Error getting active players: {e}")
    
    return active_player_mentions

def check_bot_permissions(guild: discord.Guild) -> tuple[bool, bool]:
    bot_member = guild.get_member(bot.user.id)
    if not bot_member:
        return (False, False)
    
    permissions = bot_member.guild_permissions
    return (permissions.move_members, permissions.manage_channels)


async def send_temporary(channel, content: str = None, embed: discord.Embed = None, delay: float = DELETE_DELAY_NORMAL) -> discord.Message:
    msg = await channel.send(content=content, embed=embed)
    await msg.delete(delay=delay)
    return msg


async def toggle_prefix(member: discord.Member, channel: discord.TextChannel, prefix_key: str):
    prefixes = {"brb": PREFIX_BRB, "st": PREFIX_ST, "cost": PREFIX_COST, "spe": PREFIX_SPEC}
    exclusive = ["st", "cost", "spe"]
    current_nick = get_member_name(member)
    base_nick = current_nick
    active = {}
    
    guild = member.guild
    bot_member = guild.get_member(bot.user.id)
    
    if not bot_member:
        await send_temporary(channel, "⚠️ Bot configuration error. Please contact an admin.", delay=DELETE_DELAY_ERROR)
        return
    
    if not bot_member.guild_permissions.manage_nicknames:
        await send_temporary(
            channel,
            "⚠️ Bot lacks 'Manage Nicknames' permission. Ask an admin to grant this permission.",
            delay=DELETE_DELAY_LONG
        )
        return
    
    if member.id == guild.owner_id:
        await send_temporary(
            channel,
            "⚠️ Cannot change your nickname: Discord does not allow bots to modify the server owner's nickname.\n"
            "You'll need to manually change your nickname to use prefix commands.",
            delay=DELETE_DELAY_LONG
        )
        return
    
    if member.top_role >= bot_member.top_role:
        await send_temporary(
            channel,
            f"⚠️ Cannot change nickname: {member.mention}'s highest role is above or equal to the bot's role.\n"
            "Ask an admin to move the bot's role higher in Server Settings → Roles.",
            delay=DELETE_DELAY_LONG
        )
        return
    
    for key, val in prefixes.items():
        active[key] = base_nick.startswith(val)
        if active[key]:
            base_nick = base_nick[len(val):]

    # Store old spectator state before toggling
    was_spectator = active.get("spe", False)

    if prefix_key in exclusive:
        for key in exclusive:
            if key != prefix_key:
                active[key] = False
        active[prefix_key] = not active[prefix_key]
    else:
        active[prefix_key] = not active.get(prefix_key, False)
    
    # Clean up followers if no longer a spectator
    # This handles: *! to toggle off, *st, or *cost (all remove spectator status)
    is_spectator_now = active.get("spe", False)
    if was_spectator and not is_spectator_now:
        follower_id = member.id
        if follower_id in bot.follower_targets:
            await db.remove_follower(follower_id, member.guild.id)
            bot.follower_targets.pop(follower_id)
            await clean_followers(member.guild)

    # Storyteller logic: manage session assignment (prefix-based, no role)
    if prefix_key == "st":
        guild = member.guild
        guild_id = guild.id
        
        session = None
        if bot.session_manager and channel and channel.category:
            session = await bot.session_manager.get_session_from_channel(channel, channel.guild)
        
        # Get category for this session - ONLY use current channel's category
        botc_category = None
        if session:
            botc_category = guild.get_channel(session.category_id)
        elif channel and channel.category:
            # Only use the current channel's category - don't search for other BOTC categories
            botc_category = channel.category
        
        if active["st"]:
            if session and bot.session_manager:
                session.storyteller_user_id = member.id
                await bot.session_manager.update_session(session)
            elif botc_category and bot.session_manager:
                # Create new session ONLY if in a category - don't auto-create in random categories
                # User should run /setbotc to properly configure the session first
                logger.info(f"User {member.display_name} used *st but no session exists in category {botc_category.name}. Suggest using /setbotc.")
            
            # Remove ST prefix from other members in this category ONLY
            if botc_category:
                category_members = set()
                for vc in botc_category.voice_channels:
                    for m in vc.members:
                        category_members.add(m.id)
                
                for other_member in guild.members:
                    if other_member.id == member.id:
                        continue
                    if other_member.nick and other_member.nick.startswith(PREFIX_ST) and other_member.id in category_members:
                        try:
                            new_other_nick = other_member.nick[len(PREFIX_ST):]
                            bot_initiated_nick_changes.add((other_member.id, new_other_nick))
                            await other_member.edit(nick=new_other_nick)
                        except Exception as e:
                            logger.warning(f"Could not remove ST prefix from {other_member.display_name}: {e}")
            
            # Clear grimoire link for this session
            if session:
                session.grimoire_link = None
                await bot.session_manager.update_session(session)
            else:
                await db.upsert_guild(guild_id)
        else:
            if session and bot.session_manager:
                session.storyteller_user_id = None
                await bot.session_manager.update_session(session)

    new_nick = ""
    if active.get("brb"):
        new_nick += PREFIX_BRB
    if active.get("st"):
        new_nick += PREFIX_ST
    elif active.get("cost"):
        new_nick += PREFIX_COST
    elif active.get("spe"):
        new_nick += PREFIX_SPEC
    new_nick += base_nick

    if len(new_nick) > MAX_NICK_LENGTH:
        prefix_length = len(new_nick) - len(base_nick)
        max_base_length = MAX_NICK_LENGTH - prefix_length
        base_nick = base_nick[:max_base_length]
        
        new_nick = ""
        if active.get("brb"):
            new_nick += PREFIX_BRB
        if active.get("st"):
            new_nick += PREFIX_ST
        elif active.get("cost"):
            new_nick += PREFIX_COST
        elif active.get("spe"):
            new_nick += PREFIX_SPEC
        new_nick += base_nick

    confirmation_messages = {
        "brb": f"{member.display_name} will be right back" if active.get("brb") else f"{member.display_name} is back",
        "cost": "You are now Co-Storyteller!" if active.get("cost") else "No longer Co-Storyteller.",
        "spe": "You're now spectating" if active.get("spe") else "You're no longer spectating"
    }

    try:
        bot_initiated_nick_changes.add((member.id, new_nick))
        
        await member.edit(nick=new_nick)
        
        # Send confirmation AFTER successful edit
        msg_text = confirmation_messages.get(prefix_key)
        if msg_text:
            await send_temporary(channel, msg_text, delay=DELETE_DELAY_QUICK)
    except discord.errors.Forbidden:
        await send_temporary(channel, "I don't have permission to change your nickname.", delay=DELETE_DELAY_NORMAL)
    except Exception as e:
        logger.error(f"Could not update nickname for {member.display_name}: {e}")



async def clean_followers(guild: discord.Guild) -> None:
    valid_ids = {m.id for m in guild.members}
    
    for follower_id in list(follower_targets.keys()):
        target_id = follower_targets[follower_id]
        if follower_id not in valid_ids or target_id not in valid_ids:
            follower_targets.pop(follower_id, None)
            await db.remove_follower(follower_id, guild.id)
    
    all_followers = await db.get_all_followers_for_guild(guild.id)
    for target_id, follower_ids in all_followers.items():
        if target_id not in valid_ids:
            for fid in follower_ids:
                await db.remove_follower(fid, guild.id)
                follower_targets.pop(fid, None)
            continue
        
        for fid in follower_ids:
            if fid not in valid_ids:
                await db.remove_follower(fid, guild.id)
                follower_targets.pop(fid, None)


def check_rate_limit(user_id: int, command: str, cooldown_seconds: int = COMMAND_COOLDOWN_SECONDS) -> bool:
    now = time.time()
    user_cmds = command_cooldowns.setdefault(user_id, {})
    
    last_used = user_cmds.get(command, 0)
    if now - last_used < cooldown_seconds:
        return False
    
    user_cmds[command] = now
    return True


def add_script_emoji(script_name: str) -> str:
    script_lower = script_name.lower()
    if 'trouble' in script_lower and 'brewing' in script_lower:
        return f"{EMOJI_TROUBLE_BREWING} {script_name}"
    elif 'sects' in script_lower or 'violet' in script_lower:
        return f"{EMOJI_SECTS_AND_VIOLETS} {script_name}"
    elif 'bad' in script_lower and 'moon' in script_lower:
        return f"{EMOJI_BAD_MOON_RISING} {script_name}"
    return script_name


async def call_townspeople(guild: discord.Guild, category_id: Optional[int] = None) -> tuple[int, discord.VoiceChannel]:
    guild_id = guild.id
    
    # Get session-specific configuration (required)
    dest_channel = None
    exception_ids = set()
    botc_category = None
    
    if not category_id or not session_manager:
        raise ValueError("❌ This command must be used within a BOTC session category.")
    
    session = await session_manager.get_session(guild_id, category_id)
    if not session:
        raise ValueError("❌ No session found for this category. An admin should run `/setbotc` to create a session first.")
    
    # Use session-specific configuration
    if session.destination_channel_id:
        dest_channel = guild.get_channel(session.destination_channel_id)
    if session.exception_channel_id:
        exception_ids.add(session.exception_channel_id)
    botc_category = guild.get_channel(category_id)
    
    if not dest_channel:
        raise ValueError("❌ Town Square not configured for this session. An admin should run `/settown #channel` from within this category.")
    
    if not botc_category:
        raise ValueError("❌ Could not find BOTC category. Please check the category configuration.")

    can_move, _ = check_bot_permissions(guild)
    if not can_move:
        raise ValueError("Bot lacks 'Move Members' permission. Please grant this permission in Server Settings.")

    moved_count = 0
    failed_count = 0
    
    members_to_move = []
    for channel in botc_category.voice_channels:
        if channel.id in exception_ids:
            continue
        for member in channel.members:
            if member.bot:
                continue
            try:
                if member.voice and member.voice.channel and dest_channel and member.voice.channel.id == dest_channel.id:
                    continue
            except AttributeError as e:
                # If voice state is unexpectedly None, log and include member to be safe
                logger.debug(f"Voice state check failed for {member.display_name}: {e}")
            try:
                if member.voice and member.voice.channel and member.voice.channel.id in exception_ids:
                    continue
            except AttributeError as e:
                logger.debug(f"Exception channel check failed for {member.display_name}: {e}")
            members_to_move.append(member)
    
    # Move members in batches to avoid Discord rate limits
    # Optimized batch settings for faster moves while respecting limits
    BATCH_SIZE = 15
    BATCH_DELAY = 0.08  # 80ms between batches
    
    async def move_member(member):
        try:
            await member.move_to(dest_channel)
            return True
        except discord.HTTPException as e:
            logger.warning(f"HTTP error moving {member.display_name}: {e}")
            return False
        except discord.Forbidden as e:
            logger.warning(f"Permission denied moving {member.display_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error moving {member.display_name}: {e}")
            return False
    
    if members_to_move:
        for i in range(0, len(members_to_move), BATCH_SIZE):
            batch = members_to_move[i:i + BATCH_SIZE]
            results = await asyncio.gather(*[move_member(m) for m in batch])
            moved_count += sum(results)
            failed_count += len(results) - sum(results)
            
            if i + BATCH_SIZE < len(members_to_move):
                await asyncio.sleep(BATCH_DELAY)

    return moved_count, dest_channel



try:
    timer_manager = TimerManager(bot, db, call_townspeople)
except (TypeError, ValueError) as e:
    logger.error(f"Failed to initialize TimerManager: {e}")
    timer_manager = None


async def get_session_from_channel_wrapper(channel, session_manager):
    """Wrapper for session_manager.get_session_from_channel for backwards compatibility."""
    if not session_manager or not channel or not hasattr(channel, 'category') or not channel.category:
        return None
    return await session_manager.get_session_from_channel(channel, channel.guild)

bot.get_active_players = get_active_players
bot.is_storyteller = is_storyteller
bot.is_main_storyteller = is_main_storyteller
bot.call_townspeople = call_townspeople
bot.get_session_from_channel = get_session_from_channel_wrapper
bot.timer_manager = timer_manager
bot.session_manager = None  # Will be set in on_ready after DB initialization
bot.db = db
bot.check_rate_limit = check_rate_limit
bot.is_admin = lambda member: is_admin(member, bot.db)
bot.send_temporary = send_temporary
bot.toggle_prefix = toggle_prefix
bot.get_botc_category = get_botc_category
bot.get_member_name = get_member_name
bot.get_player_role = get_player_role
bot.strip_brb_prefix = strip_brb_prefix
bot.check_bot_permissions = check_bot_permissions
bot.last_player_snapshots = last_player_snapshots
bot.follower_targets = follower_targets
bot.clean_followers = clean_followers
bot.bot_initiated_nick_changes = bot_initiated_nick_changes


from botc.handlers import start_game_handler as _start_game_handler

async def start_game_handler(interaction: discord.Interaction, script: object, custom_name: str = ""):
    """Wrapper for start_game_handler that injects bot dependencies."""
    return await _start_game_handler(interaction, bot, db, script, custom_name)

bot.start_game_handler = start_game_handler


# Use `from botc.utils import parse_duration, humanize_seconds, format_end_time`




from botc.handlers import end_game_handler as _end_game_handler

async def end_game_handler(interaction: discord.Interaction, winner: str):
    """Wrapper for end_game_handler that injects bot dependencies."""
    await _end_game_handler(interaction, bot, db, winner)

bot.end_game_handler = end_game_handler


async def stats_handler(interaction: discord.Interaction) -> None:
    """Display game statistics for the guild.
    
    Shows total games played, win rates for Good/Evil, script breakdowns, and trends.
    """
    if not check_rate_limit(interaction.user.id, "stats", COMMAND_COOLDOWN_LONG):
        await interaction.response.send_message("⏳ Please wait before using /stats again.", ephemeral=True)
        return
    
    try:
        guild = interaction.guild
        guild_id = guild.id
        
        # Fetch all game history for accurate stats (no limit)
        history = await db.get_game_history(guild_id, limit=None)
        
        if not history:
            await interaction.response.send_message("No game history recorded for this server yet.", ephemeral=True)
            return
        
        # Filter out games without valid winners and clean them up
        valid_history = []
        invalid_game_ids = []
        for game in history:
            winner = game.get("winner")
            if winner in ["Good", "Evil"]:
                valid_history.append(game)
            else:
                # Mark invalid games for deletion
                game_id = game.get("game_id")
                if game_id:
                    invalid_game_ids.append(game_id)
        
        if invalid_game_ids:
            for game_id in invalid_game_ids:
                try:
                    await db.delete_game_by_id(game_id)
                    logger.info(f"Deleted invalid game (no winner): {game_id}")
                except Exception as e:
                    logger.error(f"Failed to delete invalid game {game_id}: {e}")
        
        history = valid_history
        
        if not history:
            await interaction.response.send_message("No valid game history found. Invalid games have been cleaned up.", ephemeral=True)
            return
        
        total_games = len(history)
        good_wins = sum(1 for g in history if g.get("winner") == "Good")
        evil_wins = sum(1 for g in history if g.get("winner") == "Evil")
        
        good_rate = (good_wins / total_games * 100) if total_games > 0 else 0
        evil_rate = (evil_wins / total_games * 100) if total_games > 0 else 0
        
        scripts = {}
        script_wins = {}
        for game in history:
            script = game.get("script", "Unknown")
            if script in ["Custom Script", "Homebrew Script"]:
                script = "Custom Script"
            scripts[script] = scripts.get(script, 0) + 1
            
            winner = game.get("winner")
            if script not in script_wins:
                script_wins[script] = {"Good": 0, "Evil": 0}
            if winner in ["Good", "Evil"]:
                script_wins[script][winner] += 1
        
        embed = discord.Embed(
            title=f"{EMOJI_SCRIPT} Server Stats",
            description=f"Game stats for **{guild.name}**",
            color=discord.Color.gold()
        )
        
        # Overall stats with visual indicators
        balance = f"{EMOJI_BALANCE} Balanced" if abs(good_rate - evil_rate) < 10 else (f"{EMOJI_GOOD} Good-favored" if good_rate > evil_rate else f"{EMOJI_EVIL} Evil-favored")
        
        embed.add_field(
            name="📊 Overall Performance",
            value=(
                f"**Total Games:** {total_games}\n"
                f"**{EMOJI_GOOD} Good Wins:** {good_wins} ({good_rate:.1f}%)\n"
                f"**{EMOJI_EVIL} Evil Wins:** {evil_wins} ({evil_rate:.1f}%)\n"
                f"**Balance:** {balance}"
            ),
            inline=False
        )
        
        # Most played scripts with win rates
        if scripts:
            sorted_scripts = sorted(scripts.items(), key=lambda x: x[1], reverse=True)[:3]
            script_lines = []
            for script_name, count in sorted_scripts:
                wins = script_wins.get(script_name, {"Good": 0, "Evil": 0})
                good_pct = (wins["Good"] / count * 100) if count > 0 else 0
                evil_pct = (wins["Evil"] / count * 100) if count > 0 else 0
                
                script_lines.append(
                    f"{add_script_emoji(script_name)}\n"
                    f"**{count} games** • {EMOJI_GOOD} {good_pct:.0f}% | {EMOJI_EVIL} {evil_pct:.0f}%"
                )
            
            embed.add_field(
                name=f"{EMOJI_SCROLL} Most Played Scripts",
                value="\n\n".join(script_lines),
                inline=False
            )
        
        # Top storytellers (top 3)
        try:
            st_stats = await db.get_storyteller_stats(guild_id)
            if st_stats:
                top_sts = st_stats[:3]
                st_lines = []
                for idx, st in enumerate(top_sts, 1):
                    st_id = st['storyteller_id']
                    member = guild.get_member(st_id)
                    if member:
                        st_display = strip_st_prefix(member.display_name)
                    else:
                        st_display = st['storyteller_name'] or f"User {st_id}"
                    
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, "")
                    st_lines.append(f"{medal} {st_display} - {st['total_games']} games")
                
                embed.add_field(
                    name=f"{EMOJI_PEN} Top Storytellers",
                    value="\n".join(st_lines),
                    inline=True
                )
        except Exception as e:
            logger.warning(f"Could not fetch top storytellers: {e}")
        
        # Recent activity (last 10 games trend)
        if len(history) >= 10:
            recent_games = history[:10]  # Already sorted newest first
            recent_good = sum(1 for g in recent_games if g.get("winner") == "Good")
            recent_evil = sum(1 for g in recent_games if g.get("winner") == "Evil")
            recent_good_pct = (recent_good / 10 * 100)
            
            trend = "📈 Good trending up" if recent_good_pct > good_rate + 10 else ("📉 Evil trending up" if recent_good_pct < good_rate - 10 else "📊 Stable")
            
            embed.add_field(
                name="🔥 Recent Trend",
                value=(
                    f"Last 10 games:\n"
                    f"{EMOJI_GOOD} {recent_good} | {EMOJI_EVIL} {recent_evil}\n"
                    f"{trend}"
                ),
                inline=True
            )
        
        embed.set_footer(text=f"Use /ststats for detailed ST stats • v{VERSION}")
        await interaction.response.send_message(embed=embed)
        
    except DatabaseError as e:
        logger.error(f"Database error in stats_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to load stats. Database error.", ephemeral=True)
    except Exception as e:
        logger.exception(f"Unexpected error in stats_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to load stats. See logs.", ephemeral=True)


async def gamehistory_handler(interaction: discord.Interaction, limit: int = 50) -> None:
    """Display recent game history for the guild with pagination.
    
    Auto-detects session context: if used in a BOTC category, shows only that session's history.
    If used outside a BOTC category, shows all games across all sessions.
    
    Args:
        interaction: Discord interaction
        limit: Maximum number of recent games to fetch (default: 50)
    """
    if not check_rate_limit(interaction.user.id, "gamehistory", COMMAND_COOLDOWN_LONG):
        await interaction.response.send_message("⏳ Please wait before using /gamehistory again.", ephemeral=True)
        return
    
    try:
        guild = interaction.guild
        guild_id = guild.id
        
        # Auto-detect session context
        category_id = None
        if bot.session_manager and interaction.channel and interaction.channel.category:
            session = await bot.session_manager.get_session_from_channel(interaction.channel, guild)
            if session:
                category_id = session.category_id
        
        history = await db.get_game_history(guild_id, limit=limit, category_id=category_id)
        
        if not history:
            scope_msg = "this session" if category_id else "this server"
            await interaction.response.send_message(f"No game history recorded for {scope_msg} yet.", ephemeral=True)
            return
        
        if category_id:
            category = guild.get_channel(category_id)
            category_name = category.name if category else f"Category {category_id}"
            context_desc = f"Session: **{category_name}**"
        else:
            context_desc = f"Server: **{guild.name}**"
        
        view = GameHistoryView(history, context_desc, guild)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view)
        
    except DatabaseError as e:
        logger.error(f"Database error in gamehistory_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to load game history. Database error.", ephemeral=True)
    except Exception as e:
        logger.exception(f"Unexpected error in gamehistory_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to load game history. See logs.", ephemeral=True)


class GameHistoryView(discord.ui.View):
    """Paginated view for game history."""
    
    def __init__(self, games: List[Dict], context_desc: str, guild: discord.Guild):
        super().__init__(timeout=300)
        self.games = games
        self.context_desc = context_desc
        self.guild = guild
        self.current_page = 0
        self.games_per_page = 5
        self.total_pages = (len(games) + self.games_per_page - 1) // self.games_per_page
        self._update_buttons()
    
    def _update_buttons(self):
        """Enable/disable navigation buttons based on current page."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def create_embed(self) -> discord.Embed:
        """Create embed for current page."""
        start_idx = self.current_page * self.games_per_page
        end_idx = min(start_idx + self.games_per_page, len(self.games))
        page_games = self.games[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"{EMOJI_SCRIPT} Game History",
            description=f"{self.context_desc} • {len(self.games)} game(s) total",
            color=discord.Color.blue()
        )
        
        for game in page_games:
            game_id = game.get("game_id", "?")
            script = game.get("script", "Unknown")
            custom_name = game.get("custom_name", "")
            winner = game.get("winner", "Unknown")
            storyteller_id = game.get("storyteller_id")
            
            # Format the script name with custom name if present
            if custom_name and script == "Custom Script":
                script_display = f"{script} ({custom_name})"
            else:
                script_display = script
            
            # Format timestamps - stored as Unix timestamps (floats)
            start_time = game.get("start_time", 0)
            end_time = game.get("end_time", 0)
            
            # Calculate duration in seconds
            if end_time and start_time:
                duration = int(end_time - start_time)
            else:
                duration = 0
            
            # Calculate duration in hours and minutes
            hours, remainder = divmod(duration, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if hours > 0:
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = f"{minutes}m"
            
            # Winner emoji
            winner_emoji = {
                "Good": EMOJI_GOOD_WIN,
                "Evil": EMOJI_EVIL_WIN,
                "Cancel": "❌"
            }.get(winner, EMOJI_QUESTION)
            
            # Storyteller display
            st_display = f"<@{storyteller_id}>" if storyteller_id else "Unknown"
            
            field_value = f"{winner_emoji} Winner: **{winner}**\n{EMOJI_PEN} Storyteller: {st_display}\n{EMOJI_CLOCK} Duration: {duration_str}\nGame ID: `{game_id}`"
            
            embed.add_field(
                name=script_display,
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} • v{VERSION}")
        
        return embed
    
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)


bot.stats_handler = stats_handler
bot.gamehistory_handler = gamehistory_handler


async def storytellerstats_handler(interaction: discord.Interaction, user: discord.User = None) -> None:
    """Display storyteller statistics for the guild or bot-wide for a specific user.
    
    Args:
        interaction: Discord interaction
        user: Optional user to show stats for (defaults to guild leaderboard)
    """
    if not check_rate_limit(interaction.user.id, "storytellerstats", COMMAND_COOLDOWN_LONG):
        await interaction.response.send_message("⏳ Please wait before using this command again.", ephemeral=True)
        return
    
    try:
        guild = interaction.guild
        guild_id = guild.id
        
        # If looking up a specific user, get bot-wide stats and profile
        # Otherwise get guild-specific leaderboard
        if user:
            stats = await db.get_storyteller_stats(None)  # Bot-wide
        else:
            stats = await db.get_storyteller_stats(guild_id)  # Guild-specific
        
        if not stats:
            if user:
                await interaction.response.send_message("No storyteller statistics recorded yet.", ephemeral=True)
            else:
                await interaction.response.send_message("No storyteller statistics recorded for this server yet.", ephemeral=True)
            return
        
        # Update storyteller names if they've changed (only for guild-specific queries)
        if not user:
            for stat in stats:
                st_id = stat['storyteller_id']
                member = guild.get_member(st_id)
                if member and stat['storyteller_name'] != member.display_name:
                    await db.update_storyteller_name(guild_id, st_id, member.display_name)
                    stat['storyteller_name'] = member.display_name
        
        # Filter for specific user if requested
        if user:
            stats = [s for s in stats if s['storyteller_id'] == user.id]
            if not stats:
                await interaction.response.send_message(f"{user.display_name} has no storytelling history.", ephemeral=True)
                return
            # Defer early since card generation takes time
            await interaction.response.defer()
        
        # If showing individual stats, make it more detailed
        if user and len(stats) == 1:
            stat = stats[0]
            total = stat['total_games']
            good = stat['good_wins']
            evil = stat['evil_wins']
            
            if total == 0:
                await interaction.response.send_message(f"{user.display_name} has no completed games yet.", ephemeral=True)
                return
            
            good_rate = (good / total * 100) if total > 0 else 0
            evil_rate = (evil / total * 100) if total > 0 else 0
            
            embed = discord.Embed(
                title=f"{EMOJI_PEN} Storyteller Stats",
                description=f"Bot-wide statistics for **{user.display_name}**",
                color=discord.Color.purple()
            )
            
            # Set user's profile picture as thumbnail
            embed.set_thumbnail(url=user.display_avatar.url)
            
            # Set author with name and avatar
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            
            # Get profile data and add to description if available
            profile = await db.get_storyteller_profile(user.id)
            if profile:
                profile_text = []
                if profile.get('pronouns'):
                    profile_text.append(f"*({profile['pronouns']})*")
                if profile.get('custom_title'):
                    profile_text.append(f"🎭 The {profile['custom_title']}")
                if profile_text:
                    embed.description += "\n" + " • ".join(profile_text)
            
            embed.add_field(
                name=f"{EMOJI_STAR} Overall Performance",
                value=(
                    f"**Total Games:** {total}\n"
                    f"**{EMOJI_GOOD} Good Wins:** {good} ({good_rate:.1f}%)\n"
                    f"**{EMOJI_EVIL} Evil Wins:** {evil} ({evil_rate:.1f}%)\n"
                    f"**Balance:** {'Good-favored' if good_rate > 55 else 'Evil-favored' if evil_rate > 55 else 'Balanced'}"
                ),
                inline=False
            )
            
            total_duration = stat.get('total_game_duration', 0) or 0
            total_players = stat.get('total_player_count', 0) or 0
            
            if total > 0 and total_duration > 0:
                avg_duration_minutes = (total_duration / total) // 60
                avg_duration_hours = avg_duration_minutes // 60
                avg_duration_mins = avg_duration_minutes % 60
                
                avg_player_count = total_players / total
                
                duration_str = f"{int(avg_duration_hours)}h {int(avg_duration_mins)}m" if avg_duration_hours > 0 else f"{int(avg_duration_minutes)}m"
                
                embed.add_field(
                    name=f"{EMOJI_CLOCK} Game Metrics",
                    value=(
                        f"**Avg Game Length:** {duration_str}\n"
                        f"**{EMOJI_PLAYERS} Avg Player Count:** {avg_player_count:.1f}"
                    ),
                    inline=False
                )
            
            script_stats = []
            if stat['tb_games'] > 0:
                tb_good_rate = (stat['tb_good_wins'] / stat['tb_games'] * 100)
                tb_evil_rate = (stat['tb_evil_wins'] / stat['tb_games'] * 100)
                script_stats.append(
                    f"**{EMOJI_TROUBLE_BREWING} Trouble Brewing**\n"
                    f"Games: {stat['tb_games']} | {EMOJI_GOOD} {stat['tb_good_wins']} ({tb_good_rate:.0f}%) | {EMOJI_EVIL} {stat['tb_evil_wins']} ({tb_evil_rate:.0f}%)"
                )
            
            if stat['snv_games'] > 0:
                snv_good_rate = (stat['snv_good_wins'] / stat['snv_games'] * 100)
                snv_evil_rate = (stat['snv_evil_wins'] / stat['snv_games'] * 100)
                script_stats.append(
                    f"**{EMOJI_SECTS_AND_VIOLETS} Sects & Violets**\n"
                    f"Games: {stat['snv_games']} | {EMOJI_GOOD} {stat['snv_good_wins']} ({snv_good_rate:.0f}%) | {EMOJI_EVIL} {stat['snv_evil_wins']} ({snv_evil_rate:.0f}%)"
                )
            
            if stat['bmr_games'] > 0:
                bmr_good_rate = (stat['bmr_good_wins'] / stat['bmr_games'] * 100)
                bmr_evil_rate = (stat['bmr_evil_wins'] / stat['bmr_games'] * 100)
                script_stats.append(
                    f"**{EMOJI_BAD_MOON_RISING} Bad Moon Rising**\n"
                    f"Games: {stat['bmr_games']} | {EMOJI_GOOD} {stat['bmr_good_wins']} ({bmr_good_rate:.0f}%) | {EMOJI_EVIL} {stat['bmr_evil_wins']} ({bmr_evil_rate:.0f}%)"
                )
            
            if script_stats:
                embed.add_field(
                    name=f"{EMOJI_SCRIPT} Script Performance",
                    value="\n\n".join(script_stats),
                    inline=False
                )
            
            script_counts = [
                ("Trouble Brewing", stat['tb_games']),
                ("Sects & Violets", stat['snv_games']),
                ("Bad Moon Rising", stat['bmr_games'])
            ]
            most_played = max(script_counts, key=lambda x: x[1])
            if most_played[1] > 0:
                embed.add_field(
                    name=f"{EMOJI_SWORD} Favorite Script",
                    value=f"{add_script_emoji(most_played[0])} ({most_played[1]} games)",
                    inline=True
                )
            
            if stat.get('last_game_at'):
                from datetime import datetime
                last_game = stat['last_game_at']
                embed.add_field(
                    name=f"{EMOJI_CANDLE} Last Game",
                    value=f"<t:{int(last_game.timestamp())}:R>",
                    inline=True
                )
            
            try:
                from botc.card_generator import generate_stats_card
                
                avg_duration_minutes = None
                avg_players = None
                if total > 0:
                    if stat.get('total_game_duration', 0):
                        avg_duration_minutes = (stat['total_game_duration'] / total) / 60
                    if stat.get('total_player_count', 0):
                        avg_players = stat['total_player_count'] / total
                
                card_buffer = await generate_stats_card(
                    username=user.display_name,
                    avatar_url=str(user.display_avatar.url),
                    total_games=total,
                    good_wins=good,
                    evil_wins=evil,
                    pronouns=profile.get('pronouns') if profile else None,
                    version=VERSION,
                    tb_games=stat.get('tb_games', 0) or 0,
                    snv_games=stat.get('snv_games', 0) or 0,
                    bmr_games=stat.get('bmr_games', 0) or 0,
                    avg_duration_minutes=avg_duration_minutes,
                    avg_players=avg_players,
                    custom_title=profile.get('custom_title') if profile else None,
                    color_theme=profile.get('color_theme') if profile else None
                )
                
                if card_buffer:
                    card_file = discord.File(fp=card_buffer, filename=f"stats_{user.id}.png")
                    await interaction.followup.send(file=card_file)
                else:
                    await interaction.followup.send(embed=embed)
                    
            except Exception as e:
                logger.warning(f"Failed to generate stats card: {e}")
                await interaction.followup.send(embed=embed)
        
        else:
            embed = discord.Embed(
                title=f"{EMOJI_PEN} Storyteller Leaderboard",
                description=f"Stats for all storytellers in **{guild.name}**",
                color=discord.Color.purple()
            )
            
            for idx, stat in enumerate(stats[:10], 1):  # Show top 10
                st_name = stat['storyteller_name'] or f"<@{stat['storyteller_id']}>"
                total = stat['total_games']
                good = stat['good_wins']
                evil = stat['evil_wins']
                
                if total > 0:
                    good_rate = (good / total * 100) if total > 0 else 0
                    evil_rate = (evil / total * 100) if total > 0 else 0
                    
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"**{idx}.**")
                    
                    stats_text = f"**{total} games** • {EMOJI_GOOD} {good} ({good_rate:.0f}%) | {EMOJI_EVIL} {evil} ({evil_rate:.0f}%)\n"
                    
                    scripts = [("TB", stat['tb_games']), ("S&V", stat['snv_games']), ("BMR", stat['bmr_games'])]
                    top_script = max(scripts, key=lambda x: x[1])
                    if top_script[1] > 0:
                        stats_text += f"Favorite: {top_script[0]} ({top_script[1]} games)"
                    
                    embed.add_field(
                        name=f"{medal} {st_name}",
                        value=stats_text,
                        inline=False
                    )
            
            if len(stats) > 10:
                embed.set_footer(text=f"Showing top 10 of {len(stats)} storytellers • v{VERSION}")
            else:
                embed.set_footer(text=f"Use /ststats @user for detailed stats • v{VERSION}")
            
            await interaction.response.send_message(embed=embed)
        
    except DatabaseError as e:
        logger.error(f"Database error in storytellerstats_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to load storyteller stats. Database error.", ephemeral=True)
    except Exception as e:
        logger.exception(f"Unexpected error in storytellerstats_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to load storyteller stats. See logs.", ephemeral=True)


bot.storytellerstats_handler = storytellerstats_handler


async def deletegame_handler(interaction: discord.Interaction, game_id: int) -> None:
    """Delete a specific game from history by game_id (Admin only).

    Args:
        interaction: Discord interaction
        game_id: The game_id to delete (shown in /gamehistory)
    """
    try:
        guild = interaction.guild
        member = guild.get_member(interaction.user.id) if guild else None
        if not is_admin(member):
            try:
                await interaction.response.send_message("Only administrators can delete game history.", ephemeral=True)
            except discord.HTTPException:
                try:
                    await interaction.followup.send("Only administrators can delete game history.", ephemeral=True)
                except discord.HTTPException:
                    logger.debug("Could not send permission denied message")
            return

        # Delete game by ID directly (with guild check for security)
        deleted = await db.delete_game_by_id(game_id, guild.id)
        
        if not deleted:
            try:
                await interaction.response.send_message(f"❌ Game ID `{game_id}` not found. Use `/gamehistory` to see valid game IDs.", ephemeral=True)
            except discord.HTTPException:
                try:
                    await interaction.followup.send(f"❌ Game ID `{game_id}` not found. Use `/gamehistory` to see valid game IDs.", ephemeral=True)
                except discord.HTTPException:
                    logger.debug("Could not send game not found message")
            return

        try:
            await interaction.response.send_message(f"✅ Deleted game ID `{game_id}`", ephemeral=True)
        except discord.HTTPException:
            try:
                await interaction.followup.send(f"✅ Deleted game ID `{game_id}`", ephemeral=True)
            except discord.HTTPException:
                logger.debug("Could not send delete confirmation")
    except DatabaseError as e:
        logger.error(f"Database error in deletegame_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to delete game. Database error.", ephemeral=True)
    except Exception as e:
        logger.exception(f"Unexpected error in deletegame_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to delete game. See logs.", ephemeral=True)


async def clearhistory_handler(interaction: discord.Interaction) -> None:
    """Clear all game history for the guild (Admin only).

    This operation is irreversible; the slash command is restricted to
    administrators. It clears the stored `game_history` entry for the
    guild and persists the change.
    """
    try:
        guild = interaction.guild
        member = guild.get_member(interaction.user.id) if guild else None
        if not is_admin(member):
            await safe_send_interaction(interaction, "Only administrators can clear game history.", ephemeral=True)
            return

        guild_id = guild.id
        history = await db.get_game_history(guild_id, limit=None)
        
        if not history:
            await safe_send_interaction(interaction, "No game history to clear.", ephemeral=True)
            return

        try:
            await db.clear_game_history(guild_id)
        except DatabaseError as e:
            logger.error(f"Failed to clear game history from database: {e}")
            await safe_send_interaction(interaction, "❌ Failed to clear history. Database error.", ephemeral=True)
            return

        await safe_send_interaction(interaction, "✅ Cleared game history for this server.", ephemeral=True)
    except Exception as e:
        logger.exception(f"Unexpected error in clearhistory_handler: {e}")
        await safe_send_interaction(interaction, "❌ Failed to clear history. See logs.", ephemeral=True)


bot.deletegame_handler = deletegame_handler
bot.clearhistory_handler = clearhistory_handler


async def autosetup_handler(interaction: discord.Interaction) -> None:
    """Handle /autosetup command - automatically create gothic-themed BOTC server structure."""
    try:
        guild = interaction.guild
        member = guild.get_member(interaction.user.id) if guild else None
        
        # Check admin permissions
        if not is_admin(member):
            await interaction.response.send_message("❌ Only administrators can use /autosetup.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        # Check bot permissions
        bot_member = guild.get_member(bot.user.id)
        if not bot_member or not bot_member.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Bot needs 'Manage Channels' permission to run autosetup.", ephemeral=True)
            return
        
        status_msg = await interaction.followup.send("🕯️ Setting up your Blood on the Clocktower server...")
        
        gothic_red = discord.Color.from_rgb(139, 0, 0)
        
        # Check for existing BOTC categories to determine session number
        existing_botc_categories = [
            cat for cat in guild.categories 
            if cat.name.lower().startswith("🩸• blood on the clocktower") or 
               cat.name.lower() in ["botc", "bot c", "blood on the clocktower"]
        ]
        
        if len(existing_botc_categories) == 0:
            category_name = "🩸• Blood on the Clocktower"
        else:
            category_name = f"🩸• Blood on the Clocktower - Session {len(existing_botc_categories) + 1}"
        
        botc_category = await guild.create_category(
            category_name,
            position=0
        )
        
        announce_channel = await guild.create_text_channel(
            "📜┃announcements",
            category=botc_category,
            topic="Game updates, timer notifications, and bot announcements"
        )
        
        consultation = await guild.create_voice_channel(
            "🕯️┃Consultation",
            category=botc_category,
            user_limit=0
        )
        
        town_square = await guild.create_voice_channel(
            "🏛️┃Town Square",
            category=botc_category,
            user_limit=0
        )
        
        private_2 = await guild.create_voice_channel(
            "🌙┃Private Chamber (2)",
            category=botc_category,
            user_limit=2
        )
        
        private_3 = await guild.create_voice_channel(
            "⚰️┃Private Chamber (3)",
            category=botc_category,
            user_limit=3
        )
        
        commons = await guild.create_voice_channel(
            "🗡️┃Commons",
            category=botc_category,
            user_limit=0
        )
        
        guild_id = guild.id
        
        # Create session for this category (don't update guild-wide botc_category_id if sessions already exist)
        if len(existing_botc_categories) == 0:
            # First session - set as guild default
            await db.upsert_guild(
                guild_id,
                botc_category_id=botc_category.id
            )
        
        if session_manager:
            try:
                await session_manager.create_session(
                    guild_id=guild_id,
                    category_id=botc_category.id,
                    destination_channel_id=town_square.id,
                    grimoire_link=None,
                    exception_channel_id=consultation.id,
                    announce_channel_id=announce_channel.id,
                    active_game_id=None
                )
                logger.info(f"Autosetup: Created session for guild {guild_id}, category {botc_category.id}")
            except Exception as e:
                logger.error(f"Autosetup: Failed to create session: {e}")
        
        # Send success message to announcements channel
        session_number = len(existing_botc_categories) + 1
        if session_number == 1:
            title = "🩸 Grimkeeper Setup Complete"
            description = "Your Blood on the Clocktower server is ready!"
        else:
            title = f"🩸 Session {session_number} Created"
            description = f"Your Blood on the Clocktower session is ready in **{category_name}**!"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=gothic_red
        )
        
        embed.add_field(
            name="🏛️ Town Square",
            value=f"{town_square.mention} - Main gathering point for all players",
            inline=False
        )
        
        embed.add_field(
            name="🕯️ Consultation",
            value=f"{consultation.mention} - Private channel for storytellers (excluded from `*call`)",
            inline=False
        )
        
        embed.add_field(
            name="🌙 Private Chambers",
            value=f"{private_2.mention} (2 players)\n{private_3.mention} (3 players)\nUse these for private conversations!",
            inline=False
        )
        
        embed.add_field(
            name="📜 Next Steps",
            value=(
                "• Use `*st` to claim Storyteller role\n"
                "• Use `*g <link>` to set your grimoire link (session-scoped)\n"
                "• Use `*call` to summon players to Town Square\n"
                "• Use `/startgame` to begin tracking a game\n"
                "• Type `*help` for all commands"
            ),
            inline=False
        )
        
        if session_number > 1:
            embed.add_field(
                name="🎭 Multi-Session Server",
                value=(
                    f"You now have **{session_number} active sessions**!\n\n"
                    f"**Session-Scoped Config:**\n"
                    f"• Each category has its own grimoire link, town square, exception channel\n"
                    f"• Commands like `*g` and `/settown` affect only the category you run them in\n"
                    f"• Game history and timers are tracked separately per session\n\n"
                    f"**Running Multiple Games:**\n"
                    f"• Run `/autosetup` again to create more game categories\n"
                    f"• Each session operates completely independently\n"
                    f"• Use `*sessions` to view all active sessions"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="🎭 Multi-Session Support",
                value=(
                    "**Want to run multiple simultaneous games?**\n\n"
                    f"**Option 1: Use /autosetup again**\n"
                    f"Run `/autosetup` to create another gothic-themed category\n\n"
                    f"**Option 2: Manual setup**\n"
                    f"1. Create a new Discord category (any name)\n"
                    f"2. Add text/voice channels inside it\n"
                    f"3. Run config commands from within that category:\n"
                    f"   - `/setbotc <category>` to create the session\n"
                    f"   - `/settown #channel` to set town square\n"
                    f"   - `/setexception #channel` (optional)\n\n"
                    f"Each category operates independently with its own grimoire, game history, and timers!"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"Grimkeeper v{VERSION} | Your story begins...")
        
        await announce_channel.send(embed=embed)
        await status_msg.edit(content=f"✅ Setup complete! Check {announce_channel.mention} for details.")
        
        logger.info(f"Autosetup completed for guild: {guild.name} (ID: {guild.id})")
        
    except discord.Forbidden as e:
        logger.error(f"Permission denied during autosetup for {guild.name}: {e}")
        try:
            await interaction.followup.send(
                "❌ Bot lacks permissions to create channels. Please ensure the bot has 'Manage Channels' permission.",
                ephemeral=True
            )
        except discord.HTTPException:
            logger.debug("Could not send permission error message")
    except DatabaseError as e:
        logger.error(f"Database error during autosetup for {guild.name}: {e}")
        try:
            await interaction.followup.send("❌ Setup failed due to database error. Please try again.", ephemeral=True)
        except discord.HTTPException:
            logger.debug("Could not send database error message")
    except Exception as e:
        logger.exception(f"Unexpected error in autosetup_handler: {e}")
        try:
            await interaction.followup.send("❌ Setup failed. Check bot permissions and try again.", ephemeral=True)
        except discord.HTTPException:
            logger.debug("Could not send error message")


bot.autosetup_handler = autosetup_handler




def load_changelog():
    """Load changelog from changelog.json file"""
    try:
        changelog_path = BASE_DIR / "changelog.json"
        with open(changelog_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load changelog.json: {e}")
        return []

changelog_data = load_changelog()



async def load_cogs():
    """Load all bot cogs."""
    try:
        await bot.load_extension('botc.cogs.events')
        await bot.load_extension('botc.cogs.slash')
        await bot.load_extension('botc.cogs.polls')
        await bot.load_extension('botc.cogs.timers')
        await bot.load_extension('botc.cogs.voice_commands')
        await bot.load_extension('botc.cogs.commands')
        logger.info("Loaded all cogs: events, slash, polls, timers, voice_commands, commands")
    except Exception as e:
        logger.error(f"Failed to load cogs: {e}")
        raise

session_manager: Optional[SessionManager] = None
announcement_processor: Optional[AnnouncementProcessor] = None
cleanup_task: Optional[CleanupTask] = None

@bot.event
async def setup_hook():
    """Setup hook called before bot connects to Discord.
    
    This runs before on_ready and is the proper place to load cogs.
    """
    global session_manager, announcement_processor, cleanup_task
    
    session_manager = SessionManager(db)
    bot.session_manager = session_manager
    logger.info("Session manager initialized")
    
    # Initialize announcement processor for website events
    announcement_processor = AnnouncementProcessor(bot, db, session_manager)
    bot.announcement_processor = announcement_processor
    logger.info("Announcement processor initialized")
    
    # Initialize cleanup task
    cleanup_task = CleanupTask(db)
    bot.cleanup_task = cleanup_task
    logger.info("Cleanup task initialized")
    
    await load_cogs()




@bot.event
async def on_command_error(ctx, error):
    """Handle command errors - suppress CommandNotFound for on_message handled commands."""
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

@bot.event
async def on_message(message):
    """Minimal on_message handler - rate limiting, command deletion, and cog delegation."""
    if message.author.bot:
        return

    content = message.content.strip()
    content_lower = content.lower()

    if not content:
        return
    
    content_words = content_lower.split()
    first_word = content_words[0] if content_words else ""
    
    if content_lower.startswith("*"):
        if not check_rate_limit(message.author.id, first_word or "*"):
            return

    if first_word in DELETABLE_COMMANDS:
        try:
            await message.delete(delay=DELETE_DELAY_QUICK)
        except discord.errors.Forbidden:
            pass
        except Exception as e:
            logger.warning(f"Could not delete command message: {e}")

    await bot.process_commands(message)


if __name__ == "__main__":
    bot.run(token)
