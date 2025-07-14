"""
Weather UI widgets for the Trainer application.
Author: Oliver Ernster

This module contains weather display widgets following solid Object-Oriented
design principles with proper separation of concerns and theme integration.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette

from version import __weather_version__, __weather_api_provider__
from ..models.weather_data import (
    WeatherData,
    WeatherForecastData,
    TemperatureUnit,
    default_weather_icon_provider,
)
from ..managers.weather_manager import WeatherObserver
from ..managers.weather_config import WeatherConfig

logger = logging.getLogger(__name__)


class WeatherDisplayComponent(QWidget):
    """
    Abstract base class for weather display components.

    Follows Liskov Substitution Principle - derived classes are
    fully substitutable for this base class.
    """

    # Signals for weather widget interactions
    weather_item_clicked = Signal(object)  # WeatherData
    weather_item_hovered = Signal(object)  # WeatherData

    def __init__(self, parent=None):
        """Initialize weather display component."""
        super().__init__(parent)
        self._weather_data: Optional[WeatherData] = None
        self._config: Optional[WeatherConfig] = None
        self._theme_colors: Dict[str, str] = {}
        self.setup_ui()

    @abstractmethod
    def setup_ui(self) -> None:
        """Setup the user interface."""
        pass

    def update_weather_data(self, weather_data: WeatherData) -> None:
        """Update weather data and refresh display."""
        self._weather_data = weather_data
        self._refresh_display()

    def update_config(self, config: WeatherConfig) -> None:
        """Update weather configuration."""
        self._config = config
        self._refresh_display()

    @abstractmethod
    def _refresh_display(self) -> None:
        """Refresh the display with current weather data."""
        pass

    def apply_theme(self, theme_colors: Dict[str, str]) -> None:
        """Apply theme colors to the widget."""
        self._theme_colors = theme_colors
        self._apply_theme_styling()

    @abstractmethod
    def _apply_theme_styling(self) -> None:
        """Apply theme-specific styling."""
        pass

    def get_weather_data(self) -> Optional[WeatherData]:
        """Get current weather data."""
        return self._weather_data


class WeatherItemWidget(WeatherDisplayComponent):
    """
    Individual weather display item widget.

    Follows Single Responsibility Principle - only responsible for
    displaying a single weather data point.
    """

    def __init__(
        self,
        weather_data: Optional[WeatherData] = None,
        is_daily: bool = False,
        parent=None,
        scale_factor=1.0,
    ):
        """
        Initialize weather item widget.

        Args:
            weather_data: Weather data to display
            is_daily: Whether this is a daily forecast item
            parent: Parent widget
            scale_factor: UI scale factor for responsive design
        """
        self._is_daily = is_daily
        self._scale_factor = scale_factor
        self._time_label: Optional[QLabel] = None
        self._icon_label: Optional[QLabel] = None
        self._temp_label: Optional[QLabel] = None
        self._humidity_label: Optional[QLabel] = None

        super().__init__(parent)

        if weather_data:
            self.update_weather_data(weather_data)

    def setup_ui(self) -> None:
        """Setup the weather item UI."""
        # Scale widget size based on screen size - reasonable compact size for small screens
        if self._scale_factor < 1.0:  # Small screens
            base_width = 90 if self._is_daily else 80
            base_height = 130
        else:  # Large screens
            base_width = 120 if self._is_daily else 100
            base_height = 170 if self._is_daily else 150  # Increased height for daily forecast on large screens
        scaled_width = int(base_width * self._scale_factor)
        scaled_height = int(base_height * self._scale_factor)
        self.setFixedSize(scaled_width, scaled_height)

        # Main layout with minimal top margins to maximize space usage (scaled)
        layout = QVBoxLayout(self)
        scaled_margin_h = int(4 * self._scale_factor)
        scaled_margin_v_top = 0  # Zero top margin to eliminate space at top
        scaled_margin_v_bottom = int(8 * self._scale_factor)  # Reduced bottom margin
        scaled_spacing = int(1 * self._scale_factor)  # Minimal spacing
        layout.setContentsMargins(scaled_margin_h, scaled_margin_v_top, scaled_margin_h, scaled_margin_v_bottom)
        layout.setSpacing(scaled_spacing)

        # Time/Date label
        self._time_label = QLabel("--:--")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scaled_font_size = int(8 * self._scale_factor)
        self._time_label.setFont(QFont("Arial", scaled_font_size))
        layout.addWidget(self._time_label)

        # Weather icon - reasonable size for smaller screens (scaled)
        self._icon_label = QLabel("❓")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Use reasonable icon size for small screens - not too small
        base_icon_size = 32 if self._scale_factor < 1.0 else 48
        scaled_icon_size = int(base_icon_size * self._scale_factor)
        self._icon_label.setStyleSheet(
            f"font-size: {scaled_icon_size}px; font-family: 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji';"
        )
        layout.addWidget(self._icon_label)

        # Temperature
        self._temp_label = QLabel("--°")
        self._temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scaled_temp_font = int(10 * self._scale_factor)
        self._temp_label.setFont(QFont("Arial", scaled_temp_font, QFont.Weight.Bold))
        layout.addWidget(self._temp_label)

        # Humidity
        self._humidity_label = QLabel("--%")
        self._humidity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._humidity_label.setFont(QFont("Arial", scaled_font_size))
        layout.addWidget(self._humidity_label)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

    def _refresh_display(self) -> None:
        """Refresh the display with current weather data."""
        if not self._weather_data:
            return

        # Update time/date display
        if self._time_label:
            time_text = self._get_time_display()
            self._time_label.setText(time_text)

        # Update weather icon
        if self._icon_label:
            icon = default_weather_icon_provider.get_weather_icon(
                self._weather_data.weather_code
            )
            self._icon_label.setText(icon)

        # Update temperature
        if self._temp_label:
            if self._config and not self._config.is_metric_units():
                temp_text = self._weather_data.get_temperature_display_in_unit(
                    TemperatureUnit.FAHRENHEIT
                )
            else:
                temp_text = self._weather_data.temperature_display
            self._temp_label.setText(temp_text)

        # Update humidity
        if self._humidity_label:
            show_humidity = not self._config or self._config.show_humidity
            if show_humidity:
                # Add "H:" prefix to make it clear this is humidity
                humidity_text = f"H:{self._weather_data.humidity}%"
                self._humidity_label.setText(humidity_text)
                self._humidity_label.show()
            else:
                self._humidity_label.hide()

    def _get_time_display(self) -> str:
        """Get formatted time display."""
        if not self._weather_data:
            return "--:--"

        if self._is_daily:
            # Show day name for daily forecast
            return self._weather_data.timestamp.strftime("%a")
        else:
            # Show time for hourly forecast
            return self._weather_data.timestamp.strftime("%H:%M")

    def _apply_theme_styling(self) -> None:
        """Apply theme-specific styling."""
        if not self._theme_colors:
            return

        # Get theme colors with fallbacks
        text_color = self._theme_colors.get("text_primary", "#ffffff")
        hover_color = self._theme_colors.get("background_hover", "#404040")
        accent_color = self._theme_colors.get("primary_accent", "#1976d2")

        # Apply styling with completely transparent background
        style = f"""
        WeatherItemWidget {{
            background: transparent;
            border: none;
            border-radius: 12px;
            color: {text_color};
            padding: 0px;
        }}
        WeatherItemWidget:hover {{
            background-color: {hover_color};
            border: 1px solid {accent_color};
        }}
        QLabel {{
            color: {text_color};
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        """
        self.setStyleSheet(style)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton and self._weather_data:
            self.weather_item_clicked.emit(self._weather_data)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Handle mouse enter events."""
        if self._weather_data:
            self.weather_item_hovered.emit(self._weather_data)
        super().enterEvent(event)


class WeatherForecastWidget(QWidget):
    """
    Simple weather forecast display widget with guaranteed rounded corners.

    Uses QWidget for clean, direct styling control.
    """

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize forecast widget."""
        super().__init__(parent)
        self._scale_factor = scale_factor
        self._weather_items: List[WeatherItemWidget] = []
        self._container_layout: QHBoxLayout
        self.setup_ui()

    def setup_ui(self) -> None:
        """Setup the forecast widget UI."""
        # Scale height based on screen size - increase for large screens to prevent cutoff
        if self._scale_factor < 1.0:  # Small screens
            base_height = 160
        else:  # Large screens
            base_height = 180  # Increased for large screens to accommodate taller items
        scaled_height = int(base_height * self._scale_factor)
        self.setFixedHeight(scaled_height)

        # Simple horizontal layout for weather items (scaled) - centered distribution
        self._container_layout = QHBoxLayout(self)
        scaled_margin_h = int(8 * self._scale_factor)
        scaled_margin_v = 0  # Zero vertical margins to maximize space
        self._container_layout.setContentsMargins(scaled_margin_h, scaled_margin_v, scaled_margin_h, scaled_margin_v)

    def update_weather_forecast(
        self,
        weather_data: List[WeatherData],
        is_daily: bool = False,
        config: Optional[WeatherConfig] = None,
    ) -> None:
        """
        Update weather forecast display.

        Args:
            weather_data: List of weather data to display
            is_daily: Whether this is daily forecast data
            config: Weather configuration
        """
        # Clear existing items
        self.clear_weather_items()

        # Add leading stretch to center the items
        self._container_layout.addStretch(1)

        # Create weather items with proper spacing and centering
        for i, weather in enumerate(weather_data):
            item = WeatherItemWidget(weather, is_daily, scale_factor=self._scale_factor)
            if config:
                item.update_config(config)

            # Connect signals
            item.weather_item_clicked.connect(self._on_weather_item_clicked)
            item.weather_item_hovered.connect(self._on_weather_item_hovered)

            self._weather_items.append(item)
            self._container_layout.addWidget(item, 0)  # Fixed size, no stretch
            
            # Add spacing between items (except after the last one)
            if i < len(weather_data) - 1:
                scaled_spacing = int(4 * self._scale_factor)
                self._container_layout.addSpacing(scaled_spacing)

        # Add trailing stretch to center the items
        self._container_layout.addStretch(1)

        logger.debug(f"Updated weather forecast with {len(weather_data)} items")

    def clear_weather_items(self) -> None:
        """Clear all weather items."""
        for item in self._weather_items:
            item.deleteLater()
        self._weather_items.clear()

        # Clear layout
        while self._container_layout.count():
            child = self._container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def apply_theme(self, theme_colors: Dict[str, str]) -> None:
        """Apply theme to all weather items and frame."""
        for item in self._weather_items:
            item.apply_theme(theme_colors)

        # Make the forecast container completely transparent to allow weather items to blend with main window
        self.setStyleSheet(
            f"""
            background: transparent !important;
            border: none !important;
            border-radius: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
        """
        )

    def _on_weather_item_clicked(self, weather_data: WeatherData) -> None:
        """Handle weather item click."""
        logger.info(f"Weather item clicked: {weather_data.timestamp}")

    def _on_weather_item_hovered(self, weather_data: WeatherData) -> None:
        """Handle weather item hover."""
        # Could show tooltip or status bar message
        pass


class DailyForecastWidget(WeatherForecastWidget):
    """Widget for displaying daily weather forecast."""

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize daily forecast widget."""
        super().__init__(parent, scale_factor=scale_factor)

    def update_daily_forecast(
        self, daily_data: List[WeatherData], config: Optional[WeatherConfig] = None
    ) -> None:
        """Update daily forecast display."""
        self.update_weather_forecast(daily_data, is_daily=True, config=config)


class HourlyForecastWidget(WeatherForecastWidget):
    """Widget for displaying hourly weather forecast."""

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize hourly forecast widget."""
        super().__init__(parent, scale_factor=scale_factor)

    def update_hourly_forecast(
        self, hourly_data: List[WeatherData], config: Optional[WeatherConfig] = None
    ) -> None:
        """Update hourly forecast display."""
        self.update_weather_forecast(hourly_data, is_daily=False, config=config)


class WeatherWidget(QWidget):
    """
    Main weather display widget with two horizontal layers.

    Implements WeatherObserver interface to receive weather updates.
    Follows Composite pattern to manage child widgets.
    """

    # Signals for weather widget events
    weather_refresh_requested = Signal()
    weather_settings_requested = Signal()

    def __init__(self, parent=None, scale_factor=1.0):
        """Initialize weather widget."""
        super().__init__(parent)
        self._scale_factor = scale_factor

        # Child widgets
        self._daily_label: Optional[QLabel] = None
        self._weekly_label: Optional[QLabel] = None
        self._daily_forecast_widget: Optional[HourlyForecastWidget] = None
        self._weekly_forecast_widget: Optional[DailyForecastWidget] = None
        self._status_label: Optional[QLabel] = None

        # State
        self._current_forecast: Optional[WeatherForecastData] = None
        self._config: Optional[WeatherConfig] = None
        self._is_loading = False
        
        # Track user's manual visibility preference to prevent automatic overrides
        self._user_manually_hidden: bool = False

        # Auto-hide timer for error messages
        self._status_timer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status)

        self.setup_ui()
        logger.debug("WeatherWidget initialized")

    def setup_ui(self) -> None:
        """Setup the weather widget UI."""
        # Main layout with zero top padding to maximize content space
        scaled_margin_h = int(4 * self._scale_factor)  # Horizontal margins
        scaled_margin_top = 0  # Zero top margin to move content to very top
        scaled_margin_bottom = int(4 * self._scale_factor)  # Bottom margin
        scaled_spacing = int(4 * self._scale_factor)  # Further reduced spacing
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scaled_margin_h, scaled_margin_top, scaled_margin_h, scaled_margin_bottom)
        layout.setSpacing(scaled_spacing)

        # Daily forecast section
        self._daily_label = QLabel("Today's Weather (3-hourly)")
        scaled_font_size = int(10 * self._scale_factor)
        self._daily_label.setFont(QFont("Arial", scaled_font_size, QFont.Weight.Bold))
        layout.addWidget(self._daily_label)

        self._daily_forecast_widget = HourlyForecastWidget(scale_factor=self._scale_factor)
        layout.addWidget(self._daily_forecast_widget)

        # Reduced spacing before the 7-Day Forecast label for more compact layout
        scaled_extra_spacing = int(10 * self._scale_factor)  # Reduced from 35 to 10
        layout.addSpacing(scaled_extra_spacing)

        # Weekly forecast section
        self._weekly_label = QLabel("7-Day Forecast")
        self._weekly_label.setFont(QFont("Arial", scaled_font_size, QFont.Weight.Bold))
        layout.addWidget(self._weekly_label)

        self._weekly_forecast_widget = DailyForecastWidget(scale_factor=self._scale_factor)
        layout.addWidget(self._weekly_forecast_widget)

        # Status label removed - no longer needed

        # Set size policy with reasonable height (scaled)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Further increased height to prevent truncation of humidity values
        if self._scale_factor < 1.0:  # Small screens
            base_height = 330  # Increased from 310 to 330 to prevent cut-off
        else:  # Large screens
            base_height = 370  # Increased from 350 to 370 to prevent cut-off
        scaled_height = int(base_height * self._scale_factor)
        self.setFixedHeight(scaled_height)

    def update_config(self, config: WeatherConfig) -> None:
        """Update weather configuration."""
        self._config = config

        # Update child widgets
        if self._daily_forecast_widget:
            for item in self._daily_forecast_widget._weather_items:
                item.update_config(config)

        if self._weekly_forecast_widget:
            for item in self._weekly_forecast_widget._weather_items:
                item.update_config(config)

        # CRITICAL FIX: Don't override user's manual visibility preference
        # Never automatically set visibility based on config.enabled during updates
        # The visibility should only be controlled by user actions, not config updates
        if not hasattr(self, '_config_visibility_set'):
            # Only set visibility on the very first initialization, not on subsequent updates
            self.setVisible(config.enabled)
            self._config_visibility_set = True
            logger.debug(f"Weather widget visibility set to {config.enabled} (initial setup only)")
        else:
            # ALWAYS preserve user's manual visibility preference during any config update
            current_visibility = self.isVisible()
            logger.debug(f"Weather widget visibility preserved during config update: {current_visibility} (user preference)")
            # Do NOT call setVisible() here - this was causing the widget to reappear

    def apply_theme(self, theme_colors: Dict[str, str]) -> None:
        """Apply theme to weather widget and children."""
        # Apply theme to child widgets
        if self._daily_forecast_widget:
            self._daily_forecast_widget.apply_theme(theme_colors)

        if self._weekly_forecast_widget:
            self._weekly_forecast_widget.apply_theme(theme_colors)

        # Apply theme to labels
        text_color = theme_colors.get("primary_accent", "#1976d2")
        bg_color = theme_colors.get("background_primary", "#1a1a1a")

        label_style = f"""
        QLabel {{
            color: {text_color};
            background: transparent;
            padding: 2px;
        }}
        """

        if self._daily_label:
            self._daily_label.setStyleSheet(label_style)

        if self._weekly_label:
            self._weekly_label.setStyleSheet(label_style)

        # Apply theme to main widget - make completely transparent to blend with main window
        widget_style = f"""
        WeatherWidget {{
            background: transparent;
            border: none;
            border-radius: 0px;
            margin: 0px;
            padding: 0px;
        }}
        WeatherWidget QWidget {{
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        WeatherWidget QFrame {{
            background: transparent;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        """
        self.setStyleSheet(widget_style)

    # WeatherObserver implementation
    def on_weather_updated(self, weather_data: WeatherForecastData) -> None:
        """Handle weather data update."""
        self._current_forecast = weather_data

        # Update daily forecast (3-hourly for current day)
        if self._daily_forecast_widget:
            today_hourly = weather_data.current_day_hourly
            self._daily_forecast_widget.update_hourly_forecast(
                today_hourly, self._config
            )

        # Update weekly forecast
        if self._weekly_forecast_widget:
            self._weekly_forecast_widget.update_daily_forecast(
                weather_data.daily_forecast, self._config
            )

        # Status updates removed - no longer showing status messages

        logger.debug("Weather widget updated with new forecast data")

    def on_weather_error(self, error: Exception) -> None:
        """Handle weather error."""
        # Status messages disabled - only log errors
        logger.error(f"Weather widget received error: {error}")

    def on_weather_loading(self, is_loading: bool) -> None:
        """Handle weather loading state change."""
        self._is_loading = is_loading

        # Loading status messages removed - no longer showing status
        pass

    def _show_status(self, message: str, is_error: bool = False) -> None:
        """Show status message - disabled."""
        # Status messages disabled to eliminate unwanted widget below weather sections
        pass

    def _clear_status(self) -> None:
        """Clear status message - disabled."""
        # Status messages disabled
        pass

    def get_current_forecast(self) -> Optional[WeatherForecastData]:
        """Get current weather forecast."""
        return self._current_forecast

    def is_loading(self) -> bool:
        """Check if weather data is loading."""
        return self._is_loading

    def refresh_weather(self) -> None:
        """Request weather refresh."""
        self.weather_refresh_requested.emit()

    def show_weather_settings(self) -> None:
        """Request weather settings dialog."""
        self.weather_settings_requested.emit()
