"""
Main window for the Train Times application.
Author: Oliver Ernster

This module contains the primary application window with theme switching,
menu bar, status bar, and train display area.
"""

import logging
from pathlib import Path
from typing import List, Optional
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
    QApplication,
)
from PySide6.QtCore import QTimer, Signal, Qt, QSize
from PySide6.QtGui import QAction, QIcon, QKeySequence
from ..models.train_data import TrainData
from ..managers.config_manager import ConfigManager, ConfigurationError
from ..managers.theme_manager import ThemeManager
from ..managers.weather_manager import WeatherManager
from .train_widgets import TrainListWidget
from .weather_widgets import WeatherWidget
from .settings_dialog import SettingsDialog
from version import __version__, __app_display_name__, get_about_text

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window with theme switching and train display.

    Features:
    - Light/Dark theme switching (defaults to dark)
    - Custom train icon from assets/train_icon.svg
    - Real-time train data display
    - 16-hour time window
    - Automatic and manual refresh
    """

    # Signals
    refresh_requested = Signal()
    theme_changed = Signal(str)
    auto_refresh_toggle_requested = Signal()

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the main window."""
        super().__init__()

        # Initialize managers
        self.config_manager = config_manager or ConfigManager()
        self.theme_manager = ThemeManager()

        # Install default config to AppData on first run
        self.config_manager.install_default_config_to_appdata()

        # Load configuration
        try:
            self.config = self.config_manager.load_config()
            # Set theme from config (defaults to dark)
            self.theme_manager.set_theme(self.config.display.theme)
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            self.show_error_message("Configuration Error", str(e))
            # Use default config
            self.config = None

        # UI components
        self.train_list_widget: Optional[TrainListWidget] = None
        self.weather_widget: Optional[WeatherWidget] = None
        self.last_update_label: Optional[QLabel] = None
        self.next_update_label: Optional[QLabel] = None
        self.time_window_label: Optional[QLabel] = None
        self.theme_button: Optional[QPushButton] = None
        self.refresh_button: Optional[QPushButton] = None
        self.connection_status: Optional[QLabel] = None
        self.train_count_label: Optional[QLabel] = None
        self.theme_status: Optional[QLabel] = None
        self.auto_refresh_status: Optional[QLabel] = None
        self.weather_status: Optional[QLabel] = None
        
        # Weather manager
        self.weather_manager: Optional[WeatherManager] = None

        # Setup UI
        self.setup_ui()
        self.setup_application_icon()
        self.setup_theme_system()
        self.setup_weather_system()
        self.apply_theme()
        self.connect_signals()

        logger.info("Main window initialized")

    def setup_ui(self):
        """Initialize UI components."""
        self.setWindowTitle(__app_display_name__)
        self.setMinimumSize(800, 900)  # Increased height for weather widgets
        self.resize(1000, 1000)  # Larger default size for weather integration

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        self.setup_header(layout)

        # Weather widget (always create, show/hide based on config)
        self.weather_widget = WeatherWidget()
        layout.addWidget(self.weather_widget)
        
        # Hide initially if weather is disabled
        if not (self.config and hasattr(self.config, 'weather') and self.config.weather and self.config.weather.enabled):
            self.weather_widget.hide()

        # Train list with extended capacity
        self.train_list_widget = TrainListWidget(max_trains=50)
        layout.addWidget(self.train_list_widget)

        # Status bar
        self.setup_status_bar()

        # Menu bar
        self.setup_menu_bar()

    def setup_application_icon(self):
        """Setup application icon from assets directory for window."""
        # Try PNG files first (better Windows compatibility)
        png_sizes = [16, 24, 32, 48, 64]
        icon = QIcon()
        png_found = False

        for size in png_sizes:
            png_path = Path(f"assets/train_icon_{size}.png")
            if png_path.exists():
                icon.addFile(str(png_path), QSize(size, size))
                png_found = True

        if png_found:
            # Set window icon (this also affects taskbar on Windows)
            self.setWindowIcon(icon)
            logger.info("Window icon loaded from PNG files with multiple sizes")
            return

        # Fallback to SVG if PNG files not available
        svg_path = Path("assets/train_icon.svg")
        if svg_path.exists():
            # Create QIcon with multiple sizes for better display
            icon = QIcon(str(svg_path))

            # Add multiple sizes for crisp display at different scales
            icon.addFile(str(svg_path), QSize(16, 16))
            icon.addFile(str(svg_path), QSize(24, 24))
            icon.addFile(str(svg_path), QSize(32, 32))
            icon.addFile(str(svg_path), QSize(48, 48))
            icon.addFile(str(svg_path), QSize(64, 64))

            # Set window icon (this also affects taskbar on Windows)
            self.setWindowIcon(icon)
            logger.info(
                "Window icon loaded from assets/train_icon.svg with multiple sizes"
            )
        else:
            # Fallback to Unicode train emoji in title
            self.setWindowTitle(f"🚂 {__app_display_name__}")
            logger.warning("No train icon files found, using Unicode fallback")

    def setup_header(self, layout):
        """Setup header section with theme toggle."""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)

        # Status labels
        self.last_update_label = QLabel("Last Updated: --:--:--")
        self.next_update_label = QLabel("Next Update: --")
        self.time_window_label = QLabel("Showing trains for next 16 hours")

        # Control buttons
        self.theme_button = QPushButton(self.theme_manager.get_theme_icon())
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setToolTip(self.theme_manager.get_theme_tooltip())
        self.theme_button.setFixedSize(32, 32)

        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.manual_refresh)
        self.refresh_button.setToolTip("Refresh train data (F5)")

        self.auto_refresh_button = QPushButton("⏸️ Auto-refresh")
        self.auto_refresh_button.clicked.connect(self.toggle_auto_refresh)
        self.auto_refresh_button.setToolTip("Toggle auto-refresh")
        self.auto_refresh_button.setFixedSize(120, 32)

        # Layout
        header_layout.addWidget(self.last_update_label)
        header_layout.addWidget(self.time_window_label)
        header_layout.addStretch()
        header_layout.addWidget(self.next_update_label)
        header_layout.addWidget(self.auto_refresh_button)
        header_layout.addWidget(self.theme_button)
        header_layout.addWidget(self.refresh_button)

        layout.addWidget(header_widget)

    def setup_status_bar(self):
        """Setup status bar with connection and theme info."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.connection_status = QLabel("Disconnected")
        self.train_count_label = QLabel("0 trains")
        self.theme_status = QLabel(f"Theme: {self.theme_manager.current_theme.title()}")
        self.auto_refresh_status = QLabel("Auto-refresh: OFF")
        self.weather_status = QLabel("Weather: OFF")

        self.status_bar.addWidget(self.connection_status)
        self.status_bar.addPermanentWidget(self.train_count_label)
        self.status_bar.addPermanentWidget(self.weather_status)
        self.status_bar.addPermanentWidget(self.theme_status)
        self.status_bar.addPermanentWidget(self.auto_refresh_status)

    def setup_menu_bar(self):
        """Setup application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.manual_refresh)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        options_action = QAction("Options...", self)
        options_action.setShortcut(QKeySequence("Ctrl+,"))
        options_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(options_action)

        # View menu
        view_menu = menubar.addMenu("View")

        self.theme_action = QAction("Switch Theme", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+T"))
        self.theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.theme_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def setup_theme_system(self):
        """Setup theme switching system."""
        # Connect theme change signal
        self.theme_manager.theme_changed.connect(self.on_theme_changed)
    
    def setup_weather_system(self):
        """Setup weather integration system."""
        if not self.config or not hasattr(self.config, 'weather') or not self.config.weather:
            logger.warning("Weather configuration not available")
            self.update_weather_status(False)
            return
        
        try:
            # Initialize weather manager (even if disabled, for potential later enabling)
            self.weather_manager = WeatherManager(self.config.weather)
            
            # Connect weather widget if it exists
            if self.weather_widget:
                # Connect weather widget signals
                self.weather_widget.weather_refresh_requested.connect(self.refresh_weather)
                self.weather_widget.weather_settings_requested.connect(self.show_settings_dialog)
                
                # Update weather widget config
                self.weather_widget.update_config(self.config.weather)
            
            # Connect weather manager Qt signals to weather widget
            self.weather_manager.weather_updated.connect(self.on_weather_updated)
            self.weather_manager.weather_error.connect(self.on_weather_error)
            self.weather_manager.loading_state_changed.connect(self.on_weather_loading_changed)
            
            # Connect weather manager signals directly to weather widget
            if self.weather_widget:
                self.weather_manager.weather_updated.connect(self.weather_widget.on_weather_updated)
                self.weather_manager.weather_error.connect(self.weather_widget.on_weather_error)
                self.weather_manager.loading_state_changed.connect(self.weather_widget.on_weather_loading)
            
            # Update weather status and visibility
            enabled = self.config.weather.enabled
            self.update_weather_status(enabled)
            
            if self.weather_widget:
                self.weather_widget.setVisible(enabled)
            
            if enabled:
                logger.info("Weather system initialized and enabled")
                # Start initial weather fetch
                self.refresh_weather()
            else:
                logger.info("Weather system initialized but disabled")
            
        except Exception as e:
            logger.error(f"Failed to initialize weather system: {e}")
            self.update_weather_status(False)
            if self.weather_widget:
                self.weather_widget.hide()

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.theme_manager.switch_theme()

        # Update config if available
        if self.config:
            self.config.display.theme = self.theme_manager.current_theme
            try:
                self.config_manager.save_config(self.config)
                logger.info(f"Theme switched to {self.theme_manager.current_theme}")
            except ConfigurationError as e:
                logger.error(f"Failed to save theme setting: {e}")

    def on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        self.apply_theme()

        # Update theme button
        if self.theme_button:
            self.theme_button.setText(self.theme_manager.get_theme_icon())
            self.theme_button.setToolTip(self.theme_manager.get_theme_tooltip())

        # Update status bar
        if self.theme_status:
            self.theme_status.setText(f"Theme: {theme_name.title()}")

        # Update train list widget
        if self.train_list_widget:
            self.train_list_widget.apply_theme(theme_name)

        # Update weather widget
        if self.weather_widget:
            # Create theme colors dictionary for weather widget
            theme_colors = {
                'background_primary': '#1a1a1a' if theme_name == 'dark' else '#ffffff',
                'background_secondary': '#2d2d2d' if theme_name == 'dark' else '#f5f5f5',
                'background_hover': '#404040' if theme_name == 'dark' else '#e0e0e0',
                'text_primary': '#ffffff' if theme_name == 'dark' else '#000000',
                'primary_accent': '#4fc3f7',
                'border_primary': '#404040' if theme_name == 'dark' else '#cccccc',
            }
            self.weather_widget.apply_theme(theme_colors)

        # Emit signal for other components
        self.theme_changed.emit(theme_name)

        logger.info(f"Theme changed to {theme_name}")

    def apply_theme(self):
        """Apply current theme styling."""
        main_style = self.theme_manager.get_main_window_stylesheet()
        widget_style = self.theme_manager.get_widget_stylesheet()

        self.setStyleSheet(main_style + widget_style)

    def manual_refresh(self):
        """Trigger manual refresh of train data."""
        self.refresh_requested.emit()
        logger.info("Manual refresh requested")

    def toggle_auto_refresh(self):
        """Toggle auto-refresh on/off."""
        # This will be connected to the train manager's auto-refresh control
        self.auto_refresh_toggle_requested.emit()
        logger.info("Auto-refresh toggle requested")

    def update_train_display(self, trains: List[TrainData]):
        """
        Update train list display.

        Args:
            trains: List of train data to display
        """
        if self.train_list_widget:
            self.train_list_widget.update_trains(trains)

        # Update train count
        if self.train_count_label:
            self.train_count_label.setText(f"{len(trains)} trains")

        logger.info(f"Updated display with {len(trains)} trains")

    def update_last_update_time(self, timestamp: str):
        """
        Update last update timestamp.

        Args:
            timestamp: Formatted timestamp string
        """
        if self.last_update_label:
            self.last_update_label.setText(f"Last Updated: {timestamp}")

    def update_next_update_countdown(self, seconds: int):
        """
        Update next update countdown.

        Args:
            seconds: Seconds until next update
        """
        if self.next_update_label:
            minutes = seconds // 60
            secs = seconds % 60
            if minutes > 0:
                self.next_update_label.setText(f"Next Update: {minutes}m {secs}s")
            else:
                self.next_update_label.setText(f"Next Update: {secs}s")

    def update_connection_status(self, connected: bool, message: str = ""):
        """
        Update connection status.

        Args:
            connected: Whether connected to API
            message: Optional status message
        """
        if self.connection_status:
            if connected:
                self.connection_status.setText("Connected")
                self.connection_status.setStyleSheet("color: #4caf50;")  # Green
            else:
                status_text = "Disconnected"
                if message:
                    status_text += f" ({message})"
                self.connection_status.setText(status_text)
                self.connection_status.setStyleSheet("color: #f44336;")  # Red

    def update_auto_refresh_status(self, enabled: bool):
        """
        Update auto-refresh status.

        Args:
            enabled: Whether auto-refresh is enabled
        """
        if self.auto_refresh_status:
            status = "ON" if enabled else "OFF"
            self.auto_refresh_status.setText(f"Auto-refresh: {status}")

        # Update auto-refresh button
        if hasattr(self, "auto_refresh_button"):
            if enabled:
                self.auto_refresh_button.setText("⏸️ Auto-refresh")
                self.auto_refresh_button.setToolTip(
                    "Auto-refresh is ON - Click to disable"
                )
            else:
                self.auto_refresh_button.setText("▶️ Auto-refresh")
                self.auto_refresh_button.setToolTip(
                    "Auto-refresh is OFF - Click to enable"
                )

    def update_weather_status(self, enabled: bool):
        """
        Update weather status display.
        
        Args:
            enabled: Whether weather integration is enabled
        """
        if self.weather_status:
            status = "ON" if enabled else "OFF"
            self.weather_status.setText(f"Weather: {status}")
            
            # Color coding
            if enabled:
                self.weather_status.setStyleSheet("color: #4caf50;")  # Green
            else:
                self.weather_status.setStyleSheet("color: #666666;")  # Gray

    def refresh_weather(self):
        """Trigger manual weather refresh."""
        if self.weather_manager:
            # Run async refresh
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.weather_manager.refresh_weather())
            else:
                asyncio.run(self.weather_manager.refresh_weather())
            logger.info("Manual weather refresh requested")

    def on_weather_updated(self, weather_data):
        """Handle weather data update."""
        logger.info("Weather data updated in main window")
        # Weather widget will be updated automatically via observer pattern

    def on_weather_error(self, error_message: str):
        """Handle weather error."""
        logger.warning(f"Weather error: {error_message}")
        # Could show in status bar or as notification

    def on_weather_loading_changed(self, is_loading: bool):
        """Handle weather loading state change."""
        if is_loading:
            logger.info("Weather data loading...")
        else:
            logger.info("Weather data loading complete")

    def show_error_message(self, title: str, message: str):
        """
        Show error message dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()

    def show_info_message(self, title: str, message: str):
        """
        Show information message dialog.

        Args:
            title: Dialog title
            message: Information message
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()

    def show_settings_dialog(self):
        """Show settings dialog."""
        try:
            dialog = SettingsDialog(self.config_manager, self)
            dialog.settings_saved.connect(self.on_settings_saved)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to show settings dialog: {e}")
            self.show_error_message("Settings Error", f"Failed to open settings: {e}")

    def on_settings_saved(self):
        """Handle settings saved event."""
        try:
            # Reload configuration
            self.config = self.config_manager.load_config()

            # Update theme if changed
            if self.config:
                self.theme_manager.set_theme(self.config.display.theme)
                
                # Update weather system if configuration changed
                if hasattr(self.config, 'weather') and self.config.weather:
                    if self.config.weather.enabled and not self.weather_manager:
                        # Weather was enabled, initialize system
                        self.setup_weather_system()
                    elif self.weather_manager:
                        # Update existing weather manager configuration
                        self.weather_manager.update_config(self.config.weather)
                        
                        # Update weather widget configuration
                        if self.weather_widget:
                            self.weather_widget.update_config(self.config.weather)
                            self.weather_widget.setVisible(self.config.weather.enabled)
                    
                    # Update weather status
                    self.update_weather_status(self.config.weather.enabled)
                elif hasattr(self.config, 'weather'):
                    # Weather config exists but is None, disable weather
                    self.update_weather_status(False)

            logger.info("Settings reloaded after save")

        except ConfigurationError as e:
            logger.error(f"Failed to reload settings: {e}")
            self.show_error_message(
                "Configuration Error", f"Failed to reload settings: {e}"
            )

    def show_about_dialog(self):
        """Show about dialog using centralized version system."""
        # Get config path for display
        config_path = self.config_manager.config_path
        
        # Use centralized about text with config path
        about_text = get_about_text()
        about_text += f"<p><small>Config: {config_path}</small></p>"

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("About")
        msg_box.setText(about_text)
        msg_box.exec()

    def connect_signals(self):
        """Connect internal signals."""
        # Additional signal connections can be added here
        pass

    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Application closing")
        
        # Shutdown weather manager if it exists
        if self.weather_manager:
            try:
                self.weather_manager.shutdown()
                logger.info("Weather manager shutdown complete")
            except Exception as e:
                logger.warning(f"Error shutting down weather manager: {e}")
        
        event.accept()
