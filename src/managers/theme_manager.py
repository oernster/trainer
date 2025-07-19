"""
Theme management for the Train Times application.

This module handles switching between light and dark themes,
managing theme state, and providing theme-related utilities.
"""

from PySide6.QtCore import QObject, Signal


class ThemeManager(QObject):
    """
    Manages application themes and theme switching.

    Provides functionality to switch between light and dark themes,
    emit signals when themes change, and get theme-specific resources.
    """

    # Signal emitted when theme changes (theme_name: str)
    theme_changed = Signal(str)

    def __init__(self):
        """Initialize the theme manager with dark theme as default."""
        super().__init__()
        self.current_theme = "dark"  # Default to dark theme
        self._theme_colors = self._initialize_theme_colors()

    def _initialize_theme_colors(self) -> dict:
        """Initialize color palettes for both themes."""
        return {
            "dark": {
                # Background Colors
                "background_primary": "#1a1a1a",
                "background_secondary": "#2d2d2d",
                "background_tertiary": "#3d3d3d",
                "background_hover": "#404040",
                # Text Colors
                "text_primary": "#ffffff",
                "text_secondary": "#b0b0b0",
                "text_disabled": "#666666",
                "text_accent": "#1976d2",
                # Status Colors
                "success": "#4caf50",
                "warning": "#ff9800",
                "error": "#f44336",
                "info": "#2196f3",
                # Accent Colors
                "primary_accent": "#1976d2",
                "secondary_accent": "#81c784",
                "tertiary_accent": "#ffb74d",
                # Border Colors
                "border_primary": "#404040",
                "border_secondary": "#555555",
                "border_accent": "#1976d2",
            },
            "light": {
                # Background Colors
                "background_primary": "#ffffff",
                "background_secondary": "#f5f5f5",
                "background_tertiary": "#e0e0e0",
                "background_hover": "#eeeeee",
                # Text Colors
                "text_primary": "#212121",
                "text_secondary": "#757575",
                "text_disabled": "#bdbdbd",
                "text_accent": "#1976d2",
                # Status Colors
                "success": "#388e3c",
                "warning": "#f57c00",
                "error": "#d32f2f",
                "info": "#1976d2",
                # Accent Colors
                "primary_accent": "#1976d2",
                "secondary_accent": "#388e3c",
                "tertiary_accent": "#f57c00",
                # Border Colors
                "border_primary": "#e0e0e0",
                "border_secondary": "#bdbdbd",
                "border_accent": "#1976d2",
            },
        }

    def switch_theme(self) -> None:
        """Switch between light and dark themes."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.theme_changed.emit(self.current_theme)

    def set_theme(self, theme_name: str) -> None:
        """
        Set specific theme.

        Args:
            theme_name: Theme name ("dark" or "light")
        """
        if theme_name in ["dark", "light"] and theme_name != self.current_theme:
            self.current_theme = theme_name
            self.theme_changed.emit(self.current_theme)

    def get_theme_icon(self) -> str:
        """
        Get appropriate theme toggle icon.

        Returns:
            str: Unicode icon for theme toggle button
        """
        return "☀️" if self.current_theme == "dark" else "🌙"

    def get_theme_tooltip(self) -> str:
        """
        Get tooltip text for theme toggle button.

        Returns:
            str: Tooltip text
        """
        return (
            "Switch to Light Theme"
            if self.current_theme == "dark"
            else "Switch to Dark Theme"
        )

    def get_color(self, color_key: str) -> str:
        """
        Get color value for current theme.

        Args:
            color_key: Color key from theme palette

        Returns:
            str: Color value (hex code)
        """
        return self._theme_colors[self.current_theme].get(color_key, "#000000")

    def get_colors_for_theme(self, theme_name: str) -> dict:
        """
        Get all colors for a specific theme.

        Args:
            theme_name: Theme name ("dark" or "light")

        Returns:
            dict: Color palette for the theme
        """
        return self._theme_colors.get(theme_name, self._theme_colors["dark"])

    def get_current_colors(self) -> dict:
        """
        Get all colors for current theme.

        Returns:
            dict: Current theme color palette
        """
        return self._theme_colors[self.current_theme]

    def is_dark_theme(self) -> bool:
        """
        Check if current theme is dark.

        Returns:
            bool: True if dark theme is active
        """
        return self.current_theme == "dark"

    def is_light_theme(self) -> bool:
        """
        Check if current theme is light.

        Returns:
            bool: True if light theme is active
        """
        return self.current_theme == "light"

    def get_status_color(self, status: str) -> str:
        """
        Get status color for current theme.

        Args:
            status: Status type ("success", "warning", "error", "info")

        Returns:
            str: Color value for the status
        """
        status_map = {
            "on_time": "success",
            "delayed": "warning",
            "cancelled": "error",
            "unknown": "text_disabled",
        }

        color_key = status_map.get(status, status)
        return self.get_color(color_key)

    def get_main_window_stylesheet(self) -> str:
        """
        Get main window stylesheet for current theme.

        Returns:
            str: CSS stylesheet for main window
        """
        colors = self.get_current_colors()

        return f"""
        QMainWindow {{
            background-color: {colors['background_primary']};
            color: {colors['text_primary']};
        }}
        
        QMainWindow::separator {{
            background-color: {colors['border_primary']};
            width: 1px;
            height: 1px;
        }}
        
        QMenuBar {{
            background-color: {colors['background_secondary']};
            color: {colors['text_primary']};
            border-bottom: 1px solid {colors['border_primary']};
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors['background_hover']};
        }}
        
        QStatusBar {{
            background-color: {colors['background_secondary']};
            color: {colors['text_secondary']};
            border-top: 1px solid {colors['border_primary']};
        }}
        """

    def get_widget_stylesheet(self) -> str:
        """
        Get general widget stylesheet for current theme.

        Returns:
            str: CSS stylesheet for widgets
        """
        colors = self.get_current_colors()

        return f"""
        QWidget {{
            background-color: {colors['background_secondary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_primary']};
            border-radius: 8px;
            padding: 12px;
            margin: 8px;
        }}
        
        QLabel {{
            color: {colors['text_primary']};
            font-size: 12px;
            font-weight: 500;
            border: none;
            margin: 0px;
            padding: 0px;
        }}
        
        QPushButton {{
            background-color: {colors['primary_accent']};
            color: {colors['text_primary']};
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            margin: 2px;
        }}
        
        QPushButton:hover {{
            background-color: {colors['background_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['border_accent']};
        }}
        
        QScrollArea {{
            border: 1px solid {colors['border_primary']};
            border-radius: 8px;
            background-color: {colors['background_primary']};
        }}
        
        QScrollBar:vertical {{
            background-color: {colors['background_secondary']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors['border_secondary']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['text_secondary']};
        }}
        
        QComboBox {{
            background-color: {colors['background_secondary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_primary']};
            border-radius: 4px;
            padding: 5px;
            min-height: 30px;
        }}
        
        QComboBox::drop-down {{
            width: 20px;
            border-left: 1px solid {colors['border_primary']};
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {colors['text_primary']};
            margin-right: 5px;
        }}
        
        QComboBox:hover {{
            border-color: {colors['primary_accent']};
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {colors['background_secondary']};
            color: {colors['text_primary']};
            selection-background-color: {colors['primary_accent']};
            selection-color: {colors['text_primary']};
            border: 1px solid {colors['border_primary']};
        }}
        
        QComboBox QLineEdit {{
            background-color: {colors['background_secondary']};
            color: {colors['text_primary']};
            selection-background-color: {colors['primary_accent']};
            selection-color: {colors['text_primary']};
        }}
        """

    def apply_theme_to_widget(self, widget):
        """
        Apply the current theme stylesheet to a widget.
        
        Args:
            widget: The widget to apply the theme to
        """
        stylesheet = self.get_widget_stylesheet()
        widget.setStyleSheet(stylesheet)
