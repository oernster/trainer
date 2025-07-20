"""
Route Details Widget for the Train Settings Dialog.

This widget displays detailed route information including journey time,
distance, changes, and interchange stations.
"""

import logging
import sys
from typing import Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QApplication,
    QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from .time_picker_widget import TimePickerWidget

logger = logging.getLogger(__name__)


class RouteDetailsWidget(QWidget):
    """Widget for displaying detailed route information."""
    
    # Signals
    departure_time_changed = Signal(str)
    
    def __init__(self, parent=None, theme_manager=None):
        """
        Initialize the route details widget.
        
        Args:
            parent: Parent widget
            theme_manager: Theme manager for styling
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        
        # UI elements
        self.time_picker = None
        self.arrival_time_edit = None
        self.journey_time_label = None
        self.distance_label = None
        self.route_details_label = None
        
        # Current route data and preferences
        self.route_data = {}
        self.preferences = {}
        
        # Detect small screen for platform-specific adjustments
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            self.is_small_screen = screen_geometry.width() <= 1440 or screen_geometry.height() <= 900
        else:
            self.is_small_screen = False
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("RouteDetailsWidget initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Platform-specific spacing
        if sys.platform.startswith('linux') and self.is_small_screen:
            layout.setSpacing(10)  # Reduced spacing for Linux small screens
        else:
            layout.setSpacing(15)
        
        # Time selection section
        time_group = self._create_time_selection_group()
        layout.addWidget(time_group)
        
        # Route information section
        info_group = self._create_route_info_group()
        layout.addWidget(info_group)
    
    def _create_time_selection_group(self) -> QGroupBox:
        """Create the time selection group box."""
        group = QGroupBox("Journey Times")
        layout = QGridLayout(group)
        
        # Departure time
        dep_label = QLabel("Departure:")
        dep_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(dep_label, 0, 0)
        
        self.time_picker = TimePickerWidget("08:00", parent=self, theme_manager=self.theme_manager)
        layout.addWidget(self.time_picker, 0, 1)
        
        # Arrival time (read-only, calculated)
        arr_label = QLabel("Arrival:")
        arr_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(arr_label, 0, 2)
        
        self.arrival_time_edit = QLabel("--:--")
        self.arrival_time_edit.setObjectName("arrivalTimeEdit")
        layout.addWidget(self.arrival_time_edit, 0, 3)
        
        # Journey time display
        journey_label = QLabel("Journey Time:")
        journey_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(journey_label, 1, 0)
        
        self.journey_time_label = QLabel("--:--")
        self.journey_time_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
        layout.addWidget(self.journey_time_label, 1, 1)
        
        # Distance display
        dist_label = QLabel("Distance:")
        dist_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(dist_label, 1, 2)
        
        self.distance_label = QLabel("-- km")
        layout.addWidget(self.distance_label, 1, 3)
        
        return group
    
    def _create_route_info_group(self) -> QGroupBox:
        """Create the route information group box."""
        group = QGroupBox("Route Information")
        
        # Platform-specific group box sizing
        if sys.platform.startswith('linux') and self.is_small_screen:
            # Make the group box expand to fill available space
            group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            # Set a large minimum height for the entire group box to extend the border
            group.setMinimumHeight(450)  # Increased to ensure border is fully visible
        elif sys.platform == "darwin":
            # CRITICAL FIX: macOS also needs larger group box for route information
            group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            group.setMinimumHeight(250)  # Provide adequate space for route details on macOS
        
        layout = QVBoxLayout(group)
        
        # Platform-specific layout settings
        if sys.platform.startswith('linux') and self.is_small_screen:
            # Minimal margins for maximum space usage
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(0)
        else:
            # Default margins
            layout.setContentsMargins(5, 10, 5, 10)
        
        # Route details
        self.route_details_label = QLabel("No route selected")
        self.route_details_label.setObjectName("routeDetailsLabel")
        self.route_details_label.setWordWrap(True)
        
        # Always use top alignment for text
        self.route_details_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Platform-specific settings
        if sys.platform.startswith('linux'):
            if self.is_small_screen:
                # Make the label MUCH taller for Linux small screens - INCREASED MORE
                self.route_details_label.setMinimumHeight(400)  # Increased from 350
                # Add internal padding to keep text at top with proper spacing
                self.route_details_label.setStyleSheet("""
                    QLabel {
                        padding-top: 10px;
                        padding-left: 10px;
                        padding-right: 10px;
                        padding-bottom: 20px;
                        background-color: transparent;
                    }
                """)
                # Even smaller font for Linux small screens
                font = self.route_details_label.font()
                font.setPointSize(font.pointSize() - 2)  # Reduced by 2 points instead of 1
                self.route_details_label.setFont(font)
            else:
                # Linux normal screens
                self.route_details_label.setMinimumHeight(300)  # Increased from 250
                self.route_details_label.setStyleSheet("""
                    QLabel {
                        padding: 10px;
                        background-color: transparent;
                    }
                """)
                # Also reduce font for normal Linux screens
                font = self.route_details_label.font()
                font.setPointSize(font.pointSize() - 1)
                self.route_details_label.setFont(font)
        elif sys.platform == "darwin":
            # CRITICAL FIX: macOS needs much more space for route details, especially on 13" laptops
            self.route_details_label.setMinimumHeight(200)  # Much larger than original 80px
            self.route_details_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: transparent;
                }
            """)
        else:
            # Original height for Windows only
            self.route_details_label.setMinimumHeight(80)
        
        layout.addWidget(self.route_details_label)
        
        return group
    
    def _connect_signals(self):
        """Connect signals and slots."""
        if self.time_picker:
            self.time_picker.timeChanged.connect(self._on_departure_time_changed)
    
    def _on_departure_time_changed(self, time_str: str):
        """Handle departure time change."""
        self.departure_time_changed.emit(time_str)
        self._calculate_arrival_time()
        logger.debug(f"Departure time changed: {time_str}")
    
    def set_departure_time(self, time_str: str):
        """Set the departure time."""
        if self.time_picker:
            self.time_picker.set_time(time_str)
    
    def get_departure_time(self) -> str:
        """Get the current departure time."""
        return self.time_picker.get_time() if self.time_picker else "08:00"
    
    def update_route_data(self, route_data: Dict[str, Any]):
        """Update the route data and refresh display."""
        self.route_data = route_data.copy() if route_data else {}
        self._update_route_info()
        self._calculate_arrival_time()
        logger.debug(f"Route data updated: {len(self.route_data)} keys")
    
    def set_preferences(self, preferences: Dict[str, Any]):
        """Set preferences and refresh display."""
        self.preferences = preferences.copy() if preferences else {}
        self._update_route_info()  # Refresh display with new preferences
        logger.debug(f"Preferences updated: {list(self.preferences.keys())}")
    
    def clear_route_data(self):
        """Clear all route data."""
        self.route_data = {}
        self._update_route_info()
        logger.debug("Route data cleared")
    
    def _update_route_info(self):
        """Update the route information display."""
        try:
            if self.route_data:
                # Update journey time
                journey_time = self.route_data.get('journey_time', 0)
                if self.journey_time_label:
                    if journey_time > 0:
                        hours = journey_time // 60
                        minutes = journey_time % 60
                        if hours > 0:
                            self.journey_time_label.setText(f"{hours}h {minutes}m")
                        else:
                            self.journey_time_label.setText(f"{minutes}m")
                    else:
                        self.journey_time_label.setText("--:--")
                
                # Update distance
                distance = self.route_data.get('distance', 0)
                if self.distance_label:
                    if distance > 0:
                        self.distance_label.setText(f"{distance:.1f} km")
                    else:
                        self.distance_label.setText("-- km")
                
                # Update route details
                if self.route_details_label:
                    details = self._format_route_details()
                    self.route_details_label.setText(details)
                
            else:
                if self.journey_time_label:
                    self.journey_time_label.setText("--:--")
                if self.distance_label:
                    self.distance_label.setText("-- km")
                if self.route_details_label:
                    self.route_details_label.setText("No route selected")
                if self.arrival_time_edit:
                    self.arrival_time_edit.setText("--:--")
                
        except Exception as e:
            logger.error(f"Error updating route info: {e}")
    
    def _format_route_details(self) -> str:
        """Format route details for display using horizontal space efficiently."""
        try:
            # From and To stations on one line
            from_station = self.route_data.get('from_station', 'N/A')
            to_station = self.route_data.get('to_station', 'N/A')
            
            # Check if we should show intermediate stations
            show_intermediate = self.preferences.get('show_intermediate_stations', True)
            
            if show_intermediate:
                # Show full route with intermediate stations
                full_path = self.route_data.get('full_path', [])
                if full_path and len(full_path) > 2:
                    # Use full path which includes all intermediate stations
                    route_line = ' → '.join(full_path)
                else:
                    # Fallback to via stations if full_path not available
                    via_stations = self.route_data.get('via_stations', [])
                    if via_stations:
                        route_line = f"{from_station} → {' → '.join(via_stations)} → {to_station}"
                    else:
                        route_line = f"{from_station} → {to_station}"
            else:
                # Show only origin, destination, and change stations (yellow stations)
                interchange_stations = self.route_data.get('interchange_stations', [])
                if interchange_stations:
                    # Show route with only change stations
                    route_parts = [from_station]
                    route_parts.extend(interchange_stations)
                    route_parts.append(to_station)
                    route_line = ' → '.join(route_parts)
                else:
                    # No changes, just origin to destination
                    route_line = f"{from_station} → {to_station}"
            
            details = [route_line]
            
            # Changes and route type on one line
            changes = self.route_data.get('changes', 0)
            route_type = self.route_data.get('route_type', '')
            is_direct = self.route_data.get('is_direct', False)
            
            info_parts = []
            if is_direct:
                info_parts.append("✓ Direct route")
            else:
                info_parts.append(f"Changes: {changes}")
            
            if route_type:
                info_parts.append(f"Type: {route_type}")
            
            if info_parts:
                details.append(" • ".join(info_parts))
            
            # Show interchange stations where changes occur
            interchange_stations = self.route_data.get('interchange_stations', [])
            if interchange_stations:
                details.append(f"Change at: {', '.join(interchange_stations)}")
            elif self.route_data.get('operators') and not is_direct:
                # Fallback to operators if no interchange stations available
                operators = self.route_data.get('operators', [])
                if len(operators) <= 3:  # Only show if not too many
                    details.append(f"Operators: {', '.join(operators)}")
            
            # Check for walking segments and display walking information
            segments = self.route_data.get('segments', [])
            walking_segments = []
            
            for segment in segments:
                if hasattr(segment, 'line_name') and segment.line_name == 'WALKING':
                    from_station = segment.from_station
                    to_station = segment.to_station
                    distance_km = segment.distance_km
                    time_min = segment.journey_time_minutes
                    
                    # Calculate walking time based on 4mph if not provided
                    if not time_min and distance_km:
                        # 4mph = 6.44km/h = 0.107km/min
                        time_min = int(distance_km / 0.107)
                    
                    walking_segments.append(f"Walk {distance_km:.1f}km ({time_min}min) between {from_station} and {to_station}")
            
            if walking_segments:
                details.append("Walking required:")
                details.extend([f"• {segment}" for segment in walking_segments])
            
            return "\n".join(details)
            
        except Exception as e:
            logger.error(f"Error formatting route details: {e}")
            return "Error displaying route details"
    
    def _calculate_arrival_time(self):
        """Calculate and display arrival time."""
        try:
            departure_time = self.get_departure_time()
            journey_time = self.route_data.get('journey_time', 0)
            
            if departure_time and journey_time > 0:
                arrival_time = self._add_time_duration(departure_time, journey_time)
                if self.arrival_time_edit:
                    self.arrival_time_edit.setText(arrival_time)
            else:
                if self.arrival_time_edit:
                    self.arrival_time_edit.setText("--:--")
                
        except Exception as e:
            logger.error(f"Error calculating arrival time: {e}")
            if self.arrival_time_edit:
                self.arrival_time_edit.setText("--:--")
    
    def _add_time_duration(self, start_time: str, duration_minutes: int) -> str:
        """Add duration in minutes to a time string."""
        try:
            hours, minutes = map(int, start_time.split(':'))
            total_minutes = hours * 60 + minutes + duration_minutes
            
            result_hours = (total_minutes // 60) % 24
            result_minutes = total_minutes % 60
            
            return f"{result_hours:02d}:{result_minutes:02d}"
            
        except Exception as e:
            logger.error(f"Error adding time duration: {e}")
            return "--:--"
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the widget."""
        if self.time_picker:
            self.time_picker.setEnabled(enabled)
    
    def apply_theme(self, theme_manager):
        """Apply theme to the widget."""
        self.theme_manager = theme_manager
        if theme_manager:
            try:
                theme_manager.apply_theme_to_widget(self)
            except Exception as e:
                logger.error(f"Error applying theme: {e}")