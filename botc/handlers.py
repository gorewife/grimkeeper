"""Business logic handlers for slash commands.

These handlers are called by the SlashCog but contain all the business logic,
keeping the cog focused on Discord interaction handling.
"""
from __future__ import annotations

import time
import random
import json
import logging
from typing import TYPE_CHECKING

import discord

from botc.constants import (
    VERSION,
    PREFIX_ST,
    PREFIX_COST,
    EMOJI_TOWN_SQUARE,
    EMOJI_SCRIPT,
    EMOJI_PLAYERS,
    EMOJI_CANDLE,
    EMOJI_GOOD_WIN,
    EMOJI_EVIL_WIN,
    EMOJI_SWORD,
    EMOJI_CLOCK,
    EMOJI_GOOD,
    EMOJI_EVIL,
    ICON_GOOD,
    ICON_EVIL,
    DELETE_DELAY_LONG,
    DELETE_DELAY_ERROR,
    COMMAND_COOLDOWN_LONG,
)
from botc.discord_utils import safe_send_interaction
from botc.exceptions import DatabaseError

if TYPE_CHECKING:
    from botc.database import Database

from botc.utils import strip_st_prefix, add_script_emoji

logger = logging.getLogger('botc_bot')


async def start_game_handler(
    interaction: discord.Interaction,
    bot,
    db: 'Database',
    script: object,
    custom_name: str = ""
) -> None:
    """Handle /startgame command.
    
    Args:
        interaction: Discord interaction
        bot: Bot instance (for helper functions)
        db: Database instance
        script: Script choice from slash command
        custom_name: Custom script name if applicable
    """
    try:
        guild = interaction.guild
        member = interaction.user
        
        # Get script value
        script_value = script.value if hasattr(script, "value") else str(script)
        
        # Validate custom_name requirement for Custom Script
        if script_value == "Custom Script" and not custom_name.strip():
            await safe_send_interaction(
                interaction,
                "❌ Please provide a custom script name when using Custom Script option.",
                ephemeral=True
            )
            return
        
        # Determine display name
        if script_value in ["Custom Script", "Homebrew Script"] and custom_name.strip():
            display_name = custom_name.strip()
        else:
            display_name = script_value
        
        guild_id = guild.id
        
        # Get session context from the channel where command was run
        botc_category = None
        if interaction.channel and interaction.channel.category:
            # Command run from within a category - use that category
            botc_category = interaction.channel.category
        else:
            # Command run from outside a category - try to get default BOTC category
            guild_config = await db.get_guild(guild_id)
            if guild_config and guild_config.get("botc_category_id"):
                botc_category = await bot.get_botc_category(guild, bot.db)
        
        if not botc_category:
            await safe_send_interaction(
                interaction,
                "❌ Cannot determine which category to start game in.\n"
                "Either run this command from a text channel inside your BOTC category, "
                "or have an admin create a session with `/setbotc <category>` or `/autosetup`.",
                ephemeral=True
            )
            return
        
        # Collect current players
        players = []
        player_ids = []
        main_st = None
        co_sts = []
        
        for vc in botc_category.voice_channels:
            for vc_member in vc.members:
                if vc_member.bot:
                    continue
                name = vc_member.nick or vc_member.display_name or ""
                base_name, is_player = bot.get_player_role(vc_member)
                
                if name.startswith(PREFIX_ST):
                    if not main_st:
                        main_st = vc_member
                elif name.startswith(PREFIX_COST):
                    co_sts.append(vc_member)
                elif is_player:
                    players.append((name, base_name))
                    player_ids.append(vc_member.id)
        
        # Require main ST
        if not main_st:
            await safe_send_interaction(
                interaction,
                "❌ No main Storyteller found in voice channels.\n"
                "Someone must have the `(ST)` prefix (use `*st` command) before starting a game.\n"
                "Co-Storytellers `(Co-ST)` alone are not enough - you need a main ST.",
                ephemeral=True
            )
            return
        
        # Update snapshot
        snapshot_key = (guild_id, botc_category.id) if botc_category else (guild_id, None)
        current_player_ids = set(player_ids)
        bot.last_player_snapshots[snapshot_key] = current_player_ids
        
        if not player_ids:
            await safe_send_interaction(
                interaction,
                "❌ No players found in BOTC category. Make sure players are in voice channels.",
                ephemeral=True
            )
            return
        
        # Check if there's already an active game in this category
        existing_game = await db.get_active_game(guild_id, botc_category.id if botc_category else None)
        if existing_game:
            # Calculate how long the game has been running
            current_time = time.time()
            start_time = existing_game.get('start_time', current_time)
            duration_hours = (current_time - start_time) / 3600
            
            existing_script = existing_game.get('script', 'Unknown')
            existing_st_id = existing_game.get('storyteller_id')
            
            error_msg = f"❌ **A game is already in progress in this category!**\n\n"
            error_msg += f"**Script:** {existing_script}\n"
            error_msg += f"**Duration:** {duration_hours:.1f} hours\n"
            
            if existing_st_id:
                st_member = guild.get_member(existing_st_id)
                if st_member:
                    error_msg += f"**Started by:** {st_member.mention}\n"
            
            error_msg += f"\nPlease use `/endgame` to finish the current game before starting a new one."
            
            await safe_send_interaction(
                interaction,
                error_msg,
                ephemeral=True
            )
            return
        
        # Record game
        storyteller_id = main_st.id
        
        await db.start_game(
            guild_id=guild_id,
            script=script_value,
            custom_name=custom_name.strip() if custom_name else "",
            start_time=time.time(),
            players=player_ids,
            storyteller_id=storyteller_id,
            category_id=botc_category.id if botc_category else None
        )
        
        # Create or update session
        session_manager = bot.session_manager
        if session_manager and botc_category:
            try:
                # Invalidate cache first to ensure we get fresh data
                session_manager.invalidate_cache(guild_id=guild_id, category_id=botc_category.id)
                
                active_game = await db.get_active_game(guild_id, botc_category.id)
                game_id = active_game.get("game_id") if active_game else None
                
                existing_session = await session_manager.get_session(guild_id, botc_category.id)
                if existing_session:
                    existing_session.active_game_id = game_id
                    existing_session.last_active = time.time()
                    existing_session.storyteller_user_id = storyteller_id
                    await session_manager.update_session(existing_session)
                    logger.info(f"Session updated for guild {guild_id}, category {botc_category.id}")
                else:
                    logger.warning(f"No session found for guild {guild_id}, category {botc_category.id}. Game started but session not linked.")
            except Exception as e:
                logger.error(f"Failed to create/update session: {e}")
        
        # Create announcement embed
        st_name = strip_st_prefix(main_st.display_name)
        embed = discord.Embed(
            title=f"{EMOJI_TOWN_SQUARE} A New Tale Begins",
            description=f"The grimoire opens as shadows gather in the town square...",
            color=discord.Color.dark_gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=f"Storyteller: {st_name}", icon_url=main_st.display_avatar.url)
        
        embed.add_field(
            name=f"**{EMOJI_SCRIPT} Script**",
            value=f"{add_script_emoji(display_name)}",
            inline=True
        )
        
        player_display_names = [display_name for (display_name, base_name) in players]
        
        embed.add_field(
            name=f"**{EMOJI_PLAYERS} Players**",
            value=f"{len(player_display_names)}",
            inline=True
        )
        
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        if co_sts:
            co_st_names = [strip_st_prefix(co.display_name) for co in co_sts]
            embed.add_field(
                name="🎭 Co-Storyteller(s)",
                value=", ".join(co_st_names),
                inline=False
            )
        
        if len(player_display_names) <= 25:
            players_text = ", ".join(player_display_names)
        else:
            players_text = ", ".join(player_display_names[:25]) + f"\n*...and {len(player_display_names) - 25} more*"
        
        embed.add_field(
            name=f"{EMOJI_CANDLE} Gathered in the Square",
            value=players_text,
            inline=False
        )
        
        # Add session code if available
        if session_manager and botc_category:
            session = await session_manager.get_session(guild_id, botc_category.id)
            if session and session.session_code:
                embed.add_field(
                    name="🔗 Session Code",
                    value=f"`{session.session_code}` - Use this code to link stats on grim.hystericca.dev",
                    inline=False
                )
        
        embed.set_footer(text=f"Grimkeeper v{VERSION} • May fate be kind...")
        
        # Return the embed so it can be sent to the channel where command was used
        # (Don't send to announcement channel - that would be duplicate)
        return embed
                        
    except DatabaseError as e:
        logger.error(f"Database error in start_game_handler: {e}")
        await safe_send_interaction(
            interaction,
            "❌ Database error starting game. Please try again.",
            ephemeral=True
        )
    except Exception as e:
        logger.exception(f"Unexpected error in start_game_handler: {e}")
        await safe_send_interaction(
            interaction,
            "❌ Failed to start game. See logs.",
            ephemeral=True
        )


async def end_game_handler(
    interaction: discord.Interaction,
    bot,
    db: 'Database',
    winner: str
) -> None:
    """Handle /endgame command.
    
    Args:
        interaction: Discord interaction
        bot: Bot instance
        db: Database instance
        winner: 'Good', 'Evil', or 'Cancel'
    """
    good_win_messages = [
        "The last whispers of the Demon's manipulation fade away as the sun rises once more. Truth claims its victory over lies and deceit.",
        "Free from evil, dawn brings justice, and with it comes the end of the Demon's grasp over the village.",
        "Through unwavering resolve, the townsfolk expose their enemies in the dark. The Demon is cast down, and the village reclaims its peace.",
        "Good has prevailed! The evil threat is vanquished, and your town lives to see another sunrise.",
        "As dawn breaks, the final whispers of evil are snuffed out. The townsfolk stand victorious. Bruised, battered, but unbroken.",
        "Good wins! Turns out teamwork, blind panic, and arguing loudly really does defeat demons.",
        "The final vote seals the fate of evil. With the demon gone, the village can at last breathe freely. Good triumphs!",
        "Against all logic, accusations, and five days of utter nonsense, the good team somehow pulls it off. Evil is dead. Enjoy the bragging rights."
    ]
    evil_win_messages = [
        "With the final flicker of hope being extinguished at last, evil tightens its grip. The town's final breath belongs to the Demon.",
        "As the last ounce of good disappears, silence settles over the cobblestone. The Demon's victory is absolute, and the night belongs to evil.",
        "The final stand of the good team proves fruitless. In the silence that follows the death of the townsfolk, evil's laughter fills the square.",
        "Night falls forever. With the final shred of hope extinguished, evil claims the town.",
        "The demon's plan unfolds flawlessly. As the last good soul falls, darkness tightens its grip. Evil triumphs.",
        "Evil wins! Turns out lying through your teeth does pay off.",
        "As dawn breaks, the town falls silent. The Demon's plot is complete, its minions triumphant. With the good dead or deceived beyond recovery, evil claims the final victory in the town square.",
        "After days of arguing, tunneling, and trusting exactly the wrong people, the town hands victory to evil on a silver platter."
    ]
    
    try:
        guild = interaction.guild
        member = guild.get_member(interaction.user.id) if guild else None
        
        guild_id = guild.id
        
        # Get session context
        category_id = None
        if bot.session_manager and interaction.channel:
            session = await bot.get_session_from_channel(interaction.channel, bot.session_manager)
            if session:
                category_id = session.category_id
        
        # Load active game
        game = await db.get_active_game(guild_id, category_id)
        if not game:
            await safe_send_interaction(
                interaction,
                "No active game found for this server. Did you use /startgame?",
                ephemeral=True
            )
            return
        
        # Check permission: must be the storyteller who started the game OR have storyteller role
        game_storyteller_id = game.get('storyteller_id')
        is_game_storyteller = (game_storyteller_id == interaction.user.id)
        has_st_role = bot.is_storyteller(member)
        
        if not (is_game_storyteller or has_st_role):
            await safe_send_interaction(
                interaction,
                "Only the storyteller who started this game can end it.",
                ephemeral=True
            )
            return
        
        valid_winners = {"Good", "Evil", "Cancel"}
        if winner not in valid_winners:
            await safe_send_interaction(
                interaction,
                "Invalid winner. Must be one of: Good, Evil, Cancel.",
                ephemeral=True
            )
            return
        
        if winner == "Cancel":
            await db.cancel_game(guild_id, category_id)
            
            # Invalidate session cache to ensure fresh data on next command
            if bot.session_manager and category_id:
                bot.session_manager.invalidate_cache(guild_id=guild_id, category_id=category_id)
            
            await safe_send_interaction(
                interaction,
                "\n❌ **Game Cancelled**\n"
                "This session was **not recorded** in the game history.\n"
                "If this was a mistake, you can start a new game with `/startgame`.",
                ephemeral=True
            )
            return
        
        # End game and record
        end_time = time.time()
        await db.end_game(guild_id=guild_id, end_time=end_time, winner=winner, category_id=category_id)
        
        # Invalidate session cache to ensure fresh data on next command
        if bot.session_manager and category_id:
            bot.session_manager.invalidate_cache(guild_id=guild_id, category_id=category_id)
        
        # Clear reminder tracking for this game (if event handler exists)
        event_handler = interaction.client.get_cog('EventHandlers')
        if event_handler and hasattr(event_handler, 'reminded_games'):
            game_key = (guild_id, category_id)
            event_handler.reminded_games.discard(game_key)
        
        # Build display record
        record = {
            "script": game["script"],
            "custom_name": game.get("custom_name", ""),
            "start_time": game["start_time"],
            "end_time": end_time,
            "players": game["players"],
            "winner": winner
        }
        
        # Parse players
        players_data = record['players']
        if isinstance(players_data, str):
            try:
                players_list = json.loads(players_data)
            except:
                players_list = []
        elif isinstance(players_data, list):
            players_list = players_data
        else:
            players_list = []
        
        player_count = len(players_list)
        
        # Calculate duration
        duration_seconds = int(end_time - game["start_time"])
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if hours > 0:
            duration_str = f"{hours}h {minutes}m"
        else:
            duration_str = f"{minutes}m"
        
        # Get script display name
        if record['script'] in ["Custom Script", "Homebrew Script"]:
            script_name = "Custom Script"
        else:
            script_name = record['script']
        script_name = add_script_emoji(script_name)
        winner_str = record['winner']
        
        # Create embed
        st_name = strip_st_prefix(member.display_name)
        if winner_str == "Good":
            embed = discord.Embed(
                title=f"{EMOJI_GOOD_WIN} The Dawn Breaks",
                description=f"*{random.choice(good_win_messages)}*",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=st_name, icon_url=member.display_avatar.url)
            embed.set_thumbnail(url=ICON_GOOD)
            embed.add_field(name=f"**{EMOJI_SWORD} Victor**", value="Good", inline=True)
        elif winner_str == "Evil":
            embed = discord.Embed(
                title=f"{EMOJI_EVIL_WIN} Eternal Night Falls",
                description=f"*{random.choice(evil_win_messages)}*",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=st_name, icon_url=member.display_avatar.url)
            embed.set_thumbnail(url=ICON_EVIL)
            embed.add_field(name=f"**{EMOJI_SWORD} Victor**", value="Evil", inline=True)
        else:
            embed = discord.Embed(
                title=f"{EMOJI_SCRIPT} The Grimoire Closes",
                description=f"*The tale of {script_name} ends in shadow...*",
                color=discord.Color.dark_gray(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=st_name, icon_url=member.display_avatar.url)
            embed.add_field(name=f"**{EMOJI_SWORD} Result**", value=f"{winner_str}", inline=True)
        
        embed.add_field(name=f"**{EMOJI_SCRIPT} Script**", value=f"{script_name}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name=f"**{EMOJI_CLOCK} Duration**", value=f"{duration_str}", inline=True)
        embed.add_field(name=f"**{EMOJI_PLAYERS} Players**", value=f"{player_count}", inline=True)
        
        start_timestamp = int(game["start_time"])
        embed.add_field(name=f"**{EMOJI_CLOCK} Began**", value=f"<t:{start_timestamp}:t>", inline=True)
        
        # Add session code if available
        session_manager = bot.session_manager
        session = None
        if session_manager and category_id:
            session = await session_manager.get_session(guild_id, category_id)
        
        footer_text = f"Grimkeeper v{VERSION} • The tale is told"
        if session and session.session_code:
            footer_text += f" • Session: {session.session_code}"
        embed.set_footer(text=footer_text)
        
        # Send to the channel where the command was used (not announcement channel)
        await interaction.response.send_message(embed=embed)
                        
    except DatabaseError as e:
        logger.error(f"Database error in end_game_handler: {e}")
        await safe_send_interaction(
            interaction,
            "❌ Database error ending game. Please try again.",
            ephemeral=True
        )
    except Exception as e:
        logger.exception(f"Unexpected error in end_game_handler: {e}")
        await safe_send_interaction(
            interaction,
            "❌ Failed to end game. See logs.",
            ephemeral=True
        )
