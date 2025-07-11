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
from ..managers.train_manager import TrainManager
from ..managers.config_manager import ConfigManager, ConfigurationError
from ..managers.theme_manager import ThemeManager
from ..managers.weather_manager import WeatherManager
from ..managers.astronomy_manager import AstronomyManager
from ..managers.initialization_manager import InitializationManager
from .train_widgets import TrainListWidget, RouteDisplayDialog
from .weather_widgets import WeatherWidget
from .astronomy_widgets import AstronomyWidget
from .stations_settings_dialog import StationsSettingsDialog
from .nasa_settings_dialog import NASASettingsDialog
from .train_detail_dialog import TrainDetailDialog
from version import __version__, __app_display_name__, get_about_text

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window with theme switching and train display.

    Features:
    - Light/Dark theme switching (defaults to dark)
    - Unicode train emoji (🚂) in window title and about dialog
    - Scheduled train data display
    - 16-hour time window
    - Automatic and manual refresh
    """

    # Signals
    refresh_requested = Signal()
    theme_changed = Signal(str)
    # Auto-refresh removed
    astronomy_manager_ready = Signal()  # New signal for when astronomy manager is ready
    route_changed = Signal(str, str)  # Signal for when route changes (from_code, to_code)
    config_updated = Signal(object)  # Signal for when configuration is updated

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
        self.theme_button: Optional[QPushButton] = None
        self.astronomy_button: Optional[QPushButton] = None

        # Managers
        self.weather_manager: Optional[WeatherManager] = None
        self.astronomy_manager: Optional[AstronomyManager] = None
        self.initialization_manager: Optional[InitializationManager] = None
        self.train_manager: Optional[TrainManager] = None  # Will be set by main.py

        # Setup theme system first to ensure proper styling from the start
        self.setup_theme_system()
        self.apply_theme()

        # Setup UI with theme already applied
        self.setup_ui()
        self.setup_application_icon()
        
        # Initialize the optimized initialization manager
        self.initialization_manager = InitializationManager(self.config_manager, self)
        
        # Connect initialization signals
        self.initialization_manager.initialization_completed.connect(self._on_initialization_completed)
        self.initialization_manager.nasa_data_ready.connect(self._on_nasa_data_ready)
        
        # Apply theme to all widgets after creation
        self.apply_theme_to_all_widgets()
        self.connect_signals()
        
        # Start optimized widget initialization
        QTimer.singleShot(50, self._start_optimized_initialization)

        logger.debug("Main window initialized")

        # Remove the invisible attributes but don't show yet - let main.py control when to show
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        self.setVisible(False)
        # Don't call show() here - main.py will call it when ready

    def setup_ui(self):
        """Initialize UI components."""
        self.setWindowTitle(__app_display_name__)
        
        # Get screen dimensions for responsive sizing
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # Calculate responsive window size
        # For smaller screens (like 13" laptops), scale to ~80% for better space utilization
        # For larger screens, keep full size
        self.is_small_screen = screen_width <= 1440 or screen_height <= 900
        self.ui_scale_factor = 0.8 if self.is_small_screen else 1.0
        
        # Check if astronomy is enabled to determine window height
        astronomy_enabled = (
            self.config and
            hasattr(self.config, 'astronomy') and
            self.config.astronomy and
            self.config.astronomy.enabled
        )
        
        if self.is_small_screen:
            # Further reduced height for 13" MacBook compatibility but increased width for astronomy widget
            min_width = int(900 * 0.8)  # 720
            default_width = int(1100 * 0.8)  # 880
            
            if astronomy_enabled:
                min_height = int(950 * 0.8)  # 760
                default_height = int(1050 * 0.8)  # 840
            else:
                # Compact height when astronomy disabled
                min_height = int(700 * 0.8)  # 560
                default_height = int(800 * 0.8)  # 640
            
            logger.info(f"Small screen detected ({screen_width}x{screen_height}), using scaled window size: {default_width}x{default_height} (astronomy {'enabled' if astronomy_enabled else 'disabled'})")
        else:
            # Increased width for larger screens to accommodate astronomy widget
            min_width = 900
            default_width = 1100
            
            if astronomy_enabled:
                min_height = 1100
                default_height = 1200
            else:
                # Compact height when astronomy disabled
                min_height = 800
                default_height = 900
            
            logger.debug(f"Large screen detected ({screen_width}x{screen_height}), using full window size: {default_width}x{default_height} (astronomy {'enabled' if astronomy_enabled else 'disabled'})")
        
        self.setMinimumSize(min_width, min_height)
        self.resize(default_width, default_height)
        
        # Center the window on the screen
        self.center_window()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        # Add proper spacing between widgets to prevent overlap (scaled)
        scaled_spacing = int(12 * self.ui_scale_factor)
        layout.setSpacing(scaled_spacing)

        # Weather widget (always create, show/hide based on config)
        self.weather_widget = WeatherWidget(scale_factor=self.ui_scale_factor)
        layout.addWidget(self.weather_widget)

        # Hide initially if weather is disabled
        if not (
            self.config
            and hasattr(self.config, "weather")
            and self.config.weather
            and self.config.weather.enabled
        ):
            self.weather_widget.hide()

        # Astronomy widget (create and conditionally add to layout based on config)
        self.astronomy_widget = AstronomyWidget(scale_factor=self.ui_scale_factor)

        # Only add to layout if astronomy is enabled - this prevents wasted space
        should_show_astronomy = True
        if (
            self.config
            and hasattr(self.config, "astronomy")
            and self.config.astronomy
            and not self.config.astronomy.enabled
        ):
            should_show_astronomy = False
        
        if should_show_astronomy:
            layout.addWidget(self.astronomy_widget)
            self.astronomy_widget.show()
            logger.debug("Astronomy widget added to layout and shown")
        else:
            # Don't add to layout when disabled - this saves vertical space
            logger.info("Astronomy widget not added to layout (disabled in config)")

        # Train list with extended capacity and reduced height for small screens
        self.train_list_widget = TrainListWidget(max_trains=50)
        
        # For small screens, reduce train pane height by ~20% by setting a maximum height
        if self.is_small_screen:
            # Calculate reduced height: base height * scale * reduction factor
            max_train_height = int(400 * self.ui_scale_factor * 0.8)  # ~20% reduction
            self.train_list_widget.setMaximumHeight(max_train_height)
        
        layout.addWidget(self.train_list_widget)

        # Menu bar
        self.setup_menu_bar()
        
        # Standalone header buttons in top-right corner
        self.setup_header_buttons()

    def setup_application_icon(self):
        """Setup application icon using Unicode train emoji."""
        from PySide6.QtGui import QPixmap, QPainter, QFont
        from PySide6.QtCore import Qt
        
        # Set window title without emoji (emoji is already in the window icon)
        self.setWindowTitle(__app_display_name__)
        
        # Create and set window icon from emoji
        try:
            # Create a pixmap for the icon
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            # Paint the emoji onto the pixmap
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Set up font for emoji
            font = QFont()
            font.setPointSize(48)
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.black)
            
            # Draw the train emoji centered
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🚂")
            painter.end()
            
            # Create icon and set it
            icon = QIcon(pixmap)
            self.setWindowIcon(icon)
            
            logger.debug("Window icon set using Unicode train emoji")
            
        except Exception as e:
            logger.warning(f"Failed to create emoji window icon: {e}")
            logger.info("Using Unicode train emoji in window title only")


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

        stations_action = QAction("&Stations...", self)
        stations_action.setShortcut(QKeySequence("Ctrl+,"))
        stations_action.setStatusTip("Configure station settings, display, and refresh options")
        stations_action.triggered.connect(self.show_stations_settings_dialog)
        settings_menu.addAction(stations_action)

        nasa_action = QAction("&NASA API...", self)
        nasa_action.setStatusTip("Configure NASA API settings and astronomy options")
        nasa_action.triggered.connect(self.show_nasa_settings_dialog)
        settings_menu.addAction(nasa_action)

        # View menu
        view_menu = menubar.addMenu("&View")

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

        # Theme button will be created as a standalone floating button
        self.theme_button = None  # Will be created in setup_theme_button()

        # Apply menu bar styling
        self.apply_menu_bar_styling(menubar)

    def setup_header_buttons(self):
        """Setup header buttons (theme and astronomy toggle) in top-right corner."""
        # Create theme button
        self.theme_button = QPushButton(self.theme_manager.get_theme_icon(), self)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setToolTip(self.theme_manager.get_theme_tooltip())
        self.theme_button.setFixedSize(32, 32)
        
        # Create astronomy toggle button
        self.astronomy_button = QPushButton(self.get_astronomy_icon(), self)
        self.astronomy_button.clicked.connect(self.toggle_astronomy)
        self.astronomy_button.setToolTip(self.get_astronomy_tooltip())
        self.astronomy_button.setFixedSize(32, 32)
        
        # Apply styling to both buttons
        self.apply_header_button_styling()
        
        # Position the buttons in the top-right corner
        self.position_header_buttons()
        
        # Make sure the buttons stay on top
        self.theme_button.raise_()
        self.astronomy_button.raise_()
        self.theme_button.show()
        self.astronomy_button.show()

    def get_astronomy_icon(self):
        """Get astronomy button icon based on current state."""
        if (self.config and
            hasattr(self.config, 'astronomy') and
            self.config.astronomy and
            self.config.astronomy.enabled):
            return "🌏"  # Earth/space when enabled
        else:
            return "🔭"  # Telescope when disabled (to enable)

    def get_astronomy_tooltip(self):
        """Get astronomy button tooltip based on current state."""
        if (self.config and
            hasattr(self.config, 'astronomy') and
            self.config.astronomy and
            self.config.astronomy.enabled):
            return "Astronomy enabled - click to disable"
        else:
            return "Astronomy disabled - click to enable"

    def apply_header_button_styling(self):
        """Apply styling to header buttons (theme and astronomy)."""
        # Get current theme colors
        if self.theme_manager.current_theme == "dark":
            button_style = """
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #404040;
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
            }
            """
        else:
            button_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                color: #000000;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
            """
        
        if self.theme_button:
            self.theme_button.setStyleSheet(button_style)
        if self.astronomy_button:
            self.astronomy_button.setStyleSheet(button_style)

    def apply_theme_button_styling(self):
        """Apply styling to the standalone theme button (legacy method)."""
        # Delegate to the new header button styling method
        self.apply_header_button_styling()

    def position_header_buttons(self):
        """Position header buttons (theme and astronomy) in the top-right corner."""
        button_width = 32
        button_spacing = 8
        right_margin = 8
        top_margin = 8
        
        if self.astronomy_button:
            # Astronomy button (rightmost)
            astro_x = self.width() - button_width - right_margin
            self.astronomy_button.move(astro_x, top_margin)
        
        if self.theme_button:
            # Theme button (left of astronomy button)
            theme_x = self.width() - (button_width * 2) - button_spacing - right_margin
            self.theme_button.move(theme_x, top_margin)

    def position_theme_button(self):
        """Position the theme button (legacy method)."""
        # Delegate to the new header button positioning method
        self.position_header_buttons()

    def _update_window_size_for_astronomy(self):
        """Update window size and center window based on astronomy enabled state (legacy method)."""
        # Delegate to the new unified method
        self._update_window_size_for_widgets()

    def _update_window_size_for_widgets(self):
        """Update window size and center window based on currently visible widgets."""
        # Determine which widgets are currently visible by checking layout presence
        weather_visible = False
        astronomy_visible = False
        
        central_widget = self.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            if layout:
                # Check if weather widget is in layout and visible
                if self.weather_widget:
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget() == self.weather_widget:
                            weather_visible = self.weather_widget.isVisible()
                            break
                
                # Check if astronomy widget is in layout and visible
                if self.astronomy_widget:
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget() == self.astronomy_widget:
                            astronomy_visible = self.astronomy_widget.isVisible()
                            break
        
        # Calculate target height with AGGRESSIVE differences for dramatic visible changes
        if self.is_small_screen:
            # Small screen calculations (scaled by 0.8) - aggressive sizing
            if weather_visible and astronomy_visible:
                target_height = int(1200 * 0.8)  # 960 - both widgets (full height)
            elif weather_visible:
                target_height = int(725 * 0.8)   # 580 - weather only (HALF + 1/8th + 50px for proper display)
            elif astronomy_visible:
                target_height = int(600 * 0.8)   # 480 - astronomy only (HALF height)
            else:
                target_height = int(450 * 0.8)   # 360 - trains only (QUARTER height + 150px for perfect usability)
        else:
            # Large screen calculations - aggressive sizing
            if weather_visible and astronomy_visible:
                target_height = 1200  # Both widgets (full height)
            elif weather_visible:
                target_height = 725   # Weather only (HALF + 1/8th + 50px for proper display)
            elif astronomy_visible:
                target_height = 600   # Astronomy only (HALF height)
            else:
                target_height = 450   # Trains only (QUARTER height + 150px for perfect usability)
        
        # Always force resize regardless of current size
        current_height = self.height()
        current_width = self.width()
        
        # CRITICAL FIX: Temporarily remove minimum size constraint to allow ultra-aggressive shrinking
        self.setMinimumSize(0, 0)
        
        # Force resize to target height
        self.resize(current_width, target_height)
        
        # CRITICAL FIX: Restore a reasonable minimum size but much smaller than before
        # This allows the ultra-tiny sizes while preventing complete collapse
        min_width = 400  # Reasonable minimum width
        min_height = 100  # Very small minimum height to allow ultra-aggressive shrinking
        self.setMinimumSize(min_width, min_height)
        
        # Center the window on screen after resizing
        self.center_window()
        
        # Log the resize with widget status
        widget_status = []
        if weather_visible:
            widget_status.append("weather")
        if astronomy_visible:
            widget_status.append("astronomy")
        if not widget_status:
            widget_status.append("trains only")
        
        logger.info(f"Window FORCED resize from {current_width}x{current_height} to {current_width}x{target_height} and recentered (visible: {', '.join(widget_status)})")

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
                    self.show_stations_settings_dialog
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
                logger.debug("Weather system initialized and enabled")
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
        # Handle missing astronomy configuration gracefully
        if (
            not self.config
            or not hasattr(self.config, "astronomy")
            or not self.config.astronomy
        ):
            logger.info("Astronomy configuration not available - widget will show placeholder")
            # Still connect widget signals and show placeholder content
            if self.astronomy_widget:
                # Connect astronomy widget signals even without config
                self.astronomy_widget.astronomy_refresh_requested.connect(
                    self.refresh_astronomy
                )
                self.astronomy_widget.nasa_link_clicked.connect(
                    self.on_nasa_link_clicked
                )
                logger.info("Astronomy widget signals connected (no config)")
            
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

                logger.debug("Astronomy system initialized with API key")
                # Emit signal to indicate astronomy manager is ready for data fetch
                self.astronomy_manager_ready.emit()
            else:
                logger.info(
                    "Astronomy system initialized without API key - widget will show placeholder"
                )

            # Update astronomy status and visibility
            enabled = self.config.astronomy.enabled
            self.update_astronomy_status(enabled)

            # Only hide the widget if explicitly disabled in config
            # Always show by default (will show placeholder if no API key)
            if self.astronomy_widget:
                # Only hide if explicitly disabled, otherwise show by default
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

    def toggle_astronomy(self):
        """Toggle astronomy integration with smart API key detection."""
        if not self.config:
            logger.warning("Cannot toggle astronomy: no configuration available")
            return
            
        # Check if astronomy config exists
        if not hasattr(self.config, 'astronomy') or not self.config.astronomy:
            logger.warning("Cannot toggle astronomy: no astronomy configuration available")
            return
            
        # Smart toggle logic: check for API key if trying to enable
        current_enabled = self.config.astronomy.enabled
        
        if not current_enabled and not self.config.astronomy.has_valid_api_key():
            # User wants to enable but no API key - launch settings dialog
            logger.info("Astronomy toggle requested but no API key - launching NASA settings dialog")
            self.show_nasa_settings_dialog()
            return
            
        # Direct toggle - API key is available or user is disabling
        self.config.astronomy.enabled = not current_enabled
        
        try:
            self.config_manager.save_config(self.config)
            logger.info(f"Astronomy {'enabled' if self.config.astronomy.enabled else 'disabled'}")
            
            # Update button appearance
            if self.astronomy_button:
                self.astronomy_button.setText(self.get_astronomy_icon())
                self.astronomy_button.setToolTip(self.get_astronomy_tooltip())
            
            # Handle layout and window resize directly for immediate toggle
            if self.config.astronomy.enabled:
                # Enabling astronomy - add widget and resize window
                self._ensure_astronomy_widget_in_layout()
                self._update_window_size_for_widgets()
            else:
                # Disabling astronomy - remove widget and resize window
                self._remove_astronomy_widget_from_layout()
                self._update_window_size_for_widgets()
            
        except ConfigurationError as e:
            logger.error(f"Failed to save astronomy setting: {e}")
            # Revert the change
            self.config.astronomy.enabled = current_enabled

    def on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        self.apply_theme()

        # Update header buttons
        if self.theme_button:
            self.theme_button.setText(self.theme_manager.get_theme_icon())
            self.theme_button.setToolTip(self.theme_manager.get_theme_tooltip())
        if self.astronomy_button:
            self.astronomy_button.setText(self.get_astronomy_icon())
            self.astronomy_button.setToolTip(self.get_astronomy_tooltip())
        self.apply_header_button_styling()

        # Update menu bar styling
        menubar = self.menuBar()
        if menubar:
            self.apply_menu_bar_styling(menubar)

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
                "primary_accent": "#1976d2",
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
                "primary_accent": "#1976d2",
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
                "primary_accent": "#1976d2",
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
                "primary_accent": "#1976d2",
                "border_primary": "#404040" if current_theme == "dark" else "#cccccc",
            }
            self.astronomy_widget.apply_theme(theme_colors)

    def manual_refresh(self):
        """Trigger manual refresh of train data."""
        self.refresh_requested.emit()
        logger.info("Manual refresh requested")

    # Auto-refresh functionality removed as obsolete

    def update_route_display(self, from_station: str, to_station: str, via_stations: Optional[List[str]] = None):
        """
        Update route display (header removed - now only logs route info).
        
        Args:
            from_station: Origin station name
            to_station: Destination station name
            via_stations: Optional list of via stations
        """
        # Header removed - route display no longer shown in UI, only logged
        # Clean up station names by removing railway line context for logging
        def clean_station_name(station_name: str) -> str:
            """Remove railway line context from station name for cleaner display."""
            if not station_name:
                return station_name
            # Remove text in parentheses (railway line context)
            if '(' in station_name:
                return station_name.split('(')[0].strip()
            return station_name
        
        clean_from = clean_station_name(from_station)
        clean_to = clean_station_name(to_station)
        
        if via_stations:
            # Clean via station names
            clean_via_stations = [clean_station_name(station) for station in via_stations]
            via_text = " -> ".join(clean_via_stations)
            route_text = f"Route: {clean_from} -> {via_text} -> {clean_to}"
        else:
            route_text = f"Route: {clean_from} -> {clean_to}"
        
        logger.debug(f"Route display updated: {route_text}")

    def update_train_display(self, trains: List[TrainData]):
        """
        Update train list display.

        Args:
            trains: List of train data to display
        """
        if self.train_list_widget:
            self.train_list_widget.update_trains(trains)
            # Connect train selection signal if not already connected
            if not hasattr(self, '_train_selection_connected'):
                self.train_list_widget.train_selected.connect(self.show_train_details)
                self._train_selection_connected = True
            # Connect route selection signal if not already connected
            if not hasattr(self, '_route_selection_connected'):
                self.train_list_widget.route_selected.connect(self.show_route_details)
                self._route_selection_connected = True

        # Status bar removed - no longer updating train count

        logger.debug(f"Updated display with {len(trains)} trains")

    def update_last_update_time(self, timestamp: str):
        """
        Update last update timestamp (header removed - now only logs).

        Args:
            timestamp: Formatted timestamp string
        """
        # Header removed - last update time no longer shown in UI, only logged
        logger.debug(f"Last Updated: {timestamp}")

    # Auto-refresh countdown removed

    def update_connection_status(self, connected: bool, message: str = ""):
        """
        Update connection status.

        Args:
            connected: Whether connected to API
            message: Optional status message
        """
        # Status bar removed - this method is kept for compatibility but does nothing
        pass

    # Auto-refresh status update removed

    def update_weather_status(self, enabled: bool):
        """
        Update weather status display.

        Args:
            enabled: Whether weather integration is enabled
        """
        # Status bar removed - this method is kept for compatibility but does nothing
        pass

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
        logger.debug("Weather data updated in main window")
        # Weather widget will be updated automatically via observer pattern

    def on_weather_error(self, error_message: str):
        """Handle weather error."""
        logger.warning(f"Weather error: {error_message}")
        # Could show in status bar or as notification

    def on_weather_loading_changed(self, is_loading: bool):
        """Handle weather loading state change."""
        if is_loading:
            logger.debug("Weather data loading...")
        else:
            logger.debug("Weather data loading complete")

    def update_astronomy_status(self, enabled: bool):
        """
        Update astronomy status display.

        Args:
            enabled: Whether astronomy integration is enabled
        """
        # Status bar removed - this method is kept for compatibility but does nothing
        pass

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
                    # Additional null check to satisfy Pylance
                    if self.astronomy_manager:
                        asyncio.create_task(self.astronomy_manager.refresh_astronomy())
                        logger.info("Manual astronomy refresh requested (async task)")
                except RuntimeError:
                    # No running loop, create a new one
                    def run_refresh():
                        # Additional null check to satisfy Pylance
                        if self.astronomy_manager:
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
        logger.debug("Astronomy data updated in main window")
        # Astronomy widget will be updated automatically via observer pattern

    def on_astronomy_error(self, error_message: str):
        """Handle astronomy error."""
        logger.warning(f"Astronomy error: {error_message}")
        # Could show in status bar or as notification

    def on_astronomy_loading_changed(self, is_loading: bool):
        """Handle astronomy loading state change."""
        if is_loading:
            logger.debug("Astronomy data loading...")
        else:
            logger.debug("Astronomy data loading complete")

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

    def show_stations_settings_dialog(self):
        """Show stations settings dialog."""
        try:
            dialog = StationsSettingsDialog(self.config_manager, self, self.theme_manager)
            dialog.settings_saved.connect(self.on_settings_saved)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to show stations settings dialog: {e}")
            self.show_error_message("Settings Error", f"Failed to open stations settings: {e}")

    def show_nasa_settings_dialog(self):
        """Show NASA settings dialog."""
        try:
            dialog = NASASettingsDialog(self.config_manager, self, self.theme_manager)
            dialog.settings_saved.connect(self.on_settings_saved)
            dialog.astronomy_enable_requested.connect(self.on_astronomy_enable_requested)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to show NASA settings dialog: {e}")
            self.show_error_message("Settings Error", f"Failed to open NASA settings: {e}")


    def on_settings_saved(self):
        """Handle settings saved event."""
        try:
            # Store old time window for comparison
            old_time_window = None
            if self.config and hasattr(self.config, 'display'):
                old_time_window = self.config.display.time_window_hours
            
            # Reload configuration
            self.config = self.config_manager.load_config()

            # Update theme if changed
            if self.config:
                self.theme_manager.set_theme(self.config.display.theme)
                
                # Emit config updated signal to update train manager
                self.config_updated.emit(self.config)
                
                # Update time window display if changed
                if hasattr(self.config, 'display') and self.config.display:
                    new_time_window = self.config.display.time_window_hours
                    if old_time_window != new_time_window:
                        # Header removed - time window no longer shown in UI, only logged
                        logger.info(f"Time window changed from {old_time_window} to {new_time_window} hours")
                        
                        # Trigger refresh to reload trains with new time window
                        self.refresh_requested.emit()
                        logger.info(f"Refreshing train data for new time window")
                
                # Update train manager route if stations changed
                # This signal will be connected from main.py
                self.route_changed.emit(self.config.stations.from_code, self.config.stations.to_code)
                
                # Update route display with via stations
                via_stations = getattr(self.config.stations, 'via_stations', [])
                self.update_route_display(
                    self.config.stations.from_name,
                    self.config.stations.to_name,
                    via_stations
                )
                
                # Trigger refresh to load trains with new route data
                self.refresh_requested.emit()
                logger.info("Route changed - refreshing train data for new route")

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
                    needs_data_fetch = False

                    if self.config.astronomy.enabled:
                        if (
                            not self.astronomy_manager
                            and self.config.astronomy.has_valid_api_key()
                        ):
                            # Astronomy was enabled and API key is now available
                            needs_reinit = True
                            needs_data_fetch = True
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
                        # Reinitialize astronomy system completely
                        self.setup_astronomy_system()
                        logger.info("Astronomy system reinitialized with new API key")
                        
                        # Reset the astronomy data fetched flag so showEvent can trigger fetch
                        if hasattr(self, "_astronomy_data_fetched"):
                            delattr(self, "_astronomy_data_fetched")
                            logger.info("Reset astronomy data fetched flag for new manager")

                    # CRITICAL FIX: Emit signal to trigger immediate data fetch for new/updated API key
                    if needs_data_fetch and self.astronomy_manager:
                        logger.info("Emitting astronomy manager ready signal to trigger data fetch")
                        self.astronomy_manager_ready.emit()
                    
                    # ADDITIONAL FIX: Also trigger data fetch if astronomy was just enabled with existing API key
                    elif (self.config.astronomy.enabled and
                          self.astronomy_manager and
                          self.config.astronomy.has_valid_api_key()):
                        logger.info("Astronomy enabled with existing API key - triggering data fetch")
                        self.astronomy_manager_ready.emit()

                    # Always update astronomy widget configuration
                    if self.astronomy_widget:
                        self.astronomy_widget.update_config(self.config.astronomy)
                        
                        # CRITICAL: Ensure widget is hidden if not in layout to prevent white space
                        if self.config.astronomy.enabled:
                            # Check if widget is actually in layout
                            central_widget = self.centralWidget()
                            if central_widget:
                                layout = central_widget.layout()
                                widget_in_layout = False
                                if layout:
                                    for i in range(layout.count()):
                                        item = layout.itemAt(i)
                                        if item and item.widget() == self.astronomy_widget:
                                            widget_in_layout = True
                                            break
                                
                                # If enabled but not in layout, keep it hidden until data is ready
                                if not widget_in_layout:
                                    self.astronomy_widget.setVisible(False)
                                    logger.debug("Astronomy widget kept hidden until data is ready")
                        
                        # Handle layout changes when enabling/disabling astronomy
                        central_widget = self.centralWidget()
                        if central_widget:
                            from PySide6.QtWidgets import QVBoxLayout
                            layout = central_widget.layout()
                            
                            if isinstance(layout, QVBoxLayout):
                                is_currently_in_layout = False
                                for i in range(layout.count()):
                                    item = layout.itemAt(i)
                                    if item and item.widget() == self.astronomy_widget:
                                        is_currently_in_layout = True
                                        break
                                
                                should_be_in_layout = self.config.astronomy.enabled
                                
                                if is_currently_in_layout != should_be_in_layout:
                                    if should_be_in_layout:
                                        # Don't add to layout immediately - wait for data to be ready
                                        # The widget will be added by _ensure_astronomy_widget_in_layout()
                                        # when astronomy data is actually loaded
                                        logger.info("Astronomy enabled - will add widget to layout when data is ready")
                                    else:
                                        # Remove from layout and hide
                                        layout.removeWidget(self.astronomy_widget)
                                        self.astronomy_widget.setVisible(False)
                                        logger.info("Astronomy widget removed from layout (disabled in settings)")
                        
                        # Update menu action state
                        if self.astronomy_toggle_action:
                            self.astronomy_toggle_action.setChecked(self.config.astronomy.enabled)

                    # Update astronomy status
                    self.update_astronomy_status(self.config.astronomy.enabled)
                    
                    # Only update window size if astronomy is being disabled
                    # If enabling, wait for data to be ready before resizing
                    if not self.config.astronomy.enabled:
                        self._update_window_size_for_widgets()
                    else:
                        logger.debug("Deferring window resize until astronomy data is ready")
                elif hasattr(self.config, "astronomy"):
                    # Astronomy config exists but is None, disable astronomy
                    self.update_astronomy_status(False)
                else:
                    # FIRST-TIME SETUP: No astronomy config existed before, now it does
                    # This handles the case where config.json was just created for the first time
                    logger.info("First-time astronomy setup detected - initializing astronomy system")
                    self.setup_astronomy_system()
                    
                    # Reset the astronomy data fetched flag for first-time setup
                    if hasattr(self, "_astronomy_data_fetched"):
                        delattr(self, "_astronomy_data_fetched")
                        logger.info("Reset astronomy data fetched flag for first-time setup")

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
        """Toggle weather widget visibility and resize window accordingly."""
        if self.weather_widget:
            is_visible = self.weather_widget.isVisible()
            
            # Simply toggle visibility
            self.weather_widget.setVisible(not is_visible)

            # Update menu action text
            if self.weather_toggle_action:
                self.weather_toggle_action.setChecked(not is_visible)

            # Resize and center the window
            self._update_window_size_for_widgets()
            
            logger.info(f"Weather widget {'hidden' if is_visible else 'shown'} - window resized and centered")

    def toggle_astronomy_visibility(self):
        """Toggle astronomy widget visibility and resize window accordingly."""
        if self.astronomy_widget:
            is_visible = self.astronomy_widget.isVisible()
            
            # Simply toggle visibility
            self.astronomy_widget.setVisible(not is_visible)

            # Update menu action text
            if self.astronomy_toggle_action:
                self.astronomy_toggle_action.setChecked(not is_visible)

            # Resize and center the window
            self._update_window_size_for_widgets()
            
            logger.info(f"Astronomy widget {'hidden' if is_visible else 'shown'} - window resized and centered")

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
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background-color: #0d47a1;
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
                background-color: #1976d2;
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
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background-color: #0d47a1;
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
                background-color: #1976d2;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #cccccc;
                margin: 2px 0px;
            }
            """

        menubar.setStyleSheet(menu_style)


    def connect_signals(self):
        """Connect internal signals."""
        # Connect astronomy manager ready signal to trigger data fetch
        self.astronomy_manager_ready.connect(self._on_astronomy_manager_ready)

    def _on_astronomy_manager_ready(self):
        """Handle astronomy manager ready signal - trigger immediate data fetch."""
        if self.astronomy_manager:
            logger.debug("Astronomy manager ready signal received - triggering data fetch")
            self.refresh_astronomy()
            
            # Start auto-refresh if enabled
            if (self.config and
                hasattr(self.config, "astronomy") and
                self.config.astronomy and
                self.config.astronomy.enabled):
                self.astronomy_manager.start_auto_refresh()
                logger.debug("Auto-refresh started for newly configured astronomy")
        else:
            logger.warning("Astronomy manager ready signal received but no manager available")

    def on_astronomy_enable_requested(self):
        """Handle astronomy enable request from settings dialog - wait for data before showing success."""
        if self.astronomy_manager:
            # Connect to astronomy signals to wait for data
            self.astronomy_manager.astronomy_updated.connect(self._on_astronomy_data_ready_after_enable)
            self.astronomy_manager.astronomy_error.connect(self._on_astronomy_error_after_enable)
            logger.debug("Connected to astronomy signals to wait for data after enable")
        else:
            # No manager available, show immediate message
            self._show_astronomy_enabled_message()

    def _on_astronomy_data_ready_after_enable(self, forecast_data):
        """Handle astronomy data ready after enable request."""
        # Disconnect the temporary signals
        if self.astronomy_manager:
            self.astronomy_manager.astronomy_updated.disconnect(self._on_astronomy_data_ready_after_enable)
            self.astronomy_manager.astronomy_error.disconnect(self._on_astronomy_error_after_enable)
        
        # Now that data is ready, add astronomy widget to layout if not already there
        self._ensure_astronomy_widget_in_layout()
        
        # Show success message now that data is ready
        self._show_astronomy_enabled_message()
        logger.info("Astronomy data loaded successfully after enable")

    def _on_astronomy_error_after_enable(self, error_message):
        """Handle astronomy error after enable request."""
        # Disconnect the temporary signals
        if self.astronomy_manager:
            self.astronomy_manager.astronomy_updated.disconnect(self._on_astronomy_data_ready_after_enable)
            self.astronomy_manager.astronomy_error.disconnect(self._on_astronomy_error_after_enable)
        
        # Show error message
        from PySide6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Astronomy Data Error")
        msg_box.setText(f"Astronomy integration has been enabled, but there was an error loading data:\n\n{error_message}\n\n"
                       "You can try refreshing the data later.")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
                color: #1976d2;
            }
            QMessageBox QLabel {
                color: #1976d2;
                background-color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                color: #1976d2;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #1976d2;
            }
            QMessageBox QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
        """)
        msg_box.exec()
        logger.warning(f"Astronomy error after enable: {error_message}")

    def _ensure_astronomy_widget_in_layout(self):
        """Ensure astronomy widget is added to layout when data is ready."""
        if not self.astronomy_widget:
            return
            
        central_widget = self.centralWidget()
        if central_widget:
            from PySide6.QtWidgets import QVBoxLayout
            layout = central_widget.layout()
            
            if isinstance(layout, QVBoxLayout):
                # Check if widget is already in the layout
                is_in_layout = False
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == self.astronomy_widget:
                        is_in_layout = True
                        break
                
                if not is_in_layout:
                    # Add to layout between weather and train widgets
                    weather_index = -1
                    train_index = -1
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget():
                            if item.widget() == self.weather_widget:
                                weather_index = i
                            elif item.widget() == self.train_list_widget:
                                train_index = i
                    
                    # Insert astronomy widget after weather widget
                    insert_index = weather_index + 1 if weather_index >= 0 else 0
                    if train_index >= 0 and insert_index > train_index:
                        insert_index = train_index
                    
                    layout.insertWidget(insert_index, self.astronomy_widget)
                    self.astronomy_widget.setVisible(True)
                    logger.info("Astronomy widget added to layout after data ready")
                    
                    # Update window size for astronomy now that widget is in layout with data
                    self._update_window_size_for_widgets()

    def _remove_astronomy_widget_from_layout(self):
        """Remove astronomy widget from layout when disabled."""
        if not self.astronomy_widget:
            return
            
        central_widget = self.centralWidget()
        if central_widget:
            from PySide6.QtWidgets import QVBoxLayout
            layout = central_widget.layout()
            
            if isinstance(layout, QVBoxLayout):
                # Check if widget is in the layout and remove it
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == self.astronomy_widget:
                        layout.removeWidget(self.astronomy_widget)
                        self.astronomy_widget.setVisible(False)
                        logger.info("Astronomy widget removed from layout")
                        break

    def _ensure_weather_widget_in_layout(self):
        """Ensure weather widget is added to layout at the correct position (first position)."""
        if not self.weather_widget:
            return
            
        central_widget = self.centralWidget()
        if central_widget:
            from PySide6.QtWidgets import QVBoxLayout
            layout = central_widget.layout()
            
            if isinstance(layout, QVBoxLayout):
                # Check if widget is already in the layout
                is_in_layout = False
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == self.weather_widget:
                        is_in_layout = True
                        break
                
                if not is_in_layout:
                    # Add weather widget at the beginning (index 0)
                    layout.insertWidget(0, self.weather_widget)
                    self.weather_widget.setVisible(True)
                    logger.info("Weather widget added to layout at position 0")

    def _remove_weather_widget_from_layout(self):
        """Remove weather widget from layout when hidden."""
        if not self.weather_widget:
            return
            
        central_widget = self.centralWidget()
        if central_widget:
            from PySide6.QtWidgets import QVBoxLayout
            layout = central_widget.layout()
            
            if isinstance(layout, QVBoxLayout):
                # Check if widget is in the layout and remove it
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == self.weather_widget:
                        layout.removeWidget(self.weather_widget)
                        self.weather_widget.setVisible(False)
                        logger.info("Weather widget removed from layout")
                        break

    def _show_astronomy_enabled_message(self):
        """Show the astronomy enabled success message."""
        from PySide6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Astronomy Enabled")
        msg_box.setText("Astronomy integration has been enabled! "
                       "You'll now see space events and astronomical data in your app.")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
                color: #1976d2;
            }
            QMessageBox QLabel {
                color: #1976d2;
                background-color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                color: #1976d2;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #1976d2;
            }
            QMessageBox QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
        """)
        msg_box.exec()

    def showEvent(self, event):
        """Handle window show event - trigger astronomy data fetch when UI is displayed."""
        super().showEvent(event)

        # Only fetch astronomy data once when window is first shown
        if not hasattr(self, "_astronomy_data_fetched"):
            self._astronomy_data_fetched = True
            if self.astronomy_manager:
                logger.debug("UI displayed - emitting astronomy manager ready signal")
                self.astronomy_manager_ready.emit()

    def resizeEvent(self, event):
        """Handle window resize event - reposition header buttons."""
        super().resizeEvent(event)
        # Reposition the header buttons when window is resized
        self.position_header_buttons()

    def closeEvent(self, event):
        """Handle window close event."""
        logger.debug("Application closing")

        # Shutdown weather manager if it exists
        if self.weather_manager:
            try:
                self.weather_manager.shutdown()
                logger.debug("Weather manager shutdown complete")
            except Exception as e:
                logger.warning(f"Error shutting down weather manager: {e}")

        # Shutdown initialization manager if it exists
        if self.initialization_manager:
            try:
                self.initialization_manager.shutdown()
                logger.debug("Initialization manager shutdown complete")
            except Exception as e:
                logger.warning(f"Error shutting down initialization manager: {e}")

        # Shutdown astronomy manager if it exists
        if self.astronomy_manager:
            try:
                self.astronomy_manager.shutdown()
                logger.debug("Astronomy manager shutdown complete")
            except Exception as e:
                logger.warning(f"Error shutting down astronomy manager: {e}")

        event.accept()

    def center_window(self):
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        
        # Calculate center position
        center_x = screen_geometry.center().x() - window_geometry.width() // 2
        center_y = screen_geometry.center().y() - window_geometry.height() // 2
        
        # Move window to center
        self.move(center_x, center_y)
        logger.debug("Window centered on screen")

    def show_train_details(self, train_data: TrainData):
        """
        Show detailed train information dialog.
        
        Args:
            train_data: Train data to display in detail
        """
        try:
            dialog = TrainDetailDialog(
                train_data,
                self.theme_manager.current_theme,
                self
            )
            dialog.exec()
            logger.info(f"Showed train details for {train_data.destination}")
        except Exception as e:
            logger.error(f"Failed to show train details: {e}")
            self.show_error_message("Train Details Error", f"Failed to show train details: {e}")

    def show_route_details(self, train_data: TrainData):
        """
        Show route display dialog with all calling points.
        
        Args:
            train_data: Train data to display route for
        """
        try:
            # Get train manager from main.py if available
            train_manager = getattr(self, 'train_manager', None)
            
            dialog = RouteDisplayDialog(
                train_data,
                self.theme_manager.current_theme,
                self,
                train_manager
            )
            dialog.exec()
            logger.info(f"Showed route details for {train_data.destination}")
        except Exception as e:
            logger.error(f"Failed to show route details: {e}")
            self.show_error_message("Route Details Error", f"Failed to show route details: {e}")

    def _start_optimized_initialization(self) -> None:
        """Start the optimized widget initialization process."""
        if self.initialization_manager:
            self.initialization_manager.initialize_widgets(self)
            logger.info("Optimized widget initialization started")
        else:
            logger.warning("Cannot start optimized initialization: no initialization manager")

    def _on_initialization_completed(self) -> None:
        """Handle completion of optimized widget initialization."""
        logger.info("Optimized widget initialization completed")
        
        # Update managers from initialization manager
        if self.initialization_manager:
            self.weather_manager = self.initialization_manager.weather_manager
            self.astronomy_manager = self.initialization_manager.astronomy_manager

    def _on_nasa_data_ready(self) -> None:
        """Handle NASA data ready signal from parallel fetch."""
        logger.info("NASA data ready from parallel fetch")
        # The astronomy widget will be automatically updated via signals
