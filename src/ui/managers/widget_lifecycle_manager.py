"""
Widget Lifecycle Manager for the main window.

This module handles widget visibility, lifecycle management, and dynamic
widget addition/removal from the layout.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import QTimer

logger = logging.getLogger(__name__)


class WidgetLifecycleManager:
    """
    Manages widget lifecycle, visibility, and dynamic layout changes.
    
    Handles adding/removing widgets from layout, managing visibility states,
    and coordinating widget lifecycle events.
    """
    
    def __init__(self, main_window):
        """
        Initialize the widget lifecycle manager.
        
        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        self.ui_layout_manager = None  # Will be set by main window
        
        # Track initialization state
        self._weather_system_initialized = False
        self._astronomy_data_fetched = False
        
        logger.debug("WidgetLifecycleManager initialized")
    
    def set_ui_layout_manager(self, ui_layout_manager) -> None:
        """Set reference to UI layout manager."""
        self.ui_layout_manager = ui_layout_manager
    
    def setup_weather_system(self) -> None:
        """Setup weather integration system."""
        config = getattr(self.main_window, 'config', None)
        
        if not config or not hasattr(config, "weather") or not config.weather:
            logger.warning("Weather configuration not available")
            self.update_weather_status(False)
            return

        try:
            # Initialize weather manager
            weather_manager = getattr(self.main_window, 'weather_manager', None)
            weather_widget = self.ui_layout_manager.weather_widget if self.ui_layout_manager else None
            
            if weather_manager and weather_widget:
                # Connect weather widget signals
                weather_widget.weather_refresh_requested.connect(self.main_window.refresh_weather)
                weather_widget.weather_settings_requested.connect(self.main_window.show_stations_settings_dialog)
                
                # Update weather widget config
                weather_widget.update_config(config.weather)
                
                # Connect weather manager signals
                weather_manager.weather_updated.connect(self.main_window.on_weather_updated)
                weather_manager.weather_error.connect(self.main_window.on_weather_error)
                weather_manager.loading_state_changed.connect(self.main_window.on_weather_loading_changed)
                
                # Connect to weather widget
                weather_manager.weather_updated.connect(weather_widget.on_weather_updated)
                weather_manager.weather_error.connect(weather_widget.on_weather_error)
                weather_manager.loading_state_changed.connect(weather_widget.on_weather_loading)

            # Update weather status and visibility
            enabled = config.weather.enabled
            self.update_weather_status(enabled)

            # Set visibility if this is first initialization
            if weather_widget and not self._weather_system_initialized:
                if not hasattr(config, 'ui') or not config.ui:
                    weather_widget.setVisible(enabled)
                    logger.debug(f"Weather widget visibility set to {enabled} (first setup, no UI config)")
                self._weather_system_initialized = True

            if enabled and weather_manager:
                logger.debug("Weather system initialized and enabled")
                self.main_window.refresh_weather()
            else:
                logger.info("Weather system initialized but disabled")

        except Exception as e:
            logger.error(f"Failed to initialize weather system: {e}")
            self.update_weather_status(False)
            if self.ui_layout_manager and self.ui_layout_manager.weather_widget:
                self.ui_layout_manager.weather_widget.hide()
    
    def setup_astronomy_system(self) -> None:
        """Setup astronomy integration system."""
        config = getattr(self.main_window, 'config', None)
        
        if not config or not hasattr(config, "astronomy") or not config.astronomy:
            logger.info("Astronomy configuration not available - widget will show placeholder")
            self._connect_astronomy_widget_signals()
            self.update_astronomy_status(False)
            return

        try:
            # Always connect astronomy widget signals
            self._connect_astronomy_widget_signals()
            
            astronomy_widget = self.ui_layout_manager.astronomy_widget if self.ui_layout_manager else None
            if astronomy_widget:
                astronomy_widget.update_config(config.astronomy)

            # Initialize astronomy manager if enabled
            if config.astronomy.enabled:
                astronomy_manager = getattr(self.main_window, 'astronomy_manager', None)
                if astronomy_manager and astronomy_widget:
                    # Connect astronomy manager signals
                    astronomy_manager.astronomy_updated.connect(self.main_window.on_astronomy_updated)
                    astronomy_manager.astronomy_error.connect(self.main_window.on_astronomy_error)
                    astronomy_manager.loading_state_changed.connect(self.main_window.on_astronomy_loading_changed)
                    
                    # Connect to astronomy widget
                    astronomy_manager.astronomy_updated.connect(astronomy_widget.on_astronomy_updated)
                    astronomy_manager.astronomy_error.connect(astronomy_widget.on_astronomy_error)
                    astronomy_manager.loading_state_changed.connect(astronomy_widget.on_astronomy_loading)

                logger.debug("Astronomy system initialized with API key")
                # Emit signal to indicate astronomy manager is ready
                if hasattr(self.main_window, 'astronomy_manager_ready'):
                    self.main_window.astronomy_manager_ready.emit()
            else:
                logger.info("Astronomy system initialized without API key - widget will show placeholder")

            # Update astronomy status and visibility
            enabled = config.astronomy.enabled
            self.update_astronomy_status(enabled)

            # Set widget visibility
            if astronomy_widget:
                astronomy_widget.setVisible(enabled)

        except Exception as e:
            logger.error(f"Failed to initialize astronomy system: {e}")
            self.update_astronomy_status(False)
    
    def _connect_astronomy_widget_signals(self) -> None:
        """Connect astronomy widget signals."""
        astronomy_widget = self.ui_layout_manager.astronomy_widget if self.ui_layout_manager else None
        if astronomy_widget:
            astronomy_widget.astronomy_refresh_requested.connect(self.main_window.refresh_astronomy)
            astronomy_widget.nasa_link_clicked.connect(self.main_window.on_nasa_link_clicked)
            logger.info("Astronomy widget signals connected")
    
    def update_weather_status(self, enabled: bool) -> None:
        """Update weather status display."""
        # This method is kept for compatibility but does nothing
        # Status bar was removed from the main window
        pass
    
    def update_astronomy_status(self, enabled: bool) -> None:
        """Update astronomy status display."""
        # This method is kept for compatibility but does nothing
        # Status bar was removed from the main window
        pass
    
    def ensure_astronomy_widget_in_layout(self) -> None:
        """Ensure astronomy widget is added to layout when data is ready."""
        astronomy_widget = self.ui_layout_manager.astronomy_widget if self.ui_layout_manager else None
        if not astronomy_widget:
            return
            
        central_widget = self.main_window.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            
            if isinstance(layout, QVBoxLayout):
                # Check if widget is already in the layout
                is_in_layout = False
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == astronomy_widget:
                        is_in_layout = True
                        break
                
                if not is_in_layout:
                    # Add to layout between weather and train widgets
                    weather_widget = self.ui_layout_manager.weather_widget if self.ui_layout_manager else None
                    train_list_widget = self.ui_layout_manager.train_list_widget if self.ui_layout_manager else None
                    
                    weather_index = -1
                    train_index = -1
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget():
                            if item.widget() == weather_widget:
                                weather_index = i
                            elif item.widget() == train_list_widget:
                                train_index = i
                    
                    # Insert astronomy widget after weather widget
                    insert_index = weather_index + 1 if weather_index >= 0 else 0
                    if train_index >= 0 and insert_index > train_index:
                        insert_index = train_index
                    
                    layout.insertWidget(insert_index, astronomy_widget)
                    astronomy_widget.setVisible(True)
                    logger.info("Astronomy widget added to layout after data ready")
                    
                    # Update window size for astronomy
                    if self.ui_layout_manager:
                        self.ui_layout_manager.update_window_size_for_widgets()
    
    def remove_astronomy_widget_from_layout(self) -> None:
        """Remove astronomy widget from layout when disabled."""
        astronomy_widget = self.ui_layout_manager.astronomy_widget if self.ui_layout_manager else None
        if not astronomy_widget:
            return
            
        central_widget = self.main_window.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            
            if isinstance(layout, QVBoxLayout):
                # Check if widget is in the layout and remove it
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == astronomy_widget:
                        layout.removeWidget(astronomy_widget)
                        astronomy_widget.setVisible(False)
                        logger.info("Astronomy widget removed from layout")
                        break
    
    def ensure_weather_widget_in_layout(self) -> None:
        """Ensure weather widget is added to layout at the correct position."""
        weather_widget = self.ui_layout_manager.weather_widget if self.ui_layout_manager else None
        if not weather_widget:
            return
            
        central_widget = self.main_window.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            
            if isinstance(layout, QVBoxLayout):
                # Check if widget is already in the layout
                is_in_layout = False
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == weather_widget:
                        is_in_layout = True
                        break
                
                if not is_in_layout:
                    # Add weather widget at the beginning (index 0)
                    layout.insertWidget(0, weather_widget)
                    weather_widget.setVisible(True)
                    logger.info("Weather widget added to layout at position 0")
    
    def remove_weather_widget_from_layout(self) -> None:
        """Remove weather widget from layout when hidden."""
        weather_widget = self.ui_layout_manager.weather_widget if self.ui_layout_manager else None
        if not weather_widget:
            return
            
        central_widget = self.main_window.centralWidget()
        if central_widget:
            layout = central_widget.layout()
            
            if isinstance(layout, QVBoxLayout):
                # Check if widget is in the layout and remove it
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() == weather_widget:
                        layout.removeWidget(weather_widget)
                        weather_widget.setVisible(False)
                        logger.info("Weather widget removed from layout")
                        break
    
    def save_ui_state(self) -> None:
        """Save current UI widget visibility states and window size to configuration."""
        config = getattr(self.main_window, 'config', None)
        if not config or not hasattr(config, 'ui') or not config.ui:
            return
            
        widgets = self.ui_layout_manager.get_widgets() if self.ui_layout_manager else {}
        weather_widget = widgets.get('weather_widget')
        astronomy_widget = widgets.get('astronomy_widget')
        
        # Update UI state in config
        if weather_widget:
            config.ui.weather_widget_visible = weather_widget.isVisible()
        if astronomy_widget:
            config.ui.astronomy_widget_visible = astronomy_widget.isVisible()
        
        # Save current window size for the current widget state
        current_size = (self.main_window.width(), self.main_window.height())
        weather_visible = weather_widget.isVisible() if weather_widget else False
        astronomy_visible = astronomy_widget.isVisible() if astronomy_widget else False
        
        if weather_visible and astronomy_visible:
            config.ui.window_size_both_visible = current_size
        elif weather_visible:
            config.ui.window_size_weather_only = current_size
        elif astronomy_visible:
            config.ui.window_size_astronomy_only = current_size
        else:
            config.ui.window_size_trains_only = current_size
        
        # Save to file
        try:
            config_manager = getattr(self.main_window, 'config_manager', None)
            if config_manager:
                config_manager.save_config(config)
                logger.debug(f"UI state saved: weather={config.ui.weather_widget_visible}, astronomy={config.ui.astronomy_widget_visible}, size={current_size}")
        except Exception as e:
            logger.error(f"Failed to save UI state: {e}")