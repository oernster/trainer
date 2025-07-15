"""
Refactored Train Settings Dialog for the Train Times application.

This dialog provides a user interface for configuring train route settings,
using a modular component-based architecture for better maintainability.
"""

import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

# Import components
from .components.station_selection_widget import StationSelectionWidget
from .components.route_action_buttons import RouteActionButtons
from .components.route_details_widget import RouteDetailsWidget
from .components.preferences_widget import PreferencesWidget

# Import handlers
from .handlers.settings_handler import SettingsHandler
from .handlers.route_calculation_handler import RouteCalculationHandler

# Import state management
from .state.dialog_state import DialogState

# Import core services
from src.core.services.service_factory import ServiceFactory

logger = logging.getLogger(__name__)


class StationsSettingsDialog(QDialog):
    """
    Refactored Train Settings Dialog.
    
    This dialog provides a user interface for configuring train route settings
    using a modular component-based architecture.
    """
    
    # Signals - keep both for compatibility
    settings_saved = Signal()  # Original signal expected by main window
    settings_changed = Signal()
    route_updated = Signal(dict)
    
    def __init__(self, parent=None, station_database=None, config_manager=None, theme_manager=None):
        """
        Initialize the train settings dialog.
        
        Args:
            parent: Parent widget
            station_database: Station database manager (legacy)
            config_manager: Configuration manager
            theme_manager: Theme manager
        """
        super().__init__(parent)
        
        # Store references
        self.parent_window = parent
        self.station_database = station_database  # Keep for backward compatibility
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        
        # Initialize core services
        self.station_service = None
        self.route_service = None
        self._initialize_core_services()
        
        # Initialize state management
        self.dialog_state = DialogState(self)
        
        # Initialize handlers
        self.settings_handler = SettingsHandler(
            self, config_manager, self.station_service, self.route_service
        )
        self.route_calculation_handler = RouteCalculationHandler(
            self, self.station_service, self.route_service
        )
        
        # UI components
        self.tab_widget = None
        self.station_selection_widget = None
        self.route_action_buttons = None
        self.route_details_widget = None
        self.preferences_widget = None
        self.status_label = None
        self.save_button = None
        self.cancel_button = None
        
        # Initialize the dialog
        self._setup_dialog()
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        self._apply_theme()
        
        logger.info("StationsSettingsDialog (refactored) initialized successfully")
    
    def _initialize_core_services(self):
        """Initialize core services for real route calculations."""
        try:
            service_factory = ServiceFactory()
            self.station_service = service_factory.get_station_service()
            self.route_service = service_factory.get_route_service()
            logger.info("Core services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize core services: {e}")
            self.station_service = None
            self.route_service = None
    
    def _setup_dialog(self):
        """Set up basic dialog properties."""
        self.setWindowTitle("Train Settings")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        # Set window icon if available
        if hasattr(self.parent_window, 'windowIcon') and self.parent_window:
            try:
                self.setWindowIcon(self.parent_window.windowIcon())
            except:
                pass
    
    def _setup_ui(self):
        """Set up the complete user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create tab widget for different sections
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_route_tab()
        self._create_preferences_tab()
        
        # Create status bar
        self._create_status_bar()
        main_layout.addWidget(self.status_label)
        
        # Create button bar
        button_layout = self._create_button_bar()
        main_layout.addLayout(button_layout)
        
        # Set initial tab
        self.tab_widget.setCurrentIndex(0)
    
    def _create_route_tab(self):
        """Create the main route planning tab."""
        route_tab = QWidget()
        self.tab_widget.addTab(route_tab, "Route Planning")
        
        layout = QVBoxLayout(route_tab)
        layout.setSpacing(15)
        
        # Station selection section
        station_group = QGroupBox("Station Selection")
        station_layout = QVBoxLayout(station_group)
        
        self.station_selection_widget = StationSelectionWidget(self, self.theme_manager)
        station_layout.addWidget(self.station_selection_widget)
        layout.addWidget(station_group)
        
        # Route action buttons
        self.route_action_buttons = RouteActionButtons(self, self.theme_manager)
        layout.addWidget(self.route_action_buttons)
        
        # Route details section
        details_group = QGroupBox("Route Details")
        details_layout = QVBoxLayout(details_group)
        
        self.route_details_widget = RouteDetailsWidget(self, self.theme_manager)
        details_layout.addWidget(self.route_details_widget)
        layout.addWidget(details_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def _create_preferences_tab(self):
        """Create the preferences tab."""
        preferences_tab = QWidget()
        self.tab_widget.addTab(preferences_tab, "Preferences")
        
        layout = QVBoxLayout(preferences_tab)
        layout.setSpacing(15)
        
        # Preferences widget
        self.preferences_widget = PreferencesWidget(self, self.theme_manager)
        layout.addWidget(self.preferences_widget)
        
        # Add stretch
        layout.addStretch()
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.status_label = QLabel("Ready")
        # Remove hardcoded styles - let theme manager handle it
        self.status_label.setObjectName("statusLabel")
    
    def _create_button_bar(self):
        """Create the dialog button bar."""
        layout = QHBoxLayout()
        
        # Add stretch to push buttons to the right
        layout.addStretch()
        
        # Cancel button (now first/left)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        layout.addWidget(self.cancel_button)
        
        # Save button (now second/right)
        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        self.save_button.setObjectName("saveButton")
        layout.addWidget(self.save_button)
        
        return layout
    
    def _connect_signals(self):
        """Connect all signals and slots."""
        # Station selection signals
        if self.station_selection_widget:
            self.station_selection_widget.from_station_changed.connect(self._on_station_changed)
            self.station_selection_widget.to_station_changed.connect(self._on_station_changed)
        
        # Route action button signals
        if self.route_action_buttons:
            self.route_action_buttons.find_route_clicked.connect(self._find_route)
            self.route_action_buttons.clear_route_clicked.connect(self._clear_route)
        
        # Route details signals
        if self.route_details_widget:
            self.route_details_widget.departure_time_changed.connect(self.dialog_state.set_departure_time)
        
        # Preferences signals
        if self.preferences_widget:
            self.preferences_widget.preferences_changed.connect(self.dialog_state.set_preferences)
        
        # Route calculation handler signals
        self.route_calculation_handler.route_calculated.connect(self._on_route_calculated)
        self.route_calculation_handler.route_calculation_failed.connect(self._on_route_calculation_failed)
        self.route_calculation_handler.calculation_started.connect(self._on_calculation_started)
        self.route_calculation_handler.calculation_finished.connect(self._on_calculation_finished)
        
        # Dialog state signals
        self.dialog_state.route_data_changed.connect(self._on_route_data_changed)
        
        # Button signals
        if self.save_button:
            self.save_button.clicked.connect(self._save_settings)
        if self.cancel_button:
            self.cancel_button.clicked.connect(self.reject)
    
    def _load_settings(self):
        """Load settings from configuration."""
        try:
            settings = self.settings_handler.load_settings()
            
            # Populate station lists
            self._populate_station_combos()
            
            # Apply loaded settings
            if settings:
                if self.station_selection_widget:
                    self.station_selection_widget.set_from_station(settings.get('from_station', ''))
                    self.station_selection_widget.set_to_station(settings.get('to_station', ''))
                
                if self.route_details_widget:
                    self.route_details_widget.set_departure_time(settings.get('departure_time', '08:00'))
                
                if self.preferences_widget and 'preferences' in settings:
                    self.preferences_widget.set_preferences(settings['preferences'])
            
            self._update_status("Settings loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._update_status(f"Error loading settings: {e}")
    
    def _populate_station_combos(self):
        """Populate the station combo boxes using real station service."""
        try:
            stations = []
            
            # Try to use the core station service first
            if self.station_service:
                try:
                    all_stations = self.station_service.get_all_stations()
                    stations = [station.name for station in all_stations]
                    logger.info(f"Loaded {len(stations)} stations from core service")
                except Exception as e:
                    logger.warning(f"Failed to load from core service: {e}")
            
            # Fallback to station database if core service fails
            if not stations and self.station_database:
                try:
                    stations = self.station_database.get_all_station_names()
                    logger.info(f"Loaded {len(stations)} stations from database fallback")
                except Exception as e:
                    logger.warning(f"Failed to load from database: {e}")
            
            # If we still have no stations, provide some defaults
            if not stations:
                stations = [
                    "London Waterloo", "London Victoria", "London Bridge", "London King's Cross",
                    "London Paddington", "Clapham Junction", "Woking", "Guildford",
                    "Portsmouth Harbour", "Southampton Central", "Brighton", "Reading",
                    "Cambridge", "Fleet", "Farnborough", "Basingstoke"
                ]
                logger.warning("Using default station list")
            
            # Populate station selection widget
            if self.station_selection_widget:
                self.station_selection_widget.populate_stations(stations)
            
            logger.debug(f"Populated station combos with {len(stations)} stations")
            
        except Exception as e:
            logger.error(f"Error populating station combos: {e}")
    
    def _apply_theme(self):
        """Apply the current theme to the dialog."""
        try:
            if not self.theme_manager:
                return
            
            # Apply theme to main dialog
            self.theme_manager.apply_theme_to_widget(self)
            
            # Apply theme to components
            if self.station_selection_widget:
                self.station_selection_widget.apply_theme(self.theme_manager)
            if self.route_action_buttons:
                self.route_action_buttons.apply_theme(self.theme_manager)
            if self.route_details_widget:
                self.route_details_widget.apply_theme(self.theme_manager)
            if self.preferences_widget:
                self.preferences_widget.apply_theme(self.theme_manager)
            
        except Exception as e:
            logger.error(f"Error applying theme: {e}")
    
    # Event handlers
    def _on_station_changed(self):
        """Handle station selection change."""
        # Clear route data when stations change
        self.dialog_state.clear_route_data()
        if self.route_details_widget:
            self.route_details_widget.clear_route_data()
    
    def _find_route(self):
        """Find route between selected stations."""
        if not self.station_selection_widget:
            return
        
        from_station = self.station_selection_widget.get_from_station()
        to_station = self.station_selection_widget.get_to_station()
        self.route_calculation_handler.calculate_route(from_station, to_station, [])
    
    
    def _clear_route(self):
        """Clear the current route."""
        self.dialog_state.clear_route_data()
        if self.route_details_widget:
            self.route_details_widget.clear_route_data()
        self._update_status("Route cleared")
    
    def _on_route_calculated(self, route_data: Dict[str, Any]):
        """Handle successful route calculation."""
        self.dialog_state.set_route_data(route_data)
        if self.route_details_widget:
            self.route_details_widget.update_route_data(route_data)
        self._update_status("Route found successfully")
    
    def _on_route_calculation_failed(self, error_message: str):
        """Handle failed route calculation."""
        QMessageBox.warning(self, "Route Calculation Failed", error_message)
        self._update_status(f"Route calculation failed: {error_message}")
    
    def _on_calculation_started(self):
        """Handle calculation start."""
        if self.route_action_buttons:
            self.route_action_buttons.show_progress('find', 'Finding...')
        self._update_status("Calculating route...")
    
    def _on_calculation_finished(self):
        """Handle calculation finish."""
        if self.route_action_buttons:
            self.route_action_buttons.hide_progress('find')
    
    def _on_route_data_changed(self, route_data: Dict[str, Any]):
        """Handle route data change."""
        if self.route_details_widget:
            self.route_details_widget.update_route_data(route_data)
    
    def _save_settings(self):
        """Save settings and close dialog."""
        try:
            if not self.station_selection_widget:
                return
            
            from_station = self.station_selection_widget.get_from_station()
            to_station = self.station_selection_widget.get_to_station()
            preferences = self.preferences_widget.get_preferences() if self.preferences_widget else {}
            departure_time = self.route_details_widget.get_departure_time() if self.route_details_widget else "08:00"
            route_data = self.dialog_state.get_route_data()
            
            success = self.settings_handler.save_settings(
                from_station, to_station, preferences, departure_time, route_data
            )
            
            if success:
                # Emit both signals for compatibility
                self.settings_changed.emit()
                self.settings_saved.emit()
                
                # Signal the main window to refresh trains with the new route
                if hasattr(self.parent_window, 'route_changed'):
                    self.parent_window.route_changed.emit(from_station, to_station)
                
                # Also emit refresh signal if available
                if hasattr(self.parent_window, 'refresh_requested'):
                    self.parent_window.refresh_requested.emit()
                
                # Direct call to train manager if available
                if hasattr(self.parent_window, 'train_manager') and self.parent_window.train_manager:
                    if from_station and to_station:
                        self.parent_window.train_manager.set_route(from_station, to_station)
                
                self._update_status("Settings saved successfully")
                self.accept()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            self._update_status(f"Error saving settings: {e}")
    
    def _update_status(self, message: str):
        """Update the status bar message."""
        if self.status_label:
            self.status_label.setText(message)
        logger.debug(f"Status: {message}")
    
    # Public interface methods for compatibility
    def get_current_route(self) -> dict:
        """Get the current route configuration."""
        if not self.station_selection_widget:
            return {}
        
        return {
            'from_station': self.station_selection_widget.get_from_station(),
            'to_station': self.station_selection_widget.get_to_station(),
            'via_stations': [],
            'departure_time': self.dialog_state.get_departure_time(),
            'route_data': self.dialog_state.get_route_data()
        }
    
    def set_route(self, route_config: dict):
        """Set the route configuration."""
        try:
            if 'from_station' in route_config and self.station_selection_widget:
                self.station_selection_widget.set_from_station(route_config['from_station'])
            
            if 'to_station' in route_config and self.station_selection_widget:
                self.station_selection_widget.set_to_station(route_config['to_station'])
            
            if 'departure_time' in route_config and self.route_details_widget:
                self.route_details_widget.set_departure_time(route_config['departure_time'])
            
            if 'route_data' in route_config:
                self.dialog_state.set_route_data(route_config['route_data'])
            
        except Exception as e:
            logger.error(f"Error setting route: {e}")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        try:
            # Accept the close event
            event.accept()
            
        except Exception as e:
            logger.error(f"Error during dialog close: {e}")
            event.accept()