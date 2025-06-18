"""
Splash screen for the Trainer application.
Author: Oliver Ernster

This module provides a splash screen that displays while the application is loading.
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon, QPainter, QFont
from PySide6.QtSvgWidgets import QSvgWidget

logger = logging.getLogger(__name__)


class TrainerSplashScreen(QSplashScreen):
    """
    Custom splash screen for the Trainer application.

    Shows the train icon and loading text while the application initializes.
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

        logger.info("Splash screen initialized")

    def setup_ui(self):
        """Setup the splash screen UI."""
        # Create main widget and layout
        self.main_widget = QWidget()
        layout = QVBoxLayout(self.main_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Try to load the train icon
        icon_widget = self.create_icon_widget()
        if icon_widget:
            layout.addWidget(icon_widget)

        # Add application title
        title_label = QLabel("Trainer")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Add subtitle
        subtitle_label = QLabel("Train Times Application")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        layout.addWidget(subtitle_label)

        # Add loading text
        self.loading_label = QLabel("Loading...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_font = QFont()
        loading_font.setPointSize(10)
        self.loading_label.setFont(loading_font)
        layout.addWidget(self.loading_label)

        # Set the main widget
        self.main_widget.setFixedSize(400, 300)

    def create_icon_widget(self):
        """Create the icon widget from available assets."""
        # Try SVG first
        svg_path = Path("assets/train_icon.svg")
        if svg_path.exists():
            svg_widget = QSvgWidget(str(svg_path))
            svg_widget.setFixedSize(128, 128)
            logger.info("Splash screen using SVG icon")
            return svg_widget

        # Try ICO file
        ico_path = Path("assets/train_icon.ico")
        if ico_path.exists():
            pixmap = QPixmap(str(ico_path))
            if not pixmap.isNull():
                # Scale to desired size
                scaled_pixmap = pixmap.scaled(
                    128,
                    128,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon_label = QLabel()
                icon_label.setPixmap(scaled_pixmap)
                icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logger.info("Splash screen using ICO icon")
                return icon_label

        # Try PNG files
        png_sizes = [128, 64, 48, 32]
        for size in png_sizes:
            png_path = Path(f"assets/train_icon_{size}.png")
            if png_path.exists():
                pixmap = QPixmap(str(png_path))
                if not pixmap.isNull():
                    # Scale to 128x128 if needed
                    if pixmap.width() != 128 or pixmap.height() != 128:
                        scaled_pixmap = pixmap.scaled(
                            128,
                            128,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    else:
                        scaled_pixmap = pixmap

                    icon_label = QLabel()
                    icon_label.setPixmap(scaled_pixmap)
                    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    logger.info(f"Splash screen using PNG icon ({size}x{size})")
                    return icon_label

        logger.warning("No train icon found for splash screen")
        return None

    def apply_styling(self):
        """Apply dark theme styling to the splash screen."""
        style = """
        QWidget {
            background-color: #1a1a1a;
            color: #ffffff;
            border: 2px solid #4fc3f7;
            border-radius: 8px;
        }
        QLabel {
            background-color: transparent;
            color: #ffffff;
            border: none;
        }
        """
        self.main_widget.setStyleSheet(style)

    def paintEvent(self, event):
        """Custom paint event to draw the main widget."""
        super().paintEvent(event)

        # Paint the main widget onto the splash screen
        if hasattr(self, "main_widget"):
            painter = QPainter(self)

            # Calculate center position
            splash_rect = self.rect()
            widget_rect = self.main_widget.rect()
            x = (splash_rect.width() - widget_rect.width()) // 2
            y = (splash_rect.height() - widget_rect.height()) // 2

            # Render the widget
            self.main_widget.render(
                painter,
                painter.deviceTransform().map(splash_rect.topLeft())
                + painter.deviceTransform().map(QPoint(x, y)),
            )

            painter.end()

    def show_message(self, message: str):
        """
        Update the loading message.

        Args:
            message: The message to display
        """
        if hasattr(self, "loading_label"):
            self.loading_label.setText(message)
            self.repaint()  # Force immediate repaint
            logger.debug(f"Splash screen message: {message}")

    def close_splash(self):
        """Close the splash screen."""
        logger.info("Closing splash screen")
        self.close()


# Import QPoint for the paintEvent
from PySide6.QtCore import QPoint
