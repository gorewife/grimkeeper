"""Custom exception classes for Grimkeeper bot.

Provides domain-specific exceptions for better error handling and debugging.
"""


class GrimkeeperError(Exception):
    """Base exception for all Grimkeeper-specific errors."""
    pass


class ConfigurationError(GrimkeeperError):
    """Raised when server configuration is missing or invalid.
    
    Examples:
        - BOTC category not set or not found
        - Town Square channel not configured
        - Announcement channel missing
    """
    pass


class PermissionError(GrimkeeperError):
    """Raised when bot lacks required Discord permissions.
    
    Examples:
        - Missing 'Move Members' permission for *call
        - Missing 'Manage Channels' permission for voice caps
        - Missing 'Manage Nicknames' permission for prefix system
    """
    pass


class DatabaseError(GrimkeeperError):
    """Raised when database operations fail.
    
    Examples:
        - Connection timeout
        - Query execution failure
        - Schema initialization error
    """
    pass


class RateLimitError(GrimkeeperError):
    """Raised when a user exceeds command rate limits.
    
    Note: Usually handled silently by ignoring the command.
    """
    pass


class ValidationError(GrimkeeperError):
    """Raised when user input validation fails.
    
    Examples:
        - Invalid duration format for timers
        - Invalid poll options
        - Invalid game winner choice
    """
    pass
