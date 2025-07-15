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
from typing import Optional, List

# Set up logger for this module
logger = logging.getLogger(__name__)
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
    logger.debug("Attempting to load station database...")
    if station_database.load_database():
        logger.info(f"Station database loaded successfully: {len(station_database.all_stations)} stations")
        logger.debug(f"Database stats: {station_database.get_database_stats()}")
        
        # Debug: Check if South Western Main Line loaded
        swml_line = station_database.railway_lines.get("South Western Main Line")
        if swml_line:
            logger.debug(f"South Western Main Line loaded with {len(swml_line.stations)} stations")
            # Check for Farnborough stations specifically
            farnborough_stations = [s.name for s in swml_line.stations if 'farnborough' in s.name.lower()]
            logger.debug(f"Farnborough stations in SWML: {farnborough_stations}")
        else:
            logger.warning("South Western Main Line not found in loaded lines")
            logger.debug(f"Available lines: {list(station_database.railway_lines.keys())}")
        
        # Check station name mappings for Farnborough
        farnborough_mappings = {name: name for name in station_database.all_stations.keys() if 'farnborough' in name.lower()}
        logger.debug(f"Farnborough name mappings: {farnborough_mappings}")
        
    else:
        logger.error("Failed to load station database")
except Exception as e:
    logger.error(f"Error loading station database: {e}")
    import traceback
    traceback.print_exc()


class TimePickerWidget(QWidget):
    """A time picker widget with hour and minute spinners."""

    timeChanged = Signal(str)  # Emits time in HH:MM format

    def __init__(self, initial_time="", parent=None, theme_manager=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        
        # Parse initial time or use current time
        if initial_time and ":" in initial_time:
            try:
                hour, minute = map(int, initial_time.split(":"))
                self._hour = max(0, min(23, hour))
                self._minute = max(0, min(59, minute))
            except (ValueError, IndexError):
                # Default to 09:00 if parsing fails
                self._hour = 9
                self._minute = 0
        else:
            # Default to 09:00
            self._hour = 9
            self._minute = 0

        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Hour controls
        self.hour_down_button = QPushButton("◀")
        self.hour_down_button.setFixedSize(40, 32)
        self.hour_down_button.clicked.connect(self.decrement_hour)

        self.hour_label = QLabel(f"{self._hour:02d}")
        self.hour_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_label.setMinimumWidth(30)
        self.hour_label.setFixedHeight(32)

        self.hour_up_button = QPushButton("▶")
        self.hour_up_button.setFixedSize(40, 32)
        self.hour_up_button.clicked.connect(self.increment_hour)

        # Colon separator
        colon_label = QLabel(":")
        colon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        colon_label.setFixedHeight(32)
        colon_label.setStyleSheet("font-weight: bold; font-size: 16px;")

        # Minute controls
        self.minute_down_button = QPushButton("◀")
        self.minute_down_button.setFixedSize(40, 32)
        self.minute_down_button.clicked.connect(self.decrement_minute)

        self.minute_label = QLabel(f"{self._minute:02d}")
        self.minute_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minute_label.setMinimumWidth(30)
        self.minute_label.setFixedHeight(32)

        self.minute_up_button = QPushButton("▶")
        self.minute_up_button.setFixedSize(40, 32)
        self.minute_up_button.clicked.connect(self.increment_minute)

        # Add widgets to layout
        main_layout.addWidget(self.hour_down_button)
        main_layout.addWidget(self.hour_label)
        main_layout.addWidget(self.hour_up_button)
        main_layout.addWidget(colon_label)
        main_layout.addWidget(self.minute_down_button)
        main_layout.addWidget(self.minute_label)
        main_layout.addWidget(self.minute_up_button)

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
                font-size: 16px;
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

        self.hour_up_button.setStyleSheet(button_style)
        self.hour_down_button.setStyleSheet(button_style)
        self.minute_up_button.setStyleSheet(button_style)
        self.minute_down_button.setStyleSheet(button_style)
        self.hour_label.setStyleSheet(label_style)
        self.minute_label.setStyleSheet(label_style)

    def increment_hour(self):
        """Increment the hour value."""
        self._hour = (self._hour + 1) % 24
        self.update_display()
        self.emit_time_changed()

    def decrement_hour(self):
        """Decrement the hour value."""
        self._hour = (self._hour - 1) % 24
        self.update_display()
        self.emit_time_changed()

    def increment_minute(self):
        """Increment the minute value."""
        self._minute = (self._minute + 5) % 60  # Increment by 5 minutes
        self.update_display()
        self.emit_time_changed()

    def decrement_minute(self):
        """Decrement the minute value."""
        self._minute = (self._minute - 5) % 60  # Decrement by 5 minutes
        self.update_display()
        self.emit_time_changed()


    def update_display(self):
        """Update the display labels."""
        self.hour_label.setText(f"{self._hour:02d}")
        self.minute_label.setText(f"{self._minute:02d}")

    def emit_time_changed(self):
        """Emit the timeChanged signal with current time."""
        time_str = f"{self._hour:02d}:{self._minute:02d}"
        self.timeChanged.emit(time_str)

    def get_time(self):
        """Get the current time as HH:MM string."""
        return f"{self._hour:02d}:{self._minute:02d}"

    def set_time(self, time_str):
        """Set the time from HH:MM string."""
        if not time_str or time_str == "":
            self._hour = 9
            self._minute = 0
        else:
            try:
                hour, minute = map(int, time_str.split(":"))
                self._hour = max(0, min(23, hour))
                self._minute = max(0, min(59, minute))
            except (ValueError, IndexError):
                self._hour = 9
                self._minute = 0
        self.update_display()

    def is_empty(self):
        """Check if time is at default/empty state."""
        return self._hour == 9 and self._minute == 0

    def suggest_times(self, suggested_times):
        """Show a tooltip or context menu with suggested times."""
        if not suggested_times:
            return
        
        # Create a simple tooltip with suggested times
        times_text = "Suggested times: " + ", ".join(suggested_times[:6])  # Show first 6 times
        self.setToolTip(times_text)
        
        # You could also implement a dropdown or context menu here
        # For now, just update the tooltip


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


class StationsSettingsDialog(QDialog):
    """
    Stations settings dialog for configuring station settings, display preferences, and refresh settings.
    
    CRASH-PROOF VERSION: Extensive try-except blocks around all operations to prevent program crashes.

    Features:
    - Station configuration
    - Display preferences
    - Refresh settings
    """

    # Signal emitted when settings are saved
    settings_saved = Signal()

    def __init__(self, config_manager: ConfigManager, parent=None, theme_manager=None):
        """
        Initialize the stations settings dialog with extensive error handling.

        Args:
            config_manager: Configuration manager instance
            parent: Parent widget
            theme_manager: Shared theme manager instance
        """
        logger.debug("Starting crash-proof dialog initialization...")
        
        try:
            super().__init__(parent)
            logger.debug("QDialog.__init__ completed")
        except Exception as e:
            print(f"❌ CRITICAL: QDialog.__init__ failed: {e}")
            # This is catastrophic - we can't continue
            raise

        try:
            # Make dialog completely invisible during initialization
            self.setVisible(False)
            self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            print("✅ Dialog visibility attributes set")
        except Exception as e:
            print(f"⚠️ Warning: Failed to set visibility attributes: {e}")
            # Continue anyway

        try:
            self.config_manager = config_manager
            self.config: Optional[ConfigData] = None
            print("✅ Basic attributes initialized")
        except Exception as e:
            print(f"❌ CRITICAL: Failed to set basic attributes: {e}")
            raise

        try:
            # Use shared theme manager or create new one
            self.theme_manager = theme_manager or ThemeManager()
            print("✅ Theme manager initialized")
        except Exception as e:
            print(f"⚠️ Warning: Theme manager initialization failed: {e}")
            self.theme_manager = None

        try:
            # Initialize worker manager for async operations
            self.worker_manager = WorkerManager(station_database, self)
            self.pending_operations = {}  # Track pending async operations
            print("✅ Worker manager initialized")
        except Exception as e:
            print(f"⚠️ Warning: Worker manager initialization failed: {e}")
            self.worker_manager = None
            self.pending_operations = {}
        
        try:
            # Setup worker connections
            self._setup_worker_connections()
            print("✅ Worker connections set up")
        except Exception as e:
            print(f"⚠️ Warning: Worker connections setup failed: {e}")

        try:
            # Load current configuration
            self.config = self.config_manager.load_config()
            print("✅ Configuration loaded")
        except Exception as e:
            print(f"⚠️ Warning: Failed to load config: {e}")
            self.config = None

        try:
            self.setup_ui()
            print("✅ UI setup completed")
        except Exception as e:
            print(f"❌ CRITICAL: UI setup failed: {e}")
            # Try to create a minimal UI
            try:
                self._create_minimal_ui()
                print("✅ Minimal UI created as fallback")
            except Exception as minimal_error:
                print(f"❌ CATASTROPHIC: Even minimal UI failed: {minimal_error}")
                raise

        try:
            self.load_current_settings()
            print("✅ Current settings loaded")
        except Exception as e:
            print(f"⚠️ Warning: Failed to load current settings: {e}")

        try:
            # Apply theme styling
            self.apply_theme_styling()
            print("✅ Theme styling applied")
        except Exception as e:
            print(f"⚠️ Warning: Theme styling failed: {e}")

        print("🚨 CRASH-PROOF DIALOG: Initialization completed")
    
    def __del__(self):
        """Destructor to ensure proper cleanup when dialog is destroyed."""
        try:
            print("🧹 CRASH-PROOF DIALOG: Destructor called - cleaning up...")
            self._cleanup_worker_threads()
            print("✅ Destructor cleanup completed")
        except Exception as destructor_error:
            print(f"⚠️ Destructor cleanup failed: {destructor_error}")
    
    def closeEvent(self, event):
        """Override closeEvent to ensure proper cleanup."""
        try:
            print("🧹 CRASH-PROOF DIALOG: Close event - cleaning up...")
            self._cleanup_worker_threads()
            print("✅ Close event cleanup completed")
            event.accept()
        except Exception as close_event_error:
            print(f"⚠️ Close event cleanup failed: {close_event_error}")
            event.accept()  # Accept anyway to prevent hanging
    
    def _create_minimal_ui(self):
        """Create a minimal UI as a fallback if normal UI setup fails."""
        print("🔧 Creating minimal fallback UI...")
        
        try:
            from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout
            
            # Set basic properties
            self.setWindowTitle("Train Settings (Minimal Mode)")
            self.setModal(True)
            self.setMinimumSize(400, 200)
            
            # Create minimal layout
            layout = QVBoxLayout(self)
            
            # Add error message
            error_label = QLabel("Settings dialog is in minimal mode due to initialization errors.\nSome features may not be available.")
            error_label.setStyleSheet("color: orange; font-weight: bold; padding: 10px;")
            layout.addWidget(error_label)
            
            # Add buttons
            button_layout = QHBoxLayout()
            
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(self._safe_reject)
            button_layout.addWidget(cancel_button)
            
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(self._safe_accept)
            button_layout.addWidget(ok_button)
            
            layout.addLayout(button_layout)
            
            print("✅ Minimal UI created successfully")
            
        except Exception as e:
            print(f"❌ Failed to create minimal UI: {e}")
            raise
    
    def _safe_accept(self):
        """Safely accept the dialog."""
        try:
            print("🔧 Safe accept called")
            self.accept()
        except Exception as e:
            print(f"⚠️ Safe accept failed: {e}")
            try:
                self.close()
            except:
                pass
    
    def _safe_reject(self):
        """Safely reject the dialog."""
        try:
            print("🔧 Safe reject called")
            self.reject()
        except Exception as e:
            print(f"⚠️ Safe reject failed: {e}")
            try:
                self.close()
            except:
                pass

    def _setup_worker_connections(self):
        """Setup connections to worker threads for async operations."""
        try:
            # Connect worker manager signals only if worker_manager exists
            if self.worker_manager and hasattr(self.worker_manager, 'operation_completed'):
                self.worker_manager.operation_completed.connect(self._on_operation_completed)
                self.worker_manager.operation_failed.connect(self._on_operation_failed)
                self.worker_manager.progress_updated.connect(self._on_progress_updated)
                print("✅ Worker connections established")
            else:
                print("⚠️ Worker manager not available - skipping connections")
        except Exception as e:
            print(f"⚠️ Worker connections setup failed: {e}")
        
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
                # Cancel the operation in worker manager if available
                if self.worker_manager and hasattr(self.worker_manager, 'cancel_operation'):
                    try:
                        self.worker_manager.cancel_operation(request_id)
                    except Exception as cancel_error:
                        print(f"Warning: Failed to cancel operation {request_id}: {cancel_error}")
                
                # Remove from pending operations
                if request_id in self.pending_operations:
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
                    # Direct route means no train changes required, regardless of number of stations
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

        # Departure time section
        time_label = QLabel("Departure Time (Optional):")
        time_label.setStyleSheet("font-weight: bold; color: #1976d2;")
        form.addRow(time_label)

        # Departure time picker widget
        self.departure_time_picker = TimePickerWidget(
            initial_time="",
            parent=self,
            theme_manager=self.theme_manager
        )
        
        form.addRow("Departure Time:", self.departure_time_picker)

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
        # Using absolute positioning for exact spacing control with improved sizing
        self.via_buttons_widget = QWidget()
        self.via_buttons_widget.setStyleSheet("QWidget { border: none; background: transparent; }")  # Remove any borders
        # No layout needed - using absolute positioning
        self.via_buttons_widget.setMinimumHeight(100)  # Increased height to accommodate larger buttons and more rows
        self.via_buttons_widget.setMaximumHeight(200)  # Allow for more expansion when needed
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
        self.route_info_label.setMinimumHeight(50)  # Increased minimum height for wrapped text
        self.route_info_label.setMaximumHeight(100)  # Increased maximum height for longer text
        self.route_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)  # Left-align and top-align
        from PySide6.QtWidgets import QSizePolicy
        self.route_info_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding
        )  # Allow vertical expansion
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

    def api_get_station_name(self, station_name: str, strict_mode: bool = False):
        """Get validated station name using the internal database with smart matching.
        
        Args:
            station_name: The station name to look up
            strict_mode: If True, only allow exact matches (for validating autocomplete selections)
        """
        try:
            station_name_clean = station_name.strip()
            # print(f"🔍 api_get_station_code called with: '{station_name_clean}', strict_mode={strict_mode}")
            
            # First try exact match with original name (don't parse yet)
            # Station names are used directly now - no codes needed
            station_obj = station_database.get_station_by_name(station_name_clean)
            if station_obj:
                print(f"✅ Found exact station '{station_obj.name}' for '{station_name_clean}' in internal database")
                return station_obj.name
            
            # If that fails, try with parsed name (remove parentheses)
            parsed_name = station_database.parse_station_name(station_name_clean)
            # print(f"🔍 Trying parsed name: '{parsed_name}'")
            
            if parsed_name != station_name_clean:
                parsed_station_obj = station_database.get_station_by_name(parsed_name)
                if parsed_station_obj:
                    print(f"✅ Found station '{parsed_station_obj.name}' for parsed name '{parsed_name}' in internal database")
                    return parsed_station_obj.name
            
            # In strict mode, don't use fallback search - require exact matches
            if strict_mode:
                print(f"❌ Strict mode: No exact match found for '{station_name_clean}'")
                return None
            
            # If exact matches fail, try to find the best match from search results
            # print(f"🔍 No exact match found, trying search for '{station_name_clean}'...")
            search_results = station_database.search_stations(station_name_clean, limit=5)
            
            if search_results:
                # print(f"🔍 Search results: {search_results}")
                # Use the first (best) match from search results
                best_match = search_results[0]
                
                # Try the best match directly first (without parsing)
                best_match_obj = station_database.get_station_by_name(best_match)
                if best_match_obj:
                    print(f"✅ Found best match station '{best_match_obj.name}' for '{best_match}' (from search)")
                    return best_match_obj.name
                
                # If that fails, try parsing the best match
                best_match_parsed = station_database.parse_station_name(best_match)
                if best_match_parsed != best_match:
                    best_match_parsed_obj = station_database.get_station_by_name(best_match_parsed)
                    if best_match_parsed_obj:
                        print(f"✅ Found best match station '{best_match_parsed_obj.name}' for parsed '{best_match_parsed}' (from search)")
                        return best_match_parsed_obj.name
                
                print(f"❌ Best match '{best_match}' found but no station available")
            else:
                print(f"❌ No search results found for '{station_name_clean}'")
            
            return None
            
        except Exception as e:
            print(f"❌ Error in database station code lookup: {e}")
            import traceback
            traceback.print_exc()
            return None

    def on_from_name_changed(self, text: str):
        """Handle from station name text change with immediate lookup."""
        if not text.strip():
            # Clear to station when from station is cleared
            self.clear_to_station()
            return
        
        # Cancel any pending search
        self._cancel_pending_operation("from_search")
        
        # Immediate lookup for better responsiveness
        self.lookup_from_stations()

    def on_from_name_completed(self, text: str):
        """Handle from station name autocomplete selection."""
        try:
            self.set_from_station_by_name(text)
        except Exception as e:
            print(f"Error in on_from_name_completed: {e}")

    def on_to_name_changed(self, text: str):
        """Handle to station name text change with immediate filtering."""
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
        if not query or len(query) < 1:  # Reduced from 2 to 1 character
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

    def lookup_to_stations(self):
        """Perform lookup for to stations based on current text."""
        query = self.to_name_edit.text().strip()
        if not query or len(query) < 1:
            return
        
        try:
            # Make API call to search for stations
            matches = self.api_search_stations(query)
            
            # Update completer
            model = QStringListModel(matches)
            self.to_name_completer.setModel(model)
        except Exception as e:
            print(f"Error in lookup_to_stations: {e}")

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
                
            validated_name = self.api_get_station_name(name.strip())
            if validated_name:
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
                
                # FIXED: Don't clear existing to station selection - preserve it if valid
                current_to_station = self.to_name_edit.text().strip()
                if not current_to_station:
                    # Only clear if there's no existing to station
                    self.to_name_edit.clear()
                
                # Pre-populate to station dropdown with reachable destinations
                self.populate_to_stations_completer(validated_name)
                
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

    def populate_to_stations_completer(self, from_station_name: str):
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
            
            # FIXED: Don't clear existing text - preserve user's to station selection
            # self.to_name_edit.clear()  # Commented out to preserve existing selection
            
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
            
            # Get departure time if specified
            departure_time = self.departure_time_picker.get_time() if hasattr(self, 'departure_time_picker') and not self.departure_time_picker.is_empty() else None
            departure_time = departure_time if departure_time else None
            
            # Get via station suggestions (note: suggest_via_stations doesn't use time constraints)
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
                # Dynamic button sizing parameters - optimized for better layout
                min_button_width = 120  # Reduced minimum button width
                max_button_width = 200  # Reduced maximum button width to prevent overflow
                button_height = 28      # Increased button height for better readability
                horizontal_spacing = 4  # Spacing between buttons
                vertical_spacing = 4    # Spacing between rows
                max_row_width = 700     # Maximum width available for buttons per row
                
                # Calculate button widths based on text content with better estimation
                button_data = []
                for station in self.via_stations:
                    # Better text width estimation: 8 pixels per character + padding
                    estimated_text_width = len(station) * 8 + 25  # +25 for padding and margins
                    button_width = max(min_button_width, min(estimated_text_width, max_button_width))
                    button_data.append({'station': station, 'width': button_width})
                
                # Arrange buttons with line wrapping
                current_row = 0
                current_x = 0
                max_rows_used = 0
                
                for i, data in enumerate(button_data):
                    station = data['station']
                    button_width = data['width']
                    
                    # Check if button fits on current row
                    if current_x + button_width > max_row_width and current_x > 0:
                        # Move to next row
                        current_row += 1
                        current_x = 0
                    
                    # Track maximum rows used
                    max_rows_used = max(max_rows_used, current_row)
                    
                    # Calculate position
                    x = current_x
                    y = current_row * (button_height + vertical_spacing)
                    
                    # Create button with dynamic width
                    button = QPushButton(station, self.via_buttons_widget)
                    button.setGeometry(x, y, button_width, button_height)
                    
                    # Style as selected/active via station with improved styling
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #2e7d32;
                            border: 1px solid #1b5e20;
                            border-radius: 4px;
                            padding: 3px 6px;
                            margin: 0px;
                            color: white;
                            font-weight: bold;
                            font-size: 11px;
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
                
                # Update widget height to accommodate all rows with some extra padding
                total_height = (max_rows_used + 1) * (button_height + vertical_spacing) + 10  # +10 for extra padding
                self.via_buttons_widget.setMinimumHeight(total_height)
                self.via_buttons_widget.setMaximumHeight(total_height)
                
            else:
                # No via stations - reset to minimal height
                self.via_buttons_widget.setMinimumHeight(30)
                self.via_buttons_widget.setMaximumHeight(30)
                
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
            # Get departure time if specified
            departure_time = self.departure_time_picker.get_time() if hasattr(self, 'departure_time_picker') and not self.departure_time_picker.is_empty() else None
            departure_time = departure_time if departure_time else None
            
            # Find a valid route using the station database - let it determine optimal search strategy
            routes = station_database.find_route_between_stations(from_station, to_station, departure_time=departure_time)
            
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
        print("🚀 FASTEST ROUTE BUTTON CLICKED - Starting route finding...")
        
        try:
            from_station = self.from_name_edit.text().strip()
            to_station = self.to_name_edit.text().strip()
            
            # print(f"🔍 From station: '{from_station}'")
            # print(f"🔍 To station: '{to_station}'")
            
            if not from_station or not to_station:
                print("❌ Missing stations - showing info dialog")
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
            
            # Get departure time if specified and validate it
            departure_time = self.departure_time_picker.get_time() if hasattr(self, 'departure_time_picker') and not self.departure_time_picker.is_empty() else None
            departure_time = departure_time if departure_time else None
            
            # If departure time is specified, validate it and suggest alternatives if needed
            if departure_time:
                # print(f"🔍 Departure time specified: {departure_time}")
                valid_times = self._get_valid_departure_times(from_parsed, to_parsed)
                if valid_times and departure_time not in valid_times:
                    print(f"⚠️ Departure time {departure_time} not available for this route")
                    nearest_time = self._find_nearest_valid_time(departure_time, valid_times)
                    if nearest_time:
                        print(f"💡 Suggesting nearest valid time: {nearest_time}")
                        # For now, continue with the original time but show suggestion later
                    else:
                        print("❌ No valid departure times found for this route")
            
            # First try the station database manager's route finding
            best_route = None
            # print(f"🔍 Attempting route finding from '{from_parsed}' to '{to_parsed}'")
            
            # Force database reload to ensure fresh data
            print("🔄 Force reloading station database...")
            if not station_database.load_database():
                print("❌ Database reload failed")
            
            # Debug: Check if stations exist in database using strict lookup for validation
            from_name = self.api_get_station_name(from_station, strict_mode=True)
            to_name = self.api_get_station_name(to_station, strict_mode=True)
            # print(f"🔍 Station codes (strict): from_code='{from_code}', to_code='{to_code}'")
            
            if not from_name:
                print(f"❌ CRITICAL: Cannot find station code for '{from_parsed}' (original: '{from_station}')")
                
                # Debug: Check what stations are actually in the database
                # print("🔍 Checking database contents...")
                # print(f"🔍 Database loaded: {station_database.loaded}")
                # print(f"🔍 Total stations in database: {len(station_database.all_stations)}")
                # print(f"🔍 Total station name mappings: {len(station_database.station_name_to_code)}")
                
                # Check if any Farnborough stations exist
                farnborough_stations = [name for name in station_database.all_stations.keys() if 'farnborough' in name.lower()]
                # print(f"🔍 Farnborough stations in database: {farnborough_stations}")
                
                # Try searching for similar stations
                similar_stations = station_database.search_stations(from_parsed, limit=5)
                print(f"💡 Similar stations found: {similar_stations}")
                
                # Also try searching for just "Farnborough"
                farnborough_search = station_database.search_stations("Farnborough", limit=5)
                print(f"💡 'Farnborough' search results: {farnborough_search}")
                
                # Check if South Western Main Line is loaded
                swml_line = station_database.railway_lines.get("South Western Main Line")
                if swml_line:
                    print(f"✅ South Western Main Line loaded with {len(swml_line.stations)} stations")
                    # Check if Farnborough (Main) is in the line stations
                    farnborough_in_line = [s for s in swml_line.stations if 'farnborough' in s.name.lower()]
                    # print(f"🔍 Farnborough stations in SWML: {[s.name for s in farnborough_in_line]}")
                else:
                    print("❌ South Western Main Line not found in railway_lines")
                    # print(f"🔍 Available railway lines: {list(station_database.railway_lines.keys())}")
            
            if not to_name:
                print(f"❌ CRITICAL: Cannot find station name for '{to_parsed}' (original: '{to_station}')")
                # Try searching for similar stations
                similar_stations = station_database.search_stations(to_parsed, limit=5)
                print(f"💡 Similar stations found: {similar_stations}")
            
            if not from_name or not to_name:
                print("❌ Cannot proceed with route finding - missing station names")
                # Re-enable button and show user-friendly error
                self.fastest_route_button.setEnabled(True)
                self.fastest_route_button.setText("Fastest Route")
                self.update_route_info()
                
                # Show user-friendly message asking them to select from autocomplete
                missing_stations = []
                if not from_code:
                    missing_stations.append("From station")
                if not to_code:
                    missing_stations.append("To station")
                
                station_text = " and ".join(missing_stations)
                
                QMessageBox.information(
                    self,
                    "Please Select Valid Stations",
                    f"Please select a valid {station_text.lower()} from the autocomplete list.\n\n"
                    f"Start typing the station name and then click on one of the suggestions "
                    f"that appear in the dropdown list."
                )
                return
            
            try:
                # print("🔍 Trying station database manager route finding...")
                routes = station_database.find_route_between_stations(from_parsed, to_parsed, departure_time=departure_time)
                # print(f"🔍 Database manager returned {len(routes) if routes else 0} routes")
                
                if routes:
                    # Use the shortest route found
                    best_route = min(routes, key=len)
                    print(f"✅ Found route via database manager: {' → '.join(best_route)}")
                else:
                    print("⚠️ Database manager returned no routes")
            except Exception as route_error:
                print(f"❌ Database route finding failed: {route_error}")
                import traceback
                traceback.print_exc()
            
            # If database manager fails, try our custom fastest route method
            if not best_route:
                # print("🔍 Trying custom fastest route method...")
                try:
                    best_route = self._find_fastest_direct_route(from_parsed, to_parsed)
                    if best_route:
                        print(f"✅ Found route via custom method: {' → '.join(best_route)}")
                    else:
                        print("⚠️ Custom method returned no route")
                except Exception as custom_error:
                    print(f"❌ Custom route finding failed: {custom_error}")
                    import traceback
                    traceback.print_exc()
            
            if best_route:
                print(f"✅ Best route found: {' → '.join(best_route)}")
                
                # Identify actual train change points with error handling
                train_change_stations = []
                try:
                    train_change_stations = station_database.identify_train_changes(best_route)
                    print(f"✅ Train changes identified: {train_change_stations}")
                except Exception as train_change_error:
                    print(f"⚠️ Error identifying train changes: {train_change_error}")
                    # Continue without train changes - use empty list
                
                # Update via stations
                self.via_stations.clear()
                if train_change_stations:
                    self.via_stations.extend(train_change_stations)
                    print(f"✅ Via stations updated: {self.via_stations}")
                else:
                    print("✅ No via stations needed (direct route)")
                
                # Mark route as auto-fixed
                self.route_auto_fixed = True
                
                # Update UI with error handling
                try:
                    self.update_via_buttons()
                    self.update_route_info()
                    print("✅ UI updated successfully")
                except Exception as ui_error:
                    print(f"⚠️ Error updating UI: {ui_error}")
                
                # Re-enable button BEFORE showing message dialog
                self.fastest_route_button.setEnabled(True)
                self.fastest_route_button.setText("Fastest Route")
                
                # Force UI update to ensure button is re-enabled
                QApplication.processEvents()
                
                # Show result message
                try:
                    if train_change_stations:
                        QMessageBox.information(
                            self,
                            "Fastest Route Found",
                            f"Optimal route with {len(train_change_stations)} train change(s):\n{' → '.join(best_route)}"
                        )
                    else:
                        # Direct route means no train changes required, regardless of number of stations
                        QMessageBox.information(
                            self,
                            "Direct Route",
                            f"Direct route is optimal:\n{' → '.join(best_route)}"
                        )
                except Exception as msg_error:
                    print(f"⚠️ Error showing result message: {msg_error}")
            else:
                # Re-enable button BEFORE showing message dialog
                self.fastest_route_button.setEnabled(True)
                self.fastest_route_button.setText("Fastest Route")
                self.update_route_info()
                
                # For well-known routes like Farnborough to Waterloo, provide helpful message with time suggestions
                if self._is_known_valid_route(from_parsed, to_parsed):
                    # Get valid departure times and suggest alternatives
                    valid_times = self._get_valid_departure_times(from_parsed, to_parsed)
                    
                    message = f"A route exists between {from_station} and {to_station}.\n\n"
                    
                    if departure_time and valid_times:
                        # Update time picker with suggestions
                        self.departure_time_picker.suggest_times(valid_times)
                        
                        nearest_time = self._find_nearest_valid_time(departure_time, valid_times)
                        if nearest_time:
                            message += f"The departure time {departure_time} may not be available.\n"
                            message += f"Try using {nearest_time} instead.\n\n"
                            
                            # Ask if user wants to use the suggested time
                            reply = QMessageBox.question(
                                self,
                                "Route Available - Time Suggestion",
                                f"{message}Would you like to use the suggested time {nearest_time}?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.Yes
                            )
                            if reply == QMessageBox.StandardButton.Yes:
                                self.departure_time_picker.set_time(nearest_time)
                                return  # Exit early, user can try again with new time
                        
                        # Show some available times
                        if len(valid_times) > 0:
                            sample_times = valid_times[:6]  # Show first 6 times
                            message += f"Available departure times: {', '.join(sample_times)}"
                            if len(valid_times) > 6:
                                message += f" (and {len(valid_times) - 6} more)"
                            message += "\n\n"
                    
                    message += "You can also try using the 'Auto-Fix Route' button or manually add via stations."
                    
                    QMessageBox.information(
                        self,
                        "Route Available - Check Departure Time",
                        message
                    )
                else:
                    # Enhanced error message with time suggestions
                    if departure_time:
                        valid_times = self._get_valid_departure_times(from_parsed, to_parsed)
                        if valid_times:
                            # Update time picker with suggestions
                            self.departure_time_picker.suggest_times(valid_times)
                            
                            nearest_time = self._find_nearest_valid_time(departure_time, valid_times)
                            if nearest_time:
                                error_msg = f"No route found for departure time {departure_time}.\n\nSuggested alternative: {nearest_time}"
                                # Optionally set the suggested time
                                reply = QMessageBox.question(
                                    self,
                                    "No Route Found - Time Suggestion",
                                    f"{error_msg}\n\nWould you like to use the suggested time {nearest_time}?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.Yes
                                )
                                if reply == QMessageBox.StandardButton.Yes:
                                    self.departure_time_picker.set_time(nearest_time)
                                    return  # Exit early, user can try again with new time
                            else:
                                times_str = ", ".join(valid_times[:5])  # Show first 5 times
                                error_msg = f"No route found for departure time {departure_time}.\n\nAvailable departure times: {times_str}"
                                QMessageBox.information(
                                    self,
                                    "No Route Found",
                                    error_msg
                                )
                        else:
                            # Even if no service timetable data, provide common suggested times
                            common_times = ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
                                          "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
                                          "18:00", "19:00", "20:00", "21:00", "22:00"]
                            
                            # Update time picker with common suggestions
                            self.departure_time_picker.suggest_times(common_times)
                            
                            # Find nearest common time
                            nearest_time = self._find_nearest_valid_time(departure_time, common_times)
                            
                            if nearest_time:
                                error_msg = f"No route found for departure time {departure_time}.\n\nNo service timetable data available for this route.\n\nSuggested times to try: {', '.join(common_times[:8])}\n\nNearest suggestion: {nearest_time}"
                                
                                reply = QMessageBox.question(
                                    self,
                                    "No Route Found - Try Different Time",
                                    f"{error_msg}\n\nWould you like to try {nearest_time}?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.Yes
                                )
                                if reply == QMessageBox.StandardButton.Yes:
                                    self.departure_time_picker.set_time(nearest_time)
                                    return  # Exit early, user can try again with new time
                            else:
                                error_msg = f"No route found for departure time {departure_time}.\n\nNo service timetable data available for this route.\n\nSuggested times to try: {', '.join(common_times[:8])}"
                                QMessageBox.information(
                                    self,
                                    "No Route Found",
                                    error_msg
                                )
                    else:
                        error_msg = "No Route Found\n\nNo optimal route could be found between the selected stations.\n\nPlease check that both stations are valid and try again."
                        QMessageBox.information(
                            self,
                            "No Route Found",
                            error_msg
                        )
                
        except Exception as e:
            print(f"❌ CRITICAL ERROR in find_fastest_route: {e}")
            import traceback
            traceback.print_exc()
            
            # Ensure button is re-enabled in all error cases
            try:
                self.fastest_route_button.setEnabled(True)
                self.fastest_route_button.setText("Fastest Route")
                self.update_route_info()
                print("✅ Button re-enabled after error")
            except Exception as button_error:
                print(f"❌ Error re-enabling button: {button_error}")
            
            # Show error message
            try:
                QMessageBox.critical(self, "Error", f"Failed to find fastest route: {e}")
            except Exception as msg_error:
                print(f"❌ Error showing error message: {msg_error}")
    
    def _find_fastest_direct_route(self, from_station: str, to_station: str) -> Optional[List[str]]:
        """Find the fastest direct route using actual railway service patterns and real stopping patterns."""
        try:
            # Get station codes using strict lookup for validation
            from_name = self.api_get_station_name(from_station, strict_mode=True)
            to_name = self.api_get_station_name(to_station, strict_mode=True)
            
            if not from_name or not to_name:
                return None
            
            # Check if both stations are on the same line
            from_lines = set(station_database.get_railway_lines_for_station(from_name))
            to_lines = set(station_database.get_railway_lines_for_station(to_name))
            common_lines = from_lines.intersection(to_lines)
            
            if common_lines:
                line_name = list(common_lines)[0]
                railway_line = station_database.railway_lines.get(line_name)
                
                if railway_line:
                    # First, try to find the best service pattern that serves both stations
                    best_route = self._find_best_service_pattern_route(railway_line, from_name, to_name)
                    if best_route:
                        return best_route
                    
                    # Fallback: create a realistic route based on actual line geography
                    return self._create_realistic_route(from_name, to_name, railway_line)
            
            return None
            
        except Exception as e:
            print(f"Error in fastest direct route: {e}")
            return None
    
    def _find_best_service_pattern_route(self, railway_line, from_code: str, to_code: str) -> Optional[List[str]]:
        """Find the best service pattern route that serves both stations with proper time ordering."""
        try:
            # print(f"🔍 _find_best_service_pattern_route: from_code='{from_code}', to_code='{to_code}'")
            
            if not railway_line.service_patterns:
                print("❌ No service patterns available")
                return None
            
            all_station_codes = [s.code for s in railway_line.stations]
            # print(f"🔍 All station codes: {all_station_codes}")
            
            # Try service patterns in order of preference: express, fast, semi_fast, stopping
            for pattern_name in ['express', 'fast', 'semi_fast', 'stopping']:
                # print(f"🔍 Trying {pattern_name} service pattern...")
                
                pattern = railway_line.service_patterns.get_pattern(pattern_name)
                if not pattern:
                    print(f"❌ No {pattern_name} pattern found")
                    continue
                
                # Get stations served by this pattern
                if pattern.stations == "all":
                    pattern_stations = all_station_codes
                    print(f"✅ {pattern_name} serves all stations ({len(pattern_stations)} stations)")
                elif isinstance(pattern.stations, list):
                    pattern_stations = pattern.stations
                    print(f"✅ {pattern_name} serves specific stations: {pattern_stations}")
                else:
                    print(f"❌ {pattern_name} has invalid stations format")
                    continue
                
                # Check if both stations are served by this pattern
                from_in_pattern = from_code in pattern_stations
                to_in_pattern = to_code in pattern_stations
                # print(f"🔍 {pattern_name}: from_code '{from_code}' in pattern: {from_in_pattern}")
                # print(f"🔍 {pattern_name}: to_code '{to_code}' in pattern: {to_in_pattern}")
                
                if from_in_pattern and to_in_pattern:
                    print(f"✅ Both stations found in {pattern_name} pattern")
                    try:
                        from_idx = pattern_stations.index(from_code)
                        to_idx = pattern_stations.index(to_code)
                        # print(f"🔍 Station indices: from_idx={from_idx}, to_idx={to_idx}")
                        
                        # Extract route between stations in correct direction
                        # Always go from the user's specified from_station to to_station
                        if from_idx < to_idx:
                            # Normal direction: from_station appears before to_station in the line
                            route_codes = pattern_stations[from_idx:to_idx + 1]
                            # print(f"🔍 Forward route codes: {route_codes}")
                        else:
                            # Reverse direction: from_station appears after to_station in the line
                            # We need to get the stations from to_station to from_station, then reverse
                            route_codes = list(pattern_stations[to_idx:from_idx + 1])
                            route_codes.reverse()  # Now we have from_station -> ... -> to_station
                            # print(f"🔍 Corrected reverse route codes: {route_codes}")
                        
                        # Convert codes to names and create route in user's requested direction
                        route_with_times = []
                        for station_name in route_codes:
                            station = station_database.get_station_by_name(station_name)
                            if station and station.name:
                                # Filter out line names that might have been included as stations
                                if not self._is_line_name(station.name):
                                    route_with_times.append({
                                        'name': station.name,
                                        'station_name': station_name,
                                        'times': self._get_station_times(station, railway_line)
                                    })
                                else:
                                    print(f"⚠️ Filtered out line name: {station.name}")
                            else:
                                print(f"⚠️ Could not find station for name: {station_name}")
                        
                        # Extract just the station names in the order we constructed them
                        # Do NOT sort by geographical position as this would override our direction correction
                        route_names = [station['name'] for station in route_with_times]
                        
                        # Ensure the route starts with from_station and ends with to_station
                        if route_names:
                            from_station_obj = station_database.get_station_by_name(from_code)
                            to_station_obj = station_database.get_station_by_name(to_code)
                            from_station_name = from_station_obj.name if from_station_obj else None
                            to_station_name = to_station_obj.name if to_station_obj else None
                            
                            # Verify the route direction is correct
                            if (from_station_name and to_station_name and
                                len(route_names) >= 2 and
                                route_names[0] != from_station_name):
                                print(f"⚠️ Route direction incorrect: expected to start with {from_station_name}, got {route_names[0]}")
                                # If the route is backwards, reverse it
                                if route_names[-1] == from_station_name and route_names[0] == to_station_name:
                                    route_names.reverse()
                                    print(f"🔄 Reversed route to correct direction: {' → '.join(route_names)}")
                        
                        if len(route_names) >= 2:
                            print(f"✅ Found {pattern_name} service route (time-ordered): {' → '.join(route_names)}")
                            return route_names
                        else:
                            print(f"❌ Route too short: {route_names}")
                            
                    except ValueError as e:
                        print(f"❌ ValueError in {pattern_name}: {e}")
                        continue
                else:
                    print(f"❌ Not both stations in {pattern_name} pattern")
            
            print("❌ No suitable service pattern found")
            return None
            
        except Exception as e:
            print(f"Error finding best service pattern route: {e}")
            return None
    
    def _create_realistic_route(self, from_code: str, to_code: str, railway_line) -> Optional[List[str]]:
        """Create a realistic route based on actual line geography and typical service patterns with proper time ordering."""
        try:
            all_stations = railway_line.stations
            station_codes = [s.code for s in all_stations]
            
            # Find positions of from and to stations
            try:
                from_idx = station_codes.index(from_code)
                to_idx = station_codes.index(to_code)
            except ValueError:
                return None
            
            # Get the range of stations between from and to
            if from_idx < to_idx:
                route_stations = all_stations[from_idx:to_idx + 1]
            else:
                # Reverse direction: from_station appears after to_station in the line
                # We need to get the stations from to_station to from_station, then reverse
                route_stations = list(all_stations[to_idx:from_idx + 1])
                route_stations.reverse()  # Now we have from_station -> ... -> to_station
            
            # Create a realistic stopping pattern based on typical train services
            realistic_route = self._filter_to_realistic_stops(route_stations, railway_line)
            
            if not realistic_route:
                return None
            
            # Create route in user's requested direction
            route_with_times = []
            for station in realistic_route:
                if station and station.name and not self._is_line_name(station.name):
                    route_with_times.append({
                        'name': station.name,
                        'code': station.code,
                        'times': self._get_station_times(station, railway_line)
                    })
            
            # Extract just the station names in the order we constructed them
            # Do NOT sort by geographical position as this would override our direction correction
            route_names = [station['name'] for station in route_with_times]
            
            # Ensure the route starts with from_station and ends with to_station
            if route_names and len(route_names) >= 2:
                from_station_obj = station_database.get_station_by_name(from_code)
                to_station_obj = station_database.get_station_by_name(to_code)
                from_station_name = from_station_obj.name if from_station_obj else None
                to_station_name = to_station_obj.name if to_station_obj else None
                
                # Verify the route direction is correct
                if (from_station_name and to_station_name and
                    route_names[0] != from_station_name):
                    print(f"⚠️ Route direction incorrect: expected to start with {from_station_name}, got {route_names[0]}")
                    # If the route is backwards, reverse it
                    if route_names[-1] == from_station_name and route_names[0] == to_station_name:
                        route_names.reverse()
                        print(f"🔄 Reversed route to correct direction: {' → '.join(route_names)}")
            
            return route_names if len(route_names) >= 2 else None
            
        except Exception as e:
            print(f"Error creating realistic route: {e}")
            return None
    
    def _filter_to_realistic_stops(self, route_stations, railway_line) -> List:
        """Filter stations to create a realistic stopping pattern like real train services."""
        try:
            if len(route_stations) <= 3:
                # Short routes - include all stations
                return route_stations
            
            realistic_stops = []
            
            # Always include first and last stations
            realistic_stops.append(route_stations[0])
            
            # For intermediate stations, apply realistic filtering rules
            for i, station in enumerate(route_stations[1:-1], 1):
                include_station = False
                
                # Always include major interchange stations
                if hasattr(station, 'interchange') and station.interchange:
                    include_station = True
                
                # Include major stations (based on common major station codes)
                elif station.name in ['Clapham Junction', 'Woking', 'Basingstoke', 'Winchester', 'Southampton Central', 'London Victoria', 'London Waterloo', 'London Paddington', 'London Kings Cross', 'London Euston', 'London Liverpool Street', 'London Bridge']:
                    include_station = True
                
                # For longer routes, include some intermediate stations at regular intervals
                elif len(route_stations) > 8:
                    # Include every 2nd or 3rd station for very long routes
                    if i % 2 == 0:
                        include_station = True
                elif len(route_stations) > 5:
                    # Include every other station for medium routes
                    if i % 2 == 1:
                        include_station = True
                
                # Use line-specific realistic stopping patterns
                if not include_station:
                    include_station = self._is_typical_stop_for_line(station, railway_line, route_stations)
                
                if include_station:
                    realistic_stops.append(station)
            
            # Always include the destination
            if route_stations[-1] not in realistic_stops:
                realistic_stops.append(route_stations[-1])
            
            return realistic_stops
            
        except Exception as e:
            print(f"Error filtering to realistic stops: {e}")
            return route_stations  # Return all stations as fallback
    
    def _is_typical_swr_stop(self, station, route_stations) -> bool:
        """Determine if a station is a typical stop for South Western Railway services."""
        # Based on real SWR service patterns observed from research
        typical_swr_stops = {
            'FNB',  # Farnborough (Main) - major station
            'BKW',  # Brookwood - typical stop
            'WOK',  # Woking - major interchange
            'WYB',  # Weybridge - typical stop
            'WAL',  # Walton-on-Thames - typical stop
            'SUR',  # Surbiton - major station
            'CLJ',  # Clapham Junction - major interchange
            'WIM',  # Wimbledon - major interchange
            'RAY',  # Raynes Park - typical stop
            'NEM',  # New Malden - typical stop
            'ESH',  # Esher - typical stop
            'HER',  # Hersham - typical stop
            'THD',  # Thames Ditton - typical stop
        }
        
        return station.code in typical_swr_stops
    
    def _is_typical_stop_for_line(self, station, railway_line, route_stations) -> bool:
        """Determine if a station is a typical stop for any railway line based on real service patterns."""
        line_name = railway_line.metadata.get('line_name', '')
        
        # Line-specific typical stops based on real service patterns
        if 'South Western' in line_name:
            return self._is_typical_swr_stop(station, route_stations)
        elif 'Great Western' in line_name:
            return self._is_typical_gwr_stop(station, route_stations)
        elif 'East Coast' in line_name:
            return self._is_typical_ecml_stop(station, route_stations)
        elif 'West Coast' in line_name:
            return self._is_typical_wcml_stop(station, route_stations)
        elif 'Brighton' in line_name:
            return self._is_typical_brighton_stop(station, route_stations)
        elif 'Thameslink' in line_name:
            return self._is_typical_thameslink_stop(station, route_stations)
        else:
            # Generic logic for other lines
            return self._is_generic_typical_stop(station, route_stations)
    
    def _is_typical_gwr_stop(self, station, route_stations) -> bool:
        """Typical stops for Great Western Railway services."""
        typical_gwr_stops = {
            'PAD', 'SLO', 'MAI', 'TAP', 'BUR', 'REA', 'SWI', 'DID', 'OXF',
            'BAN', 'CHI', 'LEA', 'KIN', 'SWA', 'NEW', 'CAR', 'BRI', 'PKW',
            'WSB', 'CHI', 'TAU', 'BRI', 'WSM'
        }
        return station.code in typical_gwr_stops
    
    def _is_typical_ecml_stop(self, station, route_stations) -> bool:
        """Typical stops for East Coast Main Line services."""
        typical_ecml_stops = {
            'KGX', 'FPK', 'STE', 'HIT', 'LET', 'NEW', 'PBO', 'GRA', 'DAR',
            'NCL', 'MOR', 'ALM', 'BER', 'DUN', 'EDR', 'HAY', 'KIR', 'ABD'
        }
        return station.code in typical_ecml_stops
    
    def _is_typical_wcml_stop(self, station, route_stations) -> bool:
        """Typical stops for West Coast Main Line services."""
        typical_wcml_stops = {
            'EUS', 'WAT', 'HAR', 'MKC', 'BHM', 'COV', 'NUN', 'RUG', 'STF',
            'CRE', 'WAR', 'WVH', 'PRS', 'WIG', 'CAR', 'LOC', 'MOS', 'GSW'
        }
        return station.code in typical_wcml_stops
    
    def _is_typical_brighton_stop(self, station, route_stations) -> bool:
        """Typical stops for Brighton Main Line services."""
        typical_brighton_stops = {
            'VIC', 'CLJ', 'ECP', 'THD', 'RED', 'MER', 'COL', 'HOR', 'GAT',
            'TTH', 'BAL', 'HAY', 'WIV', 'BUR', 'HAS', 'PRE', 'BTN'
        }
        return station.code in typical_brighton_stops
    
    def _is_typical_thameslink_stop(self, station, route_stations) -> bool:
        """Typical stops for Thameslink services."""
        typical_thameslink_stops = {
            'STP', 'WGC', 'KGX', 'FPK', 'CTX', 'LBG', 'ECR', 'NWX', 'ELE',
            'SUT', 'WIM', 'MIT', 'BED', 'LUT', 'STA', 'HAR', 'GAT', 'HOR'
        }
        return station.code in typical_thameslink_stops
    
    def _is_generic_typical_stop(self, station, route_stations) -> bool:
        """Generic logic for determining typical stops on any line."""
        # Always include stations with interchanges
        if hasattr(station, 'interchange') and station.interchange:
            return True
        
        # Include major stations (common major station codes)
        major_stations = {
            'CLJ', 'WOK', 'BSK', 'WIN', 'SOU', 'VIC', 'WAT', 'PAD', 'KGX',
            'EUS', 'LST', 'LBG', 'CHX', 'WAE', 'CAN', 'STR', 'MAR', 'FAR',
            'OLD', 'MOG', 'BAR', 'KIN', 'LIV', 'MAN', 'BIR', 'COV', 'RUG'
        }
        if station.code in major_stations:
            return True
        
        # For longer routes, include some intermediate stations
        if len(route_stations) > 8:
            # Include stations at regular intervals
            station_index = next((i for i, s in enumerate(route_stations) if s.code == station.code), -1)
            if station_index > 0 and station_index % 3 == 0:
                return True
        
        return False
    
    def _create_smart_route(self, from_code: str, to_code: str, railway_line) -> Optional[List[str]]:
        """Create a smart route showing realistic stops based on actual service patterns."""
        try:
            all_stations = railway_line.stations
            station_codes = [s.code for s in all_stations]
            
            from_idx = station_codes.index(from_code)
            to_idx = station_codes.index(to_code)
            
            # Get the range of stations
            if from_idx < to_idx:
                route_range = all_stations[from_idx:to_idx + 1]
            else:
                route_range = all_stations[to_idx:from_idx + 1]
                route_range.reverse()
            
            # Use the realistic filtering method
            realistic_stops = self._filter_to_realistic_stops(route_range, railway_line)
            
            return [station.name for station in realistic_stops] if realistic_stops else None
            
        except (ValueError, IndexError) as e:
            print(f"Error creating smart route: {e}")
            return None
    
    def _is_line_name(self, name: str) -> bool:
        """Check if a name is a railway line name rather than a station name."""
        line_indicators = [
            'Main Line', 'Railway', 'Line', 'Network', 'Express', 'Metro',
            'Coast', 'Valley', 'Branch', 'Junction Line', 'Circle'
        ]
        return any(indicator in name for indicator in line_indicators)
    
    def _get_station_times(self, station, railway_line) -> List[str]:
        """Get departure times for a station from the railway line data."""
        try:
            # Look for the station in the railway line JSON data
            line_file = station_database.lines_dir / railway_line.file
            if not line_file.exists():
                return []
            
            import json
            with open(line_file, 'r', encoding='utf-8') as f:
                line_data = json.load(f)
            
            # Find the station in the JSON data
            for station_data in line_data.get('stations', []):
                if station_data.get('code') == station.code:
                    times_data = station_data.get('times', {})
                    all_times = []
                    # Collect all times from all periods
                    for period, times in times_data.items():
                        if isinstance(times, list):
                            all_times.extend(times)
                    return sorted(all_times)
            
            return []
        except Exception as e:
            print(f"Error getting station times: {e}")
            return []
    
    def _sort_route_by_geographical_position(self, route_with_times: List[dict], railway_line) -> List[dict]:
        """Sort route stations by their geographical position on the railway line, not by times."""
        try:
            # Get the original station order from the railway line
            all_stations = railway_line.stations
            station_position_map = {station.code: idx for idx, station in enumerate(all_stations)}
            
            # Sort by geographical position on the line
            def get_position_key(station_info):
                code = station_info.get('code', '')
                return station_position_map.get(code, 9999)  # Unknown stations go to end
            
            sorted_route = sorted(route_with_times, key=get_position_key)
            
            # Debug output
            # print("🔍 Route sorting by geographical position:")
            for station in sorted_route:
                code = station.get('code', '')
                position = station_position_map.get(code, 'Unknown')
                times = station.get('times', [])
                earliest = min(times) if times else "No times"
                print(f"   {station['name']} ({code}): position {position}, earliest time {earliest}")
            
            return sorted_route
            
        except Exception as e:
            print(f"Error sorting route by geographical position: {e}")
            return route_with_times  # Return unsorted as fallback

    def _find_simple_direct_route_fallback(self, from_station: str, to_station: str) -> Optional[List[str]]:
        """Simple fallback for direct routes on the same line - optimized for fastest route."""
        try:
            # Get station codes using strict lookup for validation
            from_name = self.api_get_station_name(from_station, strict_mode=True)
            to_name = self.api_get_station_name(to_station, strict_mode=True)
            
            if not from_name or not to_name:
                return None
            
            # Check if both stations are on the same line
            from_lines = set(station_database.get_railway_lines_for_station(from_name))
            to_lines = set(station_database.get_railway_lines_for_station(to_name))
            common_lines = from_lines.intersection(to_lines)
            
            if common_lines:
                # Use the first common line
                line_name = list(common_lines)[0]
                railway_line = station_database.railway_lines.get(line_name)
                
                if railway_line:
                    # Try to use service patterns for optimal route
                    if railway_line.service_patterns:
                        # Get the best service pattern (fastest)
                        best_pattern = None
                        for pattern_code in ['express', 'fast', 'semi_fast', 'stopping']:
                            pattern = railway_line.service_patterns.get_pattern(pattern_code)
                            if pattern and pattern.serves_station(from_code, [s.name for s in railway_line.stations]) and pattern.serves_station(to_code, [s.name for s in railway_line.stations]):
                                best_pattern = pattern
                                break
                        
                        if best_pattern:
                            # Use service pattern stations
                            if best_pattern.stations == "all":
                                pattern_stations = [s.name for s in railway_line.stations]
                            elif isinstance(best_pattern.stations, list):
                                pattern_stations = best_pattern.stations
                            else:
                                pattern_stations = [s.name for s in railway_line.stations]
                            
                            # Find route within service pattern
                            try:
                                from_idx = pattern_stations.index(from_code)
                                to_idx = pattern_stations.index(to_code)
                                
                                if from_idx < to_idx:
                                    route_codes = pattern_stations[from_idx:to_idx + 1]
                                else:
                                    # Reverse direction: from_station appears after to_station in the line
                                    # We need to get the stations from to_station to from_station, then reverse
                                    route_codes = list(pattern_stations[to_idx:from_idx + 1])
                                    route_codes.reverse()  # Now we have from_station -> ... -> to_station
                                
                                # Convert codes to names
                                route_names = []
                                for station_name in route_codes:
                                    station = station_database.get_station_by_name(station_name)
                                    if station:
                                        route_names.append(station.name)
                                
                                # Ensure the route direction is correct
                                if route_names and len(route_names) >= 2:
                                    from_station_obj = station_database.get_station_by_name(from_code)
                                    to_station_obj = station_database.get_station_by_name(to_code)
                                    from_station_name = from_station_obj.name if from_station_obj else None
                                    to_station_name = to_station_obj.name if to_station_obj else None
                                    
                                    # Verify the route direction is correct
                                    if (from_station_name and to_station_name and
                                        route_names[0] != from_station_name):
                                        print(f"⚠️ Route direction incorrect: expected to start with {from_station_name}, got {route_names[0]}")
                                        # If the route is backwards, reverse it
                                        if route_names[-1] == from_station_name and route_names[0] == to_station_name:
                                            route_names.reverse()
                                            print(f"🔄 Reversed route to correct direction: {' → '.join(route_names)}")
                                
                                return route_names if len(route_names) >= 2 else None
                                
                            except ValueError:
                                pass  # Fall through to basic route
                    
                    # Fallback to basic direct route (for lines without service patterns)
                    station_names = [station.name for station in railway_line.stations]
                    
                    try:
                        from_idx = station_names.index(from_code)
                        to_idx = station_names.index(to_code)
                        
                        # Get the route between stations in correct direction
                        # For fastest route, always use direct from_station -> to_station order
                        route_codes = [from_code, to_code]
                        
                        # Convert codes to names
                        route_names = []
                        for station_name in route_codes:
                            station = station_database.get_station_by_name(station_name)
                            if station:
                                route_names.append(station.name)
                        
                        # Ensure the route direction is correct (should already be correct for direct routes)
                        if route_names and len(route_names) >= 2:
                            from_station_obj = station_database.get_station_by_name(from_code)
                            to_station_obj = station_database.get_station_by_name(to_code)
                            from_station_name = from_station_obj.name if from_station_obj else None
                            to_station_name = to_station_obj.name if to_station_obj else None
                            
                            # Verify the route direction is correct
                            if (from_station_name and to_station_name and
                                route_names[0] != from_station_name):
                                print(f"⚠️ Direct route direction incorrect: expected to start with {from_station_name}, got {route_names[0]}")
                                # For direct routes, this should not happen, but reverse if needed
                                if route_names[-1] == from_station_name and route_names[0] == to_station_name:
                                    route_names.reverse()
                                    print(f"🔄 Reversed direct route to correct direction: {' → '.join(route_names)}")
                        
                        return route_names if len(route_names) >= 2 else None
                        
                    except ValueError:
                        return None
            
            return None
            
        except Exception as e:
            print(f"Error in simple direct route fallback: {e}")
            return None
    
    def _get_valid_departure_times(self, from_station: str, to_station: str) -> List[str]:
        """Get valid departure times for a route between two stations."""
        try:
            valid_times = []
            
            # Get station code using strict lookup for validation
            from_name = self.api_get_station_name(from_station, strict_mode=True)
            if not from_name:
                return []
            
            # Find which railway line contains this station
            lines = station_database.get_railway_lines_for_station(from_code)
            if not lines:
                return []
            
            # Use the first line to get timing data
            line_name = lines[0]
            railway_line = station_database.railway_lines.get(line_name)
            if not railway_line:
                return []
            
            # Load the JSON file to get timing data
            line_file = station_database.lines_dir / railway_line.file
            if not line_file.exists():
                return []
            
            try:
                import json
                with open(line_file, 'r', encoding='utf-8') as f:
                    line_data = json.load(f)
                
                # Find the station in the JSON data
                for station_data in line_data.get('stations', []):
                    if station_data.get('code') == from_code:
                        times_data = station_data.get('times', {})
                        # Collect all times from all periods
                        for period, times in times_data.items():
                            if isinstance(times, list):
                                valid_times.extend(times)
                        break
                
            except Exception as json_error:
                print(f"Error reading JSON file: {json_error}")
                return []
            
            # Sort times chronologically and remove duplicates
            valid_times = sorted(list(set(valid_times)))
            return valid_times
            
        except Exception as e:
            print(f"Error getting valid departure times: {e}")
            return []
    
    def _find_nearest_valid_time(self, target_time: str, valid_times: List[str]) -> Optional[str]:
        """Find the nearest valid time to the target time."""
        try:
            if not valid_times:
                return None
            
            # Convert times to minutes for comparison
            def time_to_minutes(time_str):
                try:
                    hours, minutes = map(int, time_str.split(':'))
                    return hours * 60 + minutes
                except:
                    return 0
            
            target_minutes = time_to_minutes(target_time)
            
            # Find the closest time
            closest_time = None
            min_diff = float('inf')
            
            for valid_time in valid_times:
                valid_minutes = time_to_minutes(valid_time)
                diff = abs(target_minutes - valid_minutes)
                
                if diff < min_diff:
                    min_diff = diff
                    closest_time = valid_time
            
            return closest_time
            
        except Exception as e:
            print(f"Error finding nearest valid time: {e}")
            return None

    def _is_known_valid_route(self, from_station: str, to_station: str) -> bool:
        """Check if this is a known valid route that should exist."""
        # List of known valid route patterns
        known_routes = [
            ("Farnborough (Main)", "London Waterloo"),
            ("London Waterloo", "Farnborough (Main)"),
            ("Woking", "London Waterloo"),
            ("London Waterloo", "Woking"),
            ("Clapham Junction", "London Waterloo"),
            ("London Waterloo", "Clapham Junction"),
        ]
        
        return (from_station, to_station) in known_routes
    
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
            
            # Get departure time if specified
            departure_time = self.departure_time_picker.get_time() if hasattr(self, 'departure_time_picker') and not self.departure_time_picker.is_empty() else None
            departure_time = departure_time if departure_time else None
            
            # First try the station database manager's route finding
            best_route = None
            try:
                routes = station_database.find_route_between_stations(from_parsed, to_parsed, departure_time=departure_time)
                if routes:
                    # Use the best route (first one is typically best)
                    best_route = routes[0]
                    print(f"Auto-fix found route via database manager: {' → '.join(best_route)}")
            except Exception as route_error:
                print(f"Database route finding failed: {route_error}")
            
            # If database manager fails, try our fallback method
            if not best_route:
                best_route = self._find_simple_direct_route_fallback(from_parsed, to_parsed)
                if best_route:
                    print(f"Auto-fix found route via fallback: {' → '.join(best_route)}")
            
            if best_route:
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
                # For well-known routes, provide helpful message
                if self._is_known_valid_route(from_parsed, to_parsed):
                    QMessageBox.information(
                        self,
                        "Route Available",
                        f"A route exists between {from_station} and {to_station}.\n\n"
                        "The route finder is currently experiencing issues. "
                        "You can manually add via stations like 'Woking' or 'Clapham Junction' if needed."
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
            
            # print(f"🔍 update_via_stations_availability called:")
            print(f"   from_station: '{from_station}'")
            print(f"   to_station: '{to_station}'")
            
            # Check if we have both from and to stations AND they can be found in the database
            has_both_stations = False
            if from_station and to_station and from_station != to_station:
                # Additional check: verify both stations can be found in the database using strict mode
                from_name = self.api_get_station_name(from_station, strict_mode=True)
                to_name = self.api_get_station_name(to_station, strict_mode=True)
                has_both_stations = bool(from_name and to_name)
                print(f"   from_name: '{from_name}', to_name: '{to_name}'")
            
            print(f"   has_both_stations: {has_both_stations}")
            
            if has_both_stations:
                # Enable via station controls
                print("✅ Both stations present - enabling controls...")
                try:
                    self.add_via_combo.setEnabled(True)
                    self.add_via_button.setEnabled(True)
                    
                    # Suggest Route should be disabled when there are any via stations displayed
                    # This prevents confusion and conflicting route modifications
                    suggest_enabled = len(self.via_stations) == 0
                    self.suggest_route_button.setEnabled(suggest_enabled)
                    print(f"   suggest_route_button enabled: {suggest_enabled}")
                    
                    self.fastest_route_button.setEnabled(True)
                    print("   ✅ fastest_route_button enabled: True")
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
                print("❌ Missing stations - disabling controls...")
                try:
                    self.add_via_combo.setEnabled(False)
                    self.add_via_button.setEnabled(False)
                    self.suggest_route_button.setEnabled(False)
                    self.fastest_route_button.setEnabled(False)
                    print("   ❌ fastest_route_button disabled")
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
            if self.api_get_station_name(from_name.strip()):
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
        
        # Load departure time if available
        if hasattr(self.config.stations, 'departure_time') and self.config.stations.departure_time:
            if hasattr(self, 'departure_time_picker'):
                self.departure_time_picker.set_time(self.config.stations.departure_time)

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
        """
        ULTRA CRASH-PROOF VERSION - Prevents entire program crashes with maximum isolation.
        Every single operation is wrapped in multiple layers of try-except blocks.
        """
        logger.debug("Starting ultra crash-proof save")
        
        # Layer 1: Outer protection against catastrophic failures
        try:
            # Layer 2: Inner protection for each step
            self._crash_proof_save_step_1_data_collection()
            self._crash_proof_save_step_2_config_update()
            self._crash_proof_save_step_3_config_save()
            self._crash_proof_save_step_4_signal_emission()
            self._crash_proof_save_step_5_dialog_close()
            
        except Exception as catastrophic_error:
            print(f"🚨 CATASTROPHIC ERROR in save_settings: {catastrophic_error}")
            # Emergency shutdown sequence
            self._emergency_dialog_close()
        
        print("🚨🚨🚨 ULTRA CRASH-PROOF SAVE COMPLETED 🚨🚨🚨")
    
    def _crash_proof_save_step_1_data_collection(self):
        """Step 1: Data collection with maximum crash protection."""
        try:
            print("🔧 Step 1: Data collection...")
            
            # Initialize with safe defaults
            self._safe_from_text = ""
            self._safe_to_text = ""
            self._safe_via_stations = []
            self._safe_departure_time = ""
            
            # Collect from station
            try:
                if (hasattr(self, 'from_name_edit') and
                    self.from_name_edit and
                    hasattr(self.from_name_edit, 'text')):
                    raw_text = self.from_name_edit.text()
                    if raw_text:
                        self._safe_from_text = str(raw_text).strip()
            except Exception as from_error:
                print(f"⚠️ From station collection failed: {from_error}")
            
            # Collect to station
            try:
                if (hasattr(self, 'to_name_edit') and
                    self.to_name_edit and
                    hasattr(self.to_name_edit, 'text')):
                    raw_text = self.to_name_edit.text()
                    if raw_text:
                        self._safe_to_text = str(raw_text).strip()
            except Exception as to_error:
                print(f"⚠️ To station collection failed: {to_error}")
            
            # Collect via stations
            try:
                if hasattr(self, 'via_stations') and isinstance(self.via_stations, list):
                    self._safe_via_stations = [str(station) for station in self.via_stations if station]
            except Exception as via_error:
                print(f"⚠️ Via stations collection failed: {via_error}")
            
            # Collect departure time
            try:
                if (hasattr(self, 'departure_time_picker') and
                    self.departure_time_picker and
                    True):
                    raw_text = self.departure_time_picker.get_time()
                    if raw_text:
                        self._safe_departure_time = str(raw_text).strip()
            except Exception as time_error:
                print(f"⚠️ Departure time collection failed: {time_error}")
            
            print(f"✅ Data collected: from='{self._safe_from_text}', to='{self._safe_to_text}'")
            
        except Exception as step_error:
            print(f"❌ Step 1 failed: {step_error}")
            # Set safe defaults
            self._safe_from_text = ""
            self._safe_to_text = ""
            self._safe_via_stations = []
            self._safe_departure_time = ""
    
    def _crash_proof_save_step_2_config_update(self):
        """Step 2: Config update with maximum crash protection."""
        try:
            print("🔧 Step 2: Config update...")
            
            # Check if config exists and is valid
            if not (hasattr(self, 'config') and self.config):
                print("⚠️ No config available - skipping update")
                return
            
            # Update stations config
            try:
                if hasattr(self.config, 'stations') and self.config.stations:
                    try:
                        self.config.stations.from_name = self._safe_from_text
                        print("✅ from_name updated")
                    except:
                        pass
                    
                    try:
                        self.config.stations.to_name = self._safe_to_text
                        print("✅ to_name updated")
                    except:
                        pass
                    
                    try:
                        self.config.stations.via_stations = self._safe_via_stations
                        print("✅ via_stations updated")
                    except:
                        pass
                    
                    try:
                        self.config.stations.departure_time = self._safe_departure_time
                        print("✅ departure_time updated")
                    except:
                        pass
                        
                    # Get station codes safely
                    try:
                        if self._safe_from_text and hasattr(self, 'api_get_station_code'):
                            code = self.api_get_station_code(self._safe_from_text)
                            if code:
                                self.config.stations.from_code = str(code)
                    except:
                        pass
                    
                    try:
                        if self._safe_to_text and hasattr(self, 'api_get_station_code'):
                            code = self.api_get_station_code(self._safe_to_text)
                            if code:
                                self.config.stations.to_code = str(code)
                    except:
                        pass
                        
            except Exception as stations_error:
                print(f"⚠️ Stations config update failed: {stations_error}")
            
            print("✅ Config update completed")
            
        except Exception as step_error:
            print(f"❌ Step 2 failed: {step_error}")
    
    def _crash_proof_save_step_3_config_save(self):
        """Step 3: Config save with maximum crash protection."""
        try:
            print("🔧 Step 3: Config save...")
            
            if (hasattr(self, 'config_manager') and
                self.config_manager and
                hasattr(self, 'config') and
                self.config):
                try:
                    self.config_manager.save_config(self.config)
                    print("✅ Config saved to file")
                except Exception as save_error:
                    print(f"⚠️ Config save failed: {save_error}")
            else:
                print("⚠️ Cannot save - missing config manager or config")
                
        except Exception as step_error:
            print(f"❌ Step 3 failed: {step_error}")
    
    def _crash_proof_save_step_4_signal_emission(self):
        """Step 4: Signal emission with maximum crash protection."""
        try:
            print("🔧 Step 4: Signal emission...")
            
            if (hasattr(self, 'settings_saved') and
                self.settings_saved and
                hasattr(self.settings_saved, 'emit')):
                try:
                    self.settings_saved.emit()
                    print("✅ Signal emitted")
                except Exception as signal_error:
                    print(f"⚠️ Signal emission failed: {signal_error}")
            else:
                print("⚠️ No signal to emit")
                
        except Exception as step_error:
            print(f"❌ Step 4 failed: {step_error}")
    
    def _crash_proof_save_step_5_dialog_close(self):
        """Step 5: Dialog close with maximum crash protection and thread cleanup."""
        try:
            print("🔧 Step 5: Dialog close with thread cleanup...")
            
            # CRITICAL: Clean up worker threads BEFORE closing dialog
            self._cleanup_worker_threads()
            
            # Try multiple close methods with individual protection
            close_methods = [
                ('accept', self._try_accept),
                ('reject', self._try_reject),
                ('close', self._try_close),
                ('hide', self._try_hide),
                ('setVisible', self._try_set_invisible)
            ]
            
            for method_name, method_func in close_methods:
                try:
                    print(f"Trying {method_name}()...")
                    if method_func():
                        print(f"✅ Dialog closed with {method_name}()")
                        return
                except Exception as method_error:
                    print(f"⚠️ {method_name}() failed: {method_error}")
                    continue
            
            print("❌ All close methods failed")
                
        except Exception as step_error:
            print(f"❌ Step 5 failed: {step_error}")
    
    def _cleanup_worker_threads(self):
        """Clean up worker threads to prevent QThread destruction errors."""
        try:
            print("🧹 Cleaning up worker threads...")
            
            # Cancel all pending operations
            try:
                if hasattr(self, 'pending_operations') and self.pending_operations:
                    print(f"Canceling {len(self.pending_operations)} pending operations...")
                    for request_id in list(self.pending_operations.keys()):
                        try:
                            if (self.worker_manager and
                                hasattr(self.worker_manager, 'cancel_operation')):
                                self.worker_manager.cancel_operation(request_id)
                        except Exception as cancel_error:
                            print(f"⚠️ Failed to cancel operation {request_id}: {cancel_error}")
                    
                    self.pending_operations.clear()
                    print("✅ Pending operations cleared")
            except Exception as pending_error:
                print(f"⚠️ Error clearing pending operations: {pending_error}")
            
            # Try to stop worker manager using various methods
            try:
                if (hasattr(self, 'worker_manager') and
                    self.worker_manager):
                    print("Attempting to stop worker manager...")
                    
                    # Try different stop methods
                    stop_methods = ['stop', 'quit', 'terminate', 'shutdown']
                    for method_name in stop_methods:
                        if hasattr(self.worker_manager, method_name):
                            try:
                                method = getattr(self.worker_manager, method_name)
                                method()
                                print(f"✅ Worker manager stopped using {method_name}()")
                                break
                            except Exception as method_error:
                                print(f"⚠️ {method_name}() failed: {method_error}")
                                continue
                    else:
                        print("⚠️ No stop method found on worker manager")
                        
            except Exception as stop_error:
                print(f"⚠️ Error stopping worker manager: {stop_error}")
            
            # Try to wait for threads to finish using various methods
            try:
                if (hasattr(self, 'worker_manager') and
                    self.worker_manager):
                    print("Attempting to wait for worker threads...")
                    
                    # Try different wait methods
                    wait_methods = ['wait', 'join', 'waitForFinished']
                    for method_name in wait_methods:
                        if hasattr(self.worker_manager, method_name):
                            try:
                                method = getattr(self.worker_manager, method_name)
                                # Try with timeout parameter
                                try:
                                    method(1000)  # 1 second timeout
                                except TypeError:
                                    # Try without timeout
                                    method()
                                print(f"✅ Worker threads finished using {method_name}()")
                                break
                            except Exception as method_error:
                                print(f"⚠️ {method_name}() failed: {method_error}")
                                continue
                    else:
                        print("⚠️ No wait method found on worker manager")
                        
            except Exception as wait_error:
                print(f"⚠️ Error waiting for worker threads: {wait_error}")
            
            # Disconnect signals
            try:
                if (hasattr(self, 'worker_manager') and
                    self.worker_manager):
                    print("Disconnecting worker signals...")
                    
                    if hasattr(self.worker_manager, 'operation_completed'):
                        try:
                            self.worker_manager.operation_completed.disconnect()
                        except:
                            pass
                    
                    if hasattr(self.worker_manager, 'operation_failed'):
                        try:
                            self.worker_manager.operation_failed.disconnect()
                        except:
                            pass
                    
                    if hasattr(self.worker_manager, 'progress_updated'):
                        try:
                            self.worker_manager.progress_updated.disconnect()
                        except:
                            pass
                    
                    print("✅ Worker signals disconnected")
            except Exception as disconnect_error:
                print(f"⚠️ Error disconnecting worker signals: {disconnect_error}")
            
            # Set worker manager to None
            try:
                self.worker_manager = None
                print("✅ Worker manager reference cleared")
            except Exception as clear_error:
                print(f"⚠️ Error clearing worker manager reference: {clear_error}")
            
            print("✅ Worker thread cleanup completed")
            
        except Exception as cleanup_error:
            print(f"❌ Worker thread cleanup failed: {cleanup_error}")
            # Continue anyway - don't let cleanup failure prevent dialog close
    
    def _try_accept(self):
        """Try to accept the dialog."""
        try:
            self.accept()
            return True
        except:
            return False
    
    def _try_reject(self):
        """Try to reject the dialog."""
        try:
            self.reject()
            return True
        except:
            return False
    
    def _try_close(self):
        """Try to close the dialog."""
        try:
            self.close()
            return True
        except:
            return False
    
    def _try_hide(self):
        """Try to hide the dialog."""
        try:
            self.hide()
            return True
        except:
            return False
    
    def _try_set_invisible(self):
        """Try to set dialog invisible."""
        try:
            self.setVisible(False)
            return True
        except:
            return False
    
    def _emergency_dialog_close(self):
        """Emergency dialog close as last resort."""
        print("🚨 EMERGENCY DIALOG CLOSE")
        
        # Try every possible method to close/hide the dialog
        emergency_methods = [
            lambda: self.accept(),
            lambda: self.reject(),
            lambda: self.close(),
            lambda: self.hide(),
            lambda: self.setVisible(False),
            lambda: self.deleteLater(),
        ]
        
        for i, method in enumerate(emergency_methods):
            try:
                method()
                print(f"✅ Emergency method {i+1} succeeded")
                return
            except:
                continue
        
        print("❌ All emergency methods failed - dialog may remain open")
    
    def _collect_ui_data_simple(self):
        """Simple UI data collection without extensive debugging."""
        ui_data = {}
        
        # Collect basic fields
        ui_data['departure_station'] = self.from_name_edit.text().strip()
        ui_data['arrival_station'] = self.to_name_edit.text().strip()
        ui_data['via_stations'] = self.via_stations.copy() if hasattr(self, 'via_stations') else []
        ui_data['departure_time'] = self.departure_time_picker.get_time().strip() if hasattr(self, 'departure_time_picker') else ''
        ui_data['route_auto_fixed'] = getattr(self, 'route_auto_fixed', False)
        ui_data['max_results'] = self.max_trains_spin.value()
        ui_data['refresh_interval'] = self.time_window_spin.value()
        
        return ui_data
    
    def _update_config_simple(self, ui_data):
        """Simple config update without extensive debugging."""
        # Validate config exists and has required attributes
        if not self.config:
            raise ValueError("Config is None")
        
        if not hasattr(self.config, 'stations') or not self.config.stations:
            raise ValueError("Config stations is None or missing")
            
        if not hasattr(self.config, 'display') or not self.config.display:
            raise ValueError("Config display is None or missing")
        
        # Update station config
        self.config.stations.from_name = ui_data['departure_station']
        self.config.stations.to_name = ui_data['arrival_station']
        self.config.stations.via_stations = ui_data['via_stations']
        self.config.stations.departure_time = ui_data['departure_time']
        self.config.stations.route_auto_fixed = ui_data['route_auto_fixed']
        
        # Get station codes
        if ui_data['departure_station']:
            self.config.stations.from_code = self.api_get_station_code(ui_data['departure_station']) or ''
        if ui_data['arrival_station']:
            self.config.stations.to_code = self.api_get_station_code(ui_data['arrival_station']) or ''
        
        # Update display config
        self.config.display.max_trains = ui_data['max_results']
        self.config.display.time_window_hours = ui_data['refresh_interval']
    
    def _ui_safe_close_with_parent_restore(self, parent_window, parent_visible_before, parent_active_before):
        """Safely close dialog while ensuring parent window remains visible and active."""
        # print("🔍 Starting UI-safe close with parent restoration...")
        
        try:
            # Step 1: Close the dialog first
            # print("🔍 Closing dialog...")
            self.accept()
            print("✅ Dialog closed")
            
            # Step 2: Restore parent window state
            if parent_window:
                # print("🔍 Restoring parent window state...")
                
                try:
                    # Ensure parent is visible
                    if parent_visible_before and hasattr(parent_window, 'isVisible') and hasattr(parent_window, 'show'):
                        if not getattr(parent_window, 'isVisible')():
                            # print("🔍 Making parent window visible...")
                            getattr(parent_window, 'show')()
                    
                    # Ensure parent is not minimized
                    if hasattr(parent_window, 'isMinimized') and hasattr(parent_window, 'showNormal'):
                        if getattr(parent_window, 'isMinimized')():
                            # print("🔍 Restoring parent window from minimized state...")
                            getattr(parent_window, 'showNormal')()
                    
                    # Bring parent to front and activate
                    # print("🔍 Bringing parent window to front...")
                    if hasattr(parent_window, 'raise_'):
                        getattr(parent_window, 'raise_')()
                    if hasattr(parent_window, 'activateWindow'):
                        getattr(parent_window, 'activateWindow')()
                    
                    # Force focus to parent
                    if hasattr(parent_window, 'setFocus'):
                        getattr(parent_window, 'setFocus')()
                    
                    print("✅ Parent window state restored")
                    
                    # Verify final state
                    if hasattr(parent_window, 'isVisible'):
                        # print(f"🔍 Final parent visible: {getattr(parent_window, 'isVisible')()}")
                        pass
                    if hasattr(parent_window, 'isActiveWindow'):
                        # print(f"🔍 Final parent active: {getattr(parent_window, 'isActiveWindow')()}")
                        pass
                    if hasattr(parent_window, 'isMinimized'):
                        # print(f"🔍 Final parent minimized: {getattr(parent_window, 'isMinimized')()}")
                        pass
                    
                except Exception as restore_error:
                    print(f"⚠️ Error restoring parent window: {restore_error}")
            else:
                print("⚠️ No parent window to restore")
                
        except Exception as e:
            print(f"❌ Error in UI-safe close: {e}")
            # Fallback - just try to close
            try:
                self.close()
            except:
                pass
    
    def _ultra_debug_validate_config(self):
        """Ultra debug config validation with maximum safety."""
        try:
            # print("🔍 Ultra debug config validation starting...")
            
            if self.config is None:
                print("❌ self.config is None")
                return False
            
            print(f"✅ self.config exists: {type(self.config)}")
            
            # Check each required attribute
            required_attrs = ['stations', 'display', 'refresh']
            for attr in required_attrs:
                if not hasattr(self.config, attr):
                    print(f"❌ config.{attr} missing")
                    return False
                
                attr_value = getattr(self.config, attr)
                if attr_value is None:
                    print(f"❌ config.{attr} is None")
                    return False
                
                print(f"✅ config.{attr} exists: {type(attr_value)}")
            
            print("✅ Ultra debug config validation passed")
            return True
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR in ultra debug config validation: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _ultra_debug_collect_ui_data(self):
        """Ultra debug UI data collection with maximum safety."""
        try:
            # print("🔍 Ultra debug UI data collection starting...")
            return self._extensive_debug_collect_ui_data()
        except Exception as e:
            print(f"❌ CRITICAL ERROR in ultra debug UI data collection: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _ultra_debug_update_config(self, ui_data):
        """Ultra debug config update with maximum safety."""
        try:
            # print("🔍 Ultra debug config update starting...")
            return self._extensive_debug_update_config(ui_data)
        except Exception as e:
            print(f"❌ CRITICAL ERROR in ultra debug config update: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _ultra_debug_save_config(self):
        """Ultra debug config save with maximum safety."""
        try:
            # print("🔍 Ultra debug config save starting...")
            return self._extensive_debug_save_config()
        except Exception as e:
            print(f"❌ CRITICAL ERROR in ultra debug config save: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _ultra_debug_emit_signal_with_monitoring(self):
        """Ultra debug signal emission with crash monitoring."""
        import time
        
        try:
            # print("🔍 Pre-signal emission state check...")
            print(f"   Dialog still exists: {self is not None}")
            print(f"   Dialog visible: {self.isVisible()}")
            print(f"   Settings saved signal exists: {hasattr(self, 'settings_saved')}")
            
            if hasattr(self, 'settings_saved') and self.settings_saved:
                # print("🔍 About to emit settings_saved signal...")
                
                # Emit signal with monitoring
                self.settings_saved.emit()
                
                print("✅ Signal emitted successfully")
                
                # Wait a moment and check state
                time.sleep(0.1)
                # print("🔍 Post-signal emission state check...")
                print(f"   Dialog still exists: {self is not None}")
                print(f"   Dialog visible: {self.isVisible()}")
                
            else:
                print("⚠ No settings_saved signal to emit")
                
        except Exception as e:
            print(f"❌ CRASH in signal emission: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _ultra_debug_force_close_with_monitoring(self):
        """Ultra debug dialog close with crash monitoring."""
        import time
        
        try:
            # print("🔍 Pre-close state check...")
            print(f"   Dialog still exists: {self is not None}")
            print(f"   Dialog visible: {self.isVisible()}")
            print(f"   Dialog parent: {self.parent()}")
            
            # Try accept() with monitoring
            # print("🔍 Attempting accept()...")
            self.accept()
            
            print("✅ accept() completed")
            
            # Wait a moment and check state
            time.sleep(0.1)
            # print("🔍 Post-close state check...")
            print(f"   Dialog still exists: {self is not None}")
            try:
                print(f"   Dialog visible: {self.isVisible()}")
            except Exception as visibility_error:
                print(f"   Dialog visibility check failed (expected): {visibility_error}")
            
        except Exception as e:
            print(f"❌ CRASH in dialog close: {e}")
            import traceback
            traceback.print_exc()
            
            # Try alternative close methods
            # print("🔍 Trying alternative close methods...")
            try:
                self.reject()
                print("✅ reject() succeeded")
            except Exception as reject_error:
                print(f"❌ reject() failed: {reject_error}")
                try:
                    self.close()
                    print("✅ close() succeeded")
                except Exception as close_error:
                    print(f"❌ close() failed: {close_error}")
                    try:
                        self.hide()
                        print("✅ hide() succeeded")
                    except Exception as hide_error:
                        print(f"❌ hide() failed: {hide_error}")
    
    def _ultra_debug_show_error_and_close(self, message):
        """Show error message and close dialog safely."""
        try:
            # print(f"🔍 Showing error message: {message}")
            QMessageBox.critical(self, "Error", f"{message}. Dialog will close.")
            print("✅ Error message shown")
        except Exception as msg_error:
            print(f"❌ Error showing message: {msg_error}")
        
        try:
            # print("🔍 Closing dialog after error...")
            self._ultra_debug_force_close_with_monitoring()
        except Exception as close_error:
            print(f"❌ Error closing dialog: {close_error}")
    
    def _extensive_debug_collect_ui_data(self):
        """Extensive debug version of UI data collection with maximum logging."""
        import traceback
        
        # print("🔍 Starting extensive debug UI data collection...")
        ui_data = {
            'from_name': '',
            'to_name': '',
            'departure_time': '',
            'from_code': '',
            'to_code': '',
            'via_stations': [],
            'route_auto_fixed': False,
            'max_trains': 50,
            'time_window': 16
        }
        
        # Collect from_name with extensive debugging
        # print("🔍 Collecting from_name...")
        try:
            print(f"   hasattr(self, 'from_name_edit'): {hasattr(self, 'from_name_edit')}")
            if hasattr(self, 'from_name_edit'):
                print(f"   self.from_name_edit is not None: {self.from_name_edit is not None}")
                if self.from_name_edit:
                    print(f"   hasattr(self.from_name_edit, 'text'): {hasattr(self.from_name_edit, 'text')}")
                    if hasattr(self.from_name_edit, 'text'):
                        raw_text = self.from_name_edit.text()
                        print(f"   raw text: {repr(raw_text)}")
                        ui_data['from_name'] = str(raw_text).strip()
                        print(f"   ✅ from_name: '{ui_data['from_name']}'")
                    else:
                        print("   ❌ from_name_edit has no text() method")
                else:
                    print("   ❌ from_name_edit is None")
            else:
                print("   ❌ No from_name_edit attribute")
        except Exception as e:
            print(f"   ❌ Error collecting from_name: {e}")
            traceback.print_exc()
        
        # Collect to_name with extensive debugging
        # print("🔍 Collecting to_name...")
        try:
            print(f"   hasattr(self, 'to_name_edit'): {hasattr(self, 'to_name_edit')}")
            if hasattr(self, 'to_name_edit'):
                print(f"   self.to_name_edit is not None: {self.to_name_edit is not None}")
                if self.to_name_edit:
                    print(f"   hasattr(self.to_name_edit, 'text'): {hasattr(self.to_name_edit, 'text')}")
                    if hasattr(self.to_name_edit, 'text'):
                        raw_text = self.to_name_edit.text()
                        print(f"   raw text: {repr(raw_text)}")
                        ui_data['to_name'] = str(raw_text).strip()
                        print(f"   ✅ to_name: '{ui_data['to_name']}'")
                    else:
                        print("   ❌ to_name_edit has no text() method")
                else:
                    print("   ❌ to_name_edit is None")
            else:
                print("   ❌ No to_name_edit attribute")
        except Exception as e:
            print(f"   ❌ Error collecting to_name: {e}")
            traceback.print_exc()
        
        # Collect departure_time with extensive debugging
        # print("🔍 Collecting departure_time...")
        try:
            print(f"   hasattr(self, 'departure_time_picker'): {hasattr(self, 'departure_time_picker')}")
            if hasattr(self, 'departure_time_picker'):
                print(f"   self.departure_time_picker is not None: {self.departure_time_picker is not None}")
                if self.departure_time_picker:
                    print(f"   True: {True}")
                    if True:
                        raw_text = self.departure_time_picker.get_time()
                        print(f"   raw text: {repr(raw_text)}")
                        ui_data['departure_time'] = str(raw_text).strip()
                        print(f"   ✅ departure_time: '{ui_data['departure_time']}'")
                    else:
                        print("   ❌ departure_time_edit has no text() method")
                else:
                    print("   ❌ departure_time_edit is None")
            else:
                print("   ❌ No departure_time_edit attribute")
        except Exception as e:
            print(f"   ❌ Error collecting departure_time: {e}")
            traceback.print_exc()
        
        # Get station codes with extensive debugging
        # print("🔍 Getting station codes...")
        try:
            if ui_data['from_name']:
                print(f"   Getting code for from_name: '{ui_data['from_name']}'")
                print(f"   hasattr(self, 'api_get_station_code'): {hasattr(self, 'api_get_station_code')}")
                if hasattr(self, 'api_get_station_code'):
                    code_result = self.api_get_station_code(ui_data['from_name'])
                    print(f"   api_get_station_code result: {repr(code_result)}")
                    ui_data['from_code'] = str(code_result) if code_result else ''
                    print(f"   ✅ from_code: '{ui_data['from_code']}'")
                else:
                    print("   ❌ No api_get_station_code method")
            else:
                print("   ⚠ Skipping from_code - no from_name")
        except Exception as e:
            print(f"   ❌ Error getting from_code: {e}")
            traceback.print_exc()
        
        try:
            if ui_data['to_name']:
                print(f"   Getting code for to_name: '{ui_data['to_name']}'")
                code_result = self.api_get_station_code(ui_data['to_name'])
                print(f"   api_get_station_code result: {repr(code_result)}")
                ui_data['to_code'] = str(code_result) if code_result else ''
                print(f"   ✅ to_code: '{ui_data['to_code']}'")
            else:
                print("   ⚠ Skipping to_code - no to_name")
        except Exception as e:
            print(f"   ❌ Error getting to_code: {e}")
            traceback.print_exc()
        
        # Collect via_stations with extensive debugging
        # print("🔍 Collecting via_stations...")
        try:
            print(f"   hasattr(self, 'via_stations'): {hasattr(self, 'via_stations')}")
            if hasattr(self, 'via_stations'):
                via_stations_raw = self.via_stations
                print(f"   via_stations type: {type(via_stations_raw)}")
                print(f"   via_stations value: {repr(via_stations_raw)}")
                if isinstance(via_stations_raw, list):
                    ui_data['via_stations'] = [str(station) for station in via_stations_raw if station]
                    print(f"   ✅ via_stations: {ui_data['via_stations']}")
                else:
                    print(f"   ❌ via_stations is not a list: {type(via_stations_raw)}")
            else:
                print("   ❌ No via_stations attribute")
        except Exception as e:
            print(f"   ❌ Error collecting via_stations: {e}")
            traceback.print_exc()
        
        # Collect route_auto_fixed with extensive debugging
        # print("🔍 Collecting route_auto_fixed...")
        try:
            print(f"   hasattr(self, 'route_auto_fixed'): {hasattr(self, 'route_auto_fixed')}")
            if hasattr(self, 'route_auto_fixed'):
                route_auto_fixed_raw = self.route_auto_fixed
                print(f"   route_auto_fixed type: {type(route_auto_fixed_raw)}")
                print(f"   route_auto_fixed value: {repr(route_auto_fixed_raw)}")
                ui_data['route_auto_fixed'] = bool(route_auto_fixed_raw)
                print(f"   ✅ route_auto_fixed: {ui_data['route_auto_fixed']}")
            else:
                print("   ❌ No route_auto_fixed attribute")
        except Exception as e:
            print(f"   ❌ Error collecting route_auto_fixed: {e}")
            traceback.print_exc()
        
        # Collect display settings with extensive debugging
        # print("🔍 Collecting max_trains...")
        try:
            print(f"   hasattr(self, 'max_trains_spin'): {hasattr(self, 'max_trains_spin')}")
            if hasattr(self, 'max_trains_spin'):
                print(f"   self.max_trains_spin is not None: {self.max_trains_spin is not None}")
                if self.max_trains_spin:
                    print(f"   hasattr(self.max_trains_spin, 'value'): {hasattr(self.max_trains_spin, 'value')}")
                    if hasattr(self.max_trains_spin, 'value'):
                        value_raw = self.max_trains_spin.value()
                        print(f"   value() result: {repr(value_raw)}")
                        ui_data['max_trains'] = int(value_raw)
                        print(f"   ✅ max_trains: {ui_data['max_trains']}")
                    else:
                        print("   ❌ max_trains_spin has no value() method")
                else:
                    print("   ❌ max_trains_spin is None")
            else:
                print("   ❌ No max_trains_spin attribute")
        except Exception as e:
            print(f"   ❌ Error collecting max_trains: {e}")
            traceback.print_exc()
        
        # print("🔍 Collecting time_window...")
        try:
            print(f"   hasattr(self, 'time_window_spin'): {hasattr(self, 'time_window_spin')}")
            if hasattr(self, 'time_window_spin'):
                print(f"   self.time_window_spin is not None: {self.time_window_spin is not None}")
                if self.time_window_spin:
                    print(f"   hasattr(self.time_window_spin, 'value'): {hasattr(self.time_window_spin, 'value')}")
                    if hasattr(self.time_window_spin, 'value'):
                        value_raw = self.time_window_spin.value()
                        print(f"   value() result: {repr(value_raw)}")
                        ui_data['time_window'] = int(value_raw)
                        print(f"   ✅ time_window: {ui_data['time_window']}")
                    else:
                        print("   ❌ time_window_spin has no value() method")
                else:
                    print("   ❌ time_window_spin is None")
            else:
                print("   ❌ No time_window_spin attribute")
        except Exception as e:
            print(f"   ❌ Error collecting time_window: {e}")
            traceback.print_exc()
        
        print("✅ Extensive debug UI data collection completed")
        return ui_data
    
    def _extensive_debug_update_config(self, ui_data):
        """Extensive debug version of config update with maximum logging."""
        import traceback
        
        # print("🔍 Starting extensive debug config update...")
        
        try:
            config = self.config
            # print(f"🔍 Config object: {config}")
            # print(f"🔍 Config type: {type(config)}")
            
            if not config:
                print("❌ Config is None - cannot update")
                return False
            
            # Update station settings with extensive debugging
            # print("🔍 Updating station settings...")
            try:
                print(f"   hasattr(config, 'stations'): {hasattr(config, 'stations')}")
                if hasattr(config, 'stations'):
                    stations = config.stations
                    print(f"   stations object: {stations}")
                    print(f"   stations type: {type(stations)}")
                    
                    if stations:
                        print("   Setting from_code...")
                        stations.from_code = ui_data['from_code']
                        print(f"   ✅ from_code set to: {repr(stations.from_code)}")
                        
                        print("   Setting from_name...")
                        stations.from_name = ui_data['from_name']
                        print(f"   ✅ from_name set to: {repr(stations.from_name)}")
                        
                        print("   Setting to_code...")
                        stations.to_code = ui_data['to_code']
                        print(f"   ✅ to_code set to: {repr(stations.to_code)}")
                        
                        print("   Setting to_name...")
                        stations.to_name = ui_data['to_name']
                        print(f"   ✅ to_name set to: {repr(stations.to_name)}")
                        
                        print("   Setting via_stations...")
                        stations.via_stations = ui_data['via_stations']
                        print(f"   ✅ via_stations set to: {repr(stations.via_stations)}")
                        
                        print("   Setting route_auto_fixed...")
                        stations.route_auto_fixed = ui_data['route_auto_fixed']
                        print(f"   ✅ route_auto_fixed set to: {repr(stations.route_auto_fixed)}")
                        
                        print("   Setting departure_time...")
                        stations.departure_time = ui_data['departure_time']
                        print(f"   ✅ departure_time set to: {repr(stations.departure_time)}")
                        
                        print("   ✅ Station config updated successfully")
                    else:
                        print("   ❌ stations object is None")
                else:
                    print("   ❌ config has no stations attribute")
            except Exception as e:
                print(f"   ❌ Error updating station config: {e}")
                traceback.print_exc()
            
            # Update display settings with extensive debugging
            # print("🔍 Updating display settings...")
            try:
                print(f"   hasattr(config, 'display'): {hasattr(config, 'display')}")
                if hasattr(config, 'display'):
                    display = config.display
                    print(f"   display object: {display}")
                    print(f"   display type: {type(display)}")
                    
                    if display:
                        print("   Setting max_trains...")
                        display.max_trains = ui_data['max_trains']
                        print(f"   ✅ max_trains set to: {repr(display.max_trains)}")
                        
                        print("   Setting time_window_hours...")
                        display.time_window_hours = ui_data['time_window']
                        print(f"   ✅ time_window_hours set to: {repr(display.time_window_hours)}")
                        
                        print("   ✅ Display config updated successfully")
                    else:
                        print("   ❌ display object is None")
                else:
                    print("   ❌ config has no display attribute")
            except Exception as e:
                print(f"   ❌ Error updating display config: {e}")
                traceback.print_exc()
            
            # Update refresh settings with extensive debugging
            # print("🔍 Updating refresh settings...")
            try:
                print(f"   hasattr(config, 'refresh'): {hasattr(config, 'refresh')}")
                if hasattr(config, 'refresh'):
                    refresh = config.refresh
                    print(f"   refresh object: {refresh}")
                    print(f"   refresh type: {type(refresh)}")
                    
                    if refresh:
                        print("   Setting auto_enabled...")
                        refresh.auto_enabled = False
                        print(f"   ✅ auto_enabled set to: {repr(refresh.auto_enabled)}")
                        
                        print("   Setting interval_minutes...")
                        refresh.interval_minutes = 30
                        print(f"   ✅ interval_minutes set to: {repr(refresh.interval_minutes)}")
                        
                        print("   Setting manual_enabled...")
                        refresh.manual_enabled = True
                        print(f"   ✅ manual_enabled set to: {repr(refresh.manual_enabled)}")
                        
                        print("   ✅ Refresh config updated successfully")
                    else:
                        print("   ❌ refresh object is None")
                else:
                    print("   ❌ config has no refresh attribute")
            except Exception as e:
                print(f"   ❌ Error updating refresh config: {e}")
                traceback.print_exc()
            
            print("✅ Extensive debug config update completed")
            return True
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR in extensive debug config update: {e}")
            traceback.print_exc()
            return False
    
    def _extensive_debug_save_config(self):
        """Extensive debug version of config save with maximum logging."""
        import traceback
        
        # print("🔍 Starting extensive debug config save...")
        
        try:
            # print(f"🔍 hasattr(self, 'config_manager'): {hasattr(self, 'config_manager')}")
            if not hasattr(self, 'config_manager'):
                print("❌ No config_manager attribute")
                return False
            
            config_manager = self.config_manager
            # print(f"🔍 config_manager: {config_manager}")
            # print(f"🔍 config_manager type: {type(config_manager)}")
            
            if not config_manager:
                print("❌ config_manager is None")
                return False
            
            # print(f"🔍 hasattr(config_manager, 'save_config'): {hasattr(config_manager, 'save_config')}")
            if not hasattr(config_manager, 'save_config'):
                print("❌ config_manager has no save_config method")
                return False
            
            config = self.config
            # print(f"🔍 config for save: {config}")
            # print(f"🔍 config type: {type(config)}")
            
            if not config:
                print("❌ config is None - cannot save")
                return False
            
            # print("🔍 Calling config_manager.save_config(config)...")
            config_manager.save_config(config)
            print("✅ config_manager.save_config() completed successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR in extensive debug config save: {e}")
            traceback.print_exc()
            
            # Show error but don't crash
            try:
                # print("🔍 Attempting to show save warning dialog...")
                QMessageBox.warning(self, "Save Warning", f"Settings may not have been saved properly: {e}")
                print("✅ Save warning dialog shown successfully")
            except Exception as msg_error:
                print(f"❌ Error showing save warning dialog: {msg_error}")
                traceback.print_exc()
            
            return False
    
    def _extensive_debug_emit_signal(self):
        """Extensive debug version of signal emission with maximum logging."""
        import traceback
        
        # print("🔍 Starting extensive debug signal emission...")
        
        try:
            # print(f"🔍 hasattr(self, 'settings_saved'): {hasattr(self, 'settings_saved')}")
            if not hasattr(self, 'settings_saved'):
                print("❌ No settings_saved attribute")
                return
            
            settings_saved = self.settings_saved
            # print(f"🔍 settings_saved: {settings_saved}")
            # print(f"🔍 settings_saved type: {type(settings_saved)}")
            
            if not settings_saved:
                print("❌ settings_saved is None")
                return
            
            # print(f"🔍 hasattr(settings_saved, 'emit'): {hasattr(settings_saved, 'emit')}")
            if not hasattr(settings_saved, 'emit'):
                print("❌ settings_saved has no emit method")
                return
            
            # print("🔍 Calling settings_saved.emit()...")
            settings_saved.emit()
            print("✅ settings_saved.emit() completed successfully")
            
        except Exception as e:
            print(f"❌ ERROR in extensive debug signal emission (non-critical): {e}")
            traceback.print_exc()
    
    def _extensive_debug_force_close(self):
        """Extensive debug version of dialog close with maximum logging."""
        import traceback
        
        # print("🔍 Starting extensive debug force close...")
        
        # Method 1: Try normal accept()
        # print("🔍 Attempting accept()...")
        try:
            print(f"   hasattr(self, 'accept'): {hasattr(self, 'accept')}")
            if hasattr(self, 'accept'):
                print("   Calling self.accept()...")
                self.accept()
                print("   ✅ Dialog closed with accept()")
                return
            else:
                print("   ❌ No accept method")
        except Exception as e:
            print(f"   ❌ accept() failed: {e}")
            traceback.print_exc()
        
        # Method 2: Try reject()
        # print("🔍 Attempting reject()...")
        try:
            print(f"   hasattr(self, 'reject'): {hasattr(self, 'reject')}")
            if hasattr(self, 'reject'):
                print("   Calling self.reject()...")
                self.reject()
                print("   ✅ Dialog closed with reject()")
                return
            else:
                print("   ❌ No reject method")
        except Exception as e:
            print(f"   ❌ reject() failed: {e}")
            traceback.print_exc()
        
        # Method 3: Try close()
        # print("🔍 Attempting close()...")
        try:
            print(f"   hasattr(self, 'close'): {hasattr(self, 'close')}")
            if hasattr(self, 'close'):
                print("   Calling self.close()...")
                self.close()
                print("   ✅ Dialog closed with close()")
                return
            else:
                print("   ❌ No close method")
        except Exception as e:
            print(f"   ❌ close() failed: {e}")
            traceback.print_exc()
        
        # Method 4: Try hide()
        # print("🔍 Attempting hide()...")
        try:
            print(f"   hasattr(self, 'hide'): {hasattr(self, 'hide')}")
            if hasattr(self, 'hide'):
                print("   Calling self.hide()...")
                self.hide()
                print("   ✅ Dialog hidden with hide()")
                return
            else:
                print("   ❌ No hide method")
        except Exception as e:
            print(f"   ❌ hide() failed: {e}")
            traceback.print_exc()
        
        # Method 5: Try setVisible(False)
        # print("🔍 Attempting setVisible(False)...")
        try:
            print(f"   hasattr(self, 'setVisible'): {hasattr(self, 'setVisible')}")
            if hasattr(self, 'setVisible'):
                print("   Calling self.setVisible(False)...")
                self.setVisible(False)
                print("   ✅ Dialog hidden with setVisible(False)")
                return
            else:
                print("   ❌ No setVisible method")
        except Exception as e:
            print(f"   ❌ setVisible(False) failed: {e}")
            traceback.print_exc()
        
        print("❌ ALL DIALOG CLOSE METHODS FAILED - THIS SHOULD NEVER HAPPEN")
    
    def _collect_ui_data_safely(self):
        """Safely collect data from UI elements with extensive error handling."""
        ui_data = {
            'from_name': '',
            'to_name': '',
            'departure_time': '',
            'from_code': '',
            'to_code': '',
            'via_stations': [],
            'route_auto_fixed': False,
            'max_trains': 50,
            'time_window': 16
        }
        
        # Collect from_name
        try:
            if hasattr(self, 'from_name_edit') and self.from_name_edit and hasattr(self.from_name_edit, 'text'):
                ui_data['from_name'] = str(self.from_name_edit.text()).strip()
                print(f"✓ from_name: '{ui_data['from_name']}'")
        except Exception as e:
            print(f"⚠ Error getting from_name: {e}")
        
        # Collect to_name
        try:
            if hasattr(self, 'to_name_edit') and self.to_name_edit and hasattr(self.to_name_edit, 'text'):
                ui_data['to_name'] = str(self.to_name_edit.text()).strip()
                print(f"✓ to_name: '{ui_data['to_name']}'")
        except Exception as e:
            print(f"⚠ Error getting to_name: {e}")
        
        # Collect departure_time
        try:
            if hasattr(self, 'departure_time_picker') and self.departure_time_picker and True:
                ui_data['departure_time'] = str(self.departure_time_picker.get_time()).strip()
                print(f"✓ departure_time: '{ui_data['departure_time']}'")
        except Exception as e:
            print(f"⚠ Error getting departure_time: {e}")
        
        # Get station codes safely
        try:
            if ui_data['from_name']:
                code_result = self.api_get_station_code(ui_data['from_name'])
                ui_data['from_code'] = str(code_result) if code_result else ''
                print(f"✓ from_code: '{ui_data['from_code']}'")
        except Exception as e:
            print(f"⚠ Error getting from_code: {e}")
        
        try:
            if ui_data['to_name']:
                code_result = self.api_get_station_code(ui_data['to_name'])
                ui_data['to_code'] = str(code_result) if code_result else ''
                print(f"✓ to_code: '{ui_data['to_code']}'")
        except Exception as e:
            print(f"⚠ Error getting to_code: {e}")
        
        # Collect via_stations
        try:
            if hasattr(self, 'via_stations') and isinstance(self.via_stations, list):
                ui_data['via_stations'] = [str(station) for station in self.via_stations if station]
                print(f"✓ via_stations: {ui_data['via_stations']}")
        except Exception as e:
            print(f"⚠ Error getting via_stations: {e}")
        
        # Collect route_auto_fixed
        try:
            if hasattr(self, 'route_auto_fixed'):
                ui_data['route_auto_fixed'] = bool(self.route_auto_fixed)
                print(f"✓ route_auto_fixed: {ui_data['route_auto_fixed']}")
        except Exception as e:
            print(f"⚠ Error getting route_auto_fixed: {e}")
        
        # Collect display settings
        try:
            if hasattr(self, 'max_trains_spin') and self.max_trains_spin and hasattr(self.max_trains_spin, 'value'):
                ui_data['max_trains'] = int(self.max_trains_spin.value())
                print(f"✓ max_trains: {ui_data['max_trains']}")
        except Exception as e:
            print(f"⚠ Error getting max_trains: {e}")
        
        try:
            if hasattr(self, 'time_window_spin') and self.time_window_spin and hasattr(self.time_window_spin, 'value'):
                ui_data['time_window'] = int(self.time_window_spin.value())
                print(f"✓ time_window: {ui_data['time_window']}")
        except Exception as e:
            print(f"⚠ Error getting time_window: {e}")
        
        return ui_data
    
    def _update_config_safely(self, ui_data):
        """Safely update configuration with collected UI data."""
        try:
            # At this point, config is guaranteed to be valid from earlier validation
            config = self.config
            if not config:
                print("❌ Config is None - should not happen after validation")
                return False
            
            # Update station settings
            if hasattr(config, 'stations') and config.stations:
                try:
                    config.stations.from_name = ui_data['from_name']
                    config.stations.to_name = ui_data['to_name']
                    config.stations.via_stations = ui_data['via_stations']
                    config.stations.route_auto_fixed = ui_data['route_auto_fixed']
                    config.stations.departure_time = ui_data['departure_time']
                    print("✓ Station config updated")
                except Exception as e:
                    print(f"⚠ Error updating station config: {e}")
            
            # Update display settings
            if hasattr(config, 'display') and config.display:
                try:
                    config.display.max_trains = ui_data['max_trains']
                    config.display.time_window_hours = ui_data['time_window']
                    print("✓ Display config updated")
                except Exception as e:
                    print(f"⚠ Error updating display config: {e}")
            
            # Update refresh settings with safe defaults
            if hasattr(config, 'refresh') and config.refresh:
                try:
                    config.refresh.auto_enabled = False
                    config.refresh.interval_minutes = 30
                    config.refresh.manual_enabled = True
                    print("✓ Refresh config updated")
                except Exception as e:
                    print(f"⚠ Error updating refresh config: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Critical error updating config: {e}")
            return False
    
    def _save_config_safely(self):
        """Safely save configuration to file."""
        try:
            # Validate config manager and config before saving
            if not (hasattr(self, 'config_manager') and self.config_manager and hasattr(self.config_manager, 'save_config')):
                print("❌ Config manager not available")
                return False
            
            config = self.config
            if not config:
                print("❌ Config is None - cannot save")
                return False
            
            self.config_manager.save_config(config)
            print("✅ Configuration saved successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            # Show error but don't crash
            try:
                QMessageBox.warning(self, "Save Warning", f"Settings may not have been saved properly: {e}")
            except Exception as msg_error:
                print(f"Error showing save warning: {msg_error}")
            return False
    
    def _emit_signal_safely(self):
        """Safely emit the settings_saved signal."""
        try:
            if hasattr(self, 'settings_saved') and self.settings_saved:
                self.settings_saved.emit()
                print("✓ Signal emitted successfully")
        except Exception as e:
            print(f"⚠ Error emitting signal (non-critical): {e}")
    
    def _force_close_dialog(self):
        """Force close the dialog using multiple fallback methods."""
        print("🔒 Force closing dialog...")
        
        # Method 1: Try normal accept()
        try:
            self.accept()
            print("✓ Dialog closed with accept()")
            return
        except Exception as e:
            print(f"⚠ accept() failed: {e}")
        
        # Method 2: Try reject()
        try:
            self.reject()
            print("✓ Dialog closed with reject()")
            return
        except Exception as e:
            print(f"⚠ reject() failed: {e}")
        
        # Method 3: Try close()
        try:
            self.close()
            print("✓ Dialog closed with close()")
            return
        except Exception as e:
            print(f"⚠ close() failed: {e}")
        
        # Method 4: Try hide()
        try:
            self.hide()
            print("✓ Dialog hidden with hide()")
            return
        except Exception as e:
            print(f"⚠ hide() failed: {e}")
        
        # Method 5: Try setVisible(False)
        try:
            self.setVisible(False)
            print("✓ Dialog hidden with setVisible(False)")
            return
        except Exception as e:
            print(f"⚠ setVisible(False) failed: {e}")
        
        print("❌ All dialog close methods failed - this should never happen")

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