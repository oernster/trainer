"""
Main entry point for the Trainer train times application.
Author: Oliver Ernster

This module initializes the application, sets up logging, loads the configuration,
and starts the main window with theme support and custom icon.
"""

import sys
import tempfile
import os
from pathlib import Path

# CRITICAL: Ultra-early singleton check before ANY imports or initialization
def check_single_instance_ultra_early():
    """Ultra-early singleton check using file lock before any Qt imports."""
    lock_file_path = Path(tempfile.gettempdir()) / "trainer_app_ultra_early.lock"
    
    try:
        # Try to create lock file exclusively
        if lock_file_path.exists():
            # Check if the process that created the lock is still running
            try:
                with open(lock_file_path, 'r') as f:
                    pid = int(f.read().strip())
                
                # Check if process is still running
                if sys.platform == "win32":
                    import subprocess
                    result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'],
                                          capture_output=True, text=True, timeout=5)
                    if str(pid) in result.stdout:
                        print("ERROR: Another instance of Trainer is already running!")
                        print("Please close the existing instance before starting a new one.")
                        sys.exit(1)
                    else:
                        # Process not running, remove stale lock file
                        lock_file_path.unlink()
                else:
                    # Unix-like systems
                    try:
                        os.kill(pid, 0)  # Check if process exists
                        print("ERROR: Another instance of Trainer is already running!")
                        print("Please close the existing instance before starting a new one.")
                        sys.exit(1)
                    except OSError:
                        # Process not running, remove stale lock file
                        lock_file_path.unlink()
            except (ValueError, FileNotFoundError):
                # Invalid lock file, remove it
                lock_file_path.unlink()
        
        # Create new lock file with current PID
        with open(lock_file_path, 'w') as f:
            f.write(str(os.getpid()))
        
        print("Ultra-early singleton check passed - proceeding with application startup")
        return lock_file_path
        
    except Exception as e:
        print(f"Warning: Failed to create ultra-early lock file: {e}")
        return None

# Perform ultra-early singleton check BEFORE any other imports
_ultra_early_lock_file = check_single_instance_ultra_early()

# Now proceed with normal imports
import asyncio
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QSize, QSharedMemory
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


def cleanup_ultra_early_lock():
    """Clean up the ultra-early lock file."""
    global _ultra_early_lock_file
    if _ultra_early_lock_file and _ultra_early_lock_file.exists():
        try:
            _ultra_early_lock_file.unlink()
        except Exception as e:
            print(f"Warning: Failed to remove ultra-early lock file: {e}")


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


class SingleInstanceApplication(QApplication):
    """QApplication subclass that enforces single instance with dual protection."""
    
    def __init__(self, argv):
        # Additional Qt-level singleton check
        existing_app = QApplication.instance()
        if existing_app is not None:
            print("CRITICAL ERROR: QApplication instance already exists!")
            print("This indicates multiple application launches. Exiting immediately.")
            sys.exit(1)
        
        # Create shared memory segment for single instance check
        temp_shared_memory = QSharedMemory("TrainerAppSingleInstance")
        
        # Try to attach to existing shared memory
        if temp_shared_memory.attach():
            # Another instance is already running - exit immediately
            print("ERROR: Another Qt instance of Trainer is already running!")
            print("Please close the existing instance before starting a new one.")
            temp_shared_memory.detach()
            sys.exit(1)
        
        # No existing instance found, proceed with initialization
        super().__init__(argv)
        
        # Now create our own shared memory segment
        self.shared_memory = QSharedMemory("TrainerAppSingleInstance")
        if not self.shared_memory.create(1):
            print("CRITICAL ERROR: Failed to create shared memory for single instance check!")
            print("This should not happen. Exiting to prevent multiple instances.")
            sys.exit(1)
        
        print("Qt singleton check passed - application starting normally.")


def main():
    """Main application entry point."""
    try:
        # Setup logging first
        setup_logging()
        logger = logging.getLogger(__name__)

        logger.info("Starting Trainer - Trainer train times application")

        # Create single instance QApplication with dual protection
        app = SingleInstanceApplication(sys.argv)
        app.setApplicationName(__app_name__)
        app.setApplicationDisplayName(__app_display_name__)
        app.setApplicationVersion(__version__)
        app.setOrganizationName(__company__)
        app.setOrganizationDomain("trainer.local")

        # Set desktop file name for better Linux integration
        app.setDesktopFileName("trainer")

        # Prevent multiple instances
        app.setQuitOnLastWindowClosed(True)

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
            # Only set route if we have valid station configuration
            if (config and config.stations and
                getattr(config.stations, 'from_code', None) and
                getattr(config.stations, 'to_code', None)):
                train_manager.set_route(config.stations.from_code, config.stations.to_code)
                logger.info(f"Route configured: {config.stations.from_name} ({config.stations.from_code}) -> {config.stations.to_name} ({config.stations.to_code})")
            else:
                logger.info("No valid station configuration found - train list will be empty until stations are configured")

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
            
            # Connect to initialization completion to start train data fetch and show window
            def on_widgets_ready():
                splash.show_message("Loading train data...")
                app.processEvents()
                # Single train data fetch after widgets are ready
                train_manager.fetch_trains()
                logger.info("Train data fetched after widget initialization")
                
                # Connect to train data completion to show window
                def on_train_data_ready():
                    splash.show_message("Ready!")
                    app.processEvents()
                    # Show window immediately after train data is ready
                    window.show()
                    # Focus and activate the main window
                    window.raise_()
                    window.activateWindow()
                    splash.close()
                    logger.info("Main window shown and focused after full initialization")
                    # Disconnect the signal to prevent multiple calls
                    train_manager.trains_updated.disconnect(on_train_data_ready)
                
                # Connect to train data signal to show window when data is ready
                train_manager.trains_updated.connect(on_train_data_ready)
            
            # Use proper signaling instead of timers
            if window.initialization_manager:
                window.initialization_manager.initialization_completed.connect(on_widgets_ready)
                logger.info("Train data fetch and window display scheduled with initialization manager")
            else:
                # Fallback if initialization manager not available - still use signals
                def fallback_startup():
                    train_manager.fetch_trains()
                    # Connect to train data signal for fallback too
                    def on_fallback_train_data():
                        window.show()
                        # Focus and activate the main window
                        window.raise_()
                        window.activateWindow()
                        splash.close()
                        train_manager.trains_updated.disconnect(on_fallback_train_data)
                    train_manager.trains_updated.connect(on_fallback_train_data)
                
                QTimer.singleShot(1000, fallback_startup)
                logger.info("Train data fetch and window display scheduled with fallback signaling")

            # Don't show main window immediately - wait for initialization to complete
            # The window will be shown by the on_widgets_ready callback

            logger.info("Application initialized successfully")

            # Start event loop
            exit_code = app.exec()

            # Cleanup
            logger.info(f"Application exiting with code {exit_code}")
            sys.exit(exit_code)

        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            # Show error message without creating another window
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Configuration Error")
            msg_box.setText(str(e))
            msg_box.exec()
            sys.exit(1)

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)

    finally:
        # Always cleanup the ultra-early lock file
        cleanup_ultra_early_lock()


if __name__ == "__main__":
    main()
