"""
Model Selection Widget
Provides UI for selecting Whisper and Ollama models.
"""

import sys
import os
import subprocess
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QCheckBox, QProgressBar, QTextEdit, QGroupBox,
    QApplication, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPalette, QColor
from typing import List, Tuple

from .system_checker import SystemChecker, ConfigManager
from .utils import get_ollama_installation_instructions

# Import theme detection from app_utils
from app.utils.app_utils import detect_system_theme


class ModelDownloadThread(QThread):
    """Thread for downloading Ollama models."""
    
    progress_update = Signal(str)
    download_complete = Signal(bool, str)
    
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
    
    def run(self):
        try:
            self.progress_update.emit(f"Downloading {self.model_name}...")
            
            process = subprocess.Popen(
                ["ollama", "pull", self.model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    self.progress_update.emit(line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                self.download_complete.emit(True, f"Successfully downloaded {self.model_name}")
            else:
                self.download_complete.emit(False, f"Failed to download {self.model_name}")
                
        except Exception as e:
            self.download_complete.emit(False, f"Error downloading {self.model_name}: {str(e)}")


class ModelSelectionWidget(QWidget):
    """Widget for selecting Whisper and Ollama models."""
    
    models_selected = Signal(str, str)  # whisper_model, ollama_model
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.system_checker = SystemChecker()
        self.config_manager = ConfigManager()
        self.download_thread = None
        self.current_theme = None
        
        self.setFixedSize(500, 600)
        self.setup_ui()
        self.apply_theme()
        self.check_system_status()
    
    def detect_and_apply_theme(self):
        """Detect system theme and apply appropriate styling."""
        theme = detect_system_theme()
        if theme != self.current_theme:
            self.current_theme = theme
            self.apply_theme()
    
    def apply_theme(self):
        """Apply theme-appropriate styling to the widget."""
        theme = detect_system_theme()
        self.current_theme = theme
        
        if theme == 'dark':
            # Dark theme colors
            bg_color = "#2b2b2b"
            text_color = "#ffffff"
            secondary_text = "#cccccc"
            border_color = "#555555"
            button_bg = "#404040"
            button_hover = "#505050"
            input_bg = "#3c3c3c"
            group_bg = "#333333"
        else:
            # Light theme colors
            bg_color = "#ffffff"
            text_color = "#000000"
            secondary_text = "#666666"
            border_color = "#cccccc"
            button_bg = "#f0f0f0"
            button_hover = "#e0e0e0"
            input_bg = "#ffffff"
            group_bg = "#f8f8f8"
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            
            QLabel {{
                color: {text_color};
                border: none;
                background: transparent;
            }}
            
            QLabel[class="description"] {{
                color: {secondary_text};
                font-size: 12px;
            }}
            
            QLabel[class="status"] {{
                color: {secondary_text};
                font-size: 11px;
            }}
            
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {border_color};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {group_bg};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: {text_color};
                background-color: {bg_color};
            }}
            
            QComboBox {{
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                background-color: {input_bg};
                color: {text_color};
                min-height: 20px;
            }}
            
            QComboBox:hover {{
                border-color: #0078d4;
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {text_color};
                margin-right: 5px;
            }}
            
            QComboBox QAbstractItemView {{
                border: 1px solid {border_color};
                background-color: {input_bg};
                color: {text_color};
                selection-background-color: #0078d4;
                selection-color: white;
            }}
            
            QPushButton {{
                background-color: {button_bg};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 16px;
                color: {text_color};
                font-weight: 500;
                min-height: 20px;
            }}
            
            QPushButton:hover {{
                background-color: {button_hover};
                border-color: #0078d4;
            }}
            
            QPushButton:pressed {{
                background-color: {border_color};
            }}
            
            QPushButton:disabled {{
                background-color: {border_color};
                color: {secondary_text};
                border-color: {border_color};
            }}
            
            QPushButton[class="primary"] {{
                background-color: #0078d4;
                color: white;
                border-color: #0078d4;
            }}
            
            QPushButton[class="primary"]:hover {{
                background-color: #106ebe;
            }}
            
            QPushButton[class="primary"]:pressed {{
                background-color: #005a9e;
            }}
            
            QCheckBox {{
                color: {text_color};
                spacing: 8px;
            }}
            
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {border_color};
                border-radius: 3px;
                background-color: {input_bg};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: #0078d4;
                border-color: #0078d4;
            }}
            
            QCheckBox::indicator:checked::after {{
                content: "✓";
                color: white;
                font-weight: bold;
            }}
            
            QProgressBar {{
                border: 1px solid {border_color};
                border-radius: 4px;
                background-color: {input_bg};
                text-align: center;
                color: {text_color};
            }}
            
            QProgressBar::chunk {{
                background-color: #0078d4;
                border-radius: 3px;
            }}
            
            QTextEdit {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {input_bg};
                color: {text_color};
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 10px;
                padding: 8px;
            }}
        """)
    
    def setup_ui(self):
        """Setup the model selection UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Model Configuration")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Whisper section
        self.create_whisper_section(layout)
        
        # Ollama section
        self.create_ollama_section(layout)
        
        # Progress section
        self.create_progress_section(layout)
        
        # Bottom controls
        self.create_bottom_controls(layout)
    
    def create_whisper_section(self, parent_layout):
        """Create Whisper model selection section."""
        whisper_group = QGroupBox("Whisper Speech Recognition")
        whisper_layout = QVBoxLayout(whisper_group)
        
        # Description
        whisper_desc = QLabel("Whisper converts speech to text. Larger models are more accurate but slower.")
        whisper_desc.setProperty("class", "description")
        whisper_desc.setWordWrap(True)
        whisper_layout.addWidget(whisper_desc)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        
        self.whisper_combo = QComboBox()
        for model, size, desc in self.system_checker.get_whisper_models():
            self.whisper_combo.addItem(f"{model} ({size}) - {desc}", model)
        
        # Set current model
        current_whisper = self.config_manager.get_whisper_model()
        for i in range(self.whisper_combo.count()):
            if self.whisper_combo.itemData(i) == current_whisper:
                self.whisper_combo.setCurrentIndex(i)
                break
        
        model_layout.addWidget(self.whisper_combo)
        whisper_layout.addLayout(model_layout)
        parent_layout.addWidget(whisper_group)
    
    def create_ollama_section(self, parent_layout):
        """Create Ollama model selection section."""
        ollama_group = QGroupBox("Ollama Language Models")
        ollama_layout = QVBoxLayout(ollama_group)
        
        # Description
        ollama_desc = QLabel("Ollama provides local language models for text processing and analysis.")
        ollama_desc.setProperty("class", "description")
        ollama_desc.setWordWrap(True)
        ollama_layout.addWidget(ollama_desc)
        
        # Status
        self.ollama_status = QLabel("Checking Ollama...")
        self.ollama_status.setProperty("class", "status")
        ollama_layout.addWidget(self.ollama_status)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        
        self.ollama_combo = QComboBox()
        self.ollama_combo.setEnabled(False)
        model_layout.addWidget(self.ollama_combo)
        
        self.download_btn = QPushButton("Download")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_selected_model)
        model_layout.addWidget(self.download_btn)
        
        ollama_layout.addLayout(model_layout)
        parent_layout.addWidget(ollama_group)
    
    def create_progress_section(self, parent_layout):
        """Create download progress section."""
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_text = QTextEdit()
        self.progress_text.setMaximumHeight(100)
        self.progress_text.setVisible(False)
        self.progress_text.setReadOnly(True)
        progress_layout.addWidget(self.progress_text)
        
        parent_layout.addWidget(progress_group)
    
    def create_bottom_controls(self, parent_layout):
        """Create bottom control buttons."""
        parent_layout.addStretch()
        
        # Skip welcome checkbox
        self.skip_checkbox = QCheckBox("Don't show this setup again")
        parent_layout.addWidget(self.skip_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply Settings")
        self.apply_btn.setProperty("class", "primary")
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        parent_layout.addLayout(button_layout)
    
    def check_system_status(self):
        """Check Ollama installation and available models."""
        ollama_installed, status_msg = self.system_checker.check_ollama_installed()
        self.ollama_status.setText(status_msg)
        
        if ollama_installed:
            self.ollama_status.setProperty("class", "status")
            self.ollama_status.setStyleSheet("color: #28a745;")
            self.populate_ollama_models()
        else:
            self.ollama_status.setProperty("class", "status")
            self.ollama_status.setStyleSheet("color: #dc3545;")
            self.ollama_combo.addItem("Ollama not installed", "")
    
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
            self.ollama_combo.addItem("No models installed", "")
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
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
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
        
        self.models_selected.emit(whisper_model or "tiny", ollama_model or "")
        self.close()