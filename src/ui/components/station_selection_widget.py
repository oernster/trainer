"""
Station Selection Widget for the Train Settings Dialog.

This widget provides station selection functionality with autocomplete
and validation for from/to station selection.
"""

import logging
import sys
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QComboBox, QPushButton, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCompleter
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class StationSelectionWidget(QWidget):
    """Widget for selecting from and to stations with autocomplete."""
    
    # Signals
    from_station_changed = Signal(str)
    to_station_changed = Signal(str)
    stations_swapped = Signal(str, str)  # from_station, to_station
    
    def __init__(self, parent=None, theme_manager=None):
        """
        Initialize the station selection widget.
        
        Args:
            parent: Parent widget
            theme_manager: Theme manager for styling
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        
        # UI elements
        self.from_station_combo = None
        self.to_station_combo = None
        self.swap_button = None
        
        # Station data
        self.stations = []
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("StationSelectionWidget initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QGridLayout(self)
        
        # Platform-specific spacing
        if sys.platform.startswith('linux'):
            layout.setSpacing(5)  # Reduced from 10
            layout.setContentsMargins(5, 5, 5, 5)  # Add tight margins
        else:
            layout.setSpacing(10)
        
        # From station
        from_label = QLabel("From:")
        if sys.platform.startswith('linux'):
            from_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))  # Smaller font on Linux
        else:
            from_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(from_label, 0, 0)
        
        self.from_station_combo = QComboBox()
        self.from_station_combo.setEditable(True)
        self.from_station_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.from_station_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.from_station_combo.setMinimumWidth(200)
        
        # Ensure editability on Linux
        if sys.platform.startswith('linux'):
            # Set combo box style to ensure edit field is accessible
            self.from_station_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2d2d2d;
                    color: white;
                    border: 1px solid #555;
                    padding: 5px;
                    min-height: 30px;
                }
                QComboBox::drop-down {
                    width: 20px;
                    border-left: 1px solid #555;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid white;
                    margin-right: 5px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    color: white;
                    selection-background-color: #1976d2;
                }
            """)
            
            # Get the line edit component
            line_edit = self.from_station_combo.lineEdit()
            if line_edit:
                # Make sure it's not read-only
                line_edit.setReadOnly(False)
                line_edit.setEnabled(True)
                # Log for debugging
                logger.info(f"From station combo - Editable: {self.from_station_combo.isEditable()}, LineEdit ReadOnly: {line_edit.isReadOnly()}")
        
        layout.addWidget(self.from_station_combo, 0, 1)
        
        # To station
        to_label = QLabel("To:")
        if sys.platform.startswith('linux'):
            to_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))  # Smaller font on Linux
        else:
            to_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(to_label, 1, 0)
        
        self.to_station_combo = QComboBox()
        self.to_station_combo.setEditable(True)
        self.to_station_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.to_station_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.to_station_combo.setMinimumWidth(200)
        
        # Ensure editability on Linux
        if sys.platform.startswith('linux'):
            # Set combo box style to ensure edit field is accessible
            self.to_station_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2d2d2d;
                    color: white;
                    border: 1px solid #555;
                    padding: 5px;
                    min-height: 30px;
                }
                QComboBox::drop-down {
                    width: 20px;
                    border-left: 1px solid #555;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid white;
                    margin-right: 5px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    color: white;
                    selection-background-color: #1976d2;
                }
            """)
            
            # Get the line edit component
            line_edit = self.to_station_combo.lineEdit()
            if line_edit:
                # Make sure it's not read-only
                line_edit.setReadOnly(False)
                line_edit.setEnabled(True)
                # Log for debugging
                logger.info(f"To station combo - Editable: {self.to_station_combo.isEditable()}, LineEdit ReadOnly: {line_edit.isReadOnly()}")
        
        layout.addWidget(self.to_station_combo, 1, 1)
        
        # Swap button
        self.swap_button = QPushButton("⇅ Swap")
        
        # Platform-specific button sizing
        if sys.platform.startswith('linux'):
            # Detect small screen
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                is_small_screen = screen_geometry.width() <= 1440 or screen_geometry.height() <= 900
            else:
                is_small_screen = False
            
            if is_small_screen:
                self.swap_button.setMinimumWidth(100)  # Larger minimum width
                self.swap_button.setMinimumHeight(50)  # Taller button
                self.swap_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))  # Larger font
            else:
                self.swap_button.setMinimumWidth(90)
                self.swap_button.setMinimumHeight(45)
                self.swap_button.setFont(QFont("Arial", 10))
        else:
            self.swap_button.setMaximumWidth(80)
        
        self.swap_button.setToolTip("Swap From and To stations")
        self.swap_button.setObjectName("swapButton")
        layout.addWidget(self.swap_button, 0, 2, 2, 1)
    
    def _connect_signals(self):
        """Connect signals and slots."""
        if self.from_station_combo:
            self.from_station_combo.currentTextChanged.connect(self._on_from_station_changed)
        if self.to_station_combo:
            self.to_station_combo.currentTextChanged.connect(self._on_to_station_changed)
        if self.swap_button:
            self.swap_button.clicked.connect(self._swap_stations)
    
    def populate_stations(self, stations: List[str]):
        """
        Populate the station combo boxes with station names.
        
        Args:
            stations: List of station names
        """
        try:
            self.stations = sorted(stations) if stations else []
            
            # Clear existing items
            if self.from_station_combo:
                self.from_station_combo.clear()
                self.from_station_combo.addItems(self.stations)
                
                # Set up autocomplete
                from_completer = QCompleter(self.stations, self)
                from_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                from_completer.setFilterMode(Qt.MatchFlag.MatchContains)
                self.from_station_combo.setCompleter(from_completer)
            
            if self.to_station_combo:
                self.to_station_combo.clear()
                self.to_station_combo.addItems(self.stations)
                
                # Set up autocomplete
                to_completer = QCompleter(self.stations, self)
                to_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                to_completer.setFilterMode(Qt.MatchFlag.MatchContains)
                self.to_station_combo.setCompleter(to_completer)
            
            logger.debug(f"Populated station combos with {len(self.stations)} stations")
            
        except Exception as e:
            logger.error(f"Error populating stations: {e}")
    
    def set_from_station(self, station_name: str):
        """Set the from station."""
        if self.from_station_combo and station_name:
            index = self.from_station_combo.findText(station_name)
            if index >= 0:
                self.from_station_combo.setCurrentIndex(index)
            else:
                self.from_station_combo.setCurrentText(station_name)
    
    def set_to_station(self, station_name: str):
        """Set the to station."""
        if self.to_station_combo and station_name:
            index = self.to_station_combo.findText(station_name)
            if index >= 0:
                self.to_station_combo.setCurrentIndex(index)
            else:
                self.to_station_combo.setCurrentText(station_name)
    
    def get_from_station(self) -> str:
        """Get the current from station."""
        return self.from_station_combo.currentText() if self.from_station_combo else ""
    
    def get_to_station(self) -> str:
        """Get the current to station."""
        return self.to_station_combo.currentText() if self.to_station_combo else ""
    
    def clear_selections(self):
        """Clear both station selections."""
        if self.from_station_combo:
            self.from_station_combo.setCurrentText("")
        if self.to_station_combo:
            self.to_station_combo.setCurrentText("")
    
    def _on_from_station_changed(self, station_name: str):
        """Handle from station change."""
        self.from_station_changed.emit(station_name)
        logger.debug(f"From station changed: {station_name}")
    
    def _on_to_station_changed(self, station_name: str):
        """Handle to station change."""
        self.to_station_changed.emit(station_name)
        logger.debug(f"To station changed: {station_name}")
    
    def _swap_stations(self):
        """Swap from and to stations."""
        from_text = self.get_from_station()
        to_text = self.get_to_station()
        
        self.set_from_station(to_text)
        self.set_to_station(from_text)
        
        self.stations_swapped.emit(to_text, from_text)
        logger.debug(f"Stations swapped: {from_text} ↔ {to_text}")
    
    def validate_selection(self) -> tuple[bool, str]:
        """
        Validate the current station selection.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        from_station = self.get_from_station()
        to_station = self.get_to_station()
        
        if not from_station:
            return False, "Please select a From station"
        
        if not to_station:
            return False, "Please select a To station"
        
        if from_station == to_station:
            return False, "From and To stations must be different"
        
        # Check if stations exist in the list
        if from_station not in self.stations:
            return False, f"From station '{from_station}' is not valid"
        
        if to_station not in self.stations:
            return False, f"To station '{to_station}' is not valid"
        
        return True, ""
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the widget."""
        if self.from_station_combo:
            self.from_station_combo.setEnabled(enabled)
        if self.to_station_combo:
            self.to_station_combo.setEnabled(enabled)
        if self.swap_button:
            self.swap_button.setEnabled(enabled)
    
    def apply_theme(self, theme_manager):
        """Apply theme to the widget."""
        self.theme_manager = theme_manager
        if theme_manager:
            try:
                theme_manager.apply_theme_to_widget(self)
                # On Linux, ensure combo boxes remain editable after theme application
                if sys.platform.startswith('linux'):
                    self._ensure_linux_editability()
            except Exception as e:
                logger.error(f"Error applying theme: {e}")
    
    def _ensure_linux_editability(self):
        """Ensure combo boxes remain editable on Linux after theme changes."""
        for combo in [self.from_station_combo, self.to_station_combo]:
            if combo:
                # Re-enable editing
                combo.setEditable(True)
                line_edit = combo.lineEdit()
                if line_edit:
                    line_edit.setReadOnly(False)
                    line_edit.setEnabled(True)
                    # Force focus to be accepted
                    line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                    # Log the state
                    logger.info(f"Combo {combo.objectName() if combo.objectName() else 'unnamed'} - Editable: {combo.isEditable()}, LineEdit exists: {line_edit is not None}, ReadOnly: {line_edit.isReadOnly() if line_edit else 'N/A'}")