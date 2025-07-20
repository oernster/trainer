"""
Main window for the Train Times application.
Author: Oliver Ernster

This module contains the primary application window with theme switching,
menu bar, status bar, and train display area.
"""

import logging
import sys
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
from .widgets.train_list_widget import TrainListWidget
from .widgets.route_display_dialog import RouteDisplayDialog
from .weather_widgets import WeatherWidget
from .astronomy_widgets import AstronomyWidget
from .stations_settings_dialog import StationsSettingsDialog
from .astronomy_settings_dialog import AstronomySettingsDialog
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
    route_changed = Signal(str, str)  # Signal for when route changes (from_name, to_name)
    config_updated = Signal(object)  # Signal for when configuration is updated

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the main window."""
        super().__init__()

        # Make window completely invisible during initialization
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self.hide()  # Explicitly hide the window
        
        # Set a proper background color immediately to prevent white flash
        self.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")
        
        # Additional measures to prevent visibility
        self.setWindowOpacity(0.0)  # Make completely transparent
        self.move(-10000, -10000)   # Move off-screen

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
        self.train_button: Optional[QPushButton] = None

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
        self.initialization_manager.astronomy_data_ready.connect(self._on_astronomy_data_ready)
        
        # Apply theme to all widgets after creation
        self.apply_theme_to_all_widgets()
        self.connect_signals()
        
        # Start optimized widget initialization
        QTimer.singleShot(50, self._start_optimized_initialization)

        logger.debug("Main window initialized")

        # Keep invisible attributes until main.py is ready to show the window
        # The attributes will be removed when show() is called
        logger.debug("Main window initialized but kept invisible until ready")

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
        
        # Unified scaling approach (based on proven Linux implementation)
        if self.is_small_screen:
            self.ui_scale_factor = 0.65  # 65% scale for all platforms on small screens
        else:
            self.ui_scale_factor = 0.85  # 85% scale for all platforms on normal screens
        
        # Determine initial widget visibility from persisted UI state
        weather_visible = True  # Default
        astronomy_visible = True  # Default
        
        if self.config and hasattr(self.config, 'ui') and self.config.ui:
            weather_visible = self.config.ui.weather_widget_visible
            astronomy_visible = self.config.ui.astronomy_widget_visible
        else:
            # Fallback: Check if astronomy is enabled to determine initial visibility
            astronomy_visible = bool(
                self.config and
                hasattr(self.config, 'astronomy') and
                self.config.astronomy and
                self.config.astronomy.enabled
            )
        
        # Get target window size from persisted config
        default_width, default_height = self._get_target_window_size(weather_visible, astronomy_visible)
        
        if self.is_small_screen:
            # Apply unified scaling for small screens (Linux approach)
            min_width = int(900 * 0.65)  # 585
            min_height = int(450 * 0.65)  # 292
            default_width = int(default_width * 0.65)
            default_height = int(default_height * 0.65)
            
            logger.info(f"Small screen detected ({screen_width}x{screen_height}), using scaled window size: {default_width}x{default_height} (weather={weather_visible}, astronomy={astronomy_visible})")
        else:
            # Set reasonable minimums for large screens (Linux approach)
            min_width = int(900 * 0.85)  # 765
            min_height = int(450 * 0.85)  # 382
            
            logger.debug(f"Large screen detected ({screen_width}x{screen_height}), using persisted window size: {default_width}x{default_height} (weather={weather_visible}, astronomy={astronomy_visible})")
        
        self.setMinimumSize(min_width, min_height)
        
        # Unified window sizing (based on proven Linux implementation)
        if self.is_small_screen:
            # Smaller default size for small screens - reduced height to fit train widgets
            self.resize(int(1100 * 0.65), int(1100 * 0.65))  # 715x715 - reduced from 780
        else:
            # Slightly reduced for normal screens
            self.resize(int(1100 * 0.85), int(1100 * 0.85))  # 935x935 - reduced from 1020
        
        # Center the window on the screen
        self.center_window()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with minimal spacing for very compact UI
        layout = QVBoxLayout(central_widget)
        
        # Unified margins and spacing (based on proven Linux implementation)
        margin = int(4 * self.ui_scale_factor)
        layout.setContentsMargins(margin, margin, margin, margin)
        # Minimal spacing between widgets
        scaled_spacing = int(3 * self.ui_scale_factor)
        
        layout.setSpacing(scaled_spacing)

        # Weather widget (always create, show/hide based on config)
        self.weather_widget = WeatherWidget(scale_factor=self.ui_scale_factor)
        
        # Unified widget margins (based on proven Linux implementation)
        self.weather_widget.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.weather_widget)

        # Set initial visibility based on persisted UI state
        if self.config and hasattr(self.config, 'ui') and self.config.ui:
            self.weather_widget.setVisible(self.config.ui.weather_widget_visible)
            logger.debug(f"Weather widget visibility restored from config: {self.config.ui.weather_widget_visible}")
        else:
            # Fallback: Hide initially if weather is disabled
            if not (
                self.config
                and hasattr(self.config, "weather")
                and self.config.weather
                and self.config.weather.enabled
            ):
                self.weather_widget.hide()

        # Astronomy widget (create and show by default, hide if disabled)
        self.astronomy_widget = AstronomyWidget(scale_factor=self.ui_scale_factor)
        
        # Unified widget margins (based on proven Linux implementation)
        if self.is_small_screen:
            # Minimal margins for small screens
            self.astronomy_widget.setContentsMargins(0, 0, 0, 2)
        else:
            self.astronomy_widget.setContentsMargins(0, 0, 0, 5)
        
        layout.addWidget(self.astronomy_widget)

        # Hide astronomy widget if astronomy is disabled in config
        if (
            self.config
            and hasattr(self.config, "astronomy")
            and self.config.astronomy
            and not self.config.astronomy.enabled
        ):
            self.astronomy_widget.hide()
            logger.debug("Astronomy widget hidden (astronomy disabled in config)")
        else:
            logger.debug("Astronomy widget shown (astronomy enabled or no config)")

        # Train list with extended capacity and reduced top margin for compact layout
        # Get current preferences from config
        current_preferences = self._get_current_preferences()
        self.train_list_widget = TrainListWidget(max_trains=50, preferences=current_preferences)
        
        # Unified widget margins (based on proven Linux implementation)
        if self.is_small_screen:
            # Minimal top margin for small screens
            self.train_list_widget.setContentsMargins(0, 2, 0, 0)
        else:
            self.train_list_widget.setContentsMargins(0, 5, 0, 0)
        
        # Train list widget will expand to fill available space
        # Give it a stretch factor to ensure it gets remaining space
        layout.addWidget(self.train_list_widget, 1)  # stretch factor of 1

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

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("&Settings")

        stations_action = QAction("&Stations...", self)
        stations_action.setShortcut(QKeySequence("Ctrl+S"))
        stations_action.setStatusTip("Configure station settings, display, and refresh options")
        stations_action.triggered.connect(self.show_stations_settings_dialog)
        settings_menu.addAction(stations_action)

        astronomy_action = QAction("&Astronomy...", self)
        astronomy_action.setShortcut(QKeySequence("Ctrl+A"))
        astronomy_action.setStatusTip("Configure astronomy settings and link preferences")
        astronomy_action.triggered.connect(self.show_astronomy_settings_dialog)
        settings_menu.addAction(astronomy_action)

        # View menu removed - reverting to pre-menu checkbox state

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
        """Setup header buttons (theme, astronomy toggle, and train settings) in top-right corner."""
        # Create theme button (150% bigger: 32 * 1.5 = 48)
        self.theme_button = QPushButton(self.theme_manager.get_theme_icon(), self)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setToolTip(self.theme_manager.get_theme_tooltip())
        self.theme_button.setFixedSize(48, 48)
        
        # Create astronomy settings button (150% bigger: 32 * 1.5 = 48)
        self.astronomy_button = QPushButton("🔭", self)
        self.astronomy_button.clicked.connect(self.show_astronomy_settings_dialog)
        self.astronomy_button.setToolTip("Astronomy Settings")
        self.astronomy_button.setFixedSize(48, 48)
        
        # Create train settings button (150% bigger: 32 * 1.5 = 48)
        self.train_button = QPushButton("🚅", self)
        self.train_button.clicked.connect(self.show_stations_settings_dialog)
        self.train_button.setToolTip("Train Settings")
        self.train_button.setFixedSize(48, 48)
        
        # Apply styling to all buttons
        self.apply_header_button_styling()
        
        # Position the buttons in the top-right corner
        self.position_header_buttons()
        
        # Make sure the buttons stay on top
        self.theme_button.raise_()
        self.astronomy_button.raise_()
        self.train_button.raise_()
        self.theme_button.show()
        self.astronomy_button.show()
        self.train_button.show()

    def get_astronomy_icon(self):
        """Get astronomy button icon (always telescope for settings)."""
        return "🔭"

    def get_astronomy_tooltip(self):
        """Get astronomy button tooltip (always settings)."""
        return "Astronomy Settings"

    def apply_header_button_styling(self):
        """Apply styling to header buttons (theme, astronomy, and train)."""
        # Get current theme colors
        if self.theme_manager.current_theme == "dark":
            button_style = """
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px;
                font-size: 24px;
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
                font-size: 24px;
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
        if self.train_button:
            self.train_button.setStyleSheet(button_style)

    def apply_theme_button_styling(self):
        """Apply styling to the standalone theme button (legacy method)."""
        # Delegate to the new header button styling method
        self.apply_header_button_styling()

    def position_header_buttons(self):
        """Position header buttons (theme, astronomy, and train) in the top-right corner."""
        button_width = 48  # Updated for 150% bigger buttons
        button_spacing = 12  # Increased spacing proportionally (8 * 1.5 = 12)
        right_margin = 12    # Increased margin proportionally (8 * 1.5 = 12)
        top_margin = 12      # Increased margin proportionally (8 * 1.5 = 12)
        
        if self.astronomy_button:
            # Astronomy button (rightmost)
            astro_x = self.width() - button_width - right_margin
            self.astronomy_button.move(astro_x, top_margin)
        
        if self.train_button:
            # Train button (middle - left of astronomy button)
            train_x = self.width() - (button_width * 2) - button_spacing - right_margin
            self.train_button.move(train_x, top_margin)
        
        if self.theme_button:
            # Theme button (leftmost - left of train button)
            theme_x = self.width() - (button_width * 3) - (button_spacing * 2) - right_margin
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
        
        # Get target size from persisted UI config or calculate defaults
        target_width, target_height = self._get_target_window_size(weather_visible, astronomy_visible)
        
        # Apply scaling for small screens
        if self.is_small_screen:
            target_width = int(target_width * 0.8)
            target_height = int(target_height * 0.8)
        
        # Always force resize regardless of current size
        current_height = self.height()
        current_width = self.width()
        
        # CRITICAL FIX: Temporarily remove minimum size constraint to allow ultra-aggressive shrinking
        self.setMinimumSize(0, 0)
        
        # Force resize to target size
        self.resize(target_width, target_height)
        
        # CRITICAL FIX: Restore a reasonable minimum size to prevent UI truncation
        # This ensures widgets remain usable while still allowing dynamic resizing
        min_width = 600   # Increased minimum width for better astronomy widget display
        min_height = 450  # Increased minimum height to prevent severe truncation
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
        
        logger.info(f"Window FORCED resize from {current_width}x{current_height} to {target_width}x{target_height} and recentered (visible: {', '.join(widget_status)})")

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

            # CRITICAL FIX: Don't override user's manual visibility preference
            # Only set visibility if this is the first time AND user hasn't manually hidden the widget
            if self.weather_widget and not hasattr(self, '_weather_system_initialized'):
                if not hasattr(self.weather_widget, '_user_manually_hidden') or not self.weather_widget._user_manually_hidden:
                    # Don't override persisted UI state during system initialization
                    # Only set visibility if no UI config exists
                    if not (self.config and hasattr(self.config, 'ui') and self.config.ui):
                        self.weather_widget.setVisible(enabled)
                        logger.debug(f"Weather widget visibility set to {enabled} (first weather system setup, no UI config)")
                    else:
                        logger.debug("Weather widget visibility preserved from UI config during system setup")
                else:
                    logger.debug("Weather widget visibility preserved during system setup (user manually hidden)")
                self._weather_system_initialized = True
            elif self.weather_widget:
                logger.debug("Weather widget visibility preserved (user preference)")

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
                self.astronomy_widget.astronomy_link_clicked.connect(
                    self.on_astronomy_link_clicked
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
                self.astronomy_widget.astronomy_link_clicked.connect(
                    self.on_astronomy_link_clicked
                )

                # Update astronomy widget config
                self.astronomy_widget.update_config(self.config.astronomy)

            # Only initialize astronomy manager if astronomy is enabled
            if self.config.astronomy.enabled:
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
        """Toggle astronomy integration with smart API key detection (legacy method - now unused)."""
        # This method is no longer used since astronomy button now opens settings dialog
        # Keeping for compatibility but functionality moved to settings dialog
        logger.info("Astronomy toggle called - redirecting to settings dialog")
        self.show_astronomy_settings_dialog()

    def on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        self.apply_theme()

        # Update header buttons
        if self.theme_button:
            self.theme_button.setText(self.theme_manager.get_theme_icon())
            self.theme_button.setToolTip(self.theme_manager.get_theme_tooltip())
        if self.astronomy_button:
            self.astronomy_button.setText("🔭")
            self.astronomy_button.setToolTip("Astronomy Settings")
        if self.train_button:
            self.train_button.setText("🚅")
            self.train_button.setToolTip("Train Settings")
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

        # Update astronomy widget (only if it exists)
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

        # Apply theme to astronomy widget (only if it exists)
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
                        logger.info("Manual astronomy refresh requested (async task created)")
                except RuntimeError:
                    # No running loop, create a new one
                    def run_refresh():
                        # Additional null check to satisfy Pylance
                        if self.astronomy_manager:
                            asyncio.run(self.astronomy_manager.refresh_astronomy())

                    # Use QTimer to run in next event loop iteration
                    QTimer.singleShot(0, run_refresh)
                    logger.info("Manual astronomy refresh scheduled (QTimer)")
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

    def on_astronomy_link_clicked(self, url: str):
        """Handle astronomy link clicks."""
        logger.info(f"Astronomy link clicked: {url}")
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
            # Get station database from train manager if available
            station_db = getattr(self.train_manager, 'station_database', None) if hasattr(self, 'train_manager') else None
            dialog = StationsSettingsDialog(self, station_db, self.config_manager, self.theme_manager)
            dialog.settings_changed.connect(self.on_settings_saved)
            
            # Connect dialog signals for immediate UI updates during preference changes
            if hasattr(dialog, 'route_updated'):
                dialog.route_updated.connect(self._on_dialog_route_updated)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to show stations settings dialog: {e}")
            self.show_error_message("Settings Error", f"Failed to open stations settings: {e}")

    def show_astronomy_settings_dialog(self):
        """Show astronomy settings dialog."""
        try:
            dialog = AstronomySettingsDialog(self.config_manager, self, self.theme_manager)
            dialog.settings_saved.connect(self.on_settings_saved)
            dialog.astronomy_enable_requested.connect(self.on_astronomy_enable_requested)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to show astronomy settings dialog: {e}")
            self.show_error_message("Settings Error", f"Failed to open astronomy settings: {e}")

    def on_settings_saved(self):
        """Handle settings saved event."""
        try:
            # Store old settings for comparison
            old_time_window = None
            old_train_lookahead = None
            old_avoid_walking = None
            old_max_walking_distance = None
            old_prefer_direct = None
            old_max_changes = None
            
            if self.config:
                if hasattr(self.config, 'display'):
                    old_time_window = self.config.display.time_window_hours
                old_train_lookahead = getattr(self.config, 'train_lookahead_hours', None)
                old_avoid_walking = getattr(self.config, 'avoid_walking', None)
                old_max_walking_distance = getattr(self.config, 'max_walking_distance_km', None)
                old_prefer_direct = getattr(self.config, 'prefer_direct', None)
                old_max_changes = getattr(self.config, 'max_changes', None)
            
            # Store current theme before reloading config
            current_theme = self.theme_manager.current_theme
            
            # Reload configuration
            self.config = self.config_manager.load_config()

            # GUARANTEED FIX: Always preserve the current theme from theme manager
            if self.config:
                # Force the theme to be what's currently active in the UI
                self.config.display.theme = current_theme
                self.theme_manager.set_theme(current_theme)
                
                # Save the config again with the correct theme
                self.config_manager.save_config(self.config)
                
                # Emit config updated signal to update train manager
                self.config_updated.emit(self.config)
                
                # Check for changes that require train data refresh
                needs_refresh = False
                
                # Check display time window change
                if hasattr(self.config, 'display') and self.config.display:
                    new_time_window = self.config.display.time_window_hours
                    if old_time_window != new_time_window:
                        logger.info(f"Display time window changed from {old_time_window} to {new_time_window} hours")
                        needs_refresh = True
                
                # Check train lookahead time change
                new_train_lookahead = getattr(self.config, 'train_lookahead_hours', None)
                if old_train_lookahead != new_train_lookahead:
                    logger.info(f"Train look-ahead time changed from {old_train_lookahead} to {new_train_lookahead} hours")
                    needs_refresh = True
                
                # Check route preference changes that affect route calculation
                new_avoid_walking = getattr(self.config, 'avoid_walking', None)
                if old_avoid_walking != new_avoid_walking:
                    logger.info(f"Avoid walking preference changed from {old_avoid_walking} to {new_avoid_walking}")
                    needs_refresh = True
                
                new_max_walking_distance = getattr(self.config, 'max_walking_distance_km', None)
                if old_max_walking_distance != new_max_walking_distance:
                    logger.info(f"Max walking distance changed from {old_max_walking_distance} to {new_max_walking_distance} km")
                    needs_refresh = True
                
                new_prefer_direct = getattr(self.config, 'prefer_direct', None)
                if old_prefer_direct != new_prefer_direct:
                    logger.info(f"Prefer direct routes changed from {old_prefer_direct} to {new_prefer_direct}")
                    needs_refresh = True
                
                new_max_changes = getattr(self.config, 'max_changes', None)
                if old_max_changes != new_max_changes:
                    logger.info(f"Max changes preference changed from {old_max_changes} to {new_max_changes}")
                    needs_refresh = True
                
                # Update train list widget preferences if they changed
                if self.train_list_widget:
                    current_preferences = self._get_current_preferences()
                    self.train_list_widget.set_preferences(current_preferences)
                    logger.info("Updated train list widget preferences")
                
                # Trigger refresh if any setting that affects train data changed
                if needs_refresh:
                    self.refresh_requested.emit()
                    logger.info("Refreshing train data for new preference settings")
                
                # Update train manager route if stations changed
                # This signal will be connected from main.py
                self.route_changed.emit(self.config.stations.from_name, self.config.stations.to_name)
                
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
                            # CRITICAL FIX: Don't override user's manual visibility preference during settings save
                            # Never automatically change visibility when user has manually hidden widgets
                            if not hasattr(self.weather_widget, '_user_manually_hidden') or not self.weather_widget._user_manually_hidden:
                                # Only set visibility if user hasn't manually hidden the widget
                                if not hasattr(self, '_weather_settings_applied'):
                                    self.weather_widget.setVisible(self.config.weather.enabled)
                                    self._weather_settings_applied = True
                                    logger.debug(f"Weather widget visibility set to {self.config.weather.enabled} (first settings save)")
                                else:
                                    logger.debug("Weather widget visibility preserved during settings update (no manual override)")
                            else:
                                logger.debug("Weather widget visibility preserved during settings update (user manually hidden)")

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
                        if not self.astronomy_manager:
                            # Astronomy was enabled, initialize manager
                            needs_reinit = True
                            needs_data_fetch = True
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
                    
                    # ADDITIONAL FIX: Also trigger data fetch if astronomy was just enabled
                    elif (self.config.astronomy.enabled and
                          self.astronomy_manager):
                        logger.info("Astronomy enabled - triggering data fetch")
                        self.astronomy_manager_ready.emit()
                    
                    # IMMEDIATE REFRESH: Force immediate astronomy data refresh after settings save
                    if (self.config.astronomy.enabled and self.astronomy_manager):
                        logger.info("Forcing immediate astronomy refresh after settings save")
                        self.refresh_astronomy()

                    # Always update astronomy widget configuration
                    if self.astronomy_widget:
                        logger.info(f"Updating astronomy widget with config: enabled={self.config.astronomy.enabled}, categories={self.config.astronomy.enabled_link_categories}")
                        self.astronomy_widget.update_config(self.config.astronomy)
                        # Buttons are now always visible - no need to update visibility
                        logger.info("Updated astronomy widget configuration")
                        
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
                        
                        # Menu action state update removed - no longer using menu toggles

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
    
    def _on_dialog_route_updated(self, route_data: dict):
        """Handle route updates from the settings dialog during preference changes."""
        try:
            logger.info("Route updated from settings dialog - triggering immediate refresh")
            
            # Trigger immediate refresh of train data
            self.refresh_requested.emit()
            
            # Also emit route_changed signal if we have the route data
            if route_data and 'full_path' in route_data and len(route_data['full_path']) >= 2:
                from_station = route_data['full_path'][0]
                to_station = route_data['full_path'][-1]
                self.route_changed.emit(from_station, to_station)
                logger.info(f"Emitted route_changed signal: {from_station} → {to_station}")
            
        except Exception as e:
            logger.error(f"Error handling dialog route update: {e}")

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

    # Widget visibility toggle methods removed - reverting to pre-menu checkbox state

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

    def _sync_menu_states(self):
        """Synchronize menu action checked states with actual widget visibility - REMOVED."""
        # Menu toggle actions removed - this method is now a no-op
        pass

    def _get_target_window_size(self, weather_visible: bool, astronomy_visible: bool) -> tuple[int, int]:
        """Get target window size based on widget visibility state from persisted config."""
        if self.config and hasattr(self.config, 'ui') and self.config.ui:
            if weather_visible and astronomy_visible:
                return self.config.ui.window_size_both_visible
            elif weather_visible:
                return self.config.ui.window_size_weather_only
            elif astronomy_visible:
                return self.config.ui.window_size_astronomy_only
            else:
                return self.config.ui.window_size_trains_only
        else:
            # Fallback to default sizes if no config - properly sized for all widgets
            # Unified default sizes (based on proven Linux implementation)
            if self.is_small_screen:
                # Smaller for small screens - reduced heights to fit train widgets
                if weather_visible and astronomy_visible:
                    return (int(1100 * 0.65), int(1100 * 0.65))  # 715x715 - reduced from 780
                elif weather_visible:
                    return (int(1100 * 0.65), int(750 * 0.65))   # 715x488 - reduced from 520
                elif astronomy_visible:
                    return (int(1100 * 0.65), int(850 * 0.65))   # 715x553 - reduced from 585
                else:
                    return (int(1100 * 0.65), int(550 * 0.65))   # 715x358 - reduced from 390
            else:
                # Slightly reduced for normal screens
                if weather_visible and astronomy_visible:
                    return (int(1100 * 0.85), int(1100 * 0.85))  # 935x935 - reduced from 1020
                elif weather_visible:
                    return (int(1100 * 0.85), int(750 * 0.85))   # 935x638 - reduced from 680
                elif astronomy_visible:
                    return (int(1100 * 0.85), int(850 * 0.85))   # 935x723 - reduced from 765
                else:
                    return (int(1100 * 0.85), int(550 * 0.85))   # 935x468 - reduced from 510

    def _save_ui_state(self):
        """Save current UI widget visibility states and window size to configuration."""
        if self.config and hasattr(self.config, 'ui') and self.config.ui:
            # Update UI state in config
            if self.weather_widget:
                self.config.ui.weather_widget_visible = self.weather_widget.isVisible()
            if self.astronomy_widget:
                self.config.ui.astronomy_widget_visible = self.astronomy_widget.isVisible()
            
            # Save current window size for the current widget state
            current_size = (self.width(), self.height())
            weather_visible = self.weather_widget.isVisible() if self.weather_widget else False
            astronomy_visible = self.astronomy_widget.isVisible() if self.astronomy_widget else False
            
            if weather_visible and astronomy_visible:
                self.config.ui.window_size_both_visible = current_size
            elif weather_visible:
                self.config.ui.window_size_weather_only = current_size
            elif astronomy_visible:
                self.config.ui.window_size_astronomy_only = current_size
            else:
                self.config.ui.window_size_trains_only = current_size
            
            # Save to file
            try:
                self.config_manager.save_config(self.config)
                logger.debug(f"UI state saved: weather={self.config.ui.weather_widget_visible}, astronomy={self.config.ui.astronomy_widget_visible}, size={current_size}")
            except Exception as e:
                logger.error(f"Failed to save UI state: {e}")

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
                    self._sync_menu_states()  # Sync menu after visibility change
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
                        self._sync_menu_states()  # Sync menu after visibility change
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
                    self._sync_menu_states()  # Sync menu after visibility change
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
                        self._sync_menu_states()  # Sync menu after visibility change
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
        
        # Center window on all platforms when first shown (unified approach)
        if not hasattr(self, '_centered'):
            self._centered = True
            self._center_on_screen()

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
        """Handle window close event with enhanced error handling."""
        try:
            logger.debug("Application closing - starting main window cleanup")

            # Save UI state before closing
            try:
                self._save_ui_state()
                logger.debug("UI state saved successfully")
            except Exception as e:
                logger.warning(f"Error saving UI state: {e}")

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

            # Stop all QTimers in this window
            try:
                from PySide6.QtCore import QTimer
                timers_stopped = 0
                for timer in self.findChildren(QTimer):
                    try:
                        if timer.isActive():
                            timer.stop()
                            timers_stopped += 1
                    except RuntimeError as timer_error:
                        logger.warning(f"Error stopping timer: {timer_error}")
                
                if timers_stopped > 0:
                    logger.debug(f"Stopped {timers_stopped} QTimers in main window")
                else:
                    logger.debug("No active QTimers found in main window")
                    
            except Exception as timer_cleanup_error:
                logger.warning(f"Error during timer cleanup: {timer_cleanup_error}")

            # Clean up any remaining threads (focus on non-daemon threads only)
            try:
                import threading
                import time
                
                active_threads = threading.active_count()
                if active_threads > 1:  # Main thread + others
                    # Separate daemon and non-daemon threads
                    non_daemon_threads = []
                    daemon_count = 0
                    
                    for thread in threading.enumerate():
                        if thread != threading.current_thread():
                            if thread.daemon:
                                daemon_count += 1
                            else:
                                non_daemon_threads.append(thread)
                    
                    # Only handle non-daemon threads (these can prevent shutdown)
                    if non_daemon_threads:
                        logger.debug(f"🔄 Gracefully stopping {len(non_daemon_threads)} non-daemon threads...")
                        for thread in non_daemon_threads:
                            try:
                                thread.join(timeout=0.5)
                                if not thread.is_alive():
                                    logger.debug(f"✅ Non-daemon thread {thread.name} stopped")
                                else:
                                    logger.warning(f"⚠️ Non-daemon thread {thread.name} did not stop gracefully")
                            except Exception as join_error:
                                logger.warning(f"⚠️ Error joining thread {thread.name}: {join_error}")
                    
                    # Daemon threads are handled silently (they don't prevent shutdown)
                    # No need to actively terminate daemon threads as they won't block shutdown
                    if daemon_count > 0:
                        logger.debug(f"ℹ️ {daemon_count} daemon threads will be cleaned up automatically on exit")
                    
                    # Brief pause for cleanup
                    time.sleep(0.1)
                    
                    # Final check - only warn about non-daemon threads
                    final_non_daemon = []
                    for thread in threading.enumerate():
                        if thread != threading.current_thread() and not thread.daemon:
                            final_non_daemon.append(thread)
                    
                    if final_non_daemon:
                        logger.warning(f"⚠️ {len(final_non_daemon)} non-daemon threads still active after cleanup")
                        for thread in final_non_daemon:
                            logger.warning(f"  - Active thread: {thread.name} (alive: {thread.is_alive()})")
                    else:
                        logger.debug("✅ All critical threads cleaned up successfully")
                else:
                    logger.debug("✅ No background threads to clean up")
                    
            except Exception as thread_cleanup_error:
                logger.warning(f"⚠️ Error during thread cleanup in closeEvent: {thread_cleanup_error}")

            # Clear references to prevent memory leaks
            try:
                self.weather_manager = None
                self.astronomy_manager = None
                self.initialization_manager = None
                self.train_manager = None
                logger.debug("Manager references cleared")
            except Exception as ref_error:
                logger.warning(f"Error clearing references: {ref_error}")

            logger.debug("Main window cleanup completed successfully")
            event.accept()
            
        except Exception as close_error:
            logger.error(f"Critical error in closeEvent: {close_error}")
            # Always accept the event to prevent hanging
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
            
        else:
            logger.warning("Cannot start optimized initialization: no initialization manager")

    def _on_initialization_completed(self) -> None:
        """Handle completion of optimized widget initialization."""

        # Update managers from initialization manager
        if self.initialization_manager:
            self.weather_manager = self.initialization_manager.weather_manager
            self.astronomy_manager = self.initialization_manager.astronomy_manager
        
        # Ensure menu states are synchronized with actual widget visibility after initialization
        # Use a slight delay to ensure all visibility changes have been processed
        QTimer.singleShot(50, self._final_menu_sync)
        logger.debug("Final menu sync scheduled after initialization completion")
    
    def _final_menu_sync(self):
        """Final menu synchronization after all initialization is complete."""
        # Ensure both widgets are initialized
        if self.weather_widget and self.astronomy_widget:
            self._sync_menu_states()
            logger.debug("Final menu states synchronized with widget visibility")
            
            # Log current states for debugging
            weather_visible = self.weather_widget.isVisible()
            astronomy_visible = self.astronomy_widget.isVisible()

        else:
            # Retry sync after a short delay if widgets aren't ready
            QTimer.singleShot(100, self._final_menu_sync)
            logger.debug("Widgets not ready for menu sync, retrying in 100ms")

    def _on_astronomy_data_ready(self) -> None:
        """Handle astronomy data ready signal from parallel fetch."""
        
        # The astronomy widget will be automatically updated via signals

    def show(self):
        """Override show to properly remove invisible attributes when ready."""
        # Remove all invisible attributes and restore normal visibility
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        self.setWindowOpacity(1.0)  # Restore full opacity
        
        # Move window back to center before showing
        self.center_window()
        
        # Now show the window normally
        self.setVisible(True)
        super().show()
        logger.debug("Main window shown with all invisible attributes removed")

    def _get_current_preferences(self) -> dict:
        """Get current preferences from configuration."""
        default_preferences = {
            'show_intermediate_stations': True,
            'avoid_walking': False,
            'max_walking_distance_km': 1.0,
            'train_lookahead_hours': 16
        }
        
        if not self.config:
            return default_preferences
        
        # Extract preferences from config
        preferences = {}
        
        # Get show_intermediate_stations from config if available
        preferences['show_intermediate_stations'] = getattr(self.config, 'show_intermediate_stations', default_preferences['show_intermediate_stations'])
        
        # Get route calculation preferences
        preferences['avoid_walking'] = getattr(self.config, 'avoid_walking', default_preferences['avoid_walking'])
        preferences['max_walking_distance_km'] = getattr(self.config, 'max_walking_distance_km', default_preferences['max_walking_distance_km'])
        preferences['train_lookahead_hours'] = getattr(self.config, 'train_lookahead_hours', default_preferences['train_lookahead_hours'])
        
        return preferences
    
    def _center_on_screen(self):
        """Center the window on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2
            self.move(x, y)
            logger.debug(f"Centered main window at ({x}, {y})")
