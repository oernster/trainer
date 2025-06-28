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
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ..models.train_data import TrainData, TrainStatus

logger = logging.getLogger(__name__)


class TrainItemWidget(QFrame):
    """
    Individual train information display widget with theme support.

    Displays comprehensive train information including departure time,
    destination, platform, operator, status, and current location.
    """

    # Signal emitted when train item is clicked
    train_clicked = Signal(TrainData)

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
        self.setFrameStyle(QFrame.Box)
        self.setCursor(Qt.PointingHandCursor)

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
        platform_info.setAlignment(Qt.AlignRight)
        right_layout.addWidget(platform_info)

        # Details button
        details_button = QLabel("📋 Details")
        details_button.setAlignment(Qt.AlignRight)
        details_button.setStyleSheet("""
            QLabel {
                background-color: rgba(79, 195, 247, 0.2);
                border: 1px solid #4fc3f7;
                border-radius: 4px;
                padding: 2px 6px;
                margin-left: 8px;
                font-weight: bold;
            }
            QLabel:hover {
                background-color: rgba(79, 195, 247, 0.4);
            }
        """)
        details_button.setCursor(Qt.PointingHandCursor)
        right_layout.addWidget(details_button)

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
        status_info.setAlignment(Qt.AlignRight)
        status_font = QFont()
        status_font.setPointSize(10)
        status_font.setBold(True)
        status_info.setFont(status_font)

        # Set status color
        status_color = self.train_data.get_status_color(self.current_theme)
        status_info.setStyleSheet(f"color: {status_color};")

        details_layout.addWidget(status_info)
        layout.addLayout(details_layout)

        # Third line: Calling points (intermediate stations)
        calling_points_layout = QHBoxLayout()
        
        # Show calling points summary (show all stations)
        calling_points_text = self.train_data.format_calling_points()
        calling_points_info = QLabel(calling_points_text)
        calling_points_font = QFont()
        calling_points_font.setPointSize(9)
        calling_points_font.setItalic(True)
        calling_points_info.setFont(calling_points_font)
        calling_points_layout.addWidget(calling_points_info)
        
        calling_points_layout.addStretch()
        layout.addLayout(calling_points_layout)

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
            arrival_info.setAlignment(Qt.AlignRight)
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
            border-color: #4fc3f7;
        }}
        
        QLabel {{
            color: #ffffff;
            background-color: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
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
        """

    def update_theme(self, theme: str):
        """
        Update widget theme.

        Args:
            theme: New theme name ("dark" or "light")
        """
        self.current_theme = theme
        self.apply_theme()

    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.LeftButton:
            self.train_clicked.emit(self.train_data)
        super().mousePressEvent(event)


class TrainListWidget(QScrollArea):
    """
    Scrollable list of train departures with theme support.

    Displays up to max_trains train items in a scrollable area,
    with support for theme switching and real-time updates.
    """

    # Signal emitted when a train is selected
    train_selected = Signal(TrainData)

    def __init__(self, max_trains: int = 50):
        """
        Initialize train list widget.

        Args:
            max_trains: Maximum number of trains to display
        """
        super().__init__()
        self.max_trains = max_trains
        self.current_theme = "dark"
        self.train_items: List[TrainItemWidget] = []

        self.setup_ui()
        self.apply_theme()

        logger.info(f"TrainListWidget initialized with max_trains={max_trains}")

    def setup_ui(self):
        """Setup the train list UI."""
        # Create container widget
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(4, 4, 4, 4)
        self.container_layout.setSpacing(2)

        # Add stretch to push items to top
        self.container_layout.addStretch()

        # Configure scroll area
        self.setWidget(self.container_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def apply_theme(self, theme: str = None):
        """
        Apply theme styling to the scroll area.

        Args:
            theme: Theme name, uses current theme if None
        """
        if theme:
            self.current_theme = theme

        if self.current_theme == "dark":
            self.setStyleSheet(self.get_dark_scroll_style())
        else:
            self.setStyleSheet(self.get_light_scroll_style())

        # Update all train items
        for train_item in self.train_items:
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

        logger.info(f"Updated train list with {len(display_trains)} trains")

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

        # Insert before the stretch
        self.container_layout.insertWidget(
            self.container_layout.count() - 1, train_item
        )

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
        layout.setAlignment(Qt.AlignCenter)

        # Icon
        icon_label = QLabel("🚂")
        icon_font = QFont()
        icon_font.setPointSize(48)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Message
        message_label = QLabel("No trains available")
        message_font = QFont()
        message_font.setPointSize(16)
        message_label.setFont(message_font)
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)

        # Subtitle
        subtitle_label = QLabel("Check your connection or try refreshing")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
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
