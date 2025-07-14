"""
Astronomy settings dialog for the Train Times application.
Author: Oliver Ernster

This module provides a dialog for configuring astronomy widget preferences
in the API-free astronomy system.
"""

import logging
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
    QCheckBox,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ..managers.config_manager import ConfigManager, ConfigData, ConfigurationError
from ..managers.theme_manager import ThemeManager
from ..managers.astronomy_config import AstronomyConfig
from ..services.geocoding_service import get_city_coordinates
# Use a direct title since __astronomy_settings_title__ may not exist
ASTRONOMY_SETTINGS_TITLE = "Astronomy Settings"

logger = logging.getLogger(__name__)


class AstronomySettingsDialog(QDialog):
    """
    Astronomy settings dialog for configuring astronomy widget preferences.

    Features:
    - Location settings for astronomical calculations
    - Link category preferences
    - Display options
    - API-free astronomy configuration
    """

    # Signal emitted when settings are saved
    settings_saved = Signal()
    # Signal emitted when astronomy should be enabled
    astronomy_enable_requested = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None, theme_manager=None):
        """
        Initialize the astronomy settings dialog.

        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
            theme_manager: Shared theme manager instance
        """
        super().__init__(parent)

        # Make dialog completely invisible during initialization
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)

        self.config_manager = config_manager
        self.config: Optional[ConfigData] = None

        # Use shared theme manager or create new one
        self.theme_manager = theme_manager or ThemeManager()

        # Load current configuration
        try:
            self.config = self.config_manager.load_config()
        except ConfigurationError as e:
            logger.error(f"Failed to load config in astronomy settings dialog: {e}")
            self.config = None

        self.setup_ui()
        self.load_current_settings()

        # Apply theme styling
        self.apply_theme_styling()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle(ASTRONOMY_SETTINGS_TITLE)
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.resize(750, 550)

        # Center the dialog on screen
        from PySide6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - 750) // 2
        y = (screen.height() - 550) // 2
        self.move(x, y)

        # Main layout
        layout = QVBoxLayout(self)

        # Setup astronomy content
        self.setup_astronomy_content(layout)

        # Bottom button layout
        button_layout = QHBoxLayout()

        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setDefault(True)

        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def setup_astronomy_content(self, layout):
        """Setup astronomy configuration content."""
        main_layout = QHBoxLayout()

        # Left column - Location Settings
        left_column = QVBoxLayout()

        # Location Settings Group
        location_group = QGroupBox("Location Settings")
        location_form = QFormLayout(location_group)

        # Info label
        info_label = QLabel("Configure your location for accurate astronomical calculations and moon phases.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-style: italic; margin-bottom: 10px;")
        location_form.addRow(info_label)

        # Location settings
        location_layout = QHBoxLayout()
        self.astronomy_location_edit = QLineEdit()
        self.astronomy_location_edit.setPlaceholderText("London")
        self.astronomy_location_edit.setText("London")
        
        self.lookup_coordinates_button = QPushButton("Lookup")
        self.lookup_coordinates_button.setFixedWidth(80)
        self.lookup_coordinates_button.clicked.connect(self.lookup_coordinates)
        
        location_layout.addWidget(self.astronomy_location_edit)
        location_layout.addWidget(self.lookup_coordinates_button)
        location_form.addRow("City:", location_layout)

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
        location_form.addRow("Coordinates:", coords_layout)

        left_column.addWidget(location_group)
        left_column.addStretch()

        # Right column - Link Categories
        right_column = QVBoxLayout()

        categories_group = QGroupBox("Astronomy Link Categories")
        categories_layout = QVBoxLayout(categories_group)

        # Info label for categories
        categories_info = QLabel("Select which types of astronomy links to display in the widget:")
        categories_info.setWordWrap(True)
        categories_info.setStyleSheet("color: #666666; font-style: italic; margin-bottom: 10px;")
        categories_layout.addWidget(categories_info)

        # Link category checkboxes with explicit text setting
        self.observatory_check = QCheckBox()
        self.observatory_check.setText("🔭 Observatories (Hubble, James Webb, ESO)")
        self.observatory_check.setChecked(True)
        categories_layout.addWidget(self.observatory_check)

        self.space_agency_check = QCheckBox()
        self.space_agency_check.setText("🚀 Space Agencies (NASA, ESA, SpaceX)")
        self.space_agency_check.setChecked(True)
        categories_layout.addWidget(self.space_agency_check)


        self.tonight_sky_check = QCheckBox()
        self.tonight_sky_check.setText("🌌 Tonight's Sky (Sky maps, visibility)")
        self.tonight_sky_check.setChecked(True)
        categories_layout.addWidget(self.tonight_sky_check)

        self.educational_check = QCheckBox()
        self.educational_check.setText("📚 Educational Resources")
        self.educational_check.setChecked(False)
        categories_layout.addWidget(self.educational_check)

        self.live_data_check = QCheckBox()
        self.live_data_check.setText("📡 Live Data Feeds")
        self.live_data_check.setChecked(False)
        categories_layout.addWidget(self.live_data_check)

        self.community_check = QCheckBox()
        self.community_check.setText("👥 Community & Forums")
        self.community_check.setChecked(False)
        categories_layout.addWidget(self.community_check)

        right_column.addWidget(categories_group)

        # Add columns to main layout
        main_layout.addLayout(left_column)
        main_layout.addLayout(right_column)

        layout.addLayout(main_layout)

    def lookup_coordinates(self):
        """Lookup coordinates for the entered city name."""
        city_name = self.astronomy_location_edit.text().strip()
        
        if not city_name:
            QMessageBox.warning(
                self,
                "Missing City Name",
                "Please enter a city name before looking up coordinates.",
            )
            return
        
        # Check predefined coordinates
        coords = get_city_coordinates(city_name)
        if coords:
            lat, lon = coords
            self.astronomy_latitude_edit.setText(f"{lat:.4f}")
            self.astronomy_longitude_edit.setText(f"{lon:.4f}")
            QMessageBox.information(
                self,
                "Coordinates Found",
                f"Found coordinates for {city_name}:\n"
                f"Latitude: {lat:.4f}\n"
                f"Longitude: {lon:.4f}",
            )
        else:
            QMessageBox.warning(
                self,
                "City Not Found",
                f"Could not find coordinates for '{city_name}'.\n\n"
                f"Please enter coordinates manually or try a different city name.",
            )

    def load_current_settings(self):
        """Load current settings into the dialog."""
        if not self.config:
            return

        # Astronomy settings (load defaults if not present)
        if self.config.astronomy:
            astronomy_config = self.config.astronomy
        else:
            # Create default astronomy config if not present
            astronomy_config = AstronomyConfig.create_default()

        self.astronomy_location_edit.setText(astronomy_config.location_name)
        self.astronomy_latitude_edit.setText(str(astronomy_config.location_latitude))
        self.astronomy_longitude_edit.setText(str(astronomy_config.location_longitude))

        # Load enabled link categories
        enabled_categories = astronomy_config.enabled_link_categories
        self.observatory_check.setChecked("observatory" in enabled_categories)
        self.space_agency_check.setChecked("space_agency" in enabled_categories)
        self.tonight_sky_check.setChecked("tonight_sky" in enabled_categories)
        self.educational_check.setChecked("educational" in enabled_categories)
        self.live_data_check.setChecked("live_data" in enabled_categories)
        self.community_check.setChecked("community" in enabled_categories)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all astronomy settings to defaults?\n"
            "This will overwrite your current astronomy configuration.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset to default astronomy config
                default_config = AstronomyConfig.create_default()
                if self.config and not self.config.astronomy:
                    self.config.astronomy = default_config
                elif self.config and self.config.astronomy:
                    # Update existing config with defaults
                    self.config.astronomy.location_name = default_config.location_name
                    self.config.astronomy.location_latitude = default_config.location_latitude
                    self.config.astronomy.location_longitude = default_config.location_longitude
                    self.config.astronomy.enabled_link_categories = default_config.enabled_link_categories

                self.load_current_settings()
                QMessageBox.information(
                    self, "Settings Reset", "Astronomy settings have been reset to defaults."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings: {e}")

    def save_settings(self):
        """Save current settings."""
        if not self.config:
            QMessageBox.critical(
                self, "Error", "No configuration loaded. Cannot save settings."
            )
            return

        try:
            # Validate coordinates
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

            # Validate coordinate ranges
            if not (-90 <= latitude <= 90):
                QMessageBox.warning(
                    self,
                    "Invalid Latitude",
                    "Latitude must be between -90 and 90 degrees.",
                )
                return

            if not (-180 <= longitude <= 180):
                QMessageBox.warning(
                    self,
                    "Invalid Longitude",
                    "Longitude must be between -180 and 180 degrees.",
                )
                return

            # Create enabled link categories list
            enabled_categories = []
            if self.observatory_check.isChecked():
                enabled_categories.append("observatory")
            if self.space_agency_check.isChecked():
                enabled_categories.append("space_agency")
            if self.tonight_sky_check.isChecked():
                enabled_categories.append("tonight_sky")
            if self.educational_check.isChecked():
                enabled_categories.append("educational")
            if self.live_data_check.isChecked():
                enabled_categories.append("live_data")
            if self.community_check.isChecked():
                enabled_categories.append("community")

            # Ensure at least one category is enabled
            if not enabled_categories:
                QMessageBox.warning(
                    self,
                    "No Categories Selected",
                    "Please select at least one link category to enable.",
                )
                return

            # Create or update astronomy configuration
            if not self.config.astronomy:
                self.config.astronomy = AstronomyConfig.create_default()

            # Update astronomy configuration
            self.config.astronomy = AstronomyConfig(
                enabled=self.config.astronomy.enabled,  # Preserve current enabled state
                location_name=self.astronomy_location_edit.text().strip(),
                location_latitude=latitude,
                location_longitude=longitude,
                timezone=self.config.astronomy.timezone,
                display=self.config.astronomy.display,
                cache=self.config.astronomy.cache,
                enabled_link_categories=enabled_categories,
            )

            # Save configuration
            self.config_manager.save_config(self.config)

            # Close dialog immediately
            self.accept()
            
            # Emit signal to refresh main UI after dialog is closed
            self.settings_saved.emit()

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

        if current_theme == "light":
            # Light theme styling
            dialog_style = """
            QDialog {
                background-color: #ffffff;
                color: #1976d2;
            }
            QGroupBox {
                color: #1976d2;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                color: #1976d2;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background-color: #ffffff;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
                color: #1976d2;
            }
            QLineEdit:focus {
                border-color: #1976d2;
            }
            QCheckBox {
                color: #1976d2;
                background-color: #ffffff;
                spacing: 5px;
                font-size: 12px;
            }
            QCheckBox::text {
                color: #1976d2;
            }
            QCheckBox::indicator {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                border: 1px solid #1976d2;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                color: #1976d2;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
            QLabel {
                color: #1976d2;
                background-color: transparent;
            }
            """
        else:
            # Dark theme styling
            dialog_style = """
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #1a1a1a;
            }
            QGroupBox::title {
                color: #1976d2;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background-color: #1a1a1a;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #1976d2;
            }
            QCheckBox {
                color: #ffffff;
                background-color: #1a1a1a;
                spacing: 5px;
                font-size: 12px;
                padding: 2px;
            }
            QCheckBox::text {
                color: #ffffff;
                padding-left: 5px;
            }
            QCheckBox::indicator {
                background-color: #2d2d2d;
                border: 1px solid #404040;
            }
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                border: 1px solid #1976d2;
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
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            """

        self.setStyleSheet(dialog_style)

    def exec(self):
        """Override exec to show dialog only when fully ready."""
        # Reload current settings every time the dialog is opened
        try:
            self.config = self.config_manager.load_config()
            self.load_current_settings()
            logger.debug(f"Astronomy settings dialog loaded config with categories: {self.config.astronomy.enabled_link_categories if self.config and self.config.astronomy else 'None'}")
        except ConfigurationError as e:
            logger.error(f"Failed to reload config in astronomy settings dialog: {e}")
        
        # Remove the invisible attributes and show the dialog now that everything is ready
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        self.setVisible(True)
        self.show()
        # Call parent exec
        return super().exec()