"""
Route Info Widget for the Train Times application.

This module provides a widget for displaying route information with proper styling,
extracted from the main settings dialog for better maintainability.
"""

import logging
from typing import List, Optional
from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)


class RouteInfoWidget(QLabel):
    """A widget for displaying route information with dynamic styling."""
    
    # Signals
    route_info_updated = Signal(str)  # Emitted when route info text changes
    
    def __init__(self, parent=None, theme_manager=None):
        """
        Initialize the route info widget.
        
        Args:
            parent: Parent widget
            theme_manager: Theme manager for styling
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        
        # Widget configuration
        self.setWordWrap(True)  # Enable word wrapping
        self.setMinimumHeight(50)  # Minimum height for wrapped text
        self.setMaximumHeight(100)  # Maximum height for longer text
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)  # Left-align and top-align
        
        # Allow vertical expansion
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding
        )
        
        # Set initial text and styling
        self.set_default_message()
        
        logger.debug("RouteInfoWidget initialized")
    
    def set_default_message(self):
        """Set the default message when no route is configured."""
        self.setText("Select From and To stations to enable routing")
        self._apply_default_styling()
    
    def update_route_info(self, from_station: str, to_station: str, via_stations: List[str], 
                         route_auto_fixed: bool = False):
        """
        Update the route information display.
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            via_stations: List of via station names
            route_auto_fixed: Whether the route was auto-fixed
        """
        try:
            if not from_station or not to_station:
                self.set_default_message()
                return
            
            # Build route description
            route_parts = [from_station]
            route_parts.extend(via_stations)
            route_parts.append(to_station)
            
            # Create route description
            if len(route_parts) == 2:
                route_text = f"Direct: {route_parts[0]} → {route_parts[1]}"
            else:
                route_text = f"Route: {' → '.join(route_parts)}"
            
            # Add visual indicator if route was auto-fixed
            if route_auto_fixed:
                route_text += " 🔧 (Auto-Fixed)"
                self._apply_auto_fixed_styling()
            else:
                self._apply_normal_styling()
            
            self.setText(route_text)
            self.route_info_updated.emit(route_text)
            
            logger.debug(f"Route info updated: {route_text}")
            
        except Exception as e:
            logger.error(f"Error updating route info: {e}")
            self.setText("Error updating route information")
            self._apply_error_styling()
    
    def set_progress_message(self, operation_type: str, message: str, percentage: Optional[int] = None):
        """
        Set a progress message for ongoing operations.
        
        Args:
            operation_type: Type of operation (auto_fix, suggest_via, fastest_route, search)
            message: Progress message
            percentage: Optional progress percentage
        """
        try:
            # Choose appropriate emoji based on operation type
            emoji_map = {
                "auto_fix": "🔧",
                "suggest_via": "🔍", 
                "fastest_route": "⚡",
                "search": "🔍"
            }
            
            emoji = emoji_map.get(operation_type, "⏳")
            
            if percentage is not None:
                display_text = f"{emoji} {message} ({percentage}%)"
            else:
                display_text = f"{emoji} {message}"
            
            self.setText(display_text)
            self._apply_progress_styling(operation_type)
            
            logger.debug(f"Progress message set: {display_text}")
            
        except Exception as e:
            logger.error(f"Error setting progress message: {e}")
    
    def set_error_message(self, message: str):
        """
        Set an error message.
        
        Args:
            message: Error message to display
        """
        try:
            self.setText(f"❌ {message}")
            self._apply_error_styling()
            logger.debug(f"Error message set: {message}")
        except Exception as e:
            logger.error(f"Error setting error message: {e}")
    
    def set_success_message(self, message: str):
        """
        Set a success message.
        
        Args:
            message: Success message to display
        """
        try:
            self.setText(f"✅ {message}")
            self._apply_success_styling()
            logger.debug(f"Success message set: {message}")
        except Exception as e:
            logger.error(f"Error setting success message: {e}")
    
    def set_warning_message(self, message: str):
        """
        Set a warning message.
        
        Args:
            message: Warning message to display
        """
        try:
            self.setText(f"⚠️ {message}")
            self._apply_warning_styling()
            logger.debug(f"Warning message set: {message}")
        except Exception as e:
            logger.error(f"Error setting warning message: {e}")
    
    def _apply_default_styling(self):
        """Apply default styling for normal route info."""
        self.setStyleSheet("""
            QLabel {
                color: #888888;
                font-style: italic;
                padding: 5px;
            }
        """)
    
    def _apply_normal_styling(self):
        """Apply normal styling for route information."""
        self.setStyleSheet("""
            QLabel {
                color: #888888;
                font-style: italic;
                padding: 5px;
            }
        """)
    
    def _apply_auto_fixed_styling(self):
        """Apply styling for auto-fixed routes."""
        self.setStyleSheet("""
            QLabel {
                color: #ff9800;
                font-style: italic;
                font-weight: bold;
                padding: 5px;
                background-color: rgba(255, 152, 0, 0.1);
                border-radius: 4px;
            }
        """)
    
    def _apply_progress_styling(self, operation_type: str):
        """Apply styling for progress messages."""
        if operation_type == "auto_fix":
            color = "#ff9800"  # Orange for auto-fix
        elif operation_type in ["suggest_via", "fastest_route", "search"]:
            color = "#1976d2"  # Blue for other operations
        else:
            color = "#888888"  # Default gray
        
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-style: italic;
                font-weight: bold;
                padding: 5px;
            }}
        """)
    
    def _apply_error_styling(self):
        """Apply styling for error messages."""
        self.setStyleSheet("""
            QLabel {
                color: #d32f2f;
                font-style: italic;
                font-weight: bold;
                padding: 5px;
                background-color: rgba(211, 47, 47, 0.1);
                border-radius: 4px;
            }
        """)
    
    def _apply_success_styling(self):
        """Apply styling for success messages."""
        self.setStyleSheet("""
            QLabel {
                color: #2e7d32;
                font-style: italic;
                font-weight: bold;
                padding: 5px;
                background-color: rgba(46, 125, 50, 0.1);
                border-radius: 4px;
            }
        """)
    
    def _apply_warning_styling(self):
        """Apply styling for warning messages."""
        self.setStyleSheet("""
            QLabel {
                color: #f57c00;
                font-style: italic;
                font-weight: bold;
                padding: 5px;
                background-color: rgba(245, 124, 0, 0.1);
                border-radius: 4px;
            }
        """)
    
    def update_theme(self, theme_manager):
        """
        Update the theme manager and refresh styling.
        
        Args:
            theme_manager: New theme manager instance
        """
        self.theme_manager = theme_manager
        # Refresh styling based on current text content
        current_text = self.text()
        
        if "Auto-Fixed" in current_text:
            self._apply_auto_fixed_styling()
        elif current_text.startswith("❌"):
            self._apply_error_styling()
        elif current_text.startswith("✅"):
            self._apply_success_styling()
        elif current_text.startswith("⚠️"):
            self._apply_warning_styling()
        elif any(emoji in current_text for emoji in ["🔧", "🔍", "⚡", "⏳"]):
            # Determine operation type from emoji
            if "🔧" in current_text:
                self._apply_progress_styling("auto_fix")
            else:
                self._apply_progress_styling("other")
        else:
            self._apply_normal_styling()
        
        logger.debug("Theme updated for route info widget")
    
    def clear_message(self):
        """Clear the current message and return to default."""
        self.set_default_message()
    
    def get_current_message(self) -> str:
        """
        Get the current message text.
        
        Returns:
            Current message text
        """
        return self.text()
    
    def is_showing_progress(self) -> bool:
        """
        Check if currently showing a progress message.
        
        Returns:
            True if showing progress message
        """
        current_text = self.text()
        return any(emoji in current_text for emoji in ["🔧", "🔍", "⚡", "⏳"])
    
    def is_showing_error(self) -> bool:
        """
        Check if currently showing an error message.
        
        Returns:
            True if showing error message
        """
        return self.text().startswith("❌")