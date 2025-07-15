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
        self.optimize_for_speed_radio = None
        self.optimize_for_changes_radio = None
        self.show_intermediate_checkbox = None
        self.avoid_london_checkbox = None
        self.prefer_direct_checkbox = None
        self.max_changes_spin = None
        self.max_journey_time_spin = None
        
        # Button group for radio buttons
        self.optimization_group = None
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("PreferencesWidget initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Route optimization preferences
        optimization_group = self._create_optimization_group()
        layout.addWidget(optimization_group)
        
        # Route preferences
        preferences_group = self._create_preferences_group()
        layout.addWidget(preferences_group)
        
        # Constraints
        constraints_group = self._create_constraints_group()
        layout.addWidget(constraints_group)
        
        # Add stretch
        layout.addStretch()
    
    def _create_optimization_group(self) -> QGroupBox:
        """Create the route optimization group box."""
        group = QGroupBox("Route Optimization")
        layout = QVBoxLayout(group)
        
        # Create button group for mutual exclusion
        self.optimization_group = QButtonGroup(self)
        
        # Optimization strategy
        self.optimize_for_speed_radio = QRadioButton("Optimize for speed (shortest journey time)")
        self.optimize_for_changes_radio = QRadioButton("Optimize for fewer changes")
        
        # Add to button group
        self.optimization_group.addButton(self.optimize_for_speed_radio, 0)
        self.optimization_group.addButton(self.optimize_for_changes_radio, 1)
        
        # Set default
        self.optimize_for_speed_radio.setChecked(True)
        
        layout.addWidget(self.optimize_for_speed_radio)
        layout.addWidget(self.optimize_for_changes_radio)
        
        return group
    
    def _create_preferences_group(self) -> QGroupBox:
        """Create the route preferences group box."""
        group = QGroupBox("Route Preferences")
        layout = QVBoxLayout(group)
        
        self.show_intermediate_checkbox = QCheckBox("Show intermediate stations in route")
        self.avoid_london_checkbox = QCheckBox("Avoid routes through London when possible")
        self.prefer_direct_checkbox = QCheckBox("Prefer direct routes over faster alternatives")
        
        # Set defaults
        self.show_intermediate_checkbox.setChecked(True)
        
        layout.addWidget(self.show_intermediate_checkbox)
        layout.addWidget(self.avoid_london_checkbox)
        layout.addWidget(self.prefer_direct_checkbox)
        
        return group
    
    def _create_constraints_group(self) -> QGroupBox:
        """Create the journey constraints group box."""
        group = QGroupBox("Journey Constraints")
        layout = QGridLayout(group)
        
        # Maximum changes
        layout.addWidget(QLabel("Maximum changes:"), 0, 0)
        self.max_changes_spin = HorizontalSpinWidget(0, 10, 3, theme_manager=self.theme_manager)
        layout.addWidget(self.max_changes_spin, 0, 1)
        
        # Maximum journey time
        layout.addWidget(QLabel("Maximum journey time (hours):"), 1, 0)
        self.max_journey_time_spin = HorizontalSpinWidget(1, 24, 8, theme_manager=self.theme_manager)
        layout.addWidget(self.max_journey_time_spin, 1, 1)
        
        return group
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Optimization radio buttons
        if self.optimization_group:
            self.optimization_group.buttonClicked.connect(self._on_preferences_changed)
        
        # Checkboxes
        if self.show_intermediate_checkbox:
            self.show_intermediate_checkbox.toggled.connect(self._on_preferences_changed)
        if self.avoid_london_checkbox:
            self.avoid_london_checkbox.toggled.connect(self._on_preferences_changed)
        if self.prefer_direct_checkbox:
            self.prefer_direct_checkbox.toggled.connect(self._on_preferences_changed)
        
        # Spin widgets
        if self.max_changes_spin:
            self.max_changes_spin.valueChanged.connect(self._on_preferences_changed)
        if self.max_journey_time_spin:
            self.max_journey_time_spin.valueChanged.connect(self._on_preferences_changed)
    
    def _on_preferences_changed(self):
        """Handle preferences change."""
        preferences = self.get_preferences()
        self.preferences_changed.emit(preferences)
        logger.debug(f"Preferences changed: {list(preferences.keys())}")
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get current preferences."""
        return {
            'optimize_for_speed': self.optimize_for_speed_radio.isChecked() if self.optimize_for_speed_radio else True,
            'show_intermediate_stations': self.show_intermediate_checkbox.isChecked() if self.show_intermediate_checkbox else True,
            'avoid_london': self.avoid_london_checkbox.isChecked() if self.avoid_london_checkbox else False,
            'prefer_direct': self.prefer_direct_checkbox.isChecked() if self.prefer_direct_checkbox else False,
            'max_changes': self.max_changes_spin.value() if self.max_changes_spin else 3,
            'max_journey_time': self.max_journey_time_spin.value() if self.max_journey_time_spin else 8
        }
    
    def set_preferences(self, preferences: Dict[str, Any]):
        """Set preferences from a dictionary."""
        try:
            # Optimization strategy
            if 'optimize_for_speed' in preferences:
                optimize_for_speed = preferences['optimize_for_speed']
                if self.optimize_for_speed_radio:
                    self.optimize_for_speed_radio.setChecked(optimize_for_speed)
                if self.optimize_for_changes_radio:
                    self.optimize_for_changes_radio.setChecked(not optimize_for_speed)
            
            # Checkboxes
            if 'show_intermediate_stations' in preferences and self.show_intermediate_checkbox:
                self.show_intermediate_checkbox.setChecked(preferences['show_intermediate_stations'])
            
            if 'avoid_london' in preferences and self.avoid_london_checkbox:
                self.avoid_london_checkbox.setChecked(preferences['avoid_london'])
            
            if 'prefer_direct' in preferences and self.prefer_direct_checkbox:
                self.prefer_direct_checkbox.setChecked(preferences['prefer_direct'])
            
            # Spin widgets
            if 'max_changes' in preferences and self.max_changes_spin:
                self.max_changes_spin.setValue(preferences['max_changes'])
            
            if 'max_journey_time' in preferences and self.max_journey_time_spin:
                self.max_journey_time_spin.setValue(preferences['max_journey_time'])
            
            logger.debug(f"Preferences set: {list(preferences.keys())}")
            
        except Exception as e:
            logger.error(f"Error setting preferences: {e}")
    
    def reset_to_defaults(self):
        """Reset all preferences to their default values."""
        defaults = {
            'optimize_for_speed': True,
            'show_intermediate_stations': True,
            'avoid_london': False,
            'prefer_direct': False,
            'max_changes': 3,
            'max_journey_time': 8
        }
        self.set_preferences(defaults)
        logger.debug("Preferences reset to defaults")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the widget."""
        if self.optimize_for_speed_radio:
            self.optimize_for_speed_radio.setEnabled(enabled)
        if self.optimize_for_changes_radio:
            self.optimize_for_changes_radio.setEnabled(enabled)
        if self.show_intermediate_checkbox:
            self.show_intermediate_checkbox.setEnabled(enabled)
        if self.avoid_london_checkbox:
            self.avoid_london_checkbox.setEnabled(enabled)
        if self.prefer_direct_checkbox:
            self.prefer_direct_checkbox.setEnabled(enabled)
        if self.max_changes_spin:
            self.max_changes_spin.setEnabled(enabled)
        if self.max_journey_time_spin:
            self.max_journey_time_spin.setEnabled(enabled)
    
    def apply_theme(self, theme_manager):
        """Apply theme to the widget."""
        self.theme_manager = theme_manager
        if theme_manager:
            try:
                theme_manager.apply_theme_to_widget(self)
            except Exception as e:
                logger.error(f"Error applying theme: {e}")