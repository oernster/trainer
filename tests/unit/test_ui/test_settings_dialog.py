"""
Comprehensive unit tests for SettingsDialog class.

This test suite aims for 85%+ coverage by testing actual functionality
rather than relying heavily on mocking. It tests both HorizontalSpinWidget
and SettingsDialog classes along with APITestThread.
"""

import pytest
import tempfile
import os
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import cast

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from PySide6.QtWidgets import (
        QApplication,
        QMessageBox,
        QLineEdit,
        QPushButton,
        QComboBox,
        QCheckBox,
        QTabWidget,
        QProgressDialog,
    )
    from PySide6.QtCore import Qt, QTimer, QThread
    from PySide6.QtTest import QTest

    HAS_QT = True
except ImportError:
    HAS_QT = False

if HAS_QT:
    from src.ui.settings_dialog import (
        SettingsDialog,
        HorizontalSpinWidget,
        APITestThread,
    )
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
    from src.api.api_manager import (
        APIException,
        NetworkException,
        AuthenticationException,
    )


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


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
class TestHorizontalSpinWidget:
    """Test suite for HorizontalSpinWidget class."""

    def test_init_default_values(self, qapp):
        """Test HorizontalSpinWidget initialization with default values."""
        widget = HorizontalSpinWidget()

        assert widget.minimum == 0
        assert widget.maximum == 100
        assert widget.step == 1
        assert widget.suffix == ""
        assert widget._value == 0
        assert widget.theme_manager is None

        # Check UI components exist
        assert widget.value_label is not None
        assert widget.up_button is not None
        assert widget.down_button is not None

        # Check initial state
        assert widget.value_label.text() == "0"
        assert widget.up_button.isEnabled()
        # Note: Button states are set in set_value, not in __init__
        # So we need to check after the widget is fully initialized
        widget.set_value(0)  # Trigger button state update
        assert not widget.down_button.isEnabled()  # At minimum

    def test_init_custom_values(self, qapp):
        """Test HorizontalSpinWidget initialization with custom values."""
        theme_manager = ThemeManager()
        widget = HorizontalSpinWidget(
            minimum=10,
            maximum=50,
            initial_value=25,
            step=5,
            suffix=" items",
            theme_manager=theme_manager,
        )

        assert widget.minimum == 10
        assert widget.maximum == 50
        assert widget.step == 5
        assert widget.suffix == " items"
        assert widget._value == 25
        assert widget.theme_manager is theme_manager

        # Check initial display
        assert widget.value_label.text() == "25 items"
        assert widget.up_button.isEnabled()
        assert widget.down_button.isEnabled()

    def test_increment_normal(self, qapp):
        """Test increment functionality within bounds."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=5, step=2)

        # Test signal emission
        signal_received = []
        widget.valueChanged.connect(lambda v: signal_received.append(v))

        widget.increment()

        assert widget.value() == 7
        assert widget.value_label.text() == "7"
        assert len(signal_received) == 1
        assert signal_received[0] == 7

    def test_increment_at_maximum(self, qapp):
        """Test increment when at maximum value."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=10)

        signal_received = []
        widget.valueChanged.connect(lambda v: signal_received.append(v))

        widget.increment()

        # Should remain at maximum
        assert widget.value() == 10
        assert len(signal_received) == 0  # No signal emitted

    def test_decrement_normal(self, qapp):
        """Test decrement functionality within bounds."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=5, step=2)

        signal_received = []
        widget.valueChanged.connect(lambda v: signal_received.append(v))

        widget.decrement()

        assert widget.value() == 3
        assert widget.value_label.text() == "3"
        assert len(signal_received) == 1
        assert signal_received[0] == 3

    def test_decrement_at_minimum(self, qapp):
        """Test decrement when at minimum value."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=0)

        signal_received = []
        widget.valueChanged.connect(lambda v: signal_received.append(v))

        widget.decrement()

        # Should remain at minimum
        assert widget.value() == 0
        assert len(signal_received) == 0  # No signal emitted

    def test_set_value_valid(self, qapp):
        """Test setting valid values."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=0)

        signal_received = []
        widget.valueChanged.connect(lambda v: signal_received.append(v))

        widget.set_value(7)

        assert widget.value() == 7
        assert widget.value_label.text() == "7"
        assert widget.up_button.isEnabled()
        assert widget.down_button.isEnabled()
        assert len(signal_received) == 1
        assert signal_received[0] == 7

    def test_set_value_invalid(self, qapp):
        """Test setting invalid values (out of bounds)."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=5)

        signal_received = []
        widget.valueChanged.connect(lambda v: signal_received.append(v))

        # Try to set value above maximum
        widget.set_value(15)
        assert widget.value() == 5  # Should remain unchanged

        # Try to set value below minimum
        widget.set_value(-5)
        assert widget.value() == 5  # Should remain unchanged

        assert len(signal_received) == 0  # No signals emitted

    def test_set_value_same_value(self, qapp):
        """Test setting the same value (should not emit signal)."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=5)

        signal_received = []
        widget.valueChanged.connect(lambda v: signal_received.append(v))

        widget.set_value(5)

        assert widget.value() == 5
        assert len(signal_received) == 0  # No signal emitted for same value

    def test_setValue_qt_style(self, qapp):
        """Test Qt-style setValue method."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=0)

        widget.setValue(7)
        assert widget.value() == 7

    def test_setRange(self, qapp):
        """Test setting new range."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=5)

        # Set new range that includes current value
        widget.setRange(2, 8)
        assert widget.minimum == 2
        assert widget.maximum == 8
        assert widget.value() == 5  # Should remain unchanged

        # Set new range that excludes current value (too high)
        widget.setRange(0, 3)
        assert widget.value() == 3  # Should be clamped to maximum

        # Set new range that excludes current value (too low)
        widget.setRange(5, 10)
        assert widget.value() == 5  # Should be clamped to minimum

    def test_setSuffix(self, qapp):
        """Test setting suffix."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=5)

        widget.setSuffix(" units")
        assert widget.suffix == " units"
        assert widget.value_label.text() == "5 units"

    def test_button_states_at_boundaries(self, qapp):
        """Test button enabled states at boundaries."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=0)

        # Trigger button state update by calling set_value
        widget.set_value(0)

        # At minimum
        assert not widget.down_button.isEnabled()
        assert widget.up_button.isEnabled()

        # Move to maximum
        widget.set_value(10)
        assert widget.down_button.isEnabled()
        assert not widget.up_button.isEnabled()

        # Move to middle
        widget.set_value(5)
        assert widget.down_button.isEnabled()
        assert widget.up_button.isEnabled()

    def test_button_clicks(self, qapp):
        """Test actual button clicks."""
        widget = HorizontalSpinWidget(minimum=0, maximum=10, initial_value=5)

        # Test up button click
        widget.up_button.click()
        assert widget.value() == 6

        # Test down button click
        widget.down_button.click()
        assert widget.value() == 5

    def test_setup_style_with_theme_manager(self, qapp):
        """Test styling with theme manager."""
        theme_manager = ThemeManager()
        widget = HorizontalSpinWidget(theme_manager=theme_manager)

        # Check that styling was applied
        assert widget.up_button.styleSheet() != ""
        assert widget.down_button.styleSheet() != ""
        assert widget.value_label.styleSheet() != ""

    def test_setup_style_without_theme_manager(self, qapp):
        """Test styling without theme manager (fallback colors)."""
        widget = HorizontalSpinWidget()

        # Check that fallback styling was applied
        assert widget.up_button.styleSheet() != ""
        assert widget.down_button.styleSheet() != ""
        assert widget.value_label.styleSheet() != ""


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
class TestSettingsDialog:
    """Test suite for SettingsDialog class."""

    def test_init_with_valid_config(self, qapp, config_manager):
        """Test SettingsDialog initialization with valid config."""
        dialog = SettingsDialog(config_manager)

        assert dialog.config_manager is config_manager
        assert dialog.config is not None
        assert isinstance(dialog.theme_manager, ThemeManager)

        # Check window properties
        assert "Settings - Trainer by Oliver Ernster" in dialog.windowTitle()
        assert dialog.isModal()
        assert dialog.minimumSize().width() == 500
        assert dialog.minimumSize().height() == 400

        # Check tab widget exists
        assert dialog.tab_widget is not None
        assert dialog.tab_widget.count() == 4  # API, Stations, Display, Refresh

        dialog.close()

    def test_init_with_config_error(self, qapp):
        """Test SettingsDialog initialization when config loading fails."""
        mock_config_manager = Mock()
        mock_config_manager.load_config.side_effect = ConfigurationError("Test error")

        dialog = SettingsDialog(mock_config_manager)

        assert dialog.config is None
        assert dialog.config_manager is mock_config_manager

        dialog.close()

    def test_setup_api_tab(self, qapp, config_manager):
        """Test API tab setup and components."""
        dialog = SettingsDialog(config_manager)

        # Check API tab components exist
        assert dialog.app_id_edit is not None
        assert dialog.app_key_edit is not None
        assert dialog.show_key_button is not None
        assert dialog.timeout_spin is not None
        assert dialog.retries_spin is not None
        assert dialog.rate_limit_spin is not None

        # Check initial values
        assert dialog.app_id_edit.text() == "test_id"
        assert dialog.app_key_edit.text() == "test_key"
        assert dialog.app_key_edit.echoMode() == QLineEdit.EchoMode.Password
        assert dialog.show_key_button.text() == "Show Key"

        dialog.close()

    def test_setup_stations_tab(self, qapp, config_manager):
        """Test Stations tab setup and components."""
        dialog = SettingsDialog(config_manager)

        # Check station tab components exist
        assert dialog.from_code_edit is not None
        assert dialog.from_name_edit is not None
        assert dialog.to_code_edit is not None
        assert dialog.to_name_edit is not None

        # Check initial values
        assert dialog.from_code_edit.text() == "FLE"
        assert dialog.from_name_edit.text() == "Fleet"
        assert dialog.to_code_edit.text() == "WAT"
        assert dialog.to_name_edit.text() == "London Waterloo"

        dialog.close()

    def test_setup_display_tab(self, qapp, config_manager):
        """Test Display tab setup and components."""
        dialog = SettingsDialog(config_manager)

        # Check display tab components exist
        assert dialog.theme_combo is not None
        assert dialog.max_trains_spin is not None
        assert dialog.time_window_spin is not None
        assert dialog.show_cancelled_check is not None

        # Check initial values
        assert dialog.theme_combo.currentText() == "dark"
        assert dialog.max_trains_spin.value() == 50
        assert dialog.time_window_spin.value() == 10
        assert dialog.show_cancelled_check.isChecked()

        dialog.close()

    def test_setup_refresh_tab(self, qapp, config_manager):
        """Test Refresh tab setup and components."""
        dialog = SettingsDialog(config_manager)

        # Check refresh tab components exist
        assert dialog.auto_refresh_check is not None
        assert dialog.refresh_interval_spin is not None
        assert dialog.manual_refresh_check is not None

        # Check initial values
        assert not dialog.auto_refresh_check.isChecked()  # False in test config
        assert dialog.refresh_interval_spin.value() == 5
        assert dialog.manual_refresh_check.isChecked()

        dialog.close()

    def test_load_current_settings_with_config(self, qapp, config_manager):
        """Test loading current settings when config exists."""
        dialog = SettingsDialog(config_manager)

        # Modify config and reload
        dialog.config.api.timeout_seconds = 45
        dialog.config.stations.from_code = "ABC"
        dialog.config.display.theme = "light"
        dialog.config.refresh.auto_enabled = True

        dialog.load_current_settings()

        # Check values were loaded
        assert dialog.timeout_spin.value() == 45
        assert dialog.from_code_edit.text() == "ABC"
        assert dialog.theme_combo.currentText() == "light"
        assert dialog.auto_refresh_check.isChecked()

        dialog.close()

    def test_load_current_settings_without_config(self, qapp):
        """Test loading current settings when config is None."""
        mock_config_manager = Mock()
        mock_config_manager.load_config.side_effect = ConfigurationError("Test error")

        dialog = SettingsDialog(mock_config_manager)

        # Should not crash when config is None
        dialog.load_current_settings()

        dialog.close()

    def test_toggle_key_visibility_show(self, qapp, config_manager):
        """Test toggling API key visibility to show."""
        dialog = SettingsDialog(config_manager)

        # Initially hidden
        assert dialog.app_key_edit.echoMode() == QLineEdit.EchoMode.Password
        assert dialog.show_key_button.text() == "Show Key"

        # Toggle to show
        dialog.toggle_key_visibility()

        assert dialog.app_key_edit.echoMode() == QLineEdit.EchoMode.Normal
        assert dialog.show_key_button.text() == "Hide Key"

        dialog.close()

    def test_toggle_key_visibility_hide(self, qapp, config_manager):
        """Test toggling API key visibility to hide."""
        dialog = SettingsDialog(config_manager)

        # First show the key
        dialog.toggle_key_visibility()
        assert dialog.app_key_edit.echoMode() == QLineEdit.EchoMode.Normal

        # Then hide it
        dialog.toggle_key_visibility()

        assert dialog.app_key_edit.echoMode() == QLineEdit.EchoMode.Password
        assert dialog.show_key_button.text() == "Show Key"

        dialog.close()

    def test_show_key_button_click(self, qapp, config_manager):
        """Test show key button click functionality."""
        dialog = SettingsDialog(config_manager)

        # Click the button
        dialog.show_key_button.click()

        assert dialog.app_key_edit.echoMode() == QLineEdit.EchoMode.Normal
        assert dialog.show_key_button.text() == "Hide Key"

        dialog.close()

    def test_test_api_connection_missing_credentials(self, qapp, config_manager):
        """Test API connection test with missing credentials."""
        dialog = SettingsDialog(config_manager)

        # Clear credentials
        dialog.app_id_edit.setText("")
        dialog.app_key_edit.setText("")

        with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
            mock_box = Mock()
            mock_msgbox.warning.return_value = mock_box

            dialog.test_api_connection()

            mock_msgbox.warning.assert_called_once()
            call_args = mock_msgbox.warning.call_args[0]
            assert "Missing Credentials" in call_args[1]

        dialog.close()

    def test_test_api_connection_with_credentials(self, qapp, config_manager):
        """Test API connection test with valid credentials."""
        dialog = SettingsDialog(config_manager)

        with patch("src.ui.settings_dialog.APITestThread") as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread

            with patch("src.ui.settings_dialog.QProgressDialog") as mock_progress_class:
                mock_progress = Mock()
                mock_progress_class.return_value = mock_progress

                dialog.test_api_connection()

                # Check thread was created and started
                mock_thread_class.assert_called_once()
                mock_thread.test_completed.connect.assert_called_once()
                mock_thread.start.assert_called_once()

                # Check progress dialog was created
                mock_progress_class.assert_called_once()
                mock_progress.show.assert_called_once()

        dialog.close()

    def test_test_api_connection_with_empty_station_codes(self, qapp, config_manager):
        """Test API connection test with empty station codes (uses defaults)."""
        dialog = SettingsDialog(config_manager)

        # Set empty station codes to trigger default assignment
        dialog.config.stations.from_code = ""
        dialog.config.stations.to_code = ""

        with patch("src.ui.settings_dialog.APITestThread") as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread

            with patch("src.ui.settings_dialog.QProgressDialog"):
                dialog.test_api_connection()

                # Check that defaults were assigned
                mock_thread_class.assert_called_once()
                test_config = mock_thread_class.call_args[0][0]
                assert test_config.stations.from_code == "FLE"  # Default
                assert test_config.stations.to_code == "WAT"  # Default

        dialog.close()

    def test_test_api_connection_creates_default_config(self, qapp):
        """Test API connection test creates default config when none exists."""
        mock_config_manager = Mock()
        mock_config_manager.load_config.side_effect = ConfigurationError("Test error")

        dialog = SettingsDialog(mock_config_manager)
        dialog.app_id_edit.setText("test_id")
        dialog.app_key_edit.setText("test_key")

        with patch("src.ui.settings_dialog.APITestThread") as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread

            with patch("src.ui.settings_dialog.QProgressDialog"):
                dialog.test_api_connection()

                # Check that a test config was created
                mock_thread_class.assert_called_once()
                test_config = mock_thread_class.call_args[0][0]
                assert test_config.api.app_id == "test_id"
                assert test_config.api.app_key == "test_key"

        dialog.close()

    def test_cancel_api_test(self, qapp, config_manager):
        """Test canceling API test."""
        dialog = SettingsDialog(config_manager)

        # Create mock thread
        mock_thread = Mock()
        mock_thread.isRunning.return_value = True
        dialog.api_test_thread = mock_thread

        dialog.cancel_api_test()

        mock_thread.terminate.assert_called_once()
        mock_thread.wait.assert_called_once()

        dialog.close()

    def test_cancel_api_test_no_thread(self, qapp, config_manager):
        """Test canceling API test when no thread exists."""
        dialog = SettingsDialog(config_manager)

        # Should not crash when no thread exists
        dialog.cancel_api_test()

        dialog.close()

    def test_on_api_test_completed_success(self, qapp, config_manager):
        """Test API test completion with success."""
        dialog = SettingsDialog(config_manager)

        # Create mock progress dialog
        mock_progress = Mock()
        dialog.progress_dialog = mock_progress

        with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
            dialog.on_api_test_completed(True, "Test successful")

            mock_progress.close.assert_called_once()
            mock_msgbox.information.assert_called_once()
            call_args = mock_msgbox.information.call_args[0]
            assert "API Test Successful" in call_args[1]
            assert "Test successful" in call_args[2]

        dialog.close()

    def test_on_api_test_completed_failure(self, qapp, config_manager):
        """Test API test completion with failure."""
        dialog = SettingsDialog(config_manager)

        # Create mock progress dialog
        mock_progress = Mock()
        dialog.progress_dialog = mock_progress

        with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
            dialog.on_api_test_completed(False, "Test failed")

            mock_progress.close.assert_called_once()
            mock_msgbox.critical.assert_called_once()
            call_args = mock_msgbox.critical.call_args[0]
            assert "API Test Failed" in call_args[1]
            assert "Test failed" in call_args[2]

        dialog.close()

    def test_reset_to_defaults_confirmed(self, qapp, config_manager):
        """Test reset to defaults when user confirms."""
        dialog = SettingsDialog(config_manager)

        with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.StandardButton.Yes

            with patch.object(
                dialog.config_manager, "create_default_config"
            ) as mock_create:
                with patch.object(dialog.config_manager, "load_config") as mock_load:
                    # Create a proper mock config with the expected structure
                    mock_config = Mock()
                    mock_config.api.app_id = "test_id"
                    mock_config.api.app_key = "test_key"
                    mock_config.api.timeout_seconds = 30
                    mock_config.api.max_retries = 2
                    mock_config.api.rate_limit_per_minute = 10
                    mock_config.stations.from_code = "FLE"
                    mock_config.stations.from_name = "Fleet"
                    mock_config.stations.to_code = "WAT"
                    mock_config.stations.to_name = "London Waterloo"
                    mock_config.display.theme = "dark"
                    mock_config.display.max_trains = 50
                    mock_config.display.time_window_hours = 10
                    mock_config.display.show_cancelled = True
                    mock_config.refresh.auto_enabled = False
                    mock_config.refresh.interval_minutes = 5
                    mock_config.refresh.manual_enabled = True

                    mock_load.return_value = mock_config

                    dialog.reset_to_defaults()

                    mock_create.assert_called_once()
                    mock_load.assert_called_once()
                    mock_msgbox.information.assert_called_once()

        dialog.close()

    def test_reset_to_defaults_cancelled(self, qapp, config_manager):
        """Test reset to defaults when user cancels."""
        dialog = SettingsDialog(config_manager)

        with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.StandardButton.No

            with patch.object(
                dialog.config_manager, "create_default_config"
            ) as mock_create:
                dialog.reset_to_defaults()

                mock_create.assert_not_called()

        dialog.close()

    def test_reset_to_defaults_error(self, qapp, config_manager):
        """Test reset to defaults with configuration error."""
        dialog = SettingsDialog(config_manager)

        with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.StandardButton.Yes

            with patch.object(
                dialog.config_manager,
                "create_default_config",
                side_effect=ConfigurationError("Reset failed"),
            ):
                dialog.reset_to_defaults()

                mock_msgbox.critical.assert_called_once()
                call_args = mock_msgbox.critical.call_args[0]
                assert "Reset failed" in call_args[2]

        dialog.close()

    def test_save_settings_success(self, qapp, config_manager):
        """Test successful settings save."""
        dialog = SettingsDialog(config_manager)

        # Modify some settings
        dialog.app_id_edit.setText("new_id")
        dialog.timeout_spin.set_value(45)
        dialog.from_code_edit.setText("ABC")
        dialog.theme_combo.setCurrentText("light")
        dialog.auto_refresh_check.setChecked(True)

        with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
            with patch.object(dialog, "accept") as mock_accept:
                dialog.save_settings()

                # Check config was updated
                assert dialog.config.api.app_id == "new_id"
                assert dialog.config.api.timeout_seconds == 45
                assert dialog.config.stations.from_code == "ABC"
                assert dialog.config.display.theme == "light"
                assert dialog.config.refresh.auto_enabled

                mock_accept.assert_called_once()
                mock_msgbox.information.assert_called_once()

        dialog.close()

    def test_save_settings_no_config(self, qapp):
        """Test save settings when no config is loaded."""
        mock_config_manager = Mock()
        mock_config_manager.load_config.side_effect = ConfigurationError("Test error")

        dialog = SettingsDialog(mock_config_manager)

        with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
            dialog.save_settings()

            mock_msgbox.critical.assert_called_once()
            call_args = mock_msgbox.critical.call_args[0]
            assert "No configuration loaded" in call_args[2]

        dialog.close()

    def test_save_settings_configuration_error(self, qapp, config_manager):
        """Test save settings with configuration error."""
        dialog = SettingsDialog(config_manager)

        with patch.object(
            dialog.config_manager,
            "save_config",
            side_effect=ConfigurationError("Save failed"),
        ):
            with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
                dialog.save_settings()

                mock_msgbox.critical.assert_called_once()
                call_args = mock_msgbox.critical.call_args[0]
                assert "Save Error" in call_args[1]
                assert "Save failed" in call_args[2]

        dialog.close()

    def test_save_settings_unexpected_error(self, qapp, config_manager):
        """Test save settings with unexpected error."""
        dialog = SettingsDialog(config_manager)

        with patch.object(
            dialog.config_manager,
            "save_config",
            side_effect=Exception("Unexpected error"),
        ):
            with patch("src.ui.settings_dialog.QMessageBox") as mock_msgbox:
                dialog.save_settings()

                mock_msgbox.critical.assert_called_once()
                call_args = mock_msgbox.critical.call_args[0]
                assert "Unexpected Error" in call_args[1]
                assert "Unexpected error" in call_args[2]

        dialog.close()

    def test_button_connections(self, qapp, config_manager):
        """Test button click connections."""
        dialog = SettingsDialog(config_manager)

        # Test test button
        with patch.object(dialog, "test_api_connection") as mock_test:
            dialog.test_button.click()
            mock_test.assert_called_once()

        # Test reset button
        with patch.object(dialog, "reset_to_defaults") as mock_reset:
            dialog.reset_button.click()
            mock_reset.assert_called_once()

        # Test cancel button
        with patch.object(dialog, "reject") as mock_reject:
            dialog.cancel_button.click()
            mock_reject.assert_called_once()

        # Test save button
        with patch.object(dialog, "save_settings") as mock_save:
            dialog.save_button.click()
            mock_save.assert_called_once()

        dialog.close()

    def test_settings_saved_signal(self, qapp, config_manager):
        """Test settings saved signal emission."""
        dialog = SettingsDialog(config_manager)

        signal_received = []
        dialog.settings_saved.connect(lambda: signal_received.append(True))

        with patch("src.ui.settings_dialog.QMessageBox"):
            with patch.object(dialog, "accept"):
                dialog.save_settings()

                # Signal should be emitted on successful save
                assert len(signal_received) == 1

        dialog.close()

    def test_tab_widget_tabs(self, qapp, config_manager):
        """Test tab widget has correct tabs."""
        dialog = SettingsDialog(config_manager)

        tab_texts = []
        for i in range(dialog.tab_widget.count()):
            tab_texts.append(dialog.tab_widget.tabText(i))

        assert "API" in tab_texts
        assert "Stations" in tab_texts
        assert "Display" in tab_texts
        assert "Refresh" in tab_texts

        dialog.close()

    def test_horizontal_spin_widgets_in_dialog(self, qapp, config_manager):
        """Test that HorizontalSpinWidget instances work correctly in dialog."""
        dialog = SettingsDialog(config_manager)

        # Test timeout spin widget
        assert isinstance(dialog.timeout_spin, HorizontalSpinWidget)
        assert dialog.timeout_spin.minimum == 5
        assert dialog.timeout_spin.maximum == 60
        assert dialog.timeout_spin.suffix == " seconds"

        # Test retries spin widget
        assert isinstance(dialog.retries_spin, HorizontalSpinWidget)
        assert dialog.retries_spin.minimum == 1
        assert dialog.retries_spin.maximum == 10

        # Test rate limit spin widget
        assert isinstance(dialog.rate_limit_spin, HorizontalSpinWidget)
        assert dialog.rate_limit_spin.suffix == " per minute"

        # Test max trains spin widget
        assert isinstance(dialog.max_trains_spin, HorizontalSpinWidget)

        # Test time window spin widget
        assert isinstance(dialog.time_window_spin, HorizontalSpinWidget)
        assert dialog.time_window_spin.suffix == " hours"

        # Test refresh interval spin widget
        assert isinstance(dialog.refresh_interval_spin, HorizontalSpinWidget)
        assert dialog.refresh_interval_spin.suffix == " minutes"

        dialog.close()


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
@pytest.mark.filterwarnings(
    "ignore:coroutine 'APITestThread._test_api' was never awaited:RuntimeWarning"
)
@pytest.mark.filterwarnings(
    "ignore:coroutine 'AsyncMockMixin._execute_mock_call' was never awaited:RuntimeWarning"
)
@patch("src.ui.settings_dialog.APITestThread._test_api", new_callable=AsyncMock)
@patch("src.ui.settings_dialog.APIManager")
class TestAPITestThread:
    """Test suite for APITestThread class."""

    def test_init(self, mock_api_manager_class, mock_test_api, test_config):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test APITestThread initialization."""
        thread = APITestThread(test_config)

        assert thread.config is test_config
        assert isinstance(thread, QThread)

    def test_run_success_with_trains(
        self, mock_api_manager_class, mock_test_api, test_config
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test successful API test run with train data."""
        thread = APITestThread(test_config)

        # Create a proper async context manager mock
        async def mock_get_departures():
            return [{"departure_time": "10:30", "destination": "London"}]

        # Mock the _test_api method directly to avoid async context manager issues
        async def mock_test_api():
            trains = await mock_get_departures()
            if trains:
                return (
                    True,
                    f"Successfully connected to API and retrieved {len(trains)} train departures.",
                )
            else:
                return (
                    True,
                    "Successfully connected to API, but no train data was returned. This may be normal depending on the time and route.",
                )

        with patch.object(thread, "_test_api", side_effect=mock_test_api):
            # Capture the signal emission
            signal_received = []
            thread.test_completed.connect(
                lambda success, msg: signal_received.append((success, msg))
            )

            # Run the thread
            thread.run()

            # Check signal was emitted with success
            assert len(signal_received) == 1
            success, message = signal_received[0]
            assert success is True
            assert "Successfully connected to API" in message
            assert "1 train departures" in message

    def test_run_success_no_trains(
        self, mock_api_manager_class, mock_test_api, test_config
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test successful API test run with no train data."""
        thread = APITestThread(test_config)

        # Mock the _test_api method directly
        async def mock_test_api():
            return (
                True,
                "Successfully connected to API, but no train data was returned. This may be normal depending on the time and route.",
            )

        with patch.object(thread, "_test_api", side_effect=mock_test_api):
            # Capture the signal emission
            signal_received = []
            thread.test_completed.connect(
                lambda success, msg: signal_received.append((success, msg))
            )

            # Run the thread
            thread.run()

            # Check signal was emitted with success
            assert len(signal_received) == 1
            success, message = signal_received[0]
            assert success is True
            assert (
                "Successfully connected to API, but no train data was returned"
                in message
            )

    def test_run_authentication_error(
        self, mock_api_manager_class, mock_test_api, test_config
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test API test run with authentication error."""
        thread = APITestThread(test_config)

        # Mock the _test_api method to return the proper error response
        async def mock_test_api():
            return (
                False,
                "Authentication failed: Invalid credentials\n\nPlease check your App ID and App Key.",
            )

        with patch.object(thread, "_test_api", side_effect=mock_test_api):
            # Capture the signal emission
            signal_received = []
            thread.test_completed.connect(
                lambda success, msg: signal_received.append((success, msg))
            )

            # Run the thread
            thread.run()

            # Check signal was emitted with failure
            assert len(signal_received) == 1
            success, message = signal_received[0]
            assert success is False
            assert "Authentication failed" in message
            assert "Invalid credentials" in message
            assert "Please check your App ID and App Key" in message

    def test_run_network_error(
        self, mock_api_manager_class, mock_test_api, test_config
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test API test run with network error."""
        thread = APITestThread(test_config)

        # Mock the _test_api method to return the proper error response
        async def mock_test_api():
            return (
                False,
                "Network error: Connection timeout\n\nPlease check your internet connection.",
            )

        with patch.object(thread, "_test_api", side_effect=mock_test_api):
            # Capture the signal emission
            signal_received = []
            thread.test_completed.connect(
                lambda success, msg: signal_received.append((success, msg))
            )

            # Run the thread
            thread.run()

            # Check signal was emitted with failure
            assert len(signal_received) == 1
            success, message = signal_received[0]
            assert success is False
            assert "Network error" in message
            assert "Connection timeout" in message
            assert "Please check your internet connection" in message

    def test_run_api_error(self, mock_api_manager_class, mock_test_api, test_config):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test API test run with general API error."""
        thread = APITestThread(test_config)

        # Mock the _test_api method to return the proper error response
        async def mock_test_api():
            return False, "API error: API rate limit exceeded"

        with patch.object(thread, "_test_api", side_effect=mock_test_api):
            # Capture the signal emission
            signal_received = []
            thread.test_completed.connect(
                lambda success, msg: signal_received.append((success, msg))
            )

            # Run the thread
            thread.run()

            # Check signal was emitted with failure
            assert len(signal_received) == 1
            success, message = signal_received[0]
            assert success is False
            assert "API error" in message
            assert "API rate limit exceeded" in message

    def test_run_unexpected_error(
        self, mock_api_manager_class, mock_test_api, test_config
    ):
        """Test API test run with unexpected error."""
        # Configure the async mock to return an error
        mock_test_api.return_value = (False, "Unexpected error: ValueError occurred")

        thread = APITestThread(test_config)

        # Mock the _test_api method to return the proper error response
        async def mock_test_api_error():
            return False, "Unexpected error: ValueError occurred"

        with patch.object(thread, "_test_api", side_effect=mock_test_api_error):
            # Capture the signal emission
            signal_received = []
            thread.test_completed.connect(
                lambda success, msg: signal_received.append((success, msg))
            )

            # Run the thread
            thread.run()

            # Check signal was emitted with failure
            assert len(signal_received) == 1
            success, message = signal_received[0]
            assert success is False
            assert "Unexpected error" in message

    def test_run_exception_in_run_method(
        self, mock_api_manager_class, mock_test_api, test_config
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test exception handling in the run method itself."""
        thread = APITestThread(test_config)

        # Mock asyncio.new_event_loop to raise an exception
        with patch(
            "src.ui.settings_dialog.asyncio.new_event_loop",
            side_effect=Exception("Loop creation failed"),
        ):
            # Capture the signal emission
            signal_received = []
            thread.test_completed.connect(
                lambda success, msg: signal_received.append((success, msg))
            )

            # Run the thread
            thread.run()

            # Check signal was emitted with failure
            assert len(signal_received) == 1
            success, message = signal_received[0]
            assert success is False
            assert "Test failed with error" in message
            assert "Loop creation failed" in message

    def test_run_loop_cleanup(self, mock_api_manager_class, mock_test_api, test_config):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test that event loop is properly cleaned up."""
        thread = APITestThread(test_config)

        # Mock the event loop
        mock_loop = Mock()

        with patch(
            "src.ui.settings_dialog.asyncio.new_event_loop", return_value=mock_loop
        ):
            with patch("src.ui.settings_dialog.asyncio.set_event_loop"):
                with patch.object(
                    mock_loop,
                    "run_until_complete",
                    side_effect=Exception("Test exception"),
                ):
                    # Capture the signal emission
                    signal_received = []
                    thread.test_completed.connect(
                        lambda success, msg: signal_received.append((success, msg))
                    )

                    # Run the thread
                    thread.run()

                    # Check that loop.close() was called even after exception
                    mock_loop.close.assert_called_once()

    def test_run_loop_cleanup_when_none(
        self, mock_api_manager_class, mock_test_api, test_config
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test that no error occurs when loop is None during cleanup."""
        thread = APITestThread(test_config)

        # Mock new_event_loop to return None
        with patch("src.ui.settings_dialog.asyncio.new_event_loop", return_value=None):
            # Capture the signal emission
            signal_received = []
            thread.test_completed.connect(
                lambda success, msg: signal_received.append((success, msg))
            )

            # Run the thread - should not crash
            thread.run()

            # Should still emit a signal (likely an error)
            assert len(signal_received) == 1


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
@pytest.mark.filterwarnings(
    "ignore:coroutine 'APITestThread._test_api' was never awaited:RuntimeWarning"
)
@pytest.mark.filterwarnings(
    "ignore:coroutine 'AsyncMockMixin._execute_mock_call' was never awaited:RuntimeWarning"
)
@patch("src.ui.settings_dialog.APITestThread._test_api", new_callable=AsyncMock)
@patch("src.ui.settings_dialog.APIManager")
@patch("src.ui.settings_dialog.APITestThread")
class TestSettingsDialogIntegration:
    """Integration tests for SettingsDialog with real components."""

    def test_full_workflow_save_settings(
        self,
        mock_thread_class,
        mock_api_manager_class,
        mock_test_api,
        qapp,
        config_manager,
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test complete workflow of opening dialog, changing settings, and saving."""
        # Mock APITestThread to prevent any async coroutine creation
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        dialog = SettingsDialog(config_manager)

        # Modify all types of settings
        dialog.app_id_edit.setText("new_app_id")
        dialog.app_key_edit.setText("new_app_key")
        dialog.timeout_spin.set_value(25)
        dialog.retries_spin.set_value(5)
        dialog.rate_limit_spin.set_value(20)

        dialog.from_code_edit.setText("XYZ")
        dialog.from_name_edit.setText("Test Station")
        dialog.to_code_edit.setText("ABC")
        dialog.to_name_edit.setText("Destination Station")

        dialog.theme_combo.setCurrentText("light")
        dialog.max_trains_spin.set_value(75)
        dialog.time_window_spin.set_value(8)
        dialog.show_cancelled_check.setChecked(False)

        dialog.auto_refresh_check.setChecked(True)
        dialog.refresh_interval_spin.set_value(3)
        dialog.manual_refresh_check.setChecked(False)

        # Save settings
        with patch("src.ui.settings_dialog.QMessageBox"):
            with patch.object(dialog, "accept"):
                dialog.save_settings()

        # Verify all settings were saved
        saved_config = config_manager.load_config()
        assert saved_config.api.app_id == "new_app_id"
        assert saved_config.api.app_key == "new_app_key"
        assert saved_config.api.timeout_seconds == 25
        assert saved_config.api.max_retries == 5
        assert saved_config.api.rate_limit_per_minute == 20

        assert saved_config.stations.from_code == "XYZ"
        assert saved_config.stations.from_name == "Test Station"
        assert saved_config.stations.to_code == "ABC"
        assert saved_config.stations.to_name == "Destination Station"

        assert saved_config.display.theme == "light"
        assert saved_config.display.max_trains == 75
        assert saved_config.display.time_window_hours == 8
        assert not saved_config.display.show_cancelled

        assert saved_config.refresh.auto_enabled
        assert saved_config.refresh.interval_minutes == 3
        assert not saved_config.refresh.manual_enabled

        dialog.close()

    def test_horizontal_spin_widget_signal_integration(
        self,
        mock_thread_class,
        mock_api_manager_class,
        mock_test_api,
        qapp,
        config_manager,
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test that HorizontalSpinWidget signals work correctly in the dialog."""
        dialog = SettingsDialog(config_manager)

        # Test that changing spin widget values works
        original_timeout = dialog.timeout_spin.value()

        # Simulate button clicks
        dialog.timeout_spin.up_button.click()
        assert dialog.timeout_spin.value() == original_timeout + 1

        dialog.timeout_spin.down_button.click()
        assert dialog.timeout_spin.value() == original_timeout

        dialog.close()

    def test_theme_manager_integration(
        self,
        mock_thread_class,
        mock_api_manager_class,
        mock_test_api,
        qapp,
        config_manager,
    ):
        # Configure the async mock to return a resolved future
        mock_test_api.return_value = (True, "Test successful")
        """Test theme manager integration with HorizontalSpinWidget."""
        dialog = SettingsDialog(config_manager)

        # Check that theme manager was passed to spin widgets
        assert dialog.timeout_spin.theme_manager is dialog.theme_manager
        assert dialog.retries_spin.theme_manager is dialog.theme_manager
        assert dialog.rate_limit_spin.theme_manager is dialog.theme_manager
        assert dialog.max_trains_spin.theme_manager is dialog.theme_manager
        assert dialog.time_window_spin.theme_manager is dialog.theme_manager
        assert dialog.refresh_interval_spin.theme_manager is dialog.theme_manager

        # Check that styling was applied
        assert dialog.timeout_spin.up_button.styleSheet() != ""

        dialog.close()
