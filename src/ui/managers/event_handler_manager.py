"""
Event Handler Manager for the main window.

This module handles window events, signals, and user interactions
for the main window interface.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QCloseEvent

logger = logging.getLogger(__name__)


class EventHandlerManager:
    """
    Manages window events, signals, and user interactions.
    
    Handles close events, refresh operations, external link opening,
    and coordination between different UI components.
    """
    
    def __init__(self, main_window):
        """
        Initialize the event handler manager.
        
        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        self.ui_layout_manager = None  # Will be set by main window
        self.widget_lifecycle_manager = None  # Will be set by main window
        
        # Timer for periodic refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._on_refresh_timer)
        
        logger.debug("EventHandlerManager initialized")
    
    def set_managers(self, ui_layout_manager, widget_lifecycle_manager) -> None:
        """Set references to other managers."""
        self.ui_layout_manager = ui_layout_manager
        self.widget_lifecycle_manager = widget_lifecycle_manager
    
    def setup_refresh_timer(self) -> None:
        """Setup automatic refresh timer based on configuration."""
        config = getattr(self.main_window, 'config', None)
        if not config or not hasattr(config, 'refresh_interval_minutes'):
            return
            
        if config.refresh_interval_minutes > 0:
            interval_ms = config.refresh_interval_minutes * 60 * 1000
            self.refresh_timer.start(interval_ms)
            logger.info(f"Refresh timer started with {config.refresh_interval_minutes} minute interval")
        else:
            self.refresh_timer.stop()
            logger.info("Refresh timer disabled")
    
    def _on_refresh_timer(self) -> None:
        """Handle automatic refresh timer timeout."""
        logger.debug("Automatic refresh triggered by timer")
        self.refresh_all_data()
    
    def refresh_all_data(self) -> None:
        """Refresh all data sources (trains, weather, astronomy)."""
        try:
            # Refresh train data
            train_manager = getattr(self.main_window, 'train_manager', None)
            if train_manager:
                train_manager.refresh_trains()
                logger.debug("Train data refresh requested")
            
            # Refresh weather data
            self.refresh_weather()
            
            # Refresh astronomy data
            self.refresh_astronomy()
            
        except Exception as e:
            logger.error(f"Error during automatic refresh: {e}")
    
    def refresh_weather(self) -> None:
        """Refresh weather data."""
        try:
            weather_manager = getattr(self.main_window, 'weather_manager', None)
            if weather_manager:
                weather_manager.fetch_weather()
                logger.debug("Weather refresh requested")
        except Exception as e:
            logger.error(f"Error refreshing weather: {e}")
    
    def refresh_astronomy(self) -> None:
        """Refresh astronomy data."""
        try:
            astronomy_manager = getattr(self.main_window, 'astronomy_manager', None)
            if astronomy_manager:
                astronomy_manager.fetch_astronomy_data()
                logger.debug("Astronomy refresh requested")
        except Exception as e:
            logger.error(f"Error refreshing astronomy: {e}")
    
    def handle_close_event(self, event: QCloseEvent) -> None:
        """
        Handle window close event.
        
        Args:
            event: The close event
        """
        try:
            # Save UI state before closing
            if self.widget_lifecycle_manager:
                self.widget_lifecycle_manager.save_ui_state()
            
            # Stop refresh timer
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()
            
            # Clean up managers
            self._cleanup_managers()
            
            # Accept the close event
            event.accept()
            logger.info("Application closing - cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during close event handling: {e}")
            event.accept()  # Still close even if cleanup fails
    
    def _cleanup_managers(self) -> None:
        """Clean up all managers before closing."""
        try:
            # Clean up weather manager
            weather_manager = getattr(self.main_window, 'weather_manager', None)
            if weather_manager and hasattr(weather_manager, 'cleanup'):
                weather_manager.cleanup()
            
            # Clean up astronomy manager
            astronomy_manager = getattr(self.main_window, 'astronomy_manager', None)
            if astronomy_manager and hasattr(astronomy_manager, 'cleanup'):
                astronomy_manager.cleanup()
            
            # Clean up train manager
            train_manager = getattr(self.main_window, 'train_manager', None)
            if train_manager and hasattr(train_manager, 'cleanup'):
                train_manager.cleanup()
                
        except Exception as e:
            logger.error(f"Error during manager cleanup: {e}")
    
    def on_weather_updated(self, weather_data) -> None:
        """
        Handle weather data update.
        
        Args:
            weather_data: Updated weather information
        """
        try:
            logger.debug("Weather data updated")
            # Weather widget will handle the update directly through its connection
            
        except Exception as e:
            logger.error(f"Error handling weather update: {e}")
    
    def on_weather_error(self, error_message: str) -> None:
        """
        Handle weather data error.
        
        Args:
            error_message: Error message from weather service
        """
        logger.warning(f"Weather error: {error_message}")
        # Weather widget will handle the error display directly
    
    def on_weather_loading_changed(self, is_loading: bool) -> None:
        """
        Handle weather loading state change.
        
        Args:
            is_loading: Whether weather is currently loading
        """
        logger.debug(f"Weather loading state: {is_loading}")
        # Weather widget will handle the loading state directly
    
    def on_astronomy_updated(self, astronomy_data) -> None:
        """
        Handle astronomy data update.
        
        Args:
            astronomy_data: Updated astronomy information
        """
        try:
            logger.debug("Astronomy data updated")
            
            # Ensure astronomy widget is in layout when data is ready
            if self.widget_lifecycle_manager and not getattr(self, '_astronomy_data_fetched', False):
                self.widget_lifecycle_manager.ensure_astronomy_widget_in_layout()
                self._astronomy_data_fetched = True
            
        except Exception as e:
            logger.error(f"Error handling astronomy update: {e}")
    
    def on_astronomy_error(self, error_message: str) -> None:
        """
        Handle astronomy data error.
        
        Args:
            error_message: Error message from astronomy service
        """
        logger.warning(f"Astronomy error: {error_message}")
        # Astronomy widget will handle the error display directly
    
    def on_astronomy_loading_changed(self, is_loading: bool) -> None:
        """
        Handle astronomy loading state change.
        
        Args:
            is_loading: Whether astronomy is currently loading
        """
        logger.debug(f"Astronomy loading state: {is_loading}")
        # Astronomy widget will handle the loading state directly
    
    def on_astronomy_link_clicked(self, url: str) -> None:
        """
        Handle astronomy link click from astronomy widget.
        
        Args:
            url: URL to open
        """
        try:
            if url:
                QDesktopServices.openUrl(QUrl(url))
                logger.info(f"Opened astronomy link: {url}")
        except Exception as e:
            logger.error(f"Error opening astronomy link: {e}")
    
    def on_train_data_updated(self, train_data) -> None:
        """
        Handle train data update.
        
        Args:
            train_data: Updated train information
        """
        try:
            logger.debug("Train data updated")
            # Train widgets will handle the update through their connections
            
        except Exception as e:
            logger.error(f"Error handling train data update: {e}")
    
    def on_train_error(self, error_message: str) -> None:
        """
        Handle train data error.
        
        Args:
            error_message: Error message from train service
        """
        logger.warning(f"Train error: {error_message}")
        # Train widgets will handle the error display directly
    
    def show_route_details(self, route_data) -> None:
        """
        Show route details dialog.
        
        Args:
            route_data: Route information to display
        """
        try:
            if self.ui_layout_manager:
                widgets = self.ui_layout_manager.get_widgets()
                train_list_widget = widgets.get('train_list_widget')
                
                if train_list_widget and hasattr(train_list_widget, 'show_route_details'):
                    train_list_widget.show_route_details(route_data)
                    logger.debug("Route details dialog shown")
                    
        except Exception as e:
            logger.error(f"Error showing route details: {e}")
    
    def handle_keyboard_shortcuts(self, event) -> bool:
        """
        Handle keyboard shortcuts.
        
        Args:
            event: Key event
            
        Returns:
            bool: True if event was handled
        """
        try:
            # Handle common shortcuts
            if event.key() == 16777266:  # F5 key
                self.refresh_all_data()
                return True
            elif event.modifiers() & 0x04000000 and event.key() == 82:  # Ctrl+R
                self.refresh_all_data()
                return True
            elif event.modifiers() & 0x04000000 and event.key() == 81:  # Ctrl+Q
                QApplication.quit()
                return True
                
        except Exception as e:
            logger.error(f"Error handling keyboard shortcut: {e}")
        
        return False
    
    def handle_window_state_change(self, old_state, new_state) -> None:
        """
        Handle window state changes (minimize, maximize, etc.).
        
        Args:
            old_state: Previous window state
            new_state: New window state
        """
        try:
            logger.debug(f"Window state changed from {old_state} to {new_state}")
            
            # Pause refresh timer when minimized to save resources
            if new_state & 0x00000001:  # Minimized
                if self.refresh_timer.isActive():
                    self.refresh_timer.stop()
                    logger.debug("Refresh timer paused (window minimized)")
            else:
                # Resume refresh timer when restored
                self.setup_refresh_timer()
                
        except Exception as e:
            logger.error(f"Error handling window state change: {e}")