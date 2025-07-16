"""
Preferences Widget for the Train Settings Dialog.

This widget provides route optimization preferences and constraints
for the train settings dialog.
"""

import logging
from typing import Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox, QRadioButton, 
    QCheckBox, QLabel, QButtonGroup
)
from PySide6.QtCore import Signal

from .horizontal_spin_widget import HorizontalSpinWidget

logger = logging.getLogger(__name__)


class PreferencesWidget(QWidget):
    """Widget for route optimization preferences and constraints."""
    
    # Signals
    preferences_changed = Signal(dict)
    
    def __init__(self, parent=None, theme_manager=None):
        """
        Initialize the preferences widget.
        
        Args:
            parent: Parent widget
            theme_manager: Theme manager for styling
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        
        # UI elements
        self.show_intermediate_checkbox = None
        self.avoid_walking_checkbox = None
        self.max_walking_distance_spin = None
        self.max_walking_distance_label = None
        self.train_lookahead_hours_spin = None
        self.train_lookahead_hours_label = None
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("PreferencesWidget initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Route preferences
        preferences_group = self._create_preferences_group()
        layout.addWidget(preferences_group)
        
        # Add stretch
        layout.addStretch()
    
    def _create_preferences_group(self) -> QGroupBox:
        """Create the route preferences group box."""
        group = QGroupBox("Route Preferences")
        layout = QVBoxLayout(group)
        
        self.show_intermediate_checkbox = QCheckBox("Show intermediate stations in route")
        self.avoid_walking_checkbox = QCheckBox("Avoid walking between stations when possible")
        
        # Set defaults
        self.show_intermediate_checkbox.setChecked(True)
        
        layout.addWidget(self.show_intermediate_checkbox)
        layout.addWidget(self.avoid_walking_checkbox)
        
        # Add max walking distance configuration
        walking_layout = QGridLayout()
        self.max_walking_distance_label = QLabel("Maximum walking distance:")
        # Use integers for the spin widget (in meters) and convert to km for display
        self.max_walking_distance_spin = HorizontalSpinWidget(
            minimum=50,
            maximum=5000,
            initial_value=1000,
            step=50,
            suffix="m",
            parent=self,
            theme_manager=self.theme_manager
        )
        
        walking_layout.addWidget(self.max_walking_distance_label, 0, 0)
        walking_layout.addWidget(self.max_walking_distance_spin, 0, 1)
        layout.addLayout(walking_layout)
        
        # Add train look-ahead time configuration
        lookahead_layout = QGridLayout()
        self.train_lookahead_hours_label = QLabel("Train look-ahead time:")
        self.train_lookahead_hours_spin = HorizontalSpinWidget(
            minimum=1,
            maximum=48,
            initial_value=16,
            step=1,
            suffix="h",
            parent=self,
            theme_manager=self.theme_manager
        )
        
        lookahead_layout.addWidget(self.train_lookahead_hours_label, 0, 0)
        lookahead_layout.addWidget(self.train_lookahead_hours_spin, 0, 1)
        layout.addLayout(lookahead_layout)
        
        return group
    def _connect_signals(self):
        """Connect signals and slots."""
        # Checkboxes
        if self.show_intermediate_checkbox:
            self.show_intermediate_checkbox.toggled.connect(self._on_preferences_changed)
        if self.avoid_walking_checkbox:
            self.avoid_walking_checkbox.toggled.connect(self._on_preferences_changed)
            # Also connect to update visibility of max walking distance control
            self.avoid_walking_checkbox.toggled.connect(self._update_walking_distance_visibility)
        
        # Spin widgets
        if self.max_walking_distance_spin:
            self.max_walking_distance_spin.valueChanged.connect(self._on_preferences_changed)
        if self.train_lookahead_hours_spin:
            self.train_lookahead_hours_spin.valueChanged.connect(self._on_preferences_changed)
        
        # Initialize visibility
        self._update_walking_distance_visibility()
    
    def _update_walking_distance_visibility(self):
        """Update visibility of max walking distance control based on avoid_walking checkbox."""
        if self.avoid_walking_checkbox and self.max_walking_distance_label and self.max_walking_distance_spin:
            # Show walking distance controls when avoid_walking is NOT checked
            is_visible = not self.avoid_walking_checkbox.isChecked()
            self.max_walking_distance_label.setVisible(is_visible)
            self.max_walking_distance_spin.setVisible(is_visible)
        
    
    def _on_preferences_changed(self):
        """Handle preferences change."""
        preferences = self.get_preferences()
        self.preferences_changed.emit(preferences)
        logger.debug(f"Preferences changed: {list(preferences.keys())}")
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get current preferences."""
        # Get walking distance in km (convert from meters)
        walking_distance_km = self.max_walking_distance_spin.value() / 1000.0 if self.max_walking_distance_spin else 0.1
        
        # Get train look-ahead time in hours
        train_lookahead_hours = self.train_lookahead_hours_spin.value() if self.train_lookahead_hours_spin else 16
        
        return {
            'show_intermediate_stations': self.show_intermediate_checkbox.isChecked() if self.show_intermediate_checkbox else True,
            'avoid_walking': self.avoid_walking_checkbox.isChecked() if self.avoid_walking_checkbox else False,
            'max_walking_distance_km': walking_distance_km,
            'train_lookahead_hours': train_lookahead_hours,
        }
    
    def set_preferences(self, preferences: Dict[str, Any]):
        """Set preferences from a dictionary."""
        try:
            # Checkboxes
            if 'show_intermediate_stations' in preferences and self.show_intermediate_checkbox:
                self.show_intermediate_checkbox.setChecked(preferences['show_intermediate_stations'])
                
            if 'avoid_walking' in preferences and self.avoid_walking_checkbox:
                self.avoid_walking_checkbox.setChecked(preferences['avoid_walking'])
            
            if 'max_walking_distance_km' in preferences and self.max_walking_distance_spin:
                # Convert km to meters for the spin widget
                meters = int(preferences['max_walking_distance_km'] * 1000)
                self.max_walking_distance_spin.setValue(meters)
            
            if 'train_lookahead_hours' in preferences and self.train_lookahead_hours_spin:
                self.train_lookahead_hours_spin.setValue(preferences['train_lookahead_hours'])
            
            # Update visibility based on avoid_walking setting
            self._update_walking_distance_visibility()
            
            logger.debug(f"Preferences set: {list(preferences.keys())}")
            
        except Exception as e:
            logger.error(f"Error setting preferences: {e}")
    
    def reset_to_defaults(self):
        """Reset all preferences to their default values."""
        defaults = {
            'show_intermediate_stations': True,
            'avoid_walking': False,
            'max_walking_distance_km': 1.0,
            'train_lookahead_hours': 16,
        }
        self.set_preferences(defaults)
        logger.debug("Preferences reset to defaults")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the widget."""
        if self.show_intermediate_checkbox:
            self.show_intermediate_checkbox.setEnabled(enabled)
        if self.avoid_walking_checkbox:
            self.avoid_walking_checkbox.setEnabled(enabled)
        if self.max_walking_distance_spin:
            self.max_walking_distance_spin.setEnabled(enabled)
        if self.max_walking_distance_label:
            self.max_walking_distance_label.setEnabled(enabled)
        if self.train_lookahead_hours_spin:
            self.train_lookahead_hours_spin.setEnabled(enabled)
        if self.train_lookahead_hours_label:
            self.train_lookahead_hours_label.setEnabled(enabled)
    
    def apply_theme(self, theme_manager):
        """Apply theme to the widget."""
        self.theme_manager = theme_manager
        if theme_manager:
            try:
                theme_manager.apply_theme_to_widget(self)
            except Exception as e:
                logger.error(f"Error applying theme: {e}")