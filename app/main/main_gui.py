"""Main GUI Application
PySide6-based audio transcriber with futuristic glassmorphism interface."""

import sys
import os
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QProgressBar, QFileDialog, QMessageBox, QSizePolicy, QSpacerItem, QTabWidget, QSplitter, QInputDialog, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QPalette, QColor, QActionGroup, QClipboard
import pygame

from app.utils.app_utils import (
    ModernGlassButton, ModernGlassLineEdit, ModernGlassTextEdit, ModernGlassCard, 
    ModernHeaderLabel, ModernStatusLabel, AudioWaveformWidget, detect_system_theme, create_themed_icon_pixmap
)
from app.services.transcription_service import TranscriptionService, TranscriptionThread
from app.components.sidebar_widget import SidebarManager
from app.services.database_manager import NotesDatabase
from app.components.custom_dialogs import ProjectDialog


class AudioTranscriberGUI(QMainWindow):
    """Main application window with futuristic glassmorphism interface."""
    
    def __init__(self):
        super().__init__()
        self.transcription_service = TranscriptionService()
        self.db = NotesDatabase()
        self.transcription_thread = None
        self.current_file_path = ""
        self.current_project_id = None
        self.current_transcription = {}  # Store full transcription result
        
        # Audio playback state
        self.is_playing = False
        self.is_paused = False
        self.audio_duration = 0.0
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_playback_progress)
        self.playback_start_time = 0
        
        # Initialize pygame mixer with better settings for compatibility
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.init()
            print("Audio system initialized successfully")
        except Exception as e:
            print(f"Audio initialization warning: {e}")
            # Try fallback initialization
            try:
                pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
                print("Audio system initialized with fallback settings")
            except Exception as e2:
                print(f"Audio initialization failed: {e2}")
        
        # Theme monitoring
        self.current_system_theme = None
        self.theme_check_timer = QTimer()
        self.theme_check_timer.timeout.connect(self.check_theme_changes)
        self.theme_check_timer.start(5000)  # Check every 5 seconds
        
        # Store references to themed buttons for refresh
        self.themed_buttons = []
        
        # Study mode state
        self.study_mode_active = False
        
        # Initialize translation system
        from app.utils.translation_manager import get_translation_manager
        self.translation_manager = get_translation_manager()
        
        self.setup_window()
        self.setup_ui()
        self.create_menu()
        self.apply_futuristic_theme()
        self.connect_signals()
        
        # Apply initial translations
        self.retranslate_ui()
        
        # Initialize sidebar manager after UI is set up
        self.sidebar_manager = SidebarManager(
            all_sentences_provider=lambda: [ann['text'] for ann in self.waveform_widget.annotations if ann.get('is_transcription')]
        )
        self.sidebar_manager.current_sidebar = None
        
        # Add sidebar to splitter (initially hidden)
        self.main_splitter.addWidget(self.sidebar_manager)
        self.main_splitter.setCollapsible(0, False)  # Waveform container not collapsible
        self.main_splitter.setCollapsible(1, True)   # Sidebar collapsible
        self.main_splitter.setSizes([self.width() - 400, 400])       # Initial size with sidebar visible
        self.main_splitter.setStretchFactor(0, 1) # Main content should expand
        self.main_splitter.setStretchFactor(1, 0) # Sidebar should not expand initially
        
        # Set minimum width for sidebar to prevent it from disappearing when resized
        self.sidebar_manager.setMinimumWidth(250)  # Minimum usable width for sidebar
        
        # COMPLETELY HIDE the splitter handle while maintaining resize functionality
        self.main_splitter.setHandleWidth(0)
        
        # Load model after UI is ready
        self.load_model()
        
        # Initial theme detection and icon setup
        self.refresh_all_button_themes()
        
        # Ensure overlay is positioned correctly after UI is fully loaded
        QTimer.singleShot(200, self.position_scale_overlay)
        
    def setup_window(self):
        """Configure main window properties with futuristic styling."""
        self.setWindowTitle("Audio Transcriber")
        self.setMinimumSize(900, 700)
        self.resize(1100, 800)
        
        # Set window flags for modern appearance
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | 
                           Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint)
        
    def create_menu(self):
        """Create the main menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        self.file_menu = menu_bar.addMenu("&" + self.translation_manager.translate("menu.file"))

        self.open_action = self.file_menu.addAction(self.translation_manager.translate("menu.file_actions.open_project"))
        self.open_action.triggered.connect(self.open_project)

        self.save_action = self.file_menu.addAction(self.translation_manager.translate("menu.file_actions.save"))
        self.save_action.triggered.connect(self.save_project)

        self.save_as_action = self.file_menu.addAction(self.translation_manager.translate("menu.file_actions.save_as"))
        self.save_as_action.triggered.connect(self.save_project_as)

        self.file_menu.addSeparator()

        self.exit_action = self.file_menu.addAction(self.translation_manager.translate("menu.exit"))
        self.exit_action.triggered.connect(self.close)
        
        # Settings menu
        self.settings_menu = menu_bar.addMenu("&" + self.translation_manager.translate("menu.settings"))
        
        # Language submenu
        self.language_menu = self.settings_menu.addMenu(self.translation_manager.translate("menu.language"))
        self.create_language_submenu()
        
        # Add separator
        self.settings_menu.addSeparator()
        
        # Model Settings action
        self.model_settings_action = self.settings_menu.addAction(self.translation_manager.translate("menu.model_settings"))
        self.model_settings_action.triggered.connect(self.open_model_settings)

    def create_language_submenu(self):
        """Create the language submenu with available languages."""
        
        # Create action group for exclusive language selection
        self.language_action_group = QActionGroup(self)
        self.language_actions = {}
        
        # Get available languages from translation manager
        available_languages = self.translation_manager.get_available_languages()
        current_language = self.translation_manager.current_language
        
        for lang_code, lang_name in available_languages.items():
            action = self.language_menu.addAction(lang_name)
            action.setCheckable(True)
            action.setChecked(lang_code == current_language)
            action.triggered.connect(lambda checked, code=lang_code: self.change_language(code))
            
            # Add to action group for exclusive selection
            self.language_action_group.addAction(action)
            self.language_actions[lang_code] = action

    def change_language(self, language_code):
        """Change the application language."""
        from app.setup.system_checker import ConfigManager
        try:
            # Set the new language
            self.translation_manager.set_language(language_code)

            # Save the new language to config
            config_manager = ConfigManager()
            config_manager.set_language(language_code)
            
            # Update the UI translations
            self.retranslate_ui()
            
            # Update language submenu
            self.update_language_submenu()
            
            # Show success message
            lang_name = self.translation_manager.get_available_languages()[language_code]
            message = self.translation_manager.translate("settings.language_changed", language=lang_name)
            
            # You could show a status message here if desired
            print(f"Language changed to: {lang_name}")
            
        except Exception as e:
            print(f"Error changing language: {e}")

    def open_model_settings(self):
        """Open the model settings dialog (welcome screen)."""
        try:
            from app.setup.welcome_screen import ModernSetupDialog
            
            # Create and show the model settings dialog
            model_settings_dialog = ModernSetupDialog()
            model_settings_dialog.setWindowTitle(self.translation_manager.translate("menu.model_settings"))
            
            # Show the dialog
            model_settings_dialog.exec()
            
        except Exception as e:
            print(f"Error opening model settings: {e}")

    def update_language_submenu(self):
        """Update the language submenu to reflect current selection."""
        current_language = self.translation_manager.current_language
        
        # Update checkmarks
        for lang_code, action in self.language_actions.items():
            action.setChecked(lang_code == current_language)
        
        # Update submenu title
        if hasattr(self, 'language_menu'):
            self.language_menu.setTitle(self.translation_manager.translate("menu.language"))

    def retranslate_ui(self):
        """Retranslate all UI elements."""
        tm = self.translation_manager
        
        # Update window title
        self.setWindowTitle(tm.translate("app.title"))
        
        # Update tooltips
        if hasattr(self, 'transcribe_button'):
            self.transcribe_button.setToolTip(tm.translate("buttons.transcribe"))
        if hasattr(self, 'browse_button'):
            self.browse_button.setToolTip(tm.translate("buttons.browse"))
        if hasattr(self, 'play_pause_button'):
            self.play_pause_button.setToolTip(tm.translate("buttons.play_pause"))
        if hasattr(self, 'copy_button'):
            self.copy_button.setToolTip(tm.translate("buttons.copy"))
        if hasattr(self, 'plus_button'):
            self.plus_button.setToolTip(tm.translate("tooltips.add_note"))
        if hasattr(self, 'clear_button'):
            self.clear_button.setToolTip(tm.translate("buttons.clear"))
        
        # Update file path placeholder
        if hasattr(self, 'file_path_edit'):
            self.file_path_edit.setPlaceholderText(tm.translate("transcription.select_file"))
        
        # Update menu items
        self.update_menu_translations()

    def update_menu_translations(self):
        """Update menu item translations."""
        tm = self.translation_manager
        
        # Update menu titles
        if hasattr(self, 'file_menu'):
            self.file_menu.setTitle("&" + tm.translate("menu.file"))
        if hasattr(self, 'settings_menu'):
            self.settings_menu.setTitle("&" + tm.translate("menu.settings"))
        
        # Update File menu actions
        if hasattr(self, 'open_action'):
            self.open_action.setText(tm.translate("menu.file_actions.open_project"))
        if hasattr(self, 'save_action'):
            self.save_action.setText(tm.translate("menu.file_actions.save"))
        if hasattr(self, 'save_as_action'):
            self.save_as_action.setText(tm.translate("menu.file_actions.save_as"))
        if hasattr(self, 'exit_action'):
            self.exit_action.setText(tm.translate("menu.exit"))
        
        # Update Settings menu actions
        if hasattr(self, 'model_settings_action'):
            self.model_settings_action.setText(tm.translate("menu.model_settings"))
        
        # Update language submenu
        self.update_language_submenu()

    def setup_ui(self):
        """Create and arrange UI components with waveform as the dominant element."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with no spacing or margins for full window coverage
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create horizontal splitter for main content
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Main content: Waveform (takes full space)
        waveform_container = QWidget()
        waveform_layout = QVBoxLayout(waveform_container)
        waveform_layout.setContentsMargins(0, 0, 0, 0)
        
        # DOMINANT WAVEFORM - takes most of the space
        self.waveform_widget = AudioWaveformWidget()
        self.waveform_widget.setMinimumHeight(300)  # Reduced minimum height
        self.waveform_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Connect the notes database to the waveform widget
        self.waveform_widget.notes_db = self.db

        # Scroll area for the waveform
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.waveform_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Apply modern flat scrollbar styling
        self.apply_modern_scrollbar_style()
        waveform_layout.addWidget(self.scroll_area)
        
        # Give the waveform widget access to the scroll area for auto-scrolling
        self.waveform_widget.scroll_area = self.scroll_area
        
        # Create scale control overlay that stays fixed in position
        from app.utils.app_utils import ScaleControlOverlay
        self.scale_overlay = ScaleControlOverlay(self.waveform_widget, waveform_container)
        self.scale_overlay.show()
        
        # Position the overlay in the bottom right corner after UI is ready
        QTimer.singleShot(100, self.position_scale_overlay)
        
        # Add waveform container to splitter
        self.main_splitter.addWidget(waveform_container)
        
        main_layout.addWidget(self.main_splitter, 1)
        
        # Compact file selection
        self.create_compact_file_section(main_layout)
        
        # Bottom control buttons (small)
        self.create_bottom_controls(main_layout)
        


        
    def position_scale_overlay(self):
        """Position the scale control overlay in the bottom right corner of the waveform container."""
        if hasattr(self, 'scale_overlay') and hasattr(self, 'scroll_area'):
            # Get the waveform container (parent of scroll area) size
            waveform_container = self.scroll_area.parent()
            if waveform_container and waveform_container.width() > 0:
                container_rect = waveform_container.rect()
                
                # Position overlay in bottom right corner with smaller margin
                margin = 8
                overlay_x = max(0, container_rect.width() - self.scale_overlay.width() - margin)
                overlay_y = max(0, container_rect.height() - self.scale_overlay.height() - margin)
                
                # Move the overlay to the correct position
                self.scale_overlay.move(overlay_x, overlay_y)
            else:
                # Retry positioning after a short delay if container not ready
                QTimer.singleShot(50, self.position_scale_overlay)
    
    def resizeEvent(self, event):
        """Handle window resize to reposition the scale overlay immediately."""
        super().resizeEvent(event)
        # Position overlay immediately for smooth, real-time positioning
        self.position_scale_overlay()

    def create_compact_header(self, parent_layout):
        """Create a minimal header."""
        header_layout = QHBoxLayout()
        
        # Spacer to maintain layout
        header_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        parent_layout.addLayout(header_layout)
        parent_layout.addSpacing(10)
        

    def create_compact_file_section(self, parent_layout):
        """Create compact file selection with padding."""
        # Create a container widget for the file section with padding
        file_container = QWidget()
        file_container_layout = QVBoxLayout(file_container)
        file_container_layout.setContentsMargins(15, 0, 15, 10)  # Add padding to match icons
        file_container_layout.setSpacing(0)
        
        file_layout = QHBoxLayout()
        
        self.file_path_edit = ModernGlassLineEdit("Select an audio file...")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setMaximumHeight(35)
        
        file_layout.addWidget(self.file_path_edit)
        
        file_container_layout.addLayout(file_layout)
        parent_layout.addWidget(file_container)
        
    def create_bottom_controls(self, parent_layout):
        """Create small control buttons at the bottom with padding."""
        # Create a container widget for the controls with padding
        controls_container = QWidget()
        controls_container_layout = QVBoxLayout(controls_container)
        controls_container_layout.setContentsMargins(15, 10, 15, 15)  # Add padding only here
        controls_container_layout.setSpacing(0)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # Transcription button FIRST (most important action)
        icon_dir = os.path.join(os.path.dirname(__file__), "..", "..", "icons")
        self.transcribe_button = ModernGlassButton("", primary=True, icon_path=os.path.join(icon_dir, "ai.svg"))
        self.transcribe_button.setEnabled(False)
        self.transcribe_button.setMaximumHeight(35)
        self.transcribe_button.setToolTip(self.translation_manager.translate("tooltips.transcribe_audio"))
        controls_layout.addWidget(self.transcribe_button)
        
        # Browse button
        self.browse_button = ModernGlassButton("", icon_path=os.path.join(icon_dir, "browse.svg"))
        self.browse_button.setMaximumHeight(35)
        self.browse_button.setToolTip(self.translation_manager.translate("tooltips.browse_for_audio_file"))
        controls_layout.addWidget(self.browse_button)
        
        # Play/Pause button
        self.play_pause_button = ModernGlassButton("", icon_path=os.path.join(icon_dir, "play.svg"))
        self.play_pause_button.setEnabled(False)
        self.play_pause_button.setMaximumHeight(35)

        self.play_pause_button.setToolTip(self.translation_manager.translate("tooltips.play_pause_audio"))
        controls_layout.addWidget(self.play_pause_button)
        
        # Time label (centered, larger text, current time only)
        self.time_label = ModernStatusLabel("00:00")
        self.time_label.setMaximumHeight(35)
        self.time_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 0 20px;
            }
        """)
        controls_layout.addWidget(self.time_label)
        
        # Spacer
        controls_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Copy button
        self.copy_button = ModernGlassButton("", icon_path=os.path.join(icon_dir, "copy.svg"))
        self.copy_button.setEnabled(False)
        self.copy_button.setMaximumHeight(35)

        self.plus_button = ModernGlassButton("", icon_path=os.path.join(icon_dir, "book.svg"))
        self.plus_button.setMaximumHeight(35)
        self.plus_button.setToolTip(self.translation_manager.translate("tooltips.add_note"))
        self.copy_button.setToolTip(self.translation_manager.translate("tooltips.copy_transcription"))
        controls_layout.addWidget(self.copy_button)
        controls_layout.addWidget(self.plus_button)
        
        # Clear button
        self.clear_button = ModernGlassButton("", icon_path=os.path.join(icon_dir, "clear.svg"))
        self.clear_button.setMaximumHeight(35)
        self.clear_button.setToolTip(self.translation_manager.translate("tooltips.clear_all"))
        controls_layout.addWidget(self.clear_button)
        
        controls_container_layout.addLayout(controls_layout)
        parent_layout.addWidget(controls_container)

        
    def connect_signals(self):
        """Connect all UI element signals to their respective slots."""
        self.browse_button.clicked.connect(self.browse_for_file)
        self.transcribe_button.clicked.connect(self.start_transcription)
        self.play_pause_button.clicked.connect(self.toggle_playback)
        self.copy_button.clicked.connect(self.copy_transcription)
        self.clear_button.clicked.connect(self.clear_all)
        self.plus_button.clicked.connect(self.toggle_study_mode)  # Connect book button to study mode toggle
        self.waveform_widget.playback_position_changed.connect(self.seek_audio)
        self.waveform_widget.scrubbing_position_changed.connect(self.scrub_audio)
        self.waveform_widget.note_requested.connect(self.show_notes_sidebar)
        
        # Connect splitter resize signal for immediate scale overlay repositioning
        self.main_splitter.splitterMoved.connect(self.position_scale_overlay)

    def apply_futuristic_theme(self):
        """Apply a dark, futuristic theme with glassmorphism."""
        theme = detect_system_theme()
        self.current_system_theme = theme
        
        if theme == 'dark':
            bg_color = QColor(20, 20, 30)
            text_color = QColor(220, 220, 255)
            base_color = QColor(30, 30, 45)
            highlight_color = QColor(0, 191, 255)
        else: # light theme
            bg_color = QColor(240, 240, 245)
            text_color = QColor(20, 20, 30)
            base_color = QColor(255, 255, 255)
            highlight_color = QColor(0, 122, 255)

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {bg_color.name()};
                color: {text_color.name()};
                font-family: 'Inter', sans-serif;
            }}
            QProgressBar {{
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                background-color: rgba(0, 0, 0, 0.2);
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {highlight_color.name()};
                border-radius: 4px;
            }}
        """)
        
        # Refresh button icons for the new theme
        self.refresh_all_button_themes()

    def refresh_all_button_themes(self):
        """Refresh all ModernGlassButton icons and styles."""
        theme = detect_system_theme()
        buttons_to_update = [self.transcribe_button, self.browse_button, 
                             self.play_pause_button, self.copy_button, self.clear_button, self.plus_button]
        
        for button in buttons_to_update:
            if hasattr(button, 'update_theme'):
                button.update_theme(theme)

    def apply_modern_scrollbar_style(self):
        """Apply very thin flat scrollbar styling with round borders."""
        theme = detect_system_theme()
        
        if theme == 'dark':
            bg_color = "rgba(30, 30, 40, 0.3)"
            handle_color = "rgba(80, 80, 100, 0.7)"
            handle_hover = "rgba(100, 100, 120, 0.9)"
            handle_pressed = "rgba(0, 191, 255, 0.8)"
            border_color = "rgba(60, 60, 80, 0.4)"
        else:
            bg_color = "rgba(250, 250, 255, 0.3)"
            handle_color = "rgba(200, 200, 210, 0.7)"
            handle_hover = "rgba(180, 180, 190, 0.9)"
            handle_pressed = "rgba(0, 122, 255, 0.8)"
            border_color = "rgba(220, 220, 230, 0.4)"
        
        scrollbar_style = f"""
            QScrollBar:vertical {{
                background: {bg_color};
                width: 6px;
                border: 1px solid {border_color};
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {handle_color};
                border: 1px solid {border_color};
                border-radius: 3px;
                min-height: 20px;
                margin: 1px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover};
                border: 1px solid {handle_hover};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {handle_pressed};
                border: 1px solid {handle_pressed};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
            
            QScrollBar:horizontal {{
                background: {bg_color};
                height: 6px;
                border: 1px solid {border_color};
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {handle_color};
                border: 1px solid {border_color};
                border-radius: 3px;
                min-width: 20px;
                margin: 1px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {handle_hover};
                border: 1px solid {handle_hover};
            }}
            QScrollBar::handle:horizontal:pressed {{
                background: {handle_pressed};
                border: 1px solid {handle_pressed};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """
        
        self.scroll_area.setStyleSheet(scrollbar_style)

    def check_theme_changes(self):
        """Periodically check for system theme changes."""
        new_theme = detect_system_theme()
        if new_theme != self.current_system_theme:
            print(f"System theme changed to {new_theme}. Applying new theme.")
            self.apply_futuristic_theme()
            # Update scrollbar styling for new theme
            self.apply_modern_scrollbar_style()

    def browse_for_file(self):
        """Open a file dialog to select an audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translation_manager.translate("transcription.select_file"),
            os.path.expanduser("~"),
            "Audio Files (*.wav *.mp3 *.m4a *.flac)"
        )
        if file_path:
            self.load_audio_file(file_path)

    def load_audio_file(self, file_path):
        """Load the selected audio file and prepare for transcription."""
        self.current_file_path = file_path
        self.file_path_edit.setText(os.path.basename(file_path))
        self.transcribe_button.setEnabled(True)
        self.play_pause_button.setEnabled(True)
        self.copy_button.setEnabled(False)

        try:
            pygame.mixer.music.load(self.current_file_path)
            # Get audio duration
            import soundfile as sf
            with sf.SoundFile(self.current_file_path) as f:
                self.audio_duration = f.frames / f.samplerate
            self.update_time_label(0)
            
            # Load waveform data
            self.waveform_widget.load_audio(self.current_file_path)
            self.waveform_widget.set_audio_duration(self.audio_duration)
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                self.translation_manager.translate("dialogs.error"), 
                self.translation_manager.translate("messages.audio_load_error").format(str(e))
            )
            self.clear_all()

    def load_model(self):
        """Load the Whisper model asynchronously."""
        def on_model_loaded(success, message):
            if success:
                pass  # Model loaded successfully
            else:
                print(f"Model load failed - {message}")
        
        self.transcription_service.load_model_async(on_model_loaded)

    def start_transcription(self):
        """Begin the transcription process."""
        if not self.current_file_path:
            QMessageBox.warning(
                self, 
                self.translation_manager.translate("dialogs.warning"), 
                self.translation_manager.translate("messages.no_audio_file")
            )
            return

        if self.transcription_thread and self.transcription_thread.isRunning():
            QMessageBox.warning(self, "Warning", "Transcription is already in progress.")
            return

        # Start primary button animation
        self.transcribe_button.start_border_animation()

        self.transcribe_button.setEnabled(False)
        self.play_pause_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.browse_button.setEnabled(False)

        self.transcription_thread = TranscriptionThread(self.transcription_service.model, self.current_file_path)
        self.transcription_thread.transcription_done.connect(self.on_transcription_finished)
        self.transcription_thread.error_occurred.connect(self.on_transcription_error)
        self.transcription_thread.start()

    def on_transcription_finished(self, result):
        """Handle the completion of the transcription."""
        # Stop primary button animation
        self.transcribe_button.stop_border_animation()
        
        self.current_transcription = result  # Store full result
        self.display_transcription_results(result)

        self.transcribe_button.setEnabled(True)
        self.play_pause_button.setEnabled(True)
        self.copy_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.browse_button.setEnabled(True)

    def copy_transcription(self):
        """Copy transcription text to clipboard with cross-platform compatibility."""
        # Try to get transcription text from multiple sources for robustness
        text_to_copy = ""
        
        # First, try current_transcription (primary source)
        if hasattr(self, 'current_transcription') and self.current_transcription:
            if isinstance(self.current_transcription, dict):
                text_to_copy = self.current_transcription.get('text', '')
            else:
                text_to_copy = str(self.current_transcription)
        
        # Fallback to last_transcription_result if current_transcription is empty
        if not text_to_copy and hasattr(self, 'last_transcription_result') and self.last_transcription_result:
            if isinstance(self.last_transcription_result, dict):
                text_to_copy = self.last_transcription_result.get('text', '')
            else:
                text_to_copy = str(self.last_transcription_result)
        
        # Check if we have any text to copy
        if not text_to_copy or text_to_copy.strip() == "":
            QMessageBox.warning(
                self, 
                self.translation_manager.translate("dialogs.warning"), 
                self.translation_manager.translate("messages.nothing_to_copy")
            )
            return
        
        try:
            # Get the system clipboard
            clipboard = QApplication.clipboard()
            
            # Clear clipboard first (helps with some cross-platform issues)
            clipboard.clear()
            
            # Set text to clipboard with multiple modes for better compatibility
            clipboard.setText(text_to_copy, QClipboard.Mode.Clipboard)
            
            # Also set to selection clipboard on Linux systems
            if clipboard.supportsSelection():
                clipboard.setText(text_to_copy, QClipboard.Mode.Selection)
            
            # Verify the copy operation worked
            if clipboard.text(QClipboard.Mode.Clipboard) == text_to_copy:
                # Show success message
                QMessageBox.information(
                    self, 
                    self.translation_manager.translate("dialogs.success"), 
                    self.translation_manager.translate("messages.transcription_copied")
                )
                # Also update status label if it exists
                if hasattr(self, 'status_label'):
                    self.status_label.setText(self.translation_manager.translate("messages.transcription_copied"))
            else:
                # Fallback: try basic setText without mode specification
                clipboard.setText(text_to_copy)
                QMessageBox.information(
                    self, 
                    self.translation_manager.translate("dialogs.success"), 
                    self.translation_manager.translate("messages.transcription_copied")
                )
                
        except Exception as e:
            # Handle any clipboard errors
            QMessageBox.critical(
                self, 
                self.translation_manager.translate("dialogs.error"), 
                f"Failed to copy to clipboard: {str(e)}"
            )

    def display_transcription_results(self, result):
        """Display transcription results in the waveform widget."""
        # Update waveform with segments
        segments = result.get('segments', [])
        self.waveform_widget.set_transcription_segments(segments)

        # Store the result for potential sidebar use
        self.last_transcription_result = result

        self.transcribe_button.setEnabled(True)
        self.play_pause_button.setEnabled(True)
        self.copy_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.browse_button.setEnabled(True)

    def on_transcription_error(self, error_message):
        """Handle transcription errors."""
        # Stop primary button animation
        self.transcribe_button.stop_border_animation()
        
        # Re-enable buttons
        self.transcribe_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.browse_button.setEnabled(True)

        # Show error message
        QMessageBox.critical(self, "Transcription Error", f"An error occurred during transcription:\n{error_message}")

    def toggle_playback(self):
        """Toggle between play and pause states."""
        if not self.current_file_path:
            return

        if self.is_playing and not self.is_paused:
            # Pause playback
            pygame.mixer.music.pause()
            self.is_paused = True
            self.playback_timer.stop()
            self.waveform_widget.stop_animation()
            
            # Update icon to play button
            self.play_pause_button.icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "play.svg")
            self.play_pause_button.update_icon()
            
        elif self.is_paused:
            # Resume playback
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.playback_timer.start(50)
            self.waveform_widget.start_animation("playing")
            
            # Update icon to pause button
            self.play_pause_button.icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "pause.svg")
            self.play_pause_button.update_icon()
            
        else:
            # Start playback from current white line position
            try:
                current_position = self.waveform_widget.progress * self.audio_duration
                
                # Ensure we have a valid file
                if not self.current_file_path or not os.path.exists(self.current_file_path):
                    return
                    
                pygame.mixer.music.load(self.current_file_path)
                pygame.mixer.music.play(start=current_position)
                
                # Update internal tracking
                self.playback_start_time = time.time() - current_position
                
                self.is_playing = True
                self.is_paused = False
                self.playback_timer.start(50)
                self.waveform_widget.start_animation("playing")
                
                # Update icon to pause button
                self.play_pause_button.icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "pause.svg")
                self.play_pause_button.update_icon()
                
            except pygame.error as e:
                print(f"Pygame error starting playback: {e}")
                # Fallback to beginning
                try:
                    pygame.mixer.music.load(self.current_file_path)
                    pygame.mixer.music.play()
                    self.playback_start_time = time.time()
                except Exception as e2:
                    print(f"Fallback error: {e2}")
            except Exception as e:
                print(f"Error starting playback: {e}")

    def update_playback_progress(self):
        """Update the time label and white line position during playback."""
        if pygame.mixer.music.get_busy() and self.audio_duration > 0:
            elapsed_time = time.time() - self.playback_start_time
            # Ensure elapsed time doesn't exceed audio duration
            elapsed_time = min(elapsed_time, self.audio_duration)
            self.update_time_label(elapsed_time)
            # Update the white line position for smooth movement
            self.waveform_widget.set_playback_position(elapsed_time)
        else:
            self.playback_timer.stop()
            self.is_playing = False
            self.is_paused = False
            # Update icon path and refresh themed icon
            self.play_pause_button.icon_path = os.path.join(os.path.dirname(__file__), "icons", "play.svg")
            self.play_pause_button.update_icon()
            # Reset to beginning when playback ends
            self.update_time_label(0)
            self.waveform_widget.set_playback_position(0)

    def seek_audio(self, position_ratio):
        """Seek to a specific position in the audio and stop playback."""
        if self.audio_duration > 0:
            seek_time_sec = self.audio_duration * position_ratio
            
            # Stop current playback
            pygame.mixer.music.stop()
            
            # Reset scrubbing state
            if hasattr(self, 'is_scrubbing'):
                self.is_scrubbing = False
            
            # Update the time display and waveform position
            self.update_time_label(seek_time_sec)
            self.waveform_widget.set_playback_position(seek_time_sec)
            
            # Set the playback position for future play operations
            self.playback_start_time = time.time() - seek_time_sec
            
            # Stop playback state
            self.is_playing = False
            self.is_paused = False
            
            # Update icon to play button
            self.play_pause_button.icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "play.svg")
            self.play_pause_button.update_icon()
            
            # Stop playback timer and waveform animation
            self.playback_timer.stop()
            self.waveform_widget.stop_animation()

    def scrub_audio(self, position_ratio):
        """Play audio continuously at the scrubbed position during dragging."""
        if self.audio_duration > 0:
            seek_time_sec = self.audio_duration * position_ratio
            
            # Ensure we have a valid file loaded
            if not self.current_file_path or not os.path.exists(self.current_file_path):
                return
                
            try:
                # Stop current playback first
                pygame.mixer.music.stop()
                
                # Load the file
                pygame.mixer.music.load(self.current_file_path)
                
                # Seek to the correct position using pygame's built-in seeking
                pygame.mixer.music.play(start=seek_time_sec)
                
                # Update the time display and waveform position
                self.update_time_label(seek_time_sec)
                self.waveform_widget.set_playback_position(seek_time_sec)
                
                # Update internal tracking
                self.playback_start_time = time.time() - seek_time_sec
                
                # Set playing state
                self.is_playing = True
                self.is_paused = False
                
                # Update icon to pause button
                self.play_pause_button.icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "pause.svg")
                self.play_pause_button.update_icon()
                
                # Start waveform animation and playback timer
                self.waveform_widget.start_animation("playing")
                self.playback_timer.start(50)
                
            except pygame.error as e:
                print(f"Pygame error during scrubbing: {e}")
                # Fallback: restart from beginning
                try:
                    pygame.mixer.music.load(self.current_file_path)
                    pygame.mixer.music.play()
                    self.playback_start_time = time.time()
                except Exception as e2:
                    print(f"Fallback error: {e2}")
            except Exception as e:
                print(f"Error during scrubbing: {e}")

    def update_time_label(self, current_time):
        """Update the time display label to show only current time."""
        current_seconds = int(current_time)
        current_str = f"{current_seconds // 60:02d}:{current_seconds % 60:02d}"
        self.time_label.setText(current_str)

    def save_project(self):
        """Save the current project."""
        if self.current_project_id:
            notes = self.sidebar_manager.get_all_notes()
            self.db.save_transcription_and_notes(
                self.current_project_id,
                self.current_transcription,
                notes
            )
            QMessageBox.information(
                self, 
                self.translation_manager.translate("dialogs.success"), 
                self.translation_manager.translate("messages.project_saved")
            )
        else:
            self.save_project_as()

    def save_project_as(self):
        """Save the current work as a new project."""
        dialog = ProjectDialog(None, self)
        if dialog.exec():
            project_name = dialog.get_new_project_name()
            if project_name:
                self.current_project_id = self.db.create_project(project_name, self.current_file_path)
                self.save_project()

    def open_project(self):
        """Open an existing project."""
        print("DEBUG: open_project called - fetching fresh projects from database")
        projects = self.db.get_all_projects()
        print(f"DEBUG: Retrieved {len(projects)} projects from database")
        
        if not projects:
            QMessageBox.information(
                self, 
                self.translation_manager.translate("dialogs.info"), 
                self.translation_manager.translate("messages.no_projects")
            )
            return

        self.project_dialog = ProjectDialog(projects, self)
        self.project_dialog.project_deleted.connect(self.on_project_deleted_refresh)
        
        if self.project_dialog.exec():
            project_id = self.project_dialog.get_selected_project()
            if project_id:
                audio_filepath, transcription, notes = self.db.load_project_data(project_id)

                if audio_filepath:
                    self.current_project_id = project_id
                    self.load_audio_file(audio_filepath)
                    self.current_transcription = transcription
                    self.display_transcription_results(transcription)
                    self.sidebar_manager.load_notes(notes)
                else:
                    QMessageBox.warning(
                        self, 
                        self.translation_manager.translate("dialogs.error"), 
                        self.translation_manager.translate("messages.project_load_error")
                    )
    
    def on_project_deleted_refresh(self, project_id):
        """Close and reopen the project dialog to refresh the list."""
        # If the currently loaded project was deleted, clear the interface
        if self.current_project_id == project_id:
            self.clear_all()
            self.current_project_id = None
            self.current_transcription = None
            self.sidebar_manager.close_all_sidebars()

        # Close the current dialog
        self.project_dialog.close()
        
        # Reopen the dialog after a short delay to ensure it's refreshed
        QTimer.singleShot(100, self.open_project)

    def on_project_deleted(self, project_id):
        """Handle project deletion notification from dialog."""
        # If the currently loaded project was deleted, clear the interface
        if self.current_project_id == project_id:
            self.clear_all()
            self.current_project_id = None
            self.current_transcription = None
            self.sidebar_manager.close_all_sidebars()
        
        # Optionally show a notification
        print(f"Project {project_id} was deleted successfully")

    def on_transcription_error(self, error_message):
        """Handle transcription errors."""
        # Re-enable buttons
        self.transcribe_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.browse_button.setEnabled(True)



    def clear_all(self):
        """Clear all data and reset the interface."""
        self.current_file_path = None
        self.file_path_edit.clear()
        self.transcribe_button.setEnabled(False)
        self.play_pause_button.setEnabled(False)
        self.copy_button.setEnabled(False)
        
        # Stop any playing audio
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False

    def toggle_study_mode(self):
        """Toggle study mode on/off."""
        if not self.current_transcription:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, 
                self.translation_manager.translate("dialogs.info"), 
                "Please transcribe audio first to use study mode."
            )
            return
            
        if self.study_mode_active:
            self.deactivate_study_mode()
        else:
            self.activate_study_mode()
    
    def activate_study_mode(self):
        """Activate study mode."""
        # Update button appearance for active state
        self.update_study_mode_button_appearance(True)
        
        # Set study mode active
        self.study_mode_active = True
        
        # Update tooltip
        self.plus_button.setToolTip("Exit Study Mode")
        
        # Update sidebar manager to use study mode
        self.sidebar_manager.set_study_mode(True)
    
    def deactivate_study_mode(self):
        """Deactivate study mode."""
        if not self.study_mode_active:
            return
            
        # Update button appearance for inactive state
        self.update_study_mode_button_appearance(False)
        
        # Set study mode inactive
        self.study_mode_active = False
        
        # Update tooltip
        self.plus_button.setToolTip(self.translation_manager.translate("tooltips.study_mode"))
        
        # Update sidebar manager to disable study mode
        self.sidebar_manager.set_study_mode(False)
    
    def update_study_mode_button_appearance(self, active: bool):
        """Update the study mode button appearance."""
        if active:
            # White background, black icon - EXACT same size as other buttons
            self.plus_button.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.9);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 8px;
                    color: #CCCCCC;
                    font-weight: 500;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 1.0);
                    border-color: rgba(255, 255, 255, 0.5);
                }
                QPushButton:pressed {
                    background: rgba(240, 240, 240, 1.0);
                }
            """)
            # Update icon to black version if needed
            if hasattr(self.plus_button, 'update_icon_color'):
                self.plus_button.update_icon_color('black')
        else:
            # Reset to normal ModernGlassButton appearance - reapply the default styling
            if hasattr(self.plus_button, 'apply_style'):
                self.plus_button.apply_style()
            # Restore the theme-appropriate icon
            if hasattr(self.plus_button, 'refresh_theme'):
                self.plus_button.refresh_theme()

    def show_notes_sidebar(self, sentence_id=None, text=None, note_text=None, start_time=None, end_time=None, bubble_rect=None):
        """Show the notes sidebar with specific sentence from bubble click."""
        if not self.current_transcription and not text:
            QMessageBox.information(
                self, 
                self.translation_manager.translate("dialogs.info"), 
                self.translation_manager.translate("messages.transcribe_first")
            )
            return
        
        # Use the provided text from bubble click
        sentence = text if text else self.get_current_sentence()
        
        # Show sidebar with the specific sentence
        # In study mode, start fresh conversations without loading previous chat history
        fresh_conversation = self.study_mode_active
        self.sidebar_manager.show_sidebar(sentence, timestamp=start_time, fresh_conversation=fresh_conversation)
        
        # If there's existing note text, load it
        if note_text and self.sidebar_manager.current_sidebar:
            self.sidebar_manager.current_sidebar.editor.set_content(note_text)
        
        # Connect close signal if not already connected
        if self.sidebar_manager.current_sidebar:
            self.sidebar_manager.current_sidebar.closed.connect(self.hide_sidebar)
        
        # Adjust splitter to show sidebar
        self.main_splitter.setSizes([self.width() - 400, 400])
        
        # Reposition scale overlay after UI has updated
        QTimer.singleShot(50, self.position_scale_overlay)
    
    def get_current_sentence(self) -> str:
        """Get the current sentence for the sidebar title."""
        if not self.current_transcription:
            return "No transcription available"
        
        # Handle both string and dictionary transcription formats
        if isinstance(self.current_transcription, dict):
            text = self.current_transcription.get('text', '')
        else:
            text = str(self.current_transcription)
        
        if not text:
            return "No transcription available"
        
        # Take the first sentence or first 100 characters
        text = text.strip()
        
        # Try to find the first sentence
        import re
        sentences = re.split(r'[.!?]+', text)
        if sentences and len(sentences[0].strip()) > 0:
            first_sentence = sentences[0].strip()
            # Limit length to avoid very long titles
            if len(first_sentence) > 100:
                return first_sentence[:97] + "..."
            return first_sentence
        
        # Fallback to first 100 characters
        if len(text) > 100:
            return text[:97] + "..."
        return text
    
    def hide_sidebar(self):
        """Hide the sidebar and adjust splitter."""
        self.sidebar_manager.close_sidebar()
        self.main_splitter.setSizes([self.width(), 0])
        
        # Reposition scale overlay after UI has updated
        QTimer.singleShot(50, self.position_scale_overlay)

    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() == Qt.Key.Key_Space:
            # Only toggle playback if an audio file is loaded
            if self.current_file_path and self.play_pause_button.isEnabled():
                self.toggle_playback()
                event.accept()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Stop any running transcription threads
            if hasattr(self, 'transcription_thread') and self.transcription_thread and self.transcription_thread.isRunning():
                self.transcription_thread.quit()
                self.transcription_thread.wait(3000)  # Wait up to 3 seconds
                if self.transcription_thread.isRunning():
                    self.transcription_thread.terminate()
                    self.transcription_thread.wait(1000)  # Wait up to 1 second for termination
            
            # Stop audio playback
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except:
                pass
                
            # Clean up any other resources
            if hasattr(self, 'sidebar_manager'):
                self.sidebar_manager.close_sidebar()
                
            event.accept()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            event.accept()
        
        super().closeEvent(event)


# Entry point removed: launch the application via launcher.py