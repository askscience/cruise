"""
Audio Transcriber - Main Application
Modern PySide6 audio transcription application with glassmorphism interface.

This refactored version follows modern software architecture principles:
- Modular UI components
- Separation of concerns
- Dynamic UI loading from .ui file
- Centralized styling via QSS
- Robust layout management
- Signal/slot communication
"""

import sys
import os
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QProgressBar, QFileDialog, QMessageBox, QSizePolicy, QSpacerItem, 
    QTabWidget, QSplitter, QInputDialog, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QPalette, QColor
from PySide6.QtUiTools import QUiLoader
import pygame

# Import application modules
from app.utils.app_utils import (
    ModernGlassButton, ModernGlassLineEdit, ModernGlassTextEdit, ModernGlassCard, 
    ModernHeaderLabel, ModernStatusLabel, AudioWaveformWidget, detect_system_theme,
    create_themed_icon_pixmap, ScaleControlOverlay
)
from app.services.transcription_service import TranscriptionService, TranscriptionThread
from app.components.sidebar_widget import SidebarManager
from app.services.database_manager import NotesDatabase
from app.components.custom_dialogs import ProjectDialog


class AudioTranscriberGUI(QMainWindow):
    """
    Main application window with futuristic glassmorphism interface.
    
    This class handles:
    - UI initialization from .ui file
    - Application logic and state management
    - Signal/slot connections
    - Theme management
    - Audio playback control
    - Transcription workflow
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self._init_core_components()
        
        # Initialize audio system
        self._init_audio_system()
        
        # Initialize theme monitoring
        self._init_theme_monitoring()
        
        # Setup UI from .ui file
        self._load_ui_from_file()
        
        # Setup application components
        self._setup_application_components()
        
        # Apply styling and connect signals
        self._finalize_setup()
    
    def _init_core_components(self):
        """Initialize core application components."""
        self.transcription_service = TranscriptionService()
        self.db = NotesDatabase()
        self.transcription_thread = None
        self.current_file_path = ""
        self.current_project_id = None
        self.current_transcription = {}
        
        # Audio playback state
        self.is_playing = False
        self.is_paused = False
        self.audio_duration = 0.0
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_playback_progress)
        self.playback_start_time = 0
    
    def _init_audio_system(self):
        """Initialize pygame audio system with fallback options."""
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.init()
            print("Audio system initialized successfully")
        except Exception as e:
            print(f"Audio initialization warning: {e}")
            try:
                pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
                print("Audio system initialized with fallback settings")
            except Exception as e2:
                print(f"Audio initialization failed: {e2}")
    
    def _init_theme_monitoring(self):
        """Initialize theme monitoring system."""
        self.current_system_theme = None
        self.theme_check_timer = QTimer()
        self.theme_check_timer.timeout.connect(self.check_theme_changes)
        self.theme_check_timer.start(5000)  # Check every 5 seconds
        self.themed_buttons = []
    
    def _load_ui_from_file(self):
        """Load UI from the .ui file and setup basic window properties."""
        # Load UI file
        ui_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "user_interface.ui")
        loader = QUiLoader()
        
        # Load UI directly from file path
        self.ui = loader.load(ui_file_path, self)
        
        # Set the loaded UI as central widget
        self.setCentralWidget(self.ui.centralwidget)
        
        # Setup window properties
        self.setWindowTitle("Audio Transcriber")
        self.setMinimumSize(900, 700)
        self.resize(1100, 800)
        
        # Set window flags for modern appearance
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowCloseButtonHint | 
            Qt.WindowType.WindowMinimizeButtonHint | 
            Qt.WindowType.WindowMaximizeButtonHint
        )
        
        # Setup menu bar
        self._setup_menu_bar()
    
    def _setup_menu_bar(self):
        """Setup menu bar actions and connections."""
        # Connect menu actions
        self.ui.action_open_project.triggered.connect(self.open_project)
        self.ui.action_save.triggered.connect(self.save_project)
        self.ui.action_save_as.triggered.connect(self.save_project_as)
        self.ui.action_exit.triggered.connect(self.close)
    
    def _setup_application_components(self):
        """Setup application-specific components that require custom widgets."""
        # Replace placeholder widgets with custom components
        self._setup_waveform_widget()
        self._setup_custom_buttons()
        self._setup_sidebar_manager()
        self._setup_scale_overlay()
        
        # Configure splitter
        self._configure_splitter()
        
        # Apply modern scrollbar styling
        self._apply_modern_scrollbar_style()
    
    def _setup_waveform_widget(self):
        """Replace placeholder waveform widget with custom AudioWaveformWidget."""
        # Remove placeholder widget
        old_widget = self.ui.waveform_widget
        old_widget.setParent(None)
        
        # Create custom waveform widget
        self.waveform_widget = AudioWaveformWidget()
        self.waveform_widget.setMinimumHeight(300)
        self.waveform_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.waveform_widget.notes_db = self.db
        
        # Set it in the scroll area
        self.ui.scroll_area.setWidget(self.waveform_widget)
        self.waveform_widget.scroll_area = self.ui.scroll_area
    
    def _setup_custom_buttons(self):
        """Setup custom button styling and functionality."""
        icon_dir = os.path.join(os.path.dirname(__file__), "..", "..", "icons")
        
        # Setup buttons with icons and styling
        self._setup_button_with_icon(self.ui.transcribe_button, "ai.svg", "transcribe_button")
        self._setup_button_with_icon(self.ui.browse_button, "browse.svg", "browse_button") 
        self._setup_button_with_icon(self.ui.play_pause_button, "play.svg", "play_pause_button")
        self._setup_button_with_icon(self.ui.copy_button, "copy.svg", "copy_button")
        self._setup_button_with_icon(self.ui.plus_button, "plus.svg", "plus_button")
        self._setup_button_with_icon(self.ui.clear_button, "clear.svg", "clear_button")
        
        # Setup file path edit with custom styling
        self._setup_file_path_edit()
        
        # Setup time label with custom styling
        self._setup_time_label()
    
    def _setup_button_with_icon(self, button, icon_filename, attr_name):
        """Setup a button with icon and custom styling."""
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", icon_filename)
        
        # Set the button as an attribute for easy access
        setattr(self, attr_name, button)
        
        # Apply icon if it exists
        if os.path.exists(icon_path):
            # Create themed icon
            pixmap = create_themed_icon_pixmap(icon_path, detect_system_theme())
            icon = QIcon(pixmap)
            button.setIcon(icon)
            button.setIconSize(QSize(20, 20))
        
        # Add to themed buttons list for theme updates
        self.themed_buttons.append(button)
        
        # Apply custom properties for styling
        if attr_name == "transcribe_button":
            button.setProperty("primary", True)
        
        print(f"Successfully setup {attr_name}")
    
    def _setup_file_path_edit(self):
        """Setup file path edit with custom styling."""
        self.file_path_edit = self.ui.file_path_edit
        self.file_path_edit.setPlaceholderText("Select an audio file...")
        self.file_path_edit.setReadOnly(True)
    
    def _setup_time_label(self):
        """Setup time label with custom styling."""
        self.time_label = self.ui.time_label
        self.time_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 0 20px;
            }
        """)
    
    def refresh_all_button_themes(self):
        """Refresh all button icons and styles for theme changes."""
        theme = detect_system_theme()
        icon_dir = os.path.join(os.path.dirname(__file__), "..", "..", "icons")
        
        # Update button icons
        button_icons = {
            'transcribe_button': 'ai.svg',
            'browse_button': 'browse.svg', 
            'play_pause_button': 'play.svg',
            'copy_button': 'copy.svg',
            'plus_button': 'plus.svg',
            'clear_button': 'clear.svg'
        }
        
        for attr_name, icon_filename in button_icons.items():
            if hasattr(self, attr_name):
                button = getattr(self, attr_name)
                icon_path = os.path.join(icon_dir, icon_filename)
                if os.path.exists(icon_path):
                    pixmap = create_themed_icon_pixmap(icon_path, theme)
                    icon = QIcon(pixmap)
                    button.setIcon(icon)
    
    def _setup_sidebar_manager(self):
        """Setup sidebar manager component."""
        # Remove placeholder sidebar widget
        old_sidebar = self.ui.sidebar_manager
        old_sidebar.setParent(None)
        
        # Create sidebar manager
        self.sidebar_manager = SidebarManager(
            all_sentences_provider=lambda: [
                ann['text'] for ann in self.waveform_widget.annotations 
                if ann.get('is_transcription')
            ]
        )
        self.sidebar_manager.current_sidebar = None
        
        # Add to splitter
        self.ui.main_splitter.addWidget(self.sidebar_manager)
    
    def _setup_scale_overlay(self):
        """Setup scale control overlay."""
        waveform_container = self.ui.waveform_container
        self.scale_overlay = ScaleControlOverlay(self.waveform_widget, waveform_container)
        self.scale_overlay.show()
        
        # Position overlay after UI is ready
        QTimer.singleShot(100, self.position_scale_overlay)
    
    def _configure_splitter(self):
        """Configure the main splitter properties."""
        self.ui.main_splitter.setCollapsible(0, False)  # Waveform not collapsible
        self.ui.main_splitter.setCollapsible(1, True)   # Sidebar collapsible
        self.ui.main_splitter.setSizes([self.width() - 400, 400])
        self.ui.main_splitter.setStretchFactor(0, 1)  # Main content expands
        self.ui.main_splitter.setStretchFactor(1, 0)  # Sidebar doesn't expand
        
        # Set minimum width for sidebar
        self.sidebar_manager.setMinimumWidth(250)
        
        # Hide splitter handle
        self.ui.main_splitter.setHandleWidth(0)
    
    def _apply_modern_scrollbar_style(self):
        """Apply modern scrollbar styling to scroll area."""
        # This will be handled by the QSS file
        pass
    
    def _finalize_setup(self):
        """Finalize application setup."""
        # Load and apply stylesheet
        self._load_stylesheet()
        
        # Connect signals
        self._connect_signals()
        
        # Load model
        self.load_model()
        
        # Initial theme setup
        self.refresh_all_button_themes()
        
        # Position overlay
        QTimer.singleShot(200, self.position_scale_overlay)
    
    def _load_stylesheet(self):
        """Load and apply the external QSS stylesheet."""
        qss_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "styles.qss")
        
        try:
            with open(qss_file_path, 'r') as qss_file:
                stylesheet = qss_file.read()
                
                # Apply theme-specific variables
                theme = detect_system_theme()
                self.setProperty("theme", theme)
                
                self.setStyleSheet(stylesheet)
                
        except FileNotFoundError:
            print(f"Warning: Stylesheet file not found: {qss_file_path}")
            # Fallback to basic styling
            self._apply_fallback_theme()
    
    def _apply_fallback_theme(self):
        """Apply fallback theme if QSS file is not available."""
        theme = detect_system_theme()
        
        if theme == 'dark':
            bg_color = QColor(20, 20, 30)
            text_color = QColor(220, 220, 255)
            highlight_color = QColor(0, 191, 255)
        else:
            bg_color = QColor(240, 240, 245)
            text_color = QColor(20, 20, 30)
            highlight_color = QColor(0, 122, 255)
        
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {bg_color.name()};
                color: {text_color.name()};
                font-family: 'Inter', sans-serif;
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
        """)
    
    def _connect_signals(self):
        """Connect all UI element signals to their respective slots."""
        # Button connections
        self.browse_button.clicked.connect(self.browse_for_file)
        self.transcribe_button.clicked.connect(self.start_transcription)
        self.play_pause_button.clicked.connect(self.toggle_playback)
        self.copy_button.clicked.connect(self.copy_transcription)
        self.clear_button.clicked.connect(self.clear_all)
        self.plus_button.clicked.connect(self.show_notes_sidebar)
        
        # Waveform widget connections
        self.waveform_widget.playback_position_changed.connect(self.seek_audio)
        self.waveform_widget.scrubbing_position_changed.connect(self.scrub_audio)
        self.waveform_widget.note_requested.connect(self.show_notes_sidebar)
        
        # Splitter connection for overlay positioning
        self.ui.main_splitter.splitterMoved.connect(self.position_scale_overlay)
    
    # ==================== UI Event Handlers ====================
    
    def position_scale_overlay(self):
        """Position the scale control overlay in the bottom right corner."""
        if hasattr(self, 'scale_overlay') and hasattr(self, 'ui'):
            waveform_container = self.ui.waveform_container
            if waveform_container and waveform_container.width() > 0:
                container_rect = waveform_container.rect()
                
                margin = 8
                overlay_x = max(0, container_rect.width() - self.scale_overlay.width() - margin)
                overlay_y = max(0, container_rect.height() - self.scale_overlay.height() - margin)
                
                self.scale_overlay.move(overlay_x, overlay_y)
            else:
                QTimer.singleShot(50, self.position_scale_overlay)
    
    def resizeEvent(self, event):
        """Handle window resize to reposition the scale overlay."""
        super().resizeEvent(event)
        self.position_scale_overlay()
    
    def check_theme_changes(self):
        """Check for system theme changes and update UI accordingly."""
        current_theme = detect_system_theme()
        if current_theme != self.current_system_theme:
            self.current_system_theme = current_theme
            self.setProperty("theme", current_theme)
            self.refresh_all_button_themes()
            # Reload stylesheet to apply theme changes
            self._load_stylesheet()
    

    
    # ==================== Application Logic ====================
    
    def load_model(self):
        """Load the Whisper model asynchronously."""
        def on_model_loaded(success, message):
            if success:
                print(f"Model loaded: {message}")
            else:
                print(f"Model loading failed: {message}")
                QMessageBox.warning(self, "Model Loading Error", message)
        
        self.transcription_service.load_model_async(on_model_loaded)
    
    def browse_for_file(self):
        """Open file dialog to select audio file."""
        file_filter = self.transcription_service.get_supported_formats_filter()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", file_filter
        )
        
        if file_path:
            self.load_audio_file(file_path)
    
    def load_audio_file(self, file_path):
        """Load and validate audio file."""
        is_valid, message = self.transcription_service.validate_file(file_path)
        
        if not is_valid:
            QMessageBox.warning(self, "Invalid File", message)
            return
        
        self.current_file_path = file_path
        self.file_path_edit.setText(os.path.basename(file_path))
        
        # Enable controls
        self.transcribe_button.setEnabled(True)
        self.play_pause_button.setEnabled(True)
        
        # Load audio into waveform widget
        self.waveform_widget.load_audio_file(file_path)
        
        # Get audio duration
        self.audio_duration = self.transcription_service.get_audio_duration(file_path)
    
    def start_transcription(self):
        """Start audio transcription process."""
        if not self.current_file_path:
            QMessageBox.warning(self, "No File", "Please select an audio file first.")
            return
        
        # Check if model is loaded, if not, load it first
        if not self.transcription_service.model:
            self._load_model_and_start_transcription()
            return
        
        self._start_transcription_with_model()
    
    def _load_model_and_start_transcription(self):
        """Load the Whisper model and then start transcription."""
        # Disable transcribe button during loading
        self.transcribe_button.setEnabled(False)
        
        # Create a progress dialog
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt
        
        self.progress_dialog = QProgressDialog("Loading Whisper model...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowTitle("Model Loading")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        
        def on_progress_update(message):
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.setLabelText(message)
        
        def on_model_loaded(success, message):
            # Close progress dialog
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            if success:
                print(f"Model loaded: {message}")
                self._start_transcription_with_model()
            else:
                print(f"Model loading failed: {message}")
                # Re-enable button
                self.transcribe_button.setEnabled(True)
                QMessageBox.critical(self, "Model Loading Error", f"Failed to load Whisper model: {message}")
        
        # Handle cancel button
        def on_cancel():
            if hasattr(self.transcription_service, 'model_loading_thread') and self.transcription_service.model_loading_thread:
                self.transcription_service.model_loading_thread.terminate()
            self.transcribe_button.setEnabled(True)
        
        self.progress_dialog.canceled.connect(on_cancel)
        
        self.transcription_service.load_model_with_progress(on_progress_update, on_model_loaded)
    
    def _start_transcription_with_model(self):
        """Start transcription with a loaded model."""
        try:
            self.transcription_thread = self.transcription_service.create_transcription_thread(
                self.current_file_path
            )
            
            # Connect signals
            self.transcription_thread.transcription_done.connect(self.on_transcription_complete)
            self.transcription_thread.error_occurred.connect(self.on_transcription_error)
            self.transcription_thread.progress_update.connect(self.on_transcription_progress)
            
            # Disable transcribe button during processing
            self.transcribe_button.setEnabled(False)
            
            # Start transcription
            self.transcription_thread.start()
            
        except Exception as e:
            # Re-enable button on error
            self.transcribe_button.setEnabled(True)
            QMessageBox.critical(
                self, 
                self.translation_manager.translate("dialogs.error"), 
                self.translation_manager.translate("messages.transcription_start_error").format(str(e))
            )
    
    def on_transcription_complete(self, result):
        """Handle completed transcription."""
        self.current_transcription = result
        
        # Process transcription result and add to waveform
        if 'segments' in result:
            # Render sentence-level segments as bubbles
            self.waveform_widget.set_transcription_segments(result.get('segments', []))
        
        # Re-enable transcribe button
        self.transcribe_button.setEnabled(True)
        self.copy_button.setEnabled(True)
        
        QMessageBox.information(
            self, 
            self.translation_manager.translate("dialogs.success"), 
            self.translation_manager.translate("messages.transcription_complete")
        )
    
    def on_transcription_error(self, error_message):
        """Handle transcription error."""
        self.transcribe_button.setEnabled(True)
        QMessageBox.critical(
            self, 
            self.translation_manager.translate("dialogs.error"), 
            self.translation_manager.translate("messages.transcription_error").format(error_message)
        )
    
    def on_transcription_progress(self, message):
        """Handle transcription progress updates."""
        print(f"Transcription progress: {message}")
    
    def toggle_playback(self):
        """Toggle audio playback."""
        if not self.current_file_path:
            return
        
        try:
            if not self.is_playing:
                # Start playback
                pygame.mixer.music.load(self.current_file_path)
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.playback_start_time = time.time()
                self.playback_timer.start(100)  # Update every 100ms
                
                # Update button icon to pause
                if hasattr(self.play_pause_button, 'update_icon'):
                    icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "pause.svg")
                    self.play_pause_button.update_icon(icon_path)
                
            elif self.is_paused:
                # Resume playback
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.playback_timer.start(100)
                
            else:
                # Pause playback
                pygame.mixer.music.pause()
                self.is_paused = True
                self.playback_timer.stop()
                
        except Exception as e:
            print(f"Playback error: {e}")
    
    def seek_audio(self, position):
        """Seek audio to specific position."""
        # Implementation depends on audio backend capabilities
        pass
    
    def scrub_audio(self, position):
        """Scrub audio to specific position during dragging."""
        # Implementation for real-time scrubbing
        pass
    
    def update_playback_progress(self):
        """Update playback progress and time display."""
        if self.is_playing and not self.is_paused:
            current_time = time.time() - self.playback_start_time
            
            # Update time label
            minutes = int(current_time // 60)
            seconds = int(current_time % 60)
            self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
            
            # Update waveform position
            if hasattr(self.waveform_widget, 'update_playback_position'):
                self.waveform_widget.update_playback_position(current_time)
            
            # Check if playback finished
            if not pygame.mixer.music.get_busy():
                self.stop_playback()
    
    def stop_playback(self):
        """Stop audio playback."""
        self.is_playing = False
        self.is_paused = False
        self.playback_timer.stop()
        
        # Reset button icon to play
        if hasattr(self.play_pause_button, 'update_icon'):
            icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "play.svg")
            self.play_pause_button.update_icon(icon_path)
    
    def copy_transcription(self):
        """Copy transcription text to clipboard."""
        if self.current_transcription and 'text' in self.current_transcription:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_transcription['text'])
            QMessageBox.information(
                self, 
                self.translation_manager.translate("dialogs.success"), 
                self.translation_manager.translate("messages.transcription_copied")
            )
    
    def clear_all(self):
        """Clear all transcription data and reset UI."""
        reply = QMessageBox.question(
            self, 
            self.translation_manager.translate("dialogs.confirmation"), 
            self.translation_manager.translate("messages.clear_all_confirmation"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.waveform_widget.clear_all_annotations()
            self.current_transcription = {}
            self.copy_button.setEnabled(False)
    
    def show_notes_sidebar(self):
        """Show notes sidebar."""
        if hasattr(self.sidebar_manager, 'show_sidebar'):
            self.sidebar_manager.show_sidebar("", 0.0, fresh_conversation=False)
    
    # ==================== Project Management ====================
    
    def open_project(self):
        """Open existing project."""
        dialog = ProjectDialog(self.db, mode='open')
        if dialog.exec():
            project_data = dialog.get_selected_project()
            if project_data:
                self.load_project(project_data)
    
    def save_project(self):
        """Save current project."""
        if self.current_project_id:
            self.save_current_project()
        else:
            self.save_project_as()
    
    def save_project_as(self):
        """Save project with new name."""
        dialog = ProjectDialog(self.db, mode='save')
        if dialog.exec():
            project_name = dialog.get_project_name()
            if project_name:
                self.save_project_with_name(project_name)
    
    def load_project(self, project_data):
        """Load project data into application."""
        # Implementation for loading project
        pass
    
    def save_current_project(self):
        """Save current project state."""
        # Implementation for saving project
        pass
    
    def save_project_with_name(self, name):
        """Save project with specified name."""
        # Implementation for saving project with name
        pass


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Cruise")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Cruise")
    
    # Create and show main window
    window = AudioTranscriberGUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


# Entry point removed: launch the application via launcher.py