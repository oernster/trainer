"""
UI Layout Manager for the main window.

This module handles the setup and management of the main window's UI layout,
including widget creation, positioning, and responsive sizing.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QApplication
)
from PySide6.QtCore import QSize
from ..widgets.train_list_widget import TrainListWidget
from ..weather_widgets import WeatherWidget
from ..astronomy_widgets import AstronomyWidget

logger = logging.getLogger(__name__)


class UILayoutManager:
    """
    Manages the main window's UI layout and widget setup.
    
    Handles responsive sizing, widget creation, and layout management
    for the main application window.
    """
    
    def __init__(self, main_window):
        """
        Initialize the UI layout manager.
        
        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        self.ui_scale_factor = 1.0
        self.is_small_screen = False
        
        # Widget references
        self.train_list_widget: Optional[TrainListWidget] = None
        self.weather_widget: Optional[WeatherWidget] = None
        self.astronomy_widget: Optional[AstronomyWidget] = None
        
        logger.debug("UILayoutManager initialized")
    
    def setup_responsive_sizing(self) -> None:
        """Setup responsive sizing based on screen dimensions."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # Calculate responsive window size
        self.is_small_screen = screen_width <= 1440 or screen_height <= 900
        self.ui_scale_factor = 0.8 if self.is_small_screen else 1.0
        
        if self.is_small_screen:
            logger.info(f"Small screen detected ({screen_width}x{screen_height}), using scale factor {self.ui_scale_factor}")
        else:
            logger.debug(f"Large screen detected ({screen_width}x{screen_height}), using normal scaling")
    
    def setup_main_layout(self) -> QWidget:
        """
        Setup the main window layout and create central widget.
        
        Returns:
            QWidget: The central widget with layout configured
        """
        # Setup responsive sizing first
        self.setup_responsive_sizing()
        
        # Create central widget
        central_widget = QWidget()
        
        # Main layout with minimal spacing for compact UI
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        scaled_spacing = int(5 * self.ui_scale_factor)
        layout.setSpacing(scaled_spacing)
        
        # Create and add widgets to layout
        self._create_weather_widget(layout)
        self._create_astronomy_widget(layout)
        self._create_train_list_widget(layout)
        
        logger.debug("Main layout setup completed")
        return central_widget
    
    def _create_weather_widget(self, layout: QVBoxLayout) -> None:
        """Create and configure the weather widget."""
        self.weather_widget = WeatherWidget(scale_factor=self.ui_scale_factor)
        self.weather_widget.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.weather_widget)
        
        # Set initial visibility based on config
        config = getattr(self.main_window, 'config', None)
        if config and hasattr(config, 'ui') and config.ui:
            self.weather_widget.setVisible(config.ui.weather_widget_visible)
            logger.debug(f"Weather widget visibility set from config: {config.ui.weather_widget_visible}")
        elif not (config and hasattr(config, "weather") and config.weather and config.weather.enabled):
            self.weather_widget.hide()
            logger.debug("Weather widget hidden (weather disabled in config)")
    
    def _create_astronomy_widget(self, layout: QVBoxLayout) -> None:
        """Create and configure the astronomy widget."""
        self.astronomy_widget = AstronomyWidget(scale_factor=self.ui_scale_factor)
        self.astronomy_widget.setContentsMargins(0, 0, 0, 5)
        layout.addWidget(self.astronomy_widget)
        
        # Set initial visibility based on config
        config = getattr(self.main_window, 'config', None)
        if (config and hasattr(config, "astronomy") and config.astronomy and not config.astronomy.enabled):
            self.astronomy_widget.hide()
            logger.debug("Astronomy widget hidden (astronomy disabled in config)")
        else:
            logger.debug("Astronomy widget shown (astronomy enabled or no config)")
    
    def _create_train_list_widget(self, layout: QVBoxLayout) -> None:
        """Create and configure the train list widget."""
        self.train_list_widget = TrainListWidget(max_trains=50)
        self.train_list_widget.setContentsMargins(0, 5, 0, 0)
        layout.addWidget(self.train_list_widget)
        logger.debug("Train list widget created and added to layout")
    
    def setup_window_sizing(self) -> None:
        """Setup initial window size and constraints."""
        # Determine initial widget visibility from config
        config = getattr(self.main_window, 'config', None)
        weather_visible = True
        astronomy_visible = True
        
        if config and hasattr(config, 'ui') and config.ui:
            weather_visible = config.ui.weather_widget_visible
            astronomy_visible = config.ui.astronomy_widget_visible
        else:
            # Fallback: Check if astronomy is enabled
            astronomy_visible = bool(
                config and hasattr(config, 'astronomy') and 
                config.astronomy and config.astronomy.enabled
            )
        
        # Get target window size
        default_width, default_height = self._get_target_window_size(weather_visible, astronomy_visible)
        
        # Apply scaling for small screens
        if self.is_small_screen:
            min_width = int(900 * 0.8)  # 720
            min_height = int(450 * 0.8)  # 360
            default_width = int(default_width * 0.8)
            default_height = int(default_height * 0.8)
        else:
            min_width = 900
            min_height = 450
        
        # Set window size and constraints
        self.main_window.setMinimumSize(min_width, min_height)
        self.main_window.resize(1100, 1200)  # Increased height to prevent widget overlap
        
        # Center the window
        self._center_window()
        
        logger.debug(f"Window sizing setup: {default_width}x{default_height} (weather={weather_visible}, astronomy={astronomy_visible})")
    
    def _get_target_window_size(self, weather_visible: bool, astronomy_visible: bool) -> tuple[int, int]:
        """Get target window size based on widget visibility."""
        config = getattr(self.main_window, 'config', None)
        
        if config and hasattr(config, 'ui') and config.ui:
            if weather_visible and astronomy_visible:
                return config.ui.window_size_both_visible
            elif weather_visible:
                return config.ui.window_size_weather_only
            elif astronomy_visible:
                return config.ui.window_size_astronomy_only
            else:
                return config.ui.window_size_trains_only
        else:
            # Fallback to default sizes
            if weather_visible and astronomy_visible:
                return (1100, 1200)
            elif weather_visible:
                return (1100, 800)
            elif astronomy_visible:
                return (1100, 900)
            else:
                return (1100, 600)
    
    def _center_window(self) -> None:
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.main_window.frameGeometry()
        
        # Calculate center position
        center_x = screen_geometry.center().x() - window_geometry.width() // 2
        center_y = screen_geometry.center().y() - window_geometry.height() // 2
        
        # Move window to center
        self.main_window.move(center_x, center_y)
        logger.debug("Window centered on screen")
    
    def update_window_size_for_widgets(self) -> None:
        """Update window size based on currently visible widgets."""
        # Determine which widgets are currently visible
        weather_visible = self.weather_widget.isVisible() if self.weather_widget else False
        astronomy_visible = self.astronomy_widget.isVisible() if self.astronomy_widget else False
        
        # Get target size
        target_width, target_height = self._get_target_window_size(weather_visible, astronomy_visible)
        
        # Apply scaling for small screens
        if self.is_small_screen:
            target_width = int(target_width * 0.8)
            target_height = int(target_height * 0.8)
        
        # Temporarily remove minimum size constraint for aggressive shrinking
        self.main_window.setMinimumSize(0, 0)
        
        # Force resize to target size
        self.main_window.resize(target_width, target_height)
        
        # Restore reasonable minimum size
        min_width = 600
        min_height = 450
        self.main_window.setMinimumSize(min_width, min_height)
        
        # Center the window after resizing
        self._center_window()
        
        # Log the resize
        widget_status = []
        if weather_visible:
            widget_status.append("weather")
        if astronomy_visible:
            widget_status.append("astronomy")
        if not widget_status:
            widget_status.append("trains only")
        
        logger.info(f"Window resized to {target_width}x{target_height} (visible: {', '.join(widget_status)})")
    
    def get_widgets(self) -> dict:
        """
        Get references to all managed widgets.
        
        Returns:
            dict: Dictionary containing widget references
        """
        return {
            'train_list_widget': self.train_list_widget,
            'weather_widget': self.weather_widget,
            'astronomy_widget': self.astronomy_widget
        }
    
    def setup_ui(self) -> None:
        """Setup the main UI components."""
        # Set window title
        from version import __app_display_name__
        self.main_window.setWindowTitle(__app_display_name__)
        
        # Setup main layout
        central_widget = self.setup_main_layout()
        self.main_window.setCentralWidget(central_widget)
        
        # Setup window sizing
        self.setup_window_sizing()
        
        # Setup menu bar and header buttons
        self.setup_menu_bar()
        self.setup_header_buttons()
        
        logger.debug("Main UI setup completed")
    
    def setup_application_icon(self) -> None:
        """Setup application icon using Unicode train emoji."""
        from PySide6.QtGui import QPixmap, QPainter, QFont, QIcon
        from PySide6.QtCore import Qt
        from version import __app_display_name__
        
        # Set window title without emoji (emoji is already in the window icon)
        self.main_window.setWindowTitle(__app_display_name__)
        
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
            self.main_window.setWindowIcon(icon)
            
            logger.debug("Window icon set using Unicode train emoji")
            
        except Exception as e:
            logger.warning(f"Failed to create emoji window icon: {e}")
            logger.info("Using Unicode train emoji in window title only")
    
    def setup_menu_bar(self) -> None:
        """Setup application menu bar."""
        from PySide6.QtGui import QAction, QKeySequence
        
        # Ensure we're using the proper QMainWindow menu bar
        menubar = self.main_window.menuBar()

        # Clear any existing menu items
        menubar.clear()

        # Set menu bar properties to ensure proper display
        menubar.setNativeMenuBar(False)  # Force Qt menu bar on all platforms

        # File menu
        file_menu = menubar.addMenu("&File")

        exit_action = QAction("E&xit", self.main_window)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("&Settings")

        stations_action = QAction("&Stations...", self.main_window)
        stations_action.setShortcut(QKeySequence("Ctrl+S"))
        stations_action.setStatusTip("Configure station settings, display, and refresh options")
        stations_action.triggered.connect(self.main_window.show_stations_settings_dialog)
        settings_menu.addAction(stations_action)

        astronomy_action = QAction("&Astronomy...", self.main_window)
        astronomy_action.setShortcut(QKeySequence("Ctrl+A"))
        astronomy_action.setStatusTip("Configure astronomy settings and link preferences")
        astronomy_action.triggered.connect(self.main_window.show_astronomy_settings_dialog)
        settings_menu.addAction(astronomy_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self.main_window)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.main_window.show_about_dialog)
        help_menu.addAction(about_action)

        # Apply menu bar styling
        self.apply_menu_bar_styling(menubar)
        
        logger.debug("Menu bar setup completed")
    
    def setup_header_buttons(self) -> None:
        """Setup header buttons (theme, astronomy toggle, and train settings) in top-right corner."""
        from PySide6.QtWidgets import QPushButton
        
        # Create theme button (150% bigger: 32 * 1.5 = 48)
        theme_manager = getattr(self.main_window, 'theme_manager', None)
        if theme_manager:
            self.theme_button = QPushButton(theme_manager.get_theme_icon(), self.main_window)
            self.theme_button.clicked.connect(self.main_window.toggle_theme)
            self.theme_button.setToolTip(theme_manager.get_theme_tooltip())
            self.theme_button.setFixedSize(48, 48)
        
        # Create astronomy settings button (150% bigger: 32 * 1.5 = 48)
        self.astronomy_button = QPushButton("🔭", self.main_window)
        self.astronomy_button.clicked.connect(self.main_window.show_astronomy_settings_dialog)
        self.astronomy_button.setToolTip("Astronomy Settings")
        self.astronomy_button.setFixedSize(48, 48)
        
        # Create train settings button (150% bigger: 32 * 1.5 = 48)
        self.train_button = QPushButton("🚅", self.main_window)
        self.train_button.clicked.connect(self.main_window.show_stations_settings_dialog)
        self.train_button.setToolTip("Train Settings")
        self.train_button.setFixedSize(48, 48)
        
        # Apply styling to all buttons
        self.apply_header_button_styling()
        
        # Position the buttons in the top-right corner
        self.position_header_buttons()
        
        # Make sure the buttons stay on top
        if hasattr(self, 'theme_button'):
            self.theme_button.raise_()
            self.theme_button.show()
        self.astronomy_button.raise_()
        self.train_button.raise_()
        self.astronomy_button.show()
        self.train_button.show()
        
        logger.debug("Header buttons setup completed")
    
    def apply_header_button_styling(self) -> None:
        """Apply styling to header buttons (theme, astronomy, and train)."""
        theme_manager = getattr(self.main_window, 'theme_manager', None)
        if not theme_manager:
            return
            
        # Get current theme colors
        if theme_manager.current_theme == "dark":
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
        
        if hasattr(self, 'theme_button'):
            self.theme_button.setStyleSheet(button_style)
        if hasattr(self, 'astronomy_button'):
            self.astronomy_button.setStyleSheet(button_style)
        if hasattr(self, 'train_button'):
            self.train_button.setStyleSheet(button_style)
    
    def position_header_buttons(self) -> None:
        """Position header buttons (theme, astronomy, and train) in the top-right corner."""
        button_width = 48  # Updated for 150% bigger buttons
        button_spacing = 12  # Increased spacing proportionally
        right_margin = 12    # Increased margin proportionally
        top_margin = 12      # Increased margin proportionally
        
        if hasattr(self, 'astronomy_button'):
            # Astronomy button (rightmost)
            astro_x = self.main_window.width() - button_width - right_margin
            self.astronomy_button.move(astro_x, top_margin)
        
        if hasattr(self, 'train_button'):
            # Train button (middle - left of astronomy button)
            train_x = self.main_window.width() - (button_width * 2) - button_spacing - right_margin
            self.train_button.move(train_x, top_margin)
        
        if hasattr(self, 'theme_button'):
            # Theme button (leftmost - left of train button)
            theme_x = self.main_window.width() - (button_width * 3) - (button_spacing * 2) - right_margin
            self.theme_button.move(theme_x, top_margin)
    
    def apply_menu_bar_styling(self, menubar) -> None:
        """Apply styling to the menu bar."""
        theme_manager = getattr(self.main_window, 'theme_manager', None)
        if not theme_manager:
            return
            
        # Get current theme colors
        if theme_manager.current_theme == "dark":
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
    
    def update_theme_elements(self, theme_name: str) -> None:
        """Update theme-related UI elements."""
        # Update header buttons
        theme_manager = getattr(self.main_window, 'theme_manager', None)
        if theme_manager:
            if hasattr(self, 'theme_button'):
                self.theme_button.setText(theme_manager.get_theme_icon())
                self.theme_button.setToolTip(theme_manager.get_theme_tooltip())
            if hasattr(self, 'astronomy_button'):
                self.astronomy_button.setText("🔭")
                self.astronomy_button.setToolTip("Astronomy Settings")
            if hasattr(self, 'train_button'):
                self.train_button.setText("🚅")
                self.train_button.setToolTip("Train Settings")
            self.apply_header_button_styling()

        # Update menu bar styling
        menubar = self.main_window.menuBar()
        if menubar:
            self.apply_menu_bar_styling(menubar)
    
    def handle_resize_event(self, event) -> None:
        """Handle window resize event - reposition header buttons."""
        self.position_header_buttons()