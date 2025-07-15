"""
Via Stations Widget for the Train Times application.

This module provides a widget for managing via stations with dynamic button display,
extracted from the main settings dialog for better maintainability.
"""

import logging
from typing import List, Callable, Optional
from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)


class ViaStationsWidget(QWidget):
    """A widget for displaying and managing via stations as clickable buttons."""
    
    # Signals
    via_station_removed = Signal(str)  # Emitted when a via station is removed
    
    def __init__(self, parent=None, theme_manager=None):
        """
        Initialize the via stations widget.
        
        Args:
            parent: Parent widget
            theme_manager: Theme manager for styling
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._via_stations: List[str] = []
        self._buttons: List[QPushButton] = []
        
        # Widget configuration
        self.setStyleSheet("QWidget { border: none; background: transparent; }")
        self.setMinimumHeight(100)
        self.setMaximumHeight(200)
        
        logger.debug("ViaStationsWidget initialized")
    
    def set_via_stations(self, stations: List[str]):
        """
        Set the via stations list and update the display.
        
        Args:
            stations: List of via station names
        """
        if stations != self._via_stations:
            self._via_stations = stations.copy() if stations else []
            self._update_buttons_display()
            logger.debug(f"Via stations updated: {self._via_stations}")
    
    def get_via_stations(self) -> List[str]:
        """
        Get the current via stations list.
        
        Returns:
            Copy of the current via stations list
        """
        return self._via_stations.copy()
    
    def add_via_station(self, station: str) -> bool:
        """
        Add a via station to the list.
        
        Args:
            station: Station name to add
            
        Returns:
            True if station was added, False if it already exists
        """
        if station and station not in self._via_stations:
            self._via_stations.append(station)
            self._update_buttons_display()
            logger.debug(f"Via station added: {station}")
            return True
        return False
    
    def remove_via_station(self, station: str) -> bool:
        """
        Remove a via station from the list.
        
        Args:
            station: Station name to remove
            
        Returns:
            True if station was removed, False if it wasn't found
        """
        if station in self._via_stations:
            self._via_stations.remove(station)
            self._update_buttons_display()
            self.via_station_removed.emit(station)
            logger.debug(f"Via station removed: {station}")
            return True
        return False
    
    def clear_via_stations(self):
        """Clear all via stations."""
        if self._via_stations:
            self._via_stations.clear()
            self._update_buttons_display()
            logger.debug("All via stations cleared")
    
    def _update_buttons_display(self):
        """Update the via stations buttons display with dynamic sizing and line wrapping."""
        try:
            # Clear existing buttons
            self._clear_existing_buttons()
            
            # Only show buttons for stations that are actually in the list
            if self._via_stations:
                self._create_station_buttons()
                self._arrange_buttons_with_wrapping()
            else:
                # No via stations - reset to minimal height
                self.setMinimumHeight(30)
                self.setMaximumHeight(30)
                
        except Exception as e:
            logger.error(f"Error updating via buttons: {e}")
    
    def _clear_existing_buttons(self):
        """Clear existing button widgets."""
        try:
            # Clear existing widgets by setting them as children of None
            for button in self._buttons:
                button.setParent(None)
            self._buttons.clear()
        except Exception as e:
            logger.error(f"Error clearing existing buttons: {e}")
    
    def _create_station_buttons(self):
        """Create buttons for each via station."""
        try:
            for station in self._via_stations:
                button = QPushButton(station, self)
                button.setToolTip(f"Click to remove {station} from route")
                
                # Connect to remove function
                button.clicked.connect(lambda checked, station=station: self.remove_via_station(station))
                
                # Apply styling
                self._apply_button_styling(button)
                
                self._buttons.append(button)
                
        except Exception as e:
            logger.error(f"Error creating station buttons: {e}")
    
    def _arrange_buttons_with_wrapping(self):
        """Arrange buttons with line wrapping and dynamic sizing."""
        try:
            # Dynamic button sizing parameters - optimized for better layout
            min_button_width = 120  # Minimum button width
            max_button_width = 200  # Maximum button width to prevent overflow
            button_height = 28      # Button height for better readability
            horizontal_spacing = 4  # Spacing between buttons
            vertical_spacing = 4    # Spacing between rows
            max_row_width = 700     # Maximum width available for buttons per row
            
            # Calculate button widths based on text content
            button_data = []
            for i, button in enumerate(self._buttons):
                station = self._via_stations[i]
                # Better text width estimation: 8 pixels per character + padding
                estimated_text_width = len(station) * 8 + 25  # +25 for padding and margins
                button_width = max(min_button_width, min(estimated_text_width, max_button_width))
                button_data.append({'button': button, 'width': button_width})
            
            # Arrange buttons with line wrapping
            current_row = 0
            current_x = 0
            max_rows_used = 0
            
            for data in button_data:
                button = data['button']
                button_width = data['width']
                
                # Check if button fits on current row
                if current_x + button_width > max_row_width and current_x > 0:
                    # Move to next row
                    current_row += 1
                    current_x = 0
                
                # Track maximum rows used
                max_rows_used = max(max_rows_used, current_row)
                
                # Calculate position
                x = current_x
                y = current_row * (button_height + vertical_spacing)
                
                # Set button geometry
                button.setGeometry(x, y, button_width, button_height)
                button.show()
                
                # Update position for next button
                current_x += button_width + horizontal_spacing
            
            # Update widget height to accommodate all rows with some extra padding
            total_height = (max_rows_used + 1) * (button_height + vertical_spacing) + 10  # +10 for extra padding
            self.setMinimumHeight(total_height)
            self.setMaximumHeight(total_height)
            
        except Exception as e:
            logger.error(f"Error arranging buttons: {e}")
    
    def _apply_button_styling(self, button: QPushButton):
        """Apply styling to a via station button."""
        try:
            # Get theme colors if theme manager is available
            if self.theme_manager:
                current_theme = self.theme_manager.current_theme
                if current_theme == "light":
                    # Light theme styling
                    background_color = "#2e7d32"
                    border_color = "#1b5e20"
                    hover_color = "#d32f2f"
                    pressed_color = "#c62828"
                else:
                    # Dark theme styling
                    background_color = "#2e7d32"
                    border_color = "#1b5e20"
                    hover_color = "#d32f2f"
                    pressed_color = "#c62828"
            else:
                # Fallback styling
                background_color = "#2e7d32"
                border_color = "#1b5e20"
                hover_color = "#d32f2f"
                pressed_color = "#c62828"
            
            # Style as selected/active via station with improved styling
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {background_color};
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    padding: 3px 6px;
                    margin: 0px;
                    color: white;
                    font-weight: bold;
                    font-size: 11px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                }}
                QPushButton:pressed {{
                    background-color: {pressed_color};
                }}
            """)
            
        except Exception as e:
            logger.error(f"Error applying button styling: {e}")
    
    def update_theme(self, theme_manager):
        """
        Update the theme manager and refresh styling.
        
        Args:
            theme_manager: New theme manager instance
        """
        self.theme_manager = theme_manager
        # Refresh all button styling
        for button in self._buttons:
            self._apply_button_styling(button)
        logger.debug("Theme updated for via stations widget")
    
    def get_button_count(self) -> int:
        """
        Get the number of via station buttons currently displayed.
        
        Returns:
            Number of buttons
        """
        return len(self._buttons)
    
    def is_empty(self) -> bool:
        """
        Check if there are no via stations.
        
        Returns:
            True if no via stations are set
        """
        return len(self._via_stations) == 0