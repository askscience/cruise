"""
Main Controller Module

Contains the main application controller that handles business logic,
signal connections, and coordinates between UI and services.
"""

import os
import time
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox, QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon

# Import application services
from app.services.transcription_service import TranscriptionService, TranscriptionThread
from app.services.database_manager import NotesDatabase
from app.components.custom_dialogs import ProjectDialog
from app.utils.app_utils import create_themed_icon_pixmap, detect_system_theme


class MainController:
    """
    Main application controller that coordinates between UI and business logic.
    
    This class handles:
    - Signal/slot connections
    - Business logic coordination
    - Audio playback control
    - Transcription workflow
    - Project management
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        
        # Initialize core components
        self._init_core_components()
        
        # Initialize audio system
        self._init_audio_system()
        
        # Connect signals
        self._connect_signals()
        
        # Load model
        self.load_model()
    
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
        import pygame
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
    
    def _connect_signals(self):
        """Connect all UI element signals to their respective slots."""
        # Menu connections
        self.main_window.ui.action_open_project.triggered.connect(self.open_project)
        self.main_window.ui.action_save.triggered.connect(self.save_project)
        self.main_window.ui.action_save_as.triggered.connect(self.save_project_as)
        self.main_window.ui.action_exit.triggered.connect(self.main_window.close)
        
        # Button connections
        self.main_window.browse_button.clicked.connect(self.browse_for_file)
        self.main_window.transcribe_button.clicked.connect(self.start_transcription)
        self.main_window.play_pause_button.clicked.connect(self.toggle_playback)
        self.main_window.copy_button.clicked.connect(self.copy_transcription)
        self.main_window.clear_button.clicked.connect(self.clear_all)
        self.main_window.plus_button.clicked.connect(self.show_notes_sidebar)
        
        # Waveform widget connections
        self.main_window.waveform_widget.playback_position_changed.connect(self.seek_audio)
        self.main_window.waveform_widget.scrubbing_position_changed.connect(self.scrub_audio)
        self.main_window.waveform_widget.note_requested.connect(self.show_notes_sidebar)
        
        # Splitter connection for overlay positioning
        self.main_window.ui.main_splitter.splitterMoved.connect(self.main_window.position_scale_overlay)
    
    # ==================== Application Logic ====================
    
    def load_model(self):
        """Load the Whisper model asynchronously."""
        def on_model_loaded(success, message):
            if success:
                print(f"Model loaded: {message}")
            else:
                print(f"Model loading failed: {message}")
                QMessageBox.warning(self.main_window, "Model Loading Error", message)
        
        self.transcription_service.load_model_async(on_model_loaded)
    
    def browse_for_file(self):
        """Open file dialog to select audio file."""
        file_filter = self.transcription_service.get_supported_formats_filter()
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Select Audio File", "", file_filter
        )
        
        if file_path:
            self.load_audio_file(file_path)
    
    def load_audio_file(self, file_path):
        """Load and validate audio file."""
        is_valid, message = self.transcription_service.validate_file(file_path)
        
        if not is_valid:
            QMessageBox.warning(self.main_window, "Invalid File", message)
            return
        
        self.current_file_path = file_path
        self.main_window.file_path_edit.setText(os.path.basename(file_path))
        
        # Enable controls
        self.main_window.transcribe_button.setEnabled(True)
        self.main_window.play_pause_button.setEnabled(True)
        
        # Load audio into waveform widget
        self.main_window.waveform_widget.load_audio_file(file_path)
        
        # Get audio duration
        self.audio_duration = self.transcription_service.get_audio_duration(file_path)
    
    def start_transcription(self):
        """Start audio transcription process."""
        if not self.current_file_path:
            QMessageBox.warning(self.main_window, "No File", "Please select an audio file first.")
            return
        
        # Check if model is loaded, if not, load it first
        if not self.transcription_service.model:
            self._load_model_and_start_transcription()
            return
        
        self._start_transcription_with_model()
    
    def _load_model_and_start_transcription(self):
        """Load the Whisper model and then start transcription."""
        # Disable transcribe button during loading
        self.main_window.transcribe_button.setEnabled(False)
        
        # Create a progress dialog
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt
        
        # Create a more visible progress dialog
        self.progress_dialog = QProgressDialog("Loading Whisper model...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Model Loading")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setMinimumSize(400, 120)  # Make it more visible
        self.progress_dialog.setAutoClose(False)  # Don't auto-close
        self.progress_dialog.setAutoReset(False)  # Don't auto-reset
        
        # Style the progress dialog to be more prominent
        self.progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: #2b2b2b;
                color: white;
                border: 2px solid #4a9eff;
                border-radius: 8px;
            }
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #333;
                color: white;
                font-weight: bold;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4a9eff, stop: 1 #6bb6ff);
                border-radius: 3px;
            }
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6bb6ff;
            }
        """)
        
        self.progress_dialog.show()
        
        # Track progress steps
        self.progress_step = 0
        self.progress_steps = [
            "Preparing to load",
            "Configuring threading",
            "Downloading and loading",
            "This may take several minutes",
            "Model loaded successfully"
        ]
        
        def on_progress_update(message):
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.setLabelText(message)
                
                # Update progress based on message content
                if "Preparing to load" in message:
                    self.progress_step = 10
                elif "Configuring threading" in message:
                    self.progress_step = 25
                elif "Downloading and loading" in message:
                    self.progress_step = 40
                elif "This may take several minutes" in message:
                    self.progress_step = 60
                elif "Model loaded successfully" in message:
                    self.progress_step = 100
                elif "Error:" in message:
                    self.progress_step = 0
                    self.progress_dialog.setStyleSheet(self.progress_dialog.styleSheet() + """
                        QProgressBar::chunk {
                            background-color: #ff4444;
                        }
                    """)
                
                self.progress_dialog.setValue(self.progress_step)
        
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
                self.main_window.transcribe_button.setEnabled(True)
                QMessageBox.critical(self.main_window, "Model Loading Error", f"Failed to load Whisper model: {message}")
        
        # Handle cancel button
        def on_cancel():
            if hasattr(self.transcription_service, 'model_loading_thread') and self.transcription_service.model_loading_thread:
                self.transcription_service.model_loading_thread.terminate()
            self.main_window.transcribe_button.setEnabled(True)
        
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
            self.main_window.transcribe_button.setEnabled(False)
            
            # Start transcription
            self.transcription_thread.start()
            
        except Exception as e:
            # Re-enable button on error
            self.main_window.transcribe_button.setEnabled(True)
            QMessageBox.critical(self.main_window, "Transcription Error", f"Failed to start transcription: {str(e)}")
    
    def on_transcription_complete(self, result):
        """Handle completed transcription."""
        self.current_transcription = result
        
        # Process transcription result and add to waveform
        if 'segments' in result:
            # Render sentence-level segments as bubbles
            self.main_window.waveform_widget.set_transcription_segments(result.get('segments', []))
        
        # Re-enable transcribe button
        self.main_window.transcribe_button.setEnabled(True)
        self.main_window.copy_button.setEnabled(True)
        
        QMessageBox.information(self.main_window, "Success", "Transcription completed successfully!")
    
    def on_transcription_error(self, error_message):
        """Handle transcription error."""
        self.main_window.transcribe_button.setEnabled(True)
        QMessageBox.critical(self.main_window, "Transcription Error", f"Transcription failed: {error_message}")
    
    def on_transcription_progress(self, message):
        """Handle transcription progress updates."""
        print(f"Transcription progress: {message}")
    
    def toggle_playback(self):
        """Toggle audio playback."""
        import pygame
        
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
                self._update_play_pause_icon("pause.svg")
                
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
    
    def _update_play_pause_icon(self, icon_filename):
        """Update the play/pause button icon."""
        icon_path = Path(__file__).parent.parent.parent / "resources" / "icons" / icon_filename
        if icon_path.exists():
            pixmap = create_themed_icon_pixmap(str(icon_path), detect_system_theme())
            icon = QIcon(pixmap)
            self.main_window.play_pause_button.setIcon(icon)
    
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
        import pygame
        
        if self.is_playing and not self.is_paused:
            current_time = time.time() - self.playback_start_time
            
            # Update time label
            minutes = int(current_time // 60)
            seconds = int(current_time % 60)
            self.main_window.time_label.setText(f"{minutes:02d}:{seconds:02d}")
            
            # Update waveform position
            if hasattr(self.main_window.waveform_widget, 'update_playback_position'):
                self.main_window.waveform_widget.update_playback_position(current_time)
            
            # Check if playback finished
            if not pygame.mixer.music.get_busy():
                self.stop_playback()
    
    def stop_playback(self):
        """Stop audio playback."""
        self.is_playing = False
        self.is_paused = False
        self.playback_timer.stop()
        
        # Reset button icon to play
        self._update_play_pause_icon("play.svg")
    
    def copy_transcription(self):
        """Copy transcription text to clipboard."""
        if self.current_transcription and 'text' in self.current_transcription:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_transcription['text'])
            QMessageBox.information(self.main_window, "Copied", "Transcription copied to clipboard!")
    
    def clear_all(self):
        """Clear all transcription data and reset UI."""
        reply = QMessageBox.question(
            self.main_window, "Clear All", 
            "Are you sure you want to clear all transcription data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.main_window.waveform_widget.clear_all_annotations()
            self.current_transcription = {}
            self.main_window.copy_button.setEnabled(False)
    
    def show_notes_sidebar(self):
        """Show notes sidebar."""
        if hasattr(self.main_window.sidebar_manager, 'show_sidebar'):
            self.main_window.sidebar_manager.show_sidebar("", 0.0, fresh_conversation=False)
    
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