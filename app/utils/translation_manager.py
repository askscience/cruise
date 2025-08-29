"""
Translation Manager for Audio Transcriber Application
Provides internationalization support using JSON-based translation files.
"""

import json
import os
from typing import Dict, Optional, Any
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QLocale, QCoreApplication

from app.setup.system_checker import ConfigManager


class TranslationManager(QObject):
    """Manages application translations and language switching."""
    
    # Signal emitted when language changes
    language_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_language = "en"
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.fallback_language = "en"
        self.translations_dir = Path(__file__).parent.parent.parent / "translations"
        
        # Ensure translations directory exists
        self.translations_dir.mkdir(exist_ok=True)
        
        # Load available translations
        self._load_all_translations()
        
        # Set initial language based on system locale
        self._set_initial_language()
    
    def _load_all_translations(self):
        """Load all available translation files."""
        if not self.translations_dir.exists():
            return
            
        for file_path in self.translations_dir.glob("*.json"):
            language_code = file_path.stem
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations[language_code] = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading translation file {file_path}: {e}")
    
    def _set_initial_language(self):
        """Set initial language from config or system locale."""
        config_manager = ConfigManager()
        language_code = config_manager.get_language()

        if language_code in self.translations:
            self.current_language = language_code
        else:
            system_locale = QLocale.system().name()
            language_code = system_locale.split('_')[0]
            if language_code in self.translations:
                self.current_language = language_code
            elif self.fallback_language in self.translations:
                self.current_language = self.fallback_language
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get list of available languages with their display names."""
        languages = {}
        for lang_code in self.translations.keys():
            # Get language display name from translation file
            lang_data = self.translations.get(lang_code, {})
            display_name = lang_data.get("_meta", {}).get("display_name", lang_code.upper())
            languages[lang_code] = display_name
        return languages
    
    def set_language(self, language_code: str) -> bool:
        """Set the current language."""
        if language_code in self.translations:
            if self.current_language != language_code:
                self.current_language = language_code
                self.language_changed.emit(language_code)
            return True
        return False
    
    def get_current_language(self) -> str:
        """Get the current language code."""
        return self.current_language
    
    def translate(self, key: str, **kwargs) -> Any:
        """
        Translate a text key to the current language.
        
        Args:
            key: Translation key (can use dot notation for nested keys)
            **kwargs: Variables to substitute in the translation
            
        Returns:
            The translated value. Returns native types for non-string values (e.g., lists/dicts),
            and a formatted string for string values. If not found, returns the key itself.
        """
        # Get translation from current language
        translation = self._get_nested_value(
            self.translations.get(self.current_language, {}), 
            key
        )
        
        # Fallback to default language if not found
        if translation is None and self.current_language != self.fallback_language:
            translation = self._get_nested_value(
                self.translations.get(self.fallback_language, {}), 
                key
            )
        
        # Return key if no translation found
        if translation is None:
            return key
        
        # Handle string formatting
        if isinstance(translation, str) and kwargs:
            try:
                return translation.format(**kwargs)
            except (KeyError, ValueError):
                return translation
        
        # Preserve non-string types (like lists/dicts) so callers can handle them
        return translation
    
    def _get_nested_value(self, data: Dict, key: str) -> Optional[Any]:
        """Get value from nested dictionary using dot notation."""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        # Return the value as-is (can be str, list, dict, etc.)
        return current
    
    def tr(self, key: str, **kwargs) -> str:
        """Shorthand for translate method."""
        return self.translate(key, **kwargs)


# Global translation manager instance
_translation_manager = None


def get_translation_manager() -> TranslationManager:
    """Get the global translation manager instance."""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


def tr(key: str, **kwargs) -> str:
    """Global translation function."""
    return get_translation_manager().translate(key, **kwargs)


def set_language(language_code: str) -> bool:
    """Set the application language."""
    return get_translation_manager().set_language(language_code)


def get_available_languages() -> Dict[str, str]:
    """Get available languages."""
    return get_translation_manager().get_available_languages()