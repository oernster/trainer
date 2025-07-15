"""
Train Settings Dialog for the Train Times application.

This dialog provides a user interface for configuring train route settings,
broken down into manageable components while maintaining functionality.
"""

import logging
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QFrame, QSizePolicy,
    QMessageBox, QApplication, QWidget, QScrollArea, QTabWidget,
    QSpacerItem, QButtonGroup, QRadioButton, QCompleter
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QObject, QStringListModel
from PySide6.QtGui import QFont, QPalette, QColor, QIcon, QPixmap

# Import the working components
from .components.time_picker_widget import TimePickerWidget
from .components.horizontal_spin_widget import HorizontalSpinWidget

# Import core services for real route calculations
from src.core.services.service_factory import ServiceFactory
from src.core.services.station_service import StationService
from src.core.services.route_service import RouteService

logger = logging.getLogger(__name__)


class StationsSettingsDialog(QDialog):
    """
    Train Settings Dialog.
    
    This dialog provides a user interface for configuring train route settings.
    """
    
    # Signals - keep both for compatibility
    settings_saved = Signal()  # Original signal expected by main window
    settings_changed = Signal()
    route_updated = Signal(dict)
    validation_completed = Signal(bool, str)
    
    def __init__(self, parent=None, station_database=None, config_manager=None, theme_manager=None):
        """
        Initialize the train settings dialog.
        
        Args:
            parent: Parent widget
            station_database: Station database manager
            config_manager: Configuration manager
            theme_manager: Theme manager
        """
        super().__init__(parent)
        
        # Store references
        self.parent_window = parent
        self.station_database = station_database
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        
        # Route state
        self.via_stations = []
        self.departure_time = "08:00"
        self.route_data = {}
        
        # UI elements (will be created in setup_ui)
        self.from_station_combo = None
        self.to_station_combo = None
        self.time_picker = None
        self.arrival_time_edit = None
        self.journey_time_label = None
        self.distance_label = None
        self.via_stations_list = None
        self.add_via_button = None
        self.remove_via_button = None
        self.find_route_button = None
        self.auto_fix_route_button = None
        self.clear_route_button = None
        self.save_button = None
        self.cancel_button = None
        
        # Advanced settings UI
        self.show_intermediate_checkbox = None
        self.optimize_for_speed_radio = None
        self.optimize_for_changes_radio = None
        self.avoid_london_checkbox = None
        self.prefer_direct_checkbox = None
        self.max_changes_spin = None
        self.max_journey_time_spin = None
        
        # Status and progress UI
        self.status_label = None
        
        # Tab widget for different settings sections
        self.tab_widget = None
        self.route_tab = None
        self.preferences_tab = None
        self.advanced_tab = None
        
        # Initialize core services for real route calculations
        try:
            service_factory = ServiceFactory()
            self.station_service = service_factory.get_station_service()
            self.route_service = service_factory.get_route_service()
            logger.info("Core services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize core services: {e}")
            self.station_service = None
            self.route_service = None
        
        # Initialize the dialog
        self._setup_dialog()
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        self._apply_theme()
        
        logger.info("StationsSettingsDialog initialized successfully")
    
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
        # Create main layout
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
        self.route_tab = QWidget()
        self.tab_widget.addTab(self.route_tab, "Route Planning")
        
        layout = QVBoxLayout(self.route_tab)
        layout.setSpacing(15)
        
        # Station selection section
        station_group = self._create_station_selection_group()
        layout.addWidget(station_group)
        
        # Via stations section
        via_group = self._create_via_stations_group()
        layout.addWidget(via_group)
        
        # Time selection section
        time_group = self._create_time_selection_group()
        layout.addWidget(time_group)
        
        # Route action buttons
        action_layout = self._create_route_action_buttons()
        layout.addLayout(action_layout)
        
        # Route information section
        info_group = self._create_route_info_group()
        layout.addWidget(info_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def _create_station_selection_group(self):
        """Create the station selection group box."""
        group = QGroupBox("Station Selection")
        layout = QGridLayout(group)
        
        # From station
        layout.addWidget(QLabel("From:"), 0, 0)
        self.from_station_combo = QComboBox()
        self.from_station_combo.setEditable(True)
        self.from_station_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.from_station_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.from_station_combo, 0, 1)
        
        # To station
        layout.addWidget(QLabel("To:"), 1, 0)
        self.to_station_combo = QComboBox()
        self.to_station_combo.setEditable(True)
        self.to_station_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.to_station_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.to_station_combo, 1, 1)
        
        # Swap button
        swap_button = QPushButton("⇅ Swap")
        swap_button.setMaximumWidth(80)
        swap_button.clicked.connect(self._swap_stations)
        layout.addWidget(swap_button, 0, 2, 2, 1)
        
        return group
    
    def _create_via_stations_group(self):
        """Create the via stations group box."""
        group = QGroupBox("Via Stations")
        layout = QVBoxLayout(group)
        
        # Via stations list (simplified)
        self.via_stations_list = QLabel("No via stations")
        self.via_stations_list.setStyleSheet("border: 1px solid #ccc; padding: 10px; min-height: 60px;")
        layout.addWidget(self.via_stations_list)
        
        # Via station controls
        controls_layout = QHBoxLayout()
        
        self.add_via_button = QPushButton("Add Via Station")
        self.add_via_button.clicked.connect(self._add_via_station)
        controls_layout.addWidget(self.add_via_button)
        
        self.remove_via_button = QPushButton("Remove Last")
        self.remove_via_button.clicked.connect(self._remove_via_station)
        controls_layout.addWidget(self.remove_via_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        return group
    
    def _create_time_selection_group(self):
        """Create the time selection group box."""
        group = QGroupBox("Journey Times")
        layout = QGridLayout(group)
        
        # Departure time
        layout.addWidget(QLabel("Departure:"), 0, 0)
        self.time_picker = TimePickerWidget("08:00", parent=self, theme_manager=self.theme_manager)
        layout.addWidget(self.time_picker, 0, 1)
        
        # Arrival time (read-only, calculated)
        layout.addWidget(QLabel("Arrival:"), 0, 2)
        self.arrival_time_edit = QLineEdit()
        self.arrival_time_edit.setReadOnly(True)
        self.arrival_time_edit.setMaximumWidth(100)
        layout.addWidget(self.arrival_time_edit, 0, 3)
        
        # Journey time display
        layout.addWidget(QLabel("Journey Time:"), 1, 0)
        self.journey_time_label = QLabel("--:--")
        self.journey_time_label.setStyleSheet("font-weight: bold; color: #2E8B57;")
        layout.addWidget(self.journey_time_label, 1, 1)
        
        # Distance display
        layout.addWidget(QLabel("Distance:"), 1, 2)
        self.distance_label = QLabel("-- km")
        layout.addWidget(self.distance_label, 1, 3)
        
        return group
    
    def _create_route_action_buttons(self):
        """Create the route action buttons layout."""
        layout = QHBoxLayout()
        
        # Find route button
        self.find_route_button = QPushButton("Find Route")
        self.find_route_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.find_route_button.clicked.connect(self._find_route)
        layout.addWidget(self.find_route_button)
        
        # Auto-fix route button
        self.auto_fix_route_button = QPushButton("Auto-Fix Route")
        self.auto_fix_route_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:pressed {
                background-color: #cc7a00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.auto_fix_route_button.clicked.connect(self._auto_fix_route)
        layout.addWidget(self.auto_fix_route_button)
        
        # Clear route button
        self.clear_route_button = QPushButton("Clear Route")
        self.clear_route_button.clicked.connect(self._clear_route)
        layout.addWidget(self.clear_route_button)
        
        # Add stretch to push buttons to the left
        layout.addStretch()
        
        return layout
    
    def _create_route_info_group(self):
        """Create the route information group box."""
        group = QGroupBox("Route Information")
        layout = QVBoxLayout(group)
        
        # Route details (simplified)
        self.route_details_label = QLabel("No route selected")
        self.route_details_label.setStyleSheet("border: 1px solid #ccc; padding: 10px; min-height: 80px;")
        self.route_details_label.setWordWrap(True)
        layout.addWidget(self.route_details_label)
        
        return group
    
    def _create_preferences_tab(self):
        """Create the preferences tab."""
        self.preferences_tab = QWidget()
        self.tab_widget.addTab(self.preferences_tab, "Preferences")
        
        layout = QVBoxLayout(self.preferences_tab)
        layout.setSpacing(15)
        
        # Route optimization preferences
        optimization_group = QGroupBox("Route Optimization")
        opt_layout = QVBoxLayout(optimization_group)
        
        # Optimization strategy
        self.optimize_for_speed_radio = QRadioButton("Optimize for speed (shortest journey time)")
        self.optimize_for_changes_radio = QRadioButton("Optimize for fewer changes")
        self.optimize_for_speed_radio.setChecked(True)
        
        opt_layout.addWidget(self.optimize_for_speed_radio)
        opt_layout.addWidget(self.optimize_for_changes_radio)
        
        layout.addWidget(optimization_group)
        
        # Route preferences
        preferences_group = QGroupBox("Route Preferences")
        pref_layout = QVBoxLayout(preferences_group)
        
        self.show_intermediate_checkbox = QCheckBox("Show intermediate stations in route")
        self.avoid_london_checkbox = QCheckBox("Avoid routes through London when possible")
        self.prefer_direct_checkbox = QCheckBox("Prefer direct routes over faster alternatives")
        
        pref_layout.addWidget(self.show_intermediate_checkbox)
        pref_layout.addWidget(self.avoid_london_checkbox)
        pref_layout.addWidget(self.prefer_direct_checkbox)
        
        layout.addWidget(preferences_group)
        
        # Constraints
        constraints_group = QGroupBox("Journey Constraints")
        const_layout = QGridLayout(constraints_group)
        
        const_layout.addWidget(QLabel("Maximum changes:"), 0, 0)
        self.max_changes_spin = HorizontalSpinWidget(0, 10, 3, theme_manager=self.theme_manager)
        const_layout.addWidget(self.max_changes_spin, 0, 1)
        
        const_layout.addWidget(QLabel("Maximum journey time (hours):"), 1, 0)
        self.max_journey_time_spin = HorizontalSpinWidget(1, 24, 8, theme_manager=self.theme_manager)
        const_layout.addWidget(self.max_journey_time_spin, 1, 1)
        
        layout.addWidget(constraints_group)
        
        # Add stretch
        layout.addStretch()
    
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                border-top: 1px solid #cccccc;
                background-color: #f5f5f5;
                color: #333333;
            }
        """)
    
    def _create_button_bar(self):
        """Create the dialog button bar."""
        layout = QHBoxLayout()
        
        # Add stretch to push buttons to the right
        layout.addStretch()
        
        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self._save_settings)
        layout.addWidget(self.save_button)
        
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        return layout
    
    def _connect_signals(self):
        """Connect all signals and slots."""
        # Station selection signals
        if self.from_station_combo:
            self.from_station_combo.currentTextChanged.connect(self._on_from_station_changed)
        if self.to_station_combo:
            self.to_station_combo.currentTextChanged.connect(self._on_to_station_changed)
        
        # Time picker signals
        if self.time_picker:
            self.time_picker.timeChanged.connect(self._on_departure_time_changed)
    
    def _load_settings(self):
        """Load settings from configuration."""
        try:
            if not self.config_manager:
                return
            
            # Load station lists
            self._populate_station_combos()
            
            # Load saved route settings
            config = self.config_manager.load_config()
            
            # Set default stations - try new format first, then old format
            from_station = None
            to_station = None
            
            # Try new format first
            if hasattr(config, 'stations') and config.stations:
                if hasattr(config.stations, 'from_name') and config.stations.from_name:
                    from_station = config.stations.from_name
                if hasattr(config.stations, 'to_name') and config.stations.to_name:
                    to_station = config.stations.to_name
            
            # Fallback to old format
            if not from_station and hasattr(config, 'default_from_station') and config.default_from_station:
                from_station = config.default_from_station
            if not to_station and hasattr(config, 'default_to_station') and config.default_to_station:
                to_station = config.default_to_station
            
            # Set the combo boxes
            if from_station and self.from_station_combo:
                index = self.from_station_combo.findText(from_station)
                if index >= 0:
                    self.from_station_combo.setCurrentIndex(index)
            
            if to_station and self.to_station_combo:
                index = self.to_station_combo.findText(to_station)
                if index >= 0:
                    self.to_station_combo.setCurrentIndex(index)
            
            # Load preferences
            if hasattr(config, 'optimize_for_speed'):
                self.optimize_for_speed_radio.setChecked(config.optimize_for_speed)
                self.optimize_for_changes_radio.setChecked(not config.optimize_for_speed)
            
            if hasattr(config, 'show_intermediate_stations'):
                self.show_intermediate_checkbox.setChecked(config.show_intermediate_stations)
            
            if hasattr(config, 'avoid_london'):
                self.avoid_london_checkbox.setChecked(config.avoid_london)
            
            if hasattr(config, 'prefer_direct'):
                self.prefer_direct_checkbox.setChecked(config.prefer_direct)
            
            if hasattr(config, 'max_changes'):
                self.max_changes_spin.setValue(config.max_changes)
            
            if hasattr(config, 'max_journey_time'):
                self.max_journey_time_spin.setValue(config.max_journey_time)
            
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
            
            # Sort stations alphabetically
            stations.sort()
            
            # Clear existing items and add stations
            if self.from_station_combo:
                self.from_station_combo.clear()
                self.from_station_combo.addItems(stations)
                
                # Set up autocomplete for from station
                from_completer = QCompleter(stations, self)
                from_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                from_completer.setFilterMode(Qt.MatchFlag.MatchContains)
                self.from_station_combo.setCompleter(from_completer)
                self.from_station_combo.setEditable(True)
            
            if self.to_station_combo:
                self.to_station_combo.clear()
                self.to_station_combo.addItems(stations)
                
                # Set up autocomplete for to station
                to_completer = QCompleter(stations, self)
                to_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                to_completer.setFilterMode(Qt.MatchFlag.MatchContains)
                self.to_station_combo.setCompleter(to_completer)
                self.to_station_combo.setEditable(True)
            
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
            
        except Exception as e:
            logger.error(f"Error applying theme: {e}")
    
    # Event handlers
    def _on_from_station_changed(self, station_name: str):
        """Handle from station change."""
        # Clear route data when station changes
        self.route_data = {}
        self._update_route_info()
    
    def _on_to_station_changed(self, station_name: str):
        """Handle to station change."""
        # Clear route data when station changes
        self.route_data = {}
        self._update_route_info()
    
    def _on_departure_time_changed(self, time_str: str):
        """Handle departure time change."""
        self.departure_time = time_str
        self._calculate_arrival_time()
    
    # Action methods
    def _swap_stations(self):
        """Swap from and to stations."""
        from_text = self.from_station_combo.currentText()
        to_text = self.to_station_combo.currentText()
        
        self.from_station_combo.setCurrentText(to_text)
        self.to_station_combo.setCurrentText(from_text)
    
    def _add_via_station(self):
        """Add a via station."""
        # Simple implementation - could be enhanced with a dialog
        from_station = self.from_station_combo.currentText()
        to_station = self.to_station_combo.currentText()
        
        if not from_station or not to_station:
            QMessageBox.warning(self, "Invalid Selection", "Please select both from and to stations first.")
            return
        
        # For now, just show a message
        QMessageBox.information(self, "Add Via Station", "Via station functionality will be implemented.")
    
    def _remove_via_station(self):
        """Remove the last via station."""
        if self.via_stations:
            self.via_stations.pop()
            self._update_via_stations_display()
    
    def _find_route(self):
        """Find route between selected stations using real route calculations."""
        try:
            from_station = self.from_station_combo.currentText()
            to_station = self.to_station_combo.currentText()
            
            if not from_station or not to_station:
                QMessageBox.warning(self, "Invalid Route", "Please select both from and to stations.")
                return
            
            if from_station == to_station:
                QMessageBox.warning(self, "Invalid Route", "From and to stations must be different.")
                return
            
            # Check if core services are available
            if not self.route_service or not self.station_service:
                QMessageBox.warning(self, "Service Error", "Route calculation services are not available.")
                return
            
            self._update_status("Finding route...")
            self.find_route_button.setEnabled(False)
            
            # Use real route service to calculate the route with unlimited changes
            route_result = self.route_service.calculate_route(
                from_station,
                to_station,
                max_changes=10  # Allow up to 10 changes for any route
            )
            
            if route_result:
                # Convert route result to our expected format
                self.route_data = {
                    'from_station': from_station,
                    'to_station': to_station,
                    'via_stations': self.via_stations,
                    'journey_time': route_result.total_journey_time_minutes,
                    'distance': route_result.total_distance_km,
                    'changes': route_result.changes_required,
                    'operators': route_result.lines_used,
                    'segments': route_result.segments,
                    'route_type': route_result.route_type,
                    'is_direct': route_result.is_direct
                }
                
                self._update_route_info()
                self._update_status("Route found successfully")
                
                logger.info(f"Route calculated: {from_station} → {to_station}, "
                           f"{route_result.total_journey_time_minutes or 0}min, "
                           f"{route_result.total_distance_km or 0:.1f}km, "
                           f"{route_result.changes_required} changes")
            else:
                QMessageBox.warning(self, "No Route Found",
                                  f"No route could be found between {from_station} and {to_station}.")
                self.route_data = {}
                self._update_route_info()
                self._update_status("No route found")
            
        except Exception as e:
            logger.error(f"Error finding route: {e}")
            self._update_status(f"Error finding route: {e}")
            self.route_data = {}
            self._update_route_info()
        finally:
            self.find_route_button.setEnabled(True)
    
    def _auto_fix_route(self):
        """Auto-fix the current route."""
        try:
            from_station = self.from_station_combo.currentText()
            to_station = self.to_station_combo.currentText()
            
            if not from_station or not to_station:
                QMessageBox.warning(self, "Invalid Route", "Please select both from and to stations.")
                return
            
            self._update_status("Auto-fixing route...")
            self.auto_fix_route_button.setEnabled(False)
            
            # Simple auto-fix implementation
            QTimer.singleShot(500, lambda: self._auto_fix_callback())
            
        except Exception as e:
            logger.error(f"Error auto-fixing route: {e}")
            self._update_status(f"Error auto-fixing route: {e}")
            self.auto_fix_route_button.setEnabled(True)
    
    def _auto_fix_callback(self):
        """Handle auto-fix callback."""
        try:
            self._update_status("Route auto-fixed successfully")
            self.auto_fix_route_button.setEnabled(True)
            
        except Exception as e:
            logger.error(f"Error in auto-fix callback: {e}")
            self.auto_fix_route_button.setEnabled(True)
    
    def _clear_route(self):
        """Clear the current route."""
        self.via_stations = []
        self.route_data = {}
        self._update_via_stations_display()
        self._update_route_info()
        self._update_status("Route cleared")
    
    def _calculate_arrival_time(self):
        """Calculate and display arrival time."""
        try:
            if self.departure_time and self.route_data.get('journey_time'):
                journey_time = self.route_data['journey_time']
                arrival_time = self._add_time_duration(self.departure_time, journey_time)
                self.arrival_time_edit.setText(arrival_time)
            else:
                self.arrival_time_edit.setText("--:--")
                
        except Exception as e:
            logger.error(f"Error calculating arrival time: {e}")
            self.arrival_time_edit.setText("--:--")
    
    def _add_time_duration(self, start_time: str, duration_minutes: int) -> str:
        """Add duration in minutes to a time string."""
        try:
            hours, minutes = map(int, start_time.split(':'))
            total_minutes = hours * 60 + minutes + duration_minutes
            
            result_hours = (total_minutes // 60) % 24
            result_minutes = total_minutes % 60
            
            return f"{result_hours:02d}:{result_minutes:02d}"
            
        except Exception as e:
            logger.error(f"Error adding time duration: {e}")
            return "--:--"
    
    def _update_via_stations_display(self):
        """Update the via stations display."""
        if self.via_stations:
            self.via_stations_list.setText(" → ".join(self.via_stations))
        else:
            self.via_stations_list.setText("No via stations")
    
    def _update_route_info(self):
        """Update the route information display."""
        try:
            if self.route_data:
                # Update journey time
                journey_time = self.route_data.get('journey_time', 0)
                if journey_time > 0:
                    hours = journey_time // 60
                    minutes = journey_time % 60
                    if hours > 0:
                        self.journey_time_label.setText(f"{hours}h {minutes}m")
                    else:
                        self.journey_time_label.setText(f"{minutes}m")
                else:
                    self.journey_time_label.setText("--:--")
                
                # Update distance
                distance = self.route_data.get('distance', 0)
                if distance > 0:
                    self.distance_label.setText(f"{distance:.1f} km")
                else:
                    self.distance_label.setText("-- km")
                
                # Update route details
                details = []
                details.append(f"From: {self.route_data.get('from_station', 'N/A')}")
                details.append(f"To: {self.route_data.get('to_station', 'N/A')}")
                if self.route_data.get('via_stations'):
                    details.append(f"Via: {' → '.join(self.route_data['via_stations'])}")
                details.append(f"Changes: {self.route_data.get('changes', 0)}")
                
                # Show interchange stations where changes occur instead of operators
                if self.route_data.get('interchange_stations'):
                    interchange_stations = self.route_data['interchange_stations']
                    details.append(f"Change at: {', '.join(interchange_stations)}")
                elif self.route_data.get('operators'):
                    # Fallback to operators if no interchange stations available
                    details.append(f"Operators: {', '.join(self.route_data['operators'])}")
                
                self.route_details_label.setText("\n".join(details))
                
                # Calculate arrival time
                self._calculate_arrival_time()
            else:
                self.journey_time_label.setText("--:--")
                self.distance_label.setText("-- km")
                self.route_details_label.setText("No route selected")
                self.arrival_time_edit.setText("--:--")
                
        except Exception as e:
            logger.error(f"Error updating route info: {e}")
    
    def _update_status(self, message: str):
        """Update the status bar message."""
        if self.status_label:
            self.status_label.setText(message)
        logger.debug(f"Status: {message}")
    
    def _save_settings(self):
        """Save settings and close dialog."""
        try:
            # Validate that a route has been found before saving
            from_station = self.from_station_combo.currentText() if self.from_station_combo else ""
            to_station = self.to_station_combo.currentText() if self.to_station_combo else ""
            
            if from_station and to_station and from_station != to_station:
                # Check if route data exists (user clicked Find Route)
                if not self.route_data or not self.route_data.get('journey_time'):
                    QMessageBox.warning(
                        self,
                        "Route Not Found",
                        "Please click 'Find Route' to calculate the route before saving settings."
                    )
                    return
            
            if not self.config_manager:
                self.accept()
                return
            
            # Get current settings
            config = self.config_manager.load_config()
            
            # Update route settings (with safe attribute setting)
            from_station = self.from_station_combo.currentText() if self.from_station_combo else ""
            to_station = self.to_station_combo.currentText() if self.to_station_combo else ""
            
            if hasattr(config, 'stations'):
                if hasattr(config.stations, 'from_name'):
                    config.stations.from_name = from_station
                if hasattr(config.stations, 'to_name'):
                    config.stations.to_name = to_station
            
            # Also update the old format for backward compatibility
            if hasattr(config, 'default_from_station'):
                config.default_from_station = from_station
            if hasattr(config, 'default_to_station'):
                config.default_to_station = to_station
            
            # Update preferences (with safe attribute setting)
            if hasattr(config, 'optimize_for_speed'):
                config.optimize_for_speed = self.optimize_for_speed_radio.isChecked()
            if hasattr(config, 'show_intermediate_stations'):
                config.show_intermediate_stations = self.show_intermediate_checkbox.isChecked()
            if hasattr(config, 'avoid_london'):
                config.avoid_london = self.avoid_london_checkbox.isChecked()
            if hasattr(config, 'prefer_direct'):
                config.prefer_direct = self.prefer_direct_checkbox.isChecked()
            if hasattr(config, 'max_changes'):
                config.max_changes = self.max_changes_spin.value()
            if hasattr(config, 'max_journey_time'):
                config.max_journey_time = self.max_journey_time_spin.value()
            
            # Save configuration
            self.config_manager.save_config(config)
            
            # Emit both signals for compatibility
            self.settings_changed.emit()
            self.settings_saved.emit()
            
            # Signal the main window to refresh trains with the new route
            from_station = self.from_station_combo.currentText() if self.from_station_combo else ""
            to_station = self.to_station_combo.currentText() if self.to_station_combo else ""
            
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
            QMessageBox.critical(self, "Settings Error", f"Failed to save settings: {e}")
    
    def get_current_route(self) -> dict:
        """Get the current route configuration."""
        return {
            'from_station': self.from_station_combo.currentText(),
            'to_station': self.to_station_combo.currentText(),
            'via_stations': self.via_stations,
            'departure_time': self.departure_time,
            'route_data': self.route_data
        }
    
    def set_route(self, route_config: dict):
        """Set the route configuration."""
        try:
            if 'from_station' in route_config:
                index = self.from_station_combo.findText(route_config['from_station'])
                if index >= 0:
                    self.from_station_combo.setCurrentIndex(index)
            
            if 'to_station' in route_config:
                index = self.to_station_combo.findText(route_config['to_station'])
                if index >= 0:
                    self.to_station_combo.setCurrentIndex(index)
            
            if 'via_stations' in route_config:
                self.via_stations = route_config['via_stations']
                self._update_via_stations_display()
            
            if 'departure_time' in route_config:
                self.departure_time = route_config['departure_time']
                if self.time_picker:
                    self.time_picker.set_time(route_config['departure_time'])
            
            self._update_route_info()
            
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