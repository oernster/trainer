"""
Refactored Main window for the Train Times application.
Author: Oliver Ernster

This module contains the primary application window refactored to use
manager classes for better separation of concerns and maintainability.
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
from PySide6.QtGui import QAction, QIcon, QKeySequence, QCloseEvent
from ..models.train_data import TrainData
from ..managers.train_manager import TrainManager
from ..managers.config_manager import ConfigManager, ConfigurationError
from ..managers.theme_manager import ThemeManager
from ..managers.weather_manager import WeatherManager
from ..managers.astronomy_manager import AstronomyManager
from ..managers.initialization_manager import InitializationManager
from .managers import (
    UILayoutManager,
    WidgetLifecycleManager,
    EventHandlerManager,
    SettingsDialogManager
)
from version import __version__, __app_display_name__, get_about_text

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Refactored main application window using manager classes.

    Features:
    - Light/Dark theme switching (defaults to dark)
    - Unicode train emoji (🚂) in window title and about dialog
    - Scheduled train data display
    - 16-hour time window
    - Automatic and manual refresh
    - Modular manager-based architecture
    """

    # Signals
    refresh_requested = Signal()
    theme_changed = Signal(str)
    astronomy_manager_ready = Signal()  # Signal for when astronomy manager is ready
    route_changed = Signal(str, str)  # Signal for when route changes (from_name, to_name)
    config_updated = Signal(object)  # Signal for when configuration is updated

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the main window with manager-based architecture."""
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

        # Initialize core managers
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

        # Initialize UI manager classes
        self.ui_layout_manager = UILayoutManager(self)
        self.widget_lifecycle_manager = WidgetLifecycleManager(self)
        self.event_handler_manager = EventHandlerManager(self)
        self.settings_dialog_manager = SettingsDialogManager(self)

        # Set up manager cross-references
        self.widget_lifecycle_manager.set_ui_layout_manager(self.ui_layout_manager)
        self.event_handler_manager.set_managers(self.ui_layout_manager, self.widget_lifecycle_manager)
        self.settings_dialog_manager.set_managers(self.ui_layout_manager, self.widget_lifecycle_manager)

        # External managers (will be set by main.py)
        self.weather_manager: Optional[WeatherManager] = None
        self.astronomy_manager: Optional[AstronomyManager] = None
        self.initialization_manager: Optional[InitializationManager] = None
        self.train_manager: Optional[TrainManager] = None

        # Setup theme system first to ensure proper styling from the start
        self.setup_theme_system()
        self.apply_theme()

        # Setup UI with theme already applied
        self.ui_layout_manager.setup_ui()
        self.ui_layout_manager.setup_application_icon()
        
        # Initialize the optimized initialization manager
        self.initialization_manager = InitializationManager(self.config_manager, self)
        
        # Connect initialization signals
        self.initialization_manager.initialization_completed.connect(self._on_initialization_completed)
        # self.initialization_manager.astronomy_data_ready.connect(self._on_astronomy_data_ready)
        
        # Apply theme to all widgets after creation
        self.apply_theme_to_all_widgets()
        self.connect_signals()
        
        # Start optimized widget initialization
        QTimer.singleShot(50, self._start_optimized_initialization)

        logger.debug("Main window initialized with manager architecture")

        # Keep invisible attributes until main.py is ready to show the window
        logger.debug("Main window initialized but kept invisible until ready")

    def setup_theme_system(self):
        """Setup theme switching system."""
        # Connect theme change signal
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

    def setup_weather_system(self):
        """Setup weather integration system."""
        self.widget_lifecycle_manager.setup_weather_system()

    def setup_astronomy_system(self):
        """Setup astronomy integration system."""
        self.widget_lifecycle_manager.setup_astronomy_system()

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
        self.ui_layout_manager.update_theme_elements(theme_name)

        # Update train list widget
        widgets = self.ui_layout_manager.get_widgets()
        train_list_widget = widgets.get('train_list_widget')
        if train_list_widget:
            train_list_widget.apply_theme(theme_name)

        # Update weather widget
        weather_widget = widgets.get('weather_widget')
        if weather_widget:
            theme_colors = self._get_theme_colors(theme_name)
            weather_widget.apply_theme(theme_colors)

        # Update astronomy widget
        astronomy_widget = widgets.get('astronomy_widget')
        if astronomy_widget:
            theme_colors = self._get_theme_colors(theme_name)
            astronomy_widget.apply_theme(theme_colors)

        # Emit signal for other components
        self.theme_changed.emit(theme_name)

        logger.info(f"Theme changed to {theme_name}")

    def _get_theme_colors(self, theme_name: str) -> dict:
        """Get theme colors dictionary for widgets."""
        return {
            "background_primary": "#1a1a1a" if theme_name == "dark" else "#ffffff",
            "background_secondary": "#2d2d2d" if theme_name == "dark" else "#f5f5f5",
            "background_hover": "#404040" if theme_name == "dark" else "#e0e0e0",
            "text_primary": "#ffffff" if theme_name == "dark" else "#000000",
            "primary_accent": "#1976d2",
            "border_primary": "#404040" if theme_name == "dark" else "#cccccc",
        }

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
        widgets = self.ui_layout_manager.get_widgets()

        # Apply theme to train list widget
        train_list_widget = widgets.get('train_list_widget')
        if train_list_widget:
            train_list_widget.apply_theme(current_theme)

        # Apply theme to weather widget
        weather_widget = widgets.get('weather_widget')
        if weather_widget:
            theme_colors = self._get_theme_colors(current_theme)
            weather_widget.apply_theme(theme_colors)

        # Apply theme to astronomy widget
        astronomy_widget = widgets.get('astronomy_widget')
        if astronomy_widget:
            theme_colors = self._get_theme_colors(current_theme)
            astronomy_widget.apply_theme(theme_colors)

    def manual_refresh(self):
        """Trigger manual refresh of train data."""
        self.refresh_requested.emit()
        logger.info("Manual refresh requested")

    def refresh_weather(self):
        """Trigger manual weather refresh."""
        self.event_handler_manager.refresh_weather()

    def refresh_astronomy(self):
        """Trigger manual astronomy refresh."""
        self.event_handler_manager.refresh_astronomy()

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
        widgets = self.ui_layout_manager.get_widgets()
        train_list_widget = widgets.get('train_list_widget')
        
        if train_list_widget:
            train_list_widget.update_trains(trains)
            # Connect train selection signal if not already connected
            if not hasattr(self, '_train_selection_connected'):
                train_list_widget.train_selected.connect(self.show_train_details)
                self._train_selection_connected = True
            # Connect route selection signal if not already connected
            if not hasattr(self, '_route_selection_connected'):
                train_list_widget.route_selected.connect(self.show_route_details)
                self._route_selection_connected = True

        logger.debug(f"Updated display with {len(trains)} trains")

    def update_last_update_time(self, timestamp: str):
        """
        Update last update timestamp (header removed - now only logs).

        Args:
            timestamp: Formatted timestamp string
        """
        # Header removed - last update time no longer shown in UI, only logged
        logger.debug(f"Last Updated: {timestamp}")

    def update_connection_status(self, connected: bool, message: str = ""):
        """
        Update connection status.

        Args:
            connected: Whether connected to API
            message: Optional status message
        """
        # Status bar removed - this method is kept for compatibility but does nothing
        pass

    # Event handler delegates
    def on_weather_updated(self, weather_data):
        """Handle weather data update."""
        self.event_handler_manager.on_weather_updated(weather_data)

    def on_weather_error(self, error_message: str):
        """Handle weather error."""
        self.event_handler_manager.on_weather_error(error_message)

    def on_weather_loading_changed(self, is_loading: bool):
        """Handle weather loading state change."""
        self.event_handler_manager.on_weather_loading_changed(is_loading)

    def on_astronomy_updated(self, astronomy_data):
        """Handle astronomy data update."""
        self.event_handler_manager.on_astronomy_updated(astronomy_data)

    def on_astronomy_error(self, error_message: str):
        """Handle astronomy error."""
        self.event_handler_manager.on_astronomy_error(error_message)

    def on_astronomy_loading_changed(self, is_loading: bool):
        """Handle astronomy loading state change."""
        self.event_handler_manager.on_astronomy_loading_changed(is_loading)

    def on_astronomy_link_clicked(self, url: str):
        """Handle astronomy link clicks."""
        self.event_handler_manager.on_astronomy_link_clicked(url)

    # Settings dialog delegates
    def show_stations_settings_dialog(self):
        """Show stations settings dialog."""
        self.settings_dialog_manager.show_stations_settings_dialog()

    def show_astronomy_settings_dialog(self):
        """Show astronomy settings dialog."""
        self.settings_dialog_manager.show_astronomy_settings_dialog()

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
            
            # Reload configuration
            self.config = self.config_manager.load_config()

            # Update theme if changed
            if self.config:
                self.theme_manager.set_theme(self.config.display.theme)
                
                # Emit config updated signal to update train manager
                self.config_updated.emit(self.config)
                
                # Check for changes that require train data refresh
                needs_refresh = self._check_settings_changes_need_refresh(
                    old_time_window, old_train_lookahead, old_avoid_walking,
                    old_max_walking_distance, old_prefer_direct, old_max_changes
                )
                
                # Trigger refresh if any setting that affects train data changed
                if needs_refresh:
                    self.refresh_requested.emit()
                    logger.info("Refreshing train data for new preference settings")
                
                # Update train manager route if stations changed
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
                    self._update_weather_system()

                # Update astronomy system if configuration changed
                if hasattr(self.config, "astronomy") and self.config.astronomy:
                    self._update_astronomy_system()

            logger.info("Settings reloaded after save")

        except ConfigurationError as e:
            logger.error(f"Failed to reload settings: {e}")
            self.show_error_message(
                "Configuration Error", f"Failed to reload settings: {e}"
            )

    def _check_settings_changes_need_refresh(self, old_time_window, old_train_lookahead, 
                                           old_avoid_walking, old_max_walking_distance,
                                           old_prefer_direct, old_max_changes) -> bool:
        """Check if settings changes require train data refresh."""
        needs_refresh = False
        
        # Check display time window change
        if self.config and hasattr(self.config, 'display') and self.config.display:
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
        
        return needs_refresh

    def _update_weather_system(self):
        """Update weather system after configuration change."""
        if not self.config or not hasattr(self.config, 'weather') or not self.config.weather:
            return
            
        if self.config.weather.enabled and not self.weather_manager:
            # Weather was enabled, initialize system
            self.setup_weather_system()
        elif self.weather_manager:
            # Update existing weather manager configuration
            self.weather_manager.update_config(self.config.weather)

            # Update weather widget configuration
            widgets = self.ui_layout_manager.get_widgets()
            weather_widget = widgets.get('weather_widget')
            if weather_widget:
                weather_widget.update_config(self.config.weather)

    def _update_astronomy_system(self):
        """Update astronomy system after configuration change."""
        if not self.config or not hasattr(self.config, 'astronomy') or not self.config.astronomy:
            return
            
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

        # Emit signal to trigger immediate data fetch for new/updated API key
        if needs_data_fetch and self.astronomy_manager:
            logger.info("Emitting astronomy manager ready signal to trigger data fetch")
            self.astronomy_manager_ready.emit()

        # Always update astronomy widget configuration
        widgets = self.ui_layout_manager.get_widgets()
        astronomy_widget = widgets.get('astronomy_widget')
        if astronomy_widget:
            logger.info(f"Updating astronomy widget with config: enabled={self.config.astronomy.enabled}")
            astronomy_widget.update_config(self.config.astronomy)

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
        """Handle astronomy enable request from settings dialog."""
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
        self.widget_lifecycle_manager.ensure_astronomy_widget_in_layout()
        
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
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Astronomy Data Error")
        msg_box.setText(f"Astronomy integration has been enabled, but there was an error loading data:\n\n{error_message}\n\n"
                       "You can try refreshing the data later.")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.exec()
        logger.warning(f"Astronomy error after enable: {error_message}")

    def _show_astronomy_enabled_message(self):
        """Show the astronomy enabled success message."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Astronomy Enabled")
        msg_box.setText("Astronomy integration has been enabled! "
                       "You'll now see space events and astronomical data in your app.")
        msg_box.setIcon(QMessageBox.Icon.Information)
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
        # Delegate to UI layout manager
        self.ui_layout_manager.handle_resize_event(event)

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        self.event_handler_manager.handle_close_event(event)

    def show_train_details(self, train_data: TrainData):
        """
        Show detailed train information dialog.
        
        Args:
            train_data: Train data to display in detail
        """
        try:
            from .train_detail_dialog import TrainDetailDialog
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
            from .widgets.route_display_dialog import RouteDisplayDialog
            dialog = RouteDisplayDialog(
                train_data,
                self.theme_manager.current_theme,
                self,
                self.train_manager
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
        QTimer.singleShot(50, self._final_menu_sync)
        logger.debug("Final menu sync scheduled after initialization completion")
    
    def _final_menu_sync(self):
        """Final menu synchronization after all initialization is complete."""
        widgets = self.ui_layout_manager.get_widgets()
        weather_widget = widgets.get('weather_widget')
        astronomy_widget = widgets.get('astronomy_widget')
        
        # Ensure both widgets are initialized
        if weather_widget and astronomy_widget:
            logger.debug("Final menu states synchronized with widget visibility")
            
            # Log current states for debugging
            weather_visible = weather_widget.isVisible()
            astronomy_visible = astronomy_widget.isVisible()
        else:
            # Retry sync after a short delay if widgets aren't ready
            QTimer.singleShot(100, self._final_menu_sync)
            logger.debug("Widgets not ready for menu sync, retrying in 100ms")

    def show(self):
        """Override show to properly remove invisible attributes when ready."""
        # Remove all invisible attributes and restore normal visibility
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        self.setWindowOpacity(1.0)  # Restore full opacity
        
        # Move window back to center before showing
        self.ui_layout_manager._center_window()
        
        # Now show the window normally
        self.setVisible(True)
        super().show()
        logger.debug("Main window shown with all invisible attributes removed")