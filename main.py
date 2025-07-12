"""
Main entry point for the Trainer train times application.
Author: Oliver Ernster

This module initializes the application, sets up logging, loads the configuration,
and starts the main window with theme support and custom icon.
"""

import sys
import asyncio
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QIcon
from src.ui.main_window import MainWindow
from src.ui.splash_screen import TrainerSplashScreen
from src.managers.train_manager import TrainManager
from src.managers.config_manager import ConfigManager, ConfigurationError
from version import (
    __version__,
    __app_name__,
    __app_display_name__,
    __company__,
    __copyright__,
)


def setup_logging():
    """Setup application logging with file and console output."""
    import os
    from pathlib import Path
    
    # Create log directory in user's home directory
    if sys.platform == "darwin":  # macOS
        log_dir = Path.home() / "Library" / "Logs" / "Trainer"
    elif sys.platform == "win32":  # Windows
        log_dir = Path(os.environ.get("APPDATA", Path.home())) / "Trainer" / "logs"
    else:  # Linux and others
        log_dir = Path.home() / ".local" / "share" / "trainer" / "logs"
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "train_times.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(str(log_file)), logging.StreamHandler()],
    )

    # Set specific log levels for different modules
    logging.getLogger("src.api").setLevel(logging.INFO)
    logging.getLogger("src.ui").setLevel(logging.INFO)
    logging.getLogger("src.managers").setLevel(logging.INFO)


def setup_application_icon(app: QApplication):
    """
    Setup application icon using Unicode train emoji.

    Args:
        app: QApplication instance
    """
    from PySide6.QtGui import QPixmap, QPainter, QFont
    from PySide6.QtCore import Qt
    
    # Create a simple icon from the train emoji
    try:
        # Create a pixmap for the icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Paint the emoji onto the pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up font for emoji
        font = QFont()
        font.setPointSize(48)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.black)
        
        # Draw the train emoji centered
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🚂")
        painter.end()
        
        # Create icon and set it
        icon = QIcon(pixmap)
        app.setWindowIcon(icon)
        
        logging.info("Application icon set using Unicode train emoji")
        
    except Exception as e:
        logging.warning(f"Failed to create emoji icon, using default: {e}")


def connect_signals(window: MainWindow, train_manager: TrainManager):
    """
    Connect signals between main window and train manager.

    Args:
        window: Main window instance
        train_manager: Train manager instance
    """
    # Connect refresh signals (manual refresh only)
    window.refresh_requested.connect(train_manager.fetch_trains)
    
    # Connect route change signal
    window.route_changed.connect(train_manager.set_route)
    
    # Connect config update signal
    window.config_updated.connect(train_manager.update_config)

    # Connect train manager signals to window updates
    train_manager.trains_updated.connect(window.update_train_display)
    train_manager.connection_changed.connect(window.update_connection_status)
    train_manager.last_update_changed.connect(window.update_last_update_time)
    train_manager.error_occurred.connect(
        lambda msg: window.show_error_message("Data Error", msg)
    )

    # Auto-refresh functionality removed

    logging.info("Signals connected between main window and train manager")


def main():
    """Main application entry point."""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Trainer - Trainer train times application")

    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_display_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(__company__)
    app.setOrganizationDomain("trainer.local")

    # Set desktop file name for better Linux integration
    app.setDesktopFileName("trainer")

    # Setup application icon (must be done early for Windows taskbar)
    setup_application_icon(app)

    # Create and show splash screen first
    splash = TrainerSplashScreen()
    splash.show()
    splash.show_message("Initializing application...")
    app.processEvents()  # Process events to show splash screen

    try:
        # Initialize configuration manager (will use AppData on Windows)
        splash.show_message("Loading configuration...")
        app.processEvents()

        config_manager = ConfigManager()

        # Install default config to AppData if needed
        if config_manager.install_default_config_to_appdata():
            logger.info("Default configuration installed to AppData")

        # Load configuration
        config = config_manager.load_config()
        logger.info(f"Configuration loaded from: {config_manager.config_path}")

        # Create main window with shared config manager (but don't show it yet)
        splash.show_message("Creating main window...")
        app.processEvents()

        window = MainWindow(config_manager)

        # Initialize train manager (now works offline without API)
        splash.show_message("Initializing train manager...")
        app.processEvents()
        
        logger.info("Starting in offline mode - API credentials not required")

        # Create train manager with updated config
        train_manager = TrainManager(config)

        # Set the route from configuration for offline timetable generation
        if config and config.stations:
            train_manager.set_route(config.stations.from_code, config.stations.to_code)
            logger.info(f"Route configured: {config.stations.from_name} ({config.stations.from_code}) -> {config.stations.to_name} ({config.stations.to_code})")

        # Connect signals between components
        splash.show_message("Connecting components...")
        app.processEvents()

        # Attach train manager to window for access by dialogs
        window.train_manager = train_manager

        connect_signals(window, train_manager)

        # The optimized widget initialization will handle weather and NASA widgets
        # Train data will be fetched after widget initialization completes
        splash.show_message("Optimizing widget initialization...")
        app.processEvents()
        
        # Connect to initialization completion to start train data fetch
        def on_widgets_ready():
            splash.show_message("Loading train data...")
            app.processEvents()
            # Delay train data fetch to allow widgets to fully initialize
            QTimer.singleShot(500, train_manager.fetch_trains)
            logger.info("Train data fetch scheduled after widget initialization")
        
        if window.initialization_manager:
            window.initialization_manager.initialization_completed.connect(on_widgets_ready)
        else:
            # Fallback if initialization manager not available
            QTimer.singleShot(1000, train_manager.fetch_trains)

        # Show main window and close splash screen
        splash.show_message("Ready!")
        app.processEvents()

        # Small delay to show "Ready!" message
        QTimer.singleShot(500, lambda: [window.show(), splash.close()])

        logger.info("Application initialized successfully")

        # Start event loop
        exit_code = app.exec()

        # Cleanup
        logger.info(f"Application exiting with code {exit_code}")
        sys.exit(exit_code)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        # Still try to show window with error message
        try:
            window = MainWindow()  # Use default config manager in error case
            window.show_error_message("Configuration Error", str(e))
            window.show()
            app.exec()
        except:
            pass
        sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
