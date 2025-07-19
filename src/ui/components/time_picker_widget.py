"""
Time Picker Widget for the Train Times application.

This module provides a time picker widget with hour and minute spinners,
extracted from the main settings dialog for better maintainability.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal


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
        self.hour_down_button = QPushButton("⬅️")  # Left arrow emoji (matching style)
        self.hour_down_button.setFixedSize(40, 32)
        self.hour_down_button.clicked.connect(self.decrement_hour)

        self.hour_label = QLabel(f"{self._hour:02d}")
        self.hour_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hour_label.setMinimumWidth(30)
        self.hour_label.setFixedHeight(32)

        self.hour_up_button = QPushButton("➡️")  # Right arrow emoji (matching style)
        self.hour_up_button.setFixedSize(40, 32)
        self.hour_up_button.clicked.connect(self.increment_hour)

        # Colon separator
        colon_label = QLabel(":")
        colon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        colon_label.setFixedHeight(32)
        colon_label.setStyleSheet("font-weight: bold; font-size: 16px;")

        # Minute controls
        self.minute_down_button = QPushButton("⬅️")  # Left arrow emoji (matching style)
        self.minute_down_button.setFixedSize(40, 32)
        self.minute_down_button.clicked.connect(self.decrement_minute)

        self.minute_label = QLabel(f"{self._minute:02d}")
        self.minute_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minute_label.setMinimumWidth(30)
        self.minute_label.setFixedHeight(32)

        self.minute_up_button = QPushButton("➡️")  # Right arrow emoji (matching style)
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

        # Button styling with larger font for arrows
        button_style = f"""
            QPushButton {{
                background-color: {primary_accent};
                border: 1px solid {primary_accent};
                border-radius: 3px;
                font-weight: bold;
                font-size: 20px;
                color: #ffffff;
                padding: 2px;
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