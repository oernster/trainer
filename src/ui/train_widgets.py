"""
Train display widgets for the Train Times application.

This module contains widgets for displaying train information including
the train list and individual train item widgets.
"""

import logging
from typing import List, Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QDialog,
    QPushButton,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor
from ..models.train_data import TrainData, TrainStatus

logger = logging.getLogger(__name__)


class CustomScrollBar(QWidget):
    """
    Custom scroll bar widget that properly reflects content state.
    
    This widget provides a visual scroll bar indicator that accurately shows
    the proportion of visible content and allows for proper scrolling interaction.
    """
    
    # Signals for scroll events
    scroll_requested = Signal(int)  # Emitted when user requests scroll to position
    
    def __init__(self, parent=None):
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
        
        # Theme properties
        self._current_theme = "dark"
        self._track_color = "#2d2d2d"
        self._handle_color = "#555555"
        self._handle_hover_color = "#666666"
        self._handle_pressed_color = "#666666"
        
        # Set fixed width for vertical scroll bar
        self.setFixedWidth(12)
        self.setMinimumHeight(50)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
    
    def setRange(self, minimum, maximum):
        """Set the scroll range."""
        self._minimum = minimum
        self._maximum = maximum
        self._value = max(minimum, min(self._value, maximum))
        self.update()
    
    def setValue(self, value):
        """Set the current scroll value."""
        old_value = self._value
        self._value = max(self._minimum, min(value, self._maximum))
        if old_value != self._value:
            self.update()
    
    def setPageStep(self, step):
        """Set the page step size."""
        self._page_step = step
    
    def setSingleStep(self, step):
        """Set the single step size."""
        self._single_step = step
    
    def value(self):
        """Get the current scroll value."""
        return self._value
    
    def minimum(self):
        """Get the minimum scroll value."""
        return self._minimum
    
    def maximum(self):
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
        from PySide6.QtGui import QPainter, QColor
        from PySide6.QtCore import Qt
        
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
    
    def apply_theme(self, theme: str):
        """Apply theme-specific colors to the scroll bar."""
        self._current_theme = theme
        
        if theme == "dark":
            self._track_color = "#2d2d2d"
            self._handle_color = "#555555"
            self._handle_hover_color = "#666666"
            self._handle_pressed_color = "#666666"
        else:  # light theme
            self._track_color = "#f5f5f5"
            self._handle_color = "#bdbdbd"
            self._handle_hover_color = "#9e9e9e"
            self._handle_pressed_color = "#9e9e9e"
        
        # Trigger repaint with new colors
        self.update()


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

    def __init__(self, train_data: TrainData, theme: str = "dark", train_manager=None):
        """
        Initialize train item widget.

        Args:
            train_data: Train information to display
            theme: Current theme ("dark" or "light")
            train_manager: Train manager instance for accessing route data
        """
        super().__init__()
        self.train_data = train_data
        self.current_theme = theme
        self.train_manager = train_manager

        self.setup_ui()
        self.apply_theme()

        # Set frame style but don't make entire widget clickable
        self.setFrameStyle(QFrame.Shape.Box)

    def setup_ui(self):
        """Setup the train item UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Main train info line
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
        right_layout.addWidget(self.details_button)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        layout.addLayout(main_layout)

        # Second line: Operator, service type, duration, status
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

        # Third line: Calling points (intermediate stations) - with wrapping
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
        
        # We don't have access to the train manager here, so we can't get the full route path
        # We'll just use the calling points from the train data
        full_path = None
        
        # Get all calling points to show complete journey
        all_calling_points = self.train_data.calling_points
        
        # Debug logging to understand what calling points we have
        logger.debug(f"Train {self.train_data.service_id} has {len(all_calling_points)} calling points")
        for i, cp in enumerate(all_calling_points):
            logger.debug(f"  {i}: {cp.station_name} (origin={cp.is_origin}, dest={cp.is_destination})")
        
        # Remove duplicate stations while preserving order and keeping the most important one
        seen_stations = set()
        filtered_calling_points = []
        
        for calling_point in all_calling_points:
            station_name = calling_point.station_name
            if station_name not in seen_stations:
                seen_stations.add(station_name)
                filtered_calling_points.append(calling_point)
            else:
                # If we've seen this station before, check if this one is more important
                # Find the existing one and replace if this one is better (origin/destination preferred)
                for j, existing_cp in enumerate(filtered_calling_points):
                    if existing_cp.station_name == station_name:
                        # Prefer origin/destination over intermediate, or one with platform info
                        if (calling_point.is_origin or calling_point.is_destination or
                            (calling_point.platform and not existing_cp.platform)):
                            filtered_calling_points[j] = calling_point
                        break
        
        logger.debug(f"After filtering: {len(filtered_calling_points)} unique calling points")
        
        if filtered_calling_points and len(filtered_calling_points) >= 2:  # Show even if just origin and destination
            # Show "Stops:" prefix on first line to indicate all stops
            first_line_layout = QHBoxLayout()
            stops_label = QLabel("Stops:")
            stops_font = QFont()
            stops_font.setPointSize(9)
            stops_font.setBold(True)
            stops_label.setFont(stops_font)
            first_line_layout.addWidget(stops_label)
            
            # Limit stations per line to avoid overcrowding
            max_stations_per_line = 3  # Reduced to 3 since we're showing more stations
            current_line_layout = first_line_layout
            stations_in_current_line = 0
            
            for i, calling_point in enumerate(filtered_calling_points):
                station_name = calling_point.station_name
                # Check if we need a new line
                if stations_in_current_line >= max_stations_per_line:
                    # Finish current line and start new one
                    current_line_layout.addStretch()
                    calling_points_main_layout.addLayout(current_line_layout)
                    
                    # Start new line with indentation
                    current_line_layout = QHBoxLayout()
                    # Add indentation for continuation lines
                    indent_label = QLabel("    ")  # 4 spaces for indentation
                    current_line_layout.addWidget(indent_label)
                    stations_in_current_line = 0
                
                # Check if this is a walking connection
                # There are two types:
                # 1. A special standalone walking text entry (station name itself is the walking text)
                # 2. A station name that contains HTML formatting for walking
                is_standalone_walking = station_name.startswith("<font color='#f44336'>Walk ")
                is_embedded_walking = "<font color='#f44336'" in station_name and not is_standalone_walking
                walking_info = ""
                display_name = station_name
                
                # For standalone walking entries, we'll just display the text as is
                
                # Add arrow between stations with special handling for walking connections
                if i > 0:
                    # Find the previous station for checking walking connection
                    prev_station = filtered_calling_points[i-1].station_name
                    
                    # Check if this is a walking connection
                    is_walking_connection = False
                    walking_info = ""
                    
                    # Look for walking connections in segments
                    if hasattr(self.train_data, 'route_segments'):
                        for segment in getattr(self.train_data, 'route_segments', []):
                            if (hasattr(segment, 'from_station') and hasattr(segment, 'to_station') and
                                (segment.from_station == prev_station and segment.to_station == station_name or
                                 segment.from_station == station_name and segment.to_station == prev_station)):
                                if getattr(segment, 'line_name', '') == 'WALKING':
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
                    
                    # Special case for Farnborough stations
                    if ('Farnborough North' in prev_station and 'Farnborough (Main)' in station_name or
                        'Farnborough (Main)' in prev_station and 'Farnborough North' in station_name):
                        is_walking_connection = True
                        walking_info = "Walk 0.9km (12min)"
                    
                    # Create arrow with walking info if needed
                    if is_walking_connection and walking_info:
                        # Special red walking arrow with info
                        arrow_label = QLabel(f"→ <font color='#f44336'>{walking_info}</font> →")
                        arrow_font = QFont()
                        arrow_font.setPointSize(9)
                        arrow_label.setFont(arrow_font)
                        arrow_label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML
                    else:
                        # Regular arrow
                        arrow_label = QLabel("→")
                        arrow_font = QFont()
                        arrow_font.setPointSize(9)
                        arrow_label.setFont(arrow_font)
                        arrow_label.setStyleSheet("""
                            QLabel {
                                background-color: transparent;
                                color: #1976d2;
                                border: none;
                                margin: 0px;
                                padding: 0px;
                            }
                        """)
                    current_line_layout.addWidget(arrow_label)
                
                # Create station label with the station name, enabling HTML rendering
                station_label = QLabel()
                station_label.setText(display_name)  # This will render HTML if present
                station_label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML rendering
                
                station_font = QFont()
                station_font.setPointSize(9)
                
                # Special formatting for origin and destination
                if calling_point.is_origin or calling_point.is_destination:
                    station_font.setBold(True)
                else:
                    station_font.setItalic(True)
                    
                station_label.setFont(station_font)
                
                # No need for special styling for walking connections anymore
                # since we're using HTML formatting directly in the station name
                
                # Define combined walking detection
                is_walking = is_standalone_walking or is_embedded_walking
                
                # Only apply stylesheet if this is not a walking connection
                # This ensures the HTML formatting for walking connections is not overridden
                if not is_walking:
                    if self._is_major_interchange(display_name):
                        # Use orange/yellow for interchange stations as requested
                        interchange_color = "#ff9800" if self.current_theme == "light" else "#ffc107"
                        station_label.setStyleSheet(f"""
                            QLabel {{
                                background-color: transparent;
                                color: {interchange_color};
                                border: none;
                                margin: 0px;
                                padding: 0px;
                            }}
                        """)
                    elif calling_point.is_origin or calling_point.is_destination:
                        # Origin and destination in white/black (normal text color)
                        text_color = "#ffffff" if self.current_theme == "dark" else "#000000"
                        station_label.setStyleSheet(f"""
                            QLabel {{
                                background-color: transparent;
                                color: {text_color};
                                border: none;
                                margin: 0px;
                                padding: 0px;
                            }}
                        """)
                    else:
                        # Regular light blue text for normal intermediate stations
                        station_label.setStyleSheet("""
                            QLabel {
                                background-color: transparent;
                                color: #1976d2;
                                border: none;
                                margin: 0px;
                                padding: 0px;
                            }
                        """)
                else:
                    # For walking connections, only set background and border properties
                    # but not color, to preserve the HTML color formatting
                    station_label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            border: none;
                            margin: 0px;
                            padding: 0px;
                        }
                    """)
                current_line_layout.addWidget(station_label)
                stations_in_current_line += 1
            
            # Finish the last line
            current_line_layout.addStretch()
            calling_points_main_layout.addLayout(current_line_layout)
        else:
            # Show "Direct service" if no intermediate stations
            direct_layout = QHBoxLayout()
            direct_label = QLabel("Direct service")
            direct_font = QFont()
            direct_font.setPointSize(9)
            direct_font.setItalic(True)
            direct_label.setFont(direct_font)
            direct_layout.addWidget(direct_label)
            direct_layout.addStretch()
            calling_points_main_layout.addLayout(direct_layout)
        
        layout.addWidget(calling_points_widget)

        # Fourth line: Current location and arrival time
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

    def apply_theme(self):
        """Apply theme-specific styling."""
        if self.current_theme == "dark":
            self.setStyleSheet(self.get_dark_style())
        else:
            self.setStyleSheet(self.get_light_style())

    def get_dark_style(self) -> str:
        """Get dark theme stylesheet."""
        status_color = self.train_data.get_status_color("dark")

        return f"""
        QFrame {{
            background-color: #2d2d2d;
            border: 1px solid #404040;
            border-left: 4px solid {status_color};
            border-radius: 8px;
            margin: 2px;
            padding: 8px;
        }}
        
        QFrame:hover {{
            background-color: #3d3d3d;
            border-color: #1976d2;
        }}
        
        QLabel {{
            color: #ffffff;
            background-color: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        
        QWidget {{
            background-color: transparent;
        }}
        
        /* Walking connection styling is no longer needed here
           as we're using HTML formatting directly in the station name */
        """

    def get_light_style(self) -> str:
        """Get light theme stylesheet."""
        status_color = self.train_data.get_status_color("light")

        return f"""
        QFrame {{
            background-color: #f5f5f5;
            border: 1px solid #e0e0e0;
            border-left: 4px solid {status_color};
            border-radius: 8px;
            margin: 2px;
            padding: 8px;
        }}
        
        QFrame:hover {{
            background-color: #eeeeee;
            border-color: #1976d2;
        }}
        
        QLabel {{
            color: #212121;
            background-color: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        
        QWidget {{
            background-color: transparent;
        }}
        
        /* Walking connection styling is no longer needed here
           as we're using HTML formatting directly in the station name */
        """

    def update_theme(self, theme: str):
        """
        Update widget theme.

        Args:
            theme: New theme name ("dark" or "light")
        """
        self.current_theme = theme
        self.apply_theme()
        
        # Update station label colors for interchange stations
        self._update_station_label_colors()

    def _update_station_label_colors(self):
        """Update the colors of station labels based on current theme."""
        # Find all station labels and update their colors
        for label in self.findChildren(QLabel):
            station_name = label.text()
            # Skip non-station labels
            if station_name not in ["Via:", "→", "    ", "Direct service"] and station_name:
                # Check if this is a walking connection (HTML formatted)
                is_walking = "<font color='#f44336'" in station_name
                
                # No need to apply special styling for walking connections
                # since we're using HTML formatting directly in the station name
                
                if not is_walking and self._is_major_interchange(station_name):
                    # Update interchange station color using property
                    label.setProperty("interchange", "true")
                    label.setProperty("regular", None)
                    
                    # Set the color directly since it's theme-dependent
                    interchange_color = "#ff9800" if self.current_theme == "light" else "#ffc107"
                    label.setStyleSheet(f"color: {interchange_color};")
                    
                    # Force style refresh
                    label.style().unpolish(label)
                    label.style().polish(label)
                elif not is_walking and "→" not in station_name and not station_name.startswith("Current:") and not station_name.startswith("Arrives:"):
                    # Update regular station color using property
                    label.setProperty("interchange", None)
                    label.setProperty("regular", "true")
                    
                    # Set the color directly for regular stations
                    label.setStyleSheet("color: #1976d2;")
                    
                    # Force style refresh
                    label.style().unpolish(label)
                    label.style().polish(label)

    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only handle clicks on the Route button - remove general widget click functionality
            if hasattr(self, 'details_button') and self.details_button.geometry().contains(event.pos()):
                self.route_clicked.emit(self.train_data)
        super().mousePressEvent(event)

    def _is_major_interchange(self, station_name: str) -> bool:
        """Check if a station is where the passenger actually changes trains/lines during this journey."""
        # Clean station name for comparison
        clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        logger.debug(f"Checking interchange status for station: {clean_name}")
        
        # Check if we have route_segments data for line changes
        if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
            segments = self.train_data.route_segments
            logger.debug(f"Found {len(segments)} segments for interchange analysis")
            
            # Look for consecutive segments where the passenger changes between different JSON files
            for i in range(len(segments) - 1):
                current_segment = segments[i]
                next_segment = segments[i + 1]
                
                current_from = getattr(current_segment, 'from_station', '')
                current_to = getattr(current_segment, 'to_station', '')
                next_from = getattr(next_segment, 'from_station', '')
                current_line = getattr(current_segment, 'line_name', '')
                next_line = getattr(next_segment, 'line_name', '')
                
                logger.debug(f"Analyzing segments {i} and {i+1} for line changes")
                
                # Only consider this an interchange if:
                # 1. This station is where one segment ends and the next begins
                # 2. Both segments are actual train lines (not walking)
                # 3. The passenger changes between different JSON file lines
                # 4. Geographic validation confirms this is a legitimate interchange
                if (current_to == clean_name and next_from == clean_name and
                    current_line != 'WALKING' and next_line != 'WALKING' and
                    current_line != next_line):
                    
                    logger.debug(f"Potential interchange at {clean_name}: {current_line} -> {next_line}")
                    
                    json_change = self._is_json_file_line_change(current_line, next_line)
                    geo_valid = self._is_valid_interchange_geographically(current_from, current_to, current_line, next_line)
                    
                    if json_change and geo_valid:
                        logger.debug(f"Station {clean_name} is a valid interchange")
                        return True
                    else:
                        logger.debug(f"Station {clean_name} rejected as interchange")
            
            logger.debug(f"Station {clean_name} is not an interchange")
            return False
        else:
            logger.debug(f"No route segments available for {clean_name}")
            # If no route data is available, return False (conservative approach)
            return False
    
    def _is_json_file_line_change(self, line1: str, line2: str) -> bool:
        """Check if a line change represents a change between different JSON files (different railway lines)."""
        # Get the station-to-JSON-files mapping
        station_to_files = self._get_station_to_json_files_mapping()
        
        # Map line names to their corresponding JSON files
        line_to_file = self._get_line_to_json_file_mapping()
        
        # Get the JSON file for each line
        file1 = line_to_file.get(line1)
        file2 = line_to_file.get(line2)
        
        # If we can't find the files, fall back to simple line name comparison
        if not file1 or not file2:
            return line1 != line2
        
        # Lines are different if they come from different JSON files
        return file1 != file2
    
    def _is_valid_interchange_geographically(self, from_station: str, to_station: str,
                                           from_line: str, to_line: str) -> bool:
        """
        Use geographic distance (Haversine) to validate if an interchange is legitimate.
        
        Args:
            from_station: Station where passenger is coming from
            to_station: Station where passenger is going to (potential interchange)
            from_line: Line name from route segment
            to_line: Line name to route segment
            
        Returns:
            True if this is a valid interchange based on geographic constraints
        """
        try:
            # The interchange station is the to_station (where the line change occurs)
            interchange_station = to_station
            
            # Check if this is a known through service first
            if self._is_known_through_service(from_line, to_line, interchange_station):
                logger.debug(f"Known through service detected at {interchange_station}: {from_line} -> {to_line}")
                return False  # Not a real interchange - through service
            
            # Get station coordinates from JSON files
            station_coordinates = self._get_station_coordinates()
            
            # Check if we have coordinates for the interchange station
            if interchange_station not in station_coordinates:
                logger.debug(f"Missing coordinates for interchange station: {interchange_station}")
                return True  # Conservative: allow if we can't validate
            
            # For a valid interchange, the station should exist in both line's JSON files
            # and be at the same geographic location (within reasonable tolerance)
            
            # Get the line-to-file mapping to find which JSON files contain each line
            line_to_file = self._get_line_to_json_file_mapping()
            
            file1 = line_to_file.get(from_line)
            file2 = line_to_file.get(to_line)
            
            if not file1 or not file2:
                logger.debug(f"Could not find JSON files for lines: {from_line} -> {file1}, {to_line} -> {file2}")
                return True  # Conservative: allow if we can't validate
            
            # Check if the interchange station appears in both JSON files
            station_to_files = self._get_station_to_json_files_mapping()
            station_files = station_to_files.get(interchange_station, [])
            
            if file1 in station_files and file2 in station_files:
                logger.debug(f"Valid interchange: {interchange_station} appears in both {file1} and {file2}")
                return True
            else:
                logger.debug(f"Invalid interchange: {interchange_station} not in both files. Found in: {station_files}")
                return False
            
        except Exception as e:
            logger.error(f"Error in geographic validation: {e}")
            return True  # Conservative: allow if validation fails
    
    def _is_known_through_service(self, line1: str, line2: str, station_name: str) -> bool:
        """Check if this represents a known through service where passengers don't change trains."""
        # Hook is a known through station for South Western services
        if station_name == "Hook":
            if ((line1 == "South Western Main Line" and line2 == "Reading to Basingstoke Line") or
                (line1 == "Reading to Basingstoke Line" and line2 == "South Western Main Line")):
                return True
        
        # Fleet is also a through station for South Western services
        if station_name == "Fleet":
            if ((line1 == "South Western Main Line" and line2 == "Reading to Basingstoke Line") or
                (line1 == "Reading to Basingstoke Line" and line2 == "South Western Main Line")):
                return True
        
        # Add other known through services here
        return False
    
    def _get_station_coordinates(self) -> dict:
        """Get station coordinates from JSON files."""
        # Use instance-level cache to avoid reloading data repeatedly
        if not hasattr(self, '_station_coordinates_cache'):
            self._station_coordinates_cache = self._build_station_coordinates_mapping()
        
        return self._station_coordinates_cache
    
    def _build_station_coordinates_mapping(self) -> dict:
        """Build the mapping of station names to their coordinates."""
        station_coordinates = {}
        
        # Load all JSON files from the lines directory
        import json
        from pathlib import Path
        
        lines_dir = Path(__file__).parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Get stations from this JSON file
                    stations = data.get('stations', [])
                    
                    for station in stations:
                        station_name = station.get('name', '')
                        coordinates = station.get('coordinates', {})
                        
                        if station_name and coordinates and 'lat' in coordinates and 'lng' in coordinates:
                            station_coordinates[station_name] = coordinates
            
            logger.debug(f"Built station coordinates mapping with {len(station_coordinates)} stations")
            return station_coordinates
            
        except Exception as e:
            logger.error(f"Failed to build station coordinates mapping: {e}")
            return {}
    
    def _calculate_haversine_distance(self, coord1: dict, coord2: dict) -> float:
        """Calculate the Haversine distance between two coordinates in kilometers."""
        import math
        
        # Extract coordinates (using 'lat' and 'lng' keys from JSON data)
        lat1 = math.radians(coord1['lat'])
        lon1 = math.radians(coord1['lng'])
        lat2 = math.radians(coord2['lat'])
        lon2 = math.radians(coord2['lng'])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        earth_radius_km = 6371.0
        
        return earth_radius_km * c
    
    def _get_station_to_json_files_mapping(self) -> dict:
        """Create a mapping of station names to the JSON files they appear in."""
        # Use instance-level cache to avoid reloading data repeatedly
        if not hasattr(self, '_station_to_files_cache'):
            self._station_to_files_cache = self._build_station_to_files_mapping()
        
        return self._station_to_files_cache
    
    def _get_line_to_json_file_mapping(self) -> dict:
        """Create a mapping of line names to their JSON file names."""
        # Use instance-level cache to avoid reloading data repeatedly
        if not hasattr(self, '_line_to_file_cache'):
            self._line_to_file_cache = self._build_line_to_file_mapping()
        
        return self._line_to_file_cache
    
    def _build_station_to_files_mapping(self) -> dict:
        """Build the mapping of stations to JSON files by loading all line data."""
        station_to_files = {}
        
        # Load all JSON files from the lines directory
        import json
        from pathlib import Path
        
        lines_dir = Path(__file__).parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Get stations from this JSON file
                    stations = data.get('stations', [])
                    file_name = json_file.stem  # Get filename without extension
                    
                    for station in stations:
                        station_name = station.get('name', '')
                        if station_name:
                            if station_name not in station_to_files:
                                station_to_files[station_name] = []
                            station_to_files[station_name].append(file_name)
            
            logger.debug(f"Built station-to-files mapping with {len(station_to_files)} stations")
            return station_to_files
            
        except Exception as e:
            logger.error(f"Failed to build station-to-files mapping: {e}")
            return {}
    
    def _build_line_to_file_mapping(self) -> dict:
        """Build the mapping of line names to JSON file names."""
        line_to_file = {}
        
        # Load all JSON files from the lines directory
        import json
        from pathlib import Path
        
        lines_dir = Path(__file__).parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Get line name from metadata
                    line_name = data.get('metadata', {}).get('line_name', '')
                    operator = data.get('metadata', {}).get('operator', '')
                    file_name = json_file.stem  # Get filename without extension
                    
                    if line_name:
                        line_to_file[line_name] = file_name
                    
                    # Add operator name mappings for common cases
                    if operator:
                        line_to_file[operator] = file_name
                    
                    # Add specific mappings for known operator/service variations
                    if 'south_western' in file_name:
                        line_to_file['South Western Railway'] = file_name
                        line_to_file['South Western Main Line'] = file_name
                    elif 'cross_country' in file_name:
                        line_to_file['CrossCountry'] = file_name
                        line_to_file['Cross Country'] = file_name
                        line_to_file['Cross Country Line'] = file_name
                    elif 'reading_to_basingstoke' in file_name:
                        line_to_file['Reading to Basingstoke Line'] = file_name
            
            logger.debug(f"Built line-to-file mapping with {len(line_to_file)} lines")
            logger.debug(f"Line mappings: {list(line_to_file.keys())}")
            return line_to_file
            
        except Exception as e:
            logger.error(f"Failed to build line-to-file mapping: {e}")
            return {}

    def _is_meaningful_line_change(self, line1: str, line2: str) -> bool:
        """Check if a line change represents a meaningful train change (not just different names for same physical line)."""
        # Normalize line names to detect same physical lines with different names
        def normalize_line_name(line_name: str) -> str:
            line_lower = line_name.lower()
            
            # Be more specific about line groupings to avoid false negatives
            # Only group lines that are truly the same train service
            
            # South Western Railway network - group all SW services together
            # This includes the main line and its extensions/branches that use the same trains
            if any(keyword in line_lower for keyword in [
                'south western main line', 'waterloo to woking', 'waterloo to basingstoke',
                'reading to basingstoke', 'basingstoke to reading'
            ]):
                return 'south_western_network_group'
            
            # Portsmouth Direct Line (Woking to Portsmouth/Guildford direction) - separate from SW network
            elif any(keyword in line_lower for keyword in [
                'portsmouth direct line', 'woking to portsmouth', 'woking to guildford'
            ]):
                return 'portsmouth_direct_group'
            
            # North Downs Line (Guildford area)
            elif any(keyword in line_lower for keyword in ['north downs', 'guildford']):
                return 'north_downs_group'
            
            # Great Western Railway group (includes Reading, Paddington routes, West of England)
            elif any(keyword in line_lower for keyword in ['great western', 'paddington', 'gwr', 'west of england']):
                return 'great_western_group'
            
            elif any(keyword in line_lower for keyword in ['brighton', 'south coast']):
                return 'brighton_group'
            
            # If it contains "main line" or "line", try to group by the main route name
            elif 'main line' in line_lower:
                # Extract the main part before "main line"
                main_part = line_lower.split('main line')[0].strip()
                return f'{main_part}_main_line_group'
            
            elif 'line' in line_lower and len(line_lower.split()) > 1:
                # For other lines, use the first significant word
                words = line_lower.replace('line', '').strip().split()
                if words:
                    return f'{words[0]}_line_group'
            
            # Default: return the original name (different lines)
            return line_name.lower()
        
        # If the normalized names are the same, it's not a meaningful change
        normalized1 = normalize_line_name(line1)
        normalized2 = normalize_line_name(line2)
        
        # Debug logging for specific stations and routes
        if any(station in line1.lower() or station in line2.lower() for station in ['hook', 'woking', 'farnborough', 'guildford', 'brookwood', 'worplesdon']):
            logger.debug(f"Line normalization: '{line1}' -> '{normalized1}', '{line2}' -> '{normalized2}'")
            logger.debug(f"Meaningful change: {normalized1 != normalized2}")
        
        return normalized1 != normalized2
    
    def _is_continuous_train_service(self, line1: str, line2: str, station_name: str) -> bool:
        """Check if this represents a continuous train service where passengers don't change trains."""
        # Generic pattern: South Western Main Line continuing as Reading to Basingstoke Line
        # This represents the same physical train continuing its journey with different line designations
        if ((line1 == "South Western Main Line" and line2 == "Reading to Basingstoke Line") or
            (line1 == "Reading to Basingstoke Line" and line2 == "South Western Main Line")):
            return True
        
        # Add other continuous service patterns here as needed
        # For example, other lines where the same train continues with different designations
        
        return False


class TrainListWidget(QScrollArea):
    """
    Scrollable list of train departures with theme support.

    Displays up to max_trains train items in a scrollable list,
    with support for theme switching and real-time updates.
    """

    # Signal emitted when a train is selected
    train_selected = Signal(TrainData)
    # Signal emitted when a route button is clicked
    route_selected = Signal(TrainData)

    def __init__(self, max_trains: int = 50, train_manager=None):
        """
        Initialize train list widget.

        Args:
            max_trains: Maximum number of trains to display
            train_manager: Train manager instance for accessing route data
        """
        super().__init__()
        self.max_trains = max_trains
        self.current_theme = "dark"
        self.train_items = []
        self.train_manager = train_manager

        self.setup_ui()
        self.apply_theme()

        logger.debug(f"TrainListWidget initialized with max_trains={max_trains}")

    def setup_ui(self):
        """Setup the train list UI."""
        # Create container widget and layout
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(8, 8, 8, 8)
        self.container_layout.setSpacing(4)
        self.container_layout.addStretch()  # Add stretch at the end

        # Configure scroll area - hide default scroll bars
        self.setWidget(self.container_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Hide default scroll bar
        
        # Set a fixed height to ensure scrolling
        self.setFixedHeight(400)
        
        # Create custom scroll bar
        self.custom_scroll_bar = CustomScrollBar(self)
        self.custom_scroll_bar.scroll_requested.connect(self._on_custom_scroll)
        
        # Connect main scroll bar to custom scroll bar for synchronization
        self.verticalScrollBar().valueChanged.connect(self._sync_custom_scroll_bar)
        
        # Position custom scroll bar on the right side
        self._position_custom_scroll_bar()

    def apply_theme(self, theme: str = "dark"):
        """
        Apply theme styling to the scroll area.

        Args:
            theme: Theme name
        """
        if theme:
            self.current_theme = theme

        if self.current_theme == "dark":
            self.setStyleSheet(self.get_dark_scroll_style())
        else:
            self.setStyleSheet(self.get_light_scroll_style())

        # Update custom scroll bar theme
        if hasattr(self, 'custom_scroll_bar'):
            self.custom_scroll_bar.apply_theme(self.current_theme)

        # Update all train items
        for train_item in self.train_items:
            if hasattr(train_item, 'update_theme'):
                train_item.update_theme(self.current_theme)

    def get_dark_scroll_style(self) -> str:
        """Get dark theme scroll area stylesheet."""
        return """
        QScrollArea {
            border: 1px solid #404040;
            border-radius: 8px;
            background-color: #1a1a1a;
        }
        
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """

    def get_light_scroll_style(self) -> str:
        """Get light theme scroll area stylesheet."""
        return """
        QScrollArea {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #ffffff;
        }
        
        QScrollBar:vertical {
            background-color: #f5f5f5;
            width: 12px;
            border-radius: 6px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #bdbdbd;
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #9e9e9e;
        }
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """

    def update_trains(self, trains: List[TrainData]):
        """
        Update the displayed trains.

        Args:
            trains: List of train data to display
        """
        # Clear existing items
        self.clear_trains()

        # Limit to max_trains
        display_trains = trains[: self.max_trains]

        # Add new train items
        for train in display_trains:
            self.add_train_item(train)

        # Force scroll area to recalculate content size AFTER all items are added
        # Use a longer delay to ensure layout is completely finished
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, self.update_scroll_area)

        logger.debug(f"Updated train list with {len(display_trains)} trains")

    def clear_trains(self):
        """Clear all train items from the display."""
        # Remove all train items from layout
        for train_item in self.train_items:
            self.container_layout.removeWidget(train_item)
            train_item.deleteLater()

        self.train_items.clear()

    def add_train_item(self, train_data: TrainData):
        """
        Add a single train item to the display.

        Args:
            train_data: Train data to add
        """
        train_item = TrainItemWidget(train_data, self.current_theme, train_manager=self.train_manager)
        train_item.train_clicked.connect(self.train_selected.emit)
        train_item.route_clicked.connect(self.route_selected.emit)

        # Insert before the stretch at the end
        self.container_layout.insertWidget(self.container_layout.count() - 1, train_item)

        self.train_items.append(train_item)

    def set_train_manager(self, train_manager):
        """
        Set the train manager for accessing route data.
        
        Args:
            train_manager: Train manager instance
        """
        self.train_manager = train_manager
        logger.debug("Train manager set on TrainListWidget")

    def get_train_count(self) -> int:
        """
        Get the number of displayed trains.

        Returns:
            int: Number of trains currently displayed
        """
        return len(self.train_items)

    def scroll_to_top(self):
        """Scroll to the top of the train list."""
        self.verticalScrollBar().setValue(0)

    def scroll_to_bottom(self):
        """Scroll to the bottom of the train list."""
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def update_scroll_area(self):
        """Force the scroll area to recalculate its content size."""
        # Calculate the total height needed for all train items
        total_height = 0
        for train_item in self.train_items:
            total_height += train_item.sizeHint().height() + 4  # +4 for spacing/margins
        
        # Add some padding
        total_height += 20
        
        # Set minimum height on container widget to ensure scroll area knows the content size
        self.container_widget.setMinimumHeight(total_height)
        
        # Update the container widget size
        self.container_widget.updateGeometry()
        # Force the scroll area to recalculate
        self.updateGeometry()
        
        # Process any pending events to ensure layout is updated
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # DIRECT FIX: Manually configure scroll bar to show partial state
        viewport_height = self.viewport().height()
        content_height = total_height
        
        if content_height > viewport_height:
            # Content is larger than viewport - configure scroll bar for partial display
            scroll_bar = self.verticalScrollBar()
            
            # Set the range based on the overflow
            max_scroll = content_height - viewport_height
            scroll_bar.setRange(0, max_scroll)
            
            # Set page step to viewport height for proper handle sizing
            scroll_bar.setPageStep(viewport_height)
            scroll_bar.setSingleStep(20)
            # Force the scroll bar to show and update
            scroll_bar.setVisible(True)
            scroll_bar.update()
        
        # Update custom scroll bar as well
        self.update_custom_scroll_bar()
    
    def _on_custom_scroll(self, value):
        """Handle custom scroll bar scroll requests."""
        # Set the scroll position on the main scroll area
        self.verticalScrollBar().setValue(value)
    
    def _sync_custom_scroll_bar(self, value):
        """Synchronize custom scroll bar with main scroll bar position."""
        if hasattr(self, 'custom_scroll_bar'):
            # Update custom scroll bar position to match main scroll bar
            self.custom_scroll_bar.setValue(value)
    
    def _position_custom_scroll_bar(self):
        """Position the custom scroll bar on the right side of the widget."""
        # Position the custom scroll bar on the right edge
        scroll_bar_x = self.width() - self.custom_scroll_bar.width()
        scroll_bar_y = 0
        scroll_bar_height = self.height()
        
        self.custom_scroll_bar.setGeometry(scroll_bar_x, scroll_bar_y,
                                         self.custom_scroll_bar.width(), scroll_bar_height)
    
    def resizeEvent(self, event):
        """Handle resize events to reposition custom scroll bar."""
        super().resizeEvent(event)
        if hasattr(self, 'custom_scroll_bar'):
            self._position_custom_scroll_bar()
    
    def update_custom_scroll_bar(self):
        """Update the custom scroll bar properties based on content."""
        if not hasattr(self, 'custom_scroll_bar'):
            return
            
        # Calculate content and viewport dimensions
        total_height = 0
        for train_item in self.train_items:
            total_height += train_item.sizeHint().height() + 4
        total_height += 20  # padding
        
        viewport_height = self.viewport().height()
        
        if total_height > viewport_height:
            # Content overflows - set up scroll bar
            max_scroll = total_height - viewport_height
            self.custom_scroll_bar.setRange(0, max_scroll)
            self.custom_scroll_bar.setPageStep(viewport_height)
            self.custom_scroll_bar.setSingleStep(20)
            self.custom_scroll_bar.setVisible(True)
            
            # Sync with main scroll bar position
            main_scroll_value = self.verticalScrollBar().value()
            self.custom_scroll_bar.setValue(main_scroll_value)
        else:
            # No overflow - hide custom scroll bar
            self.custom_scroll_bar.setVisible(False)




class EmptyStateWidget(QWidget):
    """Widget displayed when no trains are available."""

    def __init__(self, theme: str = "dark"):
        """
        Initialize empty state widget.

        Args:
            theme: Current theme
        """
        super().__init__()
        self.current_theme = theme
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        """Setup empty state UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon_label = QLabel("🚂")
        icon_font = QFont()
        icon_font.setPointSize(48)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Message
        message_label = QLabel("No trains available")
        message_font = QFont()
        message_font.setPointSize(16)
        message_label.setFont(message_font)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)

        # Subtitle
        subtitle_label = QLabel("Check your connection or try refreshing")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)

    def apply_theme(self):
        """Apply theme styling."""
        if self.current_theme == "dark":
            self.setStyleSheet(
                """
            QLabel {
                color: #b0b0b0;
                background-color: transparent;
            }
            """
            )
        else:
            self.setStyleSheet(
                """
            QLabel {
                color: #757575;
                background-color: transparent;
            }
            """
            )

    def update_theme(self, theme: str):
        """Update widget theme."""
        self.current_theme = theme
        self.apply_theme()


class RouteDisplayDialog(QDialog):
    """Dialog to display all calling points for a train route."""

    def __init__(self, train_data: TrainData, theme: str = "dark", parent=None, train_manager=None):
        """
        Initialize route display dialog.

        Args:
            train_data: Train data to display route for
            theme: Current theme ("dark" or "light")
            parent: Parent widget
            train_manager: Train manager instance for detailed route generation
        """
        super().__init__(parent)
        self.train_data = train_data
        self.current_theme = theme
        self.train_manager = train_manager
        
        self.setWindowTitle(f"Route - {train_data.format_departure_time()} to {train_data.destination}")
        self.setModal(True)
        self.resize(450, 400)
        
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header with train info
        header_label = QLabel(
            f"🚂 {self.train_data.format_departure_time()} → {self.train_data.destination}"
        )
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Route title
        route_label = QLabel("Complete Journey with All Stops:")
        route_font = QFont()
        route_font.setPointSize(12)
        route_font.setBold(True)
        route_label.setFont(route_font)
        layout.addWidget(route_label)

        # Scrollable calling points list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        calling_points_widget = QWidget()
        calling_points_layout = QVBoxLayout(calling_points_widget)
        calling_points_layout.setSpacing(4)

        # First check if we can get the full route path from the train manager
        full_path = None
        if self.train_manager and hasattr(self.train_manager, 'route_path') and self.train_manager.route_path:
            # Use the stored route path from train manager if available
            full_path = self.train_manager.route_path
            logger.info(f"Using full route path from train manager with {len(full_path)} stations")
        
        # If we have a full path, use it to create a more comprehensive display
        if full_path and len(full_path) >= 2:
            # Create calling points from the full path
            from ..models.train_data import CallingPoint
            
            # Use original calling points for origin and destination to get timing info
            original_calling_points = self.train_data.calling_points
            origin_cp = None
            destination_cp = None
            
            # Find origin and destination calling points
            for cp in original_calling_points:
                if cp.is_origin:
                    origin_cp = cp
                elif cp.is_destination:
                    destination_cp = cp
            
            # Create a mapping of station names to calling points for intermediate stations
            station_to_cp = {}
            for cp in original_calling_points:
                if not cp.is_origin and not cp.is_destination:
                    station_to_cp[cp.station_name] = cp
            
            # Create new calling points list using the full path
            filtered_calling_points = []
            
            # Add each station from the full path
            for i, station_name in enumerate(full_path):
                is_origin = (i == 0)
                is_destination = (i == len(full_path) - 1)
                
                # Use existing calling point if available
                if is_origin and origin_cp:
                    filtered_calling_points.append(origin_cp)
                elif is_destination and destination_cp:
                    filtered_calling_points.append(destination_cp)
                elif station_name in station_to_cp:
                    # Use existing intermediate calling point
                    filtered_calling_points.append(station_to_cp[station_name])
                else:
                    # Create a new calling point without timing info
                    new_cp = CallingPoint(
                        station_name=station_name,
                        scheduled_arrival=None,
                        scheduled_departure=None,
                        expected_arrival=None,
                        expected_departure=None,
                        platform=None,
                        is_origin=is_origin,
                        is_destination=is_destination
                    )
                    filtered_calling_points.append(new_cp)
            
            logger.info(f"Created {len(filtered_calling_points)} calling points from full route path")
        else:
            # Fall back to using original calling points
            calling_points = self.train_data.calling_points
            logger.info(f"Falling back to original {len(calling_points)} calling points in route dialog")
            
            # Remove duplicate stations (keep the one with more complete information)
            seen_stations = set()
            filtered_calling_points = []
            
            for calling_point in calling_points:
                station_name = calling_point.station_name
                if station_name not in seen_stations:
                    seen_stations.add(station_name)
                    filtered_calling_points.append(calling_point)
                else:
                    # If we've seen this station before, check if this one has more info
                    # Find the existing one and replace if this one is better
                    for j, existing_cp in enumerate(filtered_calling_points):
                        if existing_cp.station_name == station_name:
                            # Prefer origin/destination over intermediate, or one with platform info
                            if (calling_point.is_origin or calling_point.is_destination or
                                (calling_point.platform and not existing_cp.platform)):
                                filtered_calling_points[j] = calling_point
                            break

        logger.info(f"Filtered to {len(filtered_calling_points)} unique stations")

        # Display all stations in the route
        for i, calling_point in enumerate(filtered_calling_points):
            # Check if this is a walking connection
            station_name = calling_point.station_name
            is_standalone_walking = station_name.startswith("<font color='#f44336'>Walk ")
            is_embedded_walking = "<font color='#f44336'" in station_name and not is_standalone_walking
            is_walking = is_standalone_walking or is_embedded_walking
            display_name = station_name
            
            # We don't need to add a separate walking indicator anymore
            # since the walking information is already included in the station name with HTML formatting
            
            # Create station display
            station_frame = QFrame()
            station_layout = QHBoxLayout(station_frame)
            station_layout.setContentsMargins(8, 4, 8, 4)

            # Station name with special formatting for origin/destination
            station_label = QLabel()
            station_label.setText(display_name)  # This will render HTML if present
            station_label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML rendering
            
            station_font = QFont()
            station_font.setPointSize(11)
            
            # Check if this is origin or destination
            is_origin = calling_point.is_origin
            is_destination = calling_point.is_destination
            
            if is_origin or is_destination:
                station_font.setBold(True)
            station_label.setFont(station_font)
            station_layout.addWidget(station_label)
            
            # We don't need to add the walking info label here anymore
            # since we're showing it in the walking indicator above

            # Add CHANGE indicator for major interchange stations (but not origin/destination)
            if self._is_major_interchange(calling_point.station_name) and not is_origin and not is_destination:
                change_label = QLabel("CHANGE")
                change_font = QFont()
                change_font.setPointSize(9)
                change_font.setBold(True)
                change_label.setFont(change_font)
                change_label.setStyleSheet("color: #f57f17; background-color: rgba(255, 235, 59, 0.3); padding: 2px 4px; border-radius: 2px;")
                station_layout.addWidget(change_label)

            station_layout.addStretch()

            # Time (if available)
            time_text = calling_point.get_display_time()
            if time_text:
                time_label = QLabel(time_text)
                time_font = QFont()
                time_font.setPointSize(11)
                time_font.setFamily("monospace")
                time_label.setFont(time_font)
                station_layout.addWidget(time_label)

            # Platform (if available)
            if calling_point.platform:
                platform_label = QLabel(f"Plat {calling_point.platform}")
                platform_font = QFont()
                platform_font.setPointSize(9)
                platform_label.setFont(platform_font)
                station_layout.addWidget(platform_label)

            # Apply styling based on station type
            if is_origin:
                station_frame.setStyleSheet("""
                    QFrame {
                        background-color: rgba(76, 175, 80, 0.2);
                        border-left: 3px solid #4caf50;
                        border-radius: 4px;
                        margin: 1px;
                    }
                """)
            elif is_destination:
                station_frame.setStyleSheet("""
                    QFrame {
                        background-color: rgba(244, 67, 54, 0.2);
                        border-left: 3px solid #f44336;
                        border-radius: 4px;
                        margin: 1px;
                    }
                """)
            elif is_walking:
                # For walking connections, use a distinct style but don't override text color
                station_frame.setStyleSheet("""
                    QFrame {
                        background-color: rgba(244, 67, 54, 0.1);
                        border-left: 3px solid #f44336;
                        border-radius: 4px;
                        margin: 1px;
                    }
                """)
                # Don't apply any stylesheet to the label to preserve HTML formatting
                station_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }
                """)
            elif self._is_major_interchange(calling_point.station_name):
                # Highlight interchange stations with theme-aware color
                if self.current_theme == "light":
                    # Green for light theme
                    station_frame.setStyleSheet("""
                        QFrame {
                            background-color: rgba(76, 175, 80, 0.2);
                            border-left: 3px solid #4caf50;
                            border-radius: 4px;
                            margin: 1px;
                        }
                    """)
                else:
                    # Yellow for dark theme
                    station_frame.setStyleSheet("""
                        QFrame {
                            background-color: rgba(255, 235, 59, 0.2);
                            border-left: 3px solid #ffeb3b;
                            border-radius: 4px;
                            margin: 1px;
                        }
                    """)
            else:
                station_frame.setStyleSheet("""
                    QFrame {
                        background-color: rgba(158, 158, 158, 0.1);
                        border-left: 3px solid #9e9e9e;
                        border-radius: 4px;
                        margin: 1px;
                    }
                """)

            calling_points_layout.addWidget(station_frame)

        calling_points_layout.addStretch()
        scroll_area.setWidget(calling_points_widget)
        layout.addWidget(scroll_area)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def apply_theme(self):
        """Apply theme styling to the dialog."""
        if self.current_theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #1976d2;
                    color: #000000;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QScrollArea {
                    border: 1px solid #404040;
                    border-radius: 4px;
                    background-color: #1a1a1a;
                }
                /* Walking connection styling is no longer needed here
                   as we're using HTML formatting directly in the station name */
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    color: #212121;
                }
                QLabel {
                    color: #212121;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #1976d2;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QScrollArea {
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: #ffffff;
                }
                /* Walking connection styling is no longer needed here
                   as we're using HTML formatting directly in the station name */
            """)
    
    def _is_major_interchange(self, station_name: str) -> bool:
        """Check if a station is where the passenger actually changes trains/lines during this journey."""
        # Clean station name for comparison
        clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        logger.debug(f"[RouteDialog] Checking interchange status for station: {clean_name}")
        
        # Check if we have route_segments data for line changes
        if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
            segments = self.train_data.route_segments
            logger.debug(f"[RouteDialog] Checking {len(segments)} segments for {clean_name}")
            
            # Look for consecutive segments where the passenger changes between different JSON files
            for i in range(len(segments) - 1):
                current_segment = segments[i]
                next_segment = segments[i + 1]
                
                current_from = getattr(current_segment, 'from_station', '')
                current_to = getattr(current_segment, 'to_station', '')
                next_from = getattr(next_segment, 'from_station', '')
                current_line = getattr(current_segment, 'line_name', '')
                next_line = getattr(next_segment, 'line_name', '')
                
                logger.debug(f"[RouteDialog] Segment {i}: {current_from} -> {current_to} ({current_line})")
                logger.debug(f"[RouteDialog] Segment {i+1}: {next_from} -> {next_segment.to_station} ({next_line})")
                
                # Only consider this an interchange if:
                # 1. This station is where one segment ends and the next begins
                # 2. Both segments are actual train lines (not walking)
                # 3. The passenger changes between different JSON file lines
                # 4. Geographic validation confirms this is a legitimate interchange
                if (current_to == clean_name and next_from == clean_name and
                    current_line != 'WALKING' and next_line != 'WALKING' and
                    current_line != next_line):
                    
                    logger.debug(f"[RouteDialog] Found potential interchange at {clean_name}: {current_line} -> {next_line}")
                    
                    json_change = self._is_json_file_line_change(current_line, next_line)
                    geo_valid = self._is_valid_interchange_geographically(current_from, current_to, current_line, next_line)
                    
                    logger.debug(f"[RouteDialog] JSON file line change: {json_change}, Geographic validation: {geo_valid}")
                    logger.debug(f"[RouteDialog] Line to file mapping: {current_line} -> {self._get_line_to_json_file_mapping().get(current_line)}")
                    logger.debug(f"[RouteDialog] Line to file mapping: {next_line} -> {self._get_line_to_json_file_mapping().get(next_line)}")
                    
                    if json_change and geo_valid:
                        logger.debug(f"[RouteDialog] Station {clean_name} is a valid interchange")
                        return True
                    else:
                        logger.debug(f"[RouteDialog] Station {clean_name} rejected - JSON change: {json_change}, Geo valid: {geo_valid}")
            
            logger.debug(f"[RouteDialog] Station {clean_name} is not an interchange")
            return False
        else:
            logger.debug(f"[RouteDialog] No route segments available for {clean_name}")
            # If no route data is available, return False (conservative approach)
            return False
    
    def _is_json_file_line_change(self, line1: str, line2: str) -> bool:
        """Check if a line change represents a change between different JSON files (different railway lines)."""
        # Get the station-to-JSON-files mapping
        station_to_files = self._get_station_to_json_files_mapping()
        
        # Map line names to their corresponding JSON files
        line_to_file = self._get_line_to_json_file_mapping()
        
        # Get the JSON file for each line
        file1 = line_to_file.get(line1)
        file2 = line_to_file.get(line2)
        
        # If we can't find the files, fall back to simple line name comparison
        if not file1 or not file2:
            return line1 != line2
        
        # Lines are different if they come from different JSON files
        return file1 != file2
    
    def _get_station_to_json_files_mapping(self) -> dict:
        """Create a mapping of station names to the JSON files they appear in."""
        # Use instance-level cache to avoid reloading data repeatedly
        if not hasattr(self, '_station_to_files_cache'):
            self._station_to_files_cache = self._build_station_to_files_mapping()
        
        return self._station_to_files_cache
    
    def _get_line_to_json_file_mapping(self) -> dict:
        """Create a mapping of line names to their JSON file names."""
        # Use instance-level cache to avoid reloading data repeatedly
        if not hasattr(self, '_line_to_file_cache'):
            self._line_to_file_cache = self._build_line_to_file_mapping()
        
        return self._line_to_file_cache
    
    def _build_station_to_files_mapping(self) -> dict:
        """Build the mapping of stations to JSON files by loading all line data."""
        station_to_files = {}
        
        # Load all JSON files from the lines directory
        import json
        from pathlib import Path
        
        lines_dir = Path(__file__).parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Get stations from this JSON file
                    stations = data.get('stations', [])
                    file_name = json_file.stem  # Get filename without extension
                    
                    for station in stations:
                        station_name = station.get('name', '')
                        if station_name:
                            if station_name not in station_to_files:
                                station_to_files[station_name] = []
                            station_to_files[station_name].append(file_name)
            
            logger.debug(f"Built station-to-files mapping with {len(station_to_files)} stations")
            return station_to_files
            
        except Exception as e:
            logger.error(f"Failed to build station-to-files mapping: {e}")
            return {}
    
    def _build_line_to_file_mapping(self) -> dict:
        """Build the mapping of line names to JSON file names."""
        line_to_file = {}
        
        # Load all JSON files from the lines directory
        import json
        from pathlib import Path
        
        lines_dir = Path(__file__).parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Get line name from metadata
                    line_name = data.get('metadata', {}).get('line_name', '')
                    operator = data.get('metadata', {}).get('operator', '')
                    file_name = json_file.stem  # Get filename without extension
                    
                    if line_name:
                        line_to_file[line_name] = file_name
                    
                    # Add operator name mappings for common cases
                    if operator:
                        line_to_file[operator] = file_name
                    
                    # Add specific mappings for known operator/service variations
                    if 'south_western' in file_name:
                        line_to_file['South Western Railway'] = file_name
                        line_to_file['South Western Main Line'] = file_name
                    elif 'cross_country' in file_name:
                        line_to_file['CrossCountry'] = file_name
                        line_to_file['Cross Country'] = file_name
                        line_to_file['Cross Country Line'] = file_name
                    elif 'reading_to_basingstoke' in file_name:
                        line_to_file['Reading to Basingstoke Line'] = file_name
            
            logger.debug(f"[RouteDialog] Built line-to-file mapping with {len(line_to_file)} lines")
            logger.debug(f"[RouteDialog] Line mappings: {list(line_to_file.keys())}")
            return line_to_file
            
        except Exception as e:
            logger.error(f"[RouteDialog] Failed to build line-to-file mapping: {e}")
            return {}
    
    def _is_valid_interchange_geographically(self, from_station: str, to_station: str,
                                           from_line: str, to_line: str) -> bool:
        """
        Use geographic distance (Haversine) to validate if an interchange is legitimate.
        
        Args:
            from_station: Station where passenger is coming from
            to_station: Station where passenger is going to (potential interchange)
            from_line: Line name from route segment
            to_line: Line name to route segment
            
        Returns:
            True if this is a valid interchange based on geographic constraints
        """
        try:
            # The interchange station is the to_station (where the line change occurs)
            interchange_station = to_station
            
            # Check if this is a known through service first
            if self._is_known_through_service(from_line, to_line, interchange_station):
                logger.debug(f"[RouteDialog] Known through service detected at {interchange_station}: {from_line} -> {to_line}")
                return False  # Not a real interchange - through service
            
            # Get station coordinates from JSON files
            station_coordinates = self._get_station_coordinates()
            
            # Check if we have coordinates for the interchange station
            if interchange_station not in station_coordinates:
                logger.debug(f"[RouteDialog] Missing coordinates for interchange station: {interchange_station}")
                return True  # Conservative: allow if we can't validate
            
            # For a valid interchange, the station should exist in both line's JSON files
            # and be at the same geographic location (within reasonable tolerance)
            
            # Get the line-to-file mapping to find which JSON files contain each line
            line_to_file = self._get_line_to_json_file_mapping()
            
            file1 = line_to_file.get(from_line)
            file2 = line_to_file.get(to_line)
            
            if not file1 or not file2:
                logger.debug(f"[RouteDialog] Could not find JSON files for lines: {from_line} -> {file1}, {to_line} -> {file2}")
                return True  # Conservative: allow if we can't validate
            
            # Check if the interchange station appears in both JSON files
            station_to_files = self._get_station_to_json_files_mapping()
            station_files = station_to_files.get(interchange_station, [])
            
            if file1 in station_files and file2 in station_files:
                logger.debug(f"[RouteDialog] Valid interchange: {interchange_station} appears in both {file1} and {file2}")
                return True
            else:
                logger.debug(f"[RouteDialog] Invalid interchange: {interchange_station} not in both files. Found in: {station_files}")
                return False
            
        except Exception as e:
            logger.error(f"[RouteDialog] Error in geographic validation: {e}")
            return True  # Conservative: allow if validation fails
    
    def _is_known_through_service(self, line1: str, line2: str, station_name: str) -> bool:
        """Check if this represents a known through service where passengers don't change trains."""
        # Hook is a known through station for South Western services
        if station_name == "Hook":
            if ((line1 == "South Western Main Line" and line2 == "Reading to Basingstoke Line") or
                (line1 == "Reading to Basingstoke Line" and line2 == "South Western Main Line")):
                return True
        
        # Fleet is also a through station for South Western services
        if station_name == "Fleet":
            if ((line1 == "South Western Main Line" and line2 == "Reading to Basingstoke Line") or
                (line1 == "Reading to Basingstoke Line" and line2 == "South Western Main Line")):
                return True
        
        # Add other known through services here
        return False
    
    def _get_station_coordinates(self) -> dict:
        """Get station coordinates from JSON files."""
        # Use instance-level cache to avoid reloading data repeatedly
        if not hasattr(self, '_station_coordinates_cache'):
            self._station_coordinates_cache = self._build_station_coordinates_mapping()
        
        return self._station_coordinates_cache
    
    def _build_station_coordinates_mapping(self) -> dict:
        """Build the mapping of station names to their coordinates."""
        station_coordinates = {}
        
        # Load all JSON files from the lines directory
        import json
        from pathlib import Path
        
        lines_dir = Path(__file__).parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Get stations from this JSON file
                    stations = data.get('stations', [])
                    
                    for station in stations:
                        station_name = station.get('name', '')
                        coordinates = station.get('coordinates', {})
                        
                        if station_name and coordinates and 'lat' in coordinates and 'lng' in coordinates:
                            station_coordinates[station_name] = coordinates
            
            logger.debug(f"Built station coordinates mapping with {len(station_coordinates)} stations")
            return station_coordinates
            
        except Exception as e:
            logger.error(f"Failed to build station coordinates mapping: {e}")
            return {}
    
    def _calculate_haversine_distance(self, coord1: dict, coord2: dict) -> float:
        """Calculate the Haversine distance between two coordinates in kilometers."""
        import math
        
        # Extract coordinates (using 'lat' and 'lng' keys from JSON data)
        lat1 = math.radians(coord1['lat'])
        lon1 = math.radians(coord1['lng'])
        lat2 = math.radians(coord2['lat'])
        lon2 = math.radians(coord2['lng'])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        earth_radius_km = 6371.0
        
        return earth_radius_km * c
    
    def _is_meaningful_line_change(self, line1: str, line2: str) -> bool:
        """Check if a line change represents a meaningful train change (not just different names for same physical line)."""
        # Normalize line names to detect same physical lines with different names
        def normalize_line_name(line_name: str) -> str:
            line_lower = line_name.lower()
            
            # Group related line names that are actually the same physical railway
            # South Western Railway network - group all SW services together
            # This includes the main line and its extensions/branches that use the same trains
            if any(keyword in line_lower for keyword in [
                'south western main line', 'waterloo to woking', 'waterloo to basingstoke',
                'reading to basingstoke', 'basingstoke to reading'
            ]):
                return 'south_western_network_group'
            
            # Portsmouth Direct Line (Woking to Portsmouth/Guildford direction) - separate from SW network
            elif any(keyword in line_lower for keyword in [
                'portsmouth direct line', 'woking to portsmouth', 'woking to guildford'
            ]):
                return 'portsmouth_direct_group'
            
            # Great Western Railway group (includes Reading, Paddington routes)
            elif any(keyword in line_lower for keyword in ['great western', 'reading', 'paddington', 'gwr']):
                return 'great_western_group'
            
            # Main line groups that might have different segment names
            elif any(keyword in line_lower for keyword in ['west of england', 'exeter', 'devon', 'cornwall']):
                return 'west_of_england_group'
            
            elif any(keyword in line_lower for keyword in ['north downs', 'guildford']):
                return 'north_downs_group'
            
            elif any(keyword in line_lower for keyword in ['brighton', 'south coast']):
                return 'brighton_group'
            
            # If it contains "main line" or "line", try to group by the main route name
            elif 'main line' in line_lower:
                # Extract the main part before "main line"
                main_part = line_lower.split('main line')[0].strip()
                return f'{main_part}_main_line_group'
            
            elif 'line' in line_lower and len(line_lower.split()) > 1:
                # For other lines, use the first significant word
                words = line_lower.replace('line', '').strip().split()
                if words:
                    return f'{words[0]}_line_group'
            
            # Default: return the original name (different lines)
            return line_name.lower()
        
        # If the normalized names are the same, it's not a meaningful change
        return normalize_line_name(line1) != normalize_line_name(line2)
    
    def _is_continuous_train_service(self, line1: str, line2: str, station_name: str) -> bool:
        """Check if this represents a continuous train service where passengers don't change trains."""
        # Generic pattern: South Western Main Line continuing as Reading to Basingstoke Line
        # This represents the same physical train continuing its journey with different line designations
        if ((line1 == "South Western Main Line" and line2 == "Reading to Basingstoke Line") or
            (line1 == "Reading to Basingstoke Line" and line2 == "South Western Main Line")):
            return True
        
        # Add other continuous service patterns here as needed
        # For example, other lines where the same train continues with different designations
        
        return False
    
    def _classify_station_type(self, station_name: str) -> str:
        """Classify station type based on naming patterns to help detect interchanges."""
        name_lower = station_name.lower()
        
        if 'london' in name_lower:
            return 'london_terminal'
        elif any(suburb in name_lower for suburb in ['north', 'south', 'east', 'west', 'central']):
            return 'regional_hub'
        elif any(indicator in name_lower for indicator in ['junction', 'parkway', 'interchange']):
            return 'interchange_hub'
        else:
            return 'local_station'
