"""Custom dialogs for the application."""

import hashlib
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, 
    QListWidgetItem, QLabel, QDialogButtonBox, QGridLayout, QWidget, QFrame,
    QScrollArea, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPalette, QColor, QPainter, QFont, QPen, QBrush, QLinearGradient
from app.utils.translation_manager import tr

class ProjectCard(QFrame):
    """Modern square card for project display with bubble-like styling."""
    
    clicked = Signal(int)  # Emits project_id when clicked
    delete_requested = Signal(int)  # Emits project_id when delete is requested
    
    def __init__(self, project_id, name, filepath, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.name = name
        self.filepath = filepath
        self.is_hovered = False
        self.is_selected = False
        self.delete_hovered = False
        
        # Generate consistent color based on project name
        self.border_color = self._generate_pastel_color(name)
        self.icon_letter = name[0].upper() if name else "P"
        
        # Set fixed size for square cards
        self.setFixedSize(140, 140)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
    
    def _generate_pastel_color(self, text):
        """Generate a consistent pastel color based on text hash."""
        # Create hash from text for consistency
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Use hash to seed random for consistent colors
        random.seed(int(hash_hex[:8], 16))
        
        # Pastel color palette similar to bubbles
        pastel_colors = [
            QColor(135, 206, 235),   # Sky Blue
            QColor(144, 238, 144),   # Light Green  
            QColor(186, 85, 211),    # Medium Orchid
            QColor(255, 105, 180),   # Hot Pink
            QColor(255, 165, 79),    # Light Salmon
            QColor(135, 206, 250),   # Light Sky Blue
            QColor(255, 160, 122),   # Light Salmon
            QColor(238, 130, 238),   # Violet
            QColor(255, 182, 193),   # Light Pink
            QColor(173, 216, 230),   # Light Blue
        ]
        
        return pastel_colors[random.randint(0, len(pastel_colors) - 1)]
    
    def paintEvent(self, event):
        """Custom paint event for bubble-like styling."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        rect = self.rect().adjusted(4, 4, -4, -4)  # Add margin
        
        # Base colors
        base_color = QColor(40, 40, 50, 180) if not self.is_selected else QColor(60, 60, 70, 200)
        
        # Hover effect
        if self.is_hovered:
            base_color = QColor(50, 50, 60, 200)
        
        # Selection effect
        if self.is_selected:
            base_color = QColor(70, 70, 80, 220)
        
        # Draw main card background with gradient
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, base_color)
        gradient.setColorAt(1, QColor(base_color.red() - 10, base_color.green() - 10, base_color.blue() - 10, base_color.alpha()))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(self.border_color, 2))
        painter.drawRoundedRect(rect, 12, 12)
        
        # Draw delete button (X) in top-right corner
        delete_size = 20
        delete_rect = QRect(
            rect.right() - delete_size - 5,
            rect.top() + 5,
            delete_size,
            delete_size
        )
        
        # Delete button background
        delete_bg_color = QColor(255, 0, 0, 150) if self.delete_hovered else QColor(255, 255, 255, 80)
        painter.setBrush(QBrush(delete_bg_color))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
        painter.drawEllipse(delete_rect)
        
        # Draw X symbol
        painter.setPen(QPen(QColor(255, 255, 255, 240), 2))
        x_margin = 5
        painter.drawLine(
            delete_rect.left() + x_margin, delete_rect.top() + x_margin,
            delete_rect.right() - x_margin, delete_rect.bottom() - x_margin
        )
        painter.drawLine(
            delete_rect.right() - x_margin, delete_rect.top() + x_margin,
            delete_rect.left() + x_margin, delete_rect.bottom() - x_margin
        )
        
        # Draw icon circle in upper area
        icon_size = 40
        icon_rect = QRect(
            rect.center().x() - icon_size // 2,
            rect.top() + 20,
            icon_size,
            icon_size
        )
        
        # Icon background
        icon_gradient = QLinearGradient(icon_rect.topLeft(), icon_rect.bottomRight())
        icon_gradient.setColorAt(0, self.border_color)
        icon_gradient.setColorAt(1, QColor(self.border_color.red() - 20, self.border_color.green() - 20, self.border_color.blue() - 20))
        
        painter.setBrush(QBrush(icon_gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawEllipse(icon_rect)
        
        # Draw letter icon
        painter.setPen(QPen(QColor(255, 255, 255, 240), 1))
        font = QFont("SF Pro Text", 18, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, self.icon_letter)
        
        # Draw project name
        text_rect = QRect(rect.left() + 8, icon_rect.bottom() + 10, rect.width() - 16, 30)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1))
        font = QFont("SF Pro Text", 11, QFont.Weight.Medium)
        painter.setFont(font)
        
        # Truncate name if too long
        display_name = self.name
        if len(display_name) > 12:
            display_name = display_name[:12] + "..."
        
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, display_name)
        
        # Draw subtle file path
        if self.filepath:
            path_rect = QRect(rect.left() + 8, text_rect.bottom() + 5, rect.width() - 16, 20)
            painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
            font = QFont("SF Pro Text", 8)
            painter.setFont(font)
            
            # Show just filename
            filename = self.filepath.split('/')[-1] if '/' in self.filepath else self.filepath
            if len(filename) > 15:
                filename = filename[:15] + "..."
            
            painter.drawText(path_rect, Qt.AlignmentFlag.AlignCenter, filename)
    
    def get_delete_rect(self):
        """Get the rectangle for the delete button."""
        rect = self.rect().adjusted(4, 4, -4, -4)
        delete_size = 20
        return QRect(
            rect.right() - delete_size - 5,
            rect.top() + 5,
            delete_size,
            delete_size
        )
    
    def mousePressEvent(self, event):
        """Handle mouse press for selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            delete_rect = self.get_delete_rect()
            if delete_rect.contains(event.pos()):
                # Delete button clicked
                self.delete_requested.emit(self.project_id)
            else:
                # Card clicked
                self.clicked.emit(self.project_id)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for hover effects."""
        delete_rect = self.get_delete_rect()
        old_delete_hovered = self.delete_hovered
        self.delete_hovered = delete_rect.contains(event.pos())
        
        # Update cursor based on hover state
        if self.delete_hovered:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Repaint if delete hover state changed
        if old_delete_hovered != self.delete_hovered:
            self.update()
    
    def enterEvent(self, event):
        """Handle mouse enter."""
        self.is_hovered = True
        self.update()
    
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self.is_hovered = False
        self.delete_hovered = False
        self.update()
    
    def set_selected(self, selected):
        """Set selection state."""
        self.is_selected = selected
        self.update()

class NewProjectCard(QFrame):
    """Special card for creating new projects."""
    
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_hovered = False
        
        # Set fixed size for square cards
        self.setFixedSize(140, 140)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
    
    def paintEvent(self, event):
        """Custom paint event for new project card."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        rect = self.rect().adjusted(4, 4, -4, -4)  # Add margin
        
        # Dashed border style
        base_color = QColor(80, 80, 90, 150) if not self.is_hovered else QColor(100, 100, 110, 180)
        
        # Draw dashed border
        pen = QPen(QColor(255, 255, 255, 150), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(base_color))
        painter.drawRoundedRect(rect, 12, 12)
        
        # Draw plus icon
        plus_size = 30
        plus_rect = QRect(
            rect.center().x() - plus_size // 2,
            rect.center().y() - plus_size // 2,
            plus_size,
            plus_size
        )
        
        painter.setPen(QPen(QColor(255, 255, 255, 180), 3))
        # Horizontal line
        painter.drawLine(
            plus_rect.left() + 8, plus_rect.center().y(),
            plus_rect.right() - 8, plus_rect.center().y()
        )
        # Vertical line
        painter.drawLine(
            plus_rect.center().x(), plus_rect.top() + 8,
            plus_rect.center().x(), plus_rect.bottom() - 8
        )
        
        # Draw "New Project" text
        text_rect = QRect(rect.left() + 8, plus_rect.bottom() + 10, rect.width() - 16, 20)
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
        font = QFont("SF Pro Text", 10, QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, tr("dialogs.project.new_project"))
    
    def mousePressEvent(self, event):
        """Handle mouse press for new project creation."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
    
    def enterEvent(self, event):
        """Handle mouse enter for hover effect."""
        self.is_hovered = True
        self.update()
    
    def leaveEvent(self, event):
        """Handle mouse leave for hover effect."""
        self.is_hovered = False
        self.update()

class ProjectDialog(QDialog):
    """Modern dialog for creating, opening, and managing projects with 3x3 grid layout."""
    
    # Signal emitted when a project is deleted
    project_deleted = Signal(int)  # Emits project_id
    
    def __init__(self, projects, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialogs.project.open_project"))
        self.setFixedSize(500, 600)
        self.projects = projects or []
        self.selected_project_id = None
        self.project_cards = []
        
        # Glassmorphism style
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(30, 30, 30, 0.9);
                border: none;
                border-radius: 0px;
                color: white;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: rgba(0, 191, 255, 0.8);
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the modern grid UI with scrollable area."""
        # Clear existing layout if it exists
        if self.layout():
            QWidget().setLayout(self.layout())
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Apply thin scrollbar styling
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 6px;
                border: none;
                border-radius: 3px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # Grid container
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(15, 15, 15, 15)
        
        # Add new project card first
        new_card = NewProjectCard()
        new_card.clicked.connect(self.create_new_project)
        grid_layout.addWidget(new_card, 0, 0)
        
        # Add existing project cards
        row, col = 0, 1
        self.project_cards.clear()  # Clear the cards list before rebuilding
        for project_id, name, filepath in self.projects:
            if col >= 3:  # Move to next row after 3 columns
                row += 1
                col = 0
            
            card = ProjectCard(project_id, name, filepath)
            # Fix lambda closure issue by using default parameters
            card.clicked.connect(lambda checked=False, pid=project_id: self.open_project_directly(pid))
            card.delete_requested.connect(lambda checked=False, pid=project_id: self.delete_project(pid))
            self.project_cards.append(card)
            grid_layout.addWidget(card, row, col)
            
            col += 1
        
        # Set the grid widget as the scroll area's widget
        scroll_area.setWidget(grid_widget)
        layout.addWidget(scroll_area)
        
        # New project input (initially hidden)
        self.new_project_widget = QWidget()
        new_project_layout = QVBoxLayout(self.new_project_widget)
        new_project_layout.setContentsMargins(20, 20, 20, 20)
        
        new_project_label = QLabel(tr("dialogs.project.enter_project_name"))
        new_project_layout.addWidget(new_project_label)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(tr("dialogs.project.new_project_placeholder"))
        self.name_edit.returnPressed.connect(self.create_project_and_close)
        new_project_layout.addWidget(self.name_edit)
        
        self.new_project_widget.setVisible(False)
        layout.addWidget(self.new_project_widget)
    
    def open_project_directly(self, project_id):
        """Open project directly when card is clicked."""
        self.selected_project_id = project_id
        self.accept()
    
    def create_project_and_close(self):
        """Create new project and close dialog."""
        if self.name_edit.text().strip():
            self.selected_project_id = None  # Indicates new project
            self.accept()
    
    def select_project(self, project_id):
        """Handle project selection (kept for compatibility)."""
        self.selected_project_id = project_id
        
        # Update card selection states
        for card in self.project_cards:
            card.set_selected(card.project_id == project_id)
        
        # Hide new project input if visible
        self.new_project_widget.setVisible(False)
    
    def create_new_project(self):
        """Handle new project creation."""
        self.selected_project_id = None
        
        # Clear all card selections
        for card in self.project_cards:
            card.set_selected(False)
        
        # Show new project input
        self.new_project_widget.setVisible(True)
        self.name_edit.setFocus()
    
    def get_selected_project(self):
        """Return the ID of the selected project."""
        return self.selected_project_id
    
    def get_new_project_name(self):
        """Return the name for a new project."""
        return self.name_edit.text().strip()
    
    def selected_project(self):
        """Return the name of the selected project (for backward compatibility)."""
        if self.selected_project_id:
            for project_id, name, filepath in self.projects:
                if project_id == self.selected_project_id:
                    return name
        return self.get_new_project_name()
    
    def delete_project(self, project_id):
        """Handle project deletion with confirmation and zoom-out animation."""
        project_name = None
        for pid, name, _ in self.projects:
            if pid == project_id:
                project_name = name
                break

        if not project_name:
            return

        card_to_delete = None
        for card in self.project_cards:
            if card.project_id == project_id:
                card_to_delete = card
                break

        if not card_to_delete:
            return

        dialog = ConfirmationDialog(project_name, self)
        if dialog.exec():
            self.animate_card_deletion(card_to_delete, project_id, project_name)
    
    def animate_card_deletion(self, card, project_id, project_name):
        """Animate the card deletion with zoom-out effect."""
        # Store references to prevent garbage collection
        self._deleting_card = card
        self._project_id = project_id
        self._project_name = project_name
        
        # Create opacity effect
        opacity_effect = QGraphicsOpacityEffect()
        card.setGraphicsEffect(opacity_effect)
        
        # Get current geometry
        current_rect = card.geometry()
        center = current_rect.center()
        
        # Calculate target geometry (scaled down to center point)
        target_size = 0
        target_rect = QRect(
            center.x() - target_size // 2,
            center.y() - target_size // 2,
            target_size,
            target_size
        )
        
        # Create animations
        self.scale_animation = QPropertyAnimation(card, b"geometry")
        self.opacity_animation = QPropertyAnimation(opacity_effect, b"opacity")
        
        # Configure scale animation
        self.scale_animation.setDuration(400)
        self.scale_animation.setStartValue(current_rect)
        self.scale_animation.setEndValue(target_rect)
        self.scale_animation.setEasingCurve(QEasingCurve.Type.InBack)
        
        # Configure opacity animation
        self.opacity_animation.setDuration(400)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # Connect animation finished to actual deletion
        self.scale_animation.finished.connect(self.on_animation_finished)
        
        # Start animations
        self.scale_animation.start()
        self.opacity_animation.start()
    
    def on_animation_finished(self):
        """Handle animation completion."""
        if hasattr(self, '_deleting_card') and hasattr(self, '_project_id') and hasattr(self, '_project_name'):
            self.complete_project_deletion(self._project_id, self._project_name, self._deleting_card)
            # Clean up references
            delattr(self, '_deleting_card')
            delattr(self, '_project_id')
            delattr(self, '_project_name')
    
    def complete_project_deletion(self, project_id, project_name, card):
        """Complete the project deletion process."""
        print(f"DEBUG: complete_project_deletion called for project_id: {project_id}")
        
        # Import database manager
        from app.services.database_manager import NotesDatabase
        
        # Delete from database
        db = NotesDatabase()
        success = db.delete_project(project_id)
        print(f"DEBUG: Database deletion success: {success}")
        
        if success:
            # Emit signal to notify parent that project was deleted
            self.project_deleted.emit(project_id)
            print(f"DEBUG: Emitted project_deleted signal for project_id: {project_id}")
        else:
            # Show error message and restore card
            card.setGraphicsEffect(None)  # Remove opacity effect
            original_rect = QRect(card.x(), card.y(), 140, 140)  # Restore to original size
            card.setGeometry(original_rect)
            self.show_error_message(f"Failed to delete project '{project_name}'")
    
    def refresh_project_grid_animated(self):
        """Refresh the project grid layout with smooth animations."""
        print(f"DEBUG: refresh_project_grid_animated called with {len(self.projects)} projects")
        
        # Find the scroll area and grid widget
        scroll_area = None
        for child in self.findChildren(QScrollArea):
            scroll_area = child
            break
        
        if not scroll_area:
            print("DEBUG: No scroll area found!")
            return
            
        grid_widget = scroll_area.widget()
        if not grid_widget:
            print("DEBUG: No grid widget found!")
            return
            
        grid_layout = grid_widget.layout()
        if not grid_layout:
            print("DEBUG: No grid layout found!")
            return
        
        print(f"DEBUG: Found layout with {grid_layout.count()} widgets")
        
        # Clear all widgets from layout
        while grid_layout.count():
            child = grid_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        print("DEBUG: Cleared all widgets from layout")
        
        # Re-add new project card first
        new_card = NewProjectCard()
        new_card.clicked.connect(self.create_new_project)
        grid_layout.addWidget(new_card, 0, 0)
        print("DEBUG: Added new project card")
        
        # Re-add existing project cards with animation
        self.project_cards = []  # Reset the list
        row, col = 0, 1
        
        for project_id, name, filepath in self.projects:
            if col >= 3:  # Move to next row after 3 columns
                row += 1
                col = 0
            
            print(f"DEBUG: Adding project card for {name} (ID: {project_id}) at position ({row}, {col})")
            card = ProjectCard(project_id, name, filepath)
            # Fix lambda closure issue by using default parameters
            card.clicked.connect(lambda checked=False, pid=project_id: self.open_project_directly(pid))
            card.delete_requested.connect(lambda checked=False, pid=project_id: self.delete_project(pid))
            self.project_cards.append(card)
            
            # Add card to layout
            grid_layout.addWidget(card, row, col)
            
            # Animate card appearance with delay - fix closure issue
            delay = col * 50
            QTimer.singleShot(delay, lambda c=card: self.animate_card_appearance(c))
            
            col += 1
        
        print(f"DEBUG: Added {len(self.project_cards)} project cards to layout")
        
        # Update the layout
        grid_widget.update()
        scroll_area.update()
        self.update()
        print("DEBUG: UI update completed")
    
    def animate_card_appearance(self, card):
        """Animate card appearance with fade-in effect."""
        # Create opacity effect
        opacity_effect = QGraphicsOpacityEffect()
        card.setGraphicsEffect(opacity_effect)
        
        # Create opacity animation
        self.appearance_animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.appearance_animation.setDuration(300)
        self.appearance_animation.setStartValue(0.0)
        self.appearance_animation.setEndValue(1.0)
        self.appearance_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Start animation
        self.appearance_animation.start()
        
        # Store animation reference to prevent garbage collection
        card._appearance_animation = self.appearance_animation
    
    def refresh_project_grid(self):
        """Refresh the project grid layout after deletion."""
        # Find the scroll area and grid widget
        scroll_area = None
        for child in self.findChildren(QScrollArea):
            scroll_area = child
            break
        
        if not scroll_area:
            return
            
        grid_widget = scroll_area.widget()
        if not grid_widget:
            return
            
        grid_layout = grid_widget.layout()
        if not grid_layout:
            return
        
        # Clear the layout
        while grid_layout.count():
            child = grid_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        # Re-add new project card first
        new_card = NewProjectCard()
        new_card.clicked.connect(self.create_new_project)
        grid_layout.addWidget(new_card, 0, 0)
        
        # Re-add existing project cards
        row, col = 0, 1
        for project_id, name, filepath in self.projects:
            if col >= 3:  # Move to next row after 3 columns
                row += 1
                col = 0
            
            card = ProjectCard(project_id, name, filepath)
            # Fix lambda closure issue by using default parameters
            card.clicked.connect(lambda checked=False, pid=project_id: self.open_project_directly(pid))
            card.delete_requested.connect(lambda checked=False, pid=project_id: self.delete_project(pid))
            self.project_cards.append(card)
            grid_layout.addWidget(card, row, col)
            
            col += 1
        
        # Update the layout
        grid_widget.update()
        scroll_area.update()
        self.update()
    
class ConfirmationDialog(QDialog):
    def __init__(self, project_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialogs.delete_project"))
        self.setFixedSize(400, 280)
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(40, 40, 50, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                color: white;
            }
            QLabel {
                color: white;
                background: transparent;
                border: none;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: 500;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QPushButton#deleteBtn {
                background-color: rgba(220, 53, 69, 0.8);
                border-color: rgba(220, 53, 69, 0.9);
            }
            QPushButton#deleteBtn:hover {
                background-color: rgba(220, 53, 69, 0.9);
                border-color: rgba(220, 53, 69, 1.0);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(tr("dialogs.delete_project"))
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: white;")
        layout.addWidget(title)

        message = QLabel(tr("dialogs.delete_confirmation", project_name=project_name))
        message.setStyleSheet("font-size: 14px; color: rgba(255, 255, 255, 0.9);")
        message.setWordWrap(True)
        layout.addWidget(message)

        warning = QLabel(tr("dialogs.delete_warning"))
        warning.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.7); line-height: 1.4;")
        layout.addWidget(warning)

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        cancel_btn = QPushButton(tr("buttons.cancel"))
        delete_btn = QPushButton(tr("buttons.delete"))
        delete_btn.setObjectName("deleteBtn")

        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(delete_btn)

        layout.addLayout(button_layout)

        cancel_btn.clicked.connect(self.reject)
        delete_btn.clicked.connect(self.accept)
    
    def show_success_message(self, message):
        """Show custom success message overlay."""
        self.show_notification(message, "success")
    
    def show_error_message(self, message):
        """Show custom error message overlay."""
        self.show_notification(message, "error")
    
    def show_notification(self, message, type_="info"):
        """Show custom notification overlay."""
        # Create overlay widget
        overlay = QWidget(self)
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        overlay.resize(self.size())
        overlay.show()
        
        # Create notification
        notification = QWidget(overlay)
        notification.setFixedSize(320, 120)
        
        color = "rgba(40, 167, 69, 0.9)" if type_ == "success" else "rgba(220, 53, 69, 0.9)"
        
        notification.setStyleSheet(f"""
            QWidget {{
                background-color: {color};
                border-radius: 8px;
            }}
            QLabel {{
                color: white;
                background: transparent;
                border: none;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                color: white;
                font-size: 12px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        
        # Center the notification
        notification.move(
            (overlay.width() - notification.width()) // 2,
            (overlay.height() - notification.height()) // 2
        )
        
        # Layout
        layout = QVBoxLayout(notification)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg_label)
        
        # OK button
        ok_btn = QPushButton(tr("buttons.ok"))
        ok_btn.clicked.connect(overlay.close)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        notification.show()
        
        # Auto-close after 3 seconds
        from PySide6.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(overlay.close)
        timer.setSingleShot(True)
        timer.start(3000)