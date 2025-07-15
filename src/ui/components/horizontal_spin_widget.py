"""
Horizontal Spin Widget for the Train Times application.

This module provides a horizontal spin control with left/right arrows and a value display,
extracted from the main settings dialog for better maintainability.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal


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