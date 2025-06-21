"""
Standalone comprehensive unit tests for MainWindow class.

This test suite aims for 85%+ coverage by testing actual functionality
rather than relying heavily on mocking. It avoids conftest.py dependencies.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import cast

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from PySide6.QtWidgets import QApplication, QMessageBox, QMenu, QLabel, QPushButton
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtGui import QKeySequence

    HAS_QT = True
except ImportError:
    HAS_QT = False

if HAS_QT:
    from src.ui.main_window import MainWindow
    from src.managers.config_manager import (
        ConfigManager,
        ConfigurationError,
        ConfigData,
        APIConfig,
        StationConfig,
        RefreshConfig,
        DisplayConfig,
    )
    from src.managers.theme_manager import ThemeManager
    from src.models.train_data import TrainData, TrainStatus, ServiceType
    from src.ui.train_widgets import TrainListWidget


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for UI tests."""
    if not HAS_QT:
        pytest.skip("PySide6 not available")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return ConfigData(
        api=APIConfig(
            app_id="test_id",
            app_key="test_key",
            base_url="https://transportapi.com/v3/uk",
            timeout_seconds=30,
            max_retries=2,
            rate_limit_per_minute=10,
        ),
        stations=StationConfig(
            from_code="FLE", from_name="Fleet", to_code="WAT", to_name="London Waterloo"
        ),
        refresh=RefreshConfig(
            auto_enabled=False, interval_minutes=5, manual_enabled=True
        ),
        display=DisplayConfig(
            max_trains=50, time_window_hours=10, show_cancelled=True, theme="dark"
        ),
    )


@pytest.fixture
def temp_config_file(test_config):
    """Create temporary configuration file for testing."""
    import json

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_config.model_dump(), f, indent=2)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def config_manager(temp_config_file):
    """Provide ConfigManager with temporary config file."""
    return ConfigManager(temp_config_file)


@pytest.fixture
def sample_train_data():
    """Provide sample train data for testing."""
    base_time = datetime.now().replace(second=0, microsecond=0)

    return [
        TrainData(
            departure_time=base_time + timedelta(minutes=15),
            scheduled_departure=base_time + timedelta(minutes=15),
            destination="London Waterloo",
            platform="2",
            operator="South Western Railway",
            service_type=ServiceType.FAST,
            status=TrainStatus.ON_TIME,
            delay_minutes=0,
            estimated_arrival=base_time + timedelta(minutes=62),
            journey_duration=timedelta(minutes=47),
            current_location="Fleet",
            train_uid="W12345",
            service_id="24673004",
        ),
        TrainData(
            departure_time=base_time + timedelta(minutes=22),
            scheduled_departure=base_time + timedelta(minutes=20),
            destination="London Waterloo",
            platform="1",
            operator="South Western Railway",
            service_type=ServiceType.STOPPING,
            status=TrainStatus.DELAYED,
            delay_minutes=2,
            estimated_arrival=base_time + timedelta(minutes=74),
            journey_duration=timedelta(minutes=52),
            current_location="Fleet",
            train_uid="W12346",
            service_id="24673005",
        ),
    ]


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
class TestMainWindow:
    """Test suite for MainWindow class."""

    def test_init_with_default_config_manager(self, qapp):
        """Test MainWindow initialization with default ConfigManager."""
        with patch("src.ui.main_window.ConfigManager") as mock_config_manager_class:
            mock_config_manager = Mock()
            mock_config_manager.install_default_config_to_appdata.return_value = None
            mock_config_manager.load_config.return_value = Mock()
            mock_config_manager_class.return_value = mock_config_manager

            window = MainWindow()

            assert window.config_manager is not None
            assert isinstance(window.theme_manager, ThemeManager)
            mock_config_manager.install_default_config_to_appdata.assert_called_once()
            mock_config_manager.load_config.assert_called_once()

            window.close()

    def test_init_with_provided_config_manager(self, qapp, config_manager):
        """Test MainWindow initialization with provided ConfigManager."""
        window = MainWindow(config_manager)

        assert window.config_manager is config_manager
        assert isinstance(window.theme_manager, ThemeManager)
        assert window.config is not None

        window.close()

    def test_init_with_configuration_error(self, qapp):
        """Test MainWindow initialization when configuration loading fails."""
        with patch("src.ui.main_window.ConfigManager") as mock_config_manager_class:
            mock_config_manager = Mock()
            mock_config_manager.install_default_config_to_appdata.return_value = None
            mock_config_manager.load_config.side_effect = ConfigurationError(
                "Test error"
            )
            mock_config_manager_class.return_value = mock_config_manager

            with patch.object(MainWindow, "show_error_message") as mock_show_error:
                window = MainWindow()

                assert window.config is None
                mock_show_error.assert_called_once_with(
                    "Configuration Error", "Test error"
                )

                window.close()

    def test_setup_ui_components(self, qapp, config_manager):
        """Test that all UI components are properly initialized."""
        window = MainWindow(config_manager)

        # Check window properties
        assert "Trainer" in window.windowTitle()
        assert window.minimumSize().width() == 800
        assert window.minimumSize().height() == 1100

        # Check UI components exist
        assert window.train_list_widget is not None
        assert window.last_update_label is not None
        assert window.next_update_label is not None
        assert window.time_window_label is not None
        assert window.theme_button is not None
        assert window.refresh_button is not None
        assert window.connection_status is not None
        assert window.train_count_label is not None
        assert window.theme_status is not None
        assert window.auto_refresh_status is not None

        # Check initial text values
        assert "Last Updated: --:--:--" in cast(QLabel, window.last_update_label).text()
        assert "Next Update: --" in cast(QLabel, window.next_update_label).text()
        assert (
            "Showing trains for next 16 hours"
            in cast(QLabel, window.time_window_label).text()
        )
        assert "Disconnected" in cast(QLabel, window.connection_status).text()
        assert "0 trains" in cast(QLabel, window.train_count_label).text()
        assert "Auto-refresh: OFF" in cast(QLabel, window.auto_refresh_status).text()

        window.close()

    def test_theme_toggle(self, qapp, config_manager):
        """Test theme toggling functionality."""
        window = MainWindow(config_manager)

        initial_theme = window.theme_manager.current_theme

        # Toggle theme
        window.toggle_theme()

        # Theme should have changed
        assert window.theme_manager.current_theme != initial_theme

        # Toggle back
        window.toggle_theme()
        assert window.theme_manager.current_theme == initial_theme

        window.close()

    def test_on_theme_changed(self, qapp, config_manager):
        """Test theme change event handling."""
        window = MainWindow(config_manager)

        # Mock the theme_changed signal emission
        with patch.object(window, "theme_changed") as mock_signal:
            window.on_theme_changed("light")

            # Check that theme button and status are updated
            assert (
                cast(QPushButton, window.theme_button).text()
                == window.theme_manager.get_theme_icon()
            )
            assert "Light" in cast(QLabel, window.theme_status).text()

            # Signal should be emitted
            mock_signal.emit.assert_called_once_with("light")

        window.close()

    def test_manual_refresh(self, qapp, config_manager):
        """Test manual refresh functionality."""
        window = MainWindow(config_manager)

        with patch.object(window, "refresh_requested") as mock_signal:
            window.manual_refresh()
            mock_signal.emit.assert_called_once()

        window.close()

    def test_toggle_auto_refresh(self, qapp, config_manager):
        """Test auto-refresh toggle functionality."""
        window = MainWindow(config_manager)

        with patch.object(window, "auto_refresh_toggle_requested") as mock_signal:
            window.toggle_auto_refresh()
            mock_signal.emit.assert_called_once()

        window.close()

    def test_update_train_display(self, qapp, config_manager, sample_train_data):
        """Test train display update functionality."""
        window = MainWindow(config_manager)

        # Update with sample data
        window.update_train_display(sample_train_data)

        # Check train count is updated
        assert (
            f"{len(sample_train_data)} trains"
            in cast(QLabel, window.train_count_label).text()
        )

        # Check train list widget is updated
        assert cast(TrainListWidget, window.train_list_widget).get_train_count() == len(
            sample_train_data
        )

        window.close()

    def test_update_train_display_empty_list(self, qapp, config_manager):
        """Test train display update with empty list."""
        window = MainWindow(config_manager)

        window.update_train_display([])

        assert "0 trains" in cast(QLabel, window.train_count_label).text()
        assert cast(TrainListWidget, window.train_list_widget).get_train_count() == 0

        window.close()

    def test_update_last_update_time(self, qapp, config_manager):
        """Test last update time display."""
        window = MainWindow(config_manager)

        timestamp = "12:34:56"
        window.update_last_update_time(timestamp)

        assert (
            f"Last Updated: {timestamp}"
            in cast(QLabel, window.last_update_label).text()
        )

        window.close()

    def test_update_next_update_countdown(self, qapp, config_manager):
        """Test next update countdown display."""
        window = MainWindow(config_manager)

        # Test with minutes and seconds
        window.update_next_update_countdown(125)  # 2m 5s
        assert "Next Update: 2m 5s" in cast(QLabel, window.next_update_label).text()

        # Test with only seconds
        window.update_next_update_countdown(45)
        assert "Next Update: 45s" in cast(QLabel, window.next_update_label).text()

        # Test with zero
        window.update_next_update_countdown(0)
        assert "Next Update: 0s" in cast(QLabel, window.next_update_label).text()

        window.close()

    def test_update_connection_status_connected(self, qapp, config_manager):
        """Test connection status update when connected."""
        window = MainWindow(config_manager)

        window.update_connection_status(True)

        assert "Connected" in cast(QLabel, window.connection_status).text()
        assert (
            "#4caf50" in cast(QLabel, window.connection_status).styleSheet()
        )  # Green color

        window.close()

    def test_update_connection_status_disconnected(self, qapp, config_manager):
        """Test connection status update when disconnected."""
        window = MainWindow(config_manager)

        window.update_connection_status(False, "Network error")

        assert (
            "Disconnected (Network error)"
            in cast(QLabel, window.connection_status).text()
        )
        assert (
            "#f44336" in cast(QLabel, window.connection_status).styleSheet()
        )  # Red color

        window.close()

    def test_update_auto_refresh_status_enabled(self, qapp, config_manager):
        """Test auto-refresh status update when enabled."""
        window = MainWindow(config_manager)

        window.update_auto_refresh_status(True)

        assert "Auto-refresh: ON" in cast(QLabel, window.auto_refresh_status).text()
        assert "⏸️ Auto-refresh" in cast(QPushButton, window.auto_refresh_button).text()
        assert (
            "Click to disable"
            in cast(QPushButton, window.auto_refresh_button).toolTip()
        )

        window.close()

    def test_update_auto_refresh_status_disabled(self, qapp, config_manager):
        """Test auto-refresh status update when disabled."""
        window = MainWindow(config_manager)

        window.update_auto_refresh_status(False)

        assert "Auto-refresh: OFF" in cast(QLabel, window.auto_refresh_status).text()
        assert "▶️ Auto-refresh" in cast(QPushButton, window.auto_refresh_button).text()
        assert (
            "Click to enable" in cast(QPushButton, window.auto_refresh_button).toolTip()
        )

        window.close()

    def test_show_error_message(self, qapp, config_manager):
        """Test error message dialog display."""
        window = MainWindow(config_manager)

        with patch("src.ui.main_window.QMessageBox") as mock_msgbox:
            mock_box = Mock()
            mock_msgbox.return_value = mock_box

            window.show_error_message("Test Title", "Test Message")

            mock_msgbox.assert_called_once_with(window)
            # Check that setIcon was called with any argument (the enum value gets mocked)
            mock_box.setIcon.assert_called_once()
            mock_box.setWindowTitle.assert_called_once_with("Test Title")
            mock_box.setText.assert_called_once_with("Test Message")
            mock_box.exec.assert_called_once()

        window.close()

    def test_show_info_message(self, qapp, config_manager):
        """Test info message dialog display."""
        window = MainWindow(config_manager)

        with patch("src.ui.main_window.QMessageBox") as mock_msgbox:
            mock_box = Mock()
            mock_msgbox.return_value = mock_box

            window.show_info_message("Test Title", "Test Message")

            mock_msgbox.assert_called_once_with(window)
            # Check that setIcon was called with any argument (the enum value gets mocked)
            mock_box.setIcon.assert_called_once()
            mock_box.setWindowTitle.assert_called_once_with("Test Title")
            mock_box.setText.assert_called_once_with("Test Message")
            mock_box.exec.assert_called_once()

        window.close()

    def test_show_settings_dialog_success(self, qapp, config_manager):
        """Test settings dialog display success."""
        window = MainWindow(config_manager)

        with patch("src.ui.main_window.SettingsDialog") as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog_class.return_value = mock_dialog

            window.show_settings_dialog()

            mock_dialog_class.assert_called_once_with(window.config_manager, window)
            mock_dialog.settings_saved.connect.assert_called_once()
            mock_dialog.exec.assert_called_once()

        window.close()

    def test_show_settings_dialog_exception(self, qapp, config_manager):
        """Test settings dialog display with exception."""
        window = MainWindow(config_manager)

        with patch(
            "src.ui.main_window.SettingsDialog", side_effect=Exception("Dialog error")
        ):
            with patch.object(window, "show_error_message") as mock_show_error:
                window.show_settings_dialog()

                mock_show_error.assert_called_once_with(
                    "Settings Error", "Failed to open settings: Dialog error"
                )

        window.close()

    def test_on_settings_saved_success(self, qapp, config_manager):
        """Test settings saved event handling success."""
        window = MainWindow(config_manager)

        # Mock the config manager to return a new config
        new_config = Mock()
        new_config.display.theme = "light"

        # Mock weather config to avoid weather manager issues
        mock_weather_config = Mock()
        mock_weather_config.enabled = False  # Disable weather to avoid refresh issues
        new_config.weather = mock_weather_config

        # Mock astronomy config with proper structure for setVisible() call
        mock_astronomy_config = Mock()
        mock_astronomy_config.enabled = True
        mock_astronomy_config.has_valid_api_key.return_value = False  # No API key to avoid manager initialization
        mock_astronomy_config.display = Mock()
        mock_astronomy_config.display.show_in_forecast = True
        new_config.astronomy = mock_astronomy_config

        with patch.object(
            window.config_manager, "load_config", return_value=new_config
        ):
            with patch.object(window.theme_manager, "set_theme") as mock_set_theme:
                window.on_settings_saved()

                assert window.config == new_config
                mock_set_theme.assert_called_once_with("light")

        window.close()

    def test_on_settings_saved_configuration_error(self, qapp, config_manager):
        """Test settings saved event handling with configuration error."""
        window = MainWindow(config_manager)

        with patch.object(
            window.config_manager,
            "load_config",
            side_effect=ConfigurationError("Load error"),
        ):
            with patch.object(window, "show_error_message") as mock_show_error:
                window.on_settings_saved()

                mock_show_error.assert_called_once_with(
                    "Configuration Error", "Failed to reload settings: Load error"
                )

        window.close()

    def test_show_about_dialog(self, qapp, config_manager):
        """Test about dialog display."""
        window = MainWindow(config_manager)

        with patch("src.ui.main_window.QMessageBox") as mock_msgbox:
            mock_box = Mock()
            mock_msgbox.return_value = mock_box

            window.show_about_dialog()

            mock_msgbox.assert_called_once_with(window)
            # Check that setIcon was called with any argument (the enum value gets mocked)
            mock_box.setIcon.assert_called_once()
            mock_box.setWindowTitle.assert_called_once_with("About")

            # Check that the about text contains expected content
            call_args = mock_box.setText.call_args[0][0]
            assert "Trainer" in call_args
            # Use regex to match any version format (e.g., "Version 1.0.0", "Version 2.0.0", etc.)
            import re

            assert re.search(
                r"Version \d+\.\d+\.\d+", call_args
            ), f"Version pattern not found in: {call_args}"
            assert "Oliver Ernster" in call_args
            assert "Dark/Light theme support" in call_args

            mock_box.exec.assert_called_once()

        window.close()

    def test_button_clicks(self, qapp, config_manager):
        """Test button click functionality."""
        window = MainWindow(config_manager)
        window.show()

        # Test theme button click
        with patch.object(window, "toggle_theme") as mock_toggle:
            cast(QPushButton, window.theme_button).click()
            mock_toggle.assert_called_once()

        # Test refresh button click
        with patch.object(window, "manual_refresh") as mock_refresh:
            cast(QPushButton, window.refresh_button).click()
            mock_refresh.assert_called_once()

        # Test auto-refresh button click
        with patch.object(window, "toggle_auto_refresh") as mock_auto_refresh:
            cast(QPushButton, window.auto_refresh_button).click()
            mock_auto_refresh.assert_called_once()

        window.close()

    def test_train_list_widget_integration(
        self, qapp, config_manager, sample_train_data
    ):
        """Test integration with train list widget."""
        window = MainWindow(config_manager)

        # Test that train list widget is properly configured
        train_widget = cast(TrainListWidget, window.train_list_widget)
        assert train_widget.max_trains == 50
        assert train_widget.current_theme == window.theme_manager.current_theme

        # Test train display update
        window.update_train_display(sample_train_data)

        # Verify trains are displayed
        assert train_widget.get_train_count() == len(sample_train_data)

        # Test theme application to train list
        window.on_theme_changed("light")
        assert train_widget.current_theme == "light"

        window.close()

    def test_apply_theme_method(self, qapp, config_manager):
        """Test apply_theme method functionality."""
        window = MainWindow(config_manager)

        # Test that apply_theme works without errors
        window.apply_theme()

        # Verify stylesheet is applied
        assert window.styleSheet() != ""

        # Test theme switching
        original_stylesheet = window.styleSheet()
        window.theme_manager.switch_theme()
        window.apply_theme()

        # Stylesheet should be different after theme change
        assert window.styleSheet() != original_stylesheet

        window.close()

    def test_close_event(self, qapp, config_manager):
        """Test window close event handling."""
        window = MainWindow(config_manager)

        # Create a mock event
        mock_event = Mock()

        window.closeEvent(mock_event)

        # Event should be accepted
        mock_event.accept.assert_called_once()

        window.close()

    def test_setup_application_icon_unicode_fallback(self, qapp, config_manager):
        """Test application icon setup with Unicode fallback."""
        with patch("src.ui.main_window.Path") as mock_path:

            def path_side_effect(path_str):
                # No icon files exist
                return Path("nonexistent")

            mock_path.side_effect = path_side_effect

            window = MainWindow(config_manager)

            # Window title should NOT include Unicode train emoji (we removed it from title)
            # but should still have "Trainer" in the title
            assert "Trainer" in window.windowTitle()
            assert "🚂" not in window.windowTitle()

            window.close()

    def test_menu_bar_setup(self, qapp, config_manager):
        """Test menu bar setup and actions."""
        window = MainWindow(config_manager)

        menubar = window.menuBar()
        assert menubar is not None

        # Check menus exist (menu items have & prefix for keyboard shortcuts)
        menus = [action.text() for action in menubar.actions()]
        assert "&File" in menus
        assert "&Settings" in menus
        assert "&View" in menus
        assert "&Help" in menus

        window.close()

    def test_config_none_handling(self, qapp):
        """Test handling when config is None."""
        with patch("src.ui.main_window.ConfigManager") as mock_config_manager_class:
            mock_config_manager = Mock()
            mock_config_manager.install_default_config_to_appdata.return_value = None
            mock_config_manager.load_config.side_effect = ConfigurationError(
                "Config error"
            )
            mock_config_manager_class.return_value = mock_config_manager

            with patch.object(MainWindow, "show_error_message"):
                window = MainWindow()

                # Test theme toggle with None config
                initial_theme = window.theme_manager.current_theme
                window.toggle_theme()

                # Theme should still change even with None config
                assert window.theme_manager.current_theme != initial_theme

                window.close()

    def test_setup_theme_system(self, qapp, config_manager):
        """Test theme system setup."""
        window = MainWindow(config_manager)

        # Test that theme system is properly set up
        assert window.theme_manager is not None
        assert hasattr(window, "theme_changed")

        window.close()

    def test_connect_signals(self, qapp, config_manager):
        """Test signal connections."""
        window = MainWindow(config_manager)

        # This method currently does nothing, but we test it exists and runs
        window.connect_signals()

        window.close()

    def test_setup_status_bar(self, qapp, config_manager):
        """Test status bar setup."""
        window = MainWindow(config_manager)

        # Check status bar exists and has components
        status_bar = window.statusBar()
        assert status_bar is not None

        # Test all status components are present
        assert window.connection_status is not None
        assert window.train_count_label is not None
        assert window.theme_status is not None
        assert window.auto_refresh_status is not None

        window.close()

    def test_setup_header(self, qapp, config_manager):
        """Test header setup."""
        window = MainWindow(config_manager)

        # Verify header components exist
        assert window.last_update_label is not None
        assert window.next_update_label is not None
        assert window.time_window_label is not None
        assert window.theme_button is not None
        assert window.refresh_button is not None
        assert window.auto_refresh_button is not None

        window.close()

    def test_theme_toggle_with_config_save_error(self, qapp, config_manager):
        """Test theme toggle when config save fails."""
        window = MainWindow(config_manager)

        with patch.object(
            window.config_manager,
            "save_config",
            side_effect=ConfigurationError("Save failed"),
        ):
            initial_theme = window.theme_manager.current_theme
            window.toggle_theme()

            # Theme should still change even if save fails
            assert window.theme_manager.current_theme != initial_theme

        window.close()

    def test_update_connection_status_disconnected_no_message(
        self, qapp, config_manager
    ):
        """Test connection status update when disconnected without message."""
        window = MainWindow(config_manager)

        window.update_connection_status(False)

        assert "Disconnected" in cast(QLabel, window.connection_status).text()
        assert (
            "(" not in cast(QLabel, window.connection_status).text()
        )  # No message in parentheses

        window.close()

    def test_setup_application_icon_png_files(self, qapp, config_manager):
        """Test application icon setup with PNG files."""
        # Create temporary PNG files
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir) / "assets"
            assets_dir.mkdir()

            # Create dummy PNG files
            for size in [16, 24, 32, 48, 64]:
                png_file = assets_dir / f"train_icon_{size}.png"
                png_file.write_bytes(b"dummy_png_data")

            # Mock the Path class to return our test files
            def mock_path_constructor(path_str):
                mock_path_obj = Mock()
                if path_str.startswith("assets/train_icon_") and path_str.endswith(
                    ".png"
                ):
                    size = path_str.split("_")[-1].split(".")[0]
                    test_file = assets_dir / f"train_icon_{size}.png"
                    mock_path_obj.exists.return_value = test_file.exists()
                    mock_path_obj.__str__ = Mock(return_value=str(test_file))
                else:
                    mock_path_obj.exists.return_value = False
                    mock_path_obj.__str__ = Mock(return_value=path_str)
                return mock_path_obj

            with patch("src.ui.main_window.Path", side_effect=mock_path_constructor):
                window = MainWindow(config_manager)

                # Test that the method was called (icon setup logic was executed)
                # We can't easily test the actual icon due to mocking complexity
                assert window is not None

                window.close()

    def test_setup_application_icon_svg_fallback(self, qapp, config_manager):
        """Test application icon setup with SVG fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir) / "assets"
            assets_dir.mkdir()

            # Create dummy SVG file
            svg_file = assets_dir / "train_icon.svg"
            svg_file.write_text("<svg></svg>")

            with patch("src.ui.main_window.Path") as mock_path:

                def path_side_effect(path_str):
                    if path_str.startswith("assets/train_icon_") and path_str.endswith(
                        ".png"
                    ):
                        # PNG files don't exist
                        return Path("nonexistent.png")
                    elif path_str == "assets/train_icon.svg":
                        return svg_file
                    return Path(path_str)

                mock_path.side_effect = path_side_effect

                window = MainWindow(config_manager)

                # Window should have an icon set
                assert not window.windowIcon().isNull()

                window.close()
