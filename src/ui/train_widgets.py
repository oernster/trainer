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

    def __init__(self, train_data: TrainData, theme: str = "dark"):
        """
        Initialize train item widget.

        Args:
            train_data: Train information to display
            theme: Current theme ("dark" or "light")
        """
        super().__init__()
        self.train_data = train_data
        self.current_theme = theme

        self.setup_ui()
        self.apply_theme()

        # Make widget clickable
        self.setFrameStyle(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

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
        
        # Get intermediate stations
        intermediate_stations = self.train_data.get_intermediate_stations()
        if intermediate_stations:
            # Show "Via:" prefix on first line
            first_line_layout = QHBoxLayout()
            via_label = QLabel("Via:")
            via_font = QFont()
            via_font.setPointSize(9)
            via_font.setBold(True)
            via_label.setFont(via_font)
            first_line_layout.addWidget(via_label)
            
            # Limit stations per line to avoid overcrowding
            max_stations_per_line = 4
            current_line_layout = first_line_layout
            stations_in_current_line = 0
            
            for i, station in enumerate(intermediate_stations):
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
                
                # Add arrow if not the first station on any line
                if i > 0 and stations_in_current_line > 0:
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
                elif i > 0 and stations_in_current_line == 0:
                    # For continuation lines, add arrow at the beginning
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
                
                station_label = QLabel(station.station_name)
                station_font = QFont()
                station_font.setPointSize(9)
                station_font.setItalic(True)
                station_label.setFont(station_font)
                
                # Check if this is a major interchange station for colored text
                if self._is_major_interchange(station.station_name):
                    # Theme-aware color for interchange stations
                    interchange_color = "#4caf50" if self.current_theme == "light" else "#ffeb3b"
                    station_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: transparent;
                            color: {interchange_color};
                            border: none;
                            margin: 0px;
                            padding: 0px;
                        }}
                    """)
                else:
                    # Regular light blue text for normal stations
                    station_label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            color: #1976d2;
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
                if self._is_major_interchange(station_name):
                    # Update interchange station color based on theme
                    interchange_color = "#4caf50" if self.current_theme == "light" else "#ffeb3b"
                    label.setStyleSheet(f"""
                        QLabel {{
                            background-color: transparent;
                            color: {interchange_color};
                            border: none;
                            margin: 0px;
                            padding: 0px;
                        }}
                    """)
                elif "→" not in station_name and not station_name.startswith("Current:") and not station_name.startswith("Arrives:"):
                    # Update regular station color
                    label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            color: #1976d2;
                            border: none;
                            margin: 0px;
                            padding: 0px;
                        }
                    """)

    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the click was on the Route button
            if hasattr(self, 'details_button') and self.details_button.geometry().contains(event.pos()):
                self.route_clicked.emit(self.train_data)
            else:
                self.train_clicked.emit(self.train_data)
        super().mousePressEvent(event)

    def _is_major_interchange(self, station_name: str) -> bool:
        """Check if a station is a major interchange where passengers typically change trains."""
        # Clean station name for comparison
        clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        major_interchanges = {
            "Clapham Junction",
            "Birmingham New Street",
            "Birmingham",
            "Reading",
            "Bristol Temple Meads",
            "Bristol",
            "Manchester Piccadilly",
            "Manchester",
            "Oxford",
            "London Waterloo",
            "London Paddington",
            "London Victoria",
            "London King's Cross",
            "London Euston",
            "London St Pancras",
            "Crewe",
            "Preston",
            "York",
            "Newcastle",
            "Edinburgh",
            "Glasgow Central"
        }
        
        return clean_name in major_interchanges


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

    def __init__(self, max_trains: int = 50):
        """
        Initialize train list widget.

        Args:
            max_trains: Maximum number of trains to display
        """
        super().__init__()
        self.max_trains = max_trains
        self.current_theme = "dark"
        self.train_items = []

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
        train_item = TrainItemWidget(train_data, self.current_theme)
        train_item.train_clicked.connect(self.train_selected.emit)
        train_item.route_clicked.connect(self.route_selected.emit)

        # Insert before the stretch at the end
        self.container_layout.insertWidget(self.container_layout.count() - 1, train_item)

        self.train_items.append(train_item)

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

        # Use original calling points directly to ensure consistency with main UI
        calling_points = self.train_data.calling_points
        logger.info(f"Displaying all {len(calling_points)} calling points in route dialog")

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
            # Create station display
            station_frame = QFrame()
            station_layout = QHBoxLayout(station_frame)
            station_layout.setContentsMargins(8, 4, 8, 4)

            # Station name with special formatting for origin/destination
            station_label = QLabel(calling_point.station_name)
            station_font = QFont()
            station_font.setPointSize(11)
            
            # Check if this is origin or destination
            is_origin = calling_point.is_origin
            is_destination = calling_point.is_destination
            
            if is_origin or is_destination:
                station_font.setBold(True)
            station_label.setFont(station_font)
            station_layout.addWidget(station_label)

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
            """)
    
    def _is_major_interchange(self, station_name: str) -> bool:
        """Check if a station is a major interchange where passengers typically change trains."""
        # Clean station name for comparison
        clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        major_interchanges = {
            "Clapham Junction",
            "Birmingham New Street",
            "Birmingham",
            "Reading",
            "Bristol Temple Meads",
            "Bristol",
            "Manchester Piccadilly",
            "Manchester",
            "Oxford",
            "London Waterloo",
            "London Paddington",
            "London Victoria",
            "London King's Cross",
            "London Euston",
            "London St Pancras",
            "Crewe",
            "Preston",
            "York",
            "Newcastle",
            "Edinburgh",
            "Glasgow Central"
        }
        
        return clean_name in major_interchanges
