"""
Setup Utilities
Common utility functions for the setup process.
"""

import subprocess
import sys
from typing import Optional, Tuple
from pathlib import Path


def get_ollama_installation_instructions() -> str:
    """Get platform-specific Ollama installation instructions."""
    if sys.platform == "darwin":  # macOS
        return """To install Ollama on macOS:
1. Visit https://ollama.com
2. Download the macOS installer
3. Run the installer and follow the instructions
4. Restart this application after installation"""
    elif sys.platform.startswith("linux"):
        return """To install Ollama on Linux:
1. Run: curl -fsSL https://ollama.com/install.sh | sh
2. Or visit https://ollama.com for manual installation
3. Restart this application after installation"""
    elif sys.platform == "win32":
        return """To install Ollama on Windows:
1. Visit https://ollama.com
2. Download the Windows installer
3. Run the installer and follow the instructions
4. Restart this application after installation"""
    else:
        return "Visit https://ollama.com for installation instructions"


class SetupUtils:
    """Utility functions for setup operations."""
    
    @staticmethod
    def install_ollama_instructions() -> str:
        """Get platform-specific Ollama installation instructions."""
        if sys.platform == "darwin":  # macOS
            return """To install Ollama on macOS:
1. Visit https://ollama.com
2. Download the macOS installer
3. Run the installer and follow the instructions
4. Restart this application after installation"""
        elif sys.platform.startswith("linux"):
            return """To install Ollama on Linux:
1. Run: curl -fsSL https://ollama.com/install.sh | sh
2. Or visit https://ollama.com for manual installation
3. Restart this application after installation"""
        elif sys.platform == "win32":
            return """To install Ollama on Windows:
1. Visit https://ollama.com
2. Download the Windows installer
3. Run the installer and follow the instructions
4. Restart this application after installation"""
        else:
            return "Visit https://ollama.com for installation instructions"
    
    @staticmethod
    def check_internet_connection() -> bool:
        """Check if internet connection is available."""
        try:
            import urllib.request
            urllib.request.urlopen('http://www.google.com', timeout=5)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_model_size_info(model_name: str) -> Optional[str]:
        """Get estimated download size for a model."""
        size_map = {
            # Whisper models
            "tiny": "39 MB",
            "base": "74 MB", 
            "small": "244 MB",
            "medium": "769 MB",
            "large": "1550 MB",
            "turbo": "809 MB",
            
            # Common Ollama models (approximate)
            "gemma3:1b": "815 MB",
            "gemma3": "3.3 GB",
            "llama3.2:1b": "1.3 GB",
            "llama3.2": "2.0 GB",
            "llama3.1": "4.7 GB",
            "mistral": "4.1 GB",
            "phi4-mini": "2.5 GB",
            "qwen3:0.6b": "500 MB",
            "qwen3": "1.2 GB"
        }
        return size_map.get(model_name)
    
    @staticmethod
    def validate_model_name(model_name: str) -> bool:
        """Validate if a model name is properly formatted."""
        if not model_name or not model_name.strip():
            return False
        
        # Basic validation - should not contain invalid characters
        invalid_chars = ['<', '>', '|', '&', ';', '`', '$']
        return not any(char in model_name for char in invalid_chars)
    
    @staticmethod
    def get_config_backup_path() -> Path:
        """Get path for configuration backup."""
        config_dir = Path(__file__).parent.parent.parent
        return config_dir / "transcriber_config.backup.json"
    
    @staticmethod
    def create_config_backup(config_path: Path) -> bool:
        """Create a backup of the configuration file."""
        try:
            backup_path = SetupUtils.get_config_backup_path()
            if config_path.exists():
                import shutil
                shutil.copy2(config_path, backup_path)
                return True
        except Exception:
            pass
        return False
    
    @staticmethod
    def restore_config_backup(config_path: Path) -> bool:
        """Restore configuration from backup."""
        try:
            backup_path = SetupUtils.get_config_backup_path()
            if backup_path.exists():
                import shutil
                shutil.copy2(backup_path, config_path)
                return True
        except Exception:
            pass
        return False