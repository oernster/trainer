"""
Train item widget for displaying individual train information.

This module provides a widget for displaying comprehensive train information
including departure time, destination, platform, operator, status, and current location.
"""

import json
import logging
import os
from typing import List, Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy, QLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ...models.train_data import TrainData
from ...core.services.interchange_detection_service import InterchangeDetectionService
from ...ui.formatters.underground_formatter import UndergroundFormatter
from .train_widgets_base import BaseTrainWidget

logger = logging.getLogger(__name__)


class TrainItemWidget(BaseTrainWidget):
    """
    Individual train information display widget with theme support.

    Displays comprehensive train information including departure time,
    destination, platform, operator, status, and current location.
    """

    # Signal emitted when train item is clicked
    train_clicked = Signal(TrainData)
    # Signal emitted when route button is clicked
    route_clicked = Signal(TrainData)

    def __init__(self, train_data: TrainData, theme: str = "dark",
                 train_manager=None, preferences: Optional[dict] = None, parent: Optional[QWidget] = None):
        """
        Initialize train item widget.

        Args:
            train_data: Train information to display
            theme: Current theme ("dark" or "light")
            train_manager: Train manager instance for accessing route data
            preferences: User preferences dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize theme
        self.current_theme = theme
        
        self.train_data = train_data
        self.train_manager = train_manager
        self.preferences = preferences or {}
        
        # Initialize Underground formatter for black box routing
        self.underground_formatter = UndergroundFormatter()
        
        # Load configuration files
        self.major_stations = self._load_major_stations()
        self.underground_system_indicators = self._load_underground_system_indicators()

        self._setup_ui()
        self._apply_theme_styles()
        
    def _load_major_stations(self) -> set:
        """Load major stations from configuration file."""
        try:
            # Get the path to the data directory
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            file_path = os.path.join(data_dir, 'major_stations.json')
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                return set(data.get('major_stations', []))
        except Exception as e:
            self.logger.error(f"Error loading major stations: {e}")
            # Fallback to empty set if file can't be loaded
            return set()
            
    def _load_underground_system_indicators(self) -> dict:
        """Load underground system indicators from configuration file."""
        try:
            # Get the path to the data directory
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            file_path = os.path.join(data_dir, 'underground_systems.json')
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get('system_indicators', {})
        except Exception as e:
            self.logger.error(f"Error loading underground system indicators: {e}")
            # Fallback to empty dict if file can't be loaded
            return {}

    def _setup_ui(self) -> None:
        """Setup the train item UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)  # No spacing between layout elements
        
        # Set size policy to allow expansion
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # Main train info line
        self._create_main_info_line(layout)
        
        # Second line: Operator, service type, duration, status
        self._create_details_line(layout)
        
        # Third line: Calling points (intermediate stations) - with wrapping
        self._create_calling_points_section(layout)
        
        # Fourth line: Current location and arrival time
        self._create_location_line(layout)

    def _create_main_info_line(self, layout: QVBoxLayout) -> None:
        """Create the main train information line."""
        main_layout = QHBoxLayout()

        # Left side: Train icon, time, destination
        left_layout = QHBoxLayout()
        left_layout.setSpacing(1)  # Minimal spacing
        left_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)  # No size constraints

        # Train service icon and time
        time_info = QLabel(
            f"{self.train_data.get_service_icon()} {self.train_data.format_departure_time()}"
        )
        time_font = QFont()
        time_font.setPointSize(28)  # Doubled from 14
        time_font.setBold(True)
        time_info.setFont(time_font)
        left_layout.addWidget(time_info)

        # Arrow and destination (with underground formatting if needed)
        destination_text = self.train_data.destination or "Unknown"
        destination_info = QLabel(f"→ {destination_text}")
        dest_font = QFont()
        dest_font.setPointSize(24)  # Doubled from 12
        destination_info.setFont(dest_font)
        left_layout.addWidget(destination_info)

        left_layout.addStretch()

        # Right side: Platform, status, and details button
        right_layout = QHBoxLayout()
        right_layout.setSpacing(1)  # Minimal spacing

        # Platform info
        platform_text = f"Platform {self.train_data.platform or 'TBA'}"
        platform_info = QLabel(platform_text)
        platform_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        platform_font = QFont()
        platform_font.setPointSize(20)  # Add font size for platform info
        platform_info.setFont(platform_font)
        right_layout.addWidget(platform_info)

        # Details button
        self.details_button = QLabel("🗺️ Route")
        self.details_button.setAlignment(Qt.AlignmentFlag.AlignRight)
        details_font = QFont()
        details_font.setPointSize(20)  # Add font size for route button
        details_font.setBold(True)
        self.details_button.setFont(details_font)
        self._style_details_button()
        right_layout.addWidget(self.details_button)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        layout.addLayout(main_layout)

    def _create_details_line(self, layout: QVBoxLayout) -> None:
        """Create the operator and service details line."""
        details_layout = QHBoxLayout()

        # Left: Operator and service details with underground system override
        details_layout.setSpacing(1)  # Minimal spacing
        operator_text = self.train_data.operator or "Unknown Operator"
        
        operator_info = QLabel(operator_text)
        operator_font = QFont()
        operator_font.setPointSize(20)  # Doubled from 10
        operator_info.setFont(operator_font)
        details_layout.addWidget(operator_info)

        details_layout.addStretch()

        # Right: Status with icon
        status_text = (
            f"{self.train_data.get_status_icon()} {self.train_data.format_delay()}"
        )
        status_info = QLabel(status_text)
        status_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_font = QFont()
        status_font.setPointSize(20)  # Doubled from 10
        status_font.setBold(True)
        status_info.setFont(status_font)

        # Set status color
        status_color = self.train_data.get_status_color(self.current_theme)
        status_info.setStyleSheet(f"color: {status_color};")

        details_layout.addWidget(status_info)
        layout.addLayout(details_layout)

    def _create_calling_points_section(self, layout: QVBoxLayout) -> None:
        """Create the calling points section with station information."""
        calling_points_widget = QWidget()
        calling_points_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        calling_points_main_layout = QVBoxLayout(calling_points_widget)
        calling_points_main_layout.setContentsMargins(0, 0, 0, 0)
        calling_points_main_layout.setSpacing(0)  # No spacing for calling points
        calling_points_main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-justify the layout
        
        # Check if we should show intermediate stations
        show_intermediate = self.preferences.get('show_intermediate_stations', True)
        
        # Get all calling points to show complete journey
        all_calling_points = self.train_data.calling_points
        
        # Remove duplicate stations while preserving order and keeping the most important one
        filtered_calling_points = self._filter_calling_points(all_calling_points)
        
        if not show_intermediate:
            # When intermediate stations are hidden, only show origin, destination, and interchange stations
            filtered_calling_points = self._filter_for_essential_stations_only(filtered_calling_points)
        
        if filtered_calling_points and len(filtered_calling_points) >= 2:
            self._create_calling_points_display(calling_points_main_layout, filtered_calling_points)
        else:
            self._create_direct_service_display(calling_points_main_layout)
        
        layout.addWidget(calling_points_widget)

    def _filter_calling_points(self, calling_points: List) -> List:
        """Filter calling points to remove duplicates while preserving important ones."""
        seen_stations = set()
        filtered_calling_points = []
        
        for calling_point in calling_points:
            station_name = calling_point.station_name.strip() if calling_point.station_name else ""
            if station_name not in seen_stations:
                seen_stations.add(station_name)
                filtered_calling_points.append(calling_point)
            else:
                # If we've seen this station before, check if this one is more important
                for j, existing_cp in enumerate(filtered_calling_points):
                    if existing_cp.station_name == station_name:
                        # Prefer origin/destination over intermediate, or one with platform info
                        if (calling_point.is_origin or calling_point.is_destination or
                            (calling_point.platform and not existing_cp.platform)):
                            filtered_calling_points[j] = calling_point
                        break
        
        return filtered_calling_points

    def _filter_for_essential_stations_only(self, calling_points: List) -> List:
        """Filter calling points to show only origin, destination, and interchange stations."""
        essential_calling_points = []
        
        for calling_point in calling_points:
            # Always include origin and destination
            if calling_point.is_origin or calling_point.is_destination:
                essential_calling_points.append(calling_point)
            # Include interchange stations (where user changes trains)
            elif self._is_actual_user_journey_interchange(calling_point.station_name.strip() if calling_point.station_name else ""):
                essential_calling_points.append(calling_point)
            # Include major stations
            elif self._is_major_station(calling_point.station_name.strip() if calling_point.station_name else ""):
                essential_calling_points.append(calling_point)
        
        return essential_calling_points

    def set_preferences(self, preferences: dict) -> None:
        """
        Update preferences and refresh the display.
        
        Args:
            preferences: Updated preferences dictionary
        """
        self.preferences = preferences or {}
        # Refresh the UI to apply new preferences
        self._refresh_calling_points_display()

    def _refresh_calling_points_display(self) -> None:
        """Refresh the calling points display with current preferences."""
        # Find the calling points widget and recreate it
        layout = self.layout()
        if layout and isinstance(layout, QVBoxLayout):
            # Find and remove the existing calling points widget (it's the 3rd widget)
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # Check if this is the calling points widget by looking for the specific styling
                    if hasattr(widget, 'styleSheet') and 'background-color: transparent' in widget.styleSheet():
                        layout.removeWidget(widget)
                        widget.deleteLater()
                        break
            
            # Recreate the calling points section - type cast to avoid Pylance errors
            if layout is not None:
                self._create_calling_points_section(layout)

    def _create_calling_points_display(self, layout: QVBoxLayout, calling_points: List) -> None:
        """Create the display for calling points."""
        # Underground detection removed - use calling points as-is
        
        # Show "Stops:" prefix on first line
        first_line_layout = QHBoxLayout()
        first_line_layout.setSpacing(0)  # No spacing
        first_line_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-justify the layout
        
        stops_label = QLabel("Stops:")
        stops_font = QFont()
        stops_font.setPointSize(18)  # Doubled from 9
        stops_font.setBold(True)
        stops_label.setFont(stops_font)
        first_line_layout.addWidget(stops_label)
        
        # Limit stations per line to avoid truncation
        max_stations_per_line = 3  # Allow 3 stations per line for better layout
        current_line_layout = first_line_layout
        stations_in_current_line = 0
        
        for i, calling_point in enumerate(calling_points):
            station_name = calling_point.station_name.strip() if calling_point.station_name else ""
            
            # Station name is now properly handled
            
            # Check if we need a new line
            if stations_in_current_line >= max_stations_per_line:
                current_line_layout.addStretch()
                layout.addLayout(current_line_layout)
                
                # Start new line with indentation
                current_line_layout = QHBoxLayout()
                current_line_layout.setSpacing(0)  # No spacing
                current_line_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left-justify the layout
                
                # Add indentation
                indent_label = QLabel(" ")  # 1 space for indentation
                current_line_layout.addWidget(indent_label)
                stations_in_current_line = 0
            
            # Add arrow between stations
            if i > 0:
                self._add_station_arrow(current_line_layout, calling_points, i)
            
            # Create station label
            station_label = self._create_station_label(calling_point)
            current_line_layout.addWidget(station_label)
            stations_in_current_line += 1
        
        # Finish the last line with stretch at the end
        current_line_layout.addStretch(1)
        layout.addLayout(current_line_layout)

    def _add_station_arrow(self, layout: QHBoxLayout, calling_points: List, index: int) -> None:
        """Add arrow between stations with walking connection detection."""
        # Get raw station names
        raw_curr = calling_points[index].station_name if calling_points[index].station_name else ""
        raw_prev = calling_points[index-1].station_name if calling_points[index-1].station_name else ""
        
        # Check if these are HTML-formatted station names
        is_curr_html = "<font" in raw_curr and "</font>" in raw_curr
        is_prev_html = "<font" in raw_prev and "</font>" in raw_prev
        
        # Process station names based on whether they're HTML-formatted
        if is_curr_html:
            station_name = raw_curr  # Keep HTML formatting
        else:
            station_name = raw_curr.strip()
            
        if is_prev_html:
            prev_station = raw_prev  # Keep HTML formatting
        else:
            prev_station = raw_prev.strip()
        
        # Station names and HTML formatting are now properly handled
        
        # Check for walking connections only - underground detection removed
        
        # Check for walking connections in segments
        is_walking_connection = False
        walking_info = ""
        
        if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
            for segment in self.train_data.route_segments:
                # Get raw segment station names
                raw_from = getattr(segment, 'from_station', '')
                raw_to = getattr(segment, 'to_station', '')
                
                # Check if these are HTML-formatted station names
                is_from_html = "<font" in raw_from and "</font>" in raw_from
                is_to_html = "<font" in raw_to and "</font>" in raw_to
                
                # Process segment station names based on whether they're HTML-formatted
                if is_from_html:
                    segment_from = raw_from  # Keep HTML formatting
                else:
                    segment_from = raw_from.strip()
                    
                if is_to_html:
                    segment_to = raw_to  # Keep HTML formatting
                else:
                    segment_to = raw_to.strip()
                
                # Compare station names, considering HTML formatting
                from_matches_prev = segment_from == prev_station
                from_matches_curr = segment_from == station_name
                to_matches_prev = segment_to == prev_station
                to_matches_curr = segment_to == station_name
                
                connects_stations = (from_matches_prev and to_matches_curr) or (from_matches_curr and to_matches_prev)
                
                if connects_stations:
                    line_name = getattr(segment, 'line_name', '')
                    service_pattern = getattr(segment, 'service_pattern', '') if hasattr(segment, 'service_pattern') else ''
                    
                    # Check for Underground black box segments
                    is_underground_segment = self.underground_formatter.is_underground_segment(segment)
                    
                    # Detect walking segments
                    is_walking_segment = (line_name == 'WALKING' or service_pattern == 'WALKING')
                    
                    # Show walking if this is explicitly a walking segment
                    if is_walking_segment:
                        is_walking_connection = True
                        walking_distance = getattr(segment, 'distance_km', None)
                        walking_time = getattr(segment, 'journey_time_minutes', None)
                        
                        if walking_distance and walking_time:
                            walking_info = f"Walk {walking_distance:.1f}km ({walking_time}min)"
                        elif walking_distance:
                            walking_info = f"Walk {walking_distance:.1f}km"
                        else:
                            walking_info = "Walking connection"
                        break
        
        # Create appropriate arrow with crash protection
        if is_walking_connection and walking_info:
            # Use plain text for walking connections to avoid Qt HTML rendering crashes
            # Use consistent spacing on either side of the arrow
            arrow_text = f"  → {walking_info} →  "
            
            # Create the arrow label with fixed-width spaces to ensure consistency
            arrow_label = QLabel(arrow_text)
            
            # Ensure the label doesn't get truncated
            arrow_label.setWordWrap(False)
            arrow_label.setTextFormat(Qt.TextFormat.PlainText)  # Use plain text to avoid HTML interpretation
            
            # Apply red color via stylesheet instead of HTML with explicit padding
            arrow_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: #f44336;
                    border: none;
                    margin: 0px;
                    padding-left: 4px;
                    padding-right: 4px;
                }}
            """)
        else:
            # Check if this is an Underground segment
            is_underground_connection = False
            underground_info = ""
            
            if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
                for segment in self.train_data.route_segments:
                    # Get raw segment station names
                    raw_from = getattr(segment, 'from_station', '')
                    raw_to = getattr(segment, 'to_station', '')
                    
                    # Check if these are HTML-formatted station names
                    is_from_html = "<font" in raw_from and "</font>" in raw_from
                    is_to_html = "<font" in raw_to and "</font>" in raw_to
                    
                    # Process segment station names based on whether they're HTML-formatted
                    if is_from_html:
                        segment_from = raw_from  # Keep HTML formatting
                    else:
                        segment_from = raw_from.strip()
                        
                    if is_to_html:
                        segment_to = raw_to  # Keep HTML formatting
                    else:
                        segment_to = raw_to.strip()
                    
                    # Compare station names, considering HTML formatting
                    from_matches_prev = segment_from == prev_station
                    from_matches_curr = segment_from == station_name
                    to_matches_prev = segment_to == prev_station
                    to_matches_curr = segment_to == station_name
                    
                    connects_stations = (from_matches_prev and to_matches_curr) or (from_matches_curr and to_matches_prev)
                    
                    if connects_stations and self.underground_formatter.is_underground_segment(segment):
                        is_underground_connection = True
                        # Get system-specific information
                        system_info = self.underground_formatter.get_underground_system_info(segment)
                        system_name = system_info.get("short_name", "Underground")
                        time_range = system_info.get("time_range", "10-40min")
                        emoji = system_info.get("emoji", "🚇")
                        underground_info = f"{emoji} {system_name} ({time_range})"
                        break
            
            if is_underground_connection:
                # Always use red for underground connections, but show system-specific info with emoji
                # Use consistent spacing on either side of the arrow
                arrow_text = f"  → {underground_info} →  "
                
                # Create the arrow label with fixed-width spaces to ensure consistency
                arrow_label = QLabel(arrow_text)
                
                # Ensure the label doesn't get truncated
                arrow_label.setWordWrap(False)
                arrow_label.setTextFormat(Qt.TextFormat.PlainText)  # Use plain text to avoid HTML interpretation
                
                # Apply styling with explicit padding
                arrow_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: #DC241F;
                        border: none;
                        margin: 0px;
                        padding-left: 4px;
                        padding-right: 4px;
                        font-weight: bold;
                    }}
                """)
            else:
                # Use consistent spacing on either side of the arrow
                arrow_text = "  →  "  # Added extra spaces on both sides
                
                # Arrow text is now properly handled
                
                # Create the arrow label with fixed-width spaces to ensure consistency
                arrow_label = QLabel(arrow_text)
                
                # Ensure the label doesn't get truncated
                arrow_label.setWordWrap(False)
                arrow_label.setTextFormat(Qt.TextFormat.PlainText)  # Use plain text to avoid HTML interpretation
                
                # Apply consistent styling with explicit padding
                colors = self.get_theme_colors(self.current_theme)
                arrow_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: {colors['primary_accent']};
                        border: none;
                        margin: 0px;
                        padding-left: 4px;
                        padding-right: 4px;
                    }}
                """)
                
                # Set a fixed width for the arrow to ensure consistent spacing
                arrow_label.setFixedWidth(50)
        
        arrow_font = QFont()
        arrow_font.setPointSize(15)  # Reduced font size
        arrow_label.setFont(arrow_font)
        layout.addWidget(arrow_label)

    def _create_station_label(self, calling_point) -> QLabel:
        """Create a styled station label with underground system differentiation."""
        station_label = QLabel()
        
        # Get station name and trim any leading and trailing spaces
        raw_name = calling_point.station_name if calling_point.station_name else ""
        
        # Check if this is an HTML-formatted station name (like underground connections)
        is_html_formatted = "<font" in raw_name and "</font>" in raw_name
        
        # For HTML-formatted names, we need to handle them differently
        if is_html_formatted:
            # Keep the HTML formatting but ensure consistent spacing
            station_name = raw_name
        else:
            # For plain text names, just strip spaces
            station_name = raw_name.strip()
        
        
        # Check if this station belongs to an underground system
        underground_system = None
        
        # Check if this station has wheelchair access
        is_wheelchair_accessible = self._is_wheelchair_accessible(station_name)
        
        # Build the station text with appropriate indicators
        station_text = station_name
        
        # Add underground system indicator if applicable
        if underground_system:
            # Use the loaded underground system indicators from configuration file
            indicator = self.underground_system_indicators.get(underground_system, "🚇")
            station_text += f" {indicator}"
        
        # Add wheelchair accessibility indicator if applicable
        if is_wheelchair_accessible:
            station_text += " ♿"
            
        station_label.setText(station_text)
        # Ensure text doesn't get truncated
        station_label.setWordWrap(False)
        station_label.setTextFormat(Qt.TextFormat.RichText)  # Use RichText for HTML formatting
        station_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Ensure no extra padding or margin
        station_label.setContentsMargins(0, 0, 0, 0)
        station_label.setStyleSheet("padding: 0px; margin: 0px;")
        
        station_font = QFont()
        station_font.setPointSize(18)  # Doubled from 9
        
        # Special formatting for origin and destination
        if calling_point.is_origin or calling_point.is_destination:
            station_font.setBold(True)
        else:
            station_font.setItalic(True)
            
        station_label.setFont(station_font)
        
        # Apply styling based on station type
        self._style_station_label(station_label, calling_point)
        
        return station_label

    def _style_station_label(self, label: QLabel, calling_point) -> None:
        """Apply styling to station label based on its type."""
        # Get raw station name
        raw_name = calling_point.station_name if calling_point.station_name else ""
        
        # Check if this is an HTML-formatted station name
        is_html_formatted = "<font" in raw_name and "</font>" in raw_name
        
        # Process station name based on whether it's HTML-formatted
        if is_html_formatted:
            station_name = raw_name  # Keep HTML formatting
        else:
            station_name = raw_name.strip()
            
        colors = self.get_theme_colors(self.current_theme)
        
        # Check for walking connections
        is_walking = ("<font color='#f44336'" in station_name)
        
        if not is_walking:
            if self._is_actual_user_journey_interchange(station_name):
                # Use orange/yellow ONLY for stations where user actually changes trains
                interchange_color = colors["warning"]
                label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent !important;
                        color: {interchange_color} !important;
                        border: none !important;
                        margin: 0px !important;
                        padding: 0px !important;
                    }}
                """)
            elif calling_point.is_origin or calling_point.is_destination:
                # FORCE light blue for From and To stations in light mode for visibility
                if self.current_theme == "light":
                    label.setStyleSheet(f"""
                        QLabel {{
                            background-color: transparent !important;
                            color: #1976d2 !important;
                            border: none !important;
                            margin: 0px !important;
                            padding: 0px !important;
                        }}
                    """)
                else:
                    # Dark mode: use normal text color
                    label.setStyleSheet(f"""
                        QLabel {{
                            background-color: transparent !important;
                            color: {colors['text_primary']} !important;
                            border: none !important;
                            margin: 0px !important;
                            padding: 0px !important;
                        }}
                    """)
            else:
                # Regular light blue text for normal intermediate stations
                label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent !important;
                        color: {colors['primary_accent']} !important;
                        border: none !important;
                        margin: 0px !important;
                        padding: 0px !important;
                    }}
                """)
        else:
            # For walking connections, preserve HTML formatting
            label.setStyleSheet("""
                QLabel {
                    background-color: transparent !important;
                    border: none !important;
                    margin: 0px !important;
                    padding: 0px !important;
                }
            """)

    def _create_direct_service_display(self, layout: QVBoxLayout) -> None:
        """Create display for direct service."""
        direct_layout = QHBoxLayout()
        direct_label = QLabel("Direct service")
        direct_font = QFont()
        direct_font.setPointSize(18)  # Doubled from 9
        direct_font.setItalic(True)
        direct_label.setFont(direct_font)
        direct_layout.addWidget(direct_label)
        direct_layout.addStretch()
        layout.addLayout(direct_layout)

    def _create_location_line(self, layout: QVBoxLayout) -> None:
        """Create the current location and arrival time line."""
        location_layout = QHBoxLayout()
        location_layout.setSpacing(1)  # Minimal spacing

        # Current location
        if self.train_data.current_location:
            location_text = f"Current: {self.train_data.current_location} 📍"
            location_info = QLabel(location_text)
            location_font = QFont()
            location_font.setPointSize(18)  # Doubled from 9
            location_info.setFont(location_font)
            location_layout.addWidget(location_info)

        location_layout.addStretch()

        # Arrival time
        if self.train_data.estimated_arrival:
            arrival_text = f"Arrives: {self.train_data.format_arrival_time()} 🏁"
            arrival_info = QLabel(arrival_text)
            arrival_info.setAlignment(Qt.AlignmentFlag.AlignRight)
            arrival_font = QFont()
            arrival_font.setPointSize(18)  # Doubled from 9
            arrival_info.setFont(arrival_font)
            location_layout.addWidget(arrival_info)

        layout.addLayout(location_layout)

    def _style_details_button(self) -> None:
        """Style the details button."""
        self.details_button.setStyleSheet("""
            QLabel {
                background-color: rgba(79, 195, 247, 0.2);
                border: 1px solid #1976d2;
                border-radius: 4px;
                padding: 2px 6px;
                margin-left: 8px;
                font-weight: bold;
            }
            QLabel:hover {
                background-color: rgba(79, 195, 247, 0.4);
            }
        """)
        self.details_button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply_theme_styles(self) -> None:
        """Apply theme-specific styling."""
        colors = self.get_theme_colors(self.current_theme)
        status_color = self.train_data.get_status_color(self.current_theme)

        # FORCE light theme styling when in light mode
        if self.current_theme == "light":
            style = f"""
            QFrame {{
                background-color: #ffffff !important;
                border: 1px solid #e0e0e0 !important;
                border-left: 4px solid {status_color} !important;
                border-radius: 8px !important;
                margin: 2px !important;
                padding: 8px !important;
            }}
            
            QFrame:hover {{
                background-color: #f5f5f5 !important;
                border-color: #1976d2 !important;
            }}
            
            QLabel {{
                color: #212121 !important;
                background-color: transparent !important;
                border: none !important;
                margin: 0px !important;
                padding: 0px !important;
                font-size: 15pt !important;
                text-align: left !important;
                max-width: 100000px !important;
                min-width: 0px !important;
            }}
            
            QWidget {{
                background-color: transparent !important;
            }}
            """
        else:
            # Dark theme styling
            style = f"""
            QFrame {{
                background-color: {colors['background_secondary']};
                border: 1px solid {colors['border_primary']};
                border-left: 4px solid {status_color};
                border-radius: 8px;
                margin: 2px;
                padding: 8px;
            }}
            
            QFrame:hover {{
                background-color: {colors['background_hover']};
                border-color: {colors['primary_accent']};
            }}
            
            QLabel {{
                color: {colors['text_primary']};
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
                font-size: 15pt;
                text-align: left;
                max-width: 100000px;
                min-width: 0px;
            }}
            
            QWidget {{
                background-color: transparent;
            }}
            """
        
        self.setStyleSheet(style)

    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only handle clicks on the Route button
            if hasattr(self, 'details_button') and self.details_button.geometry().contains(event.pos()):
                self.route_clicked.emit(self.train_data)
        super().mousePressEvent(event)

    def _is_actual_user_journey_interchange(self, station_name: str) -> bool:
        """
        Two-step logic as requested:
        
        STEP 1: IF user changes lines → Mark orange
        STEP 2: IF user changes lines BUT stays on same physical train → Remove orange (override)
        """
        # Check if this is an HTML-formatted station name
        is_html_formatted = "<font" in station_name and "</font>" in station_name
        
        # Process station name based on whether it's HTML-formatted
        if is_html_formatted:
            # For HTML-formatted names, we need to be careful with replacements
            # This is a simplified approach - a more robust solution would use HTML parsing
            clean_name = station_name.replace(" (Cross Country Line)", "")
        else:
            clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        # Check if we have route segments to analyze
        if not hasattr(self.train_data, 'route_segments') or not self.train_data.route_segments:
            return False
        
        # Debug logging removed - system working correctly
        
        # STEP 1: Check if user changes lines at this station
        line_change_detected = False
        same_physical_train = False
        
        # Look for consecutive segments that connect at this station
        for i in range(len(self.train_data.route_segments) - 1):
            current_segment = self.train_data.route_segments[i]
            next_segment = self.train_data.route_segments[i + 1]
            
            # Check if this station connects two segments
            current_to = getattr(current_segment, 'to_station', '').strip()
            next_from = getattr(next_segment, 'from_station', '').strip()
            
            if current_to == clean_name and next_from == clean_name:
                # This station connects segments - check for line change
                current_line = getattr(current_segment, 'line_name', '')
                next_line = getattr(next_segment, 'line_name', '')
                
                if current_line != next_line:
                    line_change_detected = True
                    
                    # STEP 2: Check if it's the same physical train despite line change
                    current_train_id = getattr(current_segment, 'train_id', None)
                    next_train_id = getattr(next_segment, 'train_id', None)
                    
                    if current_train_id and next_train_id and current_train_id == next_train_id:
                        same_physical_train = True
        
        # Return True only if there's a line change AND it's not the same physical train
        return line_change_detected and not same_physical_train
        
    def _is_major_station(self, station_name: str) -> bool:
        """
        Check if a station is considered a major station that should always be shown.
        
        Args:
            station_name: Name of the station to check
            
        Returns:
            True if the station is a major station, False otherwise
        """
        # Check if this is an HTML-formatted station name
        is_html_formatted = "<font" in station_name and "</font>" in station_name
        
        # Process station name based on whether it's HTML-formatted
        if is_html_formatted:
            # For HTML-formatted names, we need to be careful
            # This is a simplified approach - a more robust solution would use HTML parsing
            processed_name = station_name
        else:
            # Trim any leading and trailing spaces from the station name
            processed_name = station_name.strip() if station_name else ""
        
        # Use the loaded major stations list from configuration file
        return processed_name in self.major_stations
    
    def _get_theme_colors(self, theme: str) -> dict:
        """
        Get color palette for the current theme.
        
        Args:
            theme: Current theme ("dark" or "light")
            
        Returns:
            Dictionary of colors for the theme
        """
        if theme == "light":
            return {
                "background_primary": "#ffffff",
                "background_secondary": "#f5f5f5",
                "background_hover": "#e3f2fd",
                "text_primary": "#212121",
                "text_secondary": "#757575",
                "border_primary": "#e0e0e0",
                "primary_accent": "#1976d2",
                "secondary_accent": "#03a9f4",
                "warning": "#ff9800",
                "error": "#f44336",
                "success": "#4caf50"
            }
        else:
            # Dark theme colors
            return {
                "background_primary": "#121212",
                "background_secondary": "#1e1e1e",
                "background_hover": "#2c2c2c",
                "text_primary": "#ffffff",
                "text_secondary": "#b0b0b0",
                "border_primary": "#333333",
                "primary_accent": "#90caf9",
                "secondary_accent": "#4fc3f7",
                "warning": "#ffb74d",
                "error": "#e57373",
                "success": "#81c784"
            }
    
    def _is_wheelchair_accessible(self, station_name: str) -> bool:
        """
        Check if a station has wheelchair accessibility.
        
        Args:
            station_name: Name of the station to check
            
        Returns:
            True if the station is wheelchair accessible, False otherwise
        """
        # Check if this is an HTML-formatted station name
        is_html_formatted = "<font" in station_name and "</font>" in station_name
        
        # Process station name based on whether it's HTML-formatted
        if is_html_formatted:
            # For HTML-formatted names, we need to be careful
            # This is a simplified approach - a more robust solution would use HTML parsing
            processed_name = station_name
        else:
            # Trim any leading and trailing spaces from the station name
            processed_name = station_name.strip() if station_name else ""
        
        # Log for debugging
        self.logger.debug(f"Checking wheelchair accessibility for station: {processed_name}")
        
        # Check if we have station data in the train manager
        if not self.train_manager or not hasattr(self.train_manager, 'get_station_by_name'):
            self.logger.debug(f"No train manager or get_station_by_name method available")
            return False
        
        # Get station data
        station = self.train_manager.get_station_by_name(processed_name)
        if not station:
            self.logger.debug(f"Station not found: {processed_name}")
            return False
        
        # Check if station has accessibility information
        if not hasattr(station, 'accessibility') or not station.accessibility:
            self.logger.debug(f"No accessibility data for station: {processed_name}")
            return False
        
        # Check if station has wheelchair access
        if hasattr(station, 'is_accessible') and callable(station.is_accessible):
            is_accessible = station.is_accessible()
            self.logger.debug(f"Station {processed_name} wheelchair accessible: {is_accessible}")
            return bool(is_accessible)
        
        # Fallback to checking accessibility dictionary directly
        wheelchair_access = station.accessibility.get('wheelchair', False)
        self.logger.debug(f"Station {processed_name} wheelchair access from dict: {wheelchair_access}")
        return bool(wheelchair_access)
        
    def _make_log_safe(self, text: str) -> str:
        """
        Make text safe for logging by replacing problematic Unicode characters.
        
        Args:
            text: The text to make safe for logging
            
        Returns:
            A version of the text that is safe for logging
        """
        if not text:
            return ""
            
        # Replace common problematic Unicode characters
        replacements = {
            '🚇': '[subway]',
            '→': '->',
            '♿': '[wheelchair]',
            '📍': '[pin]',
            '🏁': '[flag]',
            '🗺️': '[map]'
        }
        
        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)
            
        return result