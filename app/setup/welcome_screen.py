"""
Welcome Screen Module
Provides initial setup interface for the transcriber application.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QDialog, QStackedWidget, QFrame,
                               QComboBox, QCheckBox, QProgressBar, QTextEdit, QGroupBox,
                               QScrollArea)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QPainter, QColor, QFont

from .system_checker import ConfigManager, SystemChecker
from .model_selection import ModelDownloadThread

# Import theme detection from app_utils
from app.utils.app_utils import detect_system_theme
from app.utils.translation_manager import tr


class ModernSetupDialog(QDialog):
    """Modern, flat setup dialog that combines welcome and model selection."""
    
    setup_completed = Signal()
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.system_checker = SystemChecker()
        self.download_thread = None
        
        self.setWindowTitle(tr("setup.title"))
        self.setFixedSize(600, 700)
        self.setModal(True)
        
        self.setup_ui()
        self.apply_modern_theme()
        self.check_system_status()
    
    def apply_modern_theme(self):
        """Apply modern flat theme."""
        theme = detect_system_theme()
        
        if theme == 'dark':
            bg_color = "#1e1e1e"
            card_bg = "#2d2d2d"
            text_color = "#ffffff"
            secondary_text = "#b3b3b3"
            border_color = "#404040"
            accent_color = "#0078d4"
            accent_hover = "#106ebe"
            input_bg = "#3c3c3c"
        else:
            bg_color = "#f5f5f5"
            card_bg = "#ffffff"
            text_color = "#1a1a1a"
            secondary_text = "#666666"
            border_color = "#e1e1e1"
            accent_color = "#0078d4"
            accent_hover = "#106ebe"
            input_bg = "#ffffff"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {text_color};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            
            QFrame[class="card"] {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
                padding: 0px;
            }}
            
            QLabel[class="title"] {{
                color: {text_color};
                font-size: 28px;
                font-weight: 300;
                margin: 0px;
                padding: 0px;
            }}
            
            QLabel[class="subtitle"] {{
                color: {secondary_text};
                font-size: 16px;
                font-weight: 400;
                margin: 0px;
                padding: 0px;
            }}
            
            QLabel[class="section-title"] {{
                color: {text_color};
                font-size: 18px;
                font-weight: 500;
                margin: 0px;
                padding: 0px;
            }}
            
            QLabel[class="description"] {{
                color: {secondary_text};
                font-size: 14px;
                font-weight: 400;
                margin: 0px;
                padding: 0px;
            }}
            
            QLabel[class="status"] {{
                font-size: 13px;
                font-weight: 500;
                margin: 0px;
                padding: 0px;
            }}
            
            QLabel[class="status-success"] {{
                color: #28a745;
            }}
            
            QLabel[class="status-error"] {{
                color: #dc3545;
            }}
            
            QPushButton[class="primary"] {{
                background-color: {accent_color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 28px;
                font-weight: 500;
                font-size: 15px;
                min-width: 120px;
            }}
            
            QPushButton[class="primary"]:hover {{
                background-color: {accent_hover};
            }}
            
            QPushButton[class="secondary"] {{
                background-color: transparent;
                color: {text_color};
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 12px 28px;
                font-weight: 500;
                font-size: 15px;
                min-width: 120px;
            }}
            
            QPushButton[class="secondary"]:hover {{
                border-color: {accent_color};
                color: {accent_color};
            }}
            
            QPushButton[class="small"] {{
                background-color: {accent_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 13px;
                min-width: 80px;
            }}
            
            QPushButton[class="small"]:hover {{
                background-color: {accent_hover};
            }}
            
            QPushButton:disabled {{
                background-color: {border_color};
                color: {secondary_text};
                border-color: {border_color};
            }}
            
            QComboBox {{
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 10px 14px;
                background-color: {input_bg};
                color: {text_color};
                font-size: 14px;
                min-height: 20px;
            }}
            
            QComboBox:hover {{
                border-color: {accent_color};
            }}
            
            QComboBox:focus {{
                border-color: {accent_color};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid {text_color};
                margin-right: 8px;
            }}
            
            QComboBox QAbstractItemView {{
                border: 1px solid {border_color};
                background-color: {input_bg};
                color: {text_color};
                selection-background-color: {accent_color};
                selection-color: white;
                border-radius: 6px;
            }}
            
            QCheckBox {{
                color: {text_color};
                spacing: 10px;
                font-size: 14px;
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {border_color};
                border-radius: 4px;
                background-color: {input_bg};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {accent_color};
                border-color: {accent_color};
            }}
            
            QCheckBox::indicator:checked::after {{
                content: "✓";
                color: white;
                font-weight: bold;
                font-size: 12px;
            }}
            
            QProgressBar {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {input_bg};
                text-align: center;
                color: {text_color};
                height: 20px;
            }}
            
            QProgressBar::chunk {{
                background-color: {accent_color};
                border-radius: 5px;
            }}
            
            QTextEdit {{
                border: 1px solid {border_color};
                border-radius: 8px;
                background-color: {input_bg};
                color: {text_color};
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 11px;
                padding: 12px;
            }}
            
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
        """)
    
    def setup_ui(self):
        """Setup the modern UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        self.create_header(content_layout)
        
        # Whisper section
        self.create_whisper_section(content_layout)
        
        # Ollama section
        self.create_ollama_section(content_layout)
        
        # Progress section
        self.create_progress_section(content_layout)
        
        # Footer
        self.create_footer(content_layout)
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
    
    def create_header(self, parent_layout):
        """Create the header section."""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 20)
        
        # Title
        title = QLabel(tr("setup.title"))
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel(tr("setup.subtitle"))
        subtitle.setProperty("class", "subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)
        
        parent_layout.addLayout(header_layout)
    
    def create_whisper_section(self, parent_layout):
        """Create Whisper model selection section."""
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(20, 16, 20, 16)
        
        # Section title
        title = QLabel(tr("setup.whisper_model_title"))
        title.setProperty("class", "section-title")
        card_layout.addWidget(title)
        
        # Description
        desc = QLabel(tr("setup.whisper_model_desc"))
        desc.setProperty("class", "description")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.setSpacing(12)
        
        model_label = QLabel(tr("setup.model_label"))
        model_label.setProperty("class", "description")
        model_layout.addWidget(model_label)
        
        self.whisper_combo = QComboBox()
        self.whisper_combo.setMinimumWidth(200)
        for model, size, desc in self.system_checker.get_whisper_models():
            self.whisper_combo.addItem(f"{model} ({size}) - {desc}", model)
        
        # Set current model
        current_whisper = self.config_manager.get_whisper_model()
        for i in range(self.whisper_combo.count()):
            if self.whisper_combo.itemData(i) == current_whisper:
                self.whisper_combo.setCurrentIndex(i)
                break
        
        model_layout.addWidget(self.whisper_combo)
        model_layout.addStretch()
        card_layout.addLayout(model_layout)
        
        parent_layout.addWidget(card)
    
    def create_ollama_section(self, parent_layout):
        """Create Ollama model selection section."""
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(20, 16, 20, 16)
        
        # Section title
        title = QLabel(tr("setup.ollama_model_title"))
        title.setProperty("class", "section-title")
        card_layout.addWidget(title)
        
        # Description
        desc = QLabel(tr("setup.ollama_model_desc"))
        desc.setProperty("class", "description")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)
        
        # Status
        self.ollama_status = QLabel(tr("setup.ollama_status_checking"))
        self.ollama_status.setProperty("class", "status")
        card_layout.addWidget(self.ollama_status)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.setSpacing(12)
        
        model_label = QLabel(tr("setup.model_label"))
        model_label.setProperty("class", "description")
        model_layout.addWidget(model_label)
        
        self.ollama_combo = QComboBox()
        self.ollama_combo.setMinimumWidth(200)
        model_layout.addWidget(self.ollama_combo)
        
        self.download_btn = QPushButton(tr("setup.download_button"))
        self.download_btn.setProperty("class", "secondary-button")
        self.download_btn.clicked.connect(self.download_selected_model)
        model_layout.addWidget(self.download_btn)
        
        model_layout.addStretch()
        card_layout.addLayout(model_layout)
        
        parent_layout.addWidget(card)
    
    def create_progress_section(self, parent_layout):
        """Create download progress section."""
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(20, 16, 20, 16)
        
        # Section title
        title = QLabel(tr("setup.download_progress_title"))
        title.setProperty("class", "section-title")
        card_layout.addWidget(title)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        card_layout.addWidget(self.progress_bar)
        
        # Status text
        self.progress_text = QTextEdit()
        self.progress_text.setMaximumHeight(80)
        self.progress_text.setVisible(False)
        card_layout.addWidget(self.progress_text)
        
        self.progress_card = card
        self.progress_card.setVisible(False)
        parent_layout.addWidget(card)
    
    def create_footer(self, parent_layout):
        """Create the footer section."""
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(20)
        footer_layout.setContentsMargins(0, 30, 0, 0)
        
        # Skip checkbox
        self.skip_checkbox = QCheckBox(tr("setup.skip_checkbox"))
        footer_layout.addWidget(self.skip_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)
        
        skip_btn = QPushButton(tr("setup.use_defaults_button"))
        skip_btn.setProperty("class", "secondary")
        skip_btn.clicked.connect(self.skip_setup)
        button_layout.addWidget(skip_btn)
        
        button_layout.addStretch()
        
        self.apply_btn = QPushButton(tr("setup.apply_button"))
        self.apply_btn.setProperty("class", "primary")
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        footer_layout.addLayout(button_layout)
        parent_layout.addLayout(footer_layout)
    
    def check_system_status(self):
        """Check Ollama installation and available models."""
        ollama_installed, status_key, status_args = self.system_checker.check_ollama_installed()
        
        status_msg = tr(status_key, **status_args)

        if ollama_installed:
            self.ollama_status.setText("✓ " + status_msg)
            self.ollama_status.setProperty("class", "status status-success")
            self.populate_ollama_models()
        else:
            self.ollama_status.setText("⚠ " + status_msg)
            self.ollama_status.setProperty("class", "status status-error")
            self.ollama_combo.addItem(tr("setup.ollama_not_installed"), "")
        
        # Refresh styling
        self.ollama_status.style().unpolish(self.ollama_status)
        self.ollama_status.style().polish(self.ollama_status)
    
    def populate_ollama_models(self):
        """Populate Ollama model dropdown with only installed models."""
        self.ollama_combo.setEnabled(True)
        self.download_btn.setEnabled(False)  # Disable download since we only show installed models
        
        # Add only installed models
        installed_models = self.system_checker.get_available_ollama_models()
        if installed_models:
            for model in installed_models:
                self.ollama_combo.addItem(f"✓ {model} (installed)", model)
        else:
            self.ollama_combo.addItem(tr("setup.ollama_not_installed"), "")
            self.ollama_combo.setEnabled(False)
        
        # Set current model
        current_ollama = self.config_manager.get_ollama_model()
        for i in range(self.ollama_combo.count()):
            if self.ollama_combo.itemData(i) == current_ollama:
                self.ollama_combo.setCurrentIndex(i)
                break
    
    def download_selected_model(self):
        """Download the selected Ollama model."""
        model_name = self.ollama_combo.currentData()
        if not model_name:
            return
        
        self.progress_card.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_text.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.download_btn.setEnabled(False)
        
        self.download_thread = ModelDownloadThread(model_name)
        self.download_thread.progress_update.connect(self.update_progress)
        self.download_thread.download_complete.connect(self.download_finished)
        self.download_thread.start()
    
    def update_progress(self, message: str):
        """Update progress display."""
        self.progress_text.append(message)
        self.progress_text.verticalScrollBar().setValue(
            self.progress_text.verticalScrollBar().maximum()
        )
    
    def download_finished(self, success: bool, message: str):
        """Handle download completion."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if success else 0)
        self.download_btn.setEnabled(True)
        
        self.update_progress(message)
        
        if success:
            # Refresh the model list
            self.ollama_combo.clear()
            self.populate_ollama_models()
    
    def apply_settings(self):
        """Apply the selected settings."""
        whisper_model = self.whisper_combo.currentData()
        ollama_model = self.ollama_combo.currentData()
        
        if whisper_model:
            self.config_manager.set_whisper_model(whisper_model)
        
        if ollama_model:
            self.config_manager.set_ollama_model(ollama_model)
        
        # Only set setup_completed to True if skip checkbox is checked
        if self.skip_checkbox.isChecked():
            self.config_manager.set_setup_completed(True)
            self.config_manager.set_skip_welcome(True)
        
        self.setup_completed.emit()
        self.accept()
    
    def skip_setup(self):
        """Skip the setup process."""
        self.config_manager.set_setup_completed(True)
        self.config_manager.set_skip_welcome(True)
        self.setup_completed.emit()
        self.accept()


class WelcomeScreen(ModernSetupDialog):
    """Backward compatibility wrapper for the modern setup dialog."""
    
    def __init__(self):
        super().__init__()


# Legacy overlay class for backward compatibility
class WelcomeOverlay(QWidget):
    """Legacy overlay - now redirects to modern dialog."""
    
    setup_completed = Signal()
    setup_requested = Signal()
    skip_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.modern_dialog = None
        
        # Connect signals to show modern dialog
        self.setup_requested.connect(self.show_modern_setup)
        self.skip_requested.connect(self.skip_setup)
    
    def show_modern_setup(self):
        """Show the modern setup dialog."""
        if self.modern_dialog is None:
            self.modern_dialog = ModernSetupDialog()
            self.modern_dialog.setup_completed.connect(self.setup_completed.emit)
        
        self.modern_dialog.show()
        self.modern_dialog.raise_()
        self.modern_dialog.activateWindow()
    
    def skip_setup(self):
        """Skip the setup process."""
        self.config_manager.set_setup_completed(True)
        self.config_manager.set_skip_welcome(True)
        self.setup_completed.emit()