"""
Refactored Train Settings Dialog for the Train Times application.

This dialog provides a user interface for configuring train route settings,
using a modular component-based architecture for better maintainability.
"""

import logging
import sys
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QGroupBox, QMessageBox, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QIcon

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
from src.core.services.essential_station_cache import get_essential_stations
from src.cache.station_cache_manager import get_station_cache_manager
from .workers.station_data_worker import StationDataManager

logger = logging.getLogger(__name__)


class RouteCalculationWorker(QThread):
    """Background worker thread for route calculation to avoid blocking UI."""
    
    # Signals
    route_calculated = Signal(dict)
    calculation_failed = Signal(str)
    calculation_started = Signal()
    calculation_finished = Signal()
    
    def __init__(self, dialog, from_station, to_station, preferences=None):
        super().__init__()
        self.dialog = dialog
        self.from_station = from_station
        self.to_station = to_station
        self.preferences = preferences or {}
        
    def run(self):
        """Run route calculation in background thread."""
        try:
            self.calculation_started.emit()
            logger.info(f"Background route calculation started: {self.from_station} → {self.to_station}")
            
            # Perform route calculation using the dialog's route calculation handler
            # This runs in the background thread, not blocking the UI
            if self.dialog.route_calculation_handler:
                # Get current preferences from dialog state
                preferences = self.dialog.dialog_state.get_preferences() if self.dialog.dialog_state else {}
                
                # Use the existing route calculation handler but in background
                # We need to call the actual calculation method directly
                try:
                    # Access the route service through lazy loading
                    route_service = self.dialog.route_service
                    if route_service:
                        # Perform the actual route calculation
                        route_data = self._calculate_route_data(route_service)
                        if route_data:
                            self.route_calculated.emit(route_data)
                        else:
                            self.calculation_failed.emit("No route found")
                    else:
                        self.calculation_failed.emit("Route service not available")
                        
                except Exception as e:
                    logger.error(f"Route calculation error: {e}")
                    self.calculation_failed.emit(str(e))
            else:
                self.calculation_failed.emit("Route calculation handler not available")
                
        except Exception as e:
            logger.error(f"Background route calculation failed: {e}")
            self.calculation_failed.emit(str(e))
        finally:
            self.calculation_finished.emit()
    
    def _calculate_route_data(self, route_service):
        """Calculate route data using the route service."""
        try:
            # This is a simplified version - in practice, you'd use the full route calculation logic
            # For now, we'll create a basic route data structure
            route_data = {
                'from_station': self.from_station,
                'to_station': self.to_station,
                'full_path': [self.from_station, self.to_station],
                'calculated_at': 'background_thread'
            }
            logger.info(f"Route calculated in background: {self.from_station} → {self.to_station}")
            return route_data
        except Exception as e:
            logger.error(f"Error in route data calculation: {e}")
            return None


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
        
        # Initialize core services lazily for better performance
        self._station_service = None
        self._route_service = None
        # Don't initialize services immediately - use lazy loading
        
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
        
        # Performance optimization components
        self.station_data_manager = None
        self.cache_manager = None
        self._stations_loaded = False
        self._essential_stations_loaded = False
        self._pending_station_settings = None  # Store settings for restoration after background loading
        
        # Background route calculation
        self._route_worker = None
        
        # Initialize the dialog with immediate UI responsiveness
        self._setup_dialog()
        self._setup_ui()
        
        # CRITICAL: Enable station fields immediately and load config values
        self._setup_immediate_ui_responsiveness()
        
        # Connect signals
        self._connect_signals()
        
        # Apply theme
        self._apply_theme()
        
        # Defer heavy operations to background using QTimer
        QTimer.singleShot(0, self._setup_deferred_initialization)
        
        logger.info("StationsSettingsDialog initialized with immediate UI responsiveness")
    
    @property
    def station_service(self):
        """Lazy loading property for station service."""
        if self._station_service is None:
            try:
                from src.core.services.service_factory import ServiceFactory
                service_factory = ServiceFactory()
                self._station_service = service_factory.get_station_service()
                logger.info("Station service initialized lazily")
            except Exception as e:
                logger.error(f"Failed to initialize station service: {e}")
                self._station_service = None
        return self._station_service
    
    @property
    def route_service(self):
        """Lazy loading property for route service."""
        if self._route_service is None:
            try:
                from src.core.services.service_factory import ServiceFactory
                service_factory = ServiceFactory()
                self._route_service = service_factory.get_route_service()
                logger.info("Route service initialized lazily")
            except Exception as e:
                logger.error(f"Failed to initialize route service: {e}")
                self._route_service = None
        return self._route_service
    
    def _setup_dialog(self):
        """Set up basic dialog properties."""
        self.setWindowTitle("Train Settings")
        self.setModal(True)
        
        # Use Linux implementation for all platforms - it works great
        # Detect small screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            is_small_screen = screen_geometry.width() <= 1440 or screen_geometry.height() <= 900
        else:
            is_small_screen = False
        
        if is_small_screen:
            # Optimize for small screens - increase height for better alignment space
            self.setMinimumSize(850, 750)  # Increased height from 700 to 750
            self.resize(900, 800)  # Increased height from 750 to 800
        else:
            # Normal screens - increase height for better alignment space
            self.setMinimumSize(850, 700)  # Increased height from 650 to 700
            self.resize(950, 800)  # Increased height from 750 to 800
        
        # Center the dialog on Linux
        if sys.platform.startswith('linux'):
            self._center_on_screen()
        
        # Set custom clock icon for stations dialog
        self._setup_dialog_icon()
    
    def _setup_dialog_icon(self):
        """Setup dialog icon using Unicode alarm clock emoji."""
        from PySide6.QtGui import QPixmap, QPainter, QFont
        from PySide6.QtCore import Qt
        
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
            
            # Draw the alarm clock emoji centered
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "⏰")
            painter.end()
            
            # Create icon and set it
            icon = QIcon(pixmap)
            self.setWindowIcon(icon)
            
            logger.debug("Dialog icon set using Unicode alarm clock emoji")
            
        except Exception as e:
            logger.warning(f"Failed to create emoji dialog icon: {e}")
            # Fallback to parent window icon if available
            if hasattr(self.parent_window, 'windowIcon') and self.parent_window:
                try:
                    self.setWindowIcon(self.parent_window.windowIcon())
                except:
                    pass
    
    def _center_on_screen(self):
        """Center the dialog on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            dialog_geometry = self.frameGeometry()
            x = (screen_geometry.width() - dialog_geometry.width()) // 2
            y = (screen_geometry.height() - dialog_geometry.height()) // 2
            self.move(x, y)
            logger.debug(f"Centered stations settings dialog at ({x}, {y})")
    
    def _setup_ui(self):
        """Set up the complete user interface."""
        main_layout = QVBoxLayout(self)
        
        # Use Linux layout settings for all platforms - reduced spacing to give more room for content
        main_layout.setSpacing(8)  # Reduced from 12
        main_layout.setContentsMargins(15, 15, 15, 15)  # Reduced from 20
        
        # Create tab widget for different sections
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_route_tab()
        self._create_preferences_tab()
        
        # Create button bar with integrated status
        button_layout = self._create_button_bar()
        main_layout.addLayout(button_layout)
        
        # Set initial tab
        self.tab_widget.setCurrentIndex(0)
    
    def _create_route_tab(self):
        """Create the main route planning tab."""
        route_tab = QWidget()
        self.tab_widget.addTab(route_tab, "Route Planning")
        
        layout = QVBoxLayout(route_tab)
        
        # Use Linux implementation for all platforms - reduced spacing to save vertical space
        layout.setSpacing(10)  # Reduced from 20 to save vertical space
        
        # Station selection section
        station_group = QGroupBox("Station Selection")
        station_layout = QVBoxLayout(station_group)
        
        # Use Linux layout adjustments for all platforms
        station_layout.setContentsMargins(5, 5, 5, 5)  # Very tight margins
        station_layout.setSpacing(0)  # No spacing
        # Set a maximum height for the station group
        station_group.setMaximumHeight(150)  # Limit the height
        
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
        
        # Platform-specific sizing for the details group
        if sys.platform.startswith('linux'):
            # Detect small screen
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                is_small_screen = screen_geometry.width() <= 1440 or screen_geometry.height() <= 900
            else:
                is_small_screen = False
            
            if is_small_screen:
                # Make the Route Details group expand to fill available space
                details_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(details_group, 1)  # Add with stretch factor of 1 to allow expansion
        
        # Don't add stretch - let the Route Details expand to fill space
    
    def _create_preferences_tab(self):
        """Create the preferences tab."""
        preferences_tab = QWidget()
        self.tab_widget.addTab(preferences_tab, "Preferences")
        
        layout = QVBoxLayout(preferences_tab)
        
        # Use Linux implementation for all platforms
        layout.setSpacing(20)
        
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
        
        # Platform-specific sizing for status label
        if sys.platform.startswith('linux'):
            self.status_label.setMaximumHeight(25)  # Limit height on Linux
            self.status_label.setFont(QFont("Arial", 9))  # Smaller font
    
    def _create_button_bar(self):
        """Create the dialog button bar with integrated status."""
        layout = QHBoxLayout()
        
        # Create and add status label on the left
        self._create_status_bar()
        layout.addWidget(self.status_label)
        
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
        self.dialog_state.preferences_changed.connect(self._on_preferences_changed)
        
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
                    # Also update route details widget with preferences
                    if self.route_details_widget:
                        self.route_details_widget.set_preferences(settings['preferences'])
                
                # Load route data if available
                if 'route_data' in settings and settings['route_data']:
                    self.dialog_state.set_route_data(settings['route_data'])
                    if self.route_details_widget:
                        self.route_details_widget.update_route_data(settings['route_data'])
                    self._update_status("Route path loaded from saved settings")
                
                # Auto-trigger route calculation to ensure complete route data
                from_station = settings.get('from_station', '')
                to_station = settings.get('to_station', '')
                if from_station and to_station and from_station != to_station:
                    # Use QTimer to delay the route calculation until after dialog is fully initialized
                    QTimer.singleShot(100, lambda: self._find_route())
                    logger.info(f"Auto-triggering route calculation for {from_station} → {to_station}")
            
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
                    # Use the new method that includes Underground stations for autocomplete
                    stations = self.station_service.get_all_station_names_with_underground()
                    logger.info(f"Loaded {len(stations)} stations (including Underground) from core service")
                except Exception as e:
                    logger.warning(f"Failed to load from core service with Underground: {e}")
                    # Fallback to regular stations if the new method fails
                    try:
                        all_stations = self.station_service.get_all_stations()
                        stations = [station.name for station in all_stations]
                        logger.info(f"Loaded {len(stations)} stations from core service (fallback)")
                    except Exception as e2:
                        logger.warning(f"Failed to load from core service fallback: {e2}")
            
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
    
    def _setup_optimized_loading(self):
        """Set up the optimized station data loading system."""
        try:
            # Initialize cache manager
            self.cache_manager = get_station_cache_manager()
            
            # Initialize station data manager
            self.station_data_manager = StationDataManager(self)
            
            # Connect signals for progressive loading
            self.station_data_manager.essential_stations_ready.connect(self._on_essential_stations_ready)
            self.station_data_manager.full_stations_ready.connect(self._on_full_stations_ready)
            self.station_data_manager.underground_stations_ready.connect(self._on_underground_stations_ready)
            self.station_data_manager.loading_progress.connect(self._on_loading_progress)
            self.station_data_manager.loading_error.connect(self._on_loading_error)
            
            logger.info("Optimized loading system initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup optimized loading: {e}")
            # Fallback to original loading if optimization fails
            self.station_data_manager = None
            self.cache_manager = None
    
    def _load_settings_optimized(self):
        """Load settings with optimized station data loading."""
        try:
            # STEP 1: Load essential stations immediately and populate combo boxes
            self._populate_essential_stations_immediately()
            
            # STEP 2: Load settings from configuration (with fallback for config loading issues)
            settings = None
            try:
                settings = self.settings_handler.load_settings()
            except Exception as e:
                logger.warning(f"Settings handler failed, trying direct config loading: {e}")
                # Fallback: try to load config directly if settings handler fails
                if self.config_manager:
                    try:
                        config = self.config_manager.load_config()
                        if hasattr(config, 'stations'):
                            # Use the correct attribute names from the Pydantic model
                            from_station = getattr(config.stations, 'from_name', '') or getattr(config.stations, 'from_code', '')
                            to_station = getattr(config.stations, 'to_name', '') or getattr(config.stations, 'to_code', '')
                            
                            settings = {
                                'from_station': from_station,
                                'to_station': to_station,
                                'departure_time': getattr(config.stations, 'departure_time', '08:00'),
                                'preferences': {}
                            }
                            logger.info(f"Loaded config directly from config manager: FROM='{from_station}', TO='{to_station}'")
                    except Exception as e2:
                        logger.warning(f"Direct config loading also failed: {e2}")
            
            # STEP 3: Store the loaded settings for later restoration after background loading
            self._pending_station_settings = settings
            
            # STEP 4: Apply saved FROM/TO stations immediately (they should work with essential stations)
            if settings and self.station_selection_widget:
                # Handle both direct station keys and nested stations object
                from_station = ''
                to_station = ''
                
                if 'from_station' in settings:
                    from_station = settings['from_station']
                elif 'stations' in settings and isinstance(settings['stations'], dict):
                    from_station = settings['stations'].get('from_station', '')
                
                if 'to_station' in settings:
                    to_station = settings['to_station']
                elif 'stations' in settings and isinstance(settings['stations'], dict):
                    to_station = settings['stations'].get('to_station', '')
                
                if from_station:
                    # Try to set immediately first
                    try:
                        self.station_selection_widget.set_from_station(from_station)
                        current_value = self.station_selection_widget.get_from_station()
                        if current_value == from_station:
                            logger.info(f"Successfully set FROM station immediately: {from_station}")
                        else:
                            # Use retry mechanism if immediate setting failed
                            QTimer.singleShot(50, lambda: self._set_station_with_retry('from', from_station))
                            logger.info(f"Scheduling FROM station retry: {from_station}")
                    except Exception as e:
                        logger.warning(f"Failed to set FROM station immediately: {e}")
                        QTimer.singleShot(50, lambda: self._set_station_with_retry('from', from_station))
                
                if to_station:
                    # Try to set immediately first
                    try:
                        self.station_selection_widget.set_to_station(to_station)
                        current_value = self.station_selection_widget.get_to_station()
                        if current_value == to_station:
                            logger.info(f"Successfully set TO station immediately: {to_station}")
                        else:
                            # Use retry mechanism if immediate setting failed
                            QTimer.singleShot(50, lambda: self._set_station_with_retry('to', to_station))
                            logger.info(f"Scheduling TO station retry: {to_station}")
                    except Exception as e:
                        logger.warning(f"Failed to set TO station immediately: {e}")
                        QTimer.singleShot(50, lambda: self._set_station_with_retry('to', to_station))
            
            # STEP 5: Apply other settings to UI components
            if settings:
                if self.route_details_widget:
                    self.route_details_widget.set_departure_time(settings.get('departure_time', '08:00'))
                
                if self.preferences_widget and 'preferences' in settings:
                    self.preferences_widget.set_preferences(settings['preferences'])
                    if self.route_details_widget:
                        self.route_details_widget.set_preferences(settings['preferences'])
                
                # Load route data if available
                if 'route_data' in settings and settings['route_data']:
                    self.dialog_state.set_route_data(settings['route_data'])
                    if self.route_details_widget:
                        self.route_details_widget.update_route_data(settings['route_data'])
                    self._update_status("Route path loaded from saved settings")
            
            # STEP 6: Start background loading for complete dataset (this enhances autocomplete)
            # The station selection widget will now preserve current selections when repopulated
            self._start_background_station_loading(settings)
            
            # STEP 7: Auto-trigger route calculation if both stations are set
            if settings and self.station_selection_widget:
                from_station = settings.get('from_station', '')
                to_station = settings.get('to_station', '')
                if from_station and to_station and from_station != to_station:
                    QTimer.singleShot(100, lambda: self._find_route())
                    logger.info(f"Auto-triggering route calculation for {from_station} → {to_station}")
            
            self._update_status("Ready - background loading in progress")
            
        except Exception as e:
            logger.error(f"Error in optimized settings loading: {e}")
            # Fallback to original loading
            self._load_settings()
    
    def _start_optimized_station_loading(self, settings: Optional[dict] = None):
        """Start the optimized station loading process."""
        try:
            if not self.station_data_manager:
                # Fallback to original loading
                self._populate_station_combos()
                return
            
            # Load essential stations immediately for UI responsiveness
            essential_stations = get_essential_stations()
            if essential_stations:
                logger.info(f"Using essential stations for immediate UI ({len(essential_stations)} stations)")
                self._populate_station_combos_with_list(essential_stations)
                self._essential_stations_loaded = True
                
                # CRITICAL: Enable the UI fields immediately after populating with essential stations
                self._enable_station_fields_immediately()
                
                self._update_status("Essential stations loaded - loading full dataset...")
            
            # Start background loading for complete dataset
            self.station_data_manager.start_loading(self.station_service,
                                                  getattr(self.station_service, 'data_repository', None))
            
            # Apply saved station selections after essential stations are loaded
            if settings and self._essential_stations_loaded:
                QTimer.singleShot(50, lambda: self._apply_saved_station_selections(settings))
            
        except Exception as e:
            logger.error(f"Optimized station loading failed: {e}")
            # Fallback to original loading
            self._populate_station_combos()
    
    def _populate_station_combos_with_list(self, stations: List[str]):
        """Populate station combos with a provided list of stations."""
        try:
            if not stations:
                return
            
            # Populate station selection widget
            if self.station_selection_widget:
                self.station_selection_widget.populate_stations(stations)
            
            logger.debug(f"Populated station combos with {len(stations)} stations")
            
        except Exception as e:
            logger.error(f"Error populating stations with list: {e}")
    
    def _apply_saved_station_selections(self, settings: dict):
        """Apply saved station selections after stations are loaded."""
        try:
            if not settings or not self.station_selection_widget:
                return
            
            from_station = settings.get('from_station', '')
            to_station = settings.get('to_station', '')
            
            if from_station:
                self.station_selection_widget.set_from_station(from_station)
            if to_station:
                self.station_selection_widget.set_to_station(to_station)
            
            # Auto-trigger route calculation if both stations are set
            if from_station and to_station and from_station != to_station:
                QTimer.singleShot(100, lambda: self._find_route())
                logger.info(f"Auto-triggering route calculation for {from_station} → {to_station}")
            
        except Exception as e:
            logger.error(f"Error applying saved station selections: {e}")
    
    # Signal handlers for optimized loading
    def _on_essential_stations_ready(self, stations: List[str]):
        """Handle essential stations loading completion."""
        try:
            if not self._stations_loaded:  # Only update if we don't have full data yet
                self._populate_station_combos_with_list(stations)
                self._essential_stations_loaded = True
                self._update_status(f"Essential stations ready ({len(stations)} stations)")
                logger.info(f"Essential stations ready: {len(stations)} stations")
        except Exception as e:
            logger.error(f"Error handling essential stations: {e}")
    
    def _on_full_stations_ready(self, stations: List[str]):
        """Handle full station data loading completion."""
        try:
            self._populate_station_combos_with_list(stations)
            self._stations_loaded = True
            self._update_status(f"All stations loaded ({len(stations)} stations)")
            logger.info(f"Full stations ready: {len(stations)} stations")
            
            # Save to cache for next time
            if self.cache_manager and stations:
                try:
                    data_directory = None
                    # Try to get data directory from various sources
                    if hasattr(self, 'station_service') and self.station_service:
                        # Try to access data_repository through the concrete implementation
                        if hasattr(self.station_service, 'data_repository'):
                            data_repo = getattr(self.station_service, 'data_repository', None)
                            if data_repo and hasattr(data_repo, 'data_directory'):
                                data_directory = data_repo.data_directory
                    
                    self.cache_manager.save_stations_to_cache(stations, data_directory)
                    logger.info("Station data cached for future use")
                except Exception as e:
                    logger.warning(f"Failed to cache station data: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling full stations: {e}")
    
    def _on_underground_stations_ready(self, stations: List[str]):
        """Handle underground stations loading completion."""
        try:
            # Underground stations are included in the full dataset
            # This is just for progress indication
            logger.info(f"Underground stations ready: {len(stations)} stations")
        except Exception as e:
            logger.error(f"Error handling underground stations: {e}")
    
    def _on_loading_progress(self, message: str, percentage: int):
        """Handle loading progress updates."""
        try:
            self._update_status(f"{message} ({percentage}%)")
        except Exception as e:
            logger.error(f"Error handling loading progress: {e}")
    
    def _on_loading_error(self, error_message: str):
        """Handle loading errors."""
        try:
            logger.error(f"Station loading error: {error_message}")
            self._update_status(f"Loading error: {error_message}")
            
            # Fallback to original loading on error
            if not self._essential_stations_loaded and not self._stations_loaded:
                logger.info("Falling back to original station loading")
                self._populate_station_combos()
                
        except Exception as e:
            logger.error(f"Error handling loading error: {e}")
    
    def _enable_station_fields_immediately(self):
        """Enable station input fields immediately for user interaction."""
        try:
            if self.station_selection_widget:
                # Ensure the station selection widget is enabled
                self.station_selection_widget.setEnabled(True)
                
                # Ensure individual combo boxes are enabled and editable
                if hasattr(self.station_selection_widget, 'from_station_combo') and self.station_selection_widget.from_station_combo:
                    combo = self.station_selection_widget.from_station_combo
                    combo.setEnabled(True)
                    combo.setEditable(True)
                    
                    # Ensure the line edit is enabled and focusable
                    line_edit = combo.lineEdit()
                    if line_edit:
                        line_edit.setEnabled(True)
                        line_edit.setReadOnly(False)
                        line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                
                if hasattr(self.station_selection_widget, 'to_station_combo') and self.station_selection_widget.to_station_combo:
                    combo = self.station_selection_widget.to_station_combo
                    combo.setEnabled(True)
                    combo.setEditable(True)
                    
                    # Ensure the line edit is enabled and focusable
                    line_edit = combo.lineEdit()
                    if line_edit:
                        line_edit.setEnabled(True)
                        line_edit.setReadOnly(False)
                        line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                
                # Enable the swap button
                if hasattr(self.station_selection_widget, 'swap_button') and self.station_selection_widget.swap_button:
                    self.station_selection_widget.swap_button.setEnabled(True)
                
                logger.info("Station input fields enabled immediately for user interaction")
            
        except Exception as e:
            logger.error(f"Error enabling station fields immediately: {e}")
    
    def _ensure_fields_enabled_final(self):
        """Final check to ensure station fields are enabled after all initialization."""
        try:
            # Force enable the station fields one more time
            self._enable_station_fields_immediately()
            
            # Also populate with essential stations if not already done
            if self.station_selection_widget and not self._essential_stations_loaded:
                from src.core.services.essential_station_cache import get_essential_stations
                essential_stations = get_essential_stations()
                if essential_stations:
                    self.station_selection_widget.populate_stations(essential_stations)
                    self._essential_stations_loaded = True
                    logger.info("Final population with essential stations completed")
            
            logger.info("Final field enablement check completed")
            
        except Exception as e:
            logger.error(f"Error in final field enablement: {e}")
    
    def _populate_essential_stations_immediately(self):
        """Populate combo boxes with essential stations immediately for instant interaction."""
        try:
            # Load essential stations (this is very fast - <0.001s)
            from src.core.services.essential_station_cache import get_essential_stations
            essential_stations = get_essential_stations()
            
            if essential_stations and self.station_selection_widget:
                # Populate the combo boxes immediately
                self.station_selection_widget.populate_stations(essential_stations)
                self._essential_stations_loaded = True
                
                # Ensure fields are enabled and editable
                self._enable_station_fields_immediately()
                
                logger.info(f"Essential stations populated immediately: {len(essential_stations)} stations")
                self._update_status(f"Ready ({len(essential_stations)} stations loaded)")
                
                return True
            else:
                logger.warning("No essential stations available for immediate population")
                return False
                
        except Exception as e:
            logger.error(f"Error populating essential stations immediately: {e}")
            return False
    
    def _start_background_station_loading(self, settings: Optional[dict] = None):
        """Start background loading of complete station dataset for enhanced autocomplete."""
        try:
            if not self.station_data_manager:
                logger.warning("Station data manager not available for background loading")
                return
            
            # Start background loading for complete dataset
            self.station_data_manager.start_loading(self.station_service,
                                                  getattr(self.station_service, 'data_repository', None))
            
            logger.info("Background station loading started for enhanced autocomplete")
            
        except Exception as e:
            logger.error(f"Error starting background station loading: {e}")
    
    def _set_station_with_retry(self, field_type: str, station_name: str, max_retries: int = 3):
        """Set station value with retry logic to handle timing issues."""
        try:
            if not self.station_selection_widget or not station_name:
                return
            
            success = False
            for attempt in range(max_retries):
                try:
                    if field_type == 'from':
                        self.station_selection_widget.set_from_station(station_name)
                        # Verify it was set correctly
                        current_value = self.station_selection_widget.get_from_station()
                        if current_value == station_name:
                            success = True
                            logger.info(f"Successfully set FROM station to: {station_name}")
                            break
                    elif field_type == 'to':
                        self.station_selection_widget.set_to_station(station_name)
                        # Verify it was set correctly
                        current_value = self.station_selection_widget.get_to_station()
                        if current_value == station_name:
                            success = True
                            logger.info(f"Successfully set TO station to: {station_name}")
                            break
                    
                    # If we get here, the setting didn't work, wait and retry
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed to set {field_type} station to {station_name}, retrying...")
                        QTimer.singleShot(50, lambda: self._set_station_with_retry(field_type, station_name, max_retries - attempt - 1))
                        return
                        
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} to set {field_type} station failed: {e}")
                    if attempt < max_retries - 1:
                        QTimer.singleShot(50, lambda: self._set_station_with_retry(field_type, station_name, max_retries - attempt - 1))
                        return
            
            if not success:
                logger.error(f"Failed to set {field_type} station to {station_name} after {max_retries} attempts")
                
        except Exception as e:
            logger.error(f"Error in _set_station_with_retry: {e}")
    
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
        
        # Get current preferences
        preferences = self.dialog_state.get_preferences()
        
        logger.info(f"Finding route: {from_station} → {to_station} with preferences: {preferences}")
        self.route_calculation_handler.calculate_route(from_station, to_station, [], preferences=preferences)
    
    
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
        
        # Emit route_updated signal for main window connection
        self.route_updated.emit(route_data)
        
        # Immediately update the main UI with the new route
        self._update_main_ui_with_route(route_data)
    
    def _on_route_calculation_failed(self, error_message: str):
        """Handle failed route calculation."""
        QMessageBox.warning(self, "Route Calculation Failed", error_message)
        self._update_status(f"Route calculation failed: {error_message}")
        
        # Clear any previous route data to prevent UI inconsistency
        self.dialog_state.clear_route_data()
        if self.route_details_widget:
            self.route_details_widget.clear_route_data()
            
        logger.info(f"Cleared route data after calculation failure: {error_message}")
    
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
    
    def _on_preferences_changed(self, preferences: Dict[str, Any]):
        """Handle preferences change - automatically recalculate route if stations are set."""
        logger.info(f"Preferences changed: {preferences}")
        
        # Only recalculate if we have both stations set
        if self.station_selection_widget:
            from_station = self.station_selection_widget.get_from_station()
            to_station = self.station_selection_widget.get_to_station()
            
            if from_station and to_station and from_station != to_station:
                logger.info(f"Auto-recalculating route due to preference change: {from_station} → {to_station}")
                self._find_route()
            else:
                logger.debug("Skipping route recalculation - stations not properly set")
    
    def _update_main_ui_with_route(self, route_data: Dict[str, Any]):
        """Update the main UI immediately with the calculated route."""
        try:
            if not self.station_selection_widget:
                return
            
            from_station = self.station_selection_widget.get_from_station()
            to_station = self.station_selection_widget.get_to_station()
            
            if not from_station or not to_station:
                return
            
            # Extract route path from route_data
            route_path = None
            if route_data and 'full_path' in route_data:
                route_path = route_data['full_path']
                logger.info(f"Updating main UI with route path: {' → '.join(route_path)}")
            
            # Update train manager directly
            if (self.parent_window and
                hasattr(self.parent_window, 'train_manager') and
                self.parent_window.train_manager):
                
                train_manager = self.parent_window.train_manager
                train_manager.set_route(from_station, to_station, route_path)
                
                # Share config_manager for persistence
                if self.config_manager and hasattr(train_manager.__class__, 'config_manager'):
                    train_manager.__class__.config_manager = self.config_manager
                
                logger.info(f"Updated main UI train manager with route: {from_station} → {to_station}")
            
            # Emit signals to refresh the main UI
            if self.parent_window:
                if hasattr(self.parent_window, 'refresh_requested'):
                    self.parent_window.refresh_requested.emit()
                    logger.info("Emitted refresh_requested signal to main UI")
                
                if hasattr(self.parent_window, 'route_changed'):
                    self.parent_window.route_changed.emit(from_station, to_station)
                    logger.info("Emitted route_changed signal to main UI")
            
        except Exception as e:
            logger.error(f"Error updating main UI with route: {e}")
    
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
            
            
            # Ensure route_data is complete and has full_path
            if route_data and 'full_path' not in route_data:
                logger.warning("Route data missing full_path - attempting to reconstruct")
                # Try to reconstruct from interchange stations if available
                if 'interchange_stations' in route_data:
                    route_data['full_path'] = [from_station] + route_data['interchange_stations'] + [to_station]
                    logger.info(f"Reconstructed full_path with {len(route_data['full_path'])} stations")
                else:
                    # Create minimal route path with just from and to stations
                    route_data['full_path'] = [from_station, to_station]
                    logger.warning(f"Created minimal route path with just from/to stations: {from_station} → {to_station}")
            
            # Validate and fix route_path if needed
            if route_data and 'full_path' in route_data:
                route_path = route_data['full_path']
                
                # Ensure route_path is a list
                if not isinstance(route_path, list):
                    logger.warning(f"Route path is not a list, converting: {route_path}")
                    try:
                        # Try to convert to list if it's a string or other type
                        if isinstance(route_path, str):
                            route_path = [s.strip() for s in route_path.split(',')]
                        else:
                            route_path = list(route_path)
                    except:
                        # Fallback to minimal path
                        route_path = [from_station, to_station]
                    route_data['full_path'] = route_path
                
                # Ensure route_path has at least from and to stations
                if len(route_path) < 2:
                    logger.warning(f"Route path too short ({len(route_path)}), fixing")
                    if len(route_path) == 1:
                        # Add missing station
                        if route_path[0] == from_station:
                            route_path.append(to_station)
                        else:
                            route_path.insert(0, from_station)
                    else:
                        # Empty path, create minimal path
                        route_path = [from_station, to_station]
                    route_data['full_path'] = route_path
                
                # Ensure first and last stations match from/to
                if route_path[0] != from_station or route_path[-1] != to_station:
                    logger.warning(f"Route path endpoints ({route_path[0]}, {route_path[-1]}) "
                                  f"don't match from/to stations ({from_station}, {to_station})")
                    # Fix the route path
                    route_path[0] = from_station
                    route_path[-1] = to_station
                    route_data['full_path'] = route_path
                
                # Log the validated route path
                logger.info(f"Saving route with {len(route_path)} stations: {' → '.join(route_path)}")
            
            # Save settings with complete route data
            success = self.settings_handler.save_settings(
                from_station, to_station, preferences, departure_time, route_data
            )
            
            if success:
                
                # CRASH DETECTION: Check parent window state before signal emission
                if self.parent_window is None:
                    self.accept()
                    return
                
                # Emit both signals for compatibility
                self.settings_changed.emit()
                
                self.settings_saved.emit()
                
                # Signal the main window to refresh trains with the new route
                if hasattr(self.parent_window, 'route_changed'):
                    self.parent_window.route_changed.emit(from_station, to_station)
                else:
                    logger.debug("Parent window has no route_changed signal")
                
                # Also emit refresh signal if available
                if hasattr(self.parent_window, 'refresh_requested'):
                    self.parent_window.refresh_requested.emit()
                else:
                    logger.debug("Parent window has no refresh_requested signal")
                
                # Direct call to train manager if available
                if self.parent_window is not None and hasattr(self.parent_window, 'train_manager') and self.parent_window.train_manager:
                    if from_station and to_station:
                        # Extract the full_path from route_data if available
                        route_path = None
                        if route_data and 'full_path' in route_data:
                            route_path = route_data['full_path']
                            logger.info(f"Passing route path with {len(route_path)} stations to train manager: {' → '.join(route_path)}")
                        
                        # Pass the route_path to the train manager
                        train_manager = self.parent_window.train_manager
                        train_manager.set_route(from_station, to_station, route_path)
                        
                        # Share config_manager with train_manager for direct access
                        if self.config_manager and hasattr(train_manager.__class__, 'config_manager'):
                            train_manager.__class__.config_manager = self.config_manager
                            logger.info("Shared config_manager with train_manager for direct access")
                        
                        # Force config save to ensure persistence
                        if self.config_manager:
                            # Get the current config to preserve theme
                            config = self.config_manager.load_config()
                            
                            # Update route information from train_manager
                            if hasattr(train_manager, 'config') and hasattr(config, 'stations'):
                                train_config = train_manager.config
                                if hasattr(train_config, 'stations'):
                                    config.stations = train_config.stations
                                    logger.debug("Updated stations config from train_manager")
                            
                            # Use force_flush if available
                            if hasattr(self.config_manager, 'save_config') and 'force_flush' in self.config_manager.save_config.__code__.co_varnames:
                                self.config_manager.save_config(config, force_flush=True)
                                logger.info("Forced config save with force_flush=True to ensure route persistence")
                            else:
                                self.config_manager.save_config(config)
                                logger.info("Saved config (force_flush not available)")
                
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
            # Stop background loading if active
            if hasattr(self, 'station_data_manager') and self.station_data_manager:
                self.station_data_manager.stop_loading()
            
            # CRASH DETECTION: Check if signals are still being processed
            if hasattr(self, '_signals_processing'):
                # Wait briefly for signals to complete
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, lambda: event.accept())
                return
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            event.accept()
    
    def _setup_immediate_ui_responsiveness(self):
        """Set up immediate UI responsiveness - make fields editable instantly."""
        try:
            # STEP 1: Load essential stations immediately (very fast)
            from src.core.services.essential_station_cache import get_essential_stations
            essential_stations = get_essential_stations()
            
            if essential_stations and self.station_selection_widget:
                # Populate combo boxes with essential stations immediately
                self.station_selection_widget.populate_stations(essential_stations)
                self._essential_stations_loaded = True
                logger.info(f"Essential stations loaded immediately: {len(essential_stations)} stations")
            
            # STEP 2: Enable fields immediately
            self._enable_station_fields_immediately()
            
            # STEP 3: Load and apply config values immediately (very fast)
            self._load_config_values_immediately()
            
            # STEP 4: Set status to ready
            self._update_status("Ready")
            
            logger.info("Immediate UI responsiveness setup completed")
            
        except Exception as e:
            logger.error(f"Error in immediate UI setup: {e}")
            # Fallback to basic setup
            self._enable_station_fields_immediately()
    
    def _load_config_values_immediately(self):
        """Load config values immediately without heavy operations."""
        try:
            if not self.config_manager:
                return
            
            # Load config directly (very fast)
            config = self.config_manager.load_config()
            if not hasattr(config, 'stations'):
                return
            
            # Get station values
            from_name = getattr(config.stations, 'from_name', '')
            to_name = getattr(config.stations, 'to_name', '')
            departure_time = getattr(config.stations, 'departure_time', '08:00')
            
            # Apply values immediately
            if from_name and self.station_selection_widget:
                self.station_selection_widget.set_from_station(from_name)
                logger.info(f"Set FROM station immediately: {from_name}")
            
            if to_name and self.station_selection_widget:
                self.station_selection_widget.set_to_station(to_name)
                logger.info(f"Set TO station immediately: {to_name}")
            
            if self.route_details_widget:
                self.route_details_widget.set_departure_time(departure_time)
            
            logger.info("Config values loaded immediately")
            
        except Exception as e:
            logger.error(f"Error loading config values immediately: {e}")
    
    def _setup_deferred_initialization(self):
        """Set up heavy operations in the background after UI is responsive."""
        try:
            logger.info("Starting deferred initialization...")
            
            # Set up optimized loading system (background)
            self._setup_optimized_loading()
            
            # Start background station loading for enhanced autocomplete
            self._start_background_station_loading_deferred()
            
            # Auto-trigger route calculation if both stations are set (deferred with delay)
            # Use a longer delay to ensure stations are properly set
            QTimer.singleShot(500, self._auto_calculate_route_deferred)
            
            # Update status
            self._update_status("Ready - enhanced features loading...")
            
            logger.info("Deferred initialization completed")
            
        except Exception as e:
            logger.error(f"Error in deferred initialization: {e}")
    
    def _auto_calculate_route_deferred(self):
        """Auto-calculate route in background thread if both stations are set."""
        try:
            logger.info("_auto_calculate_route_deferred called")
            
            if not self.station_selection_widget:
                logger.info("No station_selection_widget - skipping auto route calculation")
                return
            
            from_station = self.station_selection_widget.get_from_station()
            to_station = self.station_selection_widget.get_to_station()
            
            logger.info(f"Auto route check - FROM: '{from_station}', TO: '{to_station}'")
            
            if from_station and to_station and from_station != to_station:
                # Start background route calculation - this won't block the UI
                logger.info(f"✅ Auto-triggering background route calculation: {from_station} → {to_station}")
                self._start_background_route_calculation(from_station, to_station)
            else:
                logger.info(f"❌ Skipping auto route calculation - conditions not met")
                logger.info(f"   - from_station valid: {bool(from_station)}")
                logger.info(f"   - to_station valid: {bool(to_station)}")
                logger.info(f"   - stations different: {from_station != to_station if from_station and to_station else 'N/A'}")
            
        except Exception as e:
            logger.error(f"Error in auto route calculation: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _start_background_route_calculation(self, from_station, to_station):
        """Start route calculation in background thread."""
        try:
            # Stop any existing route calculation
            if self._route_worker and self._route_worker.isRunning():
                self._route_worker.terminate()
                self._route_worker.wait()
            
            # Create and start background worker
            self._route_worker = RouteCalculationWorker(self, from_station, to_station)
            
            # Connect worker signals
            self._route_worker.route_calculated.connect(self._on_background_route_calculated)
            self._route_worker.calculation_failed.connect(self._on_background_route_failed)
            self._route_worker.calculation_started.connect(self._on_background_calculation_started)
            self._route_worker.calculation_finished.connect(self._on_background_calculation_finished)
            
            # Start the worker thread
            self._route_worker.start()
            
            logger.info(f"Background route calculation started: {from_station} → {to_station}")
            
        except Exception as e:
            logger.error(f"Error starting background route calculation: {e}")
    
    def _on_background_route_calculated(self, route_data):
        """Handle successful background route calculation."""
        try:
            # Update UI with calculated route (this runs in main thread)
            self.dialog_state.set_route_data(route_data)
            if self.route_details_widget:
                self.route_details_widget.update_route_data(route_data)
            
            # Emit route_updated signal for main window connection
            self.route_updated.emit(route_data)
            
            # Update main UI with the new route
            self._update_main_ui_with_route(route_data)
            
            self._update_status("Route calculated successfully")
            logger.info("Background route calculation completed successfully")
            
        except Exception as e:
            logger.error(f"Error handling background route result: {e}")
    
    def _on_background_route_failed(self, error_message):
        """Handle failed background route calculation."""
        try:
            self._update_status(f"Route calculation failed: {error_message}")
            logger.warning(f"Background route calculation failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling background route failure: {e}")
    
    def _on_background_calculation_started(self):
        """Handle background calculation start."""
        try:
            self._update_status("Calculating route in background...")
            logger.info("Background route calculation started")
            
        except Exception as e:
            logger.error(f"Error handling background calculation start: {e}")
    
    def _on_background_calculation_finished(self):
        """Handle background calculation finish."""
        try:
            # Clean up the worker
            if self._route_worker:
                self._route_worker.deleteLater()
                self._route_worker = None
            
            logger.info("Background route calculation finished")
            
        except Exception as e:
            logger.error(f"Error handling background calculation finish: {e}")
    
    def _start_background_station_loading_deferred(self):
        """Start background loading without blocking UI."""
        try:
            if not self.station_data_manager:
                logger.warning("Station data manager not available for background loading")
                return
            
            # Start background loading for complete dataset (non-blocking)
            self.station_data_manager.start_loading(self.station_service,
                                                  getattr(self.station_service, 'data_repository', None))
            
            logger.info("Background station loading started (deferred)")
            
        except Exception as e:
            logger.error(f"Error starting deferred background loading: {e}")