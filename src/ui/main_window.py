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
from ..managers.astronomy_manager import AstronomyManager
from .train_widgets import TrainListWidget
from .weather_widgets import WeatherWidget
from .astronomy_widgets import AstronomyWidget
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

        # Make window completely invisible during initialization
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)

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
        self.astronomy_widget: Optional[AstronomyWidget] = None
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
        self.astronomy_status: Optional[QLabel] = None

        # Managers
        self.weather_manager: Optional[WeatherManager] = None
        self.astronomy_manager: Optional[AstronomyManager] = None

        # Setup theme system first to ensure proper styling from the start
        self.setup_theme_system()
        self.apply_theme()

        # Setup UI with theme already applied
        self.setup_ui()
        self.setup_application_icon()
        self.setup_weather_system()
        self.setup_astronomy_system()

        # Apply theme to all widgets after creation
        self.apply_theme_to_all_widgets()
        self.connect_signals()

        logger.info("Main window initialized")

        # Remove the invisible attributes but don't show yet - let main.py control when to show
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        self.setVisible(False)
        # Don't call show() here - main.py will call it when ready

    def setup_ui(self):
        """Initialize UI components."""
        self.setWindowTitle(__app_display_name__)
        self.setMinimumSize(
            800, 1100
        )  # Increased height for weather + astronomy widgets
        self.resize(
            1000, 1200
        )  # Larger default size for weather + astronomy integration

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(
            0
        )  # Remove spacing between widgets to eliminate horizontal lines

        # Header
        self.setup_header(layout)

        # Weather widget (always create, show/hide based on config)
        self.weather_widget = WeatherWidget()
        layout.addWidget(self.weather_widget)

        # Hide initially if weather is disabled
        if not (
            self.config
            and hasattr(self.config, "weather")
            and self.config.weather
            and self.config.weather.enabled
        ):
            self.weather_widget.hide()

        # Astronomy widget (always create, show/hide based on config)
        self.astronomy_widget = AstronomyWidget()
        layout.addWidget(self.astronomy_widget)

        # Show astronomy widget if astronomy is enabled (even without API key)
        if not (
            self.config
            and hasattr(self.config, "astronomy")
            and self.config.astronomy
            and self.config.astronomy.enabled
        ):
            self.astronomy_widget.hide()
        else:
            # Show the widget even if API key is missing - user can configure it
            self.astronomy_widget.show()

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
        header_widget.setObjectName("headerWidget")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)  # Reduced margins
        header_layout.setSpacing(8)

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

        # Apply header-specific styling to remove borders
        self.apply_header_styling(header_widget)

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
        self.astronomy_status = QLabel("Astronomy: OFF")

        self.status_bar.addWidget(self.connection_status)
        self.status_bar.addPermanentWidget(self.train_count_label)
        self.status_bar.addPermanentWidget(self.weather_status)
        self.status_bar.addPermanentWidget(self.astronomy_status)
        self.status_bar.addPermanentWidget(self.theme_status)
        self.status_bar.addPermanentWidget(self.auto_refresh_status)

    def setup_menu_bar(self):
        """Setup application menu bar."""
        # Ensure we're using the proper QMainWindow menu bar
        menubar = self.menuBar()

        # Clear any existing menu items
        menubar.clear()

        # Set menu bar properties to ensure proper display
        menubar.setNativeMenuBar(False)  # Force Qt menu bar on all platforms

        # File menu
        file_menu = menubar.addMenu("&File")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.setStatusTip("Refresh train data")
        refresh_action.triggered.connect(self.manual_refresh)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("&Settings")

        options_action = QAction("&Options...", self)
        options_action.setShortcut(QKeySequence("Ctrl+,"))
        options_action.setStatusTip("Open application settings")
        options_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(options_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        self.theme_action = QAction("Switch &Theme", self)
        self.theme_action.setShortcut(QKeySequence("Ctrl+T"))
        self.theme_action.setStatusTip("Toggle between light and dark theme")
        self.theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.theme_action)

        view_menu.addSeparator()

        # Weather toggle
        self.weather_toggle_action = QAction("Show &Weather", self)
        self.weather_toggle_action.setCheckable(True)
        self.weather_toggle_action.setChecked(True)  # Default checked
        self.weather_toggle_action.setStatusTip("Show/hide weather widget")
        self.weather_toggle_action.triggered.connect(self.toggle_weather_visibility)
        view_menu.addAction(self.weather_toggle_action)

        # Astronomy toggle
        self.astronomy_toggle_action = QAction("Show &Astronomy", self)
        self.astronomy_toggle_action.setCheckable(True)
        self.astronomy_toggle_action.setChecked(True)  # Default checked
        self.astronomy_toggle_action.setStatusTip("Show/hide astronomy widget")
        self.astronomy_toggle_action.triggered.connect(self.toggle_astronomy_visibility)
        view_menu.addAction(self.astronomy_toggle_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Apply menu bar styling
        self.apply_menu_bar_styling(menubar)

    def setup_theme_system(self):
        """Setup theme switching system."""
        # Connect theme change signal
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

    def setup_weather_system(self):
        """Setup weather integration system."""
        if (
            not self.config
            or not hasattr(self.config, "weather")
            or not self.config.weather
        ):
            logger.warning("Weather configuration not available")
            self.update_weather_status(False)
            return

        try:
            # Initialize weather manager (even if disabled, for potential later enabling)
            self.weather_manager = WeatherManager(self.config.weather)

            # Connect weather widget if it exists
            if self.weather_widget:
                # Connect weather widget signals
                self.weather_widget.weather_refresh_requested.connect(
                    self.refresh_weather
                )
                self.weather_widget.weather_settings_requested.connect(
                    self.show_settings_dialog
                )

                # Update weather widget config
                self.weather_widget.update_config(self.config.weather)

            # Connect weather manager Qt signals to weather widget
            self.weather_manager.weather_updated.connect(self.on_weather_updated)
            self.weather_manager.weather_error.connect(self.on_weather_error)
            self.weather_manager.loading_state_changed.connect(
                self.on_weather_loading_changed
            )

            # Connect weather manager signals directly to weather widget
            if self.weather_widget:
                self.weather_manager.weather_updated.connect(
                    self.weather_widget.on_weather_updated
                )
                self.weather_manager.weather_error.connect(
                    self.weather_widget.on_weather_error
                )
                self.weather_manager.loading_state_changed.connect(
                    self.weather_widget.on_weather_loading
                )

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

    def setup_astronomy_system(self):
        """Setup astronomy integration system."""
        if (
            not self.config
            or not hasattr(self.config, "astronomy")
            or not self.config.astronomy
        ):
            logger.warning("Astronomy configuration not available")
            self.update_astronomy_status(False)
            return

        try:
            # Always connect astronomy widget signals if it exists
            if self.astronomy_widget:
                # Connect astronomy widget signals
                self.astronomy_widget.astronomy_refresh_requested.connect(
                    self.refresh_astronomy
                )
                self.astronomy_widget.nasa_link_clicked.connect(
                    self.on_nasa_link_clicked
                )

                # Update astronomy widget config
                self.astronomy_widget.update_config(self.config.astronomy)

            # Only initialize astronomy manager if API key is present
            if self.config.astronomy.has_valid_api_key():
                # Initialize astronomy manager
                self.astronomy_manager = AstronomyManager(self.config.astronomy)

                # Connect astronomy manager Qt signals to astronomy widget
                self.astronomy_manager.astronomy_updated.connect(
                    self.on_astronomy_updated
                )
                self.astronomy_manager.astronomy_error.connect(self.on_astronomy_error)
                self.astronomy_manager.loading_state_changed.connect(
                    self.on_astronomy_loading_changed
                )

                # Connect astronomy manager signals directly to astronomy widget
                if self.astronomy_widget:
                    self.astronomy_manager.astronomy_updated.connect(
                        self.astronomy_widget.on_astronomy_updated
                    )
                    self.astronomy_manager.astronomy_error.connect(
                        self.astronomy_widget.on_astronomy_error
                    )
                    self.astronomy_manager.loading_state_changed.connect(
                        self.astronomy_widget.on_astronomy_loading
                    )

                logger.info("Astronomy system initialized with API key")
                # Data will be fetched when UI is shown via showEvent
            else:
                logger.info(
                    "Astronomy system initialized without API key - widget will show placeholder"
                )

            # Update astronomy status and visibility
            enabled = self.config.astronomy.enabled
            self.update_astronomy_status(enabled)

            if self.astronomy_widget:
                self.astronomy_widget.setVisible(enabled)

        except Exception as e:
            logger.error(f"Failed to initialize astronomy system: {e}")
            self.update_astronomy_status(False)
            # Don't hide the widget - let it show the error/placeholder state

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

        # Update menu bar styling
        menubar = self.menuBar()
        if menubar:
            self.apply_menu_bar_styling(menubar)

        # Update header styling
        header_widget = self.findChild(QWidget, "headerWidget")
        if header_widget:
            self.apply_header_styling(header_widget)

        # Update train list widget
        if self.train_list_widget:
            self.train_list_widget.apply_theme(theme_name)

        # Update weather widget
        if self.weather_widget:
            # Create theme colors dictionary for weather widget
            theme_colors = {
                "background_primary": "#1a1a1a" if theme_name == "dark" else "#ffffff",
                "background_secondary": (
                    "#2d2d2d" if theme_name == "dark" else "#f5f5f5"
                ),
                "background_hover": "#404040" if theme_name == "dark" else "#e0e0e0",
                "text_primary": "#ffffff" if theme_name == "dark" else "#000000",
                "primary_accent": "#4fc3f7",
                "border_primary": "#404040" if theme_name == "dark" else "#cccccc",
            }
            self.weather_widget.apply_theme(theme_colors)

        # Update astronomy widget
        if self.astronomy_widget:
            # Use same theme colors for astronomy widget
            theme_colors = {
                "background_primary": "#1a1a1a" if theme_name == "dark" else "#ffffff",
                "background_secondary": (
                    "#2d2d2d" if theme_name == "dark" else "#f5f5f5"
                ),
                "background_hover": "#404040" if theme_name == "dark" else "#e0e0e0",
                "text_primary": "#ffffff" if theme_name == "dark" else "#000000",
                "primary_accent": "#4fc3f7",
                "border_primary": "#404040" if theme_name == "dark" else "#cccccc",
            }
            self.astronomy_widget.apply_theme(theme_colors)

        # Emit signal for other components
        self.theme_changed.emit(theme_name)

        logger.info(f"Theme changed to {theme_name}")

    def apply_theme(self):
        """Apply current theme styling."""
        main_style = self.theme_manager.get_main_window_stylesheet()
        widget_style = self.theme_manager.get_widget_stylesheet()

        # Add custom styling to remove borders under menu bar
        if self.theme_manager.current_theme == "dark":
            custom_style = """
            QMainWindow {
                border: none;
            }
            QMainWindow::separator {
                border: none;
                background: transparent;
            }
            """
        else:
            custom_style = """
            QMainWindow {
                border: none;
            }
            QMainWindow::separator {
                border: none;
                background: transparent;
            }
            """

        self.setStyleSheet(main_style + widget_style + custom_style)

    def apply_theme_to_all_widgets(self):
        """Apply theme to all widgets after creation."""
        current_theme = self.theme_manager.current_theme

        # Apply theme to train list widget
        if self.train_list_widget:
            self.train_list_widget.apply_theme(current_theme)

        # Apply theme to weather widget
        if self.weather_widget:
            theme_colors = {
                "background_primary": (
                    "#1a1a1a" if current_theme == "dark" else "#ffffff"
                ),
                "background_secondary": (
                    "#2d2d2d" if current_theme == "dark" else "#f5f5f5"
                ),
                "background_hover": "#404040" if current_theme == "dark" else "#e0e0e0",
                "text_primary": "#ffffff" if current_theme == "dark" else "#000000",
                "primary_accent": "#4fc3f7",
                "border_primary": "#404040" if current_theme == "dark" else "#cccccc",
            }
            self.weather_widget.apply_theme(theme_colors)

        # Apply theme to astronomy widget
        if self.astronomy_widget:
            theme_colors = {
                "background_primary": (
                    "#1a1a1a" if current_theme == "dark" else "#ffffff"
                ),
                "background_secondary": (
                    "#2d2d2d" if current_theme == "dark" else "#f5f5f5"
                ),
                "background_hover": "#404040" if current_theme == "dark" else "#e0e0e0",
                "text_primary": "#ffffff" if current_theme == "dark" else "#000000",
                "primary_accent": "#4fc3f7",
                "border_primary": "#404040" if current_theme == "dark" else "#cccccc",
            }
            self.astronomy_widget.apply_theme(theme_colors)

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

    def update_astronomy_status(self, enabled: bool):
        """
        Update astronomy status display.

        Args:
            enabled: Whether astronomy integration is enabled
        """
        if self.astronomy_status:
            status = "ON" if enabled else "OFF"
            self.astronomy_status.setText(f"Astronomy: {status}")

            # Color coding
            if enabled:
                self.astronomy_status.setStyleSheet("color: #4caf50;")  # Green
            else:
                self.astronomy_status.setStyleSheet("color: #666666;")  # Gray

    def refresh_astronomy(self):
        """Trigger manual astronomy refresh."""
        if self.astronomy_manager:
            # Run async refresh using QTimer to defer to next event loop iteration
            import asyncio

            try:
                # Check if there's already an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in an async context, create a task
                    asyncio.create_task(self.astronomy_manager.refresh_astronomy())
                    logger.info("Manual astronomy refresh requested (async task)")
                except RuntimeError:
                    # No running loop, create a new one
                    def run_refresh():
                        asyncio.run(self.astronomy_manager.refresh_astronomy())

                    # Use QTimer to run in next event loop iteration
                    QTimer.singleShot(0, run_refresh)
                    logger.info("Manual astronomy refresh requested (new event loop)")
            except Exception as e:
                logger.warning(f"Failed to refresh astronomy: {e}")
        else:
            logger.info(
                "Astronomy refresh requested but no manager available (missing API key)"
            )

    def on_astronomy_updated(self, astronomy_data):
        """Handle astronomy data update."""
        logger.info("Astronomy data updated in main window")
        # Astronomy widget will be updated automatically via observer pattern

    def on_astronomy_error(self, error_message: str):
        """Handle astronomy error."""
        logger.warning(f"Astronomy error: {error_message}")
        # Could show in status bar or as notification

    def on_astronomy_loading_changed(self, is_loading: bool):
        """Handle astronomy loading state change."""
        if is_loading:
            logger.info("Astronomy data loading...")
        else:
            logger.info("Astronomy data loading complete")

    def on_nasa_link_clicked(self, url: str):
        """Handle NASA link clicks."""
        logger.info(f"NASA link clicked: {url}")
        # Link will be opened automatically by the astronomy widget

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
                if hasattr(self.config, "weather") and self.config.weather:
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
                elif hasattr(self.config, "weather"):
                    # Weather config exists but is None, disable weather
                    self.update_weather_status(False)

                # Update astronomy system if configuration changed
                if hasattr(self.config, "astronomy") and self.config.astronomy:
                    # Check if we need to reinitialize the astronomy system
                    needs_reinit = False

                    if self.config.astronomy.enabled:
                        if (
                            not self.astronomy_manager
                            and self.config.astronomy.has_valid_api_key()
                        ):
                            # Astronomy was enabled and API key is now available
                            needs_reinit = True
                        elif (
                            self.astronomy_manager
                            and not self.config.astronomy.has_valid_api_key()
                        ):
                            # API key was removed, shutdown manager
                            self.astronomy_manager.shutdown()
                            self.astronomy_manager = None
                            logger.info(
                                "Astronomy manager shutdown due to missing API key"
                            )
                        elif self.astronomy_manager:
                            # Update existing astronomy manager configuration
                            self.astronomy_manager.update_config(self.config.astronomy)

                    if needs_reinit:
                        # Reinitialize astronomy system
                        self.setup_astronomy_system()
                        logger.info("Astronomy system reinitialized with new API key")

                    # Always update astronomy widget configuration
                    if self.astronomy_widget:
                        self.astronomy_widget.update_config(self.config.astronomy)
                        self.astronomy_widget.setVisible(self.config.astronomy.enabled)

                    # Update astronomy status
                    self.update_astronomy_status(self.config.astronomy.enabled)
                elif hasattr(self.config, "astronomy"):
                    # Astronomy config exists but is None, disable astronomy
                    self.update_astronomy_status(False)

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

    def toggle_weather_visibility(self):
        """Toggle weather widget visibility."""
        if self.weather_widget:
            is_visible = self.weather_widget.isVisible()
            self.weather_widget.setVisible(not is_visible)

            # Update menu action text
            if self.weather_toggle_action:
                self.weather_toggle_action.setChecked(not is_visible)

            logger.info(f"Weather widget {'hidden' if is_visible else 'shown'}")

    def toggle_astronomy_visibility(self):
        """Toggle astronomy widget visibility."""
        if self.astronomy_widget:
            is_visible = self.astronomy_widget.isVisible()
            self.astronomy_widget.setVisible(not is_visible)

            # Update menu action text
            if self.astronomy_toggle_action:
                self.astronomy_toggle_action.setChecked(not is_visible)

            logger.info(f"Astronomy widget {'hidden' if is_visible else 'shown'}")

    def apply_menu_bar_styling(self, menubar):
        """Apply styling to the menu bar."""
        # Get current theme colors
        if self.theme_manager.current_theme == "dark":
            menu_style = """
            QMenuBar {
                background-color: #2d2d2d;
                color: #ffffff;
                border: none;
                border-bottom: none;
                padding: 2px;
                margin: 0px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
                margin: 0px;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #4fc3f7;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background-color: #0288d1;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
            }
            QMenu::item {
                padding: 4px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #4fc3f7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #404040;
                margin: 2px 0px;
            }
            """
        else:
            menu_style = """
            QMenuBar {
                background-color: #f0f0f0;
                color: #000000;
                border: none;
                border-bottom: none;
                padding: 2px;
                margin: 0px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
                margin: 0px;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #4fc3f7;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background-color: #0288d1;
            }
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 4px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #4fc3f7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #cccccc;
                margin: 2px 0px;
            }
            """

        menubar.setStyleSheet(menu_style)

    def apply_header_styling(self, header_widget):
        """Apply styling to the header widget to remove borders."""
        # Get current theme colors
        if self.theme_manager.current_theme == "dark":
            header_style = """
            QWidget#headerWidget {
                background-color: #1a1a1a;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
                border: none;
                padding: 2px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #404040;
                border-color: #4fc3f7;
            }
            QPushButton:pressed {
                background-color: #4fc3f7;
            }
            """
        else:
            header_style = """
            QWidget#headerWidget {
                background-color: #ffffff;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QLabel {
                color: #000000;
                background-color: transparent;
                border: none;
                padding: 2px;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                color: #000000;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #4fc3f7;
            }
            QPushButton:pressed {
                background-color: #4fc3f7;
                color: #ffffff;
            }
            """

        header_widget.setStyleSheet(header_style)

    def connect_signals(self):
        """Connect internal signals."""
        # Additional signal connections can be added here
        pass

    def showEvent(self, event):
        """Handle window show event - trigger astronomy data fetch when UI is displayed."""
        super().showEvent(event)

        # Only fetch astronomy data once when window is first shown
        if not hasattr(self, "_astronomy_data_fetched"):
            self._astronomy_data_fetched = True
            if self.astronomy_manager:
                logger.info("UI displayed - triggering astronomy data fetch")
                self.refresh_astronomy()

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

        # Shutdown astronomy manager if it exists
        if self.astronomy_manager:
            try:
                self.astronomy_manager.shutdown()
                logger.info("Astronomy manager shutdown complete")
            except Exception as e:
                logger.warning(f"Error shutting down astronomy manager: {e}")

        event.accept()
