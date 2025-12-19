"""Commands cog - handles all message-based bot commands.

This cog handles:
- User commands: *!, *st, *cost, *brb, *g
- Info commands: *help, *credits, *changelog, *players, *sessions
- Game commands: *spec, *unspec, *shadows, *dnd, *night, *day
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from botc.constants import (
    VERSION,
    PREFIX_ST,
    PREFIX_COST,
    PREFIX_SPEC,
    DELETE_DELAY_QUICK,
    DELETE_DELAY_NORMAL,
    DELETE_DELAY_MEDIUM,
    DELETE_DELAY_ERROR,
    DELETE_DELAY_LONG,
    COMMAND_COOLDOWN_LONG,
    EMOJI_TOWN_SQUARE,
    EMOJI_SCRIPT,
    EMOJI_PLAYERS,
    EMOJI_CLOCK,
    EMOJI_GEAR,
    EMOJI_SCROLL,
    EMOJI_HEART,
    EMOJI_QUESTION,
    EMOJI_BALANCE,
    EMOJI_PEN,
    EMOJI_STAR,
)

if TYPE_CHECKING:
    from botc.database import Database

logger = logging.getLogger('botc_bot')

# Load changelog data from external file
def load_changelog():
    """Load changelog from changelog.json file"""
    changelog_path = Path(__file__).resolve().parent.parent.parent / "changelog.json"
    try:
        with open(changelog_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load changelog.json: {e}")
        return []

changelog_data = load_changelog()


class Commands(commands.Cog):
    """Cog that handles all message-based bot commands.

    Expects main `bot` to expose:
      - bot.is_storyteller(member)
      - bot.get_active_players(guild)
      - bot.db (Database instance)
      - bot.check_rate_limit(user_id, command, cooldown)
      - bot.is_admin(member)
      - bot.send_temporary(channel, content, embed, delay)
      - bot.toggle_prefix(member, channel, prefix_key, announce_channel)
      - bot.get_botc_category(guild)
      - bot.get_member_name(member)
      - bot.get_player_role(member)
      - bot.strip_brb_prefix(name)
      - bot.check_bot_permissions(guild)
      - bot.last_player_snapshots (dict)
      - bot.follower_targets (dict)
      - bot.clean_followers(guild)
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("Commands cog initialized")

    async def _require_active_game(self, message: discord.Message, session=None) -> bool:
        """Check if there's an active game for the current context.
        
        Args:
            message: Discord message for context
            session: Optional session object (will try to get from channel if None)
            
        Returns:
            True if active game exists, False otherwise (and sends error message)
        """
        db: Database = self.bot.db
        guild_id = message.guild.id
        
        # Get session if not provided
        if session is None:
            get_session_func = getattr(self.bot, "get_session_from_channel", None)
            if get_session_func:
                session = await get_session_func(message.channel, self.bot.session_manager)
        
        # Determine category_id for active game check
        category_id = session.category_id if session else None
        
        # Check for active game
        active_game = await db.get_active_game(guild_id, category_id)
        if not active_game:
            msg = await message.channel.send("❌ No active game found. Use `/startgame` first!")
            await msg.delete(delay=DELETE_DELAY_ERROR)
            return False
        
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle all message-based commands."""
        if message.author.bot:
            return

        content = (message.content or "").strip()
        content_lower = content.lower()
        target = message.author

        if not content:
            return

        # Cache split result
        content_words = content_lower.split()
        first_word = content_words[0] if content_words else ""

        # Get database reference
        db: Database = self.bot.db

        # --- Credits ---
        if first_word == "*credits":
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete messages
            embed = discord.Embed(
                title=f"{EMOJI_HEART} Grimkeeper Credits",
                description="Special thanks to everyone who made this bot possible",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="💡 Original Concept",
                value="**lieutenantdv20** - For the brilliant idea that started it all",
                inline=False
            )
            
            embed.add_field(
                name="✨ Creative Writing",
                value="**pinlessthan3** - For crafting the atmospheric Good/Evil win messages",
                inline=False
            )
            
            embed.add_field(
                name="🐛 Quality Assurance",
                value="**threads** - For helping me bugtest and awesome feedback",
                inline=False
            )
            
            embed.set_footer(text=f"Grimkeeper v{VERSION} | Made with 🩸 for the BOTC community")
            await message.channel.send(embed=embed)
            return

        # --- Storyteller Help ---
        if content_lower == "*help st" or content_lower == "*help storyteller":
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete messages
            embed = discord.Embed(
                title=f"{EMOJI_PEN} Storyteller Commands",
                description="Commands for running games",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="🎭 Role & Setup",
                value=(
                    "`*st` - claim/unclaim Storyteller role\n"
                    "`*cost` - toggle Co-Storyteller role\n"
                    "`*g <link>` - set grimoire link"
                ),
                inline=False,
            )
            
            embed.add_field(
                name=f"{EMOJI_STAR} Game Management",
                value=(
                    "`/startgame <script>` - start game tracking\n"
                    "`/endgame <winner>` - record game result\n"
                    "`*call` - call all townspeople to Town Square\n"
                    "`*mute` - server mute all players (excludes STs)\n"
                    "`*unmute` - unmute all players\n"
                    "`*timer <duration>` - schedule a delayed call (e.g., `5m`, `1h30m`)\n"
                    "`*timer cancel` - cancel active timer"
                ),
                inline=False,
            )
            
            embed.add_field(
                name="📢 Announcements",
                value=(
                    "`*night` - announce nighttime\n"
                    "`*day` - announce morning\n"
                    "`*poll [123ch] <time>` - create script poll\n"
                    "*Example:* `*poll 123 10m` - poll for TB/S&V/BMR, 10 minutes"
                ),
                inline=False,
            )
            
            embed.set_footer(text=f"v{VERSION} • *help for main commands • *help admin for setup")
            await message.channel.send(embed=embed)
            return
        
        # --- Admin Help ---
        if content_lower == "*help admin" or content_lower == "*help setup":
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete messages
            embed = discord.Embed(
                title=f"{EMOJI_GEAR} Admin Commands",
                description="Server setup and configuration (Administrators only)",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🏗️ Initial Setup",
                value=(
                    "`/setbotc <category>` - create/link a session to a category\n"
                    "`/settown #channel` - set Town Square voice channel (for current session)\n"
                    "`/setexception #channel` - set consultation channel (for current session)\n"
                    "`/autosetup` - auto-create botc sessions\n\n"
                    "**Note:** Session commands must be run from within the session's category. Each category = one session."
                ),
                inline=False,
            )
            
            embed.add_field(
                name="🗑️ Session Management",
                value=(
                    "`/sessions` - list all sessions\n"
                    "`/deletesession <id>` - remove a session"
                ),
                inline=False,
            )
            
            embed.add_field(
                name="📊 Management",
                value=(
                    "`/sessions` - view server settings and active sessions\n"
                    "`/sessions view <id>` - detailed session info\n"
                    "`/sessions cleanup` - remove inactive sessions\n"
                    "`*changelog` - view version history\n"
                    "`/deletegame <number>` - delete specific game from history\n"
                    "`/clearhistory` - delete all game history"
                ),
                inline=False,
            )
            
            embed.add_field(
                name="💡 Multi-Session Support",
                value=(
                    "Run multiple concurrent games by creating multiple BOTC categories!\n"
                    "Each category becomes an independent session with its own:\n"
                    "• Game tracking • Timers • Grimoire • Player lists • History\n"
                    "Commands automatically scope to the category you're in."
                ),
                inline=False,
            )
            
            embed.set_footer(text=f"v{VERSION} • *help for main commands • *help st for storyteller")
            await message.channel.send(embed=embed)
            return

        # --- Help (General) ---
        if first_word == "*help":
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete messages
            embed = discord.Embed(
                title="🩸 Grimkeeper",
                description="Essential commands\n Use `*help st` for Storyteller commands • `*help admin` for setup commands",
                color=discord.Color.dark_red()
            )
            
            embed.add_field(
                name="👥 Players",
                value=(
                    "`*!` - toggle spectator mode\n"
                    "`*brb` - toggle away status\n"
                    "`*g` - view grimoire link\n"
                    "`*players` - list active players\n"
                    "`*timer` - check active timer\n"
                    "`*consult` - request ST consultation (active game only)"
                ),
                inline=True,
            )
            
            embed.add_field(
                name="🌘 Spectators",
                value=(
                    "`*spec @user` - shadow follow a player\n"
                    "`*unspec` - stop following\n"
                    "`*dnd` - toggle do-not-disturb\n"
                    "`*shadows` - view all followers\n"
                    "`*join @user` - join someone's voice channel"
                ),
                inline=True,
            )
            
            embed.add_field(
                name="📊 Game Info",
                value=(
                    "`/stats` - server statistics\n"
                    "`/gamehistory` - recent games\n"
                    "`*stguide` - storyteller guide\n"
                    "`*credits` - contributors"
                ),
                inline=True,
            )
            
            embed.set_footer(text=f"v{VERSION} • *help st • *help admin • Bug reports → hystericca")
            await message.channel.send(embed=embed)
            return

        # --- Storyteller Guide ---
        if first_word == "*stguide":
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass
            
            embed = discord.Embed(
                title=f"{EMOJI_SCROLL} Storyteller's Guide to Grimkeeper",
                description="A quick reference for running smooth BOTC games with this bot",
                color=discord.Color.dark_red()
            )
            
            embed.add_field(
                name="🎬 Starting a Game",
                value=(
                    "**Before:**\n"
                    "• Use `*poll` to let players vote on the script\n"
                    "• Make sure players are in BOTC voice channels\n\n"
                    "**Setup:**\n"
                    "**1.** Claim Storyteller: `*st`\n"
                    "**2.** Set your grimoire: `*g <link>`\n"
                    "**3.** Start tracking: `/startgame <script>`\n"
                    "**4.** **Confirm the player roster**\n"
                    "   • Bot shows who will be tracked\n"
                    "   • Use 🔄 Refresh if players need to toggle `*!`\n"
                    "   • Click ✅ Confirm when ready\n\n"
                    "Without `/startgame`, commands like `*timer`, `*call`, `*night`, `*day`, and `*consult` won't work."
                ),
                inline=False
            )
            
            embed.add_field(
                name="⏰ Managing Players",
                value=(
                    "`*call` - Move everyone to Town Square\n"
                    "`*mute` - Server mute all players (excludes STs)\n"
                    "`*unmute` - Unmute all players\n"
                    "`*timer 5m` or `*5m` - Schedule a delayed call\n"
                    "`*night` / `*day` - Post phase announcements\n"
                    "`*players` - See who's in the game"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎭 During the Game",
                value=(
                    "• Players can use `*consult` to request private ST chat\n"
                    "• Grimoire link is accessible via `*g` (no args)\n"
                    "• Timers persist through bot restarts!\n"
                    "• Use `/addplayer` or `/removeplayer` if roster changes"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🏁 Ending a Game",
                value=(
                    "**1.** Record the result: `/endgame <Good/Evil>`\n"
                    "**2.** Stats are automatically tracked!\n"
                    "**3.** Check your stats: `/storytellerstats`\n\n"
                    "*Tip: Use `/addplayer @user` or `/removeplayer @user` during the game if someone joins late or leaves.*"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💡 Notes",
                value=(
                    "• **Co-Storytelling:** Use `*cost` to share ST duties\n"
                    "• **Private Channel:** ST can use exception channel (excluded from `*call`)\n"
                    "• **Quick Timers:** `*3m` is faster than `*timer 3m`\n"
                    "• **Player Tracking:** Uses user IDs, immune to nickname changes\n"
                    "• **Your Stats:** Individual achievements tracked across ALL servers!"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"v{VERSION} • *help for all commands • Report issues → hystericca")
            await message.channel.send(embed=embed)
            return

        # --- Prefix toggle commands ---
        if first_word == "*!":
            await self.bot.toggle_prefix(target, message.channel, "spe")
            return
        if first_word == "*st":
            await self.bot.toggle_prefix(target, message.channel, "st")
            return
        if first_word == "*cost":
            await self.bot.toggle_prefix(target, message.channel, "cost")
            return
        if first_word == "*brb":
            await self.bot.toggle_prefix(target, message.channel, "brb")
            return

        # --- Game info ---
        if first_word == "*game":
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass
            await self._handle_game_command(message)
            return

        # --- Grimoire (session-scoped) ---
        # Check for *g or *grim specifically, not *game or other *g* commands
        if first_word == "*g" or content_lower.startswith("*g ") or first_word == "*grim" or content_lower.startswith("*grim "):
            args = content.split(maxsplit=1)
            
            # Get existing session from channel context - do not auto-create
            session_manager = getattr(self.bot, "session_manager", None)
            if not session_manager:
                msg = await message.channel.send("Session manager not available.")
                await msg.delete(delay=DELETE_DELAY_QUICK)
                return
            
            session = await session_manager.get_session_from_channel(message.channel, message.guild)
            if not session:
                msg = await message.channel.send(
                    "⚠️ No session found in this category. Run `/setbotc` first to create a session."
                )
                await msg.delete(delay=DELETE_DELAY_MEDIUM)
                return
            
            if len(args) > 1:
                if self.bot.is_storyteller(target):
                    grimoire_link = args[1].strip()
                    
                    # Update session-specific grimoire
                    session.grimoire_link = grimoire_link
                    await session_manager.update_session(session)
                    
                    # Send embed with grimoire link
                    embed = discord.Embed(
                        title=f"{EMOJI_SCROLL} Grimoire Link Set",
                        description=grimoire_link,
                        color=discord.Color.purple()
                    )
                    await message.channel.send(embed=embed)
                else:
                    msg = await message.channel.send("Only storytellers can set the grimoire link.")
                    await msg.delete(delay=DELETE_DELAY_QUICK)
            else:
                # Get grimoire link from session
                if session.grimoire_link:
                    await message.channel.send(f"{EMOJI_SCROLL} Current grimoire link: {session.grimoire_link}")
                else:
                    await message.channel.send("No grimoire link has been set for this session yet.")
            return

        # --- Night/Day Announcements ---
        if first_word == "*night":
            if not self.bot.is_storyteller(target):
                msg = await message.channel.send("Only storytellers can announce nighttime.")
                await msg.delete(delay=DELETE_DELAY_QUICK)
                return
            
            # Validate channel is in a BOTC category with a session
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
            
            # Require active game
            if not await self._require_active_game(message):
                return
            
            # Delete command message and post announcement
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass
            
            await message.channel.send("# 🌙 NIGHTTIME")
            return

        if first_word == "*day":
            if not self.bot.is_storyteller(target):
                msg = await message.channel.send("Only storytellers can announce morning.")
                await msg.delete(delay=DELETE_DELAY_QUICK)
                return
            
            # Validate channel is in a BOTC category with a session
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
            
            # Require active game
            if not await self._require_active_game(message):
                return
            
            # Delete command message and post announcement
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass
            
            await message.channel.send("# ☀️ MORNING")
            return

        # --- Shadow follow ---
        if content_lower.startswith("*spec"):
            args = message.mentions
            if not args:
                msg = await message.channel.send("Please mention someone to follow.")
                await msg.delete(delay=DELETE_DELAY_QUICK)
                return
            follower = message.author
            # Allow spectators, storytellers, and co-storytellers to use *spec
            current_nick = self.bot.get_member_name(follower)
            is_allowed = (current_nick.startswith(PREFIX_SPEC) or 
                         current_nick.startswith(PREFIX_ST) or 
                         current_nick.startswith(PREFIX_COST))
            if not is_allowed:
                msg = await message.channel.send("Only spectators, storytellers, and co-storytellers may use `*spec`.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            target_user = args[0]
            if follower.id == target_user.id:
                msg = await message.channel.send("Drop the mirror, you can't follow yourself.")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                return
            if await db.is_dnd(target_user.id):
                msg = await message.channel.send(f"{target_user.display_name} has DND enabled.")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                return
            
            follower_targets = self.bot.follower_targets
            if follower.id in follower_targets:
                old_target_id = follower_targets[follower.id]
                if old_target_id == target_user.id:
                    msg = await message.channel.send(f"Already following {target_user.display_name}.")
                    await msg.delete(delay=DELETE_DELAY_NORMAL)
                    return
                # Remove old shadow follow relationship
                await db.remove_follower(follower.id, message.guild.id)
            
            # Add new shadow follow relationship
            follower_targets[follower.id] = target_user.id
            await db.add_follower(follower.id, target_user.id, message.guild.id)
            await self.bot.clean_followers(message.guild)
            
            # Immediately move follower to target's voice channel if both are in voice and different channels
            if (follower.voice and follower.voice.channel and 
                target_user.voice and target_user.voice.channel and
                follower.voice.channel.id != target_user.voice.channel.id):
                try:
                    await follower.move_to(target_user.voice.channel)
                except Exception as e:
                    logger.warning(f"Could not immediately move {follower.display_name} to follow {target_user.display_name}: {e}")
            
            msg = await message.channel.send(f"{follower.display_name} is now following {target_user.display_name}.")
            await msg.delete(delay=DELETE_DELAY_QUICK)
            return

        if content_lower.startswith("*unspec"):
            follower_id = message.author.id
            follower_targets = self.bot.follower_targets
            if follower_id in follower_targets:
                await db.remove_follower(follower_id, message.guild.id)
                follower_targets.pop(follower_id)
                await self.bot.clean_followers(message.guild)
            msg = await message.channel.send("Stopped following.")
            await msg.delete(delay=DELETE_DELAY_QUICK)
            return

        # --- Join user in their voice channel (one-time) ---
        if content_lower.startswith("*join"):
            args = message.mentions
            if not args:
                msg = await message.channel.send("Please mention someone to join: `*join @user`")
                await msg.delete(delay=DELETE_DELAY_QUICK)
                return
            
            joiner = message.author
            
            # Require spectator prefix for *join
            current_nick = self.bot.get_member_name(joiner)
            if not current_nick.startswith(PREFIX_SPEC):
                msg = await message.channel.send("Only spectators may use `*join`. Please run `*!` to toggle spectator mode and try again.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            target_user = args[0]
            
            if joiner.id == target_user.id:
                msg = await message.channel.send("You are already in your own voice channel.")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                return
            
            # Check if target is in a voice channel
            if not target_user.voice or not target_user.voice.channel:
                msg = await message.channel.send(f"{target_user.display_name} is not in a voice channel.")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                return
            
            # Check if joiner is in a voice channel
            if not joiner.voice or not joiner.voice.channel:
                msg = await message.channel.send("You must be in a voice channel to use this command.")
                await msg.delete(delay=DELETE_DELAY_NORMAL)
                return
            
            # Move joiner to target's channel
            try:
                await joiner.move_to(target_user.voice.channel)
                msg = await message.channel.send(f"Moved {joiner.display_name} to {target_user.voice.channel.name}.")
                await msg.delete(delay=DELETE_DELAY_QUICK)
            except discord.errors.Forbidden:
                msg = await message.channel.send("I don't have permission to move members.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
            except Exception as e:
                logger.error(f"Error moving {joiner.display_name} to {target_user.display_name}'s channel: {e}")
                msg = await message.channel.send("Failed to move you to that channel.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
            return

        # --- Consult with storyteller ---
        if content_lower.startswith("*consult"):
            requester = message.author
            
            # Validate channel is in a BOTC category with a session
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
            
            # Get session from channel context
            session = None
            get_session_func = getattr(self.bot, "get_session_from_channel", None)
            if get_session_func:
                session = await get_session_func(message.channel, self.bot.session_manager)
            
            if not session:
                msg = await message.channel.send("This command can only be used in a BOTC category with an active session.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            # Require active game
            if not await self._require_active_game(message, session):
                return
            
            # Get active game to find storyteller
            active_game = await db.get_active_game(message.guild.id, session.category_id)
            
            if not active_game or not active_game.get('storyteller_id'):
                msg = await message.channel.send("❌ No active game found. Ask your storyteller to use `/startgame` first!")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            storyteller = message.guild.get_member(active_game['storyteller_id'])
            if not storyteller:
                msg = await message.channel.send("Could not find the storyteller.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            if requester.id == storyteller.id:
                msg = await message.channel.send("You cannot consult with yourself.")
                await msg.delete(delay=DELETE_DELAY_QUICK)
                return
            
            # Get exception channel
            if not session.exception_channel_id:
                msg = await message.channel.send("No consultation channel configured. Use `*setexception #channel` first.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            exception_channel = message.guild.get_channel(session.exception_channel_id)
            if not exception_channel or not isinstance(exception_channel, discord.VoiceChannel):
                msg = await message.channel.send("Consultation channel not found or is not a voice channel.")
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return
            
            # Send consultation request
            request_msg = await message.channel.send(
                f"{storyteller.mention} **{requester.display_name}** is requesting a private consultation. React with ✅ to accept."
            )
            
            await request_msg.add_reaction("✅")
            await request_msg.add_reaction("❌")
            
            # Wait for storyteller's reaction
            def check(reaction, user):
                return (
                    user.id == storyteller.id and
                    reaction.message.id == request_msg.id and
                    str(reaction.emoji) in ["✅", "❌"]
                )
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                
                if str(reaction.emoji) == "✅":
                    # Move both to exception channel
                    moved_users = []
                    
                    if requester.voice and requester.voice.channel:
                        try:
                            await requester.move_to(exception_channel)
                            moved_users.append(requester.display_name)
                        except Exception as e:
                            logger.error(f"Failed to move {requester.display_name} to consultation: {e}")
                    
                    if storyteller.voice and storyteller.voice.channel:
                        try:
                            await storyteller.move_to(exception_channel)
                            moved_users.append(storyteller.display_name)
                        except Exception as e:
                            logger.error(f"Failed to move {storyteller.display_name} to consultation: {e}")
                    
                    if moved_users:
                        await message.channel.send(f"✅ Consultation started: {', '.join(moved_users)} moved to {exception_channel.name}.")
                    else:
                        await message.channel.send("⚠️ Could not move users. Make sure both are in voice channels.")
                else:
                    await message.channel.send(f"❌ {storyteller.display_name} declined the consultation request.")
                
                # Clean up the request message
                try:
                    await request_msg.delete()
                except:
                    pass
                    
            except asyncio.TimeoutError:
                await message.channel.send(f"⏱️ Consultation request timed out (no response from {storyteller.display_name}).")
                try:
                    await request_msg.delete()
                except:
                    pass
            return

        if content_lower.startswith("*shadows"):
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete messages
            all_followers = await db.get_all_followers_for_guild(message.guild.id)
            if not all_followers:
                await message.channel.send("> 🌑 **No one is following anyone right now.**")
                return

            embed = discord.Embed(
                title="🌘 Current Shadows",
                color=discord.Color.purple()
            )

            for target_id, followers in all_followers.items():
                target_member = message.guild.get_member(target_id)
                if target_member:
                    names = [
                        message.guild.get_member(f).display_name
                        for f in followers
                        if message.guild.get_member(f)
                    ]
                    embed.add_field(
                        name=f"👤 {target_member.display_name}",
                        value=", ".join(names) if names else "_No followers_",
                        inline=False
                    )

            msg = await message.channel.send(embed=embed)
            await msg.delete(delay=DELETE_DELAY_LONG)
            return

        # --- DND ---
        if content_lower.startswith("*dnd"):
            is_dnd = await db.is_dnd(target.id)
            if is_dnd:
                await db.set_dnd(target.id, False)
                msg = await message.channel.send("DND disabled. People can now follow you.")
            else:
                await db.set_dnd(target.id, True)
                # Remove all followers when enabling DND
                followers = await db.get_followers(target.id, message.guild.id)
                follower_targets = self.bot.follower_targets
                for follower_id in followers:
                    await db.remove_follower(follower_id, message.guild.id)
                    follower_targets.pop(follower_id, None)
                msg = await message.channel.send("DND enabled. People cannot follow you.")
            await self.bot.clean_followers(message.guild)
            await msg.delete(delay=DELETE_DELAY_QUICK)
            return

        # --- Players list ---
        if first_word == "*players":
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete messages
            guild = message.guild
            guild_id = guild.id
            
            # Get session context from the channel where command was run
            botc_category = None
            if message.channel and message.channel.category:
                # Command run from within a category - use that category
                botc_category = message.channel.category
            else:
                # Command run from outside a category - try to get default BOTC category
                guild_config = await db.get_guild(guild_id)
                if guild_config and guild_config.get("botc_category_id"):
                    botc_category = await self.bot.get_botc_category(guild, self.bot.db)
            
            if not botc_category:
                msg = await message.channel.send(
                    "❌ Cannot determine which category to check players in.\n"
                    "Either run this command from a text channel inside your BOTC category, "
                    "or have an admin configure a default BOTC category with `*setbotc <category_name|category_id>`."
                )
                await msg.delete(delay=DELETE_DELAY_ERROR)
                return

            players = []
            player_map = {}  # Map user_id -> (display_name, base_name)
            # iterate voice channels in the configured category
            for vc in botc_category.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    name = self.bot.get_member_name(member)
                    base_name, is_player = self.bot.get_player_role(member)
                    if not is_player:
                        continue
                    # Track by user ID instead of nickname
                    player_map[member.id] = (name, base_name)
                    players.append((name, base_name))

            # --- Player activity logging ---
            try:
                activity_log_path = Path(__file__).resolve().parent.parent.parent / "player_activity_log.json"
                now = int(time.time())
                player_count = len(players)
                # Load existing log or start new
                if activity_log_path.exists():
                    with open(activity_log_path, "r") as f:
                        activity_log = json.load(f)
                else:
                    activity_log = []
                activity_log.append([now, player_count])
                # Optionally, keep only the last 1000 entries
                activity_log = activity_log[-1000:]
                with open(activity_log_path, "w") as f:
                    json.dump(activity_log, f)
            except Exception as e:
                logger.warning(f"Failed to log player activity: {e}")

            # Compare with last snapshot to find who joined/left
            # Track by user ID for accurate join/leave detection (immune to nickname changes)
            current_player_ids = set(player_map.keys())
            last_player_snapshots = self.bot.last_player_snapshots
            
            # Get session from channel context for session-scoped snapshots
            snapshot_key = (guild.id, None)
            get_session_func = getattr(self.bot, "get_session_from_channel", None)
            if get_session_func:
                session = await get_session_func(message.channel, self.bot.session_manager)
                if session:
                    snapshot_key = (guild.id, session.category_id)
            
            last_snapshot = last_player_snapshots.get(snapshot_key, set())
            
            joined_ids = current_player_ids - last_snapshot
            left_ids = last_snapshot - current_player_ids
            
            # Resolve names for display
            joined = [player_map[uid][1] for uid in joined_ids]  # base_name
            left = []
            for uid in left_ids:
                # Try to get current name if member still in guild
                member = guild.get_member(uid)
                if member:
                    base_name, _ = self.bot.get_player_role(member)
                    left.append(base_name)
                else:
                    # Member left guild, can't resolve name
                    left.append(f"<@{uid}>")
            
            # Update snapshot for next time (session-scoped)
            last_player_snapshots[snapshot_key] = current_player_ids

            # send pretty embed with player list
            embed = discord.Embed(
                title="👥 Active Players",
                description=f"**{len(players)} player(s)**:",
                color=discord.Color.dark_red()
            )
            
            # Handle potentially large player lists to avoid hitting Discord's 6000 char embed limit
            if players:
                # Display with full names (including prefixes)
                player_list = "\n".join([f"• {display_name}" for (display_name, base_name) in sorted(players, key=lambda x: x[1])])
                # Check if the player list would be too large (leave room for other fields)
                # Estimate: title (~20) + description (~30) + field name (~10) + other fields (~300) = ~360
                # Safe limit for this field: ~5500 chars
                if len(player_list) > 5500:
                    # Truncate and show count of hidden players
                    truncated = []
                    char_count = 0
                    hidden_count = 0
                    for (display_name, base_name) in sorted(players, key=lambda x: x[1]):
                        line = f"• {display_name}\n"
                        if char_count + len(line) > 5400:  # Leave room for "...and X more"
                            hidden_count = len(players) - len(truncated)
                            break
                        truncated.append(f"• {display_name}")
                        char_count += len(line)
                    player_list = "\n".join(truncated)
                    if hidden_count > 0:
                        player_list += f"\n\n...and {hidden_count} more"
                embed.add_field(name="Playing", value=player_list, inline=False)
            else:
                embed.description = "No players in voice channels right now."
            
            # Show joined/left only if there was a previous snapshot
            if last_snapshot:
                if joined:
                    joined_list = ", ".join(sorted(joined))
                    # Truncate joined list if too large (unlikely but possible)
                    if len(joined_list) > 1000:
                        joined_list = joined_list[:997] + "..."
                    embed.add_field(name="✅ Joined", value=joined_list, inline=False)
                if left:
                    left_list = ", ".join(sorted(left))
                    # Truncate left list if too large (unlikely but possible)
                    if len(left_list) > 1000:
                        left_list = left_list[:997] + "..."
                    embed.add_field(name="❌ Left", value=left_list, inline=False)
                if not joined and not left:
                    embed.add_field(name="📊 Changes", value="No changes since last check", inline=False)
            
            embed.set_footer(text="Updated in real-time")
            await message.channel.send(embed=embed)
            return

        # --- Changelog (Admin only) ---
        if first_word == "*changelog":
            if not self.bot.is_admin(message.author):
                await self.bot.send_temporary(message.channel, "Only administrators can view the changelog.", delay=DELETE_DELAY_QUICK)
                return
            
            try:
                await message.delete()
            except discord.errors.Forbidden:
                pass  # Bot doesn't have permission to delete messages
            
            if not changelog_data:
                await message.channel.send("Changelog data not available.")
                return
            
            # Show the latest version by default
            latest = changelog_data[0]
            
            embed = discord.Embed(
                title=f"{EMOJI_SCROLL} Grimkeeper Changelog - v{latest['version']}",
                description=latest['title'],
                color=discord.Color.blue()
            )
            
            # Add features
            features_text = "\n".join(latest['features'])
            embed.add_field(name="✨ What's New", value=features_text, inline=False)
            
            # Show total version count
            embed.set_footer(text=f"v{VERSION} | {len(changelog_data)} versions tracked")
            
            await message.channel.send(embed=embed)
            return
    
    async def _handle_game_command(self, message: discord.Message):
        """Display active game info for the current session.
        
        Usage: *game
        Shows current game status, players, duration, and storyteller.
        """
        
        if not self.bot.session_manager:
            await message.channel.send("Session manager not available.")
            return
        
        # Get session from current channel
        session = await self.bot.session_manager.get_session_from_channel(
            message.channel,
            message.guild
        )
        
        if not session:
            await message.channel.send(
                "⚠️ This category isn't configured for BOTC yet. Run `/setbotc` to set it up."
            )
            return
        
        db = self.bot.db
        guild_id = message.guild.id
        
        # Get active game
        active_game = await db.get_active_game(guild_id, session.category_id)
        
        if not active_game:
            await message.channel.send("No active game in this session. Start one with `/startgame`!")
            return
        
        # Build game info embed
        category = message.guild.get_channel(session.category_id)
        category_name = category.name if category else f"Category {session.category_id}"
        
        embed = discord.Embed(
            title=f"{EMOJI_TOWN_SQUARE} Active Game - {category_name}",
            description=f"Current game in progress",
            color=discord.Color.blue()
        )
        
        # Game details
        start_timestamp = int(active_game['start_time'])
        duration = int(time.time() - active_game['start_time'])
        hours, remainder = divmod(duration, 3600)
        minutes, _ = divmod(remainder, 60)
        
        game_info = f"**{EMOJI_SCRIPT} Script:** {active_game['script']}\n"
        game_info += f"**{EMOJI_PLAYERS} Players:** {active_game['player_count']}\n"
        game_info += f"**{EMOJI_CLOCK} Started:** <t:{start_timestamp}:F>\n"
        game_info += f"**{EMOJI_CLOCK} Duration:** {hours}h {minutes}m\n"
        
        if active_game.get('storyteller_id'):
            st_member = message.guild.get_member(active_game['storyteller_id'])
            if st_member:
                game_info += f"**{EMOJI_PEN} Storyteller:** {st_member.mention}\n"
        
        embed.add_field(name=f"{EMOJI_SCRIPT} Game Info", value=game_info, inline=False)
        
        # Session config
        config_info = ""
        if session.destination_channel_id:
            dest_channel = message.guild.get_channel(session.destination_channel_id)
            if dest_channel:
                config_info += f"**Town Square:** {dest_channel.mention}\n"
        
        if session.grimoire_link:
            config_info += f"**{EMOJI_SCROLL} Grimoire:** {session.grimoire_link}\n"
        
        if config_info.strip():  # Only add field if there's actual content
            embed.add_field(name=f"{EMOJI_GEAR} Session", value=config_info, inline=False)
        
        embed.set_footer(text=f"Game ID: {active_game['game_id']} | v{VERSION}")
        await message.channel.send(embed=embed)


async def setup(bot: commands.Bot):
    """Load the Commands cog."""
    await bot.add_cog(Commands(bot))
