"""
Custom scroll bar widget for train list display.

This module provides a custom scroll bar widget that properly reflects content state
and provides visual scroll bar indicator with accurate scrolling interaction.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor
from .train_widgets_base import BaseTrainWidget

logger = logging.getLogger(__name__)


class CustomScrollBar(BaseTrainWidget):
    """
    Custom scroll bar widget that properly reflects content state.
    
    This widget provides a visual scroll bar indicator that accurately shows
    the proportion of visible content and allows for proper scrolling interaction.
    """
    
    # Signals for scroll events
    scroll_requested = Signal(int)  # Emitted when user requests scroll to position
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the custom scroll bar."""
        super().__init__(parent)
        
        # Scroll bar properties
        self._minimum = 0
        self._maximum = 100
        self._value = 0
        self._page_step = 10
        self._single_step = 1
        
        # Visual properties
        self._handle_pressed = False
        self._handle_hover = False
        self._drag_start_pos = None
        self._drag_start_value = None
        
        # Theme properties (will be set by _apply_theme_styles)
        self._track_color = "#2d2d2d"
        self._handle_color = "#555555"
        self._handle_hover_color = "#666666"
        self._handle_pressed_color = "#666666"
        
        self._setup_widget()
        self._apply_theme_styles()
    
    def _setup_widget(self) -> None:
        """Setup widget properties and behavior."""
        # Set fixed width for vertical scroll bar
        self.setFixedWidth(12)
        self.setMinimumHeight(50)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
    
    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styles to the scroll bar."""
        colors = self.get_theme_colors(self.current_theme)
        
        if self.current_theme == "dark":
            self._track_color = colors["background_secondary"]
            self._handle_color = colors["border_secondary"]
            self._handle_hover_color = colors["background_hover"]
            self._handle_pressed_color = colors["background_hover"]
        else:  # light theme
            self._track_color = colors["background_secondary"]
            self._handle_color = colors["border_primary"]
            self._handle_hover_color = colors["text_secondary"]
            self._handle_pressed_color = colors["text_secondary"]
        
        # Trigger repaint with new colors
        self.update()
    
    def setRange(self, minimum: int, maximum: int) -> None:
        """Set the scroll range."""
        self._minimum = minimum
        self._maximum = maximum
        self._value = max(minimum, min(self._value, maximum))
        self.update()
    
    def setValue(self, value: int) -> None:
        """Set the current scroll value."""
        old_value = self._value
        self._value = max(self._minimum, min(value, self._maximum))
        if old_value != self._value:
            self.update()
    
    def setPageStep(self, step: int) -> None:
        """Set the page step size."""
        self._page_step = step
    
    def setSingleStep(self, step: int) -> None:
        """Set the single step size."""
        self._single_step = step
    
    def value(self) -> int:
        """Get the current scroll value."""
        return self._value
    
    def minimum(self) -> int:
        """Get the minimum scroll value."""
        return self._minimum
    
    def maximum(self) -> int:
        """Get the maximum scroll value."""
        return self._maximum
    
    def _get_handle_rect(self):
        """Calculate the handle rectangle based on current state."""
        if self._maximum <= self._minimum:
            # No scrolling needed - handle fills entire area
            return self.rect().adjusted(2, 2, -2, -2)
        
        # Calculate handle size and position
        total_range = self._maximum - self._minimum
        visible_ratio = min(1.0, self._page_step / (total_range + self._page_step))
        
        # Handle height based on visible content ratio
        available_height = self.height() - 4  # Account for margins
        handle_height = max(20, int(available_height * visible_ratio))
        
        # Handle position based on scroll value
        if total_range > 0:
            scroll_ratio = (self._value - self._minimum) / total_range
            max_handle_top = available_height - handle_height
            handle_top = int(max_handle_top * scroll_ratio) + 2
        else:
            handle_top = 2
        
        return self.rect().adjusted(2, handle_top, -2, handle_top + handle_height - self.height() + 2)
    
    def paintEvent(self, event):
        """Paint the custom scroll bar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background track using theme-aware color
        track_color = QColor(self._track_color)
        painter.fillRect(self.rect(), track_color)
        
        # Only draw handle if there's content to scroll
        if self._maximum > self._minimum:
            handle_rect = self._get_handle_rect()
            
            # Handle color based on state using theme-aware colors
            if self._handle_pressed:
                handle_color = QColor(self._handle_pressed_color)
            elif self._handle_hover:
                handle_color = QColor(self._handle_hover_color)
            else:
                handle_color = QColor(self._handle_color)
            
            # Draw handle with rounded corners
            painter.fillRect(handle_rect, handle_color)
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            handle_rect = self._get_handle_rect()
            
            if handle_rect.contains(event.pos()):
                # Start dragging the handle
                self._handle_pressed = True
                self._drag_start_pos = event.pos()
                self._drag_start_value = self._value
                self.update()
            else:
                # Click in track - jump to position
                self._jump_to_position(event.pos())
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self._handle_pressed and self._drag_start_pos is not None:
            # Handle dragging
            delta_y = event.pos().y() - self._drag_start_pos.y()
            
            if self._maximum > self._minimum:
                available_height = self.height() - 4
                handle_height = self._get_handle_rect().height()
                max_handle_travel = available_height - handle_height
                
                if max_handle_travel > 0:
                    value_per_pixel = (self._maximum - self._minimum) / max_handle_travel
                    new_value = self._drag_start_value + (delta_y * value_per_pixel)
                    self.setValue(int(new_value))
                    self.scroll_requested.emit(self._value)
        else:
            # Update hover state
            handle_rect = self._get_handle_rect()
            old_hover = self._handle_hover
            self._handle_hover = handle_rect.contains(event.pos())
            
            if old_hover != self._handle_hover:
                self.update()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_pressed = False
            self._drag_start_pos = None
            self._drag_start_value = None
            self.update()
        
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        """Handle wheel scroll events."""
        delta = event.angleDelta().y()
        if delta != 0:
            # Scroll by single step
            step = self._single_step if delta > 0 else -self._single_step
            new_value = self._value - step  # Negative because wheel up should scroll up
            self.setValue(new_value)
            self.scroll_requested.emit(self._value)
        
        event.accept()
    
    def _jump_to_position(self, pos):
        """Jump scroll position to clicked location."""
        if self._maximum <= self._minimum:
            return
        
        available_height = self.height() - 4
        click_ratio = max(0, min(1, (pos.y() - 2) / available_height))
        new_value = self._minimum + (click_ratio * (self._maximum - self._minimum))
        
        self.setValue(int(new_value))
        self.scroll_requested.emit(self._value)