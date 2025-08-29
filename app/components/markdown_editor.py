"""Markdown editor with toolbar for the sidebar."""

import os
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFrame, 
    QLabel, QScrollArea, QSizePolicy, QApplication
)
from PySide6.QtGui import (
    QIcon, QTextDocument, QTextCursor, QTextCharFormat, QFont, QPalette, QColor,
    QPainter, QConicalGradient, QPen
)
from PySide6.QtCore import QSize, Qt, Signal, QTimer, QPointF

# Import theme detection
from app.utils.app_utils import detect_system_theme


class MarkdownTextEdit(QTextEdit):
    """Custom QTextEdit that renders markdown without showing markers."""
    selection_format_changed = Signal(QTextCharFormat)

    # Pre-compile markdown patterns for efficiency
    MARKDOWN_PATTERNS = [
        re.compile(r'\*\*.*?\*\*'),       # Bold
        re.compile(r'\*.*?\*'),           # Italic
        re.compile(r'`.*?`'),             # Inline code
        re.compile(r'```.*?```', re.DOTALL), # Code blocks
        re.compile(r'^#{1,6}\s', re.MULTILINE), # Headers
        re.compile(r'^\*\s', re.MULTILINE),     # Bullet points
        re.compile(r'^\d+\.\s', re.MULTILINE),  # Numbered lists
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_text = ""
        self.is_updating = False
        self.last_cursor_position = 0
        self.thinking_content = ""
        self.thinking_widget = None

        # Remove the render timer to avoid cursor jumping issues
        
        # Reset any default document margins to ensure normal text positioning
        self.document().setDocumentMargin(0)
        
        self.setup_thinking_widget()
        self.textChanged.connect(self.on_text_changed)
        self.cursorPositionChanged.connect(self.on_cursor_position_changed)
        
        # Configure scrollbar to be thin without arrows and start with minimal padding
        self.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-family: 'SF Pro Text', 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QTextEdit QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 6px;
                border-radius: 3px;
            }
            QTextEdit QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 3px;
                min-height: 20px;
            }
            QTextEdit QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

    def on_cursor_position_changed(self):
        """Emit signal with the format of the current selection."""
        self.selection_format_changed.emit(self.currentCharFormat())
    
    def update_layout_spacing(self):
        """Update the main editor margins based on thinking widget visibility."""
        # Check if thinking widget should be visible (has content or is explicitly visible)
        has_thinking_content = (hasattr(self, 'thinking_text') and 
                               hasattr(self, 'thinking_widget') and
                               (self.thinking_widget.isVisible() or 
                                (self.thinking_text.toPlainText().strip() != "")))
        
        if has_thinking_content:
            # Thinking widget is visible or has content, add top margin to make room for it
            # Use same padding as editor (8px) for consistent spacing
            margin_top = self.thinking_widget.height() + 8
            # Ensure the widget is actually visible
            if not self.thinking_widget.isVisible():
                self.thinking_widget.setVisible(True)
                self.thinking_widget.setGeometry(10, 10, self.width() - 20, self.thinking_widget.height())
        else:
            # Thinking widget is hidden, use normal editor padding
            margin_top = 0  # No extra margin needed, just use the editor's natural padding
        
        # Use viewport margins to only affect the top, keeping full width
        self.setViewportMargins(0, margin_top, 0, 0)
        
        # Force a repaint to ensure the change takes effect
        self.update()
        self.repaint()

    def setup_thinking_widget(self):
        """Setup the thinking widget inside the text edit."""
        self.thinking_widget = QWidget(self)
        self.thinking_widget.setObjectName("thinking_widget")
        self.thinking_widget.setStyleSheet("""
            #thinking_widget {
                background: rgba(128, 128, 128, 0.1);
                border: 1px solid rgba(128, 128, 128, 0.3);
                border-radius: 4px;
                margin: 6px;
            }
        """)
        
        # Layout for thinking widget
        layout = QVBoxLayout(self.thinking_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Text area for thinking content - no scroll, just expand
        self.thinking_text = QTextEdit()
        self.thinking_text.setReadOnly(True)
        self.thinking_text.setMinimumHeight(60)
        self.thinking_text.setMaximumHeight(300)  # Limit max height
        
        # Disable scrollbars - widget will expand instead
        self.thinking_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.thinking_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Auto-resize based on content
        self.thinking_text.document().contentsChanged.connect(self.auto_resize_thinking_widget)
        
        # Styling for thinking content - smaller, grey text
        self.thinking_text.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.6);
                font-size: 11px;
                padding: 8px 10px;
                line-height: 1.4;
            }
        """)
        
        # Set font - smaller and lighter
        font = QFont()
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Light)
        self.thinking_text.setFont(font)
        
        layout.addWidget(self.thinking_text)
        
        # Create expand button container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 2, 0, 2)
        button_layout.setSpacing(0)
        button_layout.addStretch()
        
        # Small circular expand button
        self.expand_btn = QPushButton()
        self.expand_btn.setFixedSize(16, 16)
        self.expand_btn.setVisible(True)  # Always visible when thinking widget is shown
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background: rgba(128, 128, 128, 0.2);
                border: 1px solid rgba(128, 128, 128, 0.4);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(128, 128, 128, 0.3);
                border-color: rgba(128, 128, 128, 0.6);
                color: rgba(255, 255, 255, 1.0);
            }
            QPushButton:pressed {
                background: rgba(128, 128, 128, 0.4);
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_thinking_expand)
        
        # Initialize state before calling update_expand_button_icon
        self._thinking_expanded = False
        self.update_expand_button_icon()
        
        button_layout.addWidget(self.expand_btn)
        button_layout.addStretch()
        layout.addWidget(button_container)
        
        self.thinking_widget.setFixedHeight(95)  # Updated to match new minimum + margin
        self.thinking_widget.setVisible(False)
        
        # Initialize layout spacing
        self.update_layout_spacing()

    def auto_resize_thinking_widget(self):
        """Auto-resize thinking widget based on content."""
        if not hasattr(self, 'thinking_text') or not self.thinking_widget.isVisible():
            return
        
        # Get the document height
        doc = self.thinking_text.document()
        doc_height = doc.size().height()
        
        # Add padding and button container height (accounting for improved spacing)
        total_height = int(doc_height) + 35  # 35px for padding, margins, and button
        
        # Respect min/max heights
        min_height = 65
        max_height = 300 if self._thinking_expanded else 120
        
        final_height = max(min_height, min(max_height, total_height))
        
        # Only update if height changed significantly
        current_height = self.thinking_widget.height()
        if abs(final_height - current_height) > 5:
            self.thinking_widget.setFixedHeight(final_height)
            self.thinking_text.setFixedHeight(final_height - 35)
            self.update_layout_spacing()

    def toggle_thinking_expand(self):
        """Toggle thinking widget between normal and expanded size."""
        self._thinking_expanded = not self._thinking_expanded
        
        if self._thinking_expanded:
            # Expand to larger size
            self.thinking_text.setMaximumHeight(300)
        else:
            # Collapse to normal size
            self.thinking_text.setMaximumHeight(120)
        
        # Update expand button icon
        self.update_expand_button_icon()
        
        # Trigger auto-resize
        self.auto_resize_thinking_widget()

    def update_expand_button_icon(self):
        """Update the expand button icon based on current state."""
        if self._thinking_expanded:
            self.expand_btn.setText("↑")  # Collapse icon
        else:
            self.expand_btn.setText("↓")  # Expand icon

    def resizeEvent(self, event):
        """Handle resize events to reposition thinking widget."""
        super().resizeEvent(event)
        if hasattr(self, 'thinking_widget') and self.thinking_widget:
            # Position thinking widget at the top with better margins
            self.thinking_widget.setGeometry(10, 10, self.width() - 20, self.thinking_widget.height())

    def clear_thinking(self):
        """Clear thinking content and hide widget."""
        if hasattr(self, 'thinking_text'):
            self.thinking_text.clear()
        if hasattr(self, 'thinking_widget'):
            self.thinking_widget.setVisible(False)
        self.update_layout_spacing()

    def append_thinking_content(self, chunk):
        """Append content to thinking widget."""
        if hasattr(self, 'thinking_text'):
            # Position thinking widget if not already positioned
            if not self.thinking_widget.isVisible():
                self.thinking_widget.setGeometry(10, 10, self.width() - 20, self.thinking_widget.height())
            
            # Append content
            cursor = self.thinking_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(chunk)
            
            # Update layout spacing (this will handle visibility)
            self.update_layout_spacing()
            
            # The auto-resize will be triggered by the document contentsChanged signal

    def set_thinking_content(self, content):
        """Set thinking content and show widget."""
        if hasattr(self, 'thinking_text'):
            self.thinking_text.setPlainText(content)
            # Position thinking widget
            self.thinking_widget.setGeometry(10, 10, self.width() - 20, self.thinking_widget.height())
            # Update layout spacing (this will handle visibility)
            self.update_layout_spacing()

    def set_raw_text(self, text):
        """Set the raw text content."""
        self.raw_text = text
        self.is_updating = True
        # Store cursor position before setting text
        cursor = self.textCursor()
        cursor_position = cursor.position()
        
        self.setPlainText(text)
        
        # Restore cursor position if valid
        if cursor_position <= len(text):
            cursor.setPosition(cursor_position)
            self.setTextCursor(cursor)
        
        self.is_updating = False

    def on_text_changed(self):
        """Handle text changes - just update raw_text without any rendering."""
        if not self.is_updating:
            self.raw_text = self.toPlainText()

    def text_needs_formatting(self, text):
        """Check if text contains markdown that needs formatting."""
        # Disabled for now to keep editor simple
        return False

    def update_display(self):
        """Update the display - simplified to avoid cursor jumping."""
        # Do nothing to avoid cursor position issues
        pass
    
    def render_markdown(self):
        """Render markdown content in the text editor."""
        # Disabled to keep editor as simple plain text editor
        pass


class AnimatedAIButton(QPushButton):
    """AI button with rotating border animation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rotation_angle = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_rotation)
        self.is_animating = False
        
    def start_border_animation(self):
        """Start the rotating border animation."""
        if not self.is_animating:
            self.is_animating = True
            self.animation_timer.start(50)  # Update every 50ms for smooth animation
            
    def stop_border_animation(self):
        """Stop the rotating border animation."""
        if self.is_animating:
            self.is_animating = False
            self.animation_timer.stop()
            self.rotation_angle = 0
            self.update()
            
    def update_rotation(self):
        """Update rotation angle and repaint."""
        self.rotation_angle = (self.rotation_angle + 5) % 360
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event to draw rotating border."""
        super().paintEvent(event)
        
        if self.is_animating:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Create rotating gradient
            center = QPointF(self.width() / 2, self.height() / 2)
            gradient = QConicalGradient(center, self.rotation_angle)
            gradient.setColorAt(0.0, QColor(255, 0, 128, 255))    # Bright pink
            gradient.setColorAt(0.25, QColor(0, 212, 255, 255))   # Bright cyan
            gradient.setColorAt(0.5, QColor(255, 0, 128, 255))    # Bright pink
            gradient.setColorAt(0.75, QColor(0, 212, 255, 255))   # Bright cyan
            gradient.setColorAt(1.0, QColor(255, 0, 128, 255))    # Bright pink
            
            # Draw rotating border
            pen = QPen()
            pen.setBrush(gradient)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 4, 4)


class MarkdownToolbar(QWidget):
    """Toolbar for markdown editor."""
    
    ai_request = Signal()
    stop_request = Signal()
    bold_clicked = Signal()
    italic_clicked = Signal()
    code_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup toolbar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Format buttons
        self.bold_btn = QPushButton("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(28, 28)
        self.bold_btn.clicked.connect(self.bold_clicked.emit)
        layout.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(28, 28)
        self.italic_btn.clicked.connect(self.italic_clicked.emit)
        layout.addWidget(self.italic_btn)

        self.code_btn = QPushButton("<>")
        self.code_btn.setCheckable(True)
        self.code_btn.setFixedSize(28, 28)
        self.code_btn.clicked.connect(self.code_clicked.emit)
        layout.addWidget(self.code_btn)

        layout.addStretch()

        # AI button
        self.ai_btn = AnimatedAIButton()
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "ai.svg")
        if os.path.exists(icon_path):
            # Import the themed icon function
            from app.utils.app_utils import create_themed_icon_pixmap
            # Create white-themed icon for the AI button to match primary button
            white_icon_pixmap = create_themed_icon_pixmap(icon_path, size=16, theme='dark')  # Use dark theme to get white icon
            if white_icon_pixmap:
                self.ai_btn.setIcon(QIcon(white_icon_pixmap))
            else:
                self.ai_btn.setIcon(QIcon(icon_path))
        else:
            self.ai_btn.setText("AI")
        self.ai_btn.setIconSize(QSize(16, 16))
        self.ai_btn.setFixedSize(32, 28)
        self.ai_btn.clicked.connect(self.ai_request.emit)
        layout.addWidget(self.ai_btn)

        # Stop button
        self.stop_btn = QPushButton("■")
        self.stop_btn.setFixedSize(32, 28)
        self.stop_btn.clicked.connect(self.stop_request.emit)
        self.stop_btn.setVisible(False)  # Hidden by default
        layout.addWidget(self.stop_btn)

        # Apply styles
        self.apply_styles()

    def apply_styles(self):
        """Apply button styles."""
        button_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.8);
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
                color: rgba(255, 255, 255, 1.0);
            }
            QPushButton:checked {
                background: rgba(100, 150, 255, 0.3);
                border-color: rgba(100, 150, 255, 0.5);
            }
        """
        
        ai_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF0080, stop:1 #00D4FF);
                border: 1px solid transparent;
                border-radius: 4px;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF1493, stop:1 #00BFFF);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #DC143C, stop:1 #0099CC);
                border: 1px solid rgba(255, 255, 255, 0.5);
                color: white;
            }
        """
        
        stop_style = """
            QPushButton {
                background: rgba(255, 100, 100, 0.2);
                border: 1px solid rgba(255, 100, 100, 0.4);
                border-radius: 4px;
                color: rgba(255, 255, 255, 0.9);
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 100, 100, 0.3);
                border-color: rgba(255, 100, 100, 0.6);
                color: rgba(255, 255, 255, 1.0);
            }
        """
        
        self.bold_btn.setStyleSheet(button_style)
        self.italic_btn.setStyleSheet(button_style)
        self.code_btn.setStyleSheet(button_style)
        self.ai_btn.setStyleSheet(ai_style)
        self.stop_btn.setStyleSheet(stop_style)

    def update_format_buttons(self, fmt: QTextCharFormat):
        """Update button states based on character format."""
        self.bold_btn.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.italic_btn.setChecked(fmt.fontItalic())
        self.code_btn.setChecked(fmt.background() == Qt.GlobalColor.darkGray)
        
    def start_ai_animation(self):
        """Start AI button border animation."""
        self.ai_btn.start_border_animation()
        
    def stop_ai_animation(self):
        """Stop AI button border animation."""
        self.ai_btn.stop_border_animation()


class MarkdownEditor(QWidget):
    """Markdown editor with toolbar and auto-save functionality."""
    
    content_changed = Signal(str)
    ai_request = Signal()
    stop_request = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup editor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.toolbar = MarkdownToolbar()
        # Ensure toolbar uses full width
        self.toolbar.setMinimumWidth(0)
        self.toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.toolbar)

        # Use our custom MarkdownTextEdit which includes integrated thinking widget
        self.text_edit = MarkdownTextEdit()
        self.text_edit.setPlaceholderText("Write your notes here...")
        # Ensure text edit uses full width
        self.text_edit.setMinimumWidth(0)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.text_edit)
        
        # Ensure the MarkdownEditor itself uses full width
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-family: 'SF Pro Text', 'Segoe UI', sans-serif;
                font-size: 13px;
            }
        """)

        # Copy button for code blocks
        self.copy_button = QPushButton()
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "copy.svg")
        self.copy_button.setIcon(QIcon(icon_path))
        self.copy_button.setIconSize(QSize(16, 16))
        self.copy_button.setFixedSize(28, 28)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        self.copy_button.setParent(self.text_edit)
        self.copy_button.hide()
        self.copy_button.clicked.connect(self.copy_code_block)

        self.text_edit.cursorPositionChanged.connect(self.update_copy_button_position)
        self.text_edit.textChanged.connect(self.on_text_changed)

    def on_text_changed(self):
        """Handle text change for auto-save and emitting content changed signal."""
        self.content_changed.emit(self.get_content())

    def set_content(self, content: str):
        """Set editor content including thinking content."""
        # Parse think tags from content
        main_content, thinking_content = self.parse_think_tags(content)
        
        # Set thinking content first if present
        if thinking_content:
            self.text_edit.set_thinking_content(thinking_content)
        else:
            self.text_edit.clear_thinking()
        
        # Set main content
        self.text_edit.set_raw_text(main_content)

    def get_content(self) -> str:
        """Get the editor content as plain text."""
        main_content = self.text_edit.toPlainText()
        thinking_content = self.text_edit.thinking_text.toPlainText() if hasattr(self.text_edit, 'thinking_text') else ""
        
        # If there's thinking content, include it in the proper format
        if thinking_content.strip():
            return f"<think>\n{thinking_content}\n</think>\n\n{main_content}"
        else:
            return main_content

    def parse_think_tags(self, content: str) -> tuple[str, str]:
        """Parse think tags from content and return (main_content, thinking_content)."""
        think_pattern = r'<think>(.*?)</think>'
        think_match = re.search(think_pattern, content, re.DOTALL)
        
        if think_match:
            thinking_content = think_match.group(1).strip()
            main_content = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()
            return main_content, thinking_content
        else:
            return content.strip(), ""

    def append_thinking_content(self, chunk: str):
        """Append thinking content from AI stream."""
        self.text_edit.append_thinking_content(chunk)
    
    def append_ai_stream_content(self, chunk: str):
        """Handle AI streaming content, separating thinking from regular content."""
        if not hasattr(self, '_ai_stream_buffer'):
            self._ai_stream_buffer = ""
            self._inside_think_tags = False
            self._main_content_buffer = ""
            self._has_thinking_content = False
            self._potential_tag_buffer = ""
        
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
                        # We found a complete think tag - show the thinking widget
                        self._has_thinking_content = True
                        # Position and show thinking widget
                        self.text_edit.thinking_widget.setGeometry(10, 10, self.text_edit.width() - 20, self.text_edit.thinking_widget.height())
                        self.text_edit.update_layout_spacing()  # This will handle visibility and margins
                        
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
                        self.append_thinking_content(thinking_content)
                    
                    # Remove processed content and exit think mode (skip the closing tag)
                    self._ai_stream_buffer = self._ai_stream_buffer[think_end + 8:]  # +8 for '</think>'
                    self._inside_think_tags = False
                    continue
                else:
                    # No closing tag yet, add current content to thinking
                    if self._ai_stream_buffer.strip():
                        self.append_thinking_content(self._ai_stream_buffer)
                    self._ai_stream_buffer = ""
                    break
    
    def _flush_main_content_buffer(self, force_partial=True):
        """Flush the main content buffer, optionally waiting for complete words."""
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
            self._append_to_main_editor(content_to_add)
    
    def _append_to_main_editor(self, content: str):
        """Append content to the main editor."""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(content)
        self.text_edit.setTextCursor(cursor)
    
    def clear_ai_stream_buffer(self):
        """Clear the AI stream buffer."""
        if hasattr(self, '_ai_stream_buffer'):
            # Flush any remaining content
            if self._main_content_buffer:
                self._flush_main_content_buffer()
            
            # Reset all buffers
            self._ai_stream_buffer = ""
            self._inside_think_tags = False
            self._main_content_buffer = ""
            self._has_thinking_content = False
            self._potential_tag_buffer = ""
    
    def connect_signals(self):
        """Connect toolbar signals."""
        self.toolbar.ai_request.connect(self.ai_request)
        self.toolbar.stop_request.connect(self.stop_request)
        self.toolbar.bold_clicked.connect(self.toggle_bold)
        self.toolbar.italic_clicked.connect(self.toggle_italic)
        self.toolbar.code_clicked.connect(self.toggle_code)
        self.text_edit.selection_format_changed.connect(self.toolbar.update_format_buttons)

    def toggle_bold(self):
        """Toggle bold formatting."""
        cursor = self.text_edit.textCursor()
        fmt = cursor.charFormat()
        if fmt.fontWeight() == QFont.Weight.Bold:
            fmt.setFontWeight(QFont.Weight.Normal)
        else:
            fmt.setFontWeight(QFont.Weight.Bold)
        cursor.setCharFormat(fmt)

    def toggle_italic(self):
        """Toggle italic formatting."""
        cursor = self.text_edit.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        cursor.setCharFormat(fmt)

    def toggle_code(self):
        """Toggle code formatting."""
        cursor = self.text_edit.textCursor()
        fmt = cursor.charFormat()
        if fmt.background() == Qt.GlobalColor.darkGray:
            fmt.setBackground(Qt.GlobalColor.transparent)
        else:
            fmt.setBackground(Qt.GlobalColor.darkGray)
        cursor.setCharFormat(fmt)

    def update_copy_button_position(self):
        """Update copy button position based on cursor."""
        cursor = self.text_edit.textCursor()
        block = cursor.block()
        text = block.text()
        
        # Check if cursor is in a code block
        if text.strip().startswith('```') or '`' in text:
            rect = self.text_edit.cursorRect(cursor)
            self.copy_button.move(rect.right() + 5, rect.top())
            self.copy_button.show()
        else:
            self.copy_button.hide()

    def copy_code_block(self):
        """Copy the current code block to clipboard."""
        cursor = self.text_edit.textCursor()
        block = cursor.block()
        
        # Find the code block boundaries
        start_block = block
        end_block = block
        
        # Move to start of code block
        while start_block.previous().isValid() and not start_block.text().strip().startswith('```'):
            start_block = start_block.previous()
        
        # Move to end of code block
        while end_block.next().isValid() and not end_block.text().strip().endswith('```'):
            end_block = end_block.next()
        
        # Extract code content
        code_lines = []
        current_block = start_block.next()  # Skip opening ```
        while current_block.isValid() and current_block != end_block:
            code_lines.append(current_block.text())
            current_block = current_block.next()
        
        code_content = '\n'.join(code_lines)
        QApplication.clipboard().setText(code_content)
        
    def start_ai_animation(self):
        """Start AI button border animation."""
        self.toolbar.start_ai_animation()
        
    def stop_ai_animation(self):
        """Stop AI button border animation."""
        self.toolbar.stop_ai_animation()