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
    # Connect refresh signals
    window.refresh_requested.connect(train_manager.fetch_trains)
    window.auto_refresh_toggle_requested.connect(train_manager.toggle_auto_refresh)

    # Connect train manager signals to window updates
    train_manager.trains_updated.connect(window.update_train_display)
    train_manager.connection_changed.connect(window.update_connection_status)
    train_manager.last_update_changed.connect(window.update_last_update_time)
    train_manager.error_occurred.connect(
        lambda msg: window.show_error_message("Data Error", msg)
    )

    # Connect auto-refresh status updates
    def update_auto_refresh_ui():
        window.update_auto_refresh_status(train_manager.is_auto_refresh_active())

    window.auto_refresh_toggle_requested.connect(
        lambda: QTimer.singleShot(100, update_auto_refresh_ui)
    )

    # Update initial auto-refresh status (will be updated again after start_auto_refresh)
    window.update_auto_refresh_status(train_manager.is_auto_refresh_active())

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

        # Check if API credentials are configured
        splash.show_message("Checking API configuration...")
        app.processEvents()

        if not config_manager.validate_api_credentials():
            logger.info("API credentials not configured - showing settings dialog")

            # Import here to avoid circular imports
            from src.ui.settings_dialog import SettingsDialog

            # Close splash before showing settings dialog
            splash.show_message("Opening settings dialog...")
            app.processEvents()
            splash.close()

            # Create settings dialog for first launch (will show itself when ready)
            settings_dialog = SettingsDialog(config_manager, window)
            settings_dialog.setWindowTitle("Initial Setup - API Configuration Required")
            
            # CRITICAL FIX: Connect settings saved signal to main window
            settings_dialog.settings_saved.connect(window.on_settings_saved)

            # Add a message to the dialog
            info_text = (
                "Welcome to Trainer!\n\n"
                "To get started, please configure your Transport API credentials.\n"
                "You can get free API credentials from https://transportapi.com/"
            )

            # Execute the dialog (it will show itself when ready)
            result = settings_dialog.exec()

            if result == settings_dialog.DialogCode.Accepted:
                # Reload config after settings saved
                config = config_manager.load_config()
                logger.info("Configuration updated after initial setup")
            else:
                # User cancelled - show warning but continue
                window.show_info_message(
                    "Configuration Required",
                    "API credentials are required for the application to function properly.\n"
                    "You can configure them later via Settings → Options.",
                )
        else:
            # API is configured, continue with splash screen
            splash.show_message("Initializing train manager...")
            app.processEvents()

        # Create train manager with updated config
        train_manager = TrainManager(config)

        # Connect signals between components
        splash.show_message("Connecting components...")
        app.processEvents()

        connect_signals(window, train_manager)

        # Start auto-refresh only if enabled in config and API is configured
        if config_manager.validate_api_credentials():
            splash.show_message("Starting auto-refresh...")
            app.processEvents()

            train_manager.start_auto_refresh()

            # Do initial data fetch
            QTimer.singleShot(
                1000, train_manager.fetch_trains
            )  # Delay 1 second for UI to load
        else:
            logger.info("Skipping auto-refresh and initial fetch - API not configured")

        # Update auto-refresh status after starting
        QTimer.singleShot(
            100,
            lambda: window.update_auto_refresh_status(
                train_manager.is_auto_refresh_active()
            ),
        )

        # Show main window and close splash screen
        splash.show_message("Ready!")
        app.processEvents()

        # Small delay to show "Ready!" message
        QTimer.singleShot(500, lambda: [window.show(), splash.close()])

        logger.info("Application initialized successfully")

        # Start event loop
        exit_code = app.exec()

        # Cleanup
        train_manager.stop_auto_refresh()
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
