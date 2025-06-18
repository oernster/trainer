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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("train_times.log"), logging.StreamHandler()],
    )

    # Set specific log levels for different modules
    logging.getLogger("src.api").setLevel(logging.INFO)
    logging.getLogger("src.ui").setLevel(logging.INFO)
    logging.getLogger("src.managers").setLevel(logging.INFO)


def setup_application_icon(app: QApplication):
    """
    Setup application icon from assets directory for Windows taskbar and shortcuts.

    Args:
        app: QApplication instance
    """
    # Try PNG files first (better Windows compatibility)
    png_sizes = [16, 24, 32, 48, 64, 128, 256]
    icon = QIcon()
    png_found = False

    for size in png_sizes:
        png_path = Path(f"assets/train_icon_{size}.png")
        if png_path.exists():
            icon.addFile(str(png_path), QSize(size, size))
            png_found = True

    if png_found:
        # Set application-wide icon (for taskbar, shortcuts, etc.)
        app.setWindowIcon(icon)
        logging.info("Application icon loaded from PNG files with multiple sizes")
        return

    # Fallback to SVG if PNG files not available
    svg_path = Path("assets/train_icon.svg")
    if svg_path.exists():
        # Create QIcon from SVG
        icon = QIcon(str(svg_path))

        # Set application-wide icon (for taskbar, shortcuts, etc.)
        app.setWindowIcon(icon)

        # Set additional sizes for better Windows compatibility
        icon.addFile(str(svg_path), QSize(16, 16))
        icon.addFile(str(svg_path), QSize(32, 32))
        icon.addFile(str(svg_path), QSize(48, 48))
        icon.addFile(str(svg_path), QSize(64, 64))
        icon.addFile(str(svg_path), QSize(128, 128))
        icon.addFile(str(svg_path), QSize(256, 256))

        # Set the icon again with all sizes
        app.setWindowIcon(icon)

        logging.info(
            "Application icon loaded from assets/train_icon.svg with multiple sizes"
        )
    else:
        logging.warning("No train icon files found in assets directory")


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
        QTimer.singleShot(500, lambda: [
            window.show(),
            splash.close()
        ])

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
