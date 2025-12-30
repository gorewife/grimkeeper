from __future__ import annotations

import logging
import asyncio
import re
import json
from typing import List
import discord
from discord import app_commands
from discord.ext import commands

from botc.polls import create_poll_internal, _end_poll
from botc.wiki import fetch_character, truncate_text
from botc.discord_utils import safe_send_interaction, safe_defer
from botc.constants import EMOJI_QUESTION, EMOJI_GEAR, EMOJI_SCROLL, EMOJI_PEN, EMOJI_STAR
from botc.database import Database
from botc.i18n import get_translator

logger = logging.getLogger("botc_bot")


class CharacterView(discord.ui.View):
    """Button navigation for character information sections."""
    
    def __init__(self, char_info, initial_section: str = "summary"):
        super().__init__(timeout=300)
        self.char_info = char_info
        self.current_section = initial_section
        self.current_page = 0
        self._remove_empty_buttons()
        self._update_button_states()
    
    def _remove_empty_buttons(self):
        """Remove buttons for sections without content."""
        to_remove = []
        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue
            if item.custom_id == "tips" and not self.char_info.tips_and_tricks:
                to_remove.append(item)
            elif item.custom_id == "bluffing" and not self.char_info.bluffing:
                to_remove.append(item)
            elif item.custom_id == "howtorun" and not self.char_info.how_to_run:
                to_remove.append(item)
            elif item.custom_id == "fighting" and not self.char_info.fighting:
                to_remove.append(item)
        for item in to_remove:
            self.remove_item(item)
    
    def _update_button_states(self):
        """Highlight the current section button."""
        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue
            if item.custom_id in ["summary", "tips", "bluffing", "howtorun", "fighting"]:
                item.style = discord.ButtonStyle.primary if item.custom_id == self.current_section else discord.ButtonStyle.secondary
    
    def _format_list_content(self, text: str) -> str:
        """Format bullet-point content into numbered list for better readability."""
        if not text:
            return ""
        
        # Split by bullet points
        items = [item.strip() for item in text.split('•') if item.strip()]
        
        # If there are clear list items, number them
        if len(items) > 1:
            formatted = []
            for i, item in enumerate(items, 1):
                # Clean up the item
                item = item.strip()
                if item:
                    formatted.append(f"**{i}.** {item}")
            return '\n\n'.join(formatted)
        
        # Otherwise return as-is
        return text
    
    def _split_content(self, text: str, max_len: int = 1200) -> List[str]:
        """Split text into chunks that fit Discord limits (3-4 paragraphs per page)."""
        if not text:
            return []
        
        # Format the content first
        formatted = self._format_list_content(text)
        
        if len(formatted) <= max_len:
            return [formatted]
        
        chunks = []
        current = ""
        
        # Split by numbered items if formatted, otherwise by paragraphs
        if '\n\n**' in formatted:
            items = formatted.split('\n\n')
        else:
            items = formatted.split('\n\n')
        
        for item in items:
            if len(current) + len(item) + 2 <= max_len:
                current += item + '\n\n'
            else:
                if current:
                    chunks.append(current.strip())
                # If single item is too long, force split
                if len(item) > max_len:
                    chunks.append(item[:max_len-3] + '...')
                    current = ""
                else:
                    current = item + '\n\n'
        
        if current:
            chunks.append(current.strip())
        
        return chunks if chunks else [formatted[:max_len]]
    
    def _create_embed(self, section: str, page: int = 0) -> discord.Embed:
        """Create embed for the given section and page."""
        embed = discord.Embed(
            title=self.char_info.name,
            color=self.char_info.get_team_color(),
            url=self.char_info.wiki_url
        )
        
        if section == "summary":
            # Summary: Character icon + ability
            if self.char_info.icon_url:
                embed.set_thumbnail(url=self.char_info.icon_url)
            
            desc_parts = [f"**{self.char_info.character_type}**"]
            if self.char_info.appears_in:
                desc_parts.append(f"*Appears in: {', '.join(self.char_info.appears_in)}*")
            desc_parts.append("")  # blank line
            
            if self.char_info.ability:
                ability = self.char_info.ability
                if len(ability) > 3000:  # Leave room for the rest
                    ability = ability[:2997] + "..."
                desc_parts.append(f'*"{ability}"*')
            
            embed.description = '\n'.join(desc_parts)
            embed.set_footer(text="Click title to view on wiki")
            
        else:
            # Paginated sections
            if self.char_info.icon_url:
                embed.set_thumbnail(url=self.char_info.icon_url)
            
            content_map = {
                "tips": self.char_info.tips_and_tricks,
                "bluffing": self.char_info.bluffing,
                "howtorun": self.char_info.how_to_run,
                "fighting": self.char_info.fighting
            }
            section_names = {
                "tips": "Tips & Tricks",
                "bluffing": "Bluffing",
                "howtorun": "How to Run",
                "fighting": "Fighting"
            }
            
            content = content_map.get(section, "")
            chunks = self._split_content(content)
            
            if chunks and page < len(chunks):
                embed.description = chunks[page]
                if len(chunks) > 1:
                    embed.set_footer(text=f"{section_names.get(section, section)} • Page {page + 1}/{len(chunks)}")
                    self._manage_pagination_buttons(page, len(chunks))
                else:
                    embed.set_footer(text="Click title to view on wiki")
                    self._manage_pagination_buttons(page, 1)  # Remove pagination buttons
            else:
                embed.description = "*No content available*"
                embed.set_footer(text="Click title to view on wiki")
                self._manage_pagination_buttons(0, 1)
        
        return embed
    
    def _manage_pagination_buttons(self, page: int, total: int):
        """Add or remove pagination buttons as needed."""
        # Remove existing pagination buttons
        to_remove = [i for i in self.children if isinstance(i, discord.ui.Button) and i.custom_id in ["prev", "next"]]
        for i in to_remove:
            self.remove_item(i)
        
        # Add new ones if multi-page
        if total > 1:
            prev_btn = discord.ui.Button(
                label="◀",
                style=discord.ButtonStyle.secondary,
                custom_id="prev",
                row=2,
                disabled=(page == 0)
            )
            prev_btn.callback = self._make_page_callback(-1)
            self.add_item(prev_btn)
            
            next_btn = discord.ui.Button(
                label="▶",
                style=discord.ButtonStyle.secondary,
                custom_id="next",
                row=2,
                disabled=(page >= total - 1)
            )
            next_btn.callback = self._make_page_callback(1)
            self.add_item(next_btn)
    
    def _make_page_callback(self, delta: int):
        """Create a callback for page navigation."""
        async def callback(interaction: discord.Interaction):
            self.current_page += delta
            if self.current_page < 0:
                self.current_page = 0
            embed = self._create_embed(self.current_section, self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        return callback
    
    def _make_section_callback(self, section: str):
        """Create a callback for section navigation."""
        async def callback(interaction: discord.Interaction):
            self.current_section = section
            self.current_page = 0
            self._update_button_states()
            embed = self._create_embed(section, 0)
            await interaction.response.edit_message(embed=embed, view=self)
        return callback
    
    @discord.ui.button(label="Summary", custom_id="summary", style=discord.ButtonStyle.primary, row=0)
    async def summary_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_section_callback("summary")(interaction)
    
    @discord.ui.button(label="Tips", custom_id="tips", style=discord.ButtonStyle.secondary, row=0)
    async def tips_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_section_callback("tips")(interaction)
    
    @discord.ui.button(label="Bluffing", custom_id="bluffing", style=discord.ButtonStyle.secondary, row=0)
    async def bluffing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_section_callback("bluffing")(interaction)
    
    @discord.ui.button(label="How to Run", custom_id="howtorun", style=discord.ButtonStyle.secondary, row=1)
    async def howtorun_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_section_callback("howtorun")(interaction)
    
    @discord.ui.button(label="Fighting", custom_id="fighting", style=discord.ButtonStyle.secondary, row=1)
    async def fighting_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_section_callback("fighting")(interaction)



class StartGameConfirmView(discord.ui.View):
    """Confirmation view for /startgame with player roster preview."""
    
    def __init__(self, bot, guild: discord.Guild, script_value: str, display_name: str, storyteller: discord.Member, original_interaction: discord.Interaction):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.guild = guild
        self.script_value = script_value
        self.display_name = display_name
        self.storyteller = storyteller
        self.original_interaction = original_interaction
        self.confirmed = False
    
    async def get_player_lists(self):
        """Scan voice channels and return (players, spectators, main_st, co_sts) tuple.
        
        Returns:
            tuple: (list of player tuples, list of spectator names, main ST member, list of Co-ST members)
        """
        # Use bot methods instead of importing from main
        from botc.constants import PREFIX_ST, PREFIX_COST
        
        # Get category from original interaction channel
        botc_category = None
        if self.original_interaction.channel and self.original_interaction.channel.category:
            botc_category = self.original_interaction.channel.category
        else:
            # Fallback to configured BOTC category
            guild_config = await self.bot.db.get_guild(self.guild.id)
            if guild_config and guild_config.get("botc_category_id"):
                botc_category = await self.bot.get_botc_category(self.guild, self.bot.db)
        
        if not botc_category:
            return ([], [], None, [])
        
        players = []
        player_ids = []
        spectators = []
        main_st = None
        co_sts = []
        
        for vc in botc_category.voice_channels:
            for vc_member in vc.members:
                if vc_member.bot:
                    continue
                name = vc_member.nick or vc_member.display_name or vc_member.name
                base_name, is_player = self.bot.get_player_role(vc_member)
                
                # Check if this is ST or Co-ST
                if name.startswith(PREFIX_ST):
                    main_st = vc_member
                elif name.startswith(PREFIX_COST):
                    co_sts.append(vc_member)
                elif is_player:
                    players.append((name, base_name, vc_member.id))
                    player_ids.append(vc_member.id)
                else:
                    spectators.append(name)
        
        return (players, spectators, main_st, co_sts)
    
    def create_roster_embed(self, players: List[tuple], spectators: List[str], main_st, co_sts: List) -> discord.Embed:
        """Create embed showing current player roster.
        
        Args:
            players: List of (display_name, base_name, user_id) tuples
            spectators: List of spectator display names
            main_st: Main storyteller Discord member (or None)
            co_sts: List of Co-ST Discord members
        
        Returns:
            Discord embed with roster information
        """
        from botc.utils import strip_st_prefix
        
        # Build description with ST info
        if main_st:
            st_name = strip_st_prefix(main_st.display_name)
            description = f"**Script:** {self.display_name}\n**{EMOJI_PEN} Storyteller:** {st_name}"
            
            if co_sts:
                co_st_names = [strip_st_prefix(co.display_name) for co in co_sts]
                description += f"\n**Co-Storyteller(s):** {', '.join(co_st_names)}"
            
            description += "\n\nVerify the player roster below, then click **✅ Confirm** to start tracking the game."
        else:
            description = (
                f"**Script:** {self.display_name}\n"
                "⚠️ **No main Storyteller found!**\n"
                "Someone must use `*st` to become the main ST before starting.\n"
                "Co-Storytellers alone are not enough."
            )
        
        embed = discord.Embed(
            title="🎲 Confirm Game Start",
            description=description,
            color=discord.Color.blue() if main_st else discord.Color.red()
        )
        
        # Players section
        if players:
            player_names = [name for (name, _, _) in players]
            players_text = ", ".join(player_names) if len(player_names) <= 25 else ", ".join(player_names[:25]) + f"\n*...and {len(player_names) - 25} more*"
            embed.add_field(
                name=f"👥 Players ({len(players)})",
                value=players_text or "*None*",
                inline=False
            )
        else:
            embed.add_field(
                name=f"👥 Players (0)",
                value="⚠️ **No players detected!** Make sure players are in BOTC voice channels and have not toggled spectator mode with `*!`",
                inline=False
            )
        
        # Spectators section
        if spectators:
            spectators_text = ", ".join(spectators) if len(spectators) <= 15 else ", ".join(spectators[:15]) + f"\\n*...and {len(spectators) - 15} more*"
            embed.add_field(
                name=f"👻 Spectators ({len(spectators)})",
                value=spectators_text,
                inline=False
            )
        
        embed.set_footer(text="Use 🔄 Refresh to update the list after players toggle *! or move channels")
        
        return embed
    
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success, row=0)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and start the game."""
        # Allow any ST or Co-ST to confirm, but verify main ST exists
        is_st_or_cost = getattr(self.bot, "is_storyteller", lambda m: False)(interaction.user)
        
        if not is_st_or_cost:
            await interaction.response.send_message("Only storytellers can confirm game start.", ephemeral=True)
            return
        
        # Check if main ST exists before confirming
        players, spectators, main_st, co_sts = await self.get_player_lists()
        
        if not main_st:
            await interaction.response.send_message(
                "❌ Cannot start game without a main Storyteller.\n"
                "Someone must use `*st` to become the main ST (not Co-ST).",
                ephemeral=True
            )
            return
        
        self.confirmed = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        # Call the actual start game handler
        try:
            # Create a mock script object with value attribute
            class ScriptChoice:
                def __init__(self, value):
                    self.value = value
            
            script_obj = ScriptChoice(self.script_value)
            custom_name = self.display_name if self.script_value in ["Custom Script", "Homebrew Script"] else ""
            
            embed = await self.bot.start_game_handler(self.original_interaction, script_obj, custom_name)
            if embed:
                await self.original_interaction.followup.send(embed=embed, ephemeral=False)
        except Exception as e:
            logger.error(f"Error starting game from confirmation: {e}")
            await interaction.followup.send("❌ Error starting game. Check logs.", ephemeral=True)
        
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, row=0)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel game start."""
        # Allow any ST or Co-ST to cancel
        is_st_or_cost = getattr(self.bot, "is_storyteller", lambda m: False)(interaction.user)
        
        if not is_st_or_cost:
            await interaction.response.send_message("Only storytellers can cancel.", ephemeral=True)
            return
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(
            content="❌ Game start cancelled.",
            embed=None,
            view=self
        )
        
        self.stop()
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary, row=0)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the player list."""
        await interaction.response.defer()
        
        players, spectators, main_st, co_sts = await self.get_player_lists()
        embed = self.create_roster_embed(players, spectators, main_st, co_sts)
        
        await interaction.edit_original_response(embed=embed, view=self)


class SlashCog(commands.Cog):
    """Cog that groups slash command registration. The actual command callbacks
    delegate to helper functions exposed on the bot (to avoid circular imports).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        """Register app commands on the bot's tree when the cog is loaded."""

        # /poll
        @app_commands.command(name="poll", description="Create a timed script poll (ST/Co-ST/Admins)")
        async def poll_slash(interaction: discord.Interaction, options: str, duration: str = "5m"):
            member = interaction.guild.get_member(interaction.user.id)
            is_st = getattr(self.bot, "is_storyteller", lambda m: False)(member)
            is_admin_user = member.guild_permissions.administrator if member else False
            
            if not (is_st or is_admin_user):
                await interaction.response.send_message("⚠️ Only users with ST/Co-ST prefix or server admins can create polls. Use `*st` or `*cost` to add the prefix.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                # Create async wrapper that passes the channel
                async def get_players_with_channel(guild):
                    get_active_players = getattr(self.bot, "get_active_players")
                    return await get_active_players(guild, interaction.channel)
                
                poll_msg, unique_options, emoji_map, script_map, poll_duration = await create_poll_internal(
                    interaction.guild,
                    interaction.channel,
                    options,
                    duration,
                    member,
                    get_players_with_channel
                )
                # Schedule end
                asyncio.create_task(_end_poll(poll_duration, poll_msg, unique_options, emoji_map, script_map, interaction.user.id))
                await interaction.followup.send("✅ Poll created!", ephemeral=True)
            except ValueError as e:
                await interaction.followup.send(str(e), ephemeral=True)
            except Exception as e:
                logger.error(f"Unexpected error creating poll (slash): {e}")
                await interaction.followup.send("❌ Failed to create poll. Please check options and duration.", ephemeral=True)

        # /startgame
        @app_commands.command(name="startgame", description="Start a new game and begin tracking (Storytellers only)")
        @app_commands.describe(script="Script being played (choose from list)", custom_name="Required ONLY if you select Custom Script")
        @app_commands.choices(
            script=[
                app_commands.Choice(name="🍺 Trouble Brewing", value="Trouble Brewing"),
                app_commands.Choice(name="🪻 Sects & Violets", value="Sects & Violets"),
                app_commands.Choice(name="🌙 Bad Moon Rising", value="Bad Moon Rising"),
                app_commands.Choice(name="✨ Custom Script", value="Custom Script"),
                app_commands.Choice(name="🏠 Homebrew Script", value="Homebrew Script"),
            ]
        )
        async def startgame_slash(interaction: discord.Interaction, script: app_commands.Choice[str], custom_name: str = ""):
            member = interaction.guild.get_member(interaction.user.id)
            if not getattr(self.bot, "is_storyteller", lambda m: False)(member):
                await interaction.response.send_message("Only storytellers can start games.", ephemeral=True)
                return
            
            # Validate channel is in a BOTC category with a session
            if not interaction.channel.category:
                await interaction.response.send_message(
                    "⚠️ This command must be run in a channel within a category. Create a BOTC category first.",
                    ephemeral=True
                )
                return
            
            session_manager = getattr(self.bot, "session_manager", None)
            if session_manager:
                session = await session_manager.get_session(interaction.guild.id, interaction.channel.category.id)
                if not session:
                    await interaction.response.send_message(
                        "⚠️ This category isn't configured for BOTC yet. Run `/setbotc` to set it up.",
                        ephemeral=True
                    )
                    return
            
            # Validate custom_name requirement for Custom Script
            script_value = script.value
            if script_value == "Custom Script" and (not custom_name or not custom_name.strip()):
                await interaction.response.send_message(
                    "❌ Please provide a custom script name when using Custom Script option.",
                    ephemeral=True
                )
                return
            
            # Determine display name
            if script_value in ["Custom Script", "Homebrew Script"] and custom_name.strip():
                display_name = custom_name.strip()
            else:
                display_name = script_value
            
            # Defer the interaction
            try:
                await interaction.response.defer(ephemeral=False)
            except Exception:
                logger.debug("Could not defer startgame interaction")
            
            # Create confirmation view and get initial player lists
            view = StartGameConfirmView(self.bot, interaction.guild, script_value, display_name, member, interaction)
            
            try:
                players, spectators, main_st, co_sts = await view.get_player_lists()
                embed = view.create_roster_embed(players, spectators, main_st, co_sts)
                
                await interaction.followup.send(embed=embed, view=view)
            except Exception as e:
                logger.exception(f"Error creating start game confirmation: {e}")
                await interaction.followup.send("❌ Error preparing game start. Check logs.", ephemeral=True)

        @app_commands.command(name="endgame", description="End the current game and record the result (Storytellers only)")
        @app_commands.describe(winner="Game result: Good, Evil, or Cancel")
        @app_commands.choices(
            winner=[
                app_commands.Choice(name="Good", value="Good"),
                app_commands.Choice(name="Evil", value="Evil"),
                app_commands.Choice(name="Cancel", value="Cancel"),
            ]
        )
        async def endgame_slash(interaction: discord.Interaction, winner: app_commands.Choice[str]):
            member = interaction.guild.get_member(interaction.user.id)
            
            # Check if user is a storyteller (role or nickname-based)
            if not getattr(self.bot, "is_storyteller", lambda m: False)(member):
                await interaction.response.send_message("Only storytellers can end games.", ephemeral=True)
                return
            
            # Validate channel is in a BOTC category with a session
            if not interaction.channel.category:
                await interaction.response.send_message(
                    "⚠️ This command must be run in a channel within a category. Create a BOTC category first.",
                    ephemeral=True
                )
                return
            
            # Session-scoped validation: Check if user is ST or Co-ST for THIS session
            session_manager = getattr(self.bot, "session_manager", None)
            if session_manager and interaction.channel:
                try:
                    session = await self.bot.get_session_from_channel(interaction.channel, self.bot.session_manager)
                    if not session:
                        await interaction.response.send_message(
                            "⚠️ This category isn't configured for BOTC yet. Run `/setbotc` to set it up.",
                            ephemeral=True
                        )
                        return
                    
                    # Check if user has ST or Co-ST prefix
                    has_st_prefix = member.nick and (member.nick.startswith("(ST) ") or member.nick.startswith("(Co-ST) "))
                    
                    if not has_st_prefix:
                        await interaction.response.send_message(
                            "⚠️ You need an active Storyteller or Co-Storyteller prefix to end this game.\n"
                            "Use `*st` or `*cost` to claim your role, then try again.",
                            ephemeral=True
                        )
                        return
                    
                    # Check if this user is registered as ST for a DIFFERENT session
                    # This prevents accidentally ending the wrong session's game
                    all_sessions = await session_manager.get_all_sessions_for_guild(interaction.guild.id)
                    for other_session in all_sessions:
                        if (other_session.category_id != session.category_id and 
                            other_session.storyteller_user_id == member.id):
                            # User is ST for a different session - warn them
                            other_category = interaction.guild.get_channel(other_session.category_id)
                            category_name = other_category.name if other_category else "another session"
                            await interaction.response.send_message(
                                f"⚠️ You're registered as storyteller for **{category_name}**.\n"
                                f"Are you sure you want to end THIS session's game? If so, use `/forceendgame` as an admin.",
                                ephemeral=True
                            )
                            return
                        
                except Exception as e:
                    logger.warning(f"Session validation failed in endgame: {e}")
            
            try:
                await getattr(self.bot, "end_game_handler")(interaction, winner.value)
            except AttributeError:
                await interaction.response.send_message("Endgame handler not available.", ephemeral=True)
        
        # /forceendgame
        @app_commands.command(name="forceendgame", description="[Admin] Force end the active game in this session")
        @app_commands.describe(winner="Game result: Good, Evil, or Cancel")
        @app_commands.choices(
            winner=[
                app_commands.Choice(name="Good", value="Good"),
                app_commands.Choice(name="Evil", value="Evil"),
                app_commands.Choice(name="Cancel", value="Cancel"),
            ]
        )
        async def forceendgame_slash(interaction: discord.Interaction, winner: app_commands.Choice[str]):
            """Admin command to forcefully end a game, bypassing storyteller checks."""
            member = interaction.user
            
            # Admin check
            if not await self.bot.is_admin(member):
                await interaction.response.send_message(
                    "❌ Only server administrators can use `/forceendgame`.\n"
                    "If you're the storyteller, use `/endgame` instead.",
                    ephemeral=True
                )
                return
            
            # Verify we're in a BOTC session
            session_manager = self.bot.session_manager
            if session_manager and interaction.channel:
                try:
                    session = await self.bot.get_session_from_channel(interaction.channel, self.bot.session_manager)
                    if not session:
                        await interaction.response.send_message(
                            "⚠️ This category isn't configured for BOTC yet. No active game to end.",
                            ephemeral=True
                        )
                        return
                except Exception as e:
                    logger.warning(f"Session validation failed in forceendgame: {e}")
            
            # Call the same handler, admin bypasses all ST checks
            try:
                await getattr(self.bot, "end_game_handler")(interaction, winner.value)
            except AttributeError:
                await interaction.response.send_message("Endgame handler not available.", ephemeral=True)

        # /stats
        @app_commands.command(name="stats", description="View server game statistics")
        async def stats_slash(interaction: discord.Interaction):
            try:
                await getattr(self.bot, "stats_handler")(interaction)
            except AttributeError:
                await interaction.response.send_message("Stats handler not available.", ephemeral=True)

        # /gamehistory
        @app_commands.command(name="gamehistory", description="View recent game history")
        async def gamehistory_slash(interaction: discord.Interaction, limit: int = 10):
            try:
                await getattr(self.bot, "gamehistory_handler")(interaction, limit)
            except AttributeError:
                await interaction.response.send_message("Game history handler not available.", ephemeral=True)

        # /deletegame
        @app_commands.command(name="deletegame", description="Delete a specific game from history (Admin only)")
        @app_commands.describe(game_id="Game ID to delete (see /gamehistory)")
        async def deletegame_slash(interaction: discord.Interaction, game_id: int):
            try:
                await getattr(self.bot, "deletegame_handler")(interaction, game_id)
            except AttributeError:
                await interaction.response.send_message("Deletegame handler not available.", ephemeral=True)

        # /clearhistory
        @app_commands.command(name="clearhistory", description="Delete ALL game history (Admin only)")
        async def clearhistory_slash(interaction: discord.Interaction):
            try:
                await getattr(self.bot, "clearhistory_handler")(interaction)
            except AttributeError:
                await interaction.response.send_message("Clearhistory handler not available.", ephemeral=True)
        
        # /deleteshortgames
        @app_commands.command(name="deleteshortgames", description="Delete games shorter than specified duration (Admin only)")
        @app_commands.describe(minutes="Delete games shorter than this many minutes")
        async def deleteshortgames_slash(interaction: discord.Interaction, minutes: int):
            try:
                await getattr(self.bot, "deleteshortgames_handler")(interaction, minutes)
            except AttributeError:
                await interaction.response.send_message("Deleteshortgames handler not available.", ephemeral=True)
        
        # /ststats (renamed from storytellerstats)
        @app_commands.command(name="ststats", description="View storyteller statistics (optionally for a specific user)")
        @app_commands.describe(user="User to view stats for (leave empty for all storytellers)")
        async def ststats_slash(interaction: discord.Interaction, user: discord.User = None):
            try:
                await getattr(self.bot, "storytellerstats_handler")(interaction, user)
            except AttributeError:
                await interaction.response.send_message("Storyteller stats handler not available.", ephemeral=True)
        
        # /stprofile
        @app_commands.command(name="stprofile", description="Set your storyteller profile for stat cards")
        @app_commands.describe(
            pronouns="Your pronouns (e.g., she/her, he/him, they/them)",
            custom_title="Your custom title (e.g., Gamer, Farmer, Wizard) - max 15 chars",
            color_theme="Card color theme"
        )
        @app_commands.choices(color_theme=[
            app_commands.Choice(name="Gold", value="gold"),
            app_commands.Choice(name="Silver", value="silver"),
            app_commands.Choice(name="Crimson", value="crimson"),
            app_commands.Choice(name="Emerald", value="emerald"),
            app_commands.Choice(name="Amethyst", value="amethyst"),
            app_commands.Choice(name="Sapphire", value="sapphire"),
            app_commands.Choice(name="Rose", value="rose"),
            app_commands.Choice(name="Copper", value="copper"),
            app_commands.Choice(name="Midnight", value="midnight"),
            app_commands.Choice(name="Jade", value="jade")
        ])
        async def stprofile_slash(
            interaction: discord.Interaction,
            pronouns: str = None,
            custom_title: str = None,
            color_theme: str = None
        ):
            """Set storyteller profile fields."""
            db: Database = self.bot.db
            
            # Validate at least one field provided
            if not any([pronouns, custom_title, color_theme]):
                await interaction.response.send_message(
                    "❌ Please provide at least one field to update.\n"
                    "**Available fields:** `pronouns`, `custom_title`, `color_theme`",
                    ephemeral=True
                )
                return
            
            # Validate field lengths
            if pronouns and len(pronouns) > 15:
                await interaction.response.send_message("❌ Pronouns must be 15 characters or less.", ephemeral=True)
                return
            if custom_title and len(custom_title) > 15:
                await interaction.response.send_message("❌ Custom title must be 15 characters or less.", ephemeral=True)
                return
            
            try:
                # Update profile (bot-wide)
                success = await db.set_storyteller_profile(
                    interaction.user.id,
                    pronouns,
                    custom_title,
                    color_theme.lower() if color_theme else None
                )
                
                if success:
                    # Build confirmation message
                    updates = []
                    if pronouns:
                        updates.append(f"**Pronouns:** {pronouns}")
                    if custom_title:
                        updates.append(f"**Title:** The {custom_title}")
                    if color_theme:
                        updates.append(f"**Color:** {color_theme.lower()}")
                    
                    embed = discord.Embed(
                        title="✅ Profile Updated",
                        description="\n".join(updates),
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Bot-wide profile • View your card with /ststats")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Failed to update profile.", ephemeral=True)
            except Exception as e:
                logger.error(f"Error updating storyteller profile: {e}")
                await interaction.response.send_message("❌ An error occurred. Check logs.", ephemeral=True)
        
        # /autosetup
        @app_commands.command(name="autosetup", description="Automatically create gothic-themed BOTC server structure (Admin only)")
        async def autosetup_slash(interaction: discord.Interaction):
            try:
                await getattr(self.bot, "autosetup_handler")(interaction)
            except AttributeError:
                await interaction.response.send_message("Autosetup handler not available.", ephemeral=True)
        
        # /character
        @app_commands.command(name="character", description="Look up information about a Blood on the Clocktower character")
        @app_commands.describe(name="Character name (e.g., Imp, Fortune Teller, Baron)")
        async def character_slash(interaction: discord.Interaction, name: str):
            await interaction.response.defer()
            
            try:
                char_info = await fetch_character(name)
                
                if not char_info:
                    await interaction.followup.send(
                        f"❌ Could not find character '{name}'. Check spelling or try a different name.",
                        ephemeral=True
                    )
                    return
                
                # Create view with buttons
                view = CharacterView(char_info, initial_section="summary")
                embed = view._create_embed("summary")
                
                await interaction.followup.send(embed=embed, view=view)
                
            except Exception as e:
                logger.error(f"Error in character lookup: {e}")
                await interaction.followup.send(
                    "❌ An error occurred while fetching character information. Please try again later.",
                    ephemeral=True
                )

        # /addplayer
        @app_commands.command(name="addplayer", description="Add a player to the active game (Storytellers only)")
        @app_commands.describe(player="The player to add to the game")
        async def addplayer_slash(interaction: discord.Interaction, player: discord.Member):
            member = interaction.guild.get_member(interaction.user.id)
            if not getattr(self.bot, "is_storyteller", lambda m: False)(member):
                await interaction.response.send_message("Only storytellers can add players to the game.", ephemeral=True)
                return
            
            # Session-scoped validation
            session_manager = getattr(self.bot, "session_manager", None)
            if session_manager and interaction.channel:
                try:
                    session = await self.bot.get_session_from_channel(interaction.channel, session_manager)
                    if session and session.storyteller_user_id:
                        if session.storyteller_user_id != member.id:
                            st_member = interaction.guild.get_member(session.storyteller_user_id)
                            st_name = st_member.display_name if st_member else "another storyteller"
                            await interaction.response.send_message(
                                f"❌ You're not the storyteller for this session. {st_name} is running this game.",
                                ephemeral=True
                            )
                            return
                        # Verify prefix still present
                        has_prefix = member.nick and (member.nick.startswith("(ST) ") or member.nick.startswith("(Co-ST) "))
                        
                        if not has_prefix:
                            await interaction.response.send_message(
                                "⚠️ You're registered as this session's ST, but your prefix is missing.\n"
                                "Use `*st` to re-apply the Storyteller status, then try again.",
                                ephemeral=True
                            )
                            return
                except Exception as e:
                    logger.warning(f"Session validation failed in addplayer: {e}")
            
            await interaction.response.defer(ephemeral=False)
            
            try:
                # Import database
                import botc.database as db
                
                guild_id = interaction.guild.id
                
                # Get session context from channel
                category_id = None
                if interaction.channel and interaction.channel.category:
                    category_id = interaction.channel.category.id
                elif self.bot.session_manager:
                    session = await self.bot.get_session_from_channel(interaction.channel, self.bot.session_manager)
                    if session:
                        category_id = session.category_id
                
                # Get active game
                active_game = await db.get_active_game(guild_id, category_id)
                if not active_game:
                    await interaction.followup.send("❌ No active game found. Use `/startgame` first.", ephemeral=True)
                    return
                
                # Get current players
                current_players = json.loads(active_game.get("players", "[]")) if isinstance(active_game.get("players"), str) else active_game.get("players", [])
                
                # Check if player already in game
                if player.id in current_players:
                    await interaction.followup.send(f"❌ {player.mention} is already in the game.", ephemeral=True)
                    return
                
                # Add player
                current_players.append(player.id)
                success = await db.update_game_players(guild_id, current_players, category_id)
                
                if success:
                    embed = discord.Embed(
                        title="✅ Player Added",
                        description=f"{player.mention} has been added to the game.",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Total Players", value=str(len(current_players)), inline=False)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Failed to update game. Please try again.", ephemeral=True)
                    
            except Exception as e:
                logger.error(f"Error in addplayer: {e}")
                await interaction.followup.send("❌ An error occurred. Check logs.", ephemeral=True)

        # /removeplayer
        @app_commands.command(name="removeplayer", description="Remove a player from the active game (Storytellers only)")
        @app_commands.describe(player="The player to remove from the game")
        async def removeplayer_slash(interaction: discord.Interaction, player: discord.Member):
            member = interaction.guild.get_member(interaction.user.id)
            if not getattr(self.bot, "is_storyteller", lambda m: False)(member):
                await interaction.response.send_message("Only storytellers can remove players from the game.", ephemeral=True)
                return
            
            # Session-scoped validation
            session_manager = getattr(self.bot, "session_manager", None)
            if session_manager and interaction.channel:
                try:
                    session = await self.bot.get_session_from_channel(interaction.channel, session_manager)
                    if session and session.storyteller_user_id:
                        if session.storyteller_user_id != member.id:
                            st_member = interaction.guild.get_member(session.storyteller_user_id)
                            st_name = st_member.display_name if st_member else "another storyteller"
                            await interaction.response.send_message(
                                f"❌ You're not the storyteller for this session. {st_name} is running this game.",
                                ephemeral=True
                            )
                            return
                        # Verify prefix still present
                        has_prefix = member.nick and (member.nick.startswith("(ST) ") or member.nick.startswith("(Co-ST) "))
                        
                        if not has_prefix:
                            await interaction.response.send_message(
                                "⚠️ You're registered as this session's ST, but your prefix is missing.\n"
                                "Use `*st` to re-apply the Storyteller status, then try again.",
                                ephemeral=True
                            )
                            return
                except Exception as e:
                    logger.warning(f"Session validation failed in removeplayer: {e}")
            
            await interaction.response.defer(ephemeral=False)
            
            try:
                # Import database
                import botc.database as db
                
                guild_id = interaction.guild.id
                
                # Get session context from channel
                category_id = None
                if interaction.channel and interaction.channel.category:
                    category_id = interaction.channel.category.id
                elif self.bot.session_manager:
                    session = await self.bot.get_session_from_channel(interaction.channel, self.bot.session_manager)
                    if session:
                        category_id = session.category_id
                
                # Get active game
                active_game = await db.get_active_game(guild_id, category_id)
                if not active_game:
                    await interaction.followup.send("❌ No active game found. Use `/startgame` first.", ephemeral=True)
                    return
                
                # Get current players
                current_players = json.loads(active_game.get("players", "[]")) if isinstance(active_game.get("players"), str) else active_game.get("players", [])
                
                # Check if player in game
                if player.id not in current_players:
                    await interaction.followup.send(f"❌ {player.mention} is not in the game.", ephemeral=True)
                    return
                
                # Remove player
                current_players.remove(player.id)
                success = await db.update_game_players(guild_id, current_players, category_id)
                
                if success:
                    embed = discord.Embed(
                        title="✅ Player Removed",
                        description=f"{player.mention} has been removed from the game.",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Total Players", value=str(len(current_players)), inline=False)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ Failed to update game. Please try again.", ephemeral=True)
                    
            except Exception as e:
                logger.error(f"Error in removeplayer: {e}")
                await interaction.followup.send("❌ An error occurred. Check logs.", ephemeral=True)

        # --- Admin configuration commands ---
        @app_commands.command(name="settown", description="[Admin] Set the Town Square voice channel for this session")
        @app_commands.describe(channel="The voice channel to use as Town Square")
        async def settown_slash(interaction: discord.Interaction, channel: discord.VoiceChannel):
            """Set the Town Square voice channel for this session."""
            if not await self.bot.is_admin(interaction.user):
                await interaction.response.send_message("❌ Only administrators can set the Town Square.", ephemeral=True)
                return
            
            session_manager = getattr(self.bot, "session_manager", None)
            if not session_manager:
                await interaction.response.send_message("❌ Session manager not available.", ephemeral=True)
                return
            
            # Get existing session from channel context - do not auto-create
            session = await session_manager.get_session_from_channel(interaction.channel, interaction.guild)
            if not session:
                await interaction.response.send_message(
                    "⚠️ No session found in this category. Run `/setbotc` first to create a session.",
                    ephemeral=True
                )
                return
            
            # Update session's town square
            session.destination_channel_id = channel.id
            await session_manager.update_session(session)
            
            await interaction.response.send_message(f"✅ Town Square for this session set to {channel.mention}", ephemeral=True)

        @app_commands.command(name="setbotc", description="[Admin] Set the BOTC category for the server")
        @app_commands.describe(category="The category name or ID")
        async def setbotc_slash(interaction: discord.Interaction, category: str):
            """Set the BOTC category for the server."""
            if not await self.bot.is_admin(interaction.user):
                await interaction.response.send_message("❌ Only administrators can set the BOTC category.", ephemeral=True)
                return
            
            guild = interaction.guild
            found_category = None
            
            # Try to match by ID first
            if category.isdigit():
                cat_id = int(category)
                found_category = next((c for c in guild.categories if c.id == cat_id), None)
            else:
                # Match by name (exact first, then partial)
                name_lower = category.lower()
                found_category = next((c for c in guild.categories if c.name.lower() == name_lower), None)
                if not found_category:
                    found_category = next((c for c in guild.categories if name_lower in c.name.lower()), None)
            
            if not found_category:
                await interaction.response.send_message(
                    "❌ Category not found. Make sure the category name or ID is correct and the bot has permission to view it.",
                    ephemeral=True
                )
                return
            
            session_manager = getattr(self.bot, "session_manager", None)
            if not session_manager:
                await interaction.response.send_message("❌ Session manager not available.", ephemeral=True)
                return
            
            # Snapshot voice channel caps from this category
            vc_caps = {}
            for vc in found_category.voice_channels:
                if vc.user_limit > 0:  # Only store capped channels
                    vc_caps[vc.id] = vc.user_limit
            
            # Create or update session for this category
            session = await session_manager.get_session(guild.id, found_category.id)
            if not session:
                session = await session_manager.create_session(
                    guild.id, 
                    found_category.id,
                    vc_caps=vc_caps
                )
                code_msg = f"\n**Session Code:** `{session.session_code}`\n_Use this code to link grimoire on website_"
            else:
                # Update existing session with new VC caps snapshot (preserve existing code)
                session.vc_caps = vc_caps
                await session_manager.update_session(session)
                code_msg = f"\n**Session Code:** `{session.session_code}`" if session.session_code else ""
            
            cap_msg = f" (snapshotted {len(vc_caps)} capped voice channels)" if vc_caps else ""
            await interaction.response.send_message(
                f"✅ BOTC category set to **{found_category.name}**{cap_msg}{code_msg}\n"
                f"Voice channel caps have been saved. The bot will now manage these caps when privileged users join/leave.",
                ephemeral=True
            )

        # /setannounce - REMOVED (deprecated feature)

        @app_commands.command(name="setexception", description="[Admin] Set the exception/private ST channel for this session")
        @app_commands.describe(channel="The voice channel for private ST discussions (optional)")
        async def setexception_slash(interaction: discord.Interaction, channel: discord.VoiceChannel = None):
            """Set or clear the exception channel for this session."""
            if not await self.bot.is_admin(interaction.user):
                await interaction.response.send_message("❌ Only administrators can set the exception channel.", ephemeral=True)
                return
            
            session_manager = getattr(self.bot, "session_manager", None)
            if not session_manager:
                await interaction.response.send_message("❌ Session manager not available.", ephemeral=True)
                return
            
            # Get existing session from channel context - do not auto-create
            session = await session_manager.get_session_from_channel(interaction.channel, interaction.guild)
            if not session:
                await interaction.response.send_message(
                    "⚠️ No session found in this category. Run `/setbotc` first to create a session.",
                    ephemeral=True
                )
                return
            
            # If no channel provided, clear the exception channel
            if channel is None:
                session.exception_channel_id = None
                await session_manager.update_session(session)
                await interaction.response.send_message("✅ Exception channel cleared for this session.", ephemeral=True)
                return
            
            # Update session's exception channel
            session.exception_channel_id = channel.id
            await session_manager.update_session(session)
            
            await interaction.response.send_message(f"✅ Exception channel for this session set to {channel.mention}", ephemeral=True)

        @app_commands.command(name="sessions", description="[Admin] List all BOTC sessions in this server")
        async def sessions_slash(interaction: discord.Interaction):
            """List all game sessions in the server."""
            if not await self.bot.is_admin(interaction.user):
                await interaction.response.send_message("❌ Only administrators can view sessions.", ephemeral=True)
                return
            
            session_manager = getattr(self.bot, "session_manager", None)
            if not session_manager:
                await interaction.response.send_message("❌ Session manager not available.", ephemeral=True)
                return
            
            db = getattr(self.bot, "db", None)
            if not db:
                await interaction.response.send_message("❌ Database not available.", ephemeral=True)
                return
            
            guild_id = interaction.guild.id
            sessions = await session_manager.get_all_sessions_for_guild(guild_id)
            
            if not sessions:
                await interaction.response.send_message("No sessions found. Create one with `/setbotc <category>`", ephemeral=True)
                return
            
            # Filter out sessions where category no longer exists
            valid_sessions = []
            for session in sessions:
                category = interaction.guild.get_channel(session.category_id)
                if category:
                    valid_sessions.append(session)
            
            if not valid_sessions:
                await interaction.response.send_message("No valid sessions found (categories may have been deleted).", ephemeral=True)
                return
            
            # Sort by last_active (most recent first)
            valid_sessions.sort(key=lambda s: s.last_active or 0, reverse=True)
            
            from botc.constants import VERSION
            
            embed = discord.Embed(
                title="🎭 BOTC Sessions",
                description=f"Active sessions in **{interaction.guild.name}**\n\nUse `/sessions view <id>` for details or `/deletesession` to remove a session.",
                color=discord.Color.purple()
            )
            
            for idx, session in enumerate(valid_sessions, 1):
                category = interaction.guild.get_channel(session.category_id)
                category_name = category.name if category else f"Unknown"
                
                # Get active game info if exists
                status_emoji = "🎲"
                game_info = "No active game"
                if session.active_game_id:
                    active_game = await db.get_active_game(guild_id, session.category_id)
                    if active_game:
                        status_emoji = "🔴"
                        game_info = f"{active_game['script']} ({active_game['player_count']} players)"
                
                # Build field value
                field_value = f"{status_emoji} **{game_info}**\n"
                
                # Show session code prominently
                if session.session_code:
                    field_value += f"🔑 Code: `{session.session_code}`\n"
                
                field_value += f"📁 Category ID: `{session.category_id}`\n"
                
                if session.destination_channel_id:
                    dest_channel = interaction.guild.get_channel(session.destination_channel_id)
                    if dest_channel:
                        field_value += f"🏛️ Town Square: {dest_channel.mention}\n"
                
                if session.grimoire_link:
                    field_value += f"📜 Grimoire: {session.grimoire_link}\n"
                
                embed.add_field(
                    name=f"{idx}. {category_name}",
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text=f"💡 Use category IDs with /sessions view or /deletesession | v{VERSION}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        # /deletesession
        @app_commands.command(name="deletesession", description="Delete a BOTC session (Admins only)")
        @app_commands.describe(category_id="The category ID of the session to delete (from /sessions)")
        async def deletesession_slash(interaction: discord.Interaction, category_id: str):
            """Delete a BOTC session configuration."""
            # Admin check
            if not await self.bot.is_admin(interaction.user):
                await interaction.response.send_message("Only administrators can delete sessions.", ephemeral=True)
                return

            # Convert string to int (Discord IDs exceed JavaScript's safe integer limit)
            if not category_id.isdigit():
                await interaction.response.send_message("❌ Invalid category ID. Please provide a numeric ID.", ephemeral=True)
                return
            cat_id = int(category_id)
            guild_id = interaction.guild.id
            session_manager = getattr(self.bot, "session_manager", None)
            if not session_manager:
                await interaction.response.send_message("Session manager not available.", ephemeral=True)
                return
            session = await session_manager.get_session(guild_id, cat_id)
            if not session:
                await interaction.response.send_message(f"❌ No session found with ID `{cat_id}`.", ephemeral=True)
                return
            category = interaction.guild.get_channel(cat_id)
            category_name = category.name if category else f"Category {cat_id}"
            db: Database = self.bot.db
            active_game = await db.get_active_game(guild_id, cat_id)
            warning = ""
            if active_game:
                warning = "\n⚠️ **Warning:** This session has an active game that will be ended."
            success = await session_manager.delete_session(guild_id, cat_id)
            if success:
                embed = discord.Embed(
                    title="✅ Session Deleted",
                    description=f"Removed session for **{category_name}**{warning}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Category ID", value=f"`{cat_id}`", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Failed to delete session `{cat_id}`.", ephemeral=True)


        # /language
        @app_commands.command(name="language", description="Change the bot's language for this server (Admins only)")
        @app_commands.describe(language="Select a language")
        @app_commands.choices(language=[
            app_commands.Choice(name="🇺🇸 English", value="en"),
            app_commands.Choice(name="🇪🇸 Español (Spanish)", value="es"),
            app_commands.Choice(name="🇵🇱 Polski (Polish)", value="pl"),
            app_commands.Choice(name="🇷🇺 Русский (Russian)", value="ru"),
        ])
        async def language_slash(interaction: discord.Interaction, language: str):
            """Set the bot's language for this server."""
            # Admin check
            if not await self.bot.is_admin(interaction.user):
                await interaction.response.send_message("Only administrators can change the bot's language.", ephemeral=True)
                return
            
            guild_id = interaction.guild.id
            db: Database = self.bot.db
            translator = get_translator()
            
            # Update database
            try:
                await db.set_guild_language(guild_id, language)
                translator.set_guild_language(guild_id, language)
                
                language_names = {
                    'en': '🇺🇸 English',
                    'es': '🇪🇸 Español',
                    'pl': '🇵🇱 Polski',
                    'ru': '🇷🇺 Русский',
                }
                
                embed = discord.Embed(
                    title="✅ Language Changed",
                    description=f"Bot language set to **{language_names.get(language, language)}**",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)
            except Exception as e:
                logger.error(f"Failed to set language: {e}")
                await interaction.response.send_message("❌ Failed to change language. Check logs.", ephemeral=True)

        # /setadmin
        @app_commands.command(name="setadmin", description="Set a role as an admin role for bot commands (Owner only)")
        @app_commands.describe(
            role="The role to grant admin privileges",
            action="Add or remove the role from admin list"
        )
        @app_commands.choices(action=[
            app_commands.Choice(name="Add role as admin", value="add"),
            app_commands.Choice(name="Remove role from admin", value="remove"),
        ])
        async def setadmin_slash(interaction: discord.Interaction, role: discord.Role, action: str):
            """Set or remove a role as an admin role for bot commands."""
            # Only server administrators can manage admin roles
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Only server administrators can manage admin roles.",
                    ephemeral=True
                )
                return
            
            guild_id = interaction.guild.id
            role_id = role.id
            db: Database = self.bot.db
            
            try:
                if action == "add":
                    # Add the role as an admin role
                    success = await db.add_admin_role(guild_id, role_id)
                    if success:
                        embed = discord.Embed(
                            title="✅ Admin Role Added",
                            description=f"Role {role.mention} now has admin privileges for bot commands.",
                            color=discord.Color.green()
                        )
                        embed.add_field(
                            name="ℹ️ Info",
                            value="Members with this role can now use admin-only commands like `/setbotc`, `/deletesession`, etc.",
                            inline=False
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=False)
                    else:
                        await interaction.response.send_message(
                            f"⚠️ Role {role.mention} is already an admin role.",
                            ephemeral=True
                        )
                else:  # remove
                    # Remove the role from admin roles
                    success = await db.remove_admin_role(guild_id, role_id)
                    if success:
                        embed = discord.Embed(
                            title="✅ Admin Role Removed",
                            description=f"Role {role.mention} no longer has admin privileges for bot commands.",
                            color=discord.Color.orange()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=False)
                    else:
                        await interaction.response.send_message(
                            f"⚠️ Role {role.mention} was not an admin role.",
                            ephemeral=True
                        )
            except Exception as e:
                logger.error(f"Failed to manage admin role: {e}")
                await interaction.response.send_message(
                    "❌ Failed to update admin role. Check logs.",
                    ephemeral=True
                )

        @app_commands.command(name="exportmygames", description="Export your complete game history as CSV")
        @app_commands.describe(limit="Optional: limit to most recent N games (default: all games)")
        async def exportmygames_slash(interaction: discord.Interaction, limit: int = None):
            """Export all games for the requesting user."""
            await interaction.response.defer(ephemeral=True)
            
            try:
                from botc.csv_export import generate_player_csv
                import discord
                
                db = getattr(self.bot, "db", None)
                if not db:
                    await interaction.followup.send("❌ Database not available.", ephemeral=True)
                    return
                
                player_id = interaction.user.id
                csv_buffer = await generate_player_csv(db, player_id, limit=limit)
                
                if not csv_buffer.getvalue().strip().split('\n')[1:]:  # Only header, no data
                    await interaction.followup.send("❌ No games found in your history.", ephemeral=True)
                    return
                
                # Create file and send
                game_count = len(csv_buffer.getvalue().split('\n')) - 1
                filename = f"botc_games_{interaction.user.name}.csv"
                file = discord.File(fp=csv_buffer, filename=filename)
                
                limit_msg = f" (most recent {limit})" if limit else ""
                await interaction.followup.send(
                    f"📊 Here's your game history{limit_msg}! ({game_count} games)",
                    file=file,
                    ephemeral=True
                )
                
            except Exception as e:
                logger.exception("Error exporting games")
                await interaction.followup.send(f"❌ Failed to export games: {e}", ephemeral=True)
        
        @app_commands.command(name="exportgame", description="Export a single game as CSV")
        @app_commands.describe(game_id="The ID of the game to export")
        async def exportgame_slash(interaction: discord.Interaction, game_id: int):
            """Export a single game for the requesting user."""
            await interaction.response.defer(ephemeral=True)
            
            try:
                from botc.csv_export import generate_player_csv
                import discord
                
                db = getattr(self.bot, "db", None)
                if not db:
                    await interaction.followup.send("❌ Database not available.", ephemeral=True)
                    return
                
                # Check if game exists first
                async with db.pool.acquire() as conn:
                    game_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM games WHERE game_id = $1 AND guild_id = $2)",
                        game_id, interaction.guild_id
                    )
                    
                    if not game_exists:
                        await interaction.followup.send(
                            f"❌ Game #{game_id} not found in this server.",
                            ephemeral=True
                        )
                        return
                
                player_id = interaction.user.id
                csv_buffer = await generate_player_csv(db, player_id, game_id)
                
                if not csv_buffer.getvalue().strip().split('\n')[1:]:  # Only header, no data
                    await interaction.followup.send(
                        f"❌ You weren't a player in game #{game_id}.",
                        ephemeral=True
                    )
                    return
                
                # Create file and send
                filename = f"botc_game_{game_id}_{interaction.user.name}.csv"
                file = discord.File(fp=csv_buffer, filename=filename)
                
                await interaction.followup.send(
                    f"📊 Here's your export for game #{game_id}!",
                    file=file,
                    ephemeral=True
                )
                
            except Exception as e:
                logger.exception("Error exporting game")
                await interaction.followup.send(f"❌ Failed to export game: {e}", ephemeral=True)
        
        @app_commands.command(name="exportallplayers", description="Export CSVs for all players in a game (Storyteller only)")
        @app_commands.describe(game_id="The ID of the game to export")
        async def exportallplayers_slash(interaction: discord.Interaction, game_id: int):
            """Export individual CSVs for all players in a game (ST only)."""
            await interaction.response.defer(ephemeral=True)
            
            try:
                from botc.csv_export import generate_all_players_csvs
                import discord
                
                # Check if user is storyteller
                if not getattr(self.bot, "is_storyteller", lambda m: False)(interaction.user):
                    await interaction.followup.send("❌ Only storytellers can export all players.", ephemeral=True)
                    return
                
                db = getattr(self.bot, "db", None)
                if not db:
                    await interaction.followup.send("❌ Database not available.", ephemeral=True)
                    return
                
                # Verify game exists
                async with db.pool.acquire() as conn:
                    game = await conn.fetchrow("SELECT game_id, storyteller_id FROM games WHERE game_id = $1", game_id)
                    if not game:
                        await interaction.followup.send(f"❌ Game #{game_id} not found.", ephemeral=True)
                        return
                
                # Generate CSVs for all players
                exports = await generate_all_players_csvs(db, game_id)
                
                if not exports:
                    await interaction.followup.send(f"❌ No players found in game #{game_id}.", ephemeral=True)
                    return
                
                # Send all CSVs as attachments
                files = []
                for discord_id, csv_buffer in exports.items():
                    member = interaction.guild.get_member(discord_id)
                    username = member.name if member else str(discord_id)
                    filename = f"botc_game_{game_id}_{username}.csv"
                    files.append(discord.File(fp=csv_buffer, filename=filename))
                
                await interaction.followup.send(
                    f"📊 Here are CSV exports for all {len(exports)} players in game #{game_id}!",
                    files=files,
                    ephemeral=True
                )
                
            except Exception as e:
                logger.exception("Error exporting all players")
                await interaction.followup.send(f"❌ Failed to export: {e}", ephemeral=True)

        # Add all created commands to the bot.tree
        for cmd in [
            poll_slash,
            startgame_slash,
            endgame_slash,
            forceendgame_slash,
            stats_slash,
            gamehistory_slash,
            deletegame_slash,
            clearhistory_slash,
            deleteshortgames_slash,
            ststats_slash,
            stprofile_slash,
            autosetup_slash,
            character_slash,
            addplayer_slash,
            removeplayer_slash,
            settown_slash,
            setbotc_slash,
            setexception_slash,
            sessions_slash,
            deletesession_slash,
            language_slash,
            setadmin_slash,
            exportmygames_slash,
            exportgame_slash,
            exportallplayers_slash,
        ]:
            try:
                self.bot.tree.add_command(cmd)
            except Exception:
                # If the command already exists, skip
                logger.debug(f"Command {getattr(cmd, 'name', repr(cmd))} already added or failed to add")

        logger.info("Registered slash commands via cogs.slash SlashCog.cog_load")


async def setup(bot: commands.Bot) -> None:
    """Add the SlashCog to the bot. Commands are registered when the cog loads."""
    await bot.add_cog(SlashCog(bot))