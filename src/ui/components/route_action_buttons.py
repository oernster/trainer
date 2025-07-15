"""
Route Action Buttons Widget for the Train Settings Dialog.

This widget provides action buttons for route operations like
finding routes, auto-fixing, and clearing routes.
"""

import logging
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import Signal

logger = logging.getLogger(__name__)


class RouteActionButtons(QWidget):
    """Widget containing route action buttons."""
    
    # Signals
    find_route_clicked = Signal()
    clear_route_clicked = Signal()
    
    def __init__(self, parent=None, theme_manager=None):
        """
        Initialize the route action buttons widget.
        
        Args:
            parent: Parent widget
            theme_manager: Theme manager for styling
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        
        # UI elements
        self.find_route_button = None
        self.clear_route_button = None
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("RouteActionButtons initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        
        # Find route button
        self.find_route_button = QPushButton("Find Route")
        self.find_route_button.setObjectName("findRouteButton")
        self.find_route_button.setToolTip("Find the best route between selected stations")
        layout.addWidget(self.find_route_button)
        
        
        # Clear route button
        self.clear_route_button = QPushButton("Clear Route")
        self.clear_route_button.setObjectName("clearRouteButton")
        self.clear_route_button.setToolTip("Clear current route and via stations")
        layout.addWidget(self.clear_route_button)
        
        # Add stretch to push buttons to the left
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addItem(spacer)
    
    def _connect_signals(self):
        """Connect signals and slots."""
        if self.find_route_button:
            self.find_route_button.clicked.connect(self.find_route_clicked.emit)
        if self.clear_route_button:
            self.clear_route_button.clicked.connect(self.clear_route_clicked.emit)
    
    def set_find_route_enabled(self, enabled: bool):
        """Enable or disable the find route button."""
        if self.find_route_button:
            self.find_route_button.setEnabled(enabled)
    
    
    def set_clear_route_enabled(self, enabled: bool):
        """Enable or disable the clear route button."""
        if self.clear_route_button:
            self.clear_route_button.setEnabled(enabled)
    
    def set_all_enabled(self, enabled: bool):
        """Enable or disable all buttons."""
        self.set_find_route_enabled(enabled)
        self.set_clear_route_enabled(enabled)
    
    def set_find_route_text(self, text: str):
        """Set the text of the find route button."""
        if self.find_route_button:
            self.find_route_button.setText(text)
    
    
    def reset_button_texts(self):
        """Reset all button texts to their defaults."""
        self.set_find_route_text("Find Route")
    
    def show_progress(self, button_type: str, progress_text: str):
        """
        Show progress on a specific button.
        
        Args:
            button_type: 'find', 'auto_fix', or 'clear'
            progress_text: Text to show during progress
        """
        if button_type == 'find':
            self.set_find_route_text(progress_text)
            self.set_find_route_enabled(False)
        elif button_type == 'clear':
            # Clear doesn't typically show progress, but handle it
            self.set_clear_route_enabled(False)
    
    def hide_progress(self, button_type: str):
        """
        Hide progress and restore normal state.
        
        Args:
            button_type: 'find', 'auto_fix', or 'clear'
        """
        if button_type == 'find':
            self.set_find_route_text("Find Route")
            self.set_find_route_enabled(True)
        elif button_type == 'clear':
            self.set_clear_route_enabled(True)
    
    def apply_theme(self, theme_manager):
        """Apply theme to the widget."""
        self.theme_manager = theme_manager
        if theme_manager:
            try:
                theme_manager.apply_theme_to_widget(self)
            except Exception as e:
                logger.error(f"Error applying theme: {e}")