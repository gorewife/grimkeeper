"""Custom exception classes for Grimkeeper bot.

Provides domain-specific exceptions for better error handling and debugging.
"""


class GrimkeeperError(Exception):
    """Base exception for all Grimkeeper-specific errors."""
    pass


class ConfigurationError(GrimkeeperError):
    """Raised when server configuration is missing or invalid."""
    pass


class PermissionError(GrimkeeperError):
    """Raised when bot lacks required Discord permissions."""
    pass


class DatabaseError(GrimkeeperError):
    """Raised when database operations fail."""
    pass


class RateLimitError(GrimkeeperError):
    """Raised when a user exceeds command rate limits."""
    pass


class ValidationError(GrimkeeperError):
    """Raised when user input validation fails."""
    pass
