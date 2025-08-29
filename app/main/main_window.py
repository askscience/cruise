"""
Main Window Module

Contains the main application window class responsible for UI initialization,
layout management, and basic window operations.
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QColor
from PySide6.QtUiTools import QUiLoader

# Import application components
from app.components.sidebar_widget import SidebarManager
from app.services.database_manager import NotesDatabase
from app.utils.app_utils import detect_system_theme, create_themed_icon_pixmap
from app.utils.app_utils import AudioWaveformWidget, ScaleControlOverlay


class MainWindow(QMainWindow):
    """
    Main application window responsible for UI initialization and layout management.
    
    This class handles:
    - UI loading from .ui file
    - Window properties and appearance
    - Theme management
    - UI component setup and styling
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize theme monitoring
        self._init_theme_monitoring()
        
        # Setup UI from .ui file
        self._load_ui_from_file()
        
        # Setup application components
        self._setup_application_components()
        
        # Apply styling
        self._finalize_ui_setup()
    
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
        ui_file_path = Path(__file__).parent.parent.parent / "resources" / "ui" / "main_window.ui"
        loader = QUiLoader()
        
        # Load UI directly from file path
        self.ui = loader.load(str(ui_file_path), self)
        
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
        # Menu actions will be connected by the controller
        pass
    
    def _setup_application_components(self):
        """Setup application-specific components that require custom widgets."""
        # Initialize database
        self.db = NotesDatabase()
        
        # Replace placeholder widgets with custom components
        self._setup_waveform_widget()
        self._setup_custom_buttons()
        self._setup_sidebar_manager()
        self._setup_scale_overlay()
        
        # Configure splitter
        self._configure_splitter()
    
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
        icon_dir = Path(__file__).parent.parent.parent / "resources" / "icons"
        
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
        icon_path = Path(__file__).parent.parent.parent / "resources" / "icons" / icon_filename
        
        # Set the button as an attribute for easy access
        setattr(self, attr_name, button)
        
        # Apply icon if it exists
        if icon_path.exists():
            # Create themed icon
            pixmap = create_themed_icon_pixmap(str(icon_path), detect_system_theme())
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
    
    def _finalize_ui_setup(self):
        """Finalize UI setup."""
        # Load and apply stylesheet
        self._load_stylesheet()
        
        # Initial theme setup
        self.refresh_all_button_themes()
        
        # Position overlay
        QTimer.singleShot(200, self.position_scale_overlay)
    
    def _load_stylesheet(self):
        """Load and apply the external QSS stylesheet."""
        qss_file_path = Path(__file__).parent.parent.parent / "resources" / "styles" / "styles.qss"
        
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
    
    def refresh_all_button_themes(self):
        """Refresh all button icons and styles for theme changes."""
        theme = detect_system_theme()
        icon_dir = Path(__file__).parent.parent.parent / "resources" / "icons"
        
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
                icon_path = icon_dir / icon_filename
                if icon_path.exists():
                    pixmap = create_themed_icon_pixmap(str(icon_path), theme)
                    icon = QIcon(pixmap)
                    button.setIcon(icon)
    
    def check_theme_changes(self):
        """Check for system theme changes and update UI accordingly."""
        current_theme = detect_system_theme()
        if current_theme != self.current_system_theme:
            self.current_system_theme = current_theme
            self.setProperty("theme", current_theme)
            self.refresh_all_button_themes()
            # Reload stylesheet to apply theme changes
            self._load_stylesheet()
    
    def position_scale_overlay(self):
        """Position the scale control overlay in the bottom right corner."""
        if hasattr(self, 'scale_overlay') and hasattr(self, 'ui'):
            waveform_container = self.ui.waveform_container
            if waveform_container and waveform_container.width() > 0:
                overlay_width = 200
                overlay_height = 40
                margin = 20
                
                x = waveform_container.width() - overlay_width - margin
                y = waveform_container.height() - overlay_height - margin
                
                self.scale_overlay.setGeometry(x, y, overlay_width, overlay_height)
    
    def show_notes_sidebar(self):
        """Show the notes sidebar."""
        if hasattr(self, 'sidebar_manager'):
            self.sidebar_manager.show_notes_sidebar()