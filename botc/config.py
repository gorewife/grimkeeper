"""Configuration management for Grimkeeper.

Uses pydantic for validation and type safety.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger('botc_bot')

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field, field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

if not PYDANTIC_AVAILABLE:
    # Fallback if pydantic not installed - use simple config
    class Settings:
        """Fallback configuration without pydantic validation."""
        
        def __init__(self):
            # Try to load .env file if python-dotenv is available
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            
            self.discord_token = os.getenv("DISCORD_TOKEN")
            self.database_url = os.getenv("DATABASE_URL")
            self.log_level = os.getenv("LOG_LEVEL", "INFO")
            self.silent_restart = os.getenv("BOTC_SILENT_RESTART", "0").lower() in ("1", "true", "yes")
            self.bot_prefix = os.getenv("BOT_PREFIX", "*")
            self.db_pool_min_size = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
            self.db_pool_max_size = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
            self.db_command_timeout = int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
            self.enable_guild_whitelist = os.getenv("ENABLE_GUILD_WHITELIST", "false").lower() in ("1", "true", "yes")
            self.guild_whitelist = os.getenv("GUILD_WHITELIST")
            
            # Validate required fields
            if not self.discord_token:
                raise ValueError("DISCORD_TOKEN not found in environment!")
            if not self.database_url:
                raise ValueError("DATABASE_URL not found in environment!")
        
        def get_whitelisted_guild_ids(self):
            """Parse guild whitelist into set of guild IDs.
            
            Returns:
                Set of whitelisted guild IDs, or empty set if whitelist not enabled/configured
            """
            if not self.enable_guild_whitelist or not self.guild_whitelist:
                return set()
            
            guild_ids = set()
            for guild_id in self.guild_whitelist.split(','):
                guild_id = guild_id.strip()
                if guild_id:
                    try:
                        guild_ids.add(int(guild_id))
                    except ValueError:
                        pass
            return guild_ids

else:
    class Settings(BaseSettings):
        """Application settings with validation.
        
        All settings are loaded from environment variables or .env file.
        """
        
        model_config = SettingsConfigDict(
            env_file='.env',
            env_file_encoding='utf-8',
            case_sensitive=False,
            extra='ignore'
        )
        
        # Required settings
        discord_token: str = Field(..., validation_alias='DISCORD_TOKEN')
        database_url: str = Field(..., validation_alias='DATABASE_URL')
        
        # Optional settings with defaults
        log_level: str = Field(default="INFO", validation_alias='LOG_LEVEL')
        silent_restart: bool = Field(default=False, validation_alias='BOTC_SILENT_RESTART')
        bot_prefix: str = Field(default="*", validation_alias='BOT_PREFIX')
        
        # Database pool settings
        db_pool_min_size: int = Field(default=2, validation_alias='DB_POOL_MIN_SIZE')
        db_pool_max_size: int = Field(default=10, validation_alias='DB_POOL_MAX_SIZE')
        db_command_timeout: int = Field(default=60, validation_alias='DB_COMMAND_TIMEOUT')
        
        # Guild whitelist (optional)
        enable_guild_whitelist: bool = Field(default=False, validation_alias='ENABLE_GUILD_WHITELIST')
        guild_whitelist: Optional[str] = Field(default=None, validation_alias='GUILD_WHITELIST')
        
        def get_whitelisted_guild_ids(self) -> set[int]:
            """Parse guild whitelist into set of guild IDs.
            
            Returns:
                Set of whitelisted guild IDs, or empty set if whitelist not enabled/configured
            """
            if not self.enable_guild_whitelist or not self.guild_whitelist:
                return set()
            
            guild_ids = set()
            for guild_id in self.guild_whitelist.split(','):
                guild_id = guild_id.strip()
                if guild_id:
                    try:
                        guild_ids.add(int(guild_id))
                    except ValueError:
                        logger.warning(f"Invalid guild ID in whitelist: {guild_id}")
            return guild_ids
        
        @field_validator('enable_guild_whitelist', mode='before')
        @classmethod
        def parse_enable_whitelist(cls, v):
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.lower() in ('1', 'true', 'yes', 'on')
            return bool(v)
        
        @field_validator('log_level')
        @classmethod
        def validate_log_level(cls, v):
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            v_upper = v.upper()
            if v_upper not in valid_levels:
                raise ValueError(f"log_level must be one of {valid_levels}")
            return v_upper
        
        @field_validator('silent_restart', mode='before')
        @classmethod
        def parse_silent_restart(cls, v):
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.lower() in ('1', 'true', 'yes', 'on')
            return bool(v)

# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the application settings instance.
    
    Returns:
        Settings object with validated configuration
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
