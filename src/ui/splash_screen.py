"""
Splash screen for the Trainer application.
Author: Oliver Ernster

This module provides a splash screen that displays while the application is loading.
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPixmap, QPainter, QFont

logger = logging.getLogger(__name__)


class TrainerSplashScreen(QSplashScreen):
    """
    Custom splash screen for the Trainer application.

    Shows the train emoji (🚂) and loading text while the application initializes.
    """

    def __init__(self):
        """Initialize the splash screen."""
        # Create a blank pixmap for the base splash screen
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.GlobalColor.transparent)

        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)

        # Set window properties
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )

        # Setup the UI
        self.setup_ui()

        # Apply dark theme styling
        self.apply_styling()

        logger.debug("Splash screen initialized")

    def setup_ui(self):
        """Setup the splash screen UI."""
        # Initialize loading message
        self.loading_message = "Loading..."


    def apply_styling(self):
        """Apply dark theme styling to the splash screen."""
        # Styling is now handled in paintEvent - no widget styling needed
        pass

    def paintEvent(self, event):
        """Custom paint event to draw the splash screen content."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        
        # Draw border
        painter.setPen(Qt.GlobalColor.blue)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        
        # Calculate center position for main content
        center_y = self.rect().height() // 2
        
        # Draw train emoji centered
        painter.setPen(Qt.GlobalColor.white)
        emoji_font = QFont()
        emoji_font.setPointSize(48)
        painter.setFont(emoji_font)
        emoji_rect = self.rect().adjusted(0, center_y - 80, 0, center_y - 30)
        painter.drawText(emoji_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "🚂")
        
        # Draw title below emoji
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        painter.setFont(title_font)
        title_rect = self.rect().adjusted(0, center_y - 20, 0, center_y + 10)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "Trainer")
        
        # Draw subtitle below title
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        painter.setFont(subtitle_font)
        subtitle_rect = self.rect().adjusted(0, center_y + 20, 0, center_y + 50)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "Train Times Application")
        
        # Draw loading message at bottom
        loading_font = QFont()
        loading_font.setPointSize(10)
        painter.setFont(loading_font)
        loading_rect = self.rect().adjusted(0, 0, 0, -20)
        painter.drawText(loading_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self.loading_message)
        
        painter.end()

    def show_message(self, message: str):
        """
        Update the loading message.

        Args:
            message: The message to display
        """
        self.loading_message = message
        self.repaint()  # Force immediate repaint
        logger.debug(f"Splash screen message: {message}")

    def close_splash(self):
        """Close the splash screen."""
        logger.info("Closing splash screen")
        self.close()


