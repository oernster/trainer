"""
Stations settings dialog for the Train Times application.
Author: Oliver Ernster

This module provides a dialog for configuring station settings, display preferences, and refresh settings.
"""

import logging
import asyncio
import requests
import time
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QMessageBox,
    QTabWidget,
    QWidget,
    QProgressDialog,
    QCompleter,
    QListWidget,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QStringListModel
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import QApplication
from ..managers.config_manager import ConfigManager, ConfigData, ConfigurationError
from ..managers.theme_manager import ThemeManager
from ..managers.station_database_manager import StationDatabaseManager
from ..workers.worker_manager import WorkerManager
from version import __train_settings_title__

# Use internal database for station search - no API needed
station_database = StationDatabaseManager()

# Load the database immediately and log status
try:
    if station_database.load_database():
        print(f"Station database loaded successfully: {len(station_database.all_stations)} stations")
        print(f"Database stats: {station_database.get_database_stats()}")
    else:
        print("Failed to load station database")
except Exception as e:
    print(f"Error loading station database: {e}")


class HorizontalSpinWidget(QWidget):
    """A horizontal spin control with left/right arrows and a value display, based on test.py."""

    valueChanged = Signal(int)

    def __init__(
        self,
        minimum=0,
        maximum=100,
        initial_value=0,
        step=1,
        suffix="",
        parent=None,
        theme_manager=None,
    ):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.suffix = suffix
        self._value = initial_value
        self.theme_manager = theme_manager

        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Value display
        self.value_label = QLabel(str(self._value) + self.suffix)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumWidth(120)
        self.value_label.setFixedHeight(32)

        # Down arrow button (left side) - MUCH LARGER
        self.down_button = QPushButton("◀")
        self.down_button.setFixedSize(60, 32)
        self.down_button.clicked.connect(self.decrement)

        # Up arrow button (right side) - MUCH LARGER
        self.up_button = QPushButton("▶")
        self.up_button.setFixedSize(60, 32)
        self.up_button.clicked.connect(self.increment)

        # Add widgets to layout
        main_layout.addWidget(self.value_label)
        main_layout.addWidget(self.down_button)
        main_layout.addWidget(self.up_button)

    def setup_style(self):
        """Apply styling to the widget."""
        # Get theme colors if theme manager is available
        if self.theme_manager:
            current_theme = self.theme_manager.current_theme
            if current_theme == "light":
                # Light theme styling
                primary_accent = "#1976d2"
                text_primary = "#1976d2"
                background_primary = "#f0f0f0"
                background_hover = "#e0e0e0"
                border_primary = "#cccccc"
                disabled_bg = "#f5f5f5"
                disabled_text = "#cccccc"
            else:
                # Dark theme styling
                primary_accent = "#1976d2"
                text_primary = "#ffffff"
                background_primary = "#2d2d2d"
                background_hover = "#404040"
                border_primary = "#404040"
                disabled_bg = "#424242"
                disabled_text = "#9e9e9e"
        else:
            # Fallback to dark theme
            primary_accent = "#1976d2"
            text_primary = "#ffffff"
            background_primary = "#2d2d2d"
            background_hover = "#404040"
            border_primary = "#404040"
            disabled_bg = "#424242"
            disabled_text = "#9e9e9e"

        # Button styling
        button_style = f"""
            QPushButton {{
                background-color: {primary_accent};
                border: 1px solid {primary_accent};
                border-radius: 3px;
                font-weight: bold;
                font-size: 24px;
                color: #ffffff;
            }}
            QPushButton:hover {{
                background-color: {background_hover};
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: {primary_accent};
                border: 1px solid {primary_accent};
                color: #ffffff;
            }}
            QPushButton:disabled {{
                background-color: {disabled_bg};
                color: {disabled_text};
            }}
        """

        # Label styling
        label_style = f"""
            QLabel {{
                background-color: {background_primary};
                border: 1px solid {border_primary};
                border-radius: 2px;
                padding: 4px;
                font-weight: bold;
                color: {text_primary};
            }}
        """

        self.up_button.setStyleSheet(button_style)
        self.down_button.setStyleSheet(button_style)
        self.value_label.setStyleSheet(label_style)

    def increment(self):
        """Increment the value by the step amount."""
        new_value = min(self._value + self.step, self.maximum)
        self.set_value(new_value)

    def decrement(self):
        """Decrement the value by the step amount."""
        new_value = max(self._value - self.step, self.minimum)
        self.set_value(new_value)

    def set_value(self, value):
        """Set the current value."""
        if self.minimum <= value <= self.maximum:
            old_value = self._value
            self._value = value
            self.value_label.setText(str(value) + self.suffix)

            # Update button states
            self.up_button.setEnabled(value < self.maximum)
            self.down_button.setEnabled(value > self.minimum)

            if old_value != value:
                self.valueChanged.emit(value)

    def value(self):
        """Get the current value."""
        return self._value

    def setValue(self, value):
        """Set the current value (Qt-style method name)."""
        self.set_value(value)

    def setRange(self, minimum, maximum):
        """Set the minimum and maximum values."""
        self.minimum = minimum
        self.maximum = maximum
        # Ensure current value is within new range
        self.set_value(max(minimum, min(self._value, maximum)))

    def setSuffix(self, suffix):
        """Set the suffix text."""
        self.suffix = suffix
        self.value_label.setText(str(self._value) + self.suffix)


logger = logging.getLogger(__name__)


class StationsSettingsDialog(QDialog):
    """
    Stations settings dialog for configuring station settings, display preferences, and refresh settings.

    Features:
    - Station configuration
    - Display preferences
    - Refresh settings
    """

    # Signal emitted when settings are saved
    settings_saved = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None, theme_manager=None):
        """
        Initialize the stations settings dialog.

        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
            theme_manager: Shared theme manager instance
        """
        super().__init__(parent)

        # Make dialog completely invisible during initialization
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)

        self.config_manager = config_manager
        self.config: Optional[ConfigData] = None

        # Use shared theme manager or create new one
        self.theme_manager = theme_manager or ThemeManager()
        
        # Initialize worker manager for async operations
        self.worker_manager = WorkerManager(station_database, self)
        self.pending_operations = {}  # Track pending async operations
        
        # Setup worker connections
        self._setup_worker_connections()

        # Load current configuration
        try:
            self.config = self.config_manager.load_config()
        except ConfigurationError as e:
            logger.error(f"Failed to load config in stations settings dialog: {e}")
            self.config = None

        self.setup_ui()
        self.load_current_settings()

        # Apply theme styling
        self.apply_theme_styling()

        # Don't show here - let exec() handle it when called

    def _setup_worker_connections(self):
        """Setup connections to worker threads for async operations."""
        # Connect worker manager signals
        self.worker_manager.operation_completed.connect(self._on_operation_completed)
        self.worker_manager.operation_failed.connect(self._on_operation_failed)
        self.worker_manager.progress_updated.connect(self._on_progress_updated)
        
    def _on_operation_completed(self, operation_type: str, request_id: str, result: dict):
        """Handle completed async operations."""
        if request_id not in self.pending_operations:
            return
            
        operation_info = self.pending_operations[request_id]
        
        if operation_type == "search":
            self._handle_search_completed(operation_info, result)
        elif operation_type == "auto_fix":
            self._handle_auto_fix_completed(operation_info, result)
        elif operation_type == "suggest_via":
            self._handle_via_suggestions_completed(operation_info, result)
        elif operation_type == "fastest_route":
            self._handle_fastest_route_completed(operation_info, result)
            
        # Remove from pending operations
        del self.pending_operations[request_id]
        
    def _on_operation_failed(self, operation_type: str, request_id: str, error_message: str):
        """Handle failed async operations."""
        if request_id in self.pending_operations:
            operation_info = self.pending_operations[request_id]
            
            # Show error message
            QMessageBox.critical(self, "Operation Failed", f"{operation_type.title()} failed: {error_message}")
            
            # Hide any progress indicators
            self._hide_progress_indicators(operation_info)
            
            # Remove from pending operations
            del self.pending_operations[request_id]
            
    def _on_progress_updated(self, request_id: str, percentage: int, message: str):
        """Handle progress updates for async operations."""
        if request_id in self.pending_operations:
            operation_info = self.pending_operations[request_id]
            self._update_progress_indicator(operation_info, percentage, message)

    def _cancel_pending_operation(self, operation_type: str):
        """Cancel any pending operations of the specified type."""
        try:
            operations_to_cancel = []
            for request_id, operation_info in self.pending_operations.items():
                if operation_info.get('type') == operation_type:
                    operations_to_cancel.append(request_id)
            
            for request_id in operations_to_cancel:
                # Cancel the operation in worker manager
                self.worker_manager.cancel_operation(request_id)
                # Remove from pending operations
                del self.pending_operations[request_id]
                
        except Exception as e:
            print(f"Error canceling pending operation {operation_type}: {e}")
    
    def _show_operation_progress(self, operation_type: str, message: str):
        """Show progress indicator for an operation."""
        try:
            # Update the route info label to show progress
            if operation_type == "auto_fix":
                self.route_info_label.setText(f"🔧 {message}")
                self.route_info_label.setStyleSheet("color: #ff9800; font-style: italic; font-weight: bold;")
                # Disable the auto-fix button during operation
                self.auto_fix_route_button.setEnabled(False)
                self.auto_fix_route_button.setText("Auto-Fixing...")
            elif operation_type == "suggest_via":
                self.route_info_label.setText(f"🔍 {message}")
                self.route_info_label.setStyleSheet("color: #1976d2; font-style: italic; font-weight: bold;")
                # Disable the suggest button during operation
                self.suggest_route_button.setEnabled(False)
                self.suggest_route_button.setText("Suggesting...")
            elif operation_type == "fastest_route":
                self.route_info_label.setText(f"⚡ {message}")
                self.route_info_label.setStyleSheet("color: #1976d2; font-style: italic; font-weight: bold;")
                # Disable the fastest route button during operation
                self.fastest_route_button.setEnabled(False)
                self.fastest_route_button.setText("Finding...")
            elif operation_type == "search":
                # Could add search progress indicators here
                pass
        except Exception as e:
            print(f"Error showing operation progress: {e}")
    
    def _hide_progress_indicators(self, operation_info: dict):
        """Hide progress indicators for an operation."""
        try:
            operation_type = operation_info.get('type', '')
            if operation_type == "auto_fix":
                # Re-enable the auto-fix button
                self.auto_fix_route_button.setEnabled(True)
                self.auto_fix_route_button.setText("Auto-Fix Route")
                # Reset route info label
                self.update_route_info()
            elif operation_type == "suggest_via":
                # Re-enable the suggest button
                self.suggest_route_button.setEnabled(True)
                self.suggest_route_button.setText("Suggest Route")
                # Reset route info label
                self.update_route_info()
            elif operation_type == "fastest_route":
                # Re-enable the fastest route button
                self.fastest_route_button.setEnabled(True)
                self.fastest_route_button.setText("Fastest Route")
                # Reset route info label
                self.update_route_info()
        except Exception as e:
            print(f"Error hiding progress indicators: {e}")
    
    def _update_progress_indicator(self, operation_info: dict, percentage: int, message: str):
        """Update progress indicator with percentage and message."""
        try:
            operation_type = operation_info.get('type', '')
            if operation_type == "auto_fix":
                self.route_info_label.setText(f"🔧 {message} ({percentage}%)")
            elif operation_type == "suggest_via":
                self.route_info_label.setText(f"🔍 {message} ({percentage}%)")
            elif operation_type == "fastest_route":
                self.route_info_label.setText(f"⚡ {message} ({percentage}%)")
        except Exception as e:
            print(f"Error updating progress indicator: {e}")
    
    def _handle_search_completed(self, operation_info: dict, result: dict):
        """Handle completed search operations."""
        try:
            stations = result.get('stations', [])
            query = operation_info.get('query', '')
            
            # Update the appropriate completer based on the search type
            if 'from' in operation_info.get('type', ''):
                model = QStringListModel(stations)
                self.from_name_completer.setModel(model)
            else:
                model = QStringListModel(stations)
                self.to_name_completer.setModel(model)
                
        except Exception as e:
            print(f"Error handling search completion: {e}")
    
    def _handle_auto_fix_completed(self, operation_info: dict, result: dict):
        """Handle completed auto-fix operations."""
        try:
            # Hide progress indicators first
            self._hide_progress_indicators(operation_info)
            
            success = result.get('success', False)
            message = result.get('message', '')
            route = result.get('route', [])  # This is actually the via stations from auto-fix
            
            print(f"Auto-fix completed: success={success}, route={route}, message={message}")
            
            if success:
                # The route from auto-fix is actually the via stations (train changes)
                # No need to extract - use directly
                self.via_stations.clear()
                if route:  # If there are via stations
                    self.via_stations.extend(route)
                
                # Mark route as auto-fixed
                self.route_auto_fixed = True
                
                # Update UI
                self.update_via_buttons()
                self.update_route_info()
                
                # Show success message
                if route:  # If there are via stations
                    # Build full route for display
                    from_station = operation_info.get('from_station', '')
                    to_station = operation_info.get('to_station', '')
                    full_route = [from_station] + route + [to_station]
                    
                    QMessageBox.information(
                        self,
                        "Route Fixed",
                        f"Route has been automatically fixed with {len(route)} train changes:\n"
                        f"{' → '.join(full_route)}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Route Fixed",
                        "Route has been fixed - direct connection is optimal."
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Cannot Fix Route",
                    message or "Unable to find a valid route between the selected stations."
                )
                
        except Exception as e:
            print(f"Error handling auto-fix completion: {e}")
            # Ensure progress indicators are hidden even on error
            self._hide_progress_indicators(operation_info)
            QMessageBox.critical(self, "Error", f"Failed to process auto-fix result: {e}")
    
    def _handle_via_suggestions_completed(self, operation_info: dict, result: dict):
        """Handle completed via suggestion operations."""
        try:
            suggestions = result.get('suggestions', [])
            from_station = operation_info.get('from_station', '')
            to_station = operation_info.get('to_station', '')
            
            if suggestions:
                self.show_route_suggestion_dialog(from_station, to_station, suggestions)
            else:
                QMessageBox.information(
                    self,
                    "No Route Found",
                    f"No intermediate stations found for route from {from_station} to {to_station}."
                )
                
        except Exception as e:
            print(f"Error handling via suggestions completion: {e}")
    
    def _handle_fastest_route_completed(self, operation_info: dict, result: dict):
        """Handle completed fastest route operations."""
        try:
            success = result.get('success', False)
            route = result.get('route', [])
            message = result.get('message', '')
            
            if success and route:
                # Extract via stations from the route (exclude first and last)
                via_stations = []
                if len(route) > 2:
                    via_stations = route[1:-1]
                    self.via_stations.clear()
                    self.via_stations.extend(via_stations)
                else:
                    self.via_stations.clear()
                
                # Mark route as auto-fixed
                self.route_auto_fixed = True
                
                # Update UI
                self.update_via_buttons()
                self.update_route_info()
                
                # Show result message
                if via_stations:
                    QMessageBox.information(
                        self,
                        "Fastest Route Found",
                        f"Optimal route with {len(via_stations)} train change(s):\n{' → '.join(route)}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Direct Route",
                        f"Direct route is optimal:\n{' → '.join(route)}"
                    )
            else:
                QMessageBox.information(
                    self,
                    "No Route Found",
                    message or "No optimal route could be found between the selected stations."
                )
                
        except Exception as e:
            print(f"Error handling fastest route completion: {e}")

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle(__train_settings_title__)
        self.setModal(True)
        self.setMinimumSize(800, 650)  # Increased minimum height
        self.resize(850, 680)  # Increased default height

        # Center the dialog on screen
        from PySide6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - 850) // 2
        y = (screen.height() - 680) // 2  # Updated for new height
        self.move(x, y)

        # Main layout
        layout = QVBoxLayout(self)

        # Tab widget for different setting categories
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Setup tabs
        self.setup_stations_tab()
        self.setup_display_tab()

        # Button layout
        button_layout = QHBoxLayout()

        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_to_defaults)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setDefault(True)

        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

    def setup_stations_tab(self):
        """Setup station configuration tab."""
        stations_widget = QWidget()
        layout = QVBoxLayout(stations_widget)

        stations_group = QGroupBox("Station Configuration")
        form = QFormLayout(stations_group)

        # From station section
        from_label = QLabel("From Station:")
        from_label.setStyleSheet("font-weight: bold; color: #1976d2;")
        form.addRow(from_label)

        # From station name with API-based autocomplete
        self.from_name_edit = QLineEdit()
        self.from_name_edit.setPlaceholderText("Start typing station name for API lookup...")
        
        # Setup API-based autocomplete for from station
        self.from_name_completer = QCompleter([])
        self.from_name_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.from_name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.from_name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.from_name_completer.setMaxVisibleItems(10)
        self.from_name_edit.setCompleter(self.from_name_completer)
        
        # Setup debounce timer for API calls
        self.from_name_timer = QTimer()
        self.from_name_timer.setSingleShot(True)
        self.from_name_timer.timeout.connect(self.lookup_from_stations)
        
        form.addRow("From Station:", self.from_name_edit)

        # Add some spacing
        form.addRow(QLabel(""))

        # To station section
        to_label = QLabel("To Station:")
        to_label.setStyleSheet("font-weight: bold; color: #1976d2;")
        form.addRow(to_label)

        # To station name - simple line edit with autocomplete (no dropdown)
        self.to_name_edit = QLineEdit()
        self.to_name_edit.setEnabled(False)  # Disabled until from station is selected
        self.to_name_edit.setMaximumWidth(400)
        self.to_name_edit.setPlaceholderText("Select a From station first...")
        
        # Setup autocomplete for to station
        self.to_name_completer = QCompleter([])
        self.to_name_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.to_name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.to_name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.to_name_completer.setMaxVisibleItems(10)
        self.to_name_edit.setCompleter(self.to_name_completer)
        
        # Setup debounce timer for filtering
        self.to_name_timer = QTimer()
        self.to_name_timer.setSingleShot(True)
        self.to_name_timer.timeout.connect(self.filter_to_stations_text)
        
        form.addRow("To Station:", self.to_name_edit)

        # Add some spacing
        form.addRow(QLabel(""))

        # Via stations section
        via_label = QLabel("Via Stations (Optional):")
        via_label.setStyleSheet("font-weight: bold; color: #1976d2;")
        form.addRow(via_label)

        # Initialize via stations data structure
        self.via_stations = []  # Simple list to store via station names
        self.route_auto_fixed = False  # Track if route has been auto-fixed
        
        # Via stations buttons display (shows current via stations as clickable buttons)
        # Using absolute positioning for exact 2px spacing control
        self.via_buttons_widget = QWidget()
        self.via_buttons_widget.setStyleSheet("QWidget { border: none; background: transparent; }")  # Remove any borders
        # No layout needed - using absolute positioning
        self.via_buttons_widget.setMinimumHeight(66)  # Height for exactly 3 rows: 3 * (20px + 2px) = 66px
        self.via_buttons_widget.setMaximumHeight(66)  # Prevent excessive expansion
        # Don't add to form - add directly to avoid form spacing
        
        # Via stations functionality
        via_layout = QVBoxLayout()
        
        # Via station controls (positioned below the buttons)
        via_controls_layout = QHBoxLayout()
        via_controls_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)  # Bottom align for height matching
        via_controls_layout.setContentsMargins(0, 0, 0, 0)  # Remove layout margins
        via_controls_layout.setSpacing(5)  # Set consistent spacing between controls
        
        # Add via station combo
        self.add_via_combo = QComboBox()
        self.add_via_combo.setEditable(True)
        self.add_via_combo.setEnabled(False)  # Disabled until route is set
        # Match combobox height and alignment exactly to buttons
        self.add_via_combo.setFixedHeight(32)  # Match button height exactly
        self.add_via_combo.setFixedWidth(240)  # Set specific width to align with From Route button
        self.add_via_combo.setContentsMargins(0, 0, 0, 0)  # Remove any margins
        self.add_via_combo.setStyleSheet("""
            QComboBox {
                height: 32px;
                min-height: 32px;
                max-height: 32px;
                padding: 0px;
                margin: 0px;
                border: 1px solid #404040;
                border-radius: 4px;
                font-size: 12px;
                text-align: left;
                padding-left: 8px;
            }
            QComboBox::drop-down {
                width: 20px;
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #404040;
                background-color: #2b2b2b;
            }
        """)
        self.add_via_combo.setMaxVisibleItems(10)  # Allow dropdown to show up to 10 items
        self.add_via_combo.setPlaceholderText("Select stations first...")
        via_controls_layout.addWidget(self.add_via_combo)
        
        # Add via station button
        self.add_via_button = QPushButton("Add Via")
        self.add_via_button.setEnabled(False)
        self.add_via_button.setFixedHeight(32)  # Match combobox height exactly
        self.add_via_button.clicked.connect(self.add_via_station)
        via_controls_layout.addWidget(self.add_via_button)
        
        # Suggest route button (moved left to replace Remove button)
        self.suggest_route_button = QPushButton("Suggest Route")
        self.suggest_route_button.setEnabled(False)
        self.suggest_route_button.setFixedHeight(32)  # Match combobox height exactly
        self.suggest_route_button.clicked.connect(self.suggest_route)
        via_controls_layout.addWidget(self.suggest_route_button)
        
        # Fastest route button (moved left)
        self.fastest_route_button = QPushButton("Fastest Route")
        self.fastest_route_button.setEnabled(False)
        self.fastest_route_button.setFixedHeight(32)  # Match combobox height exactly
        self.fastest_route_button.clicked.connect(self.find_fastest_route)
        via_controls_layout.addWidget(self.fastest_route_button)
        
        via_layout.addLayout(via_controls_layout)
        
        # Add spacing between Section C and Section D
        via_layout.addSpacing(10)
        
        # Additional routing controls
        additional_controls_layout = QHBoxLayout()
        
        # Auto-Fix Route button (moved to first position, replacing From Route button)
        self.auto_fix_route_button = QPushButton("Auto-Fix Route")
        self.auto_fix_route_button.setEnabled(False)
        self.auto_fix_route_button.setMinimumHeight(32)  # Proper button height
        self.auto_fix_route_button.clicked.connect(self.auto_fix_route_from_button)
        # Style with orange/amber color to distinguish from other buttons
        self.auto_fix_route_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                border: 1px solid #f57c00;
                border-radius: 4px;
                padding: 6px 12px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
                border-color: #e65100;
            }
            QPushButton:pressed {
                background-color: #e65100;
            }
            QPushButton:disabled {
                background-color: #424242;
                border-color: #616161;
                color: #9e9e9e;
            }
        """)
        additional_controls_layout.addWidget(self.auto_fix_route_button)
        
        additional_controls_layout.addStretch()
        via_layout.addLayout(additional_controls_layout)
        
        # Add spacing before route info text
        via_layout.addSpacing(8)
        
        # Route info label with word wrapping and proper spacing
        self.route_info_label = QLabel("Select From and To stations to enable routing")
        self.route_info_label.setStyleSheet("color: #888888; font-style: italic; padding: 5px;")
        self.route_info_label.setWordWrap(True)  # Enable word wrapping
        self.route_info_label.setMinimumHeight(40)  # Ensure minimum height for wrapped text
        self.route_info_label.setMaximumHeight(80)  # Allow for up to 3-4 lines of text
        self.route_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)  # Left-align and top-align
        via_layout.addWidget(self.route_info_label)
        
        # Add extra spacing after route info to lower the UI elements below
        via_layout.addSpacing(15)
        
        form.addRow("", via_layout)

        # Connect signals for synchronization
        self.from_name_edit.textChanged.connect(self.on_from_name_changed)
        self.from_name_completer.activated.connect(self.on_from_name_completed)
        
        # Connect to station signals
        self.to_name_edit.textChanged.connect(self.on_to_name_changed)
        self.to_name_completer.activated.connect(self.on_to_name_completed)

        # Add via buttons widget directly to form layout after the via stations label
        form.addRow("", self.via_buttons_widget)
        
        layout.addWidget(stations_group)

        self.tab_widget.addTab(stations_widget, "Stations")

    def setup_display_tab(self):
        """Setup display configuration tab."""
        display_widget = QWidget()
        layout = QVBoxLayout(display_widget)

        display_group = QGroupBox("Display Settings")
        form = QFormLayout(display_group)

        # Max trains
        self.max_trains_spin = HorizontalSpinWidget(
            10, 100, 50, 1, theme_manager=self.theme_manager
        )
        form.addRow("Max Trains:", self.max_trains_spin)

        # Time window
        self.time_window_spin = HorizontalSpinWidget(
            1, 24, 16, 1, " hours", theme_manager=self.theme_manager
        )
        form.addRow("Time Window:", self.time_window_spin)

        layout.addWidget(display_group)

        self.tab_widget.addTab(display_widget, "Display")


    def api_search_stations(self, query: str, limit: int = 10):
        """Search for stations using the internal database with disambiguation."""
        try:
            # Use internal database for station search with line context for duplicates
            stations = station_database.search_stations(query, limit)
            print(f"Found {len(stations)} stations matching '{query}' in internal database")
            return stations
            
        except Exception as e:
            print(f"Error in database station search: {e}")
            return []

    def api_get_station_code(self, station_name: str):
        """Get station code for a station name using the internal database."""
        try:
            # Parse the station name to remove line context if present
            parsed_name = station_database.parse_station_name(station_name.strip())
            
            # Use internal database for station code lookup
            code = station_database.get_station_code(parsed_name)
            if code:
                print(f"Found station code '{code}' for '{parsed_name}' (from '{station_name}') in internal database")
                return code
            
            return None
            
        except Exception as e:
            print(f"Error in database station code lookup: {e}")
            return None

    def on_from_name_changed(self, text: str):
        """Handle from station name text change with async lookup."""
        if not text.strip():
            # Clear to station when from station is cleared
            self.clear_to_station()
            return
        
        # Cancel any pending search
        self._cancel_pending_operation("from_search")
        
        # Start debounce timer for async lookup
        self.from_name_timer.stop()
        self.from_name_timer.start(300)  # Reduced debounce for better responsiveness

    def on_from_name_completed(self, text: str):
        """Handle from station name autocomplete selection."""
        try:
            self.set_from_station_by_name(text)
        except Exception as e:
            print(f"Error in on_from_name_completed: {e}")

    def on_to_name_changed(self, text: str):
        """Handle to station name text change with filtering."""
        try:
            if not self.to_name_edit.isEnabled():
                return
            
            # If text is empty, reset completer
            if not text.strip():
                self.update_via_stations_availability()
                return
            
            # Update completer prefix for immediate filtering
            if len(text) >= 1:
                self.to_name_completer.setCompletionPrefix(text)
                # Force completer to show popup if there are matches
                if self.to_name_completer.completionCount() > 0:
                    self.to_name_completer.complete()
            
            # Start debounce timer for additional filtering
            self.to_name_timer.stop()
            self.to_name_timer.start(300)  # Debounce for better performance
            
            # Update via stations availability
            self.update_via_stations_availability()
            
        except Exception as e:
            print(f"Error in on_to_name_changed: {e}")

    def on_to_name_completed(self, text):
        """Handle to station name autocomplete selection."""
        try:
            # Called from completer activated signal (text)
            self.set_to_station_by_name(text)
            
        except Exception as e:
            print(f"Error in on_to_name_completed: {e}")

    def lookup_from_stations(self):
        """Perform API lookup for from stations."""
        query = self.from_name_edit.text().strip()
        if not query or len(query) < 2:
            return
        
        try:
            # Make API call to search for stations
            matches = self.api_search_stations(query)
            
            # Update completer
            model = QStringListModel(matches)
            self.from_name_completer.setModel(model)
        except Exception as e:
            print(f"Error in lookup_from_stations: {e}")

    def filter_from_stations(self, query: str):
        """Filter and update from station completer (case insensitive)."""
        try:
            if not query or len(query) < 1:
                return
            
            # Make API call to search for stations
            matches = self.api_search_stations(query, limit=15)
            
            # Update completer immediately
            model = QStringListModel(matches)
            self.from_name_completer.setModel(model)
        except Exception as e:
            print(f"Error in filter_from_stations: {e}")

    def filter_to_stations_text(self):
        """Filter to stations based on current text - now handled automatically by QCompleter."""
        # This method is no longer needed as QCompleter handles filtering automatically
        # with CaseInsensitive and MatchContains settings
        pass

    def set_from_station_by_name(self, name: str):
        """Set from station by name and enable to station."""
        try:
            if not name or not name.strip():
                # Clear via stations when from station is cleared
                self.clear_via_stations()
                return
                
            code = self.api_get_station_code(name.strip())
            if code:
                # Temporarily disconnect signals to prevent recursive calls
                line_edit = self.to_name_edit
                if line_edit:
                    try:
                        line_edit.textChanged.disconnect()
                    except:
                        pass  # Ignore if not connected
                
                # Enable to station field
                self.to_name_edit.setEnabled(True)
                if line_edit:
                    line_edit.setPlaceholderText("Start typing destination station...")
                
                # Clear any existing to station selection but don't disable the field
                self.to_name_edit.clear()
                
                # Pre-populate to station dropdown with reachable destinations
                self.populate_to_stations_completer(code)
                
                # Reconnect signals
                if line_edit:
                    line_edit.textChanged.connect(self.on_to_name_changed)
                
                # Update via stations availability - but safely
                try:
                    self.update_via_stations_availability()
                except Exception as via_error:
                    print(f"Error updating via stations from set_from_station: {via_error}")
            else:
                # No valid station code found - clear via stations
                self.clear_via_stations()
                    
        except Exception as e:
            print(f"Error in set_from_station_by_name: {e}")
            import traceback
            traceback.print_exc()
            # Ensure via stations are cleared on error
            try:
                self.clear_via_stations()
            except:
                pass

    def set_to_station_by_name(self, name: str):
        """Set to station by name."""
        try:
            if not name or not name.strip():
                return
                
            # Temporarily disconnect signals to prevent recursive calls
            try:
                self.to_name_edit.textChanged.disconnect(self.on_to_name_changed)
                self.to_name_edit.setText(name.strip())
                self.to_name_edit.textChanged.connect(self.on_to_name_changed)
            except (TypeError, RuntimeError):
                # Handle case where signal is not connected
                self.to_name_edit.setText(name.strip())
                self.to_name_edit.textChanged.connect(self.on_to_name_changed)
            
            # Update via stations availability
            try:
                self.update_via_stations_availability()
            except Exception as via_error:
                print(f"Error updating via stations: {via_error}")
                    
        except Exception as e:
            print(f"Error in set_to_station_by_name: {e}")

    def populate_to_stations_completer(self, from_station_code: str):
        """Populate to station completer with all available stations."""
        signals_disconnected = False
        try:
            # Temporarily disconnect signals to prevent crashes during population
            try:
                self.to_name_edit.textChanged.disconnect(self.on_to_name_changed)
                signals_disconnected = True
            except (TypeError, RuntimeError):
                signals_disconnected = False
            
            # Set loading state
            self.to_name_edit.setPlaceholderText("Loading destinations...")
            
            # Clear existing text
            self.to_name_edit.clear()
            
            # Get all stations with disambiguation context
            all_stations = station_database.get_all_stations_with_context()
            
            if all_stations:
                # Sort stations alphabetically for better UX
                all_stations.sort()
                
                # Update completer with all stations
                model = QStringListModel(all_stations)
                self.to_name_completer.setModel(model)
                
                # Configure completer for better performance
                self.to_name_completer.setCompletionPrefix("")
                self.to_name_completer.setCurrentRow(0)
                
                # Set success placeholder text
                self.to_name_edit.setPlaceholderText(f"Type to search {len(all_stations)} stations...")
                
                print(f"Loaded {len(all_stations)} stations with disambiguation from database")
            else:
                # No stations found - set error message
                print(f"No stations found in database")
                self.to_name_edit.setPlaceholderText("No stations available")
                return
            
        except Exception as e:
            print(f"Error in populate_to_stations_completer: {e}")
            self.to_name_edit.setPlaceholderText("Error loading stations")
            
        finally:
            # Always reconnect signals if we disconnected them
            try:
                if signals_disconnected:
                    self.to_name_edit.textChanged.connect(self.on_to_name_changed)
            except:
                pass  # Ignore if reconnection fails

    def clear_to_station(self):
        """Clear to station selection and disable field."""
        self.to_name_edit.clear()
        self.to_name_edit.setEnabled(False)
        line_edit = self.to_name_edit
        if line_edit:
            line_edit.setPlaceholderText("Select a From station first...")
        
        # Also clear via stations
        self.clear_via_stations()
    
    def add_via_station(self):
        """Add a via station to the route and automatically optimize."""
        try:
            via_station = self.add_via_combo.currentText().strip()
            if not via_station:
                return
            
            # Check if station is already in the list
            if via_station in self.via_stations:
                QMessageBox.information(self, "Duplicate Station", f"'{via_station}' is already in the via stations list.")
                return
            
            # Get current from and to stations
            from_station = self.from_name_edit.text().strip()
            to_station = self.to_name_edit.text().strip()
            
            if not from_station or not to_station:
                QMessageBox.warning(self, "Missing Stations", "Please select both From and To stations first.")
                return
            
            # Add the via station to the list
            self.via_stations.append(via_station)
            
            # Reset auto-fixed flag since user manually added a station
            self.route_auto_fixed = False
            
            # Clear the combo box
            self.add_via_combo.setCurrentText("")
            
            # Automatically find the fastest route that includes the new via station
            # This preserves the user's choice while optimizing the overall route
            self.auto_optimize_route_with_via_stations(from_station, to_station)
            
        except Exception as e:
            print(f"Error adding via station: {e}")
    
    def remove_via_station(self):
        """Remove selected via station from the route."""
        try:
            # This method is now handled by button clicks in remove_via_station_by_name
            # Keep for backward compatibility but make it a no-op
            pass
        except Exception as e:
            print(f"Error removing via station: {e}")
    
    def suggest_route(self):
        """Suggest a route between from and to stations - synchronous fallback."""
        try:
            from_station = self.from_name_edit.text().strip()
            to_station = self.to_name_edit.text().strip()
            
            if not from_station or not to_station:
                QMessageBox.information(self, "Missing Stations", "Please select both From and To stations first.")
                return
            
            # Show progress indicator
            self.suggest_route_button.setEnabled(False)
            self.suggest_route_button.setText("Suggesting...")
            self.route_info_label.setText("🔍 Finding route suggestions...")
            self.route_info_label.setStyleSheet("color: #1976d2; font-style: italic; font-weight: bold;")
            
            # Force UI update
            QApplication.processEvents()
            
            # Parse station names
            from_parsed = station_database.parse_station_name(from_station)
            to_parsed = station_database.parse_station_name(to_station)
            
            # Get via station suggestions
            via_stations = station_database.suggest_via_stations(from_parsed, to_parsed)
            
            # Re-enable button
            self.suggest_route_button.setEnabled(True)
            self.suggest_route_button.setText("Suggest Route")
            self.update_route_info()
            
            if via_stations:
                self.show_route_suggestion_dialog(from_station, to_station, via_stations)
            else:
                QMessageBox.information(
                    self,
                    "No Route Found",
                    f"No intermediate stations found for route from {from_station} to {to_station}."
                )
                
        except Exception as e:
            print(f"Error suggesting route: {e}")
            # Ensure button is re-enabled
            self.suggest_route_button.setEnabled(True)
            self.suggest_route_button.setText("Suggest Route")
            self.update_route_info()
            QMessageBox.critical(self, "Error", f"Failed to suggest route: {e}")
    
    def show_route_suggestion_dialog(self, from_station: str, to_station: str, suggested_via: list):
        """Show dialog with route suggestions."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Route Suggestions")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Info label
        info_label = QLabel(f"Suggested via stations for: {from_station} → {to_station}")
        info_label.setStyleSheet("font-weight: bold; color: #1976d2;")
        layout.addWidget(info_label)
        
        # Suggestions list
        suggestions_list = QListWidget()
        suggestions_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for station in suggested_via[:10]:  # Limit to 10 suggestions
            suggestions_list.addItem(station)
        layout.addWidget(suggestions_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(suggestions_list.selectAll)
        button_layout.addWidget(select_all_button)
        
        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(suggestions_list.clearSelection)
        button_layout.addWidget(clear_button)
        
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("Add Selected")
        ok_button.clicked.connect(dialog.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        # Show dialog and process result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = suggestions_list.selectedItems()
            selected_stations = [item.text() for item in selected_items]
            
            if selected_stations:
                # Add selected stations to existing via stations (don't clear existing ones)
                for station in selected_stations:
                    if station not in self.via_stations:  # Avoid duplicates
                        self.via_stations.append(station)
                
                # Reset auto-fixed flag since user manually added stations
                self.route_auto_fixed = False
            
            # Update UI to show all via stations (existing + newly selected)
            self.update_via_buttons()
            self.update_route_info()
            self.update_via_stations_availability()
    
    def clear_via_stations(self):
        """Clear all via stations and disable controls."""
        try:
            # Clear via stations list
            self.via_stations.clear()
            
            # Reset auto-fixed flag when clearing via stations
            self.route_auto_fixed = False
            
            self.update_via_buttons()
            
            # Clear and disable via combo
            self.add_via_combo.clear()
            self.add_via_combo.setEnabled(False)
            
            # Disable all via station buttons
            self.add_via_button.setEnabled(False)
            self.suggest_route_button.setEnabled(False)
            
            # Update placeholder text
            via_line_edit = self.add_via_combo.lineEdit()
            if via_line_edit:
                via_line_edit.setPlaceholderText("Select From and To stations first...")
            
            # Update route info and display text
            self.route_info_label.setText("Select From and To stations to enable routing")
            
        except Exception as e:
            print(f"Error clearing via stations: {e}")
    
    def update_route_info(self):
        """Update the route information display."""
        try:
            from_station = self.from_name_edit.text().strip()
            line_edit = self.to_name_edit
            to_station = line_edit.text().strip() if line_edit else ""
            
            if not from_station or not to_station:
                self.route_info_label.setText("Select From and To stations to enable routing")
                return
            
            # Build route description
            route_parts = [from_station]
            
            # Add via stations
            for via_station in self.via_stations:
                try:
                    route_parts.append(via_station)
                except Exception as via_error:
                    print(f"Error getting via station: {via_error}")
            
            route_parts.append(to_station)
            
            # Create route description
            if len(route_parts) == 2:
                route_text = f"Direct: {route_parts[0]} → {route_parts[1]}"
            else:
                route_text = f"Route: {' → '.join(route_parts)}"
            
            # Add visual indicator if route was auto-fixed (regardless of via stations count)
            if self.route_auto_fixed:
                route_text += " 🔧 (Auto-Fixed)"
                # Update label style to show auto-fixed state with word wrapping
                self.route_info_label.setStyleSheet("""
                    color: #ff9800;
                    font-style: italic;
                    font-weight: bold;
                    padding: 5px;
                    background-color: rgba(255, 152, 0, 0.1);
                    border-radius: 4px;
                """)
            else:
                # Reset to normal style with word wrapping
                self.route_info_label.setStyleSheet("""
                    color: #888888;
                    font-style: italic;
                    padding: 5px;
                """)
            
            self.route_info_label.setText(route_text)
            
        except Exception as e:
            print(f"Error updating route info: {e}")
            try:
                self.route_info_label.setText("Error updating route information")
            except Exception as label_error:
                print(f"Error setting error text: {label_error}")
    
    def update_via_buttons(self):
        """Update the via stations buttons display with dynamic sizing and line wrapping."""
        try:
            # Clear existing widgets by setting them as children of None
            for child in self.via_buttons_widget.findChildren(QPushButton):
                child.setParent(None)
            
            # Only show buttons for stations that are actually in self.via_stations
            if self.via_stations:
                # Dynamic button sizing parameters
                min_button_width = 120  # Minimum button width
                max_button_width = 300  # Maximum button width to prevent excessive stretching
                button_height = 20      # Fixed button height
                horizontal_spacing = 2  # Horizontal spacing between buttons
                vertical_spacing = 2    # Vertical spacing between rows
                max_row_width = 650     # Maximum width available for buttons per row
                
                # Calculate button widths based on text content
                button_data = []
                for station in self.via_stations:
                    # Estimate text width (rough approximation: 8 pixels per character)
                    estimated_text_width = len(station) * 8 + 20  # +20 for padding
                    button_width = max(min_button_width, min(estimated_text_width, max_button_width))
                    button_data.append({'station': station, 'width': button_width})
                
                # Arrange buttons with line wrapping
                current_row = 0
                current_x = 0
                
                for i, data in enumerate(button_data):
                    station = data['station']
                    button_width = data['width']
                    
                    # Check if button fits on current row
                    if current_x + button_width > max_row_width and current_x > 0:
                        # Move to next row
                        current_row += 1
                        current_x = 0
                    
                    # Calculate position
                    x = current_x
                    y = current_row * (button_height + vertical_spacing)
                    
                    # Create button with dynamic width
                    button = QPushButton(station, self.via_buttons_widget)
                    button.setGeometry(x, y, button_width, button_height)
                    
                    # Style as selected/active via station
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #2e7d32;
                            border: 1px solid #1b5e20;
                            border-radius: 4px;
                            padding: 2px 4px;
                            margin: 0px;
                            color: white;
                            font-weight: bold;
                            font-size: 10px;
                            text-align: center;
                        }
                        QPushButton:hover {
                            background-color: #d32f2f;
                        }
                        QPushButton:pressed {
                            background-color: #c62828;
                        }
                    """)
                    button.setToolTip(f"Click to remove {station} from route")
                    
                    # Connect to remove function
                    button.clicked.connect(lambda checked, station=station: self.remove_via_station_by_name(station))
                    button.show()
                    
                    # Update position for next button
                    current_x += button_width + horizontal_spacing
                
                # Update widget height to accommodate all rows
                total_height = (current_row + 1) * (button_height + vertical_spacing)
                self.via_buttons_widget.setMinimumHeight(total_height)
                self.via_buttons_widget.setMaximumHeight(total_height)
                
        except Exception as e:
            print(f"Error updating via buttons: {e}")
    
    def _clear_layout(self, layout):
        """Helper method to recursively clear a layout."""
        try:
            if layout is None:
                return
            for i in reversed(range(layout.count())):
                child = layout.itemAt(i)
                if child:
                    if child.widget():
                        child.widget().setParent(None)
                    elif child.layout():
                        self._clear_layout(child.layout())
        except Exception as e:
            print(f"Error clearing layout: {e}")
    
    def add_via_station_from_button(self, station_name: str):
        """Add a via station when its button is clicked."""
        try:
            # Check if station is already in the list
            if station_name in self.via_stations:
                return  # Already added, do nothing
            
            # Add to via stations list
            self.via_stations.append(station_name)
            
            # Update the buttons display to show new selection state
            self.update_via_buttons()
            
            # Update the route info to show full route
            self.update_route_info()
            
        except Exception as e:
            print(f"Error adding via station from button: {e}")
    
    def validate_route(self, from_station: str, via_stations: list, to_station: str):
        """
        Validate if the route forms a valid geographical path.
        Uses different validation rules for user-created vs auto-fixed routes.
        
        Args:
            from_station: Origin station name
            via_stations: List of via station names
            to_station: Destination station name
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            if not via_stations:
                return True, ""  # Direct routes are always valid
            
            # Build complete route
            complete_route = [from_station] + via_stations + [to_station]
            
            # Apply different validation rules based on whether route was auto-fixed
            if self.route_auto_fixed:
                # Lenient validation for auto-fixed routes
                return self._validate_auto_fixed_route(complete_route)
            else:
                # Strict validation for user-created routes
                return self._validate_user_created_route(complete_route)
            
        except Exception as e:
            print(f"Error validating route: {e}")
            return False, f"Error validating route: {e}"
    
    def _validate_user_created_route(self, complete_route: list):
        """Strict validation for user-created routes."""
        # Check each segment for direct operator connections and reasonable distances
        for i in range(len(complete_route) - 1):
            current_station = complete_route[i]
            next_station = complete_route[i + 1]
            
            # Get station objects for distance calculation (parse names to remove disambiguation)
            current_station_parsed = station_database.parse_station_name(current_station)
            next_station_parsed = station_database.parse_station_name(next_station)
            current_station_obj = station_database.get_station_by_name(current_station_parsed)
            next_station_obj = station_database.get_station_by_name(next_station_parsed)
            
            if not current_station_obj or not next_station_obj:
                return False, f"Could not find station data for {current_station} or {next_station}."
            
            # Calculate distance between stations
            distance = station_database.calculate_haversine_distance(
                current_station_obj.coordinates,
                next_station_obj.coordinates
            )
            
            # Strict validation: 50km limit for user-created routes
            if distance > 50:
                # Check if there's a direct operator connection
                operator = station_database.get_operator_for_segment(current_station_parsed, next_station_parsed)
                
                if not operator:
                    # No direct operator and too far apart
                    return False, f"Stations {current_station} and {next_station} are {distance:.1f}km apart with no direct railway connection. Use 'Auto-Fix Route' to add intermediate stations."
                else:
                    # Has direct operator but still quite far - check if it's a reasonable main line connection
                    if distance > 150:  # Even with direct operator, 150km+ is suspicious for via stations
                        return False, f"Stations {current_station} and {next_station} are {distance:.1f}km apart. While there is a direct railway connection, this distance suggests missing intermediate stations. Use 'Auto-Fix Route' to optimize the route."
            
            # For short distances, verify there's some kind of railway connection
            if distance <= 50:
                operator = station_database.get_operator_for_segment(current_station_parsed, next_station_parsed)
                if not operator:
                    # Try to find any route with reasonable number of changes
                    routes = station_database.find_route_between_stations(current_station_parsed, next_station_parsed, max_changes=2)
                    if not routes:
                        return False, f"No railway connection found between {current_station} and {next_station}, even though they are only {distance:.1f}km apart."
                    
                    # Check if the route is too complex
                    shortest_route = min(routes, key=len)
                    if len(shortest_route) > 5:  # More than 5 stations total suggests complexity
                        return False, f"Route between {current_station} and {next_station} requires {len(shortest_route)} stations total, which is too complex for a via connection. Use 'Auto-Fix Route' to optimize."
        
        return True, ""
    
    def _validate_auto_fixed_route(self, complete_route: list):
        """Lenient validation for auto-fixed routes - just check basic connectivity."""
        # For auto-fixed routes, we trust the auto-fix algorithm and just do basic checks
        for i in range(len(complete_route) - 1):
            current_station = complete_route[i]
            next_station = complete_route[i + 1]
            
            # Get station objects (parse names to remove disambiguation)
            current_station_parsed = station_database.parse_station_name(current_station)
            next_station_parsed = station_database.parse_station_name(next_station)
            current_station_obj = station_database.get_station_by_name(current_station_parsed)
            next_station_obj = station_database.get_station_by_name(next_station_parsed)
            
            if not current_station_obj or not next_station_obj:
                return False, f"Could not find station data for {current_station} or {next_station}."
            
            # Calculate distance
            distance = station_database.calculate_haversine_distance(
                current_station_obj.coordinates,
                next_station_obj.coordinates
            )
            
            # Very lenient check - only reject if distance is extremely unreasonable (>500km)
            if distance > 500:
                return False, f"Stations {current_station} and {next_station} are {distance:.1f}km apart, which seems unreasonable even for an auto-fixed route."
            
            # Check for basic railway connectivity (allow up to 3 changes for auto-fixed routes)
            operator = station_database.get_operator_for_segment(current_station_parsed, next_station_parsed)
            if not operator:
                routes = station_database.find_route_between_stations(current_station_parsed, next_station_parsed, max_changes=3)
                if not routes:
                    return False, f"No railway connection found between {current_station} and {next_station} in auto-fixed route."
        
        return True, ""

    def remove_via_station_by_name(self, station_name: str):
        """Remove a via station by name - optimized for fast UI response."""
        try:
            if station_name not in self.via_stations:
                return
            
            # For auto-fixed routes, allow immediate removal without validation
            # since auto-fixed routes are already optimized
            if self.route_auto_fixed:
                # Remove the station immediately
                self.via_stations.remove(station_name)
                
                # Reset auto-fixed flag only when ALL via stations are removed
                if len(self.via_stations) == 0:
                    self.route_auto_fixed = False
                
                # Update UI immediately for fast response
                self.update_via_buttons()
                self.update_route_info()
                self.update_via_stations_availability()
                return
            
            # For user-created routes, do minimal validation
            from_station = self.from_name_edit.text().strip()
            to_station = self.to_name_edit.text().strip()
            temp_via_stations = [s for s in self.via_stations if s != station_name]
            
            # Only validate if we have multiple via stations remaining
            # Single via station or direct routes are usually fine
            if from_station and to_station and len(temp_via_stations) > 1:
                # Quick distance-based validation only (skip complex route validation)
                try:
                    # Check if remaining route segments are reasonable (< 100km each)
                    route_segments = [from_station] + temp_via_stations + [to_station]
                    for i in range(len(route_segments) - 1):
                        current = station_database.parse_station_name(route_segments[i])
                        next_station = station_database.parse_station_name(route_segments[i + 1])
                        
                        current_obj = station_database.get_station_by_name(current)
                        next_obj = station_database.get_station_by_name(next_station)
                        
                        if current_obj and next_obj:
                            distance = station_database.calculate_haversine_distance(
                                current_obj.coordinates, next_obj.coordinates
                            )
                            
                            # If any segment is > 100km, show quick warning
                            if distance > 100:
                                reply = QMessageBox.question(
                                    self,
                                    "Remove Station?",
                                    f"Removing '{station_name}' will create a {distance:.0f}km gap. Remove anyway?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No
                                )
                                if reply == QMessageBox.StandardButton.No:
                                    return
                                break  # Only check first problematic segment
                except Exception:
                    # If validation fails, just allow removal
                    pass
            
            # Remove the station
            self.via_stations.remove(station_name)
            
            # Reset auto-fixed flag only when ALL via stations are removed
            if len(self.via_stations) == 0:
                self.route_auto_fixed = False
            
            # Update UI immediately for fast response
            self.update_via_buttons()
            self.update_route_info()
            self.update_via_stations_availability()
            
        except Exception as e:
            print(f"Error removing via station by name: {e}")

    def auto_fix_route(self, from_station: str, to_station: str):
        """Automatically fix an invalid route by finding a valid path."""
        try:
            # Find a valid route using the station database - let it determine optimal search strategy
            routes = station_database.find_route_between_stations(from_station, to_station)
            
            if routes:
                # Use the shortest valid route
                best_route = min(routes, key=len)
                
                if len(best_route) > 2:
                    # Extract via stations from the valid route
                    train_change_stations = station_database.identify_train_changes(best_route)
                    
                    self.via_stations.clear()
                    self.via_stations.extend(train_change_stations)
                    
                    # Mark route as auto-fixed
                    self.route_auto_fixed = True
                    
                    self.update_via_buttons()
                    self.update_route_info()
                    
                    QMessageBox.information(
                        self,
                        "Route Fixed",
                        f"Route has been automatically fixed with {len(train_change_stations)} train changes:\n"
                        f"{' → '.join(best_route)}"
                    )
                else:
                    # Direct route is best
                    self.via_stations.clear()
                    
                    # Mark route as auto-fixed (even though it's direct)
                    self.route_auto_fixed = True
                    
                    self.update_via_buttons()
                    self.update_route_info()
                    
                    QMessageBox.information(
                        self,
                        "Route Fixed",
                        "Route has been fixed - direct connection is optimal."
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Cannot Fix Route",
                    "Unable to find a valid route between the selected stations. "
                    "Please manually adjust your via stations."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to auto-fix route: {e}"
            )
    
    def find_fastest_route(self):
        """Find the fastest route between from and to stations - synchronous fallback."""
        try:
            from_station = self.from_name_edit.text().strip()
            to_station = self.to_name_edit.text().strip()
            
            if not from_station or not to_station:
                QMessageBox.information(self, "Missing Stations", "Please select both From and To stations first.")
                return
            
            # Show progress indicator
            self.fastest_route_button.setEnabled(False)
            self.fastest_route_button.setText("Finding...")
            self.route_info_label.setText("⚡ Finding fastest route...")
            self.route_info_label.setStyleSheet("color: #1976d2; font-style: italic; font-weight: bold;")
            
            # Force UI update
            QApplication.processEvents()
            
            # Parse station names
            from_parsed = station_database.parse_station_name(from_station)
            to_parsed = station_database.parse_station_name(to_station)
            
            # Let the database manager determine the optimal search strategy
            # Don't hard-code the number of changes - let the algorithm decide
            routes = station_database.find_route_between_stations(from_parsed, to_parsed)
            
            if routes:
                # Use the shortest route found
                best_route = min(routes, key=len)
            else:
                best_route = None
            
            if best_route:
                # Identify actual train change points
                train_change_stations = station_database.identify_train_changes(best_route)
                
                # Update via stations
                self.via_stations.clear()
                self.via_stations.extend(train_change_stations)
                
                # Mark route as auto-fixed
                self.route_auto_fixed = True
                
                # Update UI
                self.update_via_buttons()
                self.update_route_info()
                
                # Show result message
                if train_change_stations:
                    QMessageBox.information(
                        self,
                        "Fastest Route Found",
                        f"Optimal route with {len(train_change_stations)} train change(s):\n{' → '.join(best_route)}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Direct Route",
                        f"Direct route is optimal:\n{' → '.join(best_route)}"
                    )
            else:
                QMessageBox.information(
                    self,
                    "No Route Found",
                    "No optimal route could be found between the selected stations."
                )
            
            # Re-enable button
            self.fastest_route_button.setEnabled(True)
            self.fastest_route_button.setText("Fastest Route")
            self.update_route_info()
                
        except Exception as e:
            print(f"Error in find_fastest_route: {e}")
            # Ensure button is re-enabled
            self.fastest_route_button.setEnabled(True)
            self.fastest_route_button.setText("Fastest Route")
            self.update_route_info()
            QMessageBox.critical(self, "Error", f"Failed to find fastest route: {e}")
    
    def auto_fix_route_from_button(self):
        """Auto-fix route when button is clicked from main dialog - fallback to synchronous."""
        try:
            from_station = self.from_name_edit.text().strip()
            to_station = self.to_name_edit.text().strip()
            
            if not from_station or not to_station:
                QMessageBox.information(self, "Missing Stations", "Please select both From and To stations first.")
                return
            
            # Show progress indicator
            self.auto_fix_route_button.setEnabled(False)
            self.auto_fix_route_button.setText("Auto-Fixing...")
            self.route_info_label.setText("🔧 Auto-fixing route...")
            self.route_info_label.setStyleSheet("color: #ff9800; font-style: italic; font-weight: bold;")
            
            # Force UI update
            QApplication.processEvents()
            
            # Parse station names to remove disambiguation
            from_parsed = station_database.parse_station_name(from_station)
            to_parsed = station_database.parse_station_name(to_station)
            
            # Find routes using the station database - let it determine optimal search strategy
            routes = station_database.find_route_between_stations(from_parsed, to_parsed)
            
            if routes:
                # Use the best route (first one is typically best)
                best_route = routes[0]
                
                # Identify actual train change points
                train_changes = station_database.identify_train_changes(best_route)
                
                # Update via stations
                self.via_stations.clear()
                self.via_stations.extend(train_changes)
                
                # Mark route as auto-fixed
                self.route_auto_fixed = True
                
                # Update UI
                self.update_via_buttons()
                self.update_route_info()
                
                # Show success message
                if train_changes:
                    QMessageBox.information(
                        self,
                        "Route Fixed",
                        f"Route has been automatically fixed with {len(train_changes)} train changes:\n"
                        f"{' → '.join(best_route)}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Route Fixed",
                        "Route has been fixed - direct connection is optimal."
                    )
            else:
                QMessageBox.warning(
                    self,
                    "Cannot Fix Route",
                    "Unable to find a valid route between the selected stations."
                )
            
            # Re-enable button
            self.auto_fix_route_button.setEnabled(True)
            self.auto_fix_route_button.setText("Auto-Fix Route")
            self.update_route_info()
            
        except Exception as e:
            print(f"Error in auto_fix_route_from_button: {e}")
            # Ensure button is re-enabled even on error
            self.auto_fix_route_button.setEnabled(True)
            self.auto_fix_route_button.setText("Auto-Fix Route")
            self.update_route_info()
            QMessageBox.critical(self, "Error", f"Failed to auto-fix route: {e}")
    
    def auto_optimize_route_with_via_stations(self, from_station: str, to_station: str):
        """Automatically optimize route while preserving user-selected via stations."""
        try:
            # Create a route that includes all current via stations
            current_route = [from_station] + self.via_stations + [to_station]
            
            # Use train change detection to find only essential interchange stations
            train_change_stations = station_database.identify_train_changes(current_route)
            
            # Create optimized via stations list with duplicates removed
            optimized_stations = []
            seen_stations = set()
            
            # Add user-selected via stations first (preserving their choices)
            for station in self.via_stations:
                if station not in seen_stations:
                    optimized_stations.append(station)
                    seen_stations.add(station)
            
            # Add only essential train change stations that aren't already included
            for station in train_change_stations:
                if station not in seen_stations and station != from_station and station != to_station:
                    optimized_stations.append(station)
                    seen_stations.add(station)
            
            # Update via stations with the optimized, deduplicated list
            self.via_stations = optimized_stations
            
            # Update the UI
            self.update_via_buttons()
            self.update_route_info()
            
            # Force a repaint to ensure buttons are visible
            self.via_buttons_widget.update()
            self.via_buttons_widget.repaint()
            
        except Exception as e:
            print(f"Error in auto_optimize_route_with_via_stations: {e}")
            # If optimization fails, just update the UI with the current via stations
            self.update_via_buttons()
            self.update_route_info()
    
    def update_via_stations_availability(self):
        """Update via stations controls based on from/to station selection."""
        try:
            from_station = self.from_name_edit.text().strip()
            line_edit = self.to_name_edit
            to_station = line_edit.text().strip() if line_edit else ""
            
            # Check if we have both from and to stations
            has_both_stations = bool(from_station and to_station and from_station != to_station)
            
            if has_both_stations:
                # Enable via station controls
                try:
                    self.add_via_combo.setEnabled(True)
                    self.add_via_button.setEnabled(True)
                    
                    # Suggest Route should be disabled when there are any via stations displayed
                    # This prevents confusion and conflicting route modifications
                    suggest_enabled = len(self.via_stations) == 0
                    self.suggest_route_button.setEnabled(suggest_enabled)
                    
                    self.fastest_route_button.setEnabled(True)
                    self.auto_fix_route_button.setEnabled(True)
                except Exception as enable_error:
                    print(f"Error enabling controls: {enable_error}")
                
                # Update placeholder and info
                try:
                    via_line_edit = self.add_via_combo.lineEdit()
                    if via_line_edit:
                        via_line_edit.setPlaceholderText("Type or select via station...")
                except Exception as placeholder_error:
                    print(f"Error updating placeholder: {placeholder_error}")
                
                # Populate via station suggestions safely
                try:
                    # Get all UK stations with disambiguation context
                    all_stations = station_database.get_all_stations_with_context()
                    
                    # Filter out from and to stations (handle disambiguation)
                    from_parsed = station_database.parse_station_name(from_station)
                    to_parsed = station_database.parse_station_name(to_station)
                    
                    available_via = []
                    for station in all_stations:
                        station_parsed = station_database.parse_station_name(station)
                        if station_parsed != from_parsed and station_parsed != to_parsed:
                            available_via.append(station)
                    
                    self.add_via_combo.clear()
                    self.add_via_combo.addItems(available_via)  # All UK stations available
                    self.add_via_combo.setCurrentText("")
                    
                except Exception as db_error:
                    print(f"Error populating via stations: {db_error}")
                    # Fallback - just enable controls without populating
                    try:
                        self.add_via_combo.clear()
                    except Exception as clear_error:
                        print(f"Error clearing via combo: {clear_error}")
                
                try:
                    self.update_route_info()
                except Exception as route_error:
                    print(f"Error updating route info: {route_error}")
                    
            else:
                # Disable and grey out via station controls
                try:
                    self.add_via_combo.setEnabled(False)
                    self.add_via_button.setEnabled(False)
                    self.suggest_route_button.setEnabled(False)
                    self.fastest_route_button.setEnabled(False)
                    self.auto_fix_route_button.setEnabled(False)
                    
                    # Clear via stations list
                    self.via_stations.clear()
                    self.update_via_buttons()
                    self.add_via_combo.clear()
                    
                    # Update placeholder text
                    via_line_edit = self.add_via_combo.lineEdit()
                    if via_line_edit:
                        if not from_station:
                            via_line_edit.setPlaceholderText("Select From station first...")
                        elif not to_station:
                            via_line_edit.setPlaceholderText("Select To station first...")
                        else:
                            via_line_edit.setPlaceholderText("Select different From and To stations...")
                    
                    # Update route info
                    if not from_station or not to_station:
                        self.route_info_label.setText("Select From and To stations to enable routing")
                    else:
                        self.route_info_label.setText("From and To stations must be different")
                    
                except Exception as disable_error:
                    print(f"Error disabling controls: {disable_error}")
                
        except Exception as e:
            print(f"Error updating via stations availability: {e}")
            # Fallback - disable everything
            try:
                self.add_via_combo.setEnabled(False)
                self.add_via_button.setEnabled(False)
                self.suggest_route_button.setEnabled(False)
                self.fastest_route_button.setEnabled(False)
                self.auto_fix_route_button.setEnabled(False)
            except Exception as fallback_error:
                print(f"Error in fallback disable: {fallback_error}")

    def load_current_settings(self):
        """Load current settings into the dialog."""
        if not self.config:
            return

        # Station settings
        # Set from station
        from_name = self.config.stations.from_name
        if from_name:
            self.from_name_edit.setText(from_name)
            # Immediately validate and enable to station if valid
            if self.api_get_station_code(from_name.strip()):
                self.set_from_station_by_name(from_name.strip())
        
        # Set to station
        to_name = self.config.stations.to_name
        if to_name:
            self.to_name_edit.setText(to_name)
        
        # Load via stations
        if hasattr(self.config.stations, 'via_stations') and self.config.stations.via_stations:
            self.via_stations = self.config.stations.via_stations.copy()
            # Load auto-fixed flag from config if available, otherwise default to False
            self.route_auto_fixed = getattr(self.config.stations, 'route_auto_fixed', False)
            # Update the buttons display to show the loaded via stations
            self.update_via_buttons()

        # Display settings
        self.max_trains_spin.set_value(self.config.display.max_trains)
        self.time_window_spin.set_value(self.config.display.time_window_hours)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n"
            "This will overwrite your current configuration.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.config_manager.create_default_config()
                self.config = self.config_manager.load_config()
                self.load_current_settings()
                QMessageBox.information(
                    self, "Settings Reset", "Settings have been reset to defaults."
                )
            except ConfigurationError as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings: {e}")

    def save_settings(self):
        """Save current settings with route validation."""
        if not self.config:
            QMessageBox.critical(
                self, "Error", "No configuration loaded. Cannot save settings."
            )
            return

        try:
            # Get station names from input fields
            from_name = self.from_name_edit.text().strip()
            line_edit = self.to_name_edit
            to_name = line_edit.text().strip() if line_edit else ""
            
            # Check if station configuration has changed to determine if route validation is needed
            station_config_changed = False
            if self.config:
                current_from = getattr(self.config.stations, 'from_name', '')
                current_to = getattr(self.config.stations, 'to_name', '')
                current_via = getattr(self.config.stations, 'via_stations', [])
                
                station_config_changed = (
                    from_name != current_from or
                    to_name != current_to or
                    self.via_stations != current_via
                )
            
            # Only validate route if station configuration has changed and we have stations configured
            if station_config_changed and from_name and to_name and self.via_stations:
                is_valid, error_message = self.validate_route(from_name, self.via_stations, to_name)
                
                if not is_valid:
                    # Show simple validation error dialog - user must fix route manually or use Auto-Fix button
                    QMessageBox.critical(
                        self,
                        "Invalid Route Configuration",
                        f"The current route configuration is invalid and cannot be saved:\n\n{error_message}\n\nPlease fix the route using the 'Auto-Fix Route' button or manually adjust your via stations."
                    )
                    return  # Don't save, return to dialog
            
            # Get station codes from names using API
            from_code = self.api_get_station_code(from_name) if from_name else ""
            to_code = self.api_get_station_code(to_name) if to_name else ""
            
            self.config.stations.from_code = from_code if from_code else ""
            self.config.stations.from_name = from_name
            self.config.stations.to_code = to_code if to_code else ""
            self.config.stations.to_name = to_name
            
            # Save via stations
            self.config.stations.via_stations = self.via_stations.copy()
            
            # Save auto-fixed flag
            self.config.stations.route_auto_fixed = self.route_auto_fixed

            self.config.display.max_trains = self.max_trains_spin.value()
            self.config.display.time_window_hours = self.time_window_spin.value()

            # Auto-refresh removed - set to disabled and use default interval
            self.config.refresh.auto_enabled = False
            self.config.refresh.interval_minutes = 30  # Default interval
            self.config.refresh.manual_enabled = True  # Always enable manual refresh

            # Save configuration
            self.config_manager.save_config(self.config)

            # Emit signal and close dialog
            self.settings_saved.emit()
            
            # Use QTimer to ensure the signal is processed before showing the message
            QTimer.singleShot(100, lambda: [
                self.accept(),
                QMessageBox.information(
                    self, "Settings Saved", "Settings have been saved successfully."
                )
            ])

        except ConfigurationError as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}")
        except Exception as e:
            QMessageBox.critical(
                self, "Unexpected Error", f"An unexpected error occurred: {e}"
            )

    def apply_theme_styling(self):
        """Apply theme styling to the settings dialog."""
        if not self.theme_manager:
            return

        # Get current theme
        current_theme = self.theme_manager.current_theme

        if current_theme == "light":
            # Light theme styling
            dialog_style = """
            QDialog {
                background-color: #ffffff;
                color: #1976d2;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                color: #1976d2;
                padding: 8px 16px;
                border: 1px solid #cccccc;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #e3f2fd;
            }
            QGroupBox {
                color: #1976d2;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                color: #1976d2;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background-color: #ffffff;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
                color: #1976d2;
            }
            QLineEdit:focus {
                border-color: #1976d2;
            }
            QCheckBox {
                color: #1976d2;
                background-color: #ffffff;
            }
            QCheckBox::indicator {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                border: 1px solid #1976d2;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
                color: #1976d2;
            }
            QComboBox:focus {
                border-color: #1976d2;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                color: #1976d2;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 6px 12px;
                color: #1976d2;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
            QLabel {
                color: #1976d2;
                background-color: transparent;
            }
            """
        else:
            # Dark theme styling
            dialog_style = """
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #404040;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #404040;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #1a1a1a;
            }
            QGroupBox::title {
                color: #1976d2;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background-color: #1a1a1a;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #1976d2;
            }
            QCheckBox {
                color: #ffffff;
                background-color: #1a1a1a;
            }
            QCheckBox::indicator {
                background-color: #2d2d2d;
                border: 1px solid #404040;
            }
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                border: 1px solid #1976d2;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff;
            }
            QComboBox:focus {
                border-color: #1976d2;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                color: #ffffff;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 6px 12px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #404040;
                border-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #1976d2;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            """

        self.setStyleSheet(dialog_style)

    def exec(self):
        """Override exec to show dialog only when fully ready."""
        # Reload current settings every time the dialog is opened
        try:
            self.config = self.config_manager.load_config()
            self.load_current_settings()
        except ConfigurationError as e:
            logger.error(f"Failed to reload config in settings dialog: {e}")
        
        # Remove the invisible attributes and show the dialog now that everything is ready
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
        self.setVisible(True)
        self.show()
        # Call parent exec
        return super().exec()