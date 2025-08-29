"""
Audio Transcriber Application
A modern GUI application for transcribing audio files using OpenAI's Whisper AI.

This is the main entry point that brings together the GUI and transcription engine.
"""

import sys
from PySide6.QtWidgets import QApplication

from .main_gui import AudioTranscriberGUI
from app.setup.system_checker import ConfigManager
from app.setup.welcome_screen import WelcomeOverlay


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Audio Transcriber")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Whisper AI Tools")
    
    # Create main window
    window = AudioTranscriberGUI()
    
    # Check if we should show welcome screen
    config_manager = ConfigManager()
    if not config_manager.is_setup_completed():
        # Show welcome overlay on top of main window
        welcome_overlay = WelcomeOverlay(window)
        welcome_overlay.setup_completed.connect(lambda: welcome_overlay.close())
        
        # Position overlay to cover the entire main window
        welcome_overlay.resize(window.size())
        welcome_overlay.move(0, 0)
        welcome_overlay.show()
        welcome_overlay.raise_()  # Bring to front
    
    # Show main window
    window.show()
    
    sys.exit(app.exec())


# Entry point removed: launch the application via launcher.py