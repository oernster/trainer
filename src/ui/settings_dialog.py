"""
Settings dialog for the Train Times application.
Author: Oliver Ernster

This module provides a dialog for configuring API credentials and other settings.
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QMessageBox,
    QTabWidget,
    QWidget,
    QProgressDialog,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont
from ..managers.config_manager import ConfigManager, ConfigData, ConfigurationError
from ..api.api_manager import (
    APIManager,
    APIException,
    NetworkException,
    AuthenticationException,
)
from ..managers.theme_manager import ThemeManager
from ..managers.astronomy_config import AstronomyConfig


class HorizontalSpinWidget(QWidget):
    """A horizontal spin control with left/right arrows and a value display, based on test.py."""

    valueChanged = Signal(int)

    def __init__(
        self,
        minimum=0,
        maximum=100,
        initial_value=0,
        step=1,
        suffix="",
        parent=None,
        theme_manager=None,
    ):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.suffix = suffix
        self._value = initial_value
        self.theme_manager = theme_manager

        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Value display
        self.value_label = QLabel(str(self._value) + self.suffix)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumWidth(120)
        self.value_label.setFixedHeight(32)

        # Down arrow button (left side) - MUCH LARGER
        self.down_button = QPushButton("◀")
        self.down_button.setFixedSize(60, 32)
        self.down_button.clicked.connect(self.decrement)

        # Up arrow button (right side) - MUCH LARGER
        self.up_button = QPushButton("▶")
        self.up_button.setFixedSize(60, 32)
        self.up_button.clicked.connect(self.increment)

        # Add widgets to layout
        main_layout.addWidget(self.value_label)
        main_layout.addWidget(self.down_button)
        main_layout.addWidget(self.up_button)

    def setup_style(self):
        """Apply styling to the widget."""
        # Get theme colors if theme manager is available
        if self.theme_manager:
            primary_accent = self.theme_manager.get_color("primary_accent")
            text_primary = self.theme_manager.get_color("text_primary")
            background_hover = self.theme_manager.get_color("background_hover")
            border_accent = self.theme_manager.get_color("border_accent")
            background_secondary = self.theme_manager.get_color("background_secondary")
            border_primary = self.theme_manager.get_color("border_primary")
        else:
            # Fallback colors for dark theme
            primary_accent = "#4fc3f7"
            text_primary = "#ffffff"
            background_hover = "#404040"
            border_accent = "#4fc3f7"
            background_secondary = "#2d2d2d"
            border_primary = "#404040"

        # Button styling - MUCH LARGER arrows for human visibility with light blue background
        button_style = f"""
            QPushButton {{
                background-color: {primary_accent};
                border: 1px solid {border_accent};
                border-radius: 3px;
                font-weight: bold;
                font-size: 24px;
                color: {text_primary};
            }}
            QPushButton:hover {{
                background-color: {background_hover};
                color: {text_primary};
            }}
            QPushButton:pressed {{
                background-color: {border_accent};
                border: 1px solid {border_accent};
                color: {text_primary};
            }}
            QPushButton:disabled {{
                background-color: #f5f5f5;
                color: #ffc0cb;
            }}
        """

        # Label styling - Dark background for value display
        label_style = f"""
            QLabel {{
                background-color: {background_secondary};
                border: 1px solid {border_primary};
                border-radius: 2px;
                padding: 4px;
                font-weight: bold;
                color: {text_primary};
            }}
        """

        self.up_button.setStyleSheet(button_style)
        self.down_button.setStyleSheet(button_style)
        self.value_label.setStyleSheet(label_style)

    def increment(self):
        """Increment the value by the step amount."""
        new_value = min(self._value + self.step, self.maximum)
        self.set_value(new_value)

    def decrement(self):
        """Decrement the value by the step amount."""
        new_value = max(self._value - self.step, self.minimum)
        self.set_value(new_value)

    def set_value(self, value):
        """Set the current value."""
        if self.minimum <= value <= self.maximum:
            old_value = self._value
            self._value = value
            self.value_label.setText(str(value) + self.suffix)

            # Update button states
            self.up_button.setEnabled(value < self.maximum)
            self.down_button.setEnabled(value > self.minimum)

            if old_value != value:
                self.valueChanged.emit(value)

    def value(self):
        """Get the current value."""
        return self._value

    def setValue(self, value):
        """Set the current value (Qt-style method name)."""
        self.set_value(value)

    def setRange(self, minimum, maximum):
        """Set the minimum and maximum values."""
        self.minimum = minimum
        self.maximum = maximum
        # Ensure current value is within new range
        self.set_value(max(minimum, min(self._value, maximum)))

    def setSuffix(self, suffix):
        """Set the suffix text."""
        self.suffix = suffix
        self.value_label.setText(str(self._value) + self.suffix)


logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """
    Settings dialog for configuring application settings.

    Features:
    - API credentials configuration
    - Station settings
    - Display preferences
    - Refresh settings
    """

    # Signal emitted when settings are saved
    settings_saved = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize the settings dialog.

        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        # Make dialog completely invisible during initialization
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)

        self.config_manager = config_manager
        self.config: Optional[ConfigData] = None

        # Create theme manager instance
        self.theme_manager = ThemeManager()

        # Load current configuration
        try:
            self.config = self.config_manager.load_config()
        except ConfigurationError as e:
            logger.error(f"Failed to load config in settings dialog: {e}")
            self.config = None

        self.setup_ui()
        self.load_current_settings()

        # Apply theme styling
        self.apply_theme_styling()

        # Don't show here - let exec() handle it when called

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Settings - Trainer by Oliver Ernster")
        self.setModal(True)
        self.setMinimumSize(800, 550)
        self.resize(850, 580)

        # Center the dialog on screen
        from PySide6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - 850) // 2
        y = (screen.height() - 580) // 2
        self.move(x, y)

        # Main layout
        layout = QVBoxLayout(self)

        # Tab widget for different setting categories
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Setup tabs
        self.setup_api_tab()
        self.setup_nasa_tab()
        self.setup_stations_tab()
        self.setup_display_tab()
        self.setup_refresh_tab()

        # Button layout
        button_layout = QHBoxLayout()

        self.test_button = QPushButton("Test Transport API")
        self.test_button.clicked.connect(self.test_api_connection)

        self.test_nasa_button = QPushButton("Test NASA API")
        self.test_nasa_button.clicked.connect(self.test_nasa_api_connection)

        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setDefault(True)

        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.test_nasa_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def setup_api_tab(self):
        """Setup API configuration tab."""
        api_widget = QWidget()
        layout = QVBoxLayout(api_widget)

        # API Credentials Group
        api_group = QGroupBox("Transport API Credentials")
        api_form = QFormLayout(api_group)

        # Info label
        info_label = QLabel(
            "Get your API credentials from https://transportapi.com/\n"
            "Sign up for a free account to get your App ID and App Key."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "color: #cccccc; font-style: italic; background: transparent;"
        )
        api_form.addRow(info_label)

        # App ID
        self.app_id_edit = QLineEdit()
        self.app_id_edit.setPlaceholderText("Enter your Transport API App ID")
        api_form.addRow("App ID:", self.app_id_edit)

        # App Key with show/hide button
        self.app_key_edit = QLineEdit()
        self.app_key_edit.setPlaceholderText("Enter your Transport API App Key")
        self.app_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.show_key_button = QPushButton("Show Key")
        self.show_key_button.setMinimumWidth(120)
        self.show_key_button.setMaximumWidth(120)
        self.show_key_button.clicked.connect(self.toggle_key_visibility)

        key_layout = QHBoxLayout()
        key_layout.addWidget(self.app_key_edit)
        key_layout.addWidget(self.show_key_button)
        api_form.addRow("App Key:", key_layout)

        # API Settings Group
        settings_group = QGroupBox("API Settings")
        settings_form = QFormLayout(settings_group)

        self.timeout_spin = HorizontalSpinWidget(
            5, 60, 10, 1, " seconds", theme_manager=self.theme_manager
        )
        settings_form.addRow("Timeout:", self.timeout_spin)

        self.retries_spin = HorizontalSpinWidget(
            1, 10, 3, 1, theme_manager=self.theme_manager
        )
        settings_form.addRow("Max Retries:", self.retries_spin)

        self.rate_limit_spin = HorizontalSpinWidget(
            10, 100, 30, 1, " per minute", theme_manager=self.theme_manager
        )
        settings_form.addRow("Rate Limit:", self.rate_limit_spin)

        layout.addWidget(api_group)
        layout.addWidget(settings_group)

        self.tab_widget.addTab(api_widget, "Transport API")

    def setup_nasa_tab(self):
        """Setup NASA API configuration tab."""
        nasa_widget = QWidget()
        main_layout = QHBoxLayout(
            nasa_widget
        )  # Use horizontal layout for better space usage

        # Left column
        left_column = QVBoxLayout()

        # NASA API Credentials Group
        nasa_group = QGroupBox("NASA API Configuration")
        nasa_form = QFormLayout(nasa_group)

        # Compact info label
        info_label = QLabel("Get your NASA API key from https://api.nasa.gov/")
        info_label.setStyleSheet(
            "color: #cccccc; font-style: italic; background: transparent;"
        )
        nasa_form.addRow(info_label)

        # NASA API Key
        self.nasa_api_key_edit = QLineEdit()
        self.nasa_api_key_edit.setPlaceholderText("Enter your NASA API key")
        self.nasa_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.show_nasa_key_button = QPushButton("Show")
        self.show_nasa_key_button.setFixedWidth(120)
        self.show_nasa_key_button.clicked.connect(self.toggle_nasa_key_visibility)

        nasa_key_layout = QHBoxLayout()
        nasa_key_layout.addWidget(self.nasa_api_key_edit)
        nasa_key_layout.addWidget(self.show_nasa_key_button)
        nasa_form.addRow("API Key:", nasa_key_layout)

        # Astronomy Settings Group
        astronomy_group = QGroupBox("Location & Settings")
        astronomy_form = QFormLayout(astronomy_group)

        # Enable astronomy
        self.astronomy_enabled_check = QCheckBox("Enable astronomy integration")
        astronomy_form.addRow("", self.astronomy_enabled_check)

        # Location settings in compact form
        self.astronomy_location_edit = QLineEdit()
        self.astronomy_location_edit.setPlaceholderText("London")
        self.astronomy_location_edit.setText("London")
        astronomy_form.addRow("Location:", self.astronomy_location_edit)

        # Coordinates in one row
        coords_layout = QHBoxLayout()
        self.astronomy_latitude_edit = QLineEdit()
        self.astronomy_latitude_edit.setPlaceholderText("51.5074")
        self.astronomy_latitude_edit.setText("51.5074")
        self.astronomy_latitude_edit.setFixedWidth(100)

        self.astronomy_longitude_edit = QLineEdit()
        self.astronomy_longitude_edit.setPlaceholderText("-0.1278")
        self.astronomy_longitude_edit.setText("-0.1278")
        self.astronomy_longitude_edit.setFixedWidth(100)

        coords_layout.addWidget(QLabel("Lat:"))
        coords_layout.addWidget(self.astronomy_latitude_edit)
        coords_layout.addWidget(QLabel("Lng:"))
        coords_layout.addWidget(self.astronomy_longitude_edit)
        coords_layout.addStretch()
        astronomy_form.addRow("Coordinates:", coords_layout)

        # Update interval
        self.astronomy_update_interval_spin = HorizontalSpinWidget(
            60, 1440, 360, 60, " min", theme_manager=self.theme_manager
        )
        astronomy_form.addRow("Update Interval:", self.astronomy_update_interval_spin)

        left_column.addWidget(nasa_group)
        left_column.addWidget(astronomy_group)

        # Right column - NASA Services
        right_column = QVBoxLayout()

        services_group = QGroupBox("NASA Services")
        services_layout = QVBoxLayout(services_group)

        self.apod_service_check = QCheckBox("Astronomy Picture of the Day")
        self.apod_service_check.setChecked(True)
        services_layout.addWidget(self.apod_service_check)

        self.neows_service_check = QCheckBox("Near Earth Objects")
        self.neows_service_check.setChecked(True)
        services_layout.addWidget(self.neows_service_check)

        self.iss_service_check = QCheckBox("International Space Station")
        self.iss_service_check.setChecked(True)
        services_layout.addWidget(self.iss_service_check)

        self.epic_service_check = QCheckBox("Earth Imaging Camera")
        self.epic_service_check.setChecked(False)
        services_layout.addWidget(self.epic_service_check)

        right_column.addWidget(services_group)
        right_column.addStretch()

        # Add columns to main layout
        main_layout.addLayout(left_column)
        main_layout.addLayout(right_column)

        self.tab_widget.addTab(nasa_widget, "NASA API")

    def setup_stations_tab(self):
        """Setup station configuration tab."""
        stations_widget = QWidget()
        layout = QVBoxLayout(stations_widget)

        stations_group = QGroupBox("Station Configuration")
        form = QFormLayout(stations_group)

        # From station
        self.from_code_edit = QLineEdit()
        self.from_code_edit.setPlaceholderText("e.g., FLE")
        self.from_code_edit.setMaximumWidth(100)
        form.addRow("From Code:", self.from_code_edit)

        self.from_name_edit = QLineEdit()
        self.from_name_edit.setPlaceholderText("e.g., Fleet")
        form.addRow("From Name:", self.from_name_edit)

        # To station
        self.to_code_edit = QLineEdit()
        self.to_code_edit.setPlaceholderText("e.g., WAT")
        self.to_code_edit.setMaximumWidth(100)
        form.addRow("To Code:", self.to_code_edit)

        self.to_name_edit = QLineEdit()
        self.to_name_edit.setPlaceholderText("e.g., London Waterloo")
        form.addRow("To Name:", self.to_name_edit)

        layout.addWidget(stations_group)

        self.tab_widget.addTab(stations_widget, "Stations")

    def setup_display_tab(self):
        """Setup display configuration tab."""
        display_widget = QWidget()
        layout = QVBoxLayout(display_widget)

        display_group = QGroupBox("Display Settings")
        form = QFormLayout(display_group)

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        form.addRow("Theme:", self.theme_combo)

        # Max trains
        self.max_trains_spin = HorizontalSpinWidget(
            10, 100, 50, 1, theme_manager=self.theme_manager
        )
        form.addRow("Max Trains:", self.max_trains_spin)

        # Time window
        self.time_window_spin = HorizontalSpinWidget(
            1, 24, 10, 1, " hours", theme_manager=self.theme_manager
        )
        form.addRow("Time Window:", self.time_window_spin)

        # Show cancelled
        self.show_cancelled_check = QCheckBox("Show cancelled trains")
        form.addRow("", self.show_cancelled_check)

        layout.addWidget(display_group)

        self.tab_widget.addTab(display_widget, "Display")

    def setup_refresh_tab(self):
        """Setup refresh configuration tab."""
        refresh_widget = QWidget()
        layout = QVBoxLayout(refresh_widget)

        refresh_group = QGroupBox("Refresh Settings")
        form = QFormLayout(refresh_group)

        # Auto refresh
        self.auto_refresh_check = QCheckBox("Enable auto-refresh")
        form.addRow("", self.auto_refresh_check)

        # Refresh interval
        self.refresh_interval_spin = HorizontalSpinWidget(
            1, 60, 2, 1, " minutes", theme_manager=self.theme_manager
        )
        form.addRow("Refresh Interval:", self.refresh_interval_spin)

        # Manual refresh
        self.manual_refresh_check = QCheckBox("Enable manual refresh")
        form.addRow("", self.manual_refresh_check)

        layout.addWidget(refresh_group)

        self.tab_widget.addTab(refresh_widget, "Refresh")

    def load_current_settings(self):
        """Load current settings into the dialog."""
        if not self.config:
            return

        # API settings
        self.app_id_edit.setText(self.config.api.app_id)
        self.app_key_edit.setText(self.config.api.app_key)
        self.timeout_spin.set_value(self.config.api.timeout_seconds)
        self.retries_spin.set_value(self.config.api.max_retries)
        self.rate_limit_spin.set_value(self.config.api.rate_limit_per_minute)

        # Station settings
        self.from_code_edit.setText(self.config.stations.from_code)
        self.from_name_edit.setText(self.config.stations.from_name)
        self.to_code_edit.setText(self.config.stations.to_code)
        self.to_name_edit.setText(self.config.stations.to_name)

        # Display settings
        theme_index = self.theme_combo.findText(self.config.display.theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
        self.max_trains_spin.set_value(self.config.display.max_trains)
        self.time_window_spin.set_value(self.config.display.time_window_hours)
        self.show_cancelled_check.setChecked(self.config.display.show_cancelled)

        # Refresh settings
        self.auto_refresh_check.setChecked(self.config.refresh.auto_enabled)
        self.refresh_interval_spin.set_value(self.config.refresh.interval_minutes)
        self.manual_refresh_check.setChecked(self.config.refresh.manual_enabled)

        # NASA/Astronomy settings (load defaults if not present)
        if self.config.astronomy:
            astronomy_config = self.config.astronomy
        else:
            # Create default astronomy config if not present
            astronomy_config = AstronomyConfig.create_default()

        self.nasa_api_key_edit.setText(astronomy_config.nasa_api_key)
        self.astronomy_enabled_check.setChecked(astronomy_config.enabled)
        self.astronomy_location_edit.setText(astronomy_config.location_name)
        self.astronomy_latitude_edit.setText(str(astronomy_config.location_latitude))
        self.astronomy_longitude_edit.setText(str(astronomy_config.location_longitude))
        self.astronomy_update_interval_spin.set_value(
            astronomy_config.update_interval_minutes
        )

        # NASA services
        self.apod_service_check.setChecked(astronomy_config.services.apod)
        self.neows_service_check.setChecked(astronomy_config.services.neows)
        self.iss_service_check.setChecked(astronomy_config.services.iss)
        self.epic_service_check.setChecked(astronomy_config.services.epic)

    def toggle_key_visibility(self):
        """Toggle API key visibility."""
        if self.app_key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.app_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_button.setText("Hide Key")
        else:
            self.app_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_button.setText("Show Key")

    def toggle_nasa_key_visibility(self):
        """Toggle NASA API key visibility."""
        if self.nasa_api_key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.nasa_api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_nasa_key_button.setText("Hide Key")
        else:
            self.nasa_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_nasa_key_button.setText("Show Key")

    def test_api_connection(self):
        """Test API connection with current credentials."""
        app_id = self.app_id_edit.text().strip()
        app_key = self.app_key_edit.text().strip()

        if not app_id or not app_key:
            QMessageBox.warning(
                self,
                "Missing Credentials",
                "Please enter both App ID and App Key before testing.",
            )
            return

        # Create a test configuration with current values
        if self.config:
            # Copy existing config
            test_config = self.config.model_copy()
        else:
            # Create default config if none exists
            from ..managers.config_manager import (
                APIConfig,
                StationConfig,
                RefreshConfig,
                DisplayConfig,
            )

            test_config = ConfigData(
                api=APIConfig(app_id="", app_key=""),
                stations=StationConfig(),
                refresh=RefreshConfig(),
                display=DisplayConfig(),
            )

        # Update with current form values
        test_config.api.app_id = app_id
        test_config.api.app_key = app_key
        test_config.api.timeout_seconds = self.timeout_spin.value()
        test_config.api.max_retries = self.retries_spin.value()
        test_config.api.rate_limit_per_minute = self.rate_limit_spin.value()

        # Use current station settings or defaults
        if not test_config.stations.from_code:
            test_config.stations.from_code = "FLE"  # Fleet as default
        if not test_config.stations.to_code:
            test_config.stations.to_code = "WAT"  # Waterloo as default

        # Start the API test in a separate thread
        self.api_test_thread = APITestThread(test_config)
        self.api_test_thread.test_completed.connect(self.on_api_test_completed)
        self.api_test_thread.start()

        # Show progress dialog
        self.progress_dialog = QProgressDialog(
            "Testing API connection...", "Cancel", 0, 0, self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.canceled.connect(self.cancel_api_test)
        self.progress_dialog.show()

    def cancel_api_test(self):
        """Cancel the API test."""
        if hasattr(self, "api_test_thread") and self.api_test_thread.isRunning():
            self.api_test_thread.terminate()
            self.api_test_thread.wait()

    def on_api_test_completed(self, success: bool, message: str):
        """Handle API test completion."""
        if hasattr(self, "progress_dialog"):
            self.progress_dialog.close()

        if success:
            QMessageBox.information(
                self, "API Test Successful", f"API connection test passed!\n\n{message}"
            )
        else:
            QMessageBox.critical(
                self, "API Test Failed", f"API connection test failed:\n\n{message}"
            )

    def test_nasa_api_connection(self):
        """Test NASA API connection with current credentials."""
        nasa_api_key = self.nasa_api_key_edit.text().strip()

        if not nasa_api_key:
            QMessageBox.warning(
                self,
                "Missing NASA API Key",
                "Please enter your NASA API key before testing.",
            )
            return

        # Start the NASA API test in a separate thread
        self.nasa_test_thread = NASATestThread(nasa_api_key)
        self.nasa_test_thread.test_completed.connect(self.on_nasa_test_completed)
        self.nasa_test_thread.start()

        # Show progress dialog
        self.nasa_progress_dialog = QProgressDialog(
            "Testing NASA API connection...", "Cancel", 0, 0, self
        )
        self.nasa_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.nasa_progress_dialog.setMinimumDuration(0)
        self.nasa_progress_dialog.canceled.connect(self.cancel_nasa_test)
        self.nasa_progress_dialog.show()

    def cancel_nasa_test(self):
        """Cancel the NASA API test."""
        if hasattr(self, "nasa_test_thread") and self.nasa_test_thread.isRunning():
            self.nasa_test_thread.terminate()
            self.nasa_test_thread.wait()

    def on_nasa_test_completed(self, success: bool, message: str):
        """Handle NASA API test completion."""
        if hasattr(self, "nasa_progress_dialog"):
            self.nasa_progress_dialog.close()

        if success:
            QMessageBox.information(
                self,
                "NASA API Test Successful",
                f"NASA API connection test passed!\n\n{message}",
            )
        else:
            QMessageBox.critical(
                self,
                "NASA API Test Failed",
                f"NASA API connection test failed:\n\n{message}",
            )

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n"
            "This will overwrite your current configuration.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.config_manager.create_default_config()
                self.config = self.config_manager.load_config()
                self.load_current_settings()
                QMessageBox.information(
                    self, "Settings Reset", "Settings have been reset to defaults."
                )
            except ConfigurationError as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings: {e}")

    def save_settings(self):
        """Save current settings."""
        if not self.config:
            QMessageBox.critical(
                self, "Error", "No configuration loaded. Cannot save settings."
            )
            return

        try:
            # Update configuration with current values
            self.config.api.app_id = self.app_id_edit.text().strip()
            self.config.api.app_key = self.app_key_edit.text().strip()
            self.config.api.timeout_seconds = self.timeout_spin.value()
            self.config.api.max_retries = self.retries_spin.value()
            self.config.api.rate_limit_per_minute = self.rate_limit_spin.value()

            self.config.stations.from_code = self.from_code_edit.text().strip()
            self.config.stations.from_name = self.from_name_edit.text().strip()
            self.config.stations.to_code = self.to_code_edit.text().strip()
            self.config.stations.to_name = self.to_name_edit.text().strip()

            self.config.display.theme = self.theme_combo.currentText()
            self.config.display.max_trains = self.max_trains_spin.value()
            self.config.display.time_window_hours = self.time_window_spin.value()
            self.config.display.show_cancelled = self.show_cancelled_check.isChecked()

            self.config.refresh.auto_enabled = self.auto_refresh_check.isChecked()
            self.config.refresh.interval_minutes = self.refresh_interval_spin.value()
            self.config.refresh.manual_enabled = self.manual_refresh_check.isChecked()

            # NASA/Astronomy settings
            if not self.config.astronomy:
                self.config.astronomy = AstronomyConfig.create_default()

            # Update astronomy configuration
            try:
                latitude = float(self.astronomy_latitude_edit.text())
                longitude = float(self.astronomy_longitude_edit.text())
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Invalid Coordinates",
                    "Please enter valid latitude and longitude values.",
                )
                return

            # Create updated astronomy config
            from ..managers.astronomy_config import AstronomyServiceConfig

            services = AstronomyServiceConfig(
                apod=self.apod_service_check.isChecked(),
                neows=self.neows_service_check.isChecked(),
                iss=self.iss_service_check.isChecked(),
                epic=self.epic_service_check.isChecked(),
            )

            self.config.astronomy = AstronomyConfig(
                enabled=self.astronomy_enabled_check.isChecked(),
                nasa_api_key=self.nasa_api_key_edit.text().strip(),
                location_name=self.astronomy_location_edit.text().strip(),
                location_latitude=latitude,
                location_longitude=longitude,
                update_interval_minutes=self.astronomy_update_interval_spin.value(),
                timeout_seconds=self.config.astronomy.timeout_seconds,
                max_retries=self.config.astronomy.max_retries,
                retry_delay_seconds=self.config.astronomy.retry_delay_seconds,
                services=services,
                display=self.config.astronomy.display,
                cache=self.config.astronomy.cache,
            )

            # Save configuration
            self.config_manager.save_config(self.config)

            # Emit signal and close dialog
            self.settings_saved.emit()
            self.accept()

            QMessageBox.information(
                self, "Settings Saved", "Settings have been saved successfully."
            )

        except ConfigurationError as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}")
        except Exception as e:
            QMessageBox.critical(
                self, "Unexpected Error", f"An unexpected error occurred: {e}"
            )

    def apply_theme_styling(self):
        """Apply theme styling to the settings dialog."""
        if not self.theme_manager:
            return

        # Get current theme
        current_theme = self.theme_manager.current_theme

        # Apply dark theme styling to the dialog
        if current_theme == "dark":
            dialog_style = """
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #404040;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #4fc3f7;
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                color: #4fc3f7;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #4fc3f7;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #4fc3f7;
                border: 1px solid #4fc3f7;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff;
            }
            QComboBox:focus {
                border-color: #4fc3f7;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 6px 12px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #404040;
                border-color: #4fc3f7;
            }
            QPushButton:pressed {
                background-color: #4fc3f7;
            }
            QLabel {
                color: #ffffff;
            }
            """
        else:
            # Light theme styling
            dialog_style = """
            QDialog {
                background-color: #ffffff;
                color: #000000;
            }
            """

        self.setStyleSheet(dialog_style)

    def exec(self):
        """Override exec to show dialog only when fully ready."""
        # Remove the invisible attributes and show the dialog now that everything is ready
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        self.setVisible(True)
        self.show()
        # Call parent exec
        return super().exec()


class APITestThread(QThread):
    """Thread for testing API connection without blocking the UI."""

    test_completed = Signal(bool, str)  # success, message

    def __init__(self, config: ConfigData):
        super().__init__()
        self.config = config

    def run(self):
        """Run the API test in a separate thread."""
        loop = None
        try:
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the async API test
            success, message = loop.run_until_complete(self._test_api())

            self.test_completed.emit(success, message)

        except Exception as e:
            self.test_completed.emit(False, f"Test failed with error: {str(e)}")
        finally:
            # Always clean up the loop
            if loop is not None:
                loop.close()

    async def _test_api(self) -> tuple[bool, str]:
        """Perform the actual API test."""
        try:
            async with APIManager(self.config) as api_manager:
                # Try to fetch departures as a test
                trains = await api_manager.get_departures()

                if trains:
                    return (
                        True,
                        f"Successfully connected to API and retrieved {len(trains)} train departures.",
                    )
                else:
                    return (
                        True,
                        "Successfully connected to API, but no train data was returned. This may be normal depending on the time and route.",
                    )

        except AuthenticationException as e:
            return (
                False,
                f"Authentication failed: {str(e)}\n\nPlease check your App ID and App Key.",
            )
        except NetworkException as e:
            return (
                False,
                f"Network error: {str(e)}\n\nPlease check your internet connection.",
            )
        except APIException as e:
            return False, f"API error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"


class NASATestThread(QThread):
    """Thread for testing NASA API connection without blocking the UI."""

    test_completed = Signal(bool, str)  # success, message

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def run(self):
        """Run the NASA API test in a separate thread."""
        loop = None
        try:
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the async NASA API test
            success, message = loop.run_until_complete(self._test_nasa_api())

            self.test_completed.emit(success, message)

        except Exception as e:
            self.test_completed.emit(False, f"Test failed with error: {str(e)}")
        finally:
            # Always clean up the loop
            if loop is not None:
                loop.close()

    async def _test_nasa_api(self) -> tuple[bool, str]:
        """Perform the actual NASA API test."""
        import aiohttp

        try:
            # Test NASA APOD API endpoint
            url = f"https://api.nasa.gov/planetary/apod?api_key={self.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        title = data.get("title", "Unknown")
                        date = data.get("date", "Unknown")
                        return (
                            True,
                            f"Successfully connected to NASA API!\n\n"
                            f"Today's Astronomy Picture: {title}\n"
                            f"Date: {date}\n\n"
                            f"API Key: {self.api_key[:8]}{'*' * (len(self.api_key) - 8)}",
                        )
                    elif response.status == 403:
                        return (
                            False,
                            f"Authentication failed (HTTP 403).\n\n"
                            f"Your NASA API key may be invalid or has exceeded its rate limit.\n"
                            f"Please verify your API key at https://api.nasa.gov/\n\n"
                            f"Key: {self.api_key[:8]}{'*' * (len(self.api_key) - 8)}",
                        )
                    elif response.status == 429:
                        return (
                            False,
                            f"Rate limit exceeded (HTTP 429).\n\n"
                            f"Your NASA API key has exceeded its hourly rate limit.\n"
                            f"Please wait and try again later.\n\n"
                            f"Key: {self.api_key[:8]}{'*' * (len(self.api_key) - 8)}",
                        )
                    else:
                        error_text = await response.text()
                        return (
                            False,
                            f"NASA API returned HTTP {response.status}.\n\n"
                            f"Response: {error_text[:200]}...\n\n"
                            f"Please check your API key and try again.",
                        )

        except aiohttp.ClientError as e:
            return (
                False,
                f"Network error connecting to NASA API: {str(e)}\n\n"
                f"Please check your internet connection and try again.",
            )
        except asyncio.TimeoutError:
            return (
                False,
                f"Connection to NASA API timed out.\n\n"
                f"Please check your internet connection and try again.",
            )
        except Exception as e:
            return False, f"Unexpected error testing NASA API: {str(e)}"
