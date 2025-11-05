"""
Modern UI Components
Futuristic PySide6 widgets with glassmorphism and dark theme styling.
"""

import math
import os
import platform
import time
import random
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTextEdit, QProgressBar, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, Signal, QSize, QPointF
from PySide6.QtGui import (
    QPainter, QLinearGradient, QRadialGradient, QConicalGradient, QColor, QBrush, QPen, QFont, 
    QFontMetrics, QPainterPath, QIcon, QPixmap
)


_theme_cache = None

def detect_system_theme():
    """
    Detect system theme across different operating systems and desktop environments.
    Caches the result for faster subsequent calls.
    Returns 'dark' or 'light'.
    """
    global _theme_cache
    if _theme_cache is not None:
        return _theme_cache

    system = platform.system().lower()
    
    try:
        if system == "darwin":  # macOS
            # Use a faster method to check system appearance
            try:
                # Use the `defaults` command for quick theme detection
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True, text=True, timeout=0.5  # Reduced timeout
                )
                if result.returncode == 0 and 'Dark' in result.stdout:
                    _theme_cache = 'dark'
                    return 'dark'
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fallback or default
                pass
                
        elif system == "windows":  # Windows
            try:
                import winreg
                # Check Windows registry for theme setting
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return 'light' if value == 1 else 'dark'
            except (ImportError, OSError, FileNotFoundError):
                pass
                
        elif system == "linux":  # Linux
            # Try different methods for various desktop environments
            
            # Method 1: Check GNOME/GTK theme
            try:
                result = subprocess.run([
                    'gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'
                ], capture_output=True, text=True, timeout=2)
                
                if result.returncode == 0:
                    theme = result.stdout.strip().lower()
                    if 'dark' in theme:
                        return 'dark'
                    elif 'light' in theme:
                        return 'light'
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Method 2: Check KDE Plasma theme
            try:
                result = subprocess.run([
                    'kreadconfig5', '--group', 'General', '--key', 'ColorScheme'
                ], capture_output=True, text=True, timeout=2)
                
                if result.returncode == 0:
                    theme = result.stdout.strip().lower()
                    if 'dark' in theme or 'breeze dark' in theme:
                        return 'dark'
                    elif 'light' in theme:
                        return 'light'
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Method 3: Check environment variables
            desktop_session = os.environ.get('DESKTOP_SESSION', '').lower()
            xdg_current_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            
            # Check for dark theme indicators in environment
            if any(dark_indicator in env_var for env_var in [desktop_session, xdg_current_desktop] 
                   for dark_indicator in ['dark', 'night']):
                return 'dark'
            
            # Method 4: Check GTK settings file
            try:
                gtk_config_paths = [
                    os.path.expanduser('~/.config/gtk-3.0/settings.ini'),
                    os.path.expanduser('~/.gtkrc-2.0'),
                    '/etc/gtk-3.0/settings.ini'
                ]
                
                for config_path in gtk_config_paths:
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            content = f.read().lower()
                            if 'dark' in content and ('theme' in content or 'gtk' in content):
                                return 'dark'
                            elif 'light' in content and ('theme' in content or 'gtk' in content):
                                return 'light'
            except (IOError, OSError):
                pass
                
    except Exception as e:
        print(f"Error detecting system theme: {e}")
    
    # Default fallback - assume dark theme for this futuristic app
    _theme_cache = 'dark'
    return 'dark'


def get_icon_color_for_theme(theme='dark'):
    """
    Get the appropriate icon color based on the system theme.
    Returns a QColor object.
    """
    if theme == 'dark':
        return QColor(255, 255, 255, 230)  # White with slight transparency
    else:
        return QColor(30, 30, 30, 230)     # Dark gray with slight transparency


def create_themed_icon_pixmap(svg_path, size=24, theme=None, force_color=None):
    """
    Create a themed icon pixmap from SVG with appropriate colors.
    """
    if not os.path.exists(svg_path):
        return None
    
    if force_color:
        # Use the forced color
        if isinstance(force_color, str):
            # Convert string color to QColor
            if force_color.startswith('#'):
                icon_color = QColor(force_color)
            else:
                icon_color = QColor(force_color)
        else:
            icon_color = force_color
    else:
        if theme is None:
            theme = detect_system_theme()
        icon_color = get_icon_color_for_theme(theme)
    
    try:
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtGui import QPixmap, QPainter
        
        # Read SVG content
        with open(svg_path, 'r') as f:
            svg_content = f.read()
        
        # Replace currentColor with our theme-appropriate color
        color_hex = f"#{icon_color.red():02x}{icon_color.green():02x}{icon_color.blue():02x}"
        themed_svg = svg_content.replace('currentColor', color_hex)
        
        # Create pixmap from modified SVG with proper cleanup
        svg_renderer = QSvgRenderer()
        if svg_renderer.load(themed_svg.encode('utf-8')):
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                svg_renderer.render(painter)
            finally:
                painter.end()  # Ensure painter is always closed
            
            return pixmap
        else:
            print(f"Failed to load SVG: {svg_path}")
            return None
        
    except Exception as e:
        print(f"Error creating themed icon: {e}")
        return None


class ScaleControlOverlay(QWidget):
    """Overlay widget for scale control buttons that stay fixed in position."""
    
    def __init__(self, waveform_widget, parent=None):
        super().__init__(parent)
        self.waveform_widget = waveform_widget
        self.setFixedSize(70, 30)  # Smaller size for compact buttons
        
        # Make the widget transparent to clicks except on buttons
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # Set up styling
        self.setStyleSheet("background: transparent;")
        
    def paintEvent(self, event):
        """Draw the scale control buttons."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Button styling
        button_color = QColor(40, 40, 50, 220)
        border_color = QColor(80, 80, 90, 180)
        icon_color = QColor(255, 255, 255, 240)
        
        # Button size and positions - smaller and more compact
        button_size = 22
        spacing = 6
        
        # Minus button rect
        minus_rect = QRect(5, 4, button_size, button_size)
        # Plus button rect  
        plus_rect = QRect(5 + button_size + spacing, 4, button_size, button_size)
        
        # Store rects for click detection
        self.minus_rect = minus_rect
        self.plus_rect = plus_rect
        
        # Draw minus button
        painter.setBrush(QBrush(button_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(minus_rect)
        
        # Draw minus icon
        painter.setPen(QPen(icon_color, 1.5))
        center_y = minus_rect.center().y()
        margin = 5
        painter.drawLine(
            minus_rect.left() + margin, center_y,
            minus_rect.right() - margin, center_y
        )
        
        # Draw plus button
        painter.setBrush(QBrush(button_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(plus_rect)
        
        # Draw plus icon
        painter.setPen(QPen(icon_color, 1.5))
        center_x = plus_rect.center().x()
        center_y = plus_rect.center().y()
        # Horizontal line
        painter.drawLine(
            plus_rect.left() + margin, center_y,
            plus_rect.right() - margin, center_y
        )
        # Vertical line
        painter.drawLine(
            center_x, plus_rect.top() + margin,
            center_x, plus_rect.bottom() - margin
        )
    
    def mousePressEvent(self, event):
        """Handle button clicks."""
        if event.button() == Qt.MouseButton.LeftButton:
            click_pos = event.position().toPoint()
            
            if hasattr(self, 'minus_rect') and self.minus_rect.contains(click_pos):
                self.waveform_widget.decrease_scale()
                return
            elif hasattr(self, 'plus_rect') and self.plus_rect.contains(click_pos):
                self.waveform_widget.increase_scale()
                return
        



class AudioWaveformWidget(QWidget):
    """Principal audio waveform visualization - the main element of the app."""
    
    # Signal for when playback position changes via dragging
    playback_position_changed = Signal(float)
    # Signal for scrubbing (playing audio while dragging)
    scrubbing_position_changed = Signal(float)
    # Signal for when a note is requested
    note_requested = Signal(str, str, str, float, float, object)  # sentence_id, text, note_text, start_time, end_time, bubble_rect

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(300)
        # Prevent the widget from capturing focus to avoid focus on the white progress line
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.audio_duration = 0
        
        # Animation properties
        self.animation_offset = 0
        self.animation_phase = 0

        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_mode = "idle"  # "idle", "transcribing", "playing"
        
        # Performance optimization: Pre-allocate arrays and cache calculations
        self.cached_bar_heights = []
        self.cached_bar_count = 0
        self.last_width = 0
        self.performance_counter = 0
        
        # Waveform visualization properties
        self.wave_bars = 50  # Reduced from 100 to 50 for better performance
        self.bar_heights = [0.1] * self.wave_bars  # Heights of each bar
        self.scan_position = 0.0  # Position of the scanning beam (0.0 to 1.0)
        self.scan_direction = 1  # Direction of the scanning beam (1 or -1)
        
        # Layout caching for performance
        self.layout_cache = {}
        self.last_rect_size = (0, 0)
        self.icon_positions = []  # For click detection
        
        # Audio levels for animation (circular buffer for performance)
        self.audio_levels = [0.0] * 50  # Reduced buffer size for better performance
        self.audio_level_index = 0
        
        # Playback and interaction
        self.progress = 0.0
        self.is_dragging = False
        self.drag_start_pos = None
        
        # Annotations for transcribed text segments
        self.annotations = []
        self.text_annotations = []
        self.active_segment_index = -1
        
        # Transcription state
        self.transcription_finished = False
        
        # Animation properties for smooth bubble transitions
        self.bubble_animation_progress = {}
        self._bubble_animations = {}
        
        # Notes database reference (will be set by parent)
        self.notes_db = None
        
        # Timeline scale controls
        self.timeline_scale = 1.0  # Default scale factor
        self.min_scale = 0.5       # Minimum zoom out
        self.max_scale = 5.0       # Maximum zoom in
        self.scale_step = 0.2      # Scale increment/decrement step
        
    def set_bubble_progress(self, index, progress):
        """Qt property setter for bubble animation progress."""
        self.bubble_animation_progress[index] = progress
        self.update()

    def increase_scale(self):
        """Increase the timeline scale (zoom in)."""
        new_scale = min(self.timeline_scale + self.scale_step, self.max_scale)
        if new_scale != self.timeline_scale:
            self.timeline_scale = new_scale
            self._apply_scale_change()
    
    def decrease_scale(self):
        """Decrease the timeline scale (zoom out)."""
        new_scale = max(self.timeline_scale - self.scale_step, self.min_scale)
        if new_scale != self.timeline_scale:
            self.timeline_scale = new_scale
            self._apply_scale_change()
    
    def _apply_scale_change(self):
        """Apply the scale change to the widget width and update display."""
        if hasattr(self, 'audio_duration') and self.audio_duration > 0:
            # Store current playback position before scaling
            current_time = self.progress * self.audio_duration if hasattr(self, 'progress') else 0
            
            # Recalculate width based on new scale
            base_width = 800 * self.timeline_scale
            duration_width = base_width + min(self.audio_duration * 30 * self.timeline_scale, 1200 * self.timeline_scale)
            
            # If we have transcription segments, scale their layout too
            if hasattr(self, 'annotations') and self.annotations:
                transcription_count = sum(1 for ann in self.annotations if ann.get('is_transcription', False))
                if transcription_count > 0:
                    bubble_width = 400 * self.timeline_scale
                    bubble_spacing = 50 * self.timeline_scale
                    header_width = 25
                    right_padding = 100
                    content_width = (transcription_count * (bubble_width + bubble_spacing)) + header_width + right_padding
                    duration_width = max(content_width, duration_width)
            
            self.setMinimumWidth(int(duration_width))
            
            # Adjust scroll position to keep current playback position visible
            if hasattr(self, 'scroll_area') and self.scroll_area and current_time > 0:
                # Calculate new position of the playback line using same margin as timeline
                margin = 15  # Match timeline margin exactly
                header_width = 1  # Match timeline header width exactly
                available_width = int(duration_width) - (2 * margin) - header_width
                pixels_per_second = available_width / self.audio_duration
                new_playback_x = margin + header_width + (current_time * pixels_per_second)
                
                # Get current scroll position and visible area
                scroll_bar = self.scroll_area.horizontalScrollBar()
                visible_width = self.scroll_area.viewport().width()
                
                # Center the playback position in the visible area
                new_scroll = max(0, new_playback_x - (visible_width * 0.5))
                scroll_bar.setValue(int(new_scroll))
            
            # Invalidate background cache to force redraw of timeline and waveform elements
            self.background_cache_valid = False
            self.background_pixmap = None  # Also invalidate pixmap cache
            
            # Recalculate bar data for the new scale
            self._recalculate_bar_data(self.rect().width())
            
            self.update()
    
    def get_scale_button_rects(self, widget_rect):
        """Get the rectangles for the scale control buttons with fixed positioning."""
        button_size = 24  # Smaller circular buttons
        margin = 12
        spacing = 6
        
        # Use widget's actual geometry for fixed positioning (not affected by scrolling)
        widget_rect = self.rect()
        
        # Position buttons in bottom right corner of the widget (fixed position)
        plus_rect = QRect(
            widget_rect.right() - button_size - margin,
            widget_rect.bottom() - button_size - margin,
            button_size,
            button_size
        )
        
        minus_rect = QRect(
            widget_rect.right() - (button_size * 2) - margin - spacing,
            widget_rect.bottom() - button_size - margin,
            button_size,
            button_size
        )
        
        return minus_rect, plus_rect
        
    def get_bubble_progress(self, index):
        """Qt property getter for bubble animation progress."""
        return self.bubble_animation_progress.get(index, 0.0)

    def set_audio_duration(self, duration):
        """Set the audio duration to calculate the widget's width."""
        self.audio_duration = duration
        
        # Calculate width based on content needs for proper scrolling
        base_width = 800   # Base width for the waveform
        
        # If we have transcription segments, calculate width needed for all bubbles
        if hasattr(self, 'annotations') and self.annotations:
            # Count transcription segments
            transcription_count = sum(1 for ann in self.annotations if ann.get('is_transcription', False))
            
            if transcription_count > 0:
                # Calculate width needed for bubbles with padding
                bubble_width = 400  # Max bubble width
                bubble_spacing = 50  # Space between bubbles
                header_width = 25   # Track header width
                right_padding = 100  # Extra padding on the right for scrolling
                
                # Calculate total width needed for all bubbles in a single row
                content_width = (transcription_count * (bubble_width + bubble_spacing)) + header_width + right_padding
                
                # Use the larger of duration-based width or content-based width
                duration_width = base_width + min(duration * 30, 1200)
                new_width = max(content_width, duration_width)
            else:
                # No transcription segments, use duration-based width
                new_width = base_width + min(duration * 30, 1200)
        else:
            # No annotations yet, use duration-based width
            new_width = base_width + min(duration * 30, 1200)
        
        self.setMinimumWidth(int(new_width))
        
        # Set minimum height to enable vertical scrolling
        # Height should be larger than typical viewport to enable scrolling
        min_height = 800  # Minimum height for vertical scrolling
        self.setMinimumHeight(min_height)
        
        self.update()
        
        # Performance: Enable double buffering and reduce repaints
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)  # Ensure background is cleared
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.transparent)
        self.setPalette(palette)
        
        # Performance: Cache drawing objects to avoid recreating them
        self.cached_gradient = None
        self.cached_colors = {}
        self.cached_pens = {}
        self.background_pixmap = None
        self.background_cache_valid = False
        self._init_cached_drawing_objects()
        
        # Set fixed update policy for better performance
        self.setUpdatesEnabled(True)
        
        # Start idle animation immediately for visual feedback
        self.start_animation("idle")
    
    def _init_cached_drawing_objects(self):
        """Initialize cached drawing objects to avoid recreating them during paint events."""
        # Cache commonly used colors
        self.cached_colors = {
            'grid_light': QColor(255, 255, 255, 20),
            'grid_center': QColor(255, 255, 255, 40),
            'cyan': QColor(0, 255, 255, 220),      # Electric Blue
            'blue': QColor(0, 100, 255, 220),      # Bright Blue
            'purple': QColor(255, 0, 255, 200),    # Vibrant Pink
            'magenta': QColor(57, 255, 20, 200),     # Lime Green
            'progress_line': QColor(255, 255, 255, 255),
            'progress_glow': QColor(255, 255, 255, 100),
            'scan_beam': QColor(255, 255, 0, 200),
            'scan_active': QColor(255, 255, 0, 200),
            'scan_inactive': QColor(100, 150, 255, 80)
        }
        
        # Cache commonly used pens
        self.cached_pens = {
            'grid_light': QPen(self.cached_colors['grid_light'], 1),
            'grid_center': QPen(self.cached_colors['grid_center'], 1),
            'progress_line': QPen(self.cached_colors['progress_line'], 1),  # Changed from 4 to 1 for thin line
            'progress_glow': QPen(self.cached_colors['progress_glow'], 2),  # Changed from 8 to 2 for subtle glow
            'scan_beam': QPen(self.cached_colors['scan_beam'], 3),
            'waveform_outline': QPen(QColor(255, 255, 255, 100), 1)
        }
        
        # Create cached gradient for waveform
        self.cached_gradient = QLinearGradient(0, 0, 1, 0)
        self.cached_gradient.setColorAt(0.0, self.cached_colors['cyan'])
        self.cached_gradient.setColorAt(0.4, self.cached_colors['purple'])
        self.cached_gradient.setColorAt(0.8, self.cached_colors['magenta'])
        self.cached_gradient.setColorAt(1.0, self.cached_colors['blue'])
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging playback line and icon clicks."""
        if event.button() == Qt.MouseButton.LeftButton:
            click_pos = event.position().toPoint()
            rect = self.rect()
            
            # Scale controls are now handled by separate overlay widgets
            
            # Check if click is on an icon
            for i, icon_info in enumerate(self.icon_positions):
                if icon_info['rect'].contains(click_pos):
                    annotation_index = icon_info['annotation_index']
                    
                    if annotation_index < len(self.annotations):
                        annotation = self.annotations[annotation_index]
                        
                        # Get the actual sentence ID from the annotation (set by notes manager)
                        sentence_id = annotation.get('sentence_id', annotation_index)
                        
                        if icon_info['type'] == 'plus':
                            # Get the bubble rectangle for positioning
                            bubble_rect = icon_info.get('bubble_rect')
                            
                            # Check for existing note
                            note_text = ""
                            if self.notes_db:
                                note_result = self.notes_db.get_note(str(sentence_id))
                                note_text = note_result[2] if note_result else ""

                            # Emit note requested signal with bubble positioning
                            self.note_requested.emit(
                                str(sentence_id),
                                annotation.get('text', ''),
                                note_text,
                                annotation.get('start_time', 0),
                                annotation.get('end_time', 0),
                                bubble_rect  # Pass bubble rectangle for positioning
                            )
                    return
            # If no icon clicked, handle waveform interaction
            # Use same margin calculation as timeline for consistency
            margin = 15  # Match timeline margin exactly
            header_width = 1  # Match timeline header width exactly
            waveform_rect = rect.adjusted(margin + header_width, margin, -(margin + header_width), -margin)
            
            # Check if click is within waveform area
            if waveform_rect.contains(event.position().toPoint()):
                # Calculate new progress position
                relative_x = event.position().x() - waveform_rect.left()
                new_progress = max(0.0, min(1.0, relative_x / waveform_rect.width()))
                
                self.progress = new_progress
                self.is_dragging = True
                self.drag_start_pos = event.position()
                
                # Stop animation during dragging to prevent glitches
                self.was_animating = self.animation_timer.isActive()
                if self.was_animating:
                    self.animation_timer.stop()
                
                # Emit signal to update audio playback position
                self.playback_position_changed.emit(new_progress)
                self.update()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement for ultra-smooth dragging and bubble hover effects."""
        rect = self.rect()
        # Use same margin calculation as timeline for consistency
        margin = 15  # Match timeline margin exactly
        header_width = 1  # Match timeline header width exactly
        waveform_rect = rect.adjusted(margin + header_width, margin, -margin, -margin)
        
        if self.is_dragging and waveform_rect.contains(event.position().toPoint()):
            # Ultra-smooth progress calculation with sub-pixel precision
            relative_x = event.position().x() - waveform_rect.left()
            new_progress = max(0.0, min(1.0, relative_x / waveform_rect.width()))
            
            # Always update for ultra-smooth dragging
            self.progress = new_progress
            
            # Throttle scrubbing signals to prevent audio flickering
            current_time = time.time()
            if not hasattr(self, 'last_scrub_time'):
                self.last_scrub_time = 0
            
            # Only emit scrubbing signal every 100ms to prevent audio restart flickering
            if current_time - self.last_scrub_time > 0.1:  # 100ms throttle
                self.scrubbing_position_changed.emit(new_progress)
                self.last_scrub_time = current_time
            
            # Force immediate ultra-smooth update during dragging
            self.repaint()  # Use repaint for immediate visual feedback
        else:
            # Handle bubble hover detection
            self._handle_bubble_hover(event.position())
        

    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.drag_start_pos = None
            
            # Emit signal to seek to final position and stop audio
            self.playback_position_changed.emit(self.progress)
            
            # Single update to refresh the display after dragging
            self.update()
        

    
    def update_active_segment(self, current_time):
        """Update the active segment based on current audio playback time with smooth animation."""
        old_active = self.active_segment_index
        self.active_segment_index = -1
        
        # Find which segment is currently playing
        for i, annotation in enumerate(self.annotations):
            if annotation.get('is_transcription', False):
                start_time = annotation.get('start_time', 0)
                end_time = annotation.get('end_time', 0)
                
                if start_time <= current_time <= end_time:
                    self.active_segment_index = i
                    break
        
        # Update display if active segment changed
        if old_active != self.active_segment_index:
            # Initialize animation progress for smooth transitions
            if not hasattr(self, 'bubble_animation_progress'):
                self.bubble_animation_progress = {}
            
            # Reset animation for new active bubble
            for i in range(len(self.annotations)):
                if i not in self.bubble_animation_progress:
                    self.bubble_animation_progress[i] = 0.0
            
            # Use QPropertyAnimation for smooth transitions
            self.start_bubble_animation_timer()
    
    def get_dynamic_layout(self, rect):
        """Get or calculate dynamic layout that adapts to window size."""
        current_size = (rect.width(), rect.height())
        
        # Check if we need to recalculate layout
        if (self.last_rect_size != current_size or 
            current_size not in self.layout_cache):
            
            # Calculate optimal layout for current window size
            available_height = rect.height() - 60  # Adaptive margin
            available_width = rect.width() - 40   # Adaptive margin
            
            # Dynamic zone height baseline (will be overridden by bubble dynamic height when drawing)
            zone_height = 90  # Bigger baseline so longer text has space
            
            # Allow unlimited zones - don't constrain by available height
            # This enables infinite vertical scrolling of bubbles
            max_zones = 999  # Effectively unlimited
            
            # Use reasonable bubble width that allows for good text display
            # but doesn't take the entire widget width
            max_bubble_width = min(400, available_width * 0.6)  # Max 400px or 60% of available width
            
            layout = {
                'zone_height': zone_height,
                'max_zones': max_zones,
                'max_bubble_width': max_bubble_width,
                'available_height': available_height,
                'available_width': available_width
            }
            
            self.layout_cache[current_size] = layout
            self.last_rect_size = current_size
            
            return layout
        
        return self.layout_cache[current_size]
    
    def get_audio_level(self):
        """Get current audio level for reactive waveform animation."""
        # This is a simulation. For a real implementation, you'd need a library
        # that can provide real-time audio levels from the stream.
        if self.animation_mode == "playing":
            # Simulate a dynamic level for playing
            return 0.2 + (math.sin(time.time() * 10) * 0.1 + 0.1)
        return 0.1  # Minimal level when not playing
    
    def update_audio_levels(self):
        """Update the audio levels buffer for smooth, beautiful waveform animation."""
        import math
        import random
        
        # Reduce wave bars for better performance (from default to 32)
        if not hasattr(self, 'wave_bars'):
            self.wave_bars = 32  # Reduced from potentially higher number
            
        if not hasattr(self, 'bar_heights'):
            self.bar_heights = [0.3] * self.wave_bars

        # Get current audio level for reactive animation
        current_audio_level = self.get_audio_level()

        # Create smooth flowing waves based on animation mode
        time_factor = self.animation_phase * 0.05  # Smooth time progression
        
        if self.animation_mode == "playing":
            # Audio-reactive waveform using real audio levels
            for i in range(self.wave_bars):
                x_pos = i / self.wave_bars
                
                # Base waves influenced by audio
                audio_influence = (current_audio_level - 0.5) * 0.8  # Strong audio influence
                wave1 = 0.4 * math.sin(x_pos * 8 + time_factor * 2 + audio_influence * 3)
                wave2 = 0.3 * math.sin(x_pos * 12 + time_factor * 1.5 + audio_influence * 2)
                
                # Audio-reactive variation
                audio_variation = audio_influence * 0.3 * math.sin(x_pos * 10 + time_factor * 3)
                
                # Combine waves for audio-reactive pattern
                combined_wave = wave1 + wave2 + audio_variation
                
                # Final height with smooth envelope and audio reactivity
                envelope = 0.3 + 0.7 * (1 - abs(x_pos - 0.5) * 1.5)  # Center emphasis
                base_height = max(0.1, abs(combined_wave) * envelope + 0.2)
                
                # Apply audio level scaling
                audio_scale = 0.5 + current_audio_level * 0.8  # Scale based on audio level
                self.bar_heights[i] = base_height * audio_scale
                
        elif self.animation_mode == "transcribing":
            # Scanning wave effect for transcription
            scan_pos = (time_factor * 0.5) % 2.0  # Scanning position 0-2
            
            for i in range(self.wave_bars):
                x_pos = i / self.wave_bars
                
                # Base flowing wave
                base_wave = 0.3 * math.sin(x_pos * 6 + time_factor)
                
                # Scanning beam effect
                scan_distance = abs(x_pos - (scan_pos % 1.0))
                scan_intensity = max(0, 1.0 - scan_distance * 8)  # Sharp scanning beam
                
                # Combine base wave with scanning effect
                height = abs(base_wave) + scan_intensity * 0.5 + 0.2
                self.bar_heights[i] = max(0.15, min(1.0, height))
                
        else:
            # Idle mode - gentle, slow breathing effect
            for i in range(self.wave_bars):
                x_pos = i / self.wave_bars
                
                # Gentle breathing wave
                breath_wave = 0.2 * math.sin(x_pos * 4 + time_factor * 0.3)
                base_height = 0.25 + abs(breath_wave)
                
                # Subtle center emphasis
                center_factor = 1.0 - abs(x_pos - 0.5) * 0.5
                self.bar_heights[i] = base_height * center_factor
    
    def start_animation(self, mode="transcribing"):
        """Start the waveform animation with specified mode and optimized performance."""
        self.animation_mode = mode
        self.animation_phase = 0
        
        # Initialize hover tracking for bubbles
        if not hasattr(self, 'hovered_bubble_index'):
            self.hovered_bubble_index = -1
        if not hasattr(self, 'previous_hovered_bubble'):
            self.previous_hovered_bubble = -1
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Optimized timer intervals for smooth animation without excessive CPU usage
        if mode == "transcribing":
            self.animation_timer.start(80)   # 12.5 FPS - smooth scanning effect
        elif mode == "playing":
            self.animation_timer.start(66)   # 15 FPS - smooth audio-reactive animation (reduced from 30 FPS)
        else:
            self.animation_timer.start(150)  # 6.7 FPS - gentle idle breathing
    
    def stop_animation(self):
        """Stop waveform animation."""
        self.animation_timer.stop()
        self.animation_mode = "idle"
        self.update()
    

    
    def get_audio_level(self):
        """Get current audio level for reactive waveform animation."""
        try:
            import pygame
            import numpy as np
            
            # Check if audio is playing
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                # Try to get real audio data if available
                try:
                    # Get the current playback position to simulate audio levels
                    # Since pygame.mixer doesn't provide direct audio data access,
                    # we'll create a more realistic simulation based on time
                    import time
                    current_time = time.time()
                    
                    # Create multiple frequency bands for more realistic audio simulation
                    base_freq1 = np.sin(current_time * 8.0) * 0.3  # Low frequency
                    base_freq2 = np.sin(current_time * 15.0) * 0.2  # Mid frequency  
                    base_freq3 = np.sin(current_time * 25.0) * 0.15  # High frequency
                    
                    # Add some randomness to simulate real audio variation
                    import random
                    noise = (random.random() - 0.5) * 0.3
                    
                    # Combine frequencies for more realistic audio level
                    audio_level = 0.5 + base_freq1 + base_freq2 + base_freq3 + noise
                    
                    # Ensure level is within bounds
                    return max(0.1, min(1.0, audio_level))
                    
                except Exception:
                    # Fallback to simple variation
                    import random
                    base_level = 0.5 + 0.4 * random.random()
                    return max(0.2, min(1.0, base_level))
            else:
                return 0.1  # Minimal level when not playing
        except:
            return 0.1
    
    def stop_animation(self):
        """Stop the waveform animation."""
        # If we were transcribing, mark transcription as finished
        if self.animation_mode == "transcribing":
            self.transcription_finished = True
        self.animation_timer.stop()
        self.animation_mode = "idle"
        self.wave_amplitude = 0.1  # Minimal amplitude when idle
        self.background_cache_valid = False  # Invalidate background cache
        self.update()
    
    def set_transcription_finished(self, finished=True):
        """Set the transcription finished state."""
        self.transcription_finished = finished
        if finished:
            self.animation_mode = "idle"
            self.animation_timer.stop()
        self.update()
    
    def set_progress(self, progress):
        """Set playback progress (0.0 to 1.0)."""
        self.progress = max(0.0, min(1.0, progress))
        self.update()
    
    def add_annotation(self, position, text):
        """Add annotation at specific position (0.0 to 1.0)."""
        self.annotations.append({"position": position, "text": text})
        self.update()
    
    def add_text_annotation(self, start_time, end_time, text):
        """Add text annotation with timestamp information."""
        # Store the actual audio duration for better positioning
        if not hasattr(self, 'audio_duration'):
            self.audio_duration = 60.0  # Default
        
        # Calculate position based on actual duration
        position = min(start_time / max(self.audio_duration, 1.0), 1.0)
        
        # Store additional timestamp info
        annotation = {
            "position": position,
            "text": text,
            "start_time": start_time,
            "end_time": end_time,
            "is_transcription": True
        }
        self.annotations.append(annotation)
        
        # Also store in text_annotations for copying functionality
        self.text_annotations.append(annotation)
        
        self.update()
    
    def load_audio(self, file_path):
        """Load audio file and prepare waveform visualization."""
        try:
            import soundfile as sf
            
            # Load audio file to get duration and basic info
            with sf.SoundFile(file_path) as f:
                self.audio_duration = f.frames / f.samplerate
                self.audio_file_path = file_path
            
            # Clear any existing annotations
            self.clear_annotations()
            
            # Reset progress
            self.progress = 0.0
            
            # Update display
            self.update()
            
        except Exception as e:
            print(f"Error loading audio file in waveform widget: {e}")
            self.audio_duration = 0
            self.audio_file_path = None

    def set_playback_position(self, current_time):
        """Set the current playback position for the progress indicator."""
        if hasattr(self, 'audio_duration') and self.audio_duration > 0:
            self.progress = current_time / self.audio_duration
        else:
            self.progress = 0.0
        
        # Auto-scroll the waveform when playback position approaches the end of visible area
        self._auto_scroll_to_playback_position()
        
        # Update active segment based on current time
        self.update_active_segment(current_time)
        self.update()
    
    def _auto_scroll_to_playback_position(self):
        """Auto-scroll disabled to allow free scrolling."""
        pass

    def set_transcription_segments(self, segments):
        """Set transcription segments and adjust waveform width to fit them."""
        self.clear_annotations()
        if not segments:
            self.update()
            return

        max_end_time = 0
        for i, segment in enumerate(segments):
            end_time = segment.get('end', 0)
            if end_time > max_end_time:
                max_end_time = end_time

            annotation = {
                'text': segment.get('text', ''),
                'start_time': segment.get('start', 0),
                'end_time': end_time,
                'is_transcription': True,
                'sentence_id': i
            }
            self.annotations.append(annotation)

        display_duration = max(getattr(self, 'audio_duration', 0), max_end_time)
        self.set_audio_duration(display_duration)

        for ann in self.annotations:
            if ann.get('is_transcription'):
                ann['position'] = min(ann['start_time'] / max(display_duration, 1), 1.0)

        # Create annotations with indices for zone distribution
        annotations_with_indices = [(i, ann) for i, ann in enumerate(self.annotations) if ann.get('is_transcription')]
        self.zone_assignments = self._distribute_annotations_to_zones(annotations_with_indices, self.get_dynamic_layout(self.rect())['max_zones'], self.rect())
        
        # Recalculate width now that we have segments to ensure proper scrolling
        self.set_audio_duration(display_duration)
        
        self.update()

    
    def clear_annotations(self):
        """Clear all annotations."""
        self.annotations.clear()
        self.text_annotations.clear()
        self.icon_positions.clear()
        if hasattr(self, 'bubble_animation_progress'):
            self.bubble_animation_progress.clear()
        if hasattr(self, '_bubble_target_progress'):
            self._bubble_target_progress.clear()
        if hasattr(self, '_bubble_animation_timer'):
            self._bubble_animation_timer.stop()
        self.update()
    
    def update_animation(self):
        """Ultra-smooth animation update with perfect timing."""
        if self.is_dragging:
            return
            
        # Ultra-smooth animation increment with perfect timing
        self.animation_phase += 0.3  # Slower, smoother increment
        
        # Update bubble animations for smooth transitions
        needs_update = False
        if hasattr(self, 'bubble_animation_progress'):
            for i, progress in self.bubble_animation_progress.items():
                target_progress = 1.0 if i == self.active_segment_index else 0.0
                if abs(progress - target_progress) > 0.01:  # Still animating
                    needs_update = True
                    break
        
        # Only update if widget is visible and not being dragged
        if self.isVisible() and not self.is_dragging:
            if needs_update or hasattr(self, '_bubble_animation_active'):
                self.update()
    
    def start_bubble_animation_timer(self):
        """Start smooth animation for bubble transitions using QTimer."""
        if not hasattr(self, 'bubble_animation_progress'):
            self.bubble_animation_progress = {}
        if not hasattr(self, '_bubble_target_progress'):
            self._bubble_target_progress = {}
        if not hasattr(self, '_hover_animation_progress'):
            self._hover_animation_progress = {}
        if not hasattr(self, '_hover_target_progress'):
            self._hover_target_progress = {}
        if not hasattr(self, '_bubble_animation_timer'):
            from PySide6.QtCore import QTimer
            self._bubble_animation_timer = QTimer()
            self._bubble_animation_timer.timeout.connect(self._update_bubble_animations)
            self._bubble_animation_timer.setInterval(16)  # ~60 FPS
            
        # Set target progress for all bubbles (active segment + hover)
        for i in range(len(self.annotations)):
            if i not in self.bubble_animation_progress:
                self.bubble_animation_progress[i] = 0.0
            if i not in self._hover_animation_progress:
                self._hover_animation_progress[i] = 0.0
                
            # Calculate combined animation: active segment + hover effects
            is_active = i == self.active_segment_index
            is_hovered = i == self.hovered_bubble_index
            
            # Active segment gets priority, hover adds additional scaling
            base_target = 1.0 if is_active else 0.0
            hover_target = 0.8 if is_hovered else 0.0  # 80% of active animation for hover
            
            self._bubble_target_progress[i] = base_target
            self._hover_target_progress[i] = hover_target
            
        # Start animation timer if not running
        if not self._bubble_animation_timer.isActive():
            self._bubble_animation_timer.start()
    
    def _update_bubble_animations(self):
        """Update bubble animation progress with smooth easing."""
        import math
        
        animation_speed = 0.08  # Animation speed factor
        all_animations_complete = True
        
        # Update active segment animations
        for i in self._bubble_target_progress:
            current = self.bubble_animation_progress.get(i, 0.0)
            target = self._bubble_target_progress[i]
            
            # Calculate smooth transition with easing
            diff = target - current
            if abs(diff) > 0.01:
                # Apply cubic easing out
                progress_step = diff * animation_speed
                self.bubble_animation_progress[i] = current + progress_step
                all_animations_complete = False
            else:
                self.bubble_animation_progress[i] = target
        
        # Update hover animations
        for i in self._hover_target_progress:
            current = self._hover_animation_progress.get(i, 0.0)
            target = self._hover_target_progress[i]
            
            # Calculate smooth transition with easing for hover
            diff = target - current
            if abs(diff) > 0.01:
                progress_step = diff * animation_speed
                self._hover_animation_progress[i] = current + progress_step
                all_animations_complete = False
            else:
                self._hover_animation_progress[i] = target
        
        # Update the widget
        self.update()
        
        # Stop timer when all animations are complete
        if all_animations_complete and hasattr(self, '_bubble_animation_timer'):
            self._bubble_animation_timer.stop()

    def _handle_bubble_hover(self, mouse_pos):
        """Handle mouse hover detection for bubbles with smooth animations."""
        if not self.annotations:
            return
            
        # Get layout information for bubble positioning
        rect = self.rect()
        layout = self.get_dynamic_layout(rect)
        zone_height = layout['zone_height']
        max_zones = layout['max_zones']
        max_bubble_width = layout['max_bubble_width']
        
        # Get transcription annotations
        transcription_annotations_with_indices = [(i, ann) for i, ann in enumerate(self.annotations) 
                                                if ann.get('is_transcription', False)]
        zone_assignments = self._distribute_annotations_to_zones(transcription_annotations_with_indices, 
                                                               max_zones, rect)
        
        # Track headers configuration
        header_width = 25
        track_margin_top = 60
        track_spacing = 5
        
        # Find which bubble is under the mouse
        hovered_index = -1
        for i, annotation in enumerate(self.annotations):
            if not annotation.get('is_transcription', False):
                continue
                
            zone_info = zone_assignments.get(i, {'zone': 0, 'x_position': 0, 'width': 200})
            zone = zone_info['zone']
            x = zone_info.get('x_position', rect.left()) + header_width
            width = zone_info.get('width', max_bubble_width)
            
            # Calculate bubble position
            track_y = rect.top() + track_margin_top + (zone * (zone_height + track_spacing))
            bubble_rect = QRect(int(x), track_y, int(width), zone_height)
            
            # Check if mouse is over this bubble
            if bubble_rect.contains(mouse_pos.toPoint()):
                hovered_index = i
                break
        
        # Update hover state if changed
        if hovered_index != self.hovered_bubble_index:
            self.previous_hovered_bubble = self.hovered_bubble_index
            self.hovered_bubble_index = hovered_index
            
            # Trigger animation update
            self.start_bubble_animation_timer()
            
    def leaveEvent(self, event):
        """Clear hover state when mouse leaves the widget."""
        if hasattr(self, 'hovered_bubble_index') and self.hovered_bubble_index != -1:
            self.hovered_bubble_index = -1
            self.start_bubble_animation_timer()
        super().leaveEvent(event)
            
    def set_bubble_progress(self, index, progress):
        """Property setter for bubble animation progress."""
        if hasattr(self, 'bubble_animation_progress'):
            self.bubble_animation_progress[index] = progress
            self.update()
            
    def get_bubble_progress(self, index):
        """Property getter for bubble animation progress."""
        if hasattr(self, 'bubble_animation_progress'):
            return self.bubble_animation_progress.get(index, 0.0)
        return 0.0
    
    def paintEvent(self, event):
        """Paint the waveform display with smooth dragging support."""
        visible_rect = event.rect()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        rect = self.rect()
        # Use consistent margin with timeline and progress indicator
        margin = 15  # Match timeline margin exactly
        header_width = 1  # Match timeline header width exactly
        waveform_rect = rect.adjusted(margin + header_width, margin, -margin, -margin)
        
        # Clear the entire widget first for clean rendering
        painter.fillRect(rect, QColor(45, 45, 55))
        
        # Draw timeline and grid first - use same rect as progress indicator
        if self.animation_mode != "transcribing":
            self.draw_timeline(painter, waveform_rect)

        # Draw waveform animation only when not dragging
        if not self.is_dragging:
            self.draw_waveform(painter, waveform_rect)
        
        # Always draw progress indicator for smooth dragging
        self.draw_progress_indicator(painter, waveform_rect)
        
        # Draw annotations
        self.draw_annotations(painter, waveform_rect, visible_rect)
        
        # Scale controls are now handled by separate overlay widgets
    

    
    def draw_background_grid(self, painter, rect):
        """Draw subtle background grid with cached pens."""
        painter.setPen(self.cached_pens['grid_light'])
        
        # Vertical grid lines - draw fewer lines for better performance
        for i in range(0, 6):  # Reduced from 11 to 6 lines
            x = rect.left() + (rect.width() * i / 5)
            painter.drawLine(int(x), rect.top(), int(x), rect.bottom())
        
        # Horizontal center line
        center_y = rect.top() + rect.height() // 2
        painter.setPen(self.cached_pens['grid_center'])
        painter.drawLine(rect.left(), center_y, rect.right(), center_y)
    
    def draw_waveform(self, painter, rect):
        """Draw waveform visualization without animated elements."""
        # No animated circles or elements - clean waveform display
        pass
    

    

    

    

    



    
    def _recalculate_bar_data(self, width):
        """Recalculate and cache bar data for better performance."""
        self.cached_bar_heights = []
        for i in range(self.wave_bars):
            # Simplified height calculation
            height = 0.3 + 0.7 * math.sin(i * 0.2 + self.animation_offset * 0.1)
            self.cached_bar_heights.append(abs(height))
        
        self.last_width = width
        self.cached_bar_count = self.wave_bars
    
    def draw_progress_indicator(self, painter, rect):
        """Draw ultra-smooth, glitch-free progress indicator with perfect dragging."""
        if self.progress <= 0:
            return
            
        # Enable maximum smoothness
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        # Calculate position based on current time and scale factor for perfect timeline synchronization
        # The 'rect' passed in is the drawable area, so its width is the available width.
        available_width = rect.width()

        # Calculate position using the same logic as timeline: time * pixels_per_second
        if hasattr(self, 'audio_duration') and self.audio_duration > 0:
            current_time = self.progress * self.audio_duration
            pixels_per_second = available_width / self.audio_duration
            progress_x = rect.left() + (current_time * pixels_per_second)
        else:
            # Fallback for when audio_duration is not available
            progress_x = rect.left() + (available_width * self.progress)
        
        # Draw main progress line with perfect smoothness
        line_pen = QPen(QColor(255, 255, 255, 255), 3)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(line_pen)
        
        # Draw the line with exact positioning
        painter.drawLine(
            QPointF(progress_x, rect.top() + 5), 
            QPointF(progress_x, rect.bottom() - 5)
        )
        
        # Draw progress handle with perfect smoothness
        handle_size = 6
        handle_center = QPointF(progress_x, rect.center().y())
        
        # Main handle - smaller and more compact
        painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        painter.drawEllipse(handle_center, handle_size, handle_size)
    
    def draw_scale_controls(self, painter, rect):
        """Draw circular scale control buttons in the bottom right corner with fixed positioning."""
        # Get the scroll area's viewport rect for truly fixed positioning
        viewport_rect = self.rect()
        if hasattr(self, 'scroll_area') and self.scroll_area:
            # Map the viewport rect to widget coordinates
            viewport_rect = self.scroll_area.viewport().rect()
            # Convert viewport coordinates to widget coordinates
            viewport_top_left = self.mapFromGlobal(self.scroll_area.viewport().mapToGlobal(viewport_rect.topLeft()))
            viewport_rect = QRect(viewport_top_left, viewport_rect.size())
        
        minus_rect, plus_rect = self.get_scale_button_rects(viewport_rect)
        
        # Set up painter for buttons
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Button styling - more compact for smaller buttons
        button_color = QColor(40, 40, 50, 220)
        border_color = QColor(80, 80, 90, 180)
        icon_color = QColor(255, 255, 255, 240)
        
        # Draw minus button (circular)
        painter.setBrush(QBrush(button_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(minus_rect)
        
        # Draw minus icon (smaller for compact button)
        painter.setPen(QPen(icon_color, 1.5))
        center_y = minus_rect.center().y()
        margin = 6  # Smaller margin for compact button
        painter.drawLine(
            minus_rect.left() + margin, center_y,
            minus_rect.right() - margin, center_y
        )
        
        # Draw plus button (circular)
        painter.setBrush(QBrush(button_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(plus_rect)
        
        # Draw plus icon (smaller for compact button)
        painter.setPen(QPen(icon_color, 1.5))
        center_x = plus_rect.center().x()
        center_y = plus_rect.center().y()
        margin = 6  # Smaller margin for compact button
        # Horizontal line
        painter.drawLine(
            plus_rect.left() + margin, center_y,
            plus_rect.right() - margin, center_y
        )
        # Vertical line
        painter.drawLine(
            center_x, plus_rect.top() + margin,
            center_x, plus_rect.bottom() - margin
        )
    
    def draw_annotations(self, painter, rect, visible_rect=None):
        """Draw annotations with DAW-style track layout and professional styling."""
        if not self.annotations:
            return
        
        # Clear icon positions for this frame
        self.icon_positions.clear()
        
        # Get dynamic layout for current window size
        layout = self.get_dynamic_layout(rect)
        zone_height = layout['zone_height']
        max_zones = layout['max_zones']
        max_bubble_width = layout['max_bubble_width']
        
        # Get transcription annotations and calculate their positions
        transcription_annotations_with_indices = [(i, ann) for i, ann in enumerate(self.annotations) if ann.get('is_transcription', False)]
        zone_assignments = self._distribute_annotations_to_zones(transcription_annotations_with_indices, max_zones, rect)
        
        # Ensure widget height matches dynamic lane layout
        self._update_widget_height_for_zones(zone_assignments, layout)
        
        # Draw DAW-style track headers first
        self._draw_track_headers(painter, rect, zone_assignments)
        
        # Performance optimization: Get the actual visible viewport area
        if visible_rect is None:
            visible_rect = rect
        
        # Get the scroll area's viewport if we're inside one (for DAW-style performance)
        scroll_area_viewport = None
        parent = self.parent()
        while parent:
            if hasattr(parent, 'viewport') and hasattr(parent, 'horizontalScrollBar'):
                # Found the scroll area
                scroll_area_viewport = parent.viewport().rect()
                # Map the viewport rect to widget coordinates
                scroll_x = parent.horizontalScrollBar().value()
                visible_rect = QRect(scroll_x, visible_rect.y(), 
                                   scroll_area_viewport.width(), visible_rect.height())
                break
            parent = parent.parent()

        # Draw transcription segments (only visible ones for performance)
        # First draw inactive bubbles (background)
        for i, annotation in enumerate(self.annotations):
            if annotation.get('is_transcription', False) and i != self.active_segment_index:
                # Use the stored zone assignment for positioning
                zone_info = zone_assignments.get(i, {
                    'zone': i % max_zones,
                    'offset': 0,
                    'x_position': rect.left(),
                    'y_position': rect.top() + 60,
                    'width': max_bubble_width,
                    'height': 90
                })
                x = zone_info.get('x_position', rect.left())
                y = zone_info.get('y_position', rect.top() + 60)
                w = zone_info.get('width', max_bubble_width)
                h = zone_info.get('height', 90)

                # Include header width offset to match actual draw position
                header_width = 25
                bubble_rect_estimate = QRect(int(x + header_width), int(y), int(w), int(h))

                # Performance optimization: Only render if bubble intersects with visible area
                if visible_rect.intersects(bubble_rect_estimate):
                    is_active = False
                    self._draw_transcription_bubble(painter, rect, i, annotation, zone_assignments, 
                                                  layout, is_active=is_active)
        
        # Then draw active bubble last (foreground)
        if self.active_segment_index is not None and 0 <= self.active_segment_index < len(self.annotations):
            i = self.active_segment_index
            annotation = self.annotations[i]
            if annotation.get('is_transcription', False):
                # Use actual zone assignment but draw last for z-ordering
                zone_info = zone_assignments.get(i, {
                    'zone': 0,
                    'offset': 0,
                    'x_position': rect.left(),
                    'y_position': rect.top() + 60,
                    'width': max_bubble_width,
                    'height': 90
                })
                x = zone_info.get('x_position', rect.left())
                y = zone_info.get('y_position', rect.top() + 60)
                w = zone_info.get('width', max_bubble_width)
                h = zone_info.get('height', 90)
                
                # Active bubble is always rendered; compute rect for consistency
                header_width = 25
                _ = QRect(int(x + header_width), int(y), int(w), int(h))

                # Always render active bubble regardless of visibility check
                is_active = True
                self._draw_transcription_bubble(painter, rect, i, annotation, zone_assignments, 
                                              layout, is_active=is_active)
        
        # Draw regular annotations (non-transcription) - also with viewport culling
        for i, annotation in enumerate(self.annotations):
            if not annotation.get('is_transcription', False):
                position = annotation.get('position', 0)
                text = annotation.get('text', '')
                x = rect.left() + (rect.width() * position)
                
                # Check if this annotation is visible before rendering
                annotation_rect = QRect(int(x - 50), rect.top() + 20, 100, rect.height() - 40)
                if visible_rect.intersects(annotation_rect):
                    # Regular annotations (smaller, less prominent)
                    painter.setPen(QPen(QColor(100, 150, 255, 150), 2))
                    painter.drawLine(int(x), rect.top() + 20, int(x), rect.bottom() - 20)
                    
                    # Small text background
                    text_width = painter.fontMetrics().horizontalAdvance(text)
                    text_height = painter.fontMetrics().height()
                    
                    small_rect = QRect(int(x - text_width/2 - 3), rect.center().y() - 10, 
                                     text_width + 6, text_height + 4)
                    painter.setBrush(QBrush(QColor(50, 75, 125, 150)))
                    painter.setPen(QPen(QColor(100, 150, 255, 100), 1))
                    painter.drawRoundedRect(small_rect, 4, 4)
                    
                    # Small text
                    painter.setPen(QPen(QColor(255, 255, 255, 200)))
                    painter.drawText(small_rect, Qt.AlignmentFlag.AlignCenter, text)
    
    def _draw_track_headers(self, painter, rect, zone_assignments):
        """Draw DAW-style track headers with minimal visual separators."""
        if not zone_assignments:
            return
            
        # Track header configuration
        header_width = 25  # Align with bubble header offset

        # Draw only the separator line between headers and content
        painter.setPen(QPen(QColor(80, 85, 90), 1))
        painter.drawLine(header_width, rect.top(), header_width, rect.bottom())
        
        # Build dynamic lane extents from zone_assignments
        lanes = {}
        for info in zone_assignments.values():
            z = info.get('zone', 0)
            y = info.get('y_position', rect.top() + 60)
            h = info.get('height', 90)
            top_y = int(y)
            bottom_y = int(y + h)
            if z not in lanes:
                lanes[z] = {'min_y': top_y, 'max_y': bottom_y}
            else:
                lanes[z]['min_y'] = min(lanes[z]['min_y'], top_y)
                lanes[z]['max_y'] = max(lanes[z]['max_y'], bottom_y)
        
        # Draw subtle horizontal separators at the bottom of each lane
        painter.setPen(QPen(QColor(60, 65, 70, 100), 1))
        for z in sorted(lanes.keys()):
            separator_y = lanes[z]['max_y']
            painter.drawLine(header_width + 5, separator_y, rect.right() - 5, separator_y)
    
    def _draw_transcription_bubble(self, painter, rect, i, annotation, zone_assignments, layout, is_active):
        """Draw DAW-style audio segment blocks with professional styling."""
        text = annotation.get('text', '')
        
        # Get assigned zone for this annotation
        zone_info = zone_assignments.get(i, {'zone': i % 3, 'y_position': rect.top() + 60, 'x_position': 0, 'width': 200, 'height': 60})
        x = zone_info.get('x_position', rect.left())
        y = zone_info.get('y_position', rect.top() + 60)
        
        # Get animation progress for smooth transitions
        if not hasattr(self, 'bubble_animation_progress'):
            self.bubble_animation_progress = {}
        
        # Use current animation progress directly (managed by QPropertyAnimation)
        eased_progress = self.bubble_animation_progress.get(i, 0.0)
        
        # Ensure progress is within bounds
        eased_progress = max(0.0, min(1.0, eased_progress))
        
        # Use the width and height calculated in _distribute_annotations_to_zones
        segment_width = zone_info.get('width', 200)
        segment_height = zone_info.get('height', 60)
        
        header_width = 25  # Width of track header area
        
        # Adjust x position to account for track headers
        x = x + header_width
        
        # Create the audio segment rectangle (using calculated position and size)
        segment_rect = QRect(int(x), int(y), int(segment_width), int(segment_height))
        
        # Calculate zoom scale based on animation progress
        base_scale = 1.0
        max_scale = 1.15  # 15% zoom when active
        current_scale = base_scale + (max_scale - base_scale) * eased_progress
        
        # Save painter state before transformation
        painter.save()
        
        # Apply scale transformation centered on the bubble
        bubble_center = segment_rect.center()
        painter.translate(bubble_center)
        painter.scale(current_scale, current_scale)
        painter.translate(-bubble_center)
        
        # Adjust segment_rect for the scaled drawing
        scaled_rect = segment_rect
        
        # Pastel color scheme for gentle, soft appearance
        if 'color' not in annotation or annotation['color'] is None:
            # Use soft pastel colors with gentle transparency
            pastel_colors = [
                QColor(173, 216, 230, 200),   # Light Blue
                QColor(152, 251, 152, 200),   # Light Green  
                QColor(221, 160, 221, 200),   # Light Purple
                QColor(255, 182, 193, 200),   # Light Pink
                QColor(255, 218, 185, 200),   # Peach
                QColor(176, 224, 230, 200),   # Powder Blue
                QColor(255, 228, 196, 200),   # Bisque
                QColor(240, 230, 140, 200),   # Khaki
            ]
            annotation['color'] = pastel_colors[i % len(pastel_colors)]
        
        base_color = annotation['color']
        
        # Soft pastel border colors - consistent for each bubble
        pastel_borders = [
            QColor(135, 206, 235),   # Sky Blue
            QColor(144, 238, 144),   # Light Green  
            QColor(186, 85, 211),    # Medium Orchid
            QColor(255, 105, 180),   # Hot Pink
            QColor(255, 165, 79),    # Light Salmon
            QColor(135, 206, 250),   # Light Sky Blue
            QColor(255, 160, 122),   # Light Salmon
            QColor(238, 130, 238),   # Violet
        ]
        border_color = pastel_borders[i % len(pastel_borders)]
        
        # Soft background colors to complement pastel scheme
        if is_active:
            solid_bg = QColor(50, 50, 55, 255)  # Soft dark background for active
            border_width = 2  # Thinner border for active
            # Keep same border color for consistency, just slightly brighter
            border_color = QColor(
                min(255, border_color.red() + 20),
                min(255, border_color.green() + 20),
                min(255, border_color.blue() + 20)
            )
        else:
            solid_bg = QColor(35, 35, 40, 255)  # Softer dark background
            border_width = 1  # Much thinner border
        
        painter.setBrush(QBrush(solid_bg))
        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(scaled_rect, 8, 8)  # More rounded corners
        
        # Note: We now draw the text after restoring the painter transform
        # so the text stays crisp and fully visible during zoom.
        
        # Calculate segment timing for timestamp (moved to after restore for crisp text)
        
        # Fixed plus button size and position
        plus_size = 16
        plus_margin = 6
        plus_rect = QRect(scaled_rect.right() - plus_size - plus_margin, 
                         scaled_rect.top() + plus_margin, 
                         plus_size, plus_size)

        
        # Draw plus button background (white circle without border)
        plus_bg_color = QColor(255, 255, 255, 255)  # Solid white circle
        painter.setBrush(QBrush(plus_bg_color))
        painter.setPen(Qt.PenStyle.NoPen)  # Remove border completely
        painter.drawEllipse(plus_rect)
        
        # Draw plus icon (+ symbol) - perfectly centered
        plus_color = QColor(0, 0, 0, 255)  # Black plus icon for contrast on white
        painter.setPen(QPen(plus_color, 2))
        
        # Calculate precise center using exact coordinates
        center_x = plus_rect.x() + plus_rect.width() / 2.0
        center_y = plus_rect.y() + plus_rect.height() / 2.0
        
        # Draw perfectly centered plus with precise positioning
        line_length = 4  # Ensure consistent length
        # Use exact coordinates for perfect centering
        painter.drawLine(int(center_x - line_length + 0.5), int(center_y + 0.5), 
                        int(center_x + line_length + 0.5), int(center_y + 0.5))  # Horizontal
        painter.drawLine(int(center_x + 0.5), int(center_y - line_length + 0.5), 
                        int(center_x + 0.5), int(center_y + line_length + 0.5))  # Vertical
        
        # Calculate the transformed plus_rect for click detection
        # Apply the same transformation to get the actual clickable area
        transformed_plus_rect = QRect(
            int((plus_rect.x() - bubble_center.x()) * current_scale + bubble_center.x()),
            int((plus_rect.y() - bubble_center.y()) * current_scale + bubble_center.y()),
            int(plus_rect.width() * current_scale),
            int(plus_rect.height() * current_scale)
        )
        
        # Restore painter state after transformation
        painter.restore()
        
        # Store plus button click area with transformed coordinates for proper click detection
        self.icon_positions.append({
            'type': 'plus',
            'rect': transformed_plus_rect,
            'annotation_index': i,
            'bubble_rect': segment_rect
        })
        
        # Calculate the transformed segment_rect for click detection
        transformed_segment_rect = QRect(
            int((segment_rect.x() - bubble_center.x()) * current_scale + bubble_center.x()),
            int((segment_rect.y() - bubble_center.y()) * current_scale + bubble_center.y()),
            int(segment_rect.width() * current_scale),
            int(segment_rect.height() * current_scale)
        )

        # Draw crisp text outside the scaled transform so it remains visible during zoom
        font_size = 16 if is_active else 14
        painter.setFont(QFont("Arial", font_size, QFont.Weight.Normal))
        text_color = QColor(255, 255, 255, 255) if is_active else QColor(220, 220, 220, 255)
        painter.setPen(QPen(text_color))
        text_margin = 12
        top_margin = 15
        timestamp_height = 20
        # Text starts below the timestamp area
        text_rect = QRect(
            transformed_segment_rect.left() + text_margin,
            transformed_segment_rect.top() + top_margin + timestamp_height,
            transformed_segment_rect.width() - (2 * text_margin),
            transformed_segment_rect.height() - (top_margin + timestamp_height + 15),
        )
        painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, text)

        # Draw crisp timestamp outside the scaled transform
        start_time = annotation.get('start_time', 0)
        end_time = annotation.get('end_time', start_time + 3)
        timestamp_text = f"{int(start_time//60):02d}:{int(start_time%60):02d}"
        timestamp_font_size = 10
        painter.setFont(QFont("Arial", timestamp_font_size, QFont.Weight.Bold))
        painter.setPen(QColor(200, 200, 200, 255))
        timestamp_rect = QRect(
            transformed_segment_rect.left() + text_margin,
            transformed_segment_rect.top() + top_margin - 3,
            60, timestamp_height
        )
        painter.drawText(timestamp_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, timestamp_text)
        
        # Store click areas for interaction (use transformed coordinates for accurate click detection)
        self.icon_positions.append({
            'type': 'segment',
            'rect': transformed_segment_rect,
            'annotation_index': i,
            'bubble_rect': segment_rect
        })
        

    

    
    def _distribute_annotations_to_zones(self, annotations_with_indices, max_zones, rect):
        """Distribute annotations into non-overlapping lanes and use full height with per-bubble sizing."""
        if not annotations_with_indices:
            return {}

        # Sort annotations by start time
        sorted_annotations = sorted(annotations_with_indices, key=lambda item: item[1].get('start_time', 0))

        layout = self.get_dynamic_layout(rect)
        margin = 30
        header_width = 25
        available_width = max(1, rect.width() - (2 * margin) - header_width)

        # Font for measurement (match _draw_transcription_bubble text font for non-active)
        text_font = QFont("Arial", 14, QFont.Weight.Normal)
        fm = QFontMetrics(text_font)

        # UI constants
        text_margin = 12
        top_margin = 15
        timestamp_height = 20
        bottom_margin = 15
        min_bubble_width = 120

        # Precompute bubble geometry per annotation
        precomputed = []
        duration = max(self.audio_duration, 1)
        for original_index, annotation in sorted_annotations:
            start_time = annotation.get('start_time', 0)
            text = annotation.get('text', '')

            single_line_width = fm.horizontalAdvance(text) + 2 * text_margin
            bubble_width = min(layout['max_bubble_width'], max(min_bubble_width, single_line_width))
            bubble_width = min(bubble_width, available_width)

            # Wrapped text height within content width
            content_width = max(10, bubble_width - 2 * text_margin)
            text_bounds = fm.boundingRect(QRect(0, 0, int(content_width), 10000), Qt.TextFlag.TextWordWrap, text)
            text_height = text_bounds.height()

            bubble_height = top_margin + timestamp_height + bottom_margin + text_height

            start_x = margin + (start_time / duration) * available_width
            end_x = start_x + bubble_width

            precomputed.append({
                'index': original_index,
                'start_x': start_x,
                'end_x': end_x,
                'width': bubble_width,
                'height': bubble_height,
            })

        # Greedy lane assignment to avoid horizontal overlaps
        lanes = []  # each lane: list of (start_x, end_x)
        zone_assignments = {}
        buffer_px = 10
        for item in precomputed:
            assigned_zone = -1
            for zone_idx, lane in enumerate(lanes):
                can_fit = True
                for (ex_s, ex_e) in lane:
                    if not (item['end_x'] + buffer_px <= ex_s or item['start_x'] >= ex_e + buffer_px):
                        can_fit = False
                        break
                if can_fit:
                    assigned_zone = zone_idx
                    break
            if assigned_zone == -1:
                assigned_zone = len(lanes)
                lanes.append([])
            lanes[assigned_zone].append((item['start_x'], item['end_x']))

            zone_assignments[item['index']] = {
                'zone': assigned_zone,
                'offset': 0,
                'x_position': item['start_x'],
                'width': item['width'],
                'y_position': 0,  # to be filled below
                'height': item['height'],  # will be scaled per lane
            }

        # Compute lane heights (max bubble height per lane)
        lane_items = {i: [] for i in range(len(lanes))}
        for item in precomputed:
            z = zone_assignments[item['index']]['zone']
            lane_items[z].append(item)
        lane_max_heights = [max((it['height'] for it in lane_items[z]), default=90) for z in range(len(lanes))]

        # Use full available height for lanes
        track_margin_top = 60
        zone_spacing = 12
        bottom_padding = 20
        available_height = max(0, rect.height() - track_margin_top - bottom_padding)
        natural_total = sum(lane_max_heights) + zone_spacing * max(0, len(lane_max_heights) - 1)
        scale = (available_height / natural_total) if natural_total > 0 else 1.0

        lane_scaled_heights = [h * scale for h in lane_max_heights]
        lane_scales = [(lane_scaled_heights[i] / lane_max_heights[i]) if lane_max_heights[i] > 0 else 1.0 for i in range(len(lane_max_heights))]

        lane_y_offsets = []
        y_cursor = rect.top() + track_margin_top
        for h in lane_scaled_heights:
            lane_y_offsets.append(y_cursor)
            y_cursor += h + zone_spacing

        # Fill y_position and scaled heights
        for item in precomputed:
            z = zone_assignments[item['index']]['zone']
            zone_assignments[item['index']]['y_position'] = lane_y_offsets[z]
            zone_assignments[item['index']]['height'] = item['height'] * lane_scales[z]

        return zone_assignments

    def _update_widget_height_for_zones(self, zone_assignments, layout):
        """Update widget height based on the number of zones used."""
        if not zone_assignments:
            self.setMinimumHeight(150)  # Default height
            return
            
        # Determine the number of zones actually used
        used_zones = set(d['zone'] for d in zone_assignments.values())
        num_used_zones = len(used_zones) if used_zones else 1
        
        # Calculate required height based on used zones
        zone_height = layout['zone_height']
        v_spacing = 15  # Vertical spacing between zones
        required_height = 120 + num_used_zones * (zone_height + v_spacing) + 60
        
        self.setMinimumHeight(required_height)

    def _find_non_overlapping_position(self, existing_positions, x, base_y, width, height, rect):
        """Find a vertical position that doesn't overlap with existing bubbles."""
        max_attempts = 10
        vertical_spacing = 20
        
        for attempt in range(max_attempts):
            # Try different vertical levels
            if attempt == 0:
                test_y = base_y
            elif attempt % 2 == 1:
                # Try below
                test_y = base_y + (attempt // 2 + 1) * (height + vertical_spacing)
            else:
                # Try above
                test_y = base_y - (attempt // 2) * (height + vertical_spacing)
            
            # Ensure within bounds
            if test_y < rect.top() + 50:
                test_y = rect.top() + 50
            elif test_y + height > rect.bottom() - 20:
                test_y = rect.bottom() - 20 - height
            
            # Check for overlaps
            test_rect = QRect(int(x - width/2), test_y, int(width), height)
            overlaps = False
            
            for existing_rect in existing_positions:
                if test_rect.intersects(existing_rect):
                    overlaps = True
                    break
            
            if not overlaps:
                return test_y
        
        # If no non-overlapping position found, use base position
        return base_y
    
    def draw_timeline(self, painter, rect):
        """Draw time markers and background grid synchronized with audio playback."""
        # The 'rect' passed in is the drawable area, so its width is the available width.
        available_width = rect.width()
        

        
        # Use actual audio duration if available
        max_duration = getattr(self, 'audio_duration', 0)
        if not max_duration:
            return

        # --- Draw Background Grid ---
        painter.setPen(QPen(QColor(70, 70, 80), 1))
        # Horizontal center line - very compact
        center_y = rect.center().y()
        painter.drawLine(rect.left(), center_y, rect.right(), center_y)

        # --- Draw Timeline Ticks and Labels ---
        painter.setFont(QFont("Arial", 7, QFont.Weight.Bold))  # Very small font
        painter.setPen(QColor(180, 180, 190))

        # Calculate pixels per second for proper synchronization with scale factor
        pixels_per_second = available_width / max_duration
        
        # Ultra compact intervals - adjusted for scale
        if pixels_per_second > 150:
            interval = 1  # seconds - ultra dense
        elif pixels_per_second > 80:
            interval = 2  # seconds - very dense
        elif pixels_per_second > 40:
            interval = 5  # seconds - dense
        else:
            interval = 10  # seconds - sparse

        for time_in_seconds in range(0, int(max_duration) + 1, interval):
            x_pos = rect.left() + (time_in_seconds * pixels_per_second)
            
            # Only draw if within available width
            if x_pos <= rect.right():
                # Draw major tick line - ultra short
                painter.drawLine(int(x_pos), rect.bottom() - 12, int(x_pos), rect.bottom())

                # Draw time label - ultra compact format
                minutes = time_in_seconds // 60
                seconds = time_in_seconds % 60
                if minutes > 0:
                    time_text = f"{minutes}m"
                else:
                    time_text = f"{seconds}s"
                    
                text_width = painter.fontMetrics().horizontalAdvance(time_text)
                painter.drawText(int(x_pos - text_width / 2), rect.bottom() - 5, time_text)

                # Draw vertical grid line - ultra light
                painter.setPen(QPen(QColor(60, 60, 70), 1))
                painter.drawLine(int(x_pos), rect.top() + 5, int(x_pos), rect.bottom() - 5)
                painter.setPen(QColor(180, 180, 190)) # Reset pen for next label

        # Draw minor ticks - ultra compact
        minor_interval = max(1, interval // 2)  # Very tight minor intervals
        painter.setPen(QColor(100, 100, 110))
        for time_in_seconds in range(0, int(max_duration) + 1, minor_interval):
            if time_in_seconds % interval != 0:
                x_pos = rect.left() + (time_in_seconds * pixels_per_second)
                if x_pos <= rect.right():
                    painter.drawLine(int(x_pos), rect.bottom() - 8, int(x_pos), rect.bottom())
    
    def resizeEvent(self, event):
        """Handle widget resize by invalidating cached background."""
        super().resizeEvent(event)
        self.background_cache_valid = False
        self._recalculate_bar_data(event.size().width())


class ModernGlassButton(QPushButton):
    """Clean, flat button with minimal styling and dynamic theme-aware icons."""
    
    def __init__(self, text, primary=False, icon_path=""):
        super().__init__(text)
        self.primary = primary
        self.icon_path = icon_path
        self.current_theme = None
        self.setMinimumHeight(40)
        self.setFont(QFont("SF Pro Display", 11, QFont.Weight.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Animation properties
        self.rotation_angle = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_rotation)
        self.is_animating = False
        
        # Load themed icon if provided
        self.update_icon()
        self.apply_style()
    
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
        """Update rotation angle for animation."""
        self.rotation_angle = (self.rotation_angle + 5) % 360
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event to draw rotating border when animating."""
        super().paintEvent(event)
        
        if self.is_animating and self.primary:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Get button rect
            rect = self.rect()
            center = rect.center()
            
            # Create rotating gradient
            gradient = QConicalGradient(center, self.rotation_angle)
            gradient.setColorAt(0.0, QColor(255, 0, 128, 255))    # #FF0080
            gradient.setColorAt(0.25, QColor(0, 212, 255, 255))   # #00D4FF
            gradient.setColorAt(0.5, QColor(255, 0, 128, 255))    # #FF0080
            gradient.setColorAt(0.75, QColor(0, 212, 255, 255))   # #00D4FF
            gradient.setColorAt(1.0, QColor(255, 0, 128, 255))    # #FF0080
            
            # Draw rotating border
            pen = QPen(QBrush(gradient), 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw rounded rectangle border
            border_rect = rect.adjusted(2, 2, -2, -2)
            painter.drawRoundedRect(border_rect, 8, 8)
    
    def update_icon(self):
        """Update icon based on current system theme."""
        if self.icon_path and os.path.exists(self.icon_path):
            # Detect current system theme
            current_theme = detect_system_theme()
            
            # Only update if theme changed or first time loading
            if self.current_theme != current_theme:
                self.current_theme = current_theme
                
                # Use same icon size for all buttons
                icon_size = 24
                icon_display_size = 20
                
                # Create themed icon pixmap
                pixmap = create_themed_icon_pixmap(self.icon_path, size=icon_size, theme=current_theme)
                
                if pixmap:
                    # Set icon
                    icon = QIcon(pixmap)
                    self.setIcon(icon)
                    self.setIconSize(QSize(icon_display_size, icon_display_size))
                    
                    # If text is empty, make it icon-only
                    if not self.text().strip():
                        self.setText("")
                        
                    print(f"Updated icon for {self.icon_path} with {current_theme} theme")
    
    def update_icon_color(self, color):
        """Update the icon with a specific color."""
        if self.icon_path and os.path.exists(self.icon_path):
            # Use same icon size for all buttons
            icon_size = 24
            icon_display_size = 20
            
            # Create themed icon pixmap with forced color
            pixmap = create_themed_icon_pixmap(self.icon_path, size=icon_size, force_color=color)
            
            if pixmap:
                # Set icon
                icon = QIcon(pixmap)
                self.setIcon(icon)
                self.setIconSize(QSize(icon_display_size, icon_display_size))
                
                # If text is empty, make it icon-only
                if not self.text().strip():
                    self.setText("")
                    
                print(f"Updated icon for {self.icon_path} with color {color}")
    
    def refresh_theme(self):
        """Force refresh the icon theme (useful for theme changes during runtime)."""
        self.current_theme = None  # Reset to force update
        self.update_icon()

    def apply_style(self):
        """Apply clean, flat styling."""
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FF0080, stop:1 #00D4FF);
                    border: 1px solid transparent;
                    border-radius: 8px;
                    color: white;
                    font-weight: 700;
                    padding: 10px 20px;
                    text-align: center;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FF1493, stop:1 #00BFFF);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #DC143C, stop:1 #0099CC);
                    border: 1px solid rgba(255, 255, 255, 0.5);
                }
                QPushButton:disabled {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #404040, stop:1 #606060);
                    color: #888888;
                    border: 1px solid #555555;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid #444444;
                    border-radius: 8px;
                    color: #CCCCCC;
                    font-weight: 500;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    border: 1px solid #666666;
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)


class ModernGlassLineEdit(QLineEdit):
    """Clean, flat line edit."""
    
    def __init__(self, placeholder=""):
        super().__init__()
        self.setMinimumHeight(40)
        self.setFont(QFont("SF Pro Display", 11))
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.apply_style()

    def apply_style(self):
        """Apply clean, flat styling."""
        self.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                border-bottom: 1px solid #444444;
                padding: 12px 0px;
                font-size: 11pt;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #00D4FF;
            }
            QLineEdit::placeholder {
                color: #888888;
            }
        """)


class ModernGlassTextEdit(QTextEdit):
    """Clean, flat text edit."""
    
    def __init__(self, placeholder=""):
        super().__init__()
        self.setFont(QFont("SF Pro Display", 11))
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.apply_style()

    def apply_style(self):
        """Apply clean, flat styling."""
        self.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 16px;
                font-size: 11pt;
                color: #FFFFFF;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border: 1px solid #00D4FF;
            }
        """)


class ModernGlassCard(QFrame):
    """Minimal card container."""
    
    def __init__(self):
        super().__init__()
        self.apply_style()

    def apply_style(self):
        """Apply minimal card styling."""
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)


class ModernHeaderLabel(QLabel):
    """Clean header label."""
    
    def __init__(self, text, icon=""):
        super().__init__(text)  # Remove icon/emoji
        self.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
        self.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                margin-bottom: 8px;
            }
        """)


class ModernStatusLabel(QLabel):
    """Clean status label."""
    
    def __init__(self, text=""):
        super().__init__(text)
        self.setFont(QFont("SF Pro Display", 10))
        self.setWordWrap(True)
        self.set_status(text, "info")
    
    def set_status(self, message, status_type="info"):
        """Set status message with appropriate styling."""
        self.setText(message)
        
        colors = {
            "info": "#CCCCCC",
            "success": "#00FF96",
            "error": "#FF6B6B",
            "warning": "#FFD93D"
        }
        
        color = colors.get(status_type, colors["info"])
        
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
            }}
        """)


# Alias for backward compatibility
ModernButton = ModernGlassButton
ModernLineEdit = ModernGlassLineEdit
ModernTextEdit = ModernGlassTextEdit
ModernCard = ModernGlassCard
HeaderLabel = ModernHeaderLabel
StatusLabel = ModernStatusLabel