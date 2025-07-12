"""
Astronomy UI widgets for the Trainer application.
Author: Oliver Ernster

This module contains UI components for displaying astronomy information,
following solid Object-Oriented design principles with proper encapsulation,
observer pattern integration, and responsive design.
"""

import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QGridLayout,
    QSizePolicy,
    QSpacerItem,
    QToolTip,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QUrl
from PySide6.QtGui import QFont, QPixmap, QDesktopServices, QCursor

from ..models.astronomy_data import (
    AstronomyForecastData,
    AstronomyData,
    AstronomyEvent,
    AstronomyEventType,
    default_astronomy_icon_provider,
)
from ..models.combined_forecast_data import CombinedForecastData
from ..managers.astronomy_config import AstronomyConfig

logger = logging.getLogger(__name__)


class AstronomyEventIcon(QLabel):
    """
    Clickable astronomy event icon widget.

    Follows Single Responsibility Principle - only responsible for
    displaying and handling clicks on astronomy event icons.
    """

    event_clicked = Signal(AstronomyEvent)

    def __init__(self, event: AstronomyEvent, parent=None, scale_factor=1.0):
        """Initialize astronomy event icon."""
        super().__init__(parent)
        self._event = event
        self._scale_factor = scale_factor
        self._setup_ui()
        self._setup_interactions()

    def _setup_ui(self) -> None:
        """Setup icon appearance."""
        # Set icon text
        icon_text = self._event.event_icon
        self.setText(icon_text)

        # Font size will be set in _setup_interactions method

        # Set alignment
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set size policy - smaller container to prevent truncation (scaled)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if self._scale_factor < 1.0:  # Small screens - reasonable size
            base_size = 50  # Reduced from 70
        else:  # Large screens
            base_size = 60  # Reduced from 100
        scaled_size = int(base_size * self._scale_factor)
        self.setFixedSize(scaled_size, scaled_size)

        # Set tooltip
        tooltip = f"{self._event.title}\n{self._event.get_formatted_time()}"
        if self._event.has_visibility_info:
            tooltip += f"\n{self._event.visibility_info}"
        self.setToolTip(tooltip)

        # Set cursor
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _setup_interactions(self) -> None:
        """Setup mouse interactions."""
        # Get current font size from the existing style (scaled) - reasonable size for small screens
        if self._scale_factor < 1.0:  # Small screens - reasonable icon size
            base_font_size = 28 if self._event.priority.value >= 3 else 24
        else:  # Large screens
            base_font_size = 40 if self._event.priority.value >= 3 else 36
        scaled_font_size = int(base_font_size * self._scale_factor)
        font_size = f"{scaled_font_size}px"
        
        scaled_border_radius = int(4 * self._scale_factor)
        scaled_padding = int(2 * self._scale_factor)

        self.setStyleSheet(
            f"""
            AstronomyEventIcon {{
                border: 1px solid transparent;
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding}px;
                font-size: {font_size};
                font-family: 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji';
            }}
            AstronomyEventIcon:hover {{
                border: 1px solid #1976d2;
                background-color: rgba(25, 118, 210, 0.1);
                font-size: {font_size};
                font-family: 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji';
            }}
        """
        )

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.event_clicked.emit(self._event)
            logger.debug(f"Astronomy event icon clicked: {self._event.title}")
        super().mousePressEvent(event)

    def get_event(self) -> AstronomyEvent:
        """Get the associated astronomy event."""
        return self._event


class DailyAstronomyPanel(QFrame):
    """
    Panel displaying astronomy events for a single day.

    Follows Single Responsibility Principle - only responsible for
    displaying daily astronomy information.
    """

    event_icon_clicked = Signal(AstronomyEvent)

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize daily astronomy panel."""
        super().__init__(parent)
        self._scale_factor = scale_factor
        self._astronomy_data: Optional[AstronomyData] = None
        self._event_icons: List[AstronomyEventIcon] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup panel layout."""
        self.setFrameStyle(QFrame.Shape.NoFrame)  # Remove frame to eliminate dark bars
        self.setLineWidth(0)

        # Main layout (scaled)
        layout = QVBoxLayout(self)
        scaled_margin_h = int(4 * self._scale_factor)
        scaled_margin_v = int(6 * self._scale_factor)
        scaled_spacing = int(4 * self._scale_factor)
        layout.setContentsMargins(scaled_margin_h, scaled_margin_v, scaled_margin_h, scaled_margin_v)
        layout.setSpacing(scaled_spacing)

        # Date label - ensure no background styling (scaled)
        self._date_label = QLabel()
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._date_label.setStyleSheet("background: transparent; border: none;")
        font = QFont()
        scaled_font_size = int(10 * self._scale_factor)
        font.setPointSize(scaled_font_size)
        font.setBold(True)
        self._date_label.setFont(font)
        layout.addWidget(self._date_label)

        # Icons container - remove any background styling (scaled)
        self._icons_widget = QWidget()
        self._icons_widget.setStyleSheet("background: transparent; border: none;")
        self._icons_layout = QHBoxLayout(self._icons_widget)
        scaled_icon_margin_h = int(2 * self._scale_factor)
        scaled_icon_margin_v = int(4 * self._scale_factor)
        scaled_icon_spacing = int(3 * self._scale_factor)
        self._icons_layout.setContentsMargins(scaled_icon_margin_h, scaled_icon_margin_v, scaled_icon_margin_h, scaled_icon_margin_v)
        self._icons_layout.setSpacing(scaled_icon_spacing)
        self._icons_layout.addStretch()  # Center icons
        layout.addWidget(self._icons_widget)

        # Moon phase label - ensure no background styling, reasonable size for small screens (scaled)
        self._moon_label = QLabel()
        self._moon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Use reasonable moon icon size for small screens
        base_moon_size = 24 if self._scale_factor < 1.0 else 32
        scaled_moon_size = int(base_moon_size * self._scale_factor)
        self._moon_label.setStyleSheet(
            f"background: transparent; border: none; font-size: {scaled_moon_size}px; font-family: 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji';"
        )
        layout.addWidget(self._moon_label)

        # Set size policy - expanding width, fixed height for better distribution
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        base_height = 160 if self._scale_factor < 1.0 else 180  # Increased to prevent internal content truncation
        base_min_width = 100 if self._scale_factor < 1.0 else 120  # Minimum width
        scaled_height = int(base_height * self._scale_factor)
        scaled_min_width = int(base_min_width * self._scale_factor)
        self.setFixedHeight(scaled_height)
        self.setMinimumWidth(scaled_min_width)

    def update_data(self, astronomy_data: AstronomyData) -> None:
        """Update panel with astronomy data."""
        self._astronomy_data = astronomy_data

        # Update date label
        date_str = astronomy_data.date.strftime("%a\n%d")
        self._date_label.setText(date_str)

        # Clear existing icons
        self._clear_icons()

        # Add event icons (limit to 3 for space)
        events_to_show = astronomy_data.get_sorted_events(by_priority=True)[:3]

        for event in events_to_show:
            icon = AstronomyEventIcon(event, scale_factor=self._scale_factor)
            icon.event_clicked.connect(self.event_icon_clicked.emit)
            self._event_icons.append(icon)
            self._icons_layout.insertWidget(self._icons_layout.count() - 1, icon)

        # Update moon phase
        self._moon_label.setText(astronomy_data.moon_phase_icon)

        # Update styling based on event priority
        self._update_styling()

    def _clear_icons(self) -> None:
        """Clear all event icons."""
        for icon in self._event_icons:
            icon.deleteLater()
        self._event_icons.clear()

    def _update_styling(self) -> None:
        """Update panel styling based on content."""
        if not self._astronomy_data:
            return

        if self._astronomy_data.has_high_priority_events:
            # High priority events - highlight border
            self.setStyleSheet(
                """
                DailyAstronomyPanel {
                    border: 2px solid #ff9800;
                    border-radius: 12px;
                    background-color: rgba(255, 152, 0, 0.1);
                }
            """
            )
        elif self._astronomy_data.has_events:
            # Regular events - subtle border
            self.setStyleSheet(
                """
                DailyAstronomyPanel {
                    border: 1px solid #1976d2;
                    border-radius: 12px;
                    background-color: rgba(25, 118, 210, 0.05);
                }
            """
            )
        else:
            # No events - minimal styling
            self.setStyleSheet(
                """
                DailyAstronomyPanel {
                    border: 1px solid #404040;
                    border-radius: 12px;
                    background-color: transparent;
                }
            """
            )


class AstronomyForecastPanel(QWidget):
    """
    Panel displaying 7-day astronomy forecast.

    Follows Single Responsibility Principle - only responsible for
    displaying the astronomy forecast overview.
    """

    event_icon_clicked = Signal(AstronomyEvent)

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize astronomy forecast panel."""
        super().__init__(parent)
        self._scale_factor = scale_factor
        self._daily_panels: List[DailyAstronomyPanel] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup forecast panel layout."""
        # Main layout - evenly distributed panels across full width
        layout = QHBoxLayout(self)
        scaled_margin = int(4 * self._scale_factor)
        layout.setContentsMargins(scaled_margin, scaled_margin, scaled_margin, scaled_margin)
        
        # Create 7 daily panels with equal distribution
        for i in range(7):
            panel = DailyAstronomyPanel(scale_factor=self._scale_factor)
            panel.event_icon_clicked.connect(self.event_icon_clicked.emit)
            self._daily_panels.append(panel)
            layout.addWidget(panel, 1)  # Equal stretch for all panels
            
            # Add minimal spacing between panels (except after the last one)
            if i < 6:
                scaled_spacing = int(2 * self._scale_factor)  # Reduced spacing
                layout.addSpacing(scaled_spacing)

    def update_forecast(self, forecast_data: AstronomyForecastData) -> None:
        """Update forecast display with new data."""
        # Update each daily panel
        for i, panel in enumerate(self._daily_panels):
            if i < len(forecast_data.daily_astronomy):
                panel.update_data(forecast_data.daily_astronomy[i])
                panel.show()
            else:
                panel.hide()

        logger.debug(
            f"Updated astronomy forecast panel with {len(forecast_data.daily_astronomy)} days"
        )


class AstronomyEventDetails(QFrame):
    """
    Detailed view of astronomy events for a specific day.

    Follows Single Responsibility Principle - only responsible for
    displaying detailed astronomy event information.
    """

    nasa_link_clicked = Signal(str)

    def __init__(self, parent=None):
        """Initialize astronomy event details."""
        super().__init__(parent)
        self._astronomy_data: Optional[AstronomyData] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup details layout."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)

        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)

        # Initially empty
        self._show_no_data()

    def _show_no_data(self) -> None:
        """Show message when no data is available."""
        self._clear_layout()

        label = QLabel("Select a day to view astronomy details")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888888; font-style: italic;")
        self._layout.addWidget(label)

    def _clear_layout(self) -> None:
        """Clear all widgets from layout."""
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def update_data(self, astronomy_data: AstronomyData) -> None:
        """Update details with astronomy data."""
        self._astronomy_data = astronomy_data
        self._clear_layout()

        if not astronomy_data.has_events:
            self._show_no_events(astronomy_data.date)
            return

        # Date header
        date_label = QLabel(astronomy_data.date.strftime("%A, %B %d, %Y"))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        date_label.setFont(font)
        date_label.setStyleSheet("color: #1976d2; margin-bottom: 8px;")
        self._layout.addWidget(date_label)

        # Moon phase info
        if astronomy_data.moon_phase:
            moon_widget = self._create_moon_info_widget(astronomy_data)
            self._layout.addWidget(moon_widget)

        # Events
        events = astronomy_data.get_sorted_events(by_priority=True)
        for event in events:
            event_widget = self._create_event_widget(event)
            self._layout.addWidget(event_widget)

        # Add stretch
        self._layout.addStretch()

    def _show_no_events(self, event_date: date) -> None:
        """Show message when no events are available for the date."""
        date_label = QLabel(event_date.strftime("%A, %B %d, %Y"))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        date_label.setFont(font)
        self._layout.addWidget(date_label)

        no_events_label = QLabel("No astronomy events scheduled for this day")
        no_events_label.setStyleSheet(
            "color: #888888; font-style: italic; margin-top: 16px;"
        )
        self._layout.addWidget(no_events_label)

        self._layout.addStretch()

    def _create_moon_info_widget(self, astronomy_data: AstronomyData) -> QWidget:
        """Create moon phase information widget."""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.Box)
        widget.setStyleSheet(
            """
            QFrame {
                border: 1px solid #404040;
                border-radius: 6px;
                background-color: rgba(79, 195, 247, 0.05);
                padding: 8px;
            }
        """
        )

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Moon icon - larger size
        moon_icon = QLabel(astronomy_data.moon_phase_icon)
        font = QFont()
        font.setPointSize(32)  # Larger moon icon in details
        moon_icon.setFont(font)
        layout.addWidget(moon_icon)

        # Moon info
        info_layout = QVBoxLayout()

        if astronomy_data.moon_phase:
            phase_name = astronomy_data.moon_phase.value.replace("_", " ").title()
        else:
            phase_name = "Unknown"
        phase_label = QLabel(f"Moon Phase: {phase_name}")
        font = QFont()
        font.setBold(True)
        phase_label.setFont(font)
        info_layout.addWidget(phase_label)

        if astronomy_data.moon_illumination is not None:
            illumination_label = QLabel(
                f"Illumination: {astronomy_data.moon_illumination:.1%}"
            )
            info_layout.addWidget(illumination_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        return widget

    def _create_event_widget(self, event: AstronomyEvent) -> QWidget:
        """Create widget for a single astronomy event."""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.Box)

        # Style based on priority
        if event.priority.value >= 3:
            border_color = "#ff9800"  # Orange for high priority
        else:
            border_color = "#1976d2"  # Blue for normal priority

        widget.setStyleSheet(
            f"""
            QFrame {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: rgba(79, 195, 247, 0.03);
                padding: 8px;
                margin: 4px 0px;
            }}
        """
        )

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Header with icon and title
        header_layout = QHBoxLayout()

        # Event icon - larger size
        icon_label = QLabel(event.event_icon)
        font = QFont()
        font.setPointSize(26)  # Larger event icons in details
        icon_label.setFont(font)
        header_layout.addWidget(icon_label)

        # Title and time
        title_layout = QVBoxLayout()

        title_label = QLabel(event.title)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title_label.setFont(font)
        title_layout.addWidget(title_label)

        time_label = QLabel(event.get_formatted_time())
        time_label.setStyleSheet("color: #888888;")
        title_layout.addWidget(time_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Description
        desc_label = QLabel(event.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin: 8px 0px;")
        layout.addWidget(desc_label)

        # Visibility info
        if event.has_visibility_info:
            visibility_label = QLabel(f"👁️ {event.visibility_info}")
            visibility_label.setStyleSheet("color: #81c784; font-style: italic;")
            layout.addWidget(visibility_label)

        # NASA link button
        if event.nasa_url:
            link_button = QPushButton("🔗 View on NASA Website")
            link_button.setStyleSheet(
                """
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QPushButton:pressed {
                    background-color: #0d47a1;
                }
            """
            )
            if event.nasa_url:
                link_button.clicked.connect(
                    lambda url=event.nasa_url: self._open_nasa_link(url)
                )
            layout.addWidget(link_button)

        return widget

    def _open_nasa_link(self, url: str) -> None:
        """Open NASA link in browser."""
        try:
            QDesktopServices.openUrl(QUrl(url))
            self.nasa_link_clicked.emit(url)
            logger.info(f"Opened NASA link: {url}")
        except Exception as e:
            logger.error(f"Failed to open NASA link {url}: {e}")


class AstronomyExpandablePanel(QWidget):
    """
    Expandable panel for detailed astronomy information.

    Follows Single Responsibility Principle - only responsible for
    managing the expandable/collapsible behavior and detailed content.
    """

    expansion_changed = Signal(bool)
    nasa_link_clicked = Signal(str)

    def __init__(self, parent=None):
        """Initialize expandable panel."""
        super().__init__(parent)
        self._is_expanded = False
        self._forecast_data: Optional[AstronomyForecastData] = None
        self._animation: Optional[QPropertyAnimation] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup expandable panel layout."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with toggle button
        self._header = self._create_header()
        layout.addWidget(self._header)

        # Content area (initially hidden)
        self._content_area = QScrollArea()
        self._content_area.setWidgetResizable(True)
        self._content_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._content_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._content_area.setMaximumHeight(0)  # Initially collapsed

        # Content widget
        self._content_widget = AstronomyEventDetails()
        self._content_widget.nasa_link_clicked.connect(self.nasa_link_clicked.emit)
        self._content_area.setWidget(self._content_widget)

        layout.addWidget(self._content_area)

        # Setup animation
        self._setup_animation()

    def _create_header(self) -> QWidget:
        """Create header with toggle button."""
        header = QFrame()
        header.setFrameStyle(QFrame.Shape.Box)
        header.setStyleSheet(
            """
            QFrame {
                border: 1px solid #1976d2;
                border-radius: 6px;
                background-color: rgba(25, 118, 210, 0.1);
                padding: 8px;
            }
            QFrame:hover {
                background-color: rgba(79, 195, 247, 0.2);
            }
        """
        )
        header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)

        # Title
        title_label = QLabel("🌟 Astronomy Details")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        title_label.setFont(font)
        layout.addWidget(title_label)

        layout.addStretch()

        # Toggle indicator
        self._toggle_indicator = QLabel("▼")
        font = QFont()
        font.setPointSize(10)
        self._toggle_indicator.setFont(font)
        layout.addWidget(self._toggle_indicator)

        # Make header clickable
        header.mousePressEvent = self._on_header_clicked

        return header

    def _setup_animation(self) -> None:
        """Setup expand/collapse animation."""
        self._animation = QPropertyAnimation(self._content_area, b"maximumHeight")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _on_header_clicked(self, event) -> None:
        """Handle header click to toggle expansion."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_expansion()

    def toggle_expansion(self) -> None:
        """Toggle panel expansion state."""
        if self._is_expanded:
            self._collapse()
        else:
            self._expand()

    def _expand(self) -> None:
        """Expand the panel."""
        if self._is_expanded:
            return

        self._is_expanded = True
        self._toggle_indicator.setText("▲")

        # Calculate target height
        content_height = self._content_widget.sizeHint().height()
        target_height = min(content_height, 400)  # Max height limit

        # Animate expansion
        if self._animation:
            self._animation.setStartValue(0)
            self._animation.setEndValue(target_height)
            self._animation.start()

        self.expansion_changed.emit(True)
        logger.debug("Astronomy panel expanded")

    def _collapse(self) -> None:
        """Collapse the panel."""
        if not self._is_expanded:
            return

        self._is_expanded = False
        self._toggle_indicator.setText("▼")

        # Animate collapse
        if self._animation:
            current_height = self._content_area.height()
            self._animation.setStartValue(current_height)
            self._animation.setEndValue(0)
            self._animation.start()

        self.expansion_changed.emit(False)
        logger.debug("Astronomy panel collapsed")

    def update_details(self, forecast_data: AstronomyForecastData) -> None:
        """Update detailed content with forecast data."""
        self._forecast_data = forecast_data

        # Show today's data by default
        today_data = forecast_data.get_today_astronomy()
        if today_data:
            self._content_widget.update_data(today_data)
        else:
            # Show first available day
            if forecast_data.daily_astronomy:
                self._content_widget.update_data(forecast_data.daily_astronomy[0])

    def show_date_details(self, target_date: date) -> None:
        """Show details for a specific date."""
        if not self._forecast_data:
            return

        astronomy_data = self._forecast_data.get_astronomy_for_date(target_date)
        if astronomy_data:
            self._content_widget.update_data(astronomy_data)

            # Expand if not already expanded
            if not self._is_expanded:
                self._expand()

    def is_expanded(self) -> bool:
        """Check if panel is currently expanded."""
        return self._is_expanded


class AstronomyWidget(QWidget):
    """
    Main astronomy widget container.

    Follows Composite pattern - contains and coordinates multiple
    astronomy-related UI components.
    """

    astronomy_refresh_requested = Signal()
    astronomy_event_clicked = Signal(AstronomyEvent)
    nasa_link_clicked = Signal(str)

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize astronomy widget."""
        super().__init__(parent)
        self._scale_factor = scale_factor
        self._config: Optional[AstronomyConfig] = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Setup main astronomy widget layout."""
        # Main layout (scaled)
        layout = QVBoxLayout(self)
        scaled_margin_h = int(8 * self._scale_factor)
        scaled_margin_v = int(6 * self._scale_factor)
        scaled_spacing = int(6 * self._scale_factor)
        layout.setContentsMargins(scaled_margin_h, scaled_margin_v, scaled_margin_h, scaled_margin_v)
        layout.setSpacing(scaled_spacing)

        # Forecast panel
        self._forecast_panel = AstronomyForecastPanel(scale_factor=self._scale_factor)
        layout.addWidget(self._forecast_panel)

        # Astronomical events button (scaled)
        self._sky_button = QPushButton("🌟 Current Astronomical Events")
        scaled_font_size = int(12 * self._scale_factor)
        scaled_padding_h = int(12 * self._scale_factor)
        scaled_padding_v = int(6 * self._scale_factor)
        scaled_border_radius = int(6 * self._scale_factor)
        scaled_max_height = int(32 * self._scale_factor)
        self._sky_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #1976d2;
                color: white;
                border: none;
                border-radius: {scaled_border_radius}px;
                padding: {scaled_padding_v}px {scaled_padding_h}px;
                font-weight: bold;
                font-size: {scaled_font_size}px;
                max-height: {scaled_max_height}px;
            }}
            QPushButton:hover {{
                background-color: #1565c0;
            }}
            QPushButton:pressed {{
                background-color: #0d47a1;
            }}
        """
        )
        self._sky_button.clicked.connect(self._open_night_sky_view)
        layout.addWidget(self._sky_button)

        # Set size policy - adjusted height to accommodate taller panels
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Increased height to prevent internal content truncation while still being compact
        if self._scale_factor < 1.0:  # Small screens
            base_height = 220  # Increased from 200 to accommodate taller panels
        else:  # Large screens
            base_height = 280  # Increased from 260 to accommodate taller panels
        scaled_max_height = int(base_height * self._scale_factor)
        self.setMaximumHeight(scaled_max_height)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Connect forecast panel signals
        self._forecast_panel.event_icon_clicked.connect(self._on_event_icon_clicked)

    def _on_event_icon_clicked(self, event: AstronomyEvent) -> None:
        """Handle event icon click."""
        # Open NASA website for the specific event
        if event.nasa_url:
            self._open_nasa_link(event.nasa_url)
        else:
            # Fallback to general NASA astronomy page
            self._open_nasa_astronomy_page()

        # Emit signal for external handling
        self.astronomy_event_clicked.emit(event)

        logger.debug(f"Astronomy event clicked: {event.title}")

    def _open_night_sky_view(self) -> None:
        """Open current astronomical events page showing today's phenomena."""
        # Use EarthSky's Tonight page - always shows current date's astronomical events
        # This automatically updates daily with current planetary positions, conjunctions,
        # meteor showers, comets, solar activity, and other interesting phenomena
        sky_url = "https://earthsky.org/tonight/"

        self._open_nasa_link(sky_url)
        logger.info("Opened EarthSky's current astronomical events for tonight")

    def _open_nasa_astronomy_page(self) -> None:
        """Open NASA astronomy page in browser."""
        nasa_url = "https://science.nasa.gov/astrophysics/"
        self._open_nasa_link(nasa_url)

    def _open_nasa_link(self, url: str) -> None:
        """Open NASA link in browser."""
        try:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl

            QDesktopServices.openUrl(QUrl(url))
            self.nasa_link_clicked.emit(url)
            logger.info(f"Opened NASA link: {url}")
        except Exception as e:
            logger.error(f"Failed to open NASA link {url}: {e}")

    def on_astronomy_updated(self, forecast_data: AstronomyForecastData) -> None:
        """Handle astronomy data updates."""
        # Update forecast panel
        self._forecast_panel.update_forecast(forecast_data)

        logger.info(
            f"Astronomy widget updated with {forecast_data.total_events} events"
        )

    def on_astronomy_error(self, error_message: str) -> None:
        """Handle astronomy error."""
        logger.warning(f"Astronomy error in widget: {error_message}")
        # Could show error state in UI

    def on_astronomy_loading(self, is_loading: bool) -> None:
        """Handle astronomy loading state change."""
        # Could show loading indicator
        logger.debug(f"Astronomy loading state: {is_loading}")

    def update_config(self, config: AstronomyConfig) -> None:
        """Update astronomy configuration."""
        old_config = self._config
        self._config = config

        # Don't automatically show the widget here - let the main window control visibility
        # based on whether it's properly added to the layout with data
        # self.setVisible(config.enabled and config.display.show_in_forecast)
        
        # If API key was just added, show loading state
        if (old_config and not old_config.has_valid_api_key() and
            config.has_valid_api_key()):
            logger.info("API key newly available - astronomy widget ready for data")

        logger.debug("Astronomy widget configuration updated")

    def apply_theme(self, theme_colors: Dict[str, str]) -> None:
        """Apply theme colors to astronomy widget."""
        # Apply theme to the widget with absolutely no borders or frames
        self.setStyleSheet(
            f"""
            AstronomyWidget {{
                background-color: {theme_colors.get('background_primary', '#1a1a1a')};
                color: {theme_colors.get('text_primary', '#ffffff')};
                border: none;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
            }}
            AstronomyWidget QWidget {{
                border: none;
                margin: 0px;
                padding: 0px;
            }}
            AstronomyWidget QFrame {{
                border: none;
                margin: 0px;
                padding: 0px;
            }}
        """
        )

        logger.debug("Applied theme to astronomy widget")
