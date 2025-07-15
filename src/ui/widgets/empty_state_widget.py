"""
Empty state widget for when no trains are available.

This module provides a widget that displays a friendly message when no train
data is available, with proper theming support.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from .train_widgets_base import BaseTrainWidget

logger = logging.getLogger(__name__)


class EmptyStateWidget(BaseTrainWidget):
    """Widget displayed when no trains are available."""

    def __init__(self, theme: str = "dark", parent: Optional[BaseTrainWidget] = None):
        """
        Initialize empty state widget.

        Args:
            theme: Current theme ("dark" or "light")
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_theme = theme
        
        self._setup_ui()
        self._apply_theme_styles()

    def _setup_ui(self) -> None:
        """Setup empty state UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        self.icon_label = QLabel("🚂")
        icon_font = QFont()
        icon_font.setPointSize(48)
        self.icon_label.setFont(icon_font)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        # Message
        self.message_label = QLabel("No trains available")
        message_font = QFont()
        message_font.setPointSize(16)
        self.message_label.setFont(message_font)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)

        # Subtitle
        self.subtitle_label = QLabel("Check your connection or try refreshing")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle_label)

    def _apply_theme_styles(self) -> None:
        """Apply theme styling to the empty state widget."""
        colors = self.get_theme_colors(self.current_theme)
        
        style = f"""
        QLabel {{
            color: {colors["text_secondary"]};
            background-color: transparent;
        }}
        """
        
        self.setStyleSheet(style)
        
        # Update individual label styles if needed
        if hasattr(self, 'icon_label'):
            self.icon_label.setStyleSheet(f"color: {colors['text_secondary']};")
        if hasattr(self, 'message_label'):
            self.message_label.setStyleSheet(f"color: {colors['text_secondary']};")
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.setStyleSheet(f"color: {colors['text_secondary']};")

    def set_message(self, message: str, subtitle: str = "") -> None:
        """
        Update the empty state message.
        
        Args:
            message: Main message to display
            subtitle: Optional subtitle message
        """
        if hasattr(self, 'message_label'):
            self.message_label.setText(message)
        
        if subtitle and hasattr(self, 'subtitle_label'):
            self.subtitle_label.setText(subtitle)
            self.subtitle_label.setVisible(True)
        elif hasattr(self, 'subtitle_label'):
            self.subtitle_label.setVisible(False)

    def set_icon(self, icon: str) -> None:
        """
        Update the empty state icon.
        
        Args:
            icon: Icon character or emoji to display
        """
        if hasattr(self, 'icon_label'):
            self.icon_label.setText(icon)