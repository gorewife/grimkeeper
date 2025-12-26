"""Internationalization (i18n) system for Grimkeeper.

Handles loading translation files and providing localized strings.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger('botc_bot')

class Translator:
    """Manages translations for multiple languages."""
    
    def __init__(self, default_language: str = 'en', db=None):
        self.default_language = default_language
        self.translations: Dict[str, dict] = {}
        self.guild_languages: Dict[int, str] = {}
        self.db = db
        self.load_all_translations()
    
    def load_all_translations(self):
        """Load all translation files from locales/ directory."""
        locales_dir = Path(__file__).parent.parent / 'locales'
        
        for json_file in locales_dir.glob('*.json'):
            language_code = json_file.stem
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self.translations[language_code] = json.load(f)
                logger.info(f"Loaded translation: {language_code}")
            except Exception as e:
                logger.error(f"Failed to load translation {language_code}: {e}")
        
        if not self.translations:
            logger.warning("No translation files loaded!")
    
    def set_guild_language(self, guild_id: int, language_code: str) -> bool:
        """Set the language for a guild."""
        if language_code not in self.translations:
            return False
        self.guild_languages[guild_id] = language_code
        return True
    
    def get_guild_language(self, guild_id: int) -> str:
        """Get the language code for a guild (defaults to English)."""
        return self.guild_languages.get(guild_id, self.default_language)
    
    def get(self, guild_id: int, key_path: str, **kwargs) -> str:
        """Get a translated string.
        
        Args:
            guild_id: Discord guild ID
            key_path: Dot-separated path to translation key (e.g., "errors.no_permission")
            **kwargs: Format variables to substitute in the string
        
        Returns:
            Translated string with variables substituted
        
        Example:
            t.get(guild_id, "errors.no_permission")
            t.get(guild_id, "game_messages.good_wins", index=2)
        """
        lang = self.get_guild_language(guild_id)
        trans = self.translations.get(lang, self.translations.get(self.default_language, {}))
        
        keys = key_path.split('.')
        value = trans
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        if value is None:
            value = self._get_fallback(key_path)
        
        if isinstance(value, list):
            index = kwargs.pop('index', 0)
            value = value[index] if 0 <= index < len(value) else value[0]
        
        if isinstance(value, str) and kwargs:
            try:
                value = value.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format variable {e} in translation {key_path}")
        
        return value or key_path
    
    def _get_fallback(self, key_path: str) -> Optional[str]:
        """Get English fallback if translation is missing."""
        trans = self.translations.get(self.default_language, {})
        keys = key_path.split('.')
        value = trans
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get list of available languages.
        
        Returns:
            Dict of language_code -> language_name
        """
        return {
            'en': '🇺🇸 English',
            'es': '🇪🇸 Español',
            'pl': '🇵🇱 Polski',
            'ru': '🇷🇺 Русский',
        }

# Global translator instance
_translator: Optional[Translator] = None

def get_translator() -> Translator:
    """Get the global translator instance."""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator
