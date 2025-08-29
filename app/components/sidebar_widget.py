"""Sidebar widget for notes editing."""

import os
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy, QTextEdit, QLineEdit
# QSvgWidget removed - using QLabel with QPixmap instead to avoid deletion errors
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QEvent
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QTextOption

from .markdown_editor import MarkdownEditor, MarkdownTextEdit
from app.services.database_manager import NotesDatabase
from app.services.ai_client import OllamaClient
from app.utils.translation_manager import tr


class ChatMessageWidget(QWidget):
    """Widget for displaying a single chat message."""
    
    def __init__(self, role: str, text: str):
        super().__init__()
        self.role = role
        self.text = text
        self.setup_ui()

    def setup_ui(self):
        """Setup the message widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Fix entire layout at top
        
        # Icon - use QLabel with QPixmap instead of QSvgWidget to avoid deletion issues
        icon_name = "user" if self.role == "user" else "ai"
        icon_path = f'icons/{icon_name}.svg'
        self.icon = QLabel()
        self.icon.setFixedSize(20, 20)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        try:
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtGui import QPixmap, QPainter
            
            with open(icon_path, 'r') as f:
                svg_content = f.read()
            
            # Replace currentColor with white for dark theme
            themed_svg_content = svg_content.replace('currentColor', 'white')
            # Also replace any black colors with white
            themed_svg_content = themed_svg_content.replace('fill="black"', 'fill="white"')
            themed_svg_content = themed_svg_content.replace('stroke="black"', 'stroke="white"')
            
            # Create QSvgRenderer and render to QPixmap with proper cleanup
            renderer = QSvgRenderer(self)  # Set parent to ensure proper cleanup
            if renderer.load(themed_svg_content.encode('utf-8')):
                pixmap = QPixmap(20, 20)
                pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(pixmap)
                try:
                    renderer.render(painter)
                finally:
                    painter.end()  # Ensure painter is always closed
                
                self.icon.setPixmap(pixmap)
            else:
                # Fallback if SVG loading fails
                self.icon.setText("●" if self.role == "user" else "◆")
                self.icon.setStyleSheet("color: white; font-size: 12px;")
            
        except (FileNotFoundError, ImportError) as e:
            print(f"Error loading icon: {e}")
            # Create a simple text fallback
            self.icon.setText("●" if self.role == "user" else "◆")
            self.icon.setStyleSheet("color: white; font-size: 12px;")
        
        # Create content layout
        content_layout = QVBoxLayout()
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Fix content at top
        
        # Message content
        self.message_label = QLabel(self.text)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignTop)  # Fix text at top
        self.message_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 8px 10px;
                color: white;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        
        content_layout.addWidget(self.message_label)
        
        layout.addWidget(self.icon)
        layout.addLayout(content_layout)

class SidebarWidget(QWidget):
    """Sidebar widget for editing notes related to sentences."""
    
    closed = Signal()  # Emitted when sidebar is closed
    
    def __init__(self, sentence: str, timestamp: float = None, parent=None, all_sentences: list = [], study_mode: bool = False, fresh_conversation: bool = False):
        super().__init__(parent)
        self.sentence = sentence
        self.timestamp = timestamp
        self.all_sentences = all_sentences
        self.study_mode = study_mode
        self.fresh_conversation = fresh_conversation
        self.db = NotesDatabase()
        self.ollama_client = OllamaClient()
        self.pending_updates = []
        self.chat_history = []
        self.current_ai_response = ""
        self.setup_ui()
        if not self.study_mode:
            self.load_existing_note()
        else:
            # Only load chat history if not starting a fresh conversation
            if not self.fresh_conversation:
                self.load_chat_history()
        
        # Setup timer for thread-safe UI updates
        self.update_timer = QTimer(self)  # Set parent for proper cleanup
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.update_timer.start(50)  # Check for updates every 50ms
    
    def setup_ui(self):
        """Setup sidebar UI."""
        self.setMinimumWidth(300)
        # Removed setMaximumWidth to allow full expansion
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                color: rgba(255, 255, 255, 0.9);
            }
        """)
        
        # Clear existing layout if it exists
        if self.layout():
            QWidget().setLayout(self.layout())
        
        # Reset UI components that will be recreated
        self.send_icon = None
        self.send_button = None
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 15, 8, 15)  # Reduced horizontal margins from 15 to 8
        main_layout.setSpacing(0)
        
        # Header with close button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 15)
        
        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 0, 0, 0.2);
                border-color: rgba(255, 0, 0, 0.4);
            }
            QPushButton:pressed {
                background: rgba(255, 0, 0, 0.3);
            }
        """)
        self.close_btn.clicked.connect(self.close_sidebar)
        
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        main_layout.addLayout(header_layout)
        
        # Content layout
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # Sentence title (H1 style) - ensure it uses full width
        self.title_label = QLabel(self.sentence)
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumWidth(0)  # Allow shrinking
        from PySide6.QtWidgets import QSizePolicy
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.title_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.95);
                font-size: 18px;
                font-weight: 600;
                line-height: 1.3;
                padding: 0;
                margin: 0;
                border: none;
                background: transparent;
            }
        """)
        content_layout.addWidget(self.title_label)

        # Separator line - ensure it uses full width
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setMinimumWidth(0)  # Allow shrinking
        separator.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        separator.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.1);
                border: none;
                height: 1px;
                margin: 10px 0;
            }
        """)
        content_layout.addWidget(separator)

        if self.study_mode:
            # Study mode: Show thinking widget and chat interface
            self.setup_study_mode_content(content_layout)
        else:
            # Normal mode: Show markdown editor
            self.editor = MarkdownEditor()
            self.editor.setMinimumWidth(0)  # Allow shrinking
            self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.editor.content_changed.connect(self.save_note)
            self.editor.ai_request.connect(self.get_ai_explanation)
            self.editor.stop_request.connect(self.stop_ai_explanation)
            content_layout.addWidget(self.editor, 1) # Make editor take all available space

        main_layout.addLayout(content_layout)
    
    def setup_study_mode_content(self, content_layout):
        """Setup study mode content with thinking widget and chat interface."""
        # Create standalone thinking widget for study mode
        self.thinking_widget = QWidget()
        self.thinking_widget.setObjectName("thinking_widget")
        self.thinking_widget.setStyleSheet("""
            #thinking_widget {
                background: rgba(128, 128, 128, 0.1);
                border: 1px solid rgba(128, 128, 128, 0.3);
                border-radius: 4px;
                margin: 2px;
            }
        """)
        self.thinking_widget.setMaximumHeight(120)
        self.thinking_widget.setVisible(False)  # Initially hidden
        
        # Layout for thinking widget
        thinking_layout = QVBoxLayout(self.thinking_widget)
        thinking_layout.setContentsMargins(4, 4, 4, 4)
        thinking_layout.setSpacing(2)
        
        # Text area for thinking content
        self.thinking_text = QTextEdit()
        self.thinking_text.setReadOnly(True)
        self.thinking_text.setMinimumHeight(40)
        self.thinking_text.setMaximumHeight(80)
        
        # Disable scrollbars
        self.thinking_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.thinking_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Styling for thinking content
        self.thinking_text.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.6);
                font-size: 10px;
                padding: 4px;
                line-height: 1.3;
            }
        """)
        
        # Set font
        font = QFont()
        font.setPointSize(8)
        font.setWeight(QFont.Weight.Light)
        self.thinking_text.setFont(font)
        
        thinking_layout.addWidget(self.thinking_text)

        # Initialize state for AI stream processing (reusing markdown editor's approach)
        self.is_ai_responding = False
        self._ai_stream_buffer = ""
        self._inside_think_tags = False
        self._main_content_buffer = ""
        self._has_thinking_content = False
        
        content_layout.addWidget(self.thinking_widget)
        
        # Chat display area - compact design
        # Disable auto-scroll by default; user prefers no automatic scrolling
        self.auto_scroll_enabled = False
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Allow manual vertical scrolling if content exceeds view, but we avoid auto-scroll programmatically
        self.chat_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chat_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: rgba(255, 255, 255, 0.03);
                width: 4px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
                min-height: 15px;
            }
        """)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(2)
        self.chat_layout.addStretch()
        
        self.chat_scroll_area.setWidget(self.chat_container)
        content_layout.addWidget(self.chat_scroll_area, 1)
        
        # Input area - compact
        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText(tr("sidebar.ask_question_placeholder"))
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 3px;
                color: white;
                font-size: 14px;
                padding: 6px 8px;
                min-height: 18px;
            }
            QLineEdit:focus {
                border-color: rgba(100, 149, 237, 0.4);
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.message_input.returnPressed.connect(self.send_or_stop_message)
        
        # Send/Stop button with icons
        self.send_button = QPushButton()
        self.send_button.setFixedSize(28, 24)
        self.send_button.clicked.connect(self.send_or_stop_message)
        self.update_send_button_icon(False)  # Start with send icon
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        content_layout.addLayout(input_layout)
        
    def update_send_button_icon(self, is_stopping=False):
        """Update send button icon based on state."""
        # Check if send_button exists, if not, skip the update
        if not hasattr(self, 'send_button') or self.send_button is None:
            return
            
        icon_name = "pause" if is_stopping else "send"
        icon_path = f'icons/{icon_name}.svg'
        
        try:
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtGui import QPixmap, QPainter
            
            with open(icon_path, 'r') as f:
                svg_content = f.read()
            
            # Replace currentColor with white for dark theme
            themed_svg_content = svg_content.replace('currentColor', 'white')
            # Also replace any black colors with white
            themed_svg_content = themed_svg_content.replace('fill="black"', 'fill="white"')
            themed_svg_content = themed_svg_content.replace('stroke="black"', 'stroke="white"')
            
            # Create QLabel for the icon instead of QSvgWidget
            if not hasattr(self, 'send_icon') or self.send_icon is None:
                self.send_icon = QLabel(self.send_button)
                self.send_icon.setFixedSize(14, 14)
                self.send_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
            # Create QSvgRenderer and render to QPixmap with proper cleanup
            renderer = QSvgRenderer(self)  # Set parent to ensure proper cleanup
            if renderer.load(themed_svg_content.encode('utf-8')):
                pixmap = QPixmap(14, 14)
                pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(pixmap)
                try:
                    renderer.render(painter)
                finally:
                    painter.end()  # Ensure painter is always closed
                
                self.send_icon.setPixmap(pixmap)
            else:
                # Fallback if SVG loading fails
                self.send_icon.setText("⏸" if is_stopping else "▶")
                self.send_icon.setStyleSheet("color: white; font-size: 10px;")
            
            # Set button style based on state
            if is_stopping:
                button_style = """
                    QPushButton {
                        background-color: rgba(255, 100, 100, 0.7);
                        border: none;
                        border-radius: 3px;
                        padding: 2px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 100, 100, 0.9);
                    }
                """
            else:
                button_style = """
                    QPushButton {
                        background-color: rgba(100, 149, 237, 0.7);
                        border: none;
                        border-radius: 3px;
                        padding: 2px;
                    }
                    QPushButton:hover {
                        background-color: rgba(100, 149, 237, 0.9);
                    }
                """
            
            self.send_button.setStyleSheet(button_style)
            
            # Ensure icon is properly positioned without recreating layout
            if not self.send_button.layout():
                button_layout = QHBoxLayout(self.send_button)
                button_layout.setContentsMargins(0, 0, 0, 0)
                button_layout.addWidget(self.send_icon)
            
        except (FileNotFoundError, ImportError) as e:
            print(f"Error loading icon: {e}")
            # Fallback to text
            self.send_button.setText("Stop" if is_stopping else "Send")
    
    def set_study_mode(self, enabled: bool):
        """Switch between study mode and normal mode."""
        if self.study_mode == enabled:
            return
            
        self.study_mode = enabled
        # Rebuild the UI
        self.setup_ui()
        if not self.study_mode:
            self.load_existing_note()
    
    def send_or_stop_message(self):
        """Send user message or stop AI response in study mode."""
        if not self.study_mode:
            return
            
        if self.is_ai_responding:
            # Stop AI response
            self.ollama_client.stop()
            self.is_ai_responding = False
            self.update_send_button_icon(False)  # Switch back to send icon
        else:
            # Send message
            message = self.message_input.text().strip()
            if message:
                self.add_user_message(message)
                self.message_input.clear()
                self.handle_user_message(message)
                
    def send_message(self):
        """Send user message in study mode."""
        self.send_or_stop_message()
    
    def add_user_message(self, message):
        """Add user message to chat history."""
        self.chat_history.append({"role": "user", "content": message})
        
        # Save to database
        try:
            self.db.save_chat_message(self.sentence, "user", message)
        except Exception as e:
            print(f"Error saving user message to database: {e}")
        
        # Create user message widget directly
        user_widget = self._create_user_message_widget(message)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, user_widget)
        
        # Auto-scroll to bottom (disabled by default)
        if getattr(self, 'auto_scroll_enabled', False):
            QTimer.singleShot(10, lambda: self.chat_scroll_area.verticalScrollBar().setValue(
                self.chat_scroll_area.verticalScrollBar().maximum()
            ))
        
    def add_ai_message(self, message):
        """Add AI message to chat history."""
        self.chat_history.append({"role": "assistant", "content": message})
        
        # Save to database (only for non-streaming messages like errors)
        try:
            self.db.save_chat_message(self.sentence, "assistant", message)
        except Exception as e:
            print(f"Error saving AI message to database: {e}")
        
        # Create AI message widget directly (this is for completed messages)
        ai_widget = self._create_ai_message_widget(message)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, ai_widget)
        
        # Auto-scroll to bottom (disabled by default)
        if getattr(self, 'auto_scroll_enabled', False):
            QTimer.singleShot(10, lambda: self.chat_scroll_area.verticalScrollBar().setValue(
                self.chat_scroll_area.verticalScrollBar().maximum()
            ))
    


    def clear_thinking(self):
        """Clear thinking content and hide widget."""
        if hasattr(self, 'thinking_text') and self.thinking_text is not None:
            self.thinking_text.clear()
        if hasattr(self, 'thinking_widget') and self.thinking_widget is not None:
            self.thinking_widget.setVisible(False)

    def append_thinking_content(self, chunk):
        """Append content to thinking widget."""
        self._append_thinking_content(chunk)

    def handle_user_message(self, message: str):
        """Handle user message and get AI response in study mode."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "transcriber_config.json")
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            ollama_model = config.get("ollama_model", "")
            
            if not ollama_model:
                self.add_ai_message("Ollama model not configured.")
                return
                
            # Set AI responding state
            self.is_ai_responding = True
            self.update_send_button_icon(True)  # Switch to stop icon
            
            # Clear any previous thinking content
            self.clear_thinking()
                
            # Create context that includes the conversation and chat history
            context_parts = [chr(10).join(self.all_sentences)]
            
            # Add chat history if available
            if self.chat_history:
                context_parts.append("\n\nPrevious conversation:")
                for msg in self.chat_history:
                    role = "Student" if msg["role"] == "user" else "Assistant"
                    context_parts.append(f"{role}: {msg['content']}")
            
            context_with_history = "".join(context_parts)
            
            def on_chunk(chunk):
                # Use the same mechanism as regular AI explanations to prevent duplication
                self.queue_ui_update('process_chunk', chunk)

            def on_done():
                self.queue_ui_update('finish_ai')

            # Use the user's message as the user_prompt, with the original sentence as context
            self.ollama_client.get_explanation(
                model=ollama_model,
                context=context_with_history,
                sentence=self.sentence,  # The original transcribed sentence
                user_prompt=message,     # The user's question/prompt
                on_chunk=on_chunk,
                on_done=on_done,
                study_mode=True
            )
            
        except Exception as e:
            self.add_ai_message(f"Error: {str(e)}")
            self.is_ai_responding = False
            self.send_button.setText("Send")
    
    def process_ai_chunk(self, chunk):
        """Process AI response chunk in study mode - delegate to markdown editor to prevent duplication."""
        if not self.study_mode:
            return
            
        # Only process through the markdown editor to prevent duplication
        # The markdown editor will handle all streaming logic
        pass
    
    def cleanup(self):
        """Clean up resources before widget destruction."""
        # Stop the update timer
        if hasattr(self, 'update_timer') and self.update_timer:
            self.update_timer.stop()
            self.update_timer.deleteLater()
            self.update_timer = None
        
        # Stop any ongoing AI requests
        if hasattr(self, 'ollama_client') and self.ollama_client:
            self.ollama_client.stop()
        
        # Clear pending updates
        if hasattr(self, 'pending_updates'):
            self.pending_updates.clear()
    
    def closeEvent(self, event):
        """Handle widget close event."""
        self.cleanup()
        super().closeEvent(event)
        
    # Removed duplicate streaming logic - all AI streaming is handled by the markdown editor
    
    def scroll_to_bottom(self):
        """Scroll chat to bottom."""
        if hasattr(self, 'chat_scroll_area') and getattr(self, 'auto_scroll_enabled', False):
            self.chat_scroll_area.verticalScrollBar().setValue(
                self.chat_scroll_area.verticalScrollBar().maximum()
            )
    
    def load_existing_note(self):
        """Load existing note from database."""
        note_data = self.db.get_note(self.sentence)
        if hasattr(self, 'editor') and self.editor is not None:
            try:
                if note_data:
                    _, _, content, _ = note_data
                    self.editor.set_content(content or "")
                else:
                    self.editor.set_content("")
            except RuntimeError:
                # Object has been deleted, ignore
                pass

    def load_chat_history(self):
        """Load existing chat history from database for study mode."""
        if not self.study_mode:
            return
            
        try:
            # Get chat history from database
            chat_messages = self.db.get_chat_history(self.sentence)
            
            # Clear current chat history and UI
            self.chat_history.clear()
            
            # Restore chat history and create widgets
            for role, content in chat_messages:
                # Add to chat history
                self.chat_history.append({"role": role, "content": content})
                
                # Create and add widget to UI
                if role == "user":
                    widget = self._create_user_message_widget(content)
                else:  # role == "assistant"
                    widget = self._create_ai_message_widget(content)
                
                self.chat_layout.insertWidget(self.chat_layout.count() - 1, widget)
            
            # Auto-scroll to bottom if there are messages (disabled by default)
            if chat_messages and getattr(self, 'auto_scroll_enabled', False):
                QTimer.singleShot(100, lambda: self.chat_scroll_area.verticalScrollBar().setValue(
                    self.chat_scroll_area.verticalScrollBar().maximum()
                ))
                
        except Exception as e:
            print(f"Error loading chat history: {e}")
    
    def save_note(self, content: str):
        """Save note to database."""
        self.db.save_note(self.sentence, content, self.timestamp)
    
    def close_sidebar(self):
        """Close the sidebar."""
        self.closed.emit()

    def get_ai_explanation(self):
        """Get AI explanation for the sentence with thinking tags processing."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "transcriber_config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        ollama_model = config.get("ollama_model", "")

        if not ollama_model:
            self.queue_ui_update('show_error', "\n\nOllama model not configured.")
            return

        # Start AI button animation
        if hasattr(self, 'editor') and self.editor is not None:
            try:
                self.editor.start_ai_animation()
            except RuntimeError:
                # Object has been deleted, ignore
                return
        
        self.queue_ui_update('show_ai_buttons', False)

        def on_chunk(chunk):
            # Only use the markdown editor's streaming mechanism
            print(f"DEBUG: Sidebar received chunk: {chunk[:50]}...")
            self.queue_ui_update('process_chunk', chunk)

        def on_done():
            self.queue_ui_update('finish_ai')

        self.ollama_client.get_explanation(
            model=ollama_model,
            context="\n".join(self.all_sentences),
            sentence=self.sentence,  # The transcribed sentence to explain
            user_prompt=None,        # No user prompt in regular mode
            on_chunk=on_chunk,
            on_done=on_done,
            study_mode=False
        )

    def queue_ui_update(self, action, data=None):
        """Queue a UI update to be processed on the main thread."""
        self.pending_updates.append((action, data))

    def process_pending_updates(self):
        """Process all pending UI updates on the main thread."""
        if not self.pending_updates:
            return
            
        for action, data in self.pending_updates:
            if action == 'show_error':
                if hasattr(self, 'editor') and self.editor is not None:
                    try:
                        self.editor.text_edit.insertPlainText(data)
                    except RuntimeError:
                        # Object has been deleted, ignore
                        pass
            elif action == 'show_ai_buttons':
                if hasattr(self, 'editor') and self.editor is not None and hasattr(self.editor, 'toolbar'):
                    try:
                        self.editor.toolbar.ai_btn.setVisible(data)
                        self.editor.toolbar.stop_btn.setVisible(not data)
                    except RuntimeError:
                        # Object has been deleted, ignore
                        pass
            elif action == 'process_chunk':
                self.process_ai_chunk_safe(data)
            elif action == 'finish_ai':
                self.finish_ai_response()

                
        self.pending_updates.clear()

    def process_ai_chunk_safe(self, chunk):
        """Process AI response chunk safely on the main thread."""
        print(f"DEBUG: Processing chunk safely: {chunk[:50]}...")
        
        if self.study_mode:
            # Study mode: Handle AI streaming for chat interface
            print("DEBUG: Study mode - processing chunk for chat")
            try:
                self.process_ai_chunk_study_mode(chunk)
            except Exception as e:
                print(f"DEBUG: Error in study mode chunk processing: {e}")
        else:
            # Normal mode: Use editor for AI streaming
            if hasattr(self, 'editor') and self.editor is not None:
                try:
                    print("DEBUG: Calling editor.append_ai_stream_content")
                    self.editor.append_ai_stream_content(chunk)
                except RuntimeError:
                    print("DEBUG: RuntimeError in process_ai_chunk_safe")
                    # Object has been deleted, ignore the chunk
                    pass
            else:
                print("DEBUG: Editor not available in process_ai_chunk_safe")

    def process_ai_chunk_study_mode(self, chunk: str):
        """Process AI chunk for study mode chat interface."""
        if not hasattr(self, '_ai_stream_buffer'):
            self._ai_stream_buffer = ""
            self._inside_think_tags = False
            self._main_content_buffer = ""
            self._has_thinking_content = False
            self._current_ai_message = None
        
        self._ai_stream_buffer += chunk
        
        # Process the buffer to extract complete think blocks and regular content
        while True:
            if not self._inside_think_tags:
                # Look for potential opening think tag by detecting '<' character
                lt_pos = self._ai_stream_buffer.find('<')
                if lt_pos != -1:
                    # Add any content before the '<' to main content buffer
                    before_lt = self._ai_stream_buffer[:lt_pos]
                    if before_lt.strip():
                        self._main_content_buffer += before_lt
                        self._flush_main_content_buffer()
                    
                    # Check if we have enough characters to determine if it's a think tag
                    remaining = self._ai_stream_buffer[lt_pos:]
                    if len(remaining) >= 7 and remaining.startswith('<think>'):
                        # We found a complete think tag - show thinking content
                        self._has_thinking_content = True
                        
                        # Remove processed content and enter think mode
                        self._ai_stream_buffer = remaining[7:]  # +7 for '<think>'
                        self._inside_think_tags = True
                        continue
                    elif len(remaining) < 7:
                        # Not enough characters yet, keep the '<' and wait for more
                        if before_lt:
                            self._ai_stream_buffer = remaining
                        break
                    else:
                        # It's not a think tag, treat '<' as regular content
                        self._main_content_buffer += '<'
                        self._ai_stream_buffer = remaining[1:]
                        continue
                else:
                    # No '<' found, add to main content buffer
                    if self._ai_stream_buffer:
                        self._main_content_buffer += self._ai_stream_buffer
                        self._ai_stream_buffer = ""
                        # Only flush if we have complete words/sentences
                        self._flush_main_content_buffer(force_partial=False)
                    break
            else:
                # Look for closing think tag
                think_end = self._ai_stream_buffer.find('</think>')
                if think_end != -1:
                    # Add thinking content (without the closing tag)
                    thinking_content = self._ai_stream_buffer[:think_end]
                    if thinking_content.strip():
                        self._append_thinking_content(thinking_content)
                    
                    # Remove processed content and exit think mode (skip the closing tag)
                    self._ai_stream_buffer = self._ai_stream_buffer[think_end + 8:]  # +8 for '</think>'
                    self._inside_think_tags = False
                    continue
                else:
                    # No closing tag yet, add current content to thinking
                    if self._ai_stream_buffer.strip():
                        self._append_thinking_content(self._ai_stream_buffer)
                    self._ai_stream_buffer = ""
                    break
    
    def _flush_main_content_buffer(self, force_partial=True):
        """Flush the main content buffer for study mode chat."""
        if not self._main_content_buffer:
            return
        
        content_to_add = ""
        
        if force_partial:
            # Add everything in the buffer
            content_to_add = self._main_content_buffer
            self._main_content_buffer = ""
        else:
            # Only add complete words/sentences
            import re
            
            # Find the last complete word or sentence
            matches = list(re.finditer(r'[\s\n.!?;,]+', self._main_content_buffer))
            
            if matches:
                # Get the position after the last word boundary
                last_boundary = matches[-1].end()
                content_to_add = self._main_content_buffer[:last_boundary]
                self._main_content_buffer = self._main_content_buffer[last_boundary:]
            elif len(self._main_content_buffer) > 100:  # If buffer gets too long, flush anyway
                content_to_add = self._main_content_buffer
                self._main_content_buffer = ""
        
        if content_to_add:
            self._append_to_chat_message(content_to_add)
    
    def _append_to_chat_message(self, content: str):
        """Append content to the current AI chat message."""
        if not hasattr(self, '_current_ai_message') or self._current_ai_message is None:
            # Create new AI message widget
            self._current_ai_message = self._create_ai_message_widget("")
            self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._current_ai_message)
            # Initialize content buffer for streaming
            self._current_ai_message._content_buffer = ""
        
        # Update the message content
        if hasattr(self._current_ai_message, 'content_label'):
            # Append to buffer
            if not hasattr(self._current_ai_message, '_content_buffer'):
                self._current_ai_message._content_buffer = ""
            self._current_ai_message._content_buffer += content
            
            # Update the QTextEdit with markdown
            if self._current_ai_message._content_buffer.strip():
                self._current_ai_message.content_label.setMarkdown(self._current_ai_message._content_buffer)
            else:
                self._current_ai_message.content_label.setPlainText(self._current_ai_message._content_buffer)
            
            # Auto-resize the widget
            self._resize_message_widget(self._current_ai_message.content_label)
            
            # Auto-scroll to bottom (disabled by default)
            if getattr(self, 'auto_scroll_enabled', False):
                QTimer.singleShot(10, lambda: self.chat_scroll_area.verticalScrollBar().setValue(
                    self.chat_scroll_area.verticalScrollBar().maximum()
                ))
    
    def _append_thinking_content(self, content: str):
        """Append thinking content to the thinking widget."""
        if hasattr(self, 'thinking_text') and self.thinking_text is not None:
            try:
                # Show the thinking widget if it's hidden
                if not self.thinking_widget.isVisible():
                    self.thinking_widget.setVisible(True)
                
                # Append content to the thinking text
                cursor = self.thinking_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(content)
                
                # Auto-scroll to bottom
                self.thinking_text.moveCursor(QTextCursor.MoveOperation.End)
                
            except Exception as e:
                print(f"DEBUG: Error appending thinking content: {e}")
    
    def _create_user_message_widget(self, content: str):
        """Create a new user message widget for the chat."""
        message_widget = QWidget()
        message_layout = QHBoxLayout(message_widget)
        message_layout.setContentsMargins(4, 2, 4, 2)
        message_layout.setSpacing(6)
        
        # Add stretch to push content to the right
        message_layout.addStretch()
        
        # Message content with user styling
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("""
            QLabel {
                background-color: rgba(70, 130, 180, 0.8);
                border: 1px solid rgba(70, 130, 180, 0.9);
                border-radius: 6px;
                padding: 10px 12px;
                color: white;
                font-size: 14px;
                line-height: 1.4;
            }
        """)
        
        # User avatar/icon using SVG
        avatar_label = QLabel()
        avatar_label.setFixedSize(20, 20)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        try:
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtGui import QPixmap, QPainter
            
            icon_path = 'icons/user.svg'
            with open(icon_path, 'r') as f:
                svg_content = f.read()
            
            # Replace currentColor with white for dark theme
            themed_svg_content = svg_content.replace('currentColor', 'white')
            themed_svg_content = themed_svg_content.replace('fill="black"', 'fill="white"')
            themed_svg_content = themed_svg_content.replace('stroke="black"', 'stroke="white"')
            
            # Create QSvgRenderer and render to QPixmap
            renderer = QSvgRenderer(message_widget)
            if renderer.load(themed_svg_content.encode('utf-8')):
                pixmap = QPixmap(20, 20)
                pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(pixmap)
                try:
                    renderer.render(painter)
                finally:
                    painter.end()
                
                avatar_label.setPixmap(pixmap)
            else:
                # Fallback if SVG loading fails
                avatar_label.setText("U")
                avatar_label.setStyleSheet("color: white; font-size: 8px; font-weight: bold;")
                
        except (FileNotFoundError, ImportError) as e:
            print(f"Error loading user icon: {e}")
            avatar_label.setText("U")
            avatar_label.setStyleSheet("color: white; font-size: 8px; font-weight: bold;")
        
        message_layout.addWidget(content_label)
        message_layout.addWidget(avatar_label)
        
        return message_widget

    def _create_ai_message_widget(self, content: str):
        """Create a new AI message widget for the chat."""
        message_widget = QWidget()
        message_layout = QHBoxLayout(message_widget)
        message_layout.setContentsMargins(4, 2, 4, 2)
        message_layout.setSpacing(6)
        
        # AI avatar/icon using SVG
        avatar_label = QLabel()
        avatar_label.setFixedSize(20, 20)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        try:
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtGui import QPixmap, QPainter
            
            icon_path = 'icons/ai.svg'
            with open(icon_path, 'r') as f:
                svg_content = f.read()
            
            # Replace currentColor with white for dark theme
            themed_svg_content = svg_content.replace('currentColor', 'white')
            themed_svg_content = themed_svg_content.replace('fill="black"', 'fill="white"')
            themed_svg_content = themed_svg_content.replace('stroke="black"', 'stroke="white"')
            
            # Create QSvgRenderer and render to QPixmap
            renderer = QSvgRenderer(message_widget)
            if renderer.load(themed_svg_content.encode('utf-8')):
                pixmap = QPixmap(20, 20)
                pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(pixmap)
                try:
                    renderer.render(painter)
                finally:
                    painter.end()
                
                avatar_label.setPixmap(pixmap)
            else:
                # Fallback if SVG loading fails
                avatar_label.setText("AI")
                avatar_label.setStyleSheet("color: white; font-size: 8px; font-weight: bold;")
                
        except (FileNotFoundError, ImportError) as e:
            print(f"Error loading AI icon: {e}")
            avatar_label.setText("AI")
            avatar_label.setStyleSheet("color: white; font-size: 8px; font-weight: bold;")
        
        # Message content with markdown support
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        content_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Ensure wrapping is based on the available width of the widget
        content_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        content_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        # Prefer expanding horizontally and minimal vertical growth (handled by auto-resize)
        content_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # Remove frame to avoid extra visual padding affecting height calc
        content_text.setFrameShape(QFrame.Shape.NoFrame)
        # Recalculate height when the widget is resized (e.g., sidebar width changes)
        content_text.installEventFilter(self)
        
        # Set content with markdown support
        if content.strip():
            content_text.setMarkdown(content)
        else:
            content_text.setPlainText(content)
        
        # Auto-resize based on content
        content_text.document().contentsChanged.connect(
            lambda: self._resize_message_widget(content_text)
        )
        content_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(100, 149, 237, 0.1);
                border: 1px solid rgba(100, 149, 237, 0.2);
                border-radius: 6px;
                padding: 10px 12px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                line-height: 1.4;
            }
        """)
        
        # Set initial size
        self._resize_message_widget(content_text)
        
        # Also schedule a post-layout resize in case width is not final yet
        QTimer.singleShot(0, lambda te=content_text: self._resize_message_widget(te))
        
        message_layout.addWidget(avatar_label)
        message_layout.addWidget(content_text, 1)
        
        # Store reference to content text for updates
        message_widget.content_label = content_text
        
        return message_widget

    def _resize_message_widget(self, text_edit):
        """Auto-resize QTextEdit based on content to show all content without scrolling.
        Uses the QTextEdit viewport width and the QTextDocument's layout size for accuracy.
        """
        try:
            if not isinstance(text_edit, QTextEdit):
                return

            # Determine the width available for text based on the current viewport
            viewport = text_edit.viewport()
            available_width = viewport.width()

            if available_width <= 0:
                # Fallback: approximate from widget width minus contents margins
                cm = text_edit.contentsMargins()
                available_width = max(50, text_edit.width() - (cm.left() + cm.right()))

            # Configure document for proper wrapping at the viewport width
            doc = text_edit.document()
            # Remove extra document margins to keep math predictable
            try:
                doc.setDocumentMargin(0)
            except Exception:
                pass
            doc.setTextWidth(float(available_width))

            # Force layout update before reading size
            try:
                layout = doc.documentLayout()
                if layout is not None:
                    # Trigger a layout update cycle
                    layout.update()
                    doc_height = layout.documentSize().height()
                else:
                    doc.adjustSize()
                    doc_height = doc.size().height()
            except Exception:
                doc.adjustSize()
                doc_height = doc.size().height()

            # Calculate total height including widget padding and contents margins
            cm = text_edit.contentsMargins()
            # Style padding in stylesheet: padding: 10px 12px; => 10 (top) + 10 (bottom)
            style_vertical_padding = 20
            # Small safety fudge to avoid any off-by-1 truncation from fractional metrics
            fudge = 2
            total_height = int(doc_height) + cm.top() + cm.bottom() + style_vertical_padding + fudge

            # Reasonable minimum height for empty/short messages
            final_height = max(40, total_height)

            # Apply the calculated height strictly so no internal scrollbar appears
            text_edit.setMinimumHeight(final_height)
            text_edit.setMaximumHeight(final_height)
            text_edit.setFixedHeight(final_height)

            # Ensure internal scrollbar position is reset
            if text_edit.verticalScrollBar() is not None:
                text_edit.verticalScrollBar().setValue(0)
        except (RuntimeError, AttributeError):
            # Widget may be in the process of being deleted
            pass

    def eventFilter(self, obj, event):
        """Recalculate bubble height when the QTextEdit resizes or font/style changes."""
        try:
            if isinstance(obj, QTextEdit):
                et = event.type()
                if et in (QEvent.Type.Resize, QEvent.Type.FontChange, QEvent.Type.StyleChange, QEvent.Type.Polish):
                    # Defer to end of event loop to ensure widths are final
                    QTimer.singleShot(0, lambda o=obj: self._resize_message_widget(o))
        except RuntimeError:
            pass
        return super().eventFilter(obj, event)

    def finish_ai_response(self):
        """Clean up after AI response completes."""
        if self.study_mode:
            # Study mode cleanup
            try:
                # Save the complete AI message to database
                if hasattr(self, '_current_ai_message') and self._current_ai_message is not None:
                    if hasattr(self._current_ai_message, 'content_label'):
                        # Get content from buffer or QTextEdit
                        if hasattr(self._current_ai_message, '_content_buffer'):
                            complete_message = self._current_ai_message._content_buffer
                        else:
                            complete_message = self._current_ai_message.content_label.toPlainText()
                        
                        if complete_message.strip():  # Only save non-empty messages
                            # Add to chat history
                            self.chat_history.append({"role": "assistant", "content": complete_message})
                            # Save to database
                            try:
                                self.db.save_chat_message(self.sentence, "assistant", complete_message)
                            except Exception as e:
                                print(f"Error saving AI message to database: {e}")
                
                # Flush any remaining content
                if hasattr(self, '_flush_main_content_buffer'):
                    self._flush_main_content_buffer(force_partial=True)
                
                # Reset AI responding state
                if hasattr(self, 'is_ai_responding'):
                    self.is_ai_responding = False
                
                # Update send button icon
                if hasattr(self, 'send_button'):
                    self.update_send_button_icon(False)
                
                # Clear current message reference
                if hasattr(self, '_current_ai_message'):
                    self._current_ai_message = None
                    
            except Exception as e:
                print(f"DEBUG: Error in study mode finish_ai_response: {e}")
        else:
            # Normal mode cleanup
            if hasattr(self, 'editor') and self.editor is not None:
                try:
                    # Clear the AI stream buffer to process any remaining content
                    self.editor.clear_ai_stream_buffer()
                    
                    # Stop AI button animation
                    self.editor.stop_ai_animation()
                    
                    if hasattr(self.editor, 'toolbar'):
                        self.editor.toolbar.ai_btn.setVisible(True)
                        self.editor.toolbar.stop_btn.setVisible(False)
                except RuntimeError:
                    # Object has been deleted, ignore
                    pass

    def stop_ai_explanation(self):
        """Stop AI explanation."""
        self.ollama_client.stop()
        
        # Reset AI responding state if in study mode
        if self.study_mode and hasattr(self, 'is_ai_responding'):
            self.is_ai_responding = False
            if hasattr(self, 'send_button'):
                self.update_send_button_icon(False)  # Switch back to send icon
            
            # Flush any remaining content
            if hasattr(self, '_flush_main_content_buffer'):
                self._flush_main_content_buffer(force_partial=True)
            
            # Clear current message reference
            if hasattr(self, '_current_ai_message'):
                self._current_ai_message = None
        
        # Stop AI button animation
        if hasattr(self, 'editor') and self.editor is not None:
            try:
                self.editor.stop_ai_animation()
                self.queue_ui_update('finish_ai')
            except RuntimeError:
                # Object has been deleted, ignore
                pass
    



class SidebarManager(QWidget):
    """Manager for sidebar functionality."""
    
    def __init__(self, parent=None, all_sentences_provider: callable = None):
        super().__init__(parent)
        self.current_sidebar = None
        self.active_sidebars = {}
        self.all_sentences_provider = all_sentences_provider
        self.study_mode = False
        self.setup_ui()
    
    def setup_ui(self):
        """Setup manager UI."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Ensure the SidebarManager uses full width
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Initially hidden
        self.hide()
    
    def show_sidebar(self, sentence: str, timestamp: float = None, fresh_conversation: bool = False):
        """Show sidebar with given sentence."""
        self.close_all_sidebars()

        all_sentences = self.all_sentences_provider() if self.all_sentences_provider else []
        # Create new sidebar
        sidebar = SidebarWidget(sentence, timestamp, all_sentences=all_sentences, study_mode=self.study_mode, fresh_conversation=fresh_conversation)
        sidebar.closed.connect(lambda: self.close_sidebar(sentence))
        self.active_sidebars[sentence] = sidebar
        
        # Add to layout
        self.layout.addWidget(sidebar)
        self.show()
    
    def set_study_mode(self, enabled: bool):
        """Set study mode for all sidebars."""
        self.study_mode = enabled
        # Update existing sidebars
        for sidebar in self.active_sidebars.values():
            sidebar.set_study_mode(enabled)

    def close_sidebar(self, sentence: str = None):
        """Close current sidebar."""
        if sentence and sentence in self.active_sidebars:
            sidebar = self.active_sidebars.pop(sentence)
            # Clean up resources properly
            if hasattr(sidebar, 'cleanup'):
                sidebar.cleanup()
            # Remove from layout first
            self.layout.removeWidget(sidebar)
            # Remove parent relationship
            sidebar.setParent(None)
            # Schedule for deletion
            sidebar.deleteLater()

        if not self.active_sidebars:
            self.hide()

    def get_all_notes(self) -> dict:
        """Get all notes from active sidebars."""
        notes = {}
        for sentence, sidebar in self.active_sidebars.items():
            notes[sentence] = sidebar.editor.get_content()
        return notes

    def load_notes(self, notes: dict):
        """Load notes into the sidebar."""
        self.close_all_sidebars()
        for sentence, content in notes.items():
            self.show_sidebar(sentence, fresh_conversation=False)
            self.active_sidebars[sentence].editor.set_content(content)

    def close_all_sidebars(self):
        """Close all active sidebars."""
        # Close all sidebars using the proper cleanup process
        for sentence in list(self.active_sidebars.keys()):
            self.close_sidebar(sentence)

    def clear_layout(self):
        """Clear all widgets from layout."""
        widgets_to_delete = []
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                widget = child.widget()
                widget.setParent(None)  # Remove parent relationship first
                widgets_to_delete.append(widget)
        
        # Schedule widgets for deletion
        for widget in widgets_to_delete:
            widget.deleteLater()
    
    def is_visible_sidebar(self) -> bool:
        """Check if sidebar is currently visible."""
        return self.current_sidebar is not None and self.isVisible()