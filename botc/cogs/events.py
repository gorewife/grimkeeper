"""Event handlers cog - handles Discord.py events.

This cog handles:
- on_ready: Bot startup, database initialization, command sync
- on_voice_state_update: Voice channel cap management, shadow followers
- on_member_update: Nickname change detection and validation
- on_guild_join: Welcome message for new servers
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

from botc.constants import (
    VERSION,
    PREFIX_ST,
    PREFIX_COST,
    PREFIX_SPEC,
    DELETE_DELAY_LONG,
    DELETABLE_COMMANDS,
    DELETE_DELAY_QUICK,
)

if TYPE_CHECKING:
    from botc.database import Database

logger = logging.getLogger('botc_bot')


class EventHandlers(commands.Cog):
    """Cog that handles Discord.py events."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminded_games = set()  # Track (guild_id, category_id) of games we've already reminded about
        # Track last reminder time per guild to enforce cooldown
        self._last_vc_cap_reminder = {}
        logger.info("EventHandlers cog initialized")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Handle bot ready event - initialization and startup tasks."""
        logger.info(f"Bot connected as {self.bot.user}")
        
        db: Database = self.bot.db
        
        # Initialize database connection
        try:
            await db.connect()
            await db.initialize_schema()
            logger.info("Database connected and initialized")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
        
        # Build follower_targets reverse index from database
        try:
            for guild in self.bot.guilds:
                all_followers = await db.get_all_followers_for_guild(guild.id)
                for target_id, follower_ids in all_followers.items():
                    for follower_id in follower_ids:
                        self.bot.follower_targets[follower_id] = target_id
            logger.info(f"Loaded {len(self.bot.follower_targets)} shadow follower mappings")
        except Exception as e:
            logger.error(f"Failed to load shadow followers: {e}")
        
        # Sync slash commands to Discord
        try:
            synced = await self.bot.tree.sync()
            logger.info(f"Synced {len(synced)} slash command(s)")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")
        
        # Check guild whitelist and leave non-whitelisted servers
        from botc.config import get_settings
        settings = get_settings()
        whitelisted_ids = settings.get_whitelisted_guild_ids()
        
        if whitelisted_ids:
            logger.info(f"Guild whitelist ACTIVE with {len(whitelisted_ids)} whitelisted server(s)")
            for guild in self.bot.guilds:
                if guild.id not in whitelisted_ids:
                    logger.warning(f"Leaving non-whitelisted guild: {guild.name} (ID: {guild.id})")
                    try:
                        await guild.leave()
                        logger.info(f"Successfully left {guild.name}")
                    except Exception as e:
                        logger.error(f"Failed to leave {guild.name}: {e}")
        else:
            logger.info(f"Guild whitelist disabled - bot will accept all server invites")
        
        # Set bot status/activity
        activity = discord.Game(name="Blood on the Clocktower | *help")
        await self.bot.change_presence(activity=activity)
        
        # Start background task for session cleanup
        self.cleanup_inactive_sessions.start()
        
        # Start background task for long-running game reminders
        self.check_long_running_games.start()
        
        # Start announcement processor for website events
        if hasattr(self.bot, 'announcement_processor') and self.bot.announcement_processor:
            self.bot.announcement_processor.start()
            logger.info("Started announcement processor")
        
        # Start cleanup task for stale shadow followers
        if hasattr(self.bot, 'cleanup_task') and self.bot.cleanup_task:
            self.bot.cleanup_task.start()
            logger.info("Started cleanup task")
        
        # Restore persisted timers from before restart
        if self.bot.timer_manager:
            await self.bot.timer_manager.load_timers()
        
        # Startup announcement disabled; updates will be logged in the bot's Discord server.
    
    @tasks.loop(hours=24)
    async def cleanup_inactive_sessions(self):
        """Background task to clean up inactive sessions daily."""
        session_manager = self.bot.session_manager
        if session_manager:
            try:
                deleted = await session_manager.cleanup_inactive_sessions(max_age_days=30)
                if deleted > 0:
                    logger.info(f"Auto-cleanup: Removed {deleted} inactive session(s)")
            except Exception as e:
                logger.error(f"Error during session auto-cleanup: {e}")
    
    @cleanup_inactive_sessions.before_loop
    async def before_cleanup(self):
        """Wait for bot to be ready before starting cleanup loop."""
        await self.bot.wait_until_ready()
    
    @tasks.loop(hours=1.0)
    async def check_long_running_games(self):
        """Check for games running >2 hours and remind the storyteller to end them."""
        import time
        
        if not self.bot.db:
            return
        
        try:
            # Get all active games across all servers
            async with self.bot.db.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT g.guild_id, g.category_id, g.script, g.start_time, g.storyteller_id
                    FROM games g
                    WHERE g.end_time IS NULL
                """)
            
            current_time = time.time()
            two_hours = 7200  # 2 hours in seconds
            
            for row in rows:
                duration = current_time - row['start_time']
                game_key = (row['guild_id'], row.get('category_id'))
                
                three_hours = 10800  # 3 hours in seconds
                
                # Remind if game is between 2 and 3 hours old and not already reminded this session
                if duration > two_hours and duration < three_hours and game_key not in self.reminded_games:
                    try:
                        guild = self.bot.get_guild(row['guild_id'])
                        if not guild:
                            continue
                        
                        session = None
                        if self.bot.session_manager and row.get('category_id'):
                            session = await self.bot.session_manager.get_session(row['guild_id'], row['category_id'])
                        
                        hours = int(duration / 3600)
                        minutes = int((duration % 3600) / 60)
                        
                        # Long game reminder removed - announce_channel deprecated
                        self.reminded_games.add(game_key)
                        logger.info(f"Long game detected in {guild.name}: {hours}h {minutes}m (reminders disabled)")
                        continue
                        
                        # Code below is unreachable and should be removed in future cleanup
                        storyteller = await self.bot.fetch_user(row['storyteller_id'])
                        if storyteller:
                            embed = discord.Embed(
                                title="⏰ Long-Running Game Reminder",
                                description=f"Your game in **{guild.name}** has been running for **{hours}h {minutes}m**.",
                                color=discord.Color.orange()
                            )
                            embed.add_field(
                                name="Script",
                                value=row['script'],
                                inline=True
                            )
                            embed.add_field(
                                name="Reminder",
                                value="Don't forget to use `/endgame` when you're finished!",
                                inline=False
                            )
                            
                            await storyteller.send(embed=embed)
                            
                            self.reminded_games.add(game_key)
                            
                            logger.info(f"Sent long-running game reminder to {storyteller.name} for game in {guild.name} ({hours}h {minutes}m)")
                        
                    except discord.Forbidden:
                        logger.warning(f"Cannot DM user {row['storyteller_id']} for long-running game reminder")
                    except Exception as e:
                        logger.error(f"Error sending reminder for game in guild {row['guild_id']}: {e}")
                
                elif game_key in self.reminded_games and duration <= two_hours:
                    self.reminded_games.discard(game_key)
        
        except Exception as e:
            logger.error(f"Error during long-running game check: {e}")
    
    @check_long_running_games.before_loop
    async def before_game_check(self):
        """Wait for bot to be ready before starting game check loop."""
        await self.bot.wait_until_ready()
    
    async def _send_game_confirmation(
        self, 
        channel: discord.TextChannel, 
        game_row: dict, 
        guild: discord.Guild,
        hours: int,
        minutes: int
    ):
        """Send interactive game confirmation with auto-cancel if no response."""
        from botc.constants import COLOR_WARNING
        
        class GameConfirmationView(discord.ui.View):
            def __init__(self, bot, game_row, timeout_seconds=300):
                super().__init__(timeout=timeout_seconds)
                self.bot = bot
                self.game_row = game_row
                self.answered = False
            
            @discord.ui.button(label="✅ Still Playing", style=discord.ButtonStyle.success)
            async def still_playing(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.answered = True
                self.stop()
                await interaction.response.edit_message(
                    content=f"✅ Game confirmed active by {interaction.user.mention}",
                    embed=None,
                    view=None
                )
            
            @discord.ui.button(label="❌ Game Ended", style=discord.ButtonStyle.danger)
            async def game_ended(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.answered = True
                self.stop()
                try:
                    await self.bot.db.cancel_game(
                        self.game_row['guild_id'], 
                        self.game_row.get('category_id')
                    )
                    event_handler = self.bot.get_cog('EventHandlers')
                    if event_handler and hasattr(event_handler, 'reminded_games'):
                        game_key = (self.game_row['guild_id'], self.game_row.get('category_id'))
                        event_handler.reminded_games.discard(game_key)
                    await interaction.response.edit_message(
                        content=f"❌ Game cancelled by {interaction.user.mention}. This game was not recorded in history.",
                        embed=None,
                        view=None
                    )
                    logger.info(f"Long-running game auto-cancelled by {interaction.user.name}")
                except Exception as e:
                    logger.error(f"Error cancelling game: {e}")
                    await interaction.response.send_message(
                        "⚠️ Error cancelling game. Please use `/endgame` manually.",
                        ephemeral=True
                    )
            
            async def on_timeout(self):
                # Auto-cancel game if no response within timeout
                if not self.answered:
                    try:
                        await self.bot.db.cancel_game(
                            self.game_row['guild_id'], 
                            self.game_row.get('category_id')
                        )
                        event_handler = self.bot.get_cog('EventHandlers')
                        if event_handler and hasattr(event_handler, 'reminded_games'):
                            game_key = (self.game_row['guild_id'], self.game_row.get('category_id'))
                            event_handler.reminded_games.discard(game_key)
                        logger.info(f"Long-running game auto-cancelled due to timeout")
                    except Exception as e:
                        logger.error(f"Error auto-cancelling game on timeout: {e}")
        
        embed = discord.Embed(
            title="⏰ Game Status Check",
            description=(
                f"A game has been running for **{hours}h {minutes}m**.\n\n"
                f"**Script:** {game_row['script']}\n\n"
                f"Is this game still active? If no one responds in **5 minutes**, "
                f"the game will be automatically cancelled."
            ),
            color=COLOR_WARNING
        )
        embed.set_footer(text="Click a button below to respond")
        
        view = GameConfirmationView(self.bot, game_row, timeout_seconds=300)
        message = await channel.send(embed=embed, view=view)
        
        await view.wait()
        
        if not view.answered:
            try:
                await message.edit(
                    content="⏱️ No response received. Game has been automatically cancelled.",
                    embed=None,
                    view=None
                )
            except Exception as e:
                logger.error(f"Error updating timeout message: {e}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates for channel cap management and shadow followers."""
        try:
            name = self.bot.get_member_name(member)
            check_name = self.bot.strip_brb_prefix(name)
            is_privileged = (
                check_name.startswith(PREFIX_ST)
                or check_name.startswith(PREFIX_COST)
                or check_name.startswith(PREFIX_SPEC)
            )
            if after.channel and is_privileged:
                if not before.channel or before.channel.id != after.channel.id:
                    await self._handle_vc_cap_join(member, after.channel)
            if before.channel and is_privileged:
                if not after.channel or before.channel.id != after.channel.id:
                    await self._handle_vc_cap_leave(member, before.channel)
        except Exception:
            logger.exception("Unhandled error in on_voice_state_update (cap management)")
        try:
            db: Database = self.bot.db
            followers = await db.get_followers(member.id, member.guild.id)
            if followers and after.channel:
                for follower_id in followers:
                    follower = member.guild.get_member(follower_id)
                    if follower and follower.voice:
                        try:
                            await follower.move_to(after.channel)
                        except Exception as e:
                            logger.warning(f"Could not move follower {follower.display_name}: {e}")
        except Exception:
            logger.exception("Unhandled error in on_voice_state_update (shadow followers)")
    
    async def _handle_vc_cap_join(self, member: discord.Member, channel: discord.VoiceChannel):
        """Handle privileged user joining a voice channel - increase cap by 1."""
        try:
            if not channel.category:
                return
            session_manager = getattr(self.bot, "session_manager", None)
            if not session_manager:
                return
            session = await session_manager.get_session(member.guild.id, channel.category.id)
            if not session or not session.vc_caps:
                return
            original_cap = session.vc_caps.get(channel.id)
            if not original_cap:
                return
            _, can_edit = self.bot.check_bot_permissions(member.guild)
            if not can_edit:
                return
            try:
                current_cap = channel.user_limit or 0
                new_cap = current_cap + 1
                await channel.edit(user_limit=new_cap)
                logger.info(f"Increased cap for {channel.name}: {current_cap} → {new_cap} (privileged user joined)")
            except Exception as e:
                logger.error(f"Failed to increase cap for {channel.name}: {e}")
        except Exception:
            logger.exception("Error in _handle_vc_cap_join")
    
    async def _handle_vc_cap_leave(self, member: discord.Member, channel: discord.VoiceChannel):
        """Handle privileged user leaving - restore to snapshot + remaining privileged count."""
        try:
            if not channel.category:
                return
            session_manager = getattr(self.bot, "session_manager", None)
            if not session_manager:
                return
            session = await session_manager.get_session(member.guild.id, channel.category.id)
            if not session or not session.vc_caps:
                return
            original_cap = session.vc_caps.get(channel.id)
            if not original_cap:
                return
            _, can_edit = self.bot.check_bot_permissions(member.guild)
            if not can_edit:
                return
            privileged_count = 0
            for m in channel.members:
                if m.bot:
                    continue
                if m.id == member.id:
                    continue
                name = self.bot.get_member_name(m)
                check_name = self.bot.strip_brb_prefix(name)
                if (check_name.startswith(PREFIX_ST) or 
                    check_name.startswith(PREFIX_COST) or 
                    check_name.startswith(PREFIX_SPEC)):
                    privileged_count += 1
            try:
                new_cap = original_cap + privileged_count
                await channel.edit(user_limit=new_cap)
                logger.info(f"Adjusted cap for {channel.name} to {new_cap} (snapshot {original_cap} + {privileged_count} privileged)")
            except Exception as e:
                logger.error(f"Failed to restore cap for {channel.name}: {e}")
        except Exception:
            logger.exception("Error in _handle_vc_cap_leave")
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Handle member updates (nickname changes) to warn about manual prefix changes."""
        try:
            if before.nick == after.nick:
                return
            change_key = (after.id, after.nick)
            bot_initiated_nick_changes = self.bot.bot_initiated_nick_changes
            if change_key in bot_initiated_nick_changes:
                bot_initiated_nick_changes.discard(change_key)
                return
            if after.guild.owner_id == after.id:
                return
            before_name = before.nick or before.display_name or ""
            after_name = after.nick or after.display_name or ""
            before_stripped = self.bot.strip_brb_prefix(before_name)
            after_stripped = self.bot.strip_brb_prefix(after_name)
            before_has_prefix = (before_stripped.startswith(PREFIX_ST) or 
                                before_stripped.startswith(PREFIX_COST) or 
                                before_stripped.startswith(PREFIX_SPEC))
            after_has_prefix = (after_stripped.startswith(PREFIX_ST) or 
                               after_stripped.startswith(PREFIX_COST) or 
                               after_stripped.startswith(PREFIX_SPEC))
            if before_has_prefix != after_has_prefix:
                await self._send_nickname_warning(after, before_stripped, after_stripped)
                if after.voice and after.voice.channel:
                    channel = after.voice.channel
                    if after_has_prefix:
                        await self._handle_vc_cap_join(after, channel)
                    else:
                        await self._handle_vc_cap_leave(after, channel)
        except Exception as e:
            logger.exception(f"Error in on_member_update: {e}")
    
    async def _send_nickname_warning(self, member: discord.Member, before_stripped: str, after_stripped: str):
        """Send warning about manual nickname changes."""
        try:
            if after_stripped.startswith(PREFIX_ST):
                command = "`*st`"
            elif after_stripped.startswith(PREFIX_COST):
                command = "`*cost`"
            elif after_stripped.startswith(PREFIX_SPEC):
                command = "`*!`"
            else:
                if before_stripped.startswith(PREFIX_ST):
                    command = "`*st`"
                elif before_stripped.startswith(PREFIX_COST):
                    command = "`*cost`"
                else:
                    command = "`*!`"
            embed = discord.Embed(
                title="⚠️ Manual Nickname Change Detected",
                description=(
                    f"Please use the bot command {command} instead of manually changing your nickname.\n\n"
                    f"Manual changes can cause issues with:\n"
                    f"• Voice channel capacity tracking\n"
                    f"• Game state management\n"
                    f"• Player role identification\n\n"
                    f"Use {command} to properly toggle your role."
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text="Grimkeeper Bot • Use bot commands for best experience")
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                target_channel = await self._find_notification_channel(member.guild)
                if target_channel:
                    await target_channel.send(f"{member.mention}", embed=embed, delete_after=DELETE_DELAY_LONG)
        except Exception as e:
            logger.warning(f"Could not send nickname change warning to {member.display_name}: {e}")
    
    async def _find_notification_channel(self, guild: discord.Guild) -> discord.TextChannel:
        """Find a suitable channel for notifications."""
        botc_category = await self.bot.get_botc_category(guild, self.bot.db)
        if botc_category:
            for channel in botc_category.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    return channel
        
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel
        
        return None
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Send welcome message when bot joins a new server."""
        logger.info(f"Bot joined new guild: {guild.name} (ID: {guild.id})")
        
        # Check guild whitelist
        from botc.config import get_settings
        settings = get_settings()
        whitelisted_ids = settings.get_whitelisted_guild_ids()
        
        if whitelisted_ids and guild.id not in whitelisted_ids:
            logger.warning(f"Guild {guild.name} (ID: {guild.id}) is not whitelisted. Leaving...")
            try:
                await guild.leave()
                logger.info(f"Left non-whitelisted guild: {guild.name}")
            except Exception as e:
                logger.error(f"Failed to leave non-whitelisted guild {guild.name}: {e}")
            return
        
        # Find the first text channel the bot can send messages to
        target_channel = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                target_channel = channel
                break
        
        if not target_channel:
            logger.warning(f"No accessible text channel found in {guild.name} to send welcome message")
            return
        
        try:
            embed = discord.Embed(
                title="🩸 Welcome to Grimkeeper",
                description=(
                    "Thank you for adding Grimkeeper to your server!\n\n"
                    "**Important:** Grimkeeper works on a **category-basis**. "
                    "Game commands require you to set up a BOTC category first."
                ),
                color=discord.Color.dark_red()
            )
            
            embed.add_field(
                name="🚀 Quick Setup Options",
                value=(
                    "**Option 1: Automatic Setup (Recommended)**\n"
                    "Use `/autosetup` to automatically create a gothic-themed BOTC server structure!\n\n"
                    "**Option 2: Manual Setup**\n"
                    "1. Create a Discord category for your game (any name you want)\n"
                    "2. Create text and voice channels inside that category\n"
                    "3. Run `/setbotc <category>` to create a session for that category\n"
                    "4. Then configure it from within the category:\n"
                    "   - `/settown #voice-channel` - Set Town Square\n"
                    "   - `/setexception #voice-channel` (optional) - Set private ST channel\n\n"
                    "**Multi-Session Support:**\n"
                    "Run `/autosetup` multiple times or use `/setbotc` on different categories to create multiple independent game sessions. "
                    "Each session is persistent and has its own session code for website integration."
                ),
                inline=False
            )
            
            embed.add_field(
                name="📖 Getting Started",
                value=(
                    "• Type `*help` or `/help` to see all commands\n"
                    "• Storytellers use `*st` to claim their role\n"
                    "• Use `/startgame` to begin tracking games\n"
                    "• Commands are **session-scoped** - they affect only the category you use them in\n"
                    "• Check out `*changelog` to see what's new!"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔑 Required Permissions",
                value=(
                    "For full functionality, ensure the bot has:\n"
                    "• Manage Nicknames\n"
                    "• Move Members\n"
                    "• Manage Channels\n"
                    "• Manage Messages\n"
                    "• Send Messages & Embed Links\n"
                    "• Add Reactions"
                ),
                inline=False
            )
            
            embed.set_footer(text=f"Grimkeeper v{VERSION} | contact `hystericca` if you need help setting up")
            
            await target_channel.send(embed=embed)
            logger.info(f"Sent welcome message to {guild.name} in #{target_channel.name}")
            
        except Exception as e:
            logger.error(f"Failed to send welcome message to {guild.name}: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Log all DMs sent to the bot."""
        if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
            logger.info(f"📬 DM from {message.author.name} ({message.author.id}): {message.content}")
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if not isinstance(channel, discord.VoiceChannel):
            return
        session_manager = getattr(self.bot, "session_manager", None)
        if not session_manager:
            return
        session = await session_manager.get_session(channel.guild.id, channel.category.id) if channel.category else None
        if not session or not session.vc_caps:
            return
        if channel.user_limit > 0 and channel.id not in session.vc_caps:
            # Voice cap warning removed - announce_channel deprecated
            logger.info(f"Capped voice channel created in BOTC category: {channel.name} (notifications disabled)")
            if False:  # Disabled
                await channel.guild.text_channels[0].send(
                    f"⚠️ A new capped voice channel `{channel.name}` was created in a BOTC category.\n"
                    f"Please run `/setbotc` in this category after you're done adding channels to update the cap snapshot.\n"
                    f"(This reminder will not repeat for 1 hour.)"
                )


async def setup(bot: commands.Bot):
    """Setup function for loading the cog."""
    await bot.add_cog(EventHandlers(bot))
