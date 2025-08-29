"""
System Checker Module
Checks for Ollama installation and Whisper model availability.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any


class SystemChecker:
    """Checks system requirements for Whisper and Ollama."""
    
    def __init__(self):
        self.whisper_models = [
            ("tiny", "39 MB", "Fastest, lowest accuracy"),
            ("base", "74 MB", "Good speed, basic accuracy"),
            ("small", "244 MB", "Balanced speed and accuracy"),
            ("medium", "769 MB", "Better accuracy, slower"),
            ("large", "1550 MB", "Best accuracy, slowest"),
            ("turbo", "809 MB", "Optimized large model")
        ]
        
    def check_ollama_installed(self) -> Tuple[bool, str, Dict[str, str]]:
        """Check if Ollama is installed and accessible."""
        try:
            result = subprocess.run(
                ["ollama", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                return True, "setup.ollama_status_installed", {"version": result.stdout.strip()}
            else:
                return False, "setup.ollama_status_failed", {}
        except subprocess.TimeoutExpired:
            return False, "setup.ollama_status_timeout", {}
        except FileNotFoundError:
            return False, "setup.ollama_status_not_found", {}
        except Exception as e:
            return False, "setup.ollama_status_error", {"error": str(e)}
    
    def get_available_ollama_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                models = []
                for line in lines:
                    if line.strip():
                        model_name = line.split()[0]
                        models.append(model_name)
                return models
            return []
        except Exception:
            return []
    
    def get_popular_ollama_models(self) -> List[Tuple[str, str, str]]:
        """Get list of popular Ollama models with descriptions."""
        return [
            ("gemma3:1b", "1B params, 815MB", "Fast, lightweight Google model"),
            ("gemma3", "4B params, 3.3GB", "Balanced Google model"),
            ("llama3.2:1b", "1B params, 1.3GB", "Fast Meta model"),
            ("llama3.2", "3B params, 2.0GB", "Balanced Meta model"),
            ("llama3.1", "8B params, 4.7GB", "Advanced Meta model"),
            ("mistral", "7B params, 4.1GB", "Efficient Mistral model"),
            ("phi4-mini", "3.8B params, 2.5GB", "Microsoft's compact model"),
            ("qwen3:0.6b", "0.6B params, ~500MB", "Ultra-fast Alibaba model"),
            ("qwen3", "1.7B params, ~1.2GB", "Balanced Alibaba model")
        ]
    
    def check_whisper_model_available(self, model_name: str) -> bool:
        """Check if a Whisper model is available locally."""
        try:
            import whisper
            # Try to load the model to see if it's available
            model = whisper.load_model(model_name)
            return True
        except Exception:
            return False
    
    def get_whisper_models(self) -> List[Tuple[str, str, str]]:
        """Get list of available Whisper models."""
        return self.whisper_models


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self):
        self.config_file = Path(__file__).parent.parent.parent / "transcriber_config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        
        # Default configuration
        return {
            "whisper_model": "tiny",
            "ollama_model": "yasserrmd/smollm3:latest",
            "setup_completed": False,
            "skip_welcome": False,
            "language": "en"
        }
    
    def save_config(self) -> bool:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception:
            return False
    
    def is_setup_completed(self) -> bool:
        """Check if initial setup has been completed."""
        return self.config.get("setup_completed", False)
    
    def get_skip_welcome(self) -> bool:
        """Check if welcome screen should be skipped."""
        return self.config.get("skip_welcome", False)
    
    def set_setup_completed(self, completed: bool = True):
        """Mark setup as completed."""
        self.config["setup_completed"] = completed
        self.save_config()
    
    def set_skip_welcome(self, skip: bool = True):
        """Set whether to skip welcome screen."""
        self.config["skip_welcome"] = skip
        self.save_config()
    
    def set_whisper_model(self, model: str):
        """Set the Whisper model."""
        self.config["whisper_model"] = model
        self.save_config()
    
    def set_ollama_model(self, model: str):
        """Set the Ollama model."""
        self.config["ollama_model"] = model
        self.save_config()
    
    def get_whisper_model(self) -> str:
        """Get the current Whisper model."""
        return self.config.get("whisper_model", "tiny")
    
    def get_ollama_model(self) -> str:
        """Get the current Ollama model."""
        return self.config.get("ollama_model", "yasserrmd/smollm3:latest")

    def set_language(self, language: str):
        """Set the application language."""
        self.config["language"] = language
        self.save_config()

    def get_language(self) -> str:
        """Get the application language."""
        return self.config.get("language", "en")