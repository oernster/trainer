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
                 train_manager=None, parent: Optional[QWidget] = None):
        """
        Initialize train item widget.

        Args:
            train_data: Train information to display
            theme: Current theme ("dark" or "light")
            train_manager: Train manager instance for accessing route data
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize theme and logging functionality
        self.current_theme = theme
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.train_data = train_data
        self.train_manager = train_manager

        self._setup_ui()
        self._apply_theme_styles()

        # Set frame style but don't make entire widget clickable
        self.setFrameStyle(QFrame.Shape.Box)

    def _setup_ui(self) -> None:
        """Setup the train item UI layout."""
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

        # Arrow and destination
        destination_info = QLabel(f"→ {self.train_data.destination}")
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

        # Left: Operator and service details
        operator_text = (
            f"{self.train_data.operator} • {self.train_data.service_type.value.title()}"
        )
        if self.train_data.journey_duration:
            operator_text += f" • {self.train_data.format_journey_duration()}"

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
        
        # Get all calling points to show complete journey
        all_calling_points = self.train_data.calling_points
        
        # Remove duplicate stations while preserving order and keeping the most important one
        filtered_calling_points = self._filter_calling_points(all_calling_points)
        
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

    def _create_calling_points_display(self, layout: QVBoxLayout, calling_points: List) -> None:
        """Create the display for calling points."""
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
        
        # Finish the last line
        current_line_layout.addStretch()
        layout.addLayout(current_line_layout)

    def _add_station_arrow(self, layout: QHBoxLayout, calling_points: List, index: int) -> None:
        """Add arrow between stations with walking connection detection."""
        station_name = calling_points[index].station_name
        prev_station = calling_points[index-1].station_name
        
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
                    service_pattern = getattr(segment, 'service_pattern', '')
                    
                    is_walking_segment = (line_name == 'WALKING' or service_pattern == 'WALKING')
                    
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
        
        # Create appropriate arrow
        if is_walking_connection and walking_info:
            arrow_label = QLabel(f"→ <font color='#f44336'>{walking_info}</font> →")
            arrow_label.setTextFormat(Qt.TextFormat.RichText)
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
        
        arrow_font = QFont()
        arrow_font.setPointSize(9)
        arrow_label.setFont(arrow_font)
        layout.addWidget(arrow_label)

    def _create_station_label(self, calling_point) -> QLabel:
        """Create a styled station label."""
        station_label = QLabel()
        station_label.setText(calling_point.station_name)
        station_label.setTextFormat(Qt.TextFormat.RichText)
        
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
            if self._is_major_interchange(station_name):
                # Use orange/yellow for interchange stations
                interchange_color = colors["warning"]
                label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: {interchange_color};
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }}
                """)
            elif calling_point.is_origin or calling_point.is_destination:
                # Origin and destination in normal text color
                label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: {colors['text_primary']};
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }}
                """)
            else:
                # Regular light blue text for normal intermediate stations
                label.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: {colors['primary_accent']};
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }}
                """)
        else:
            # For walking connections, preserve HTML formatting
            label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
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

    def _is_major_interchange(self, station_name: str) -> bool:
        """Check if a station is where the passenger actually changes trains/lines during this journey."""
        clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        # Check if we have route_segments data for line changes
        if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
            # Use the InterchangeDetectionService for intelligent detection
            interchange_service = InterchangeDetectionService()
            interchanges = interchange_service.detect_user_journey_interchanges(self.train_data.route_segments)
            
            # Check if this station is marked as a user journey change
            for interchange in interchanges:
                if interchange.station_name == clean_name and interchange.is_user_journey_change:
                    return True
            
            return False
        else:
            # If no route data is available, return False (conservative approach)
            return False

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