"""
Train item widget for displaying individual train information.

This module provides a widget for displaying comprehensive train information
including departure time, destination, platform, operator, status, and current location.
"""

import logging
from typing import List, Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ...models.train_data import TrainData
from ...core.services.interchange_detection_service import InterchangeDetectionService
from ...ui.formatters.underground_formatter import UndergroundFormatter
from .train_widgets_base import BaseTrainWidget

logger = logging.getLogger(__name__)


class TrainItemWidget(QFrame):
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
        
        # Initialize theme and logging functionality
        self.current_theme = theme
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.train_data = train_data
        self.train_manager = train_manager
        self.preferences = preferences or {}
        
        # Initialize Underground formatter for black box routing
        self.underground_formatter = UndergroundFormatter()

        try:
            self._setup_ui()
            self._apply_theme_styles()

            # Set frame style but don't make entire widget clickable
            self.setFrameStyle(QFrame.Shape.Box)
        except Exception as e:
            # Create minimal fallback UI
            self._create_fallback_ui()

    def _setup_ui(self) -> None:
        """Setup the train item UI layout."""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(4)

            # Main train info line
            self._create_main_info_line(layout)
            
            # Second line: Operator, service type, duration, status
            self._create_details_line(layout)
            
            # Third line: Calling points (intermediate stations) - with wrapping
            self._create_calling_points_section(layout)
            
            # Fourth line: Current location and arrival time
            self._create_location_line(layout)
        except Exception as e:
            # Create minimal fallback
            self._create_fallback_ui()
    
    def _create_fallback_ui(self) -> None:
        """Create minimal fallback UI when main UI creation fails."""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 8, 12, 8)
            
            # Just show basic train info without Underground formatting
            basic_info = QLabel(f"{self.train_data.format_departure_time()} → {self.train_data.destination}")
            basic_info.setFont(QFont("Arial", 12))
            layout.addWidget(basic_info)
            
            operator_info = QLabel(f"{self.train_data.operator} • {self.train_data.format_delay()}")
            operator_info.setFont(QFont("Arial", 10))
            layout.addWidget(operator_info)
        except Exception as e:
            logger.error(f"Error creating fallback UI: {e}")

    def _create_main_info_line(self, layout: QVBoxLayout) -> None:
        """Create the main train information line."""
        main_layout = QHBoxLayout()

        # Left side: Train icon, time, destination
        left_layout = QHBoxLayout()

        # Train service icon and time
        time_info = QLabel(
            f"{self.train_data.get_service_icon()} {self.train_data.format_departure_time()}"
        )
        time_font = QFont()
        time_font.setPointSize(14)
        time_font.setBold(True)
        time_info.setFont(time_font)
        left_layout.addWidget(time_info)

        # Arrow and destination (with underground formatting if needed)
        destination_text = self._format_destination()
        destination_info = QLabel(destination_text)
        dest_font = QFont()
        dest_font.setPointSize(12)
        destination_info.setFont(dest_font)
        left_layout.addWidget(destination_info)

        left_layout.addStretch()

        # Right side: Platform, status, and details button
        right_layout = QHBoxLayout()

        # Platform info
        platform_text = f"Platform {self.train_data.platform or 'TBA'}"
        platform_info = QLabel(platform_text)
        platform_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(platform_info)

        # Details button
        self.details_button = QLabel("🗺️ Route")
        self.details_button.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._style_details_button()
        right_layout.addWidget(self.details_button)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        layout.addLayout(main_layout)

    def _create_details_line(self, layout: QVBoxLayout) -> None:
        """Create the operator and service details line."""
        details_layout = QHBoxLayout()

        # Left: Operator and service details with underground system override
        operator_text = self._format_operator_with_underground()
        
        operator_info = QLabel(operator_text)
        operator_font = QFont()
        operator_font.setPointSize(10)
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
        status_font.setPointSize(10)
        status_font.setBold(True)
        status_info.setFont(status_font)

        # Set status color
        status_color = self.train_data.get_status_color(self.current_theme)
        status_info.setStyleSheet(f"color: {status_color};")

        details_layout.addWidget(status_info)
        layout.addLayout(details_layout)

    def _create_calling_points_section(self, layout: QVBoxLayout) -> None:
        """Create the calling points section with station information."""
        try:
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
            calling_points_main_layout.setSpacing(2)
            
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
        except Exception as e:
            # Create minimal fallback
            try:
                fallback_widget = QWidget()
                fallback_layout = QVBoxLayout(fallback_widget)
                fallback_label = QLabel("Route information unavailable")
                fallback_label.setFont(QFont("Arial", 9))
                fallback_layout.addWidget(fallback_label)
                layout.addWidget(fallback_widget)
            except Exception as e2:
                logger.error(f"Error creating fallback calling points: {e2}")

    def _filter_calling_points(self, calling_points: List) -> List:
        """Filter calling points to remove duplicates while preserving important ones."""
        seen_stations = set()
        filtered_calling_points = []
        
        for calling_point in calling_points:
            station_name = calling_point.station_name
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
            elif self._is_major_interchange(calling_point.station_name):
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
        try:
            # Underground detection removed - use calling points as-is
            
            # Show "Stops:" prefix on first line
            first_line_layout = QHBoxLayout()
            stops_label = QLabel("Stops:")
            stops_font = QFont()
            stops_font.setPointSize(9)
            stops_font.setBold(True)
            stops_label.setFont(stops_font)
            first_line_layout.addWidget(stops_label)
            
            # Limit stations per line to avoid overcrowding
            max_stations_per_line = 3
            current_line_layout = first_line_layout
            stations_in_current_line = 0
            
            for i, calling_point in enumerate(calling_points):
                try:
                    station_name = calling_point.station_name
                    
                    # Check if we need a new line
                    if stations_in_current_line >= max_stations_per_line:
                        current_line_layout.addStretch()
                        layout.addLayout(current_line_layout)
                        
                        # Start new line with indentation
                        current_line_layout = QHBoxLayout()
                        indent_label = QLabel("    ")  # 4 spaces for indentation
                        current_line_layout.addWidget(indent_label)
                        stations_in_current_line = 0
                    
                    # Add arrow between stations
                    if i > 0:
                        self._add_station_arrow(current_line_layout, calling_points, i)
                    
                    # Create station label
                    station_label = self._create_station_label(calling_point)
                    current_line_layout.addWidget(station_label)
                    stations_in_current_line += 1
                except Exception as e:
                    # Continue with next station
                    continue
            
            # Finish the last line
            current_line_layout.addStretch()
            layout.addLayout(current_line_layout)
        except Exception as e:
            # Create minimal fallback
            try:
                fallback_layout = QHBoxLayout()
                fallback_label = QLabel("Stops: Route display error")
                fallback_layout.addWidget(fallback_label)
                layout.addLayout(fallback_layout)
            except Exception as e2:
                logger.error(f"Error creating fallback calling points display: {e2}")

    def _add_station_arrow(self, layout: QHBoxLayout, calling_points: List, index: int) -> None:
        """Add arrow between stations with walking connection detection."""
        station_name = calling_points[index].station_name
        prev_station = calling_points[index-1].station_name
        
        # Check for walking connections only - underground detection removed
        
        # Check for walking connections in segments
        is_walking_connection = False
        walking_info = ""
        
        if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
            for segment in self.train_data.route_segments:
                segment_from = getattr(segment, 'from_station', '')
                segment_to = getattr(segment, 'to_station', '')
                
                connects_stations = ((segment_from == prev_station and segment_to == station_name) or
                                   (segment_from == station_name and segment_to == prev_station))
                
                if connects_stations:
                    line_name = getattr(segment, 'line_name', '')
                    service_pattern = getattr(segment, 'service_pattern', '') if hasattr(segment, 'service_pattern') else ''
                    
                    # Check for Underground black box segments
                    is_underground_segment = self.underground_formatter.is_underground_segment(segment)
                    
                    # Detect walking segments
                    is_walking_segment = (line_name == 'WALKING' or service_pattern == 'WALKING')
                    
                    # Special case for Farnborough North to Farnborough (main)
                    is_farnborough_connection = (
                        (prev_station == "Farnborough North" and station_name == "Farnborough (main)") or
                        (prev_station == "Farnborough (main)" and station_name == "Farnborough North")
                    )
                    
                    # Show walking if either:
                    # 1. This is explicitly a walking segment, OR
                    # 2. This is the special Farnborough connection AND avoid_walking is not enabled
                    if is_walking_segment or (is_farnborough_connection and not self.preferences.get('avoid_walking', False)):
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
        try:
            if is_walking_connection and walking_info:
                # Use plain text for walking connections to avoid Qt HTML rendering crashes
                arrow_label = QLabel(f"→ {walking_info} →")
                # Apply red color via stylesheet instead of HTML
                arrow_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: #f44336;
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }}
                """)
            else:
                # Check if this is an Underground segment
                is_underground_connection = False
                underground_info = ""
                
                if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
                    for segment in self.train_data.route_segments:
                        segment_from = getattr(segment, 'from_station', '')
                        segment_to = getattr(segment, 'to_station', '')
                        
                        connects_stations = ((segment_from == prev_station and segment_to == station_name) or
                                           (segment_from == station_name and segment_to == prev_station))
                        
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
                    arrow_label = QLabel(f"→ {underground_info} →")
                    arrow_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: transparent;
                            color: #DC241F;
                            border: none;
                            margin: 0px;
                            padding: 0px;
                            font-weight: bold;
                        }}
                    """)
                else:
                    arrow_label = QLabel("→")
                    colors = self.get_theme_colors(self.current_theme)
                    arrow_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: transparent;
                            color: {colors['primary_accent']};
                            border: none;
                            margin: 0px;
                            padding: 0px;
                        }}
                    """)
        except Exception as e:
            # Fallback to simple arrow
            arrow_label = QLabel("→")
        
        arrow_font = QFont()
        arrow_font.setPointSize(9)
        arrow_label.setFont(arrow_font)
        layout.addWidget(arrow_label)

    def _create_station_label(self, calling_point) -> QLabel:
        """Create a styled station label with underground system differentiation."""
        station_label = QLabel()
        
        # Get station name
        station_name = calling_point.station_name
        
        # Check if this station belongs to an underground system
        underground_system = self._get_station_underground_system(station_name)
        
        if underground_system:
            # Add system indicator to underground stations
            system_indicators = {
                "London Underground": "🚇L",
                "Glasgow Subway": "🚇G",
                "Tyne and Wear Metro": "🚇T"
            }
            indicator = system_indicators.get(underground_system, "🚇")
            station_label.setText(f"{station_name} {indicator}")
        else:
            station_label.setText(station_name)
        
        station_font = QFont()
        station_font.setPointSize(9)
        
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
        station_name = calling_point.station_name
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
        direct_font.setPointSize(9)
        direct_font.setItalic(True)
        direct_label.setFont(direct_font)
        direct_layout.addWidget(direct_label)
        direct_layout.addStretch()
        layout.addLayout(direct_layout)

    def _create_location_line(self, layout: QVBoxLayout) -> None:
        """Create the current location and arrival time line."""
        location_layout = QHBoxLayout()

        # Current location
        if self.train_data.current_location:
            location_text = f"Current: {self.train_data.current_location} 📍"
            location_info = QLabel(location_text)
            location_font = QFont()
            location_font.setPointSize(9)
            location_info.setFont(location_font)
            location_layout.addWidget(location_info)

        location_layout.addStretch()

        # Arrival time
        if self.train_data.estimated_arrival:
            arrival_text = f"Arrives: {self.train_data.format_arrival_time()} 🏁"
            arrival_info = QLabel(arrival_text)
            arrival_info.setAlignment(Qt.AlignmentFlag.AlignRight)
            arrival_font = QFont()
            arrival_font.setPointSize(9)
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
            current_to = getattr(current_segment, 'to_station', '')
            next_from = getattr(next_segment, 'from_station', '')
            
            if current_to == clean_name and next_from == clean_name:
                # This station connects segments - check for line change
                current_line = getattr(current_segment, 'line_name', '')
                next_line = getattr(next_segment, 'line_name', '')
                
                # Debug logging removed - system working correctly
                
                # Skip if either line name is empty
                if not current_line or not next_line:
                    continue
                
                # STEP 1: Check if lines are different
                if current_line != next_line:
                    line_change_detected = True
                    
                    # Debug logging removed - system working correctly
                    
                    # STEP 2: Check if it's the same physical train (override)
                    
                    # Check train_service_id first (most reliable)
                    current_train_service_id = getattr(current_segment, 'train_service_id', None)
                    next_train_service_id = getattr(next_segment, 'train_service_id', None)
                    
                    if current_train_service_id is not None and next_train_service_id is not None:
                        if current_train_service_id == next_train_service_id:
                            same_physical_train = True
                            break
                        else:
                            # Different service IDs = different trains
                            break
                    
                    # Enhanced fallback: Check if this is likely the same train service
                    # This handles cases where service IDs might not be properly set
                    enhanced_result = self._is_likely_same_train_service_enhanced(current_line, next_line)
                    
                    if enhanced_result:
                        same_physical_train = True
                        break
                    
                    # Check service patterns as fallback
                    current_service = getattr(current_segment, 'service_pattern', None)
                    next_service = getattr(next_segment, 'service_pattern', None)
                    
                    if current_service is not None and next_service is not None:
                        if current_service == next_service:
                            same_physical_train = True
                            break
                    
                    # Check train IDs as fallback
                    current_train_id = getattr(current_segment, 'train_id', None)
                    next_train_id = getattr(next_segment, 'train_id', None)
                    
                    if current_train_id is not None and next_train_id is not None:
                        if current_train_id == next_train_id:
                            same_physical_train = True
                            break
                    
                    # If we get here, it's a real train change
                    break
        
        # Apply the two-step logic
        result = False
        if line_change_detected:
            if same_physical_train:
                result = False
            else:
                result = True
        else:
            result = False
        
        # Debug logging removed - system working correctly
        
        return result

    def _is_line_change_station(self, station_name: str) -> bool:
        """Check if this station is where the user actually changes from one train line to another."""
        clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        # Check if we have route segments to analyze
        if not hasattr(self.train_data, 'route_segments') or not self.train_data.route_segments:
            return False
        
        # Look for actual line changes at this station
        for i, segment in enumerate(self.train_data.route_segments):
            # Check if this segment ends at our station
            if hasattr(segment, 'to_station') and segment.to_station == clean_name:
                # Check if there's a next segment with a different line
                if i < len(self.train_data.route_segments) - 1:
                    next_segment = self.train_data.route_segments[i + 1]
                    
                    # Get line names
                    current_line = getattr(segment, 'line_name', '')
                    next_line = getattr(next_segment, 'line_name', '')
                    
                    # Skip walking segments
                    if current_line == 'WALKING' or next_line == 'WALKING':
                        continue
                    
                    # Skip if either line name is empty
                    if not current_line or not next_line:
                        continue
                    
                    # Normalize line names for comparison (handle variations)
                    current_normalized = self._normalize_line_name(current_line)
                    next_normalized = self._normalize_line_name(next_line)
                    
                    # If normalized lines are different, this is a line change
                    if current_normalized != next_normalized:
                        self.logger.debug(f"Line change detected at {clean_name}: {current_line} ({current_normalized}) → {next_line} ({next_normalized})")
                        return True
                    else:
                        self.logger.debug(f"Same line at {clean_name}: {current_line} ({current_normalized}) = {next_line} ({next_normalized})")
        
        return False
    
    def _normalize_line_name(self, line_name: str) -> str:
        """Normalize line names to handle variations of the same line."""
        if not line_name:
            return ""
        
        # Convert to lowercase for comparison
        normalized = line_name.lower().strip()
        
        # Handle South Western Railway variations
        if any(term in normalized for term in ['south western', 'swr']):
            return "south_western"
        
        # Handle Reading to Basingstoke variations
        if 'reading' in normalized and 'basingstoke' in normalized:
            return "reading_basingstoke"
        
        # Handle Great Western variations
        if any(term in normalized for term in ['great western', 'gwr']):
            return "great_western"
        
        # Handle Cross Country variations
        if 'cross country' in normalized:
            return "cross_country"
        
        # Return the original normalized name for other lines
        return normalized

    def _is_likely_same_train_service(self, current_line: str, next_line: str, operator: str) -> bool:
        """
        Check if two different line names likely represent the same physical train service.
        
        Args:
            current_line: Current line name
            next_line: Next line name
            operator: Train operator
            
        Returns:
            True if likely the same physical train service
        """
        # Great Western Railway services often have different line names but same train
        if operator in ["Great Western Railway", "GWR"]:
            gwr_lines = [
                "Great Western Main Line", "Great Western Railway", "Reading to Basingstoke Line",
                "Cotswold Line", "Thames Valley Line", "Relief Line"
            ]
            
            if current_line in gwr_lines and next_line in gwr_lines:
                return True
            else:
                # Check for partial matches or variations
                current_lower = current_line.lower()
                next_lower = next_line.lower()
                
                gwr_keywords = ["great western", "gwr", "reading", "cotswold", "thames valley"]
                current_has_gwr = any(keyword in current_lower for keyword in gwr_keywords)
                next_has_gwr = any(keyword in next_lower for keyword in gwr_keywords)
                
                if current_has_gwr and next_has_gwr:
                    return True
        
        # Cross Country services
        if operator in ["Cross Country", "CrossCountry"]:
            cross_country_lines = [
                "Cross Country Line", "CrossCountry", "West Coast Main Line",
                "East Coast Main Line", "Midland Main Line"
            ]
            if current_line in cross_country_lines and next_line in cross_country_lines:
                return True
        
        # South Western Railway services
        if operator in ["South Western Railway", "SWR"]:
            swr_lines = [
                "South Western Main Line", "Portsmouth Direct Line", "Reading to Basingstoke Line"
            ]
            if current_line in swr_lines and next_line in swr_lines:
                return True
        
        # Virgin Trains / Avanti West Coast
        if operator in ["Virgin Trains", "Avanti West Coast"]:
            west_coast_lines = [
                "West Coast Main Line", "Virgin Trains", "Avanti West Coast"
            ]
            if current_line in west_coast_lines and next_line in west_coast_lines:
                return True
        
        return False

    def _is_likely_same_train_service_enhanced(self, current_line: str, next_line: str) -> bool:
        """
        Enhanced check if two different line names likely represent the same physical train service.
        This version doesn't require operator information and uses comprehensive line name matching.
        
        Args:
            current_line: Current line name
            next_line: Next line name
            
        Returns:
            True if likely the same physical train service
        """
        # Normalize line names for comparison
        current_normalized = current_line.lower().strip()
        next_normalized = next_line.lower().strip()
        
        # Great Western Railway services - comprehensive matching
        gwr_keywords = ["great western", "gwr", "reading", "cotswold", "thames valley", "relief"]
        current_has_gwr = any(keyword in current_normalized for keyword in gwr_keywords)
        next_has_gwr = any(keyword in next_normalized for keyword in gwr_keywords)
        
        if current_has_gwr and next_has_gwr:
            return True
        
        # Cross Country services
        cross_country_keywords = ["cross country", "crosscountry"]
        current_has_cc = any(keyword in current_normalized for keyword in cross_country_keywords)
        next_has_cc = any(keyword in next_normalized for keyword in cross_country_keywords)
        
        if current_has_cc and next_has_cc:
            return True
        
        # South Western Railway services
        swr_keywords = ["south western", "swr", "portsmouth direct"]
        current_has_swr = any(keyword in current_normalized for keyword in swr_keywords)
        next_has_swr = any(keyword in next_normalized for keyword in swr_keywords)
        
        if current_has_swr and next_has_swr:
            return True
        
        # West Coast services (Virgin/Avanti)
        west_coast_keywords = ["west coast", "virgin", "avanti"]
        current_has_wc = any(keyword in current_normalized for keyword in west_coast_keywords)
        next_has_wc = any(keyword in next_normalized for keyword in west_coast_keywords)
        
        if current_has_wc and next_has_wc:
            return True
        
        # East Coast services
        east_coast_keywords = ["east coast", "lner"]
        current_has_ec = any(keyword in current_normalized for keyword in east_coast_keywords)
        next_has_ec = any(keyword in next_normalized for keyword in east_coast_keywords)
        
        if current_has_ec and next_has_ec:
            return True
        
        return False

    def _is_major_interchange(self, station_name: str) -> bool:
        """Check if a station is where the passenger actually changes trains/lines during this journey."""
        # This method is kept for backward compatibility but now delegates to the actual user journey interchange detection
        return self._is_actual_user_journey_interchange(station_name)

    def get_theme_colors(self, theme: str) -> dict[str, str]:
        """
        Get theme-specific color palette.
        
        Args:
            theme: Theme name ("dark" or "light")
            
        Returns:
            Dictionary of color names to hex values
        """
        if theme == "dark":
            return {
                "background_primary": "#1a1a1a",
                "background_secondary": "#2d2d2d",
                "background_hover": "#404040",
                "text_primary": "#ffffff",
                "text_secondary": "#b0b0b0",
                "primary_accent": "#1976d2",
                "border_primary": "#404040",
                "border_secondary": "#555555",
                "success": "#4caf50",
                "warning": "#ff9800",
                "error": "#f44336",
            }
        else:  # light theme
            return {
                "background_primary": "#ffffff",
                "background_secondary": "#f5f5f5",
                "background_hover": "#e0e0e0",
                "text_primary": "#000000",
                "text_secondary": "#757575",
                "primary_accent": "#1976d2",
                "border_primary": "#cccccc",
                "border_secondary": "#e0e0e0",
                "success": "#4caf50",
                "warning": "#ff9800",
                "error": "#f44336",
            }

    def update_theme(self, theme: str) -> None:
        """
        Update widget theme and refresh styling.
        
        Args:
            theme: New theme name ("dark" or "light")
        """
        if theme != self.current_theme:
            self.current_theme = theme
            self._apply_theme_styles()
    
    def _format_destination(self) -> str:
        """Format destination with Underground indicator if route involves Underground."""
        try:
            destination = self.train_data.destination
            
            # Check if route involves Underground segments
            has_underground = False
            underground_systems = set()
            if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
                for segment in self.train_data.route_segments:
                    if self.underground_formatter.is_underground_segment(segment):
                        has_underground = True
                        # Get system-specific information
                        system_info = self.underground_formatter.get_underground_system_info(segment)
                        system_name = system_info.get("short_name", "Underground")
                        underground_systems.add(system_name)
            
            if has_underground:
                if len(underground_systems) == 1:
                    # Single underground system
                    system_name = list(underground_systems)[0]
                    return f"→ {destination} <font color='#DC241F'>🚇 Use {system_name}</font>"
                elif len(underground_systems) > 1:
                    # Multi-system route - don't show "Use [System]" as it's misleading
                    return f"→ {destination} <font color='#DC241F'>🚇 Multi-system route</font>"
                else:
                    return f"→ {destination} <font color='#DC241F'>🚇 Use Underground</font>"
            else:
                return f"→ {destination}"
        except Exception as e:
            # Fallback to basic destination
            return f"→ {getattr(self.train_data, 'destination', 'Unknown')}"
    
    def _should_simplify_route_display(self, calling_points: List) -> bool:
        """Check if we should simplify the route display."""
        # Always return False since we use _skip_underground_stations instead
        return False
    
    def _get_simplified_calling_points(self, calling_points: List) -> List:
        """Get simplified calling points for routes involving underground."""
        # This method is replaced by _skip_underground_stations
        return calling_points
    
    def _format_operator_with_underground(self) -> str:
        """Format operator text with underground system override if applicable."""
        try:
            # Check if route involves Underground segments
            underground_systems = []
            
            if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
                for segment in self.train_data.route_segments:
                    if self.underground_formatter.is_underground_segment(segment):
                        # Get system-specific information
                        system_info = self.underground_formatter.get_underground_system_info(segment)
                        system_name = system_info.get("short_name", "Underground")
                        time_range = system_info.get("time_range", "10-40min")
                        underground_systems.append((system_name, time_range))
            
            if underground_systems:
                if len(underground_systems) == 1:
                    # Single underground system
                    system_name, time_range = underground_systems[0]
                    operator_text = f"{system_name} • Fast • {time_range}"
                else:
                    # Multi-system route - show combined info
                    unique_systems = list(set(sys[0] for sys in underground_systems))
                    if len(unique_systems) == 1:
                        # Same system, different segments
                        system_name = unique_systems[0]
                        time_range = underground_systems[0][1]  # Use first time range
                        operator_text = f"{system_name} • Fast • {time_range}"
                    else:
                        # Different systems
                        systems_text = " + ".join(unique_systems)
                        operator_text = f"{systems_text} • Multi-system • 3-5hr"
            else:
                # Use original operator and service details
                operator_text = (
                    f"{self.train_data.operator} • {self.train_data.service_type.value.title()}"
                )
                if self.train_data.journey_duration:
                    operator_text += f" • {self.train_data.format_journey_duration()}"
            
            return operator_text
        except Exception as e:
            # Fallback to basic operator info
            return f"{getattr(self.train_data, 'operator', 'Unknown')} • {getattr(self.train_data.service_type, 'value', 'Unknown').title()}"
    
    def _get_station_underground_system(self, station_name: str) -> Optional[str]:
        """Determine which underground system a station belongs to."""
        try:
            # Load the consolidated underground stations data
            import json
            import os
            
            data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'uk_underground_stations.json')
            
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    stations_data = json.load(f)
                
                # Check each system for the station
                for system_name, stations in stations_data.items():
                    for station in stations:
                        if station.get('name') == station_name:
                            return system_name
            
            return None
        except Exception as e:
            # If we can't determine the system, return None
            return None