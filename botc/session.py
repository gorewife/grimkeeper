"""Session management for category-scoped game instances.

This module provides the Session abstraction that allows multiple concurrent games
within a single Discord server by scoping game state to individual categories.

Key concepts:
- Sessions are PERSISTENT ADMIN INFRASTRUCTURE (created once, used forever)
- session_id = (guild_id, category_id) - uniquely identifies a game session
- Each session has a permanent code (s1, s2, s3) used for all games in that category
- Sessions are created by admins via /setbotc or /autosetup, NOT by storytellers
- Each category can run independent games with own ST, grimoire, players, timer
- Commands are automatically scoped to the session based on the channel they're used in
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field

import discord

if TYPE_CHECKING:
    from botc.database import Database

logger = logging.getLogger('botc_bot')


@dataclass
class Session:
    """Represents an active game session scoped to a specific category.
    
    A session encapsulates all state for one game instance:
    - Configuration (destination channel, grimoire link)
    - Active game tracking
    - Timer state
    - Storyteller assignments
    
    Attributes:
        guild_id: Discord guild (server) ID
        category_id: Discord category ID this session is scoped to
        destination_channel_id: Town Square voice channel ID for *call
        grimoire_link: Current grimoire URL set by storyteller
        exception_channel_id: Voice channel excluded from *call operations
        announce_channel_id: Text channel for bot announcements
        active_game_id: Currently running game ID (from games table)
        storyteller_user_id: User ID of the storyteller for this session
        created_at: When this session was first created
        last_active: Last time this session was used
        session_code: Human-friendly code for API/website integration (e.g., "s1", "s2")
    """
    guild_id: int
    category_id: int
    destination_channel_id: Optional[int] = None
    grimoire_link: Optional[str] = None
    exception_channel_id: Optional[int] = None
    announce_channel_id: Optional[int] = None
    active_game_id: Optional[int] = None
    storyteller_user_id: Optional[int] = None
    created_at: Optional[float] = None
    last_active: Optional[float] = None
    vc_caps: dict[int, int] = field(default_factory=dict)  # {channel_id: original_limit}
    session_code: Optional[str] = None  # Human-friendly identifier for website integration
    
    @property
    def session_id(self) -> tuple[int, int]:
        """Composite key uniquely identifying this session."""
        return (self.guild_id, self.category_id)
    
    def __repr__(self) -> str:
        return f"Session(guild={self.guild_id}, category={self.category_id})"


class SessionManager:
    """Manages session lifecycle and resolution.
    
    Responsible for:
    - Creating and loading sessions from database
    - Resolving which session a command belongs to
    - Cleaning up inactive sessions
    """
    
    def __init__(self, db: Database):
        self.db = db
        self._cache: dict[tuple[int, int], Session] = {}
    
    async def _generate_session_code(self, guild_id: int) -> str:
        """Generate a unique session code for a guild.
        
        Format: s1, s2, s3... (simple sequential numbers per guild)
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Session code like "s1", "s2", etc.
        """
        # Get existing sessions for this guild to find next number
        existing_sessions = await self.db.get_all_sessions_for_guild(guild_id)
        
        # Extract numbers from existing codes (e.g., "s1" -> 1, "s2" -> 2)
        existing_numbers = []
        for session in existing_sessions:
            if session.session_code and session.session_code.startswith('s'):
                try:
                    num = int(session.session_code[1:])
                    existing_numbers.append(num)
                except ValueError:
                    pass
        
        # Find next available number
        next_num = 1
        if existing_numbers:
            next_num = max(existing_numbers) + 1
        
        return f"s{next_num}"
    
    async def get_session_from_channel(
        self, 
        channel: discord.TextChannel | discord.VoiceChannel,
        guild: discord.Guild
    ) -> Optional[Session]:
        """Resolve session from a Discord channel.
        
        Looks up the category this channel belongs to and returns the
        corresponding session.
        
        Args:
            channel: The Discord channel where a command was used
            guild: The Discord guild
            
        Returns:
            Session if channel is in a BOTC category, None otherwise
        """
        if not channel.category:
            return None
        
        category_id = channel.category.id
        session_key = (guild.id, category_id)
        
        # Check cache first
        if session_key in self._cache:
            return self._cache[session_key]
        
        # Load from database
        session = await self.db.get_session(guild.id, category_id)
        
        if session:
            self._cache[session_key] = session
            return session
        
        return None
    
    async def get_or_create_session_from_channel(
        self,
        channel: discord.TextChannel | discord.VoiceChannel,
        guild: discord.Guild
    ) -> Optional[Session]:
        """DEPRECATED: Resolve session from a Discord channel, creating it if it doesn't exist.
        
        ⚠️ WARNING: This method is deprecated. Only /setbotc and /autosetup should create sessions.
        This method remains for backward compatibility but should NOT be used in new code.
        All session-scoped commands now require pre-existing sessions.
        
        Args:
            channel: The Discord channel where a command was used
            guild: The Discord guild
            
        Returns:
            Session for this category, creating if needed. None if channel has no category.
        """
        if not channel.category:
            return None
        
        category_id = channel.category.id
        session_key = (guild.id, category_id)
        
        # Check cache first
        if session_key in self._cache:
            return self._cache[session_key]
        
        # Load from database
        session = await self.db.get_session(guild.id, category_id)
        
        if session:
            self._cache[session_key] = session
            return session
        
        # Create new session for this category
        logger.info(f"Creating new session for guild {guild.id}, category {category_id} ({channel.category.name if channel.category else 'unknown'})")
        session = await self.create_session(guild.id, category_id)
        return session
    
    async def get_session_from_message(self, message: discord.Message) -> Optional[Session]:
        """Resolve session from a message.
        
        Args:
            message: Discord message containing a command
            
        Returns:
            Session if message is in a BOTC category, None otherwise
        """
        return await self.get_session_from_channel(message.channel, message.guild)
    
    async def get_session_from_interaction(self, interaction: discord.Interaction) -> Optional[Session]:
        """Resolve session from a slash command interaction.
        
        Args:
            interaction: Discord interaction from a slash command
            
        Returns:
            Session if interaction is in a BOTC category, None otherwise
        """
        return await self.get_session_from_channel(interaction.channel, interaction.guild)
    
    async def get_session_from_voice_channel(
        self,
        voice_channel: discord.VoiceChannel,
        guild: discord.Guild
    ) -> Optional[Session]:
        """Resolve session from a voice channel.
        
        Args:
            voice_channel: Discord voice channel
            guild: Discord guild
            
        Returns:
            Session if voice channel is in a BOTC category, None otherwise
        """
        return await self.get_session_from_channel(voice_channel, guild)
    
    async def get_session(self, guild_id: int, category_id: int) -> Optional[Session]:
        """Get a session by guild and category ID directly.
        
        Args:
            guild_id: Discord guild ID
            category_id: Discord category ID
            
        Returns:
            Session if found, None otherwise
        """
        session_key = (guild_id, category_id)
        
        # Check cache first
        if session_key in self._cache:
            return self._cache[session_key]
        
        # Load from database
        session = await self.db.get_session(guild_id, category_id)
        
        if session:
            # Auto-generate code for legacy sessions that don't have one (migration support)
            if not session.session_code:
                session.session_code = await self._generate_session_code(guild_id)
                await self.db.update_session(session)
                logger.info(f"Auto-generated session code '{session.session_code}' for legacy session: guild={guild_id}, category={category_id}")
            
            self._cache[session_key] = session
            return session
        
        # No session found
        return None
    
    async def get_session_by_code(self, guild_id: int, session_code: str) -> Optional[Session]:
        """Get a session by its session code.
        
        Args:
            guild_id: Discord guild ID
            session_code: Session code (e.g., "s1", "s2")
            
        Returns:
            Session if found, None otherwise
        """
        session = await self.db.get_session_by_code(guild_id, session_code)
        
        if session:
            # Cache it for future access
            self._cache[session.session_id] = session
        
        return session
    
    async def create_session(
        self, 
        guild_id: int, 
        category_id: int,
        destination_channel_id: Optional[int] = None,
        grimoire_link: Optional[str] = None,
        exception_channel_id: Optional[int] = None,
        announce_channel_id: Optional[int] = None,
        active_game_id: Optional[int] = None,
        storyteller_user_id: Optional[int] = None,
        vc_caps: Optional[dict[int, int]] = None,
        session_code: Optional[str] = None
    ) -> Session:
        """Create a new session for a category.
        
        Args:
            guild_id: Discord guild ID
            category_id: Discord category ID
            destination_channel_id: Optional Town Square channel ID
            grimoire_link: Optional grimoire URL
            exception_channel_id: Optional exception channel ID
            announce_channel_id: Optional announcement channel ID
            active_game_id: Optional active game ID
            storyteller_user_id: Optional storyteller user ID
            vc_caps: Optional dict of voice channel ID -> original user_limit
            session_code: Optional session code (auto-generated if not provided)
            
        Returns:
            Newly created Session
        """
        import time
        now = time.time()
        
        # Generate session code if not provided
        if not session_code:
            session_code = await self._generate_session_code(guild_id)
        
        session = Session(
            guild_id=guild_id,
            category_id=category_id,
            destination_channel_id=destination_channel_id,
            grimoire_link=grimoire_link,
            exception_channel_id=exception_channel_id,
            announce_channel_id=announce_channel_id,
            active_game_id=active_game_id,
            storyteller_user_id=storyteller_user_id,
            created_at=now,
            last_active=now,
            vc_caps=vc_caps or {},
            session_code=session_code
        )
        
        await self.db.create_session(session)
        self._cache[session.session_id] = session
        
        logger.info(f"Created new session: {session}")
        return session
    
    async def update_session(self, session: Session) -> None:
        """Update session in database and cache.
        
        Args:
            session: Session with updated fields
        """
        import time
        session.last_active = time.time()
        
        await self.db.update_session(session)
        self._cache[session.session_id] = session
    
    async def delete_session(self, guild_id: int, category_id: int) -> bool:
        """Delete a session.
        
        Args:
            guild_id: Discord guild ID
            category_id: Discord category ID
            
        Returns:
            True if session was deleted, False if it didn't exist
        """
        result = await self.db.delete_session(guild_id, category_id)
        self._cache.pop((guild_id, category_id), None)
        
        if result:
            logger.info(f"Deleted session: guild={guild_id}, category={category_id}")
        
        return result
    
    async def get_all_sessions_for_guild(self, guild_id: int) -> list[Session]:
        """Get all active sessions in a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of all sessions in the guild
        """
        return await self.db.get_all_sessions_for_guild(guild_id)
    
    async def cleanup_inactive_sessions(self, max_age_days: int = 30) -> int:
        """Clean up sessions that haven't been used recently.
        
        Args:
            max_age_days: Delete sessions inactive for this many days
            
        Returns:
            Number of sessions deleted
        """
        deleted = await self.db.delete_inactive_sessions(max_age_days)
        
        # Clear from cache
        import time
        cutoff = time.time() - (max_age_days * 24 * 60 * 60)
        for session_key in list(self._cache.keys()):
            session = self._cache[session_key]
            if session.last_active and session.last_active < cutoff:
                self._cache.pop(session_key, None)
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} inactive sessions (older than {max_age_days} days)")
        
        return deleted
    
    def invalidate_cache(self, guild_id: int = None, category_id: int = None) -> None:
        """Invalidate session cache.
        
        Args:
            guild_id: If provided, only invalidate sessions for this guild
            category_id: If provided with guild_id, only invalidate specific session
        """
        if guild_id is not None and category_id is not None:
            self._cache.pop((guild_id, category_id), None)
        elif guild_id is not None:
            keys_to_remove = [k for k in self._cache.keys() if k[0] == guild_id]
            for key in keys_to_remove:
                self._cache.pop(key, None)
        else:
            self._cache.clear()


async def get_session_category(
    session: Session,
    guild: discord.Guild
) -> Optional[discord.CategoryChannel]:
    """Get the Discord category for a session.
    
    Args:
        session: The session
        guild: Discord guild
        
    Returns:
        CategoryChannel if it exists, None otherwise
    """
    return guild.get_channel(session.category_id)
