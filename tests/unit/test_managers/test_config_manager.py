"""
Unit tests for ConfigManager and related configuration classes.

Tests configuration management with real file operations,
emphasizing actual file I/O over mocking.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from src.managers.config_manager import (
    ConfigManager,
    ConfigData,
    APIConfig,
    StationConfig,
    RefreshConfig,
    DisplayConfig,
    ConfigurationError,
)


class TestAPIConfig:
    """Test APIConfig model."""

    def test_api_config_creation(self):
        """Test creating APIConfig with valid data."""
        config = APIConfig(
            app_id="test_id",
            app_key="test_key",
            base_url="https://api.example.com",
            timeout_seconds=15,
            max_retries=5,
            rate_limit_per_minute=20,
        )

        assert config.app_id == "test_id"
        assert config.app_key == "test_key"
        assert config.base_url == "https://api.example.com"
        assert config.timeout_seconds == 15
        assert config.max_retries == 5
        assert config.rate_limit_per_minute == 20

    def test_api_config_defaults(self):
        """Test APIConfig with default values."""
        config = APIConfig(app_id="test_id", app_key="test_key")

        assert config.base_url == "https://transportapi.com/v3/uk"
        assert config.timeout_seconds == 10
        assert config.max_retries == 3
        assert config.rate_limit_per_minute == 30


class TestStationConfig:
    """Test StationConfig model."""

    def test_station_config_defaults(self):
        """Test StationConfig with default values."""
        config = StationConfig()

        assert config.from_code == "FLE"
        assert config.from_name == "Fleet"
        assert config.to_code == "WAT"
        assert config.to_name == "London Waterloo"

    def test_station_config_custom(self):
        """Test StationConfig with custom values."""
        config = StationConfig(
            from_code="ABC",
            from_name="Test Station A",
            to_code="XYZ",
            to_name="Test Station B",
        )

        assert config.from_code == "ABC"
        assert config.from_name == "Test Station A"
        assert config.to_code == "XYZ"
        assert config.to_name == "Test Station B"


class TestRefreshConfig:
    """Test RefreshConfig model."""

    def test_refresh_config_defaults(self):
        """Test RefreshConfig with default values."""
        config = RefreshConfig()

        assert config.auto_enabled == True
        assert config.interval_minutes == 2
        assert config.manual_enabled == True

    def test_refresh_config_custom(self):
        """Test RefreshConfig with custom values."""
        config = RefreshConfig(
            auto_enabled=False, interval_minutes=10, manual_enabled=False
        )

        assert config.auto_enabled == False
        assert config.interval_minutes == 10
        assert config.manual_enabled == False


class TestDisplayConfig:
    """Test DisplayConfig model."""

    def test_display_config_defaults(self):
        """Test DisplayConfig with default values."""
        config = DisplayConfig()

        assert config.max_trains == 50
        assert config.time_window_hours == 10
        assert config.show_cancelled == True
        assert config.theme == "dark"

    def test_display_config_custom(self):
        """Test DisplayConfig with custom values."""
        config = DisplayConfig(
            max_trains=25, time_window_hours=6, show_cancelled=False, theme="light"
        )

        assert config.max_trains == 25
        assert config.time_window_hours == 6
        assert config.show_cancelled == False
        assert config.theme == "light"


class TestConfigData:
    """Test ConfigData main configuration model."""

    def test_config_data_creation(self):
        """Test creating complete ConfigData."""
        config = ConfigData(
            api=APIConfig(app_id="test_id", app_key="test_key"),
            stations=StationConfig(),
            refresh=RefreshConfig(),
            display=DisplayConfig(),
        )

        assert isinstance(config.api, APIConfig)
        assert isinstance(config.stations, StationConfig)
        assert isinstance(config.refresh, RefreshConfig)
        assert isinstance(config.display, DisplayConfig)

        assert config.api.app_id == "test_id"
        assert config.stations.from_code == "FLE"
        assert config.refresh.auto_enabled == True
        assert config.display.theme == "dark"


class TestConfigManager:
    """Test configuration management with real file operations."""

    def test_load_existing_config(self, temp_config_file):
        """Test loading existing configuration file."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()

        assert isinstance(config, ConfigData)
        assert config.stations.from_code == "FLE"
        assert config.stations.to_code == "WAT"
        assert config.display.time_window_hours == 10
        assert config.display.max_trains == 50
        assert config.api.app_id == "test_id"  # From test fixture

    def test_create_default_config(self):
        """Test creating default configuration when file doesn't exist."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name

        # File should not exist now
        assert not os.path.exists(temp_path)

        manager = ConfigManager(temp_path)
        config = manager.load_config()

        # File should be created with defaults
        assert os.path.exists(temp_path)
        assert config.api.app_id == "YOUR_APP_ID_HERE"
        assert config.api.app_key == "YOUR_APP_KEY_HERE"
        assert config.display.theme == "dark"
        assert config.stations.from_code == "FLE"
        assert config.refresh.auto_enabled == True

        # Cleanup
        os.unlink(temp_path)

    def test_save_and_reload_config(self, temp_config_file):
        """Test saving configuration and reloading it."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()

        # Modify configuration
        config.display.theme = "light"
        config.display.max_trains = 30
        config.refresh.interval_minutes = 5
        config.api.timeout_seconds = 20

        # Save changes
        manager.save_config(config)

        # Create new manager and reload
        new_manager = ConfigManager(temp_config_file)
        reloaded_config = new_manager.load_config()

        # Verify changes persisted
        assert reloaded_config.display.theme == "light"
        assert reloaded_config.display.max_trains == 30
        assert reloaded_config.refresh.interval_minutes == 5
        assert reloaded_config.api.timeout_seconds == 20

    def test_invalid_config_file(self):
        """Test handling of invalid configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            temp_path = f.name

        manager = ConfigManager(temp_path)

        with pytest.raises(ConfigurationError) as exc_info:
            manager.load_config()

        assert "Invalid JSON in config file" in str(exc_info.value)

        # Cleanup
        os.unlink(temp_path)

    def test_save_config_creates_directory(self):
        """Test that save_config creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create path with non-existent subdirectory
            config_path = os.path.join(temp_dir, "subdir", "config.json")

            manager = ConfigManager(config_path)
            config = ConfigData(
                api=APIConfig(app_id="test", app_key="test"),
                stations=StationConfig(),
                refresh=RefreshConfig(),
                display=DisplayConfig(),
            )

            # Should create directory and save file
            manager.save_config(config)

            assert os.path.exists(config_path)
            assert os.path.isfile(config_path)

    def test_update_theme(self, temp_config_file):
        """Test updating theme setting."""
        manager = ConfigManager(temp_config_file)

        # Load initial config
        config = manager.load_config()
        initial_theme = config.display.theme

        # Update theme
        new_theme = "light" if initial_theme == "dark" else "dark"
        manager.update_theme(new_theme)

        # Reload and verify
        updated_config = manager.load_config()
        assert updated_config.display.theme == new_theme

    def test_update_theme_invalid(self, temp_config_file):
        """Test updating theme with invalid value."""
        manager = ConfigManager(temp_config_file)

        # Load initial config
        initial_config = manager.load_config()
        initial_theme = initial_config.display.theme

        # Try to update with invalid theme
        manager.update_theme("invalid_theme")

        # Theme should remain unchanged
        updated_config = manager.load_config()
        assert updated_config.display.theme == initial_theme

    def test_update_refresh_interval(self, temp_config_file):
        """Test updating refresh interval."""
        manager = ConfigManager(temp_config_file)

        # Update interval
        manager.update_refresh_interval(10)

        # Reload and verify
        config = manager.load_config()
        assert config.refresh.interval_minutes == 10

    def test_update_refresh_interval_invalid(self, temp_config_file):
        """Test updating refresh interval with invalid value."""
        manager = ConfigManager(temp_config_file)

        # Load initial config
        initial_config = manager.load_config()
        initial_interval = initial_config.refresh.interval_minutes

        # Try to update with invalid interval
        manager.update_refresh_interval(0)  # Invalid: must be > 0
        manager.update_refresh_interval(-5)  # Invalid: must be > 0

        # Interval should remain unchanged
        updated_config = manager.load_config()
        assert updated_config.refresh.interval_minutes == initial_interval

    def test_update_time_window(self, temp_config_file):
        """Test updating time window setting."""
        manager = ConfigManager(temp_config_file)

        # Update time window
        manager.update_time_window(12)

        # Reload and verify
        config = manager.load_config()
        assert config.display.time_window_hours == 12

    def test_update_time_window_invalid(self, temp_config_file):
        """Test updating time window with invalid values."""
        manager = ConfigManager(temp_config_file)

        # Load initial config
        initial_config = manager.load_config()
        initial_window = initial_config.display.time_window_hours

        # Try to update with invalid values
        manager.update_time_window(0)  # Too small
        manager.update_time_window(25)  # Too large
        manager.update_time_window(-1)  # Negative

        # Window should remain unchanged
        updated_config = manager.load_config()
        assert updated_config.display.time_window_hours == initial_window

    def test_validate_api_credentials_valid(self, temp_config_file):
        """Test API credentials validation with valid credentials."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()

        # Update with valid credentials
        config.api.app_id = "real_app_id"
        config.api.app_key = "real_app_key"
        manager.save_config(config)

        # Should validate as true
        assert manager.validate_api_credentials() == True

    def test_validate_api_credentials_invalid(self):
        """Test API credentials validation with default/invalid credentials."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Create config with default credentials
            default_config = {
                "api": {
                    "app_id": "YOUR_APP_ID_HERE",
                    "app_key": "YOUR_APP_KEY_HERE",
                    "base_url": "https://transportapi.com/v3/uk",
                    "timeout_seconds": 10,
                    "max_retries": 3,
                    "rate_limit_per_minute": 30,
                },
                "stations": {
                    "from_code": "FLE",
                    "from_name": "Fleet",
                    "to_code": "WAT",
                    "to_name": "London Waterloo",
                },
                "refresh": {
                    "auto_enabled": True,
                    "interval_minutes": 2,
                    "manual_enabled": True,
                },
                "display": {
                    "max_trains": 50,
                    "time_window_hours": 10,
                    "show_cancelled": True,
                    "theme": "dark",
                },
            }
            json.dump(default_config, f)
            temp_path = f.name

        manager = ConfigManager(temp_path)

        # Should validate as false with default credentials
        assert manager.validate_api_credentials() == False

        # Test with empty credentials
        config = manager.load_config()
        config.api.app_id = ""
        config.api.app_key = ""
        manager.save_config(config)

        assert manager.validate_api_credentials() == False

        # Cleanup
        os.unlink(temp_path)

    def test_get_config_summary(self, temp_config_file):
        """Test getting configuration summary."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()

        # Update some values for testing
        config.display.theme = "light"
        config.refresh.interval_minutes = 3
        config.display.time_window_hours = 8
        config.display.max_trains = 25
        config.refresh.auto_enabled = False
        manager.save_config(config)

        summary = manager.get_config_summary()

        # Verify summary contains expected keys
        expected_keys = {
            "app_version",
            "theme",
            "refresh_interval",
            "time_window",
            "max_trains",
            "auto_refresh",
            "api_configured",
            "route",
            "weather_enabled",
            "weather_location",
            "weather_refresh",
            "weather_provider",
        }
        assert set(summary.keys()) == expected_keys

        # Verify specific values
        assert summary["theme"] == "light"
        assert summary["refresh_interval"] == "3 minutes"
        assert summary["time_window"] == "8 hours"
        assert summary["max_trains"] == 25
        assert summary["auto_refresh"] == "Disabled"
        assert summary["api_configured"] == "Yes"  # Using test credentials from fixture
        assert summary["route"] == "Fleet → London Waterloo"

    def test_config_manager_without_initial_load(self):
        """Test ConfigManager methods when config hasn't been loaded yet."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name

        manager = ConfigManager(temp_path)

        # Methods should work without explicit load_config() call
        manager.update_theme("light")
        manager.update_refresh_interval(5)
        manager.update_time_window(12)

        # Verify changes were applied
        config = manager.load_config()
        assert config.display.theme == "light"
        assert config.refresh.interval_minutes == 5
        assert config.display.time_window_hours == 12

        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_config_file_permissions_error(self):
        """Test handling of file permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")

            # Create config file first
            manager = ConfigManager(config_path)
            config = ConfigData(
                api=APIConfig(app_id="test", app_key="test"),
                stations=StationConfig(),
                refresh=RefreshConfig(),
                display=DisplayConfig(),
            )
            manager.save_config(config)

            # Test with invalid path that should cause permission error
            invalid_path = os.path.join(
                temp_dir, "nonexistent", "deeply", "nested", "config.json"
            )
            invalid_manager = ConfigManager(invalid_path)

            # Try to save to invalid path - should handle gracefully
            try:
                invalid_manager.save_config(config)
                # If it doesn't raise an error, that's fine - the directory creation worked
                assert os.path.exists(invalid_path)
            except ConfigurationError as e:
                # This is the expected behavior for permission errors
                assert "Failed to save config" in str(e)

    def test_config_file_readonly_scenario(self):
        """Test handling of read-only file scenarios."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Create a valid config file
            config_data = {
                "api": {
                    "app_id": "test",
                    "app_key": "test",
                    "base_url": "https://transportapi.com/v3/uk",
                    "timeout_seconds": 10,
                    "max_retries": 3,
                    "rate_limit_per_minute": 30,
                },
                "stations": {
                    "from_code": "FLE",
                    "from_name": "Fleet",
                    "to_code": "WAT",
                    "to_name": "London Waterloo",
                },
                "refresh": {
                    "auto_enabled": True,
                    "interval_minutes": 2,
                    "manual_enabled": True,
                },
                "display": {
                    "max_trains": 50,
                    "time_window_hours": 10,
                    "show_cancelled": True,
                    "theme": "dark",
                },
            }
            json.dump(config_data, f)
            temp_path = f.name

        try:
            # Make file read-only on Windows and Unix
            if os.name == "nt":  # Windows
                import stat

                os.chmod(temp_path, stat.S_IREAD)
            else:  # Unix-like
                os.chmod(temp_path, 0o444)

            manager = ConfigManager(temp_path)

            # Should be able to read the file
            config = manager.load_config()
            assert config.api.app_id == "test"

            # Trying to save should raise an error
            with pytest.raises(ConfigurationError) as exc_info:
                manager.save_config(config)

            assert "Failed to save config" in str(exc_info.value)

        finally:
            # Restore write permissions for cleanup
            if os.name == "nt":  # Windows
                import stat

                os.chmod(temp_path, stat.S_IWRITE | stat.S_IREAD)
            else:  # Unix-like
                os.chmod(temp_path, 0o644)

            # Cleanup
            os.unlink(temp_path)


class TestConfigManagerMissingCoverage:
    """Test cases to cover missing lines for 100% coverage."""

    def test_init_with_none_config_path(self):
        """Test ConfigManager initialization with None config_path (line 85)."""
        # This will trigger line 85: self.config_path = self.get_default_config_path()
        manager = ConfigManager(config_path=None)
        assert manager.config_path is not None
        assert isinstance(manager.config_path, Path)

    def test_get_default_config_path_windows(self, monkeypatch):
        """Test get_default_config_path on Windows (lines 108-126)."""
        # Mock Windows environment
        monkeypatch.setattr("os.name", "nt")
        monkeypatch.setenv("APPDATA", "C:/Users/Test/AppData/Roaming")

        path = ConfigManager.get_default_config_path()

        assert "Trainer" in str(path)
        assert "config.json" in str(path)
        assert "AppData" in str(path)

    def test_get_default_config_path_windows_no_appdata(self, monkeypatch):
        """Test get_default_config_path on Windows without APPDATA (lines 108-126)."""
        # Mock Windows environment without APPDATA
        monkeypatch.setattr("os.name", "nt")
        monkeypatch.delenv("APPDATA", raising=False)

        # Mock getattr to return True for sys.frozen check
        import sys

        original_getattr = getattr

        def mock_getattr(obj, name, default=None):
            if obj is sys and name == "frozen":
                return True
            return original_getattr(obj, name, default)

        monkeypatch.setattr("builtins.getattr", mock_getattr)

        path = ConfigManager.get_default_config_path()

        assert "config.json" in str(path)
        assert ".trainer" in str(path)

    @pytest.mark.skipif(os.name == "nt", reason="Cannot test PosixPath behavior on Windows")
    def test_get_default_config_path_non_windows_executable(self, monkeypatch):
        """Test get_default_config_path on non-Windows as executable (lines 118-123)."""
        # This test only runs on Unix-like systems
        # Mock getattr to return True for sys.frozen check
        import sys

        original_getattr = getattr

        def mock_getattr(obj, name, default=None):
            if obj is sys and name == "frozen":
                return True
            return original_getattr(obj, name, default)

        monkeypatch.setattr("builtins.getattr", mock_getattr)

        path = ConfigManager.get_default_config_path()

        assert ".trainer" in str(path)
        assert "config.json" in str(path)

    def test_get_default_config_path_windows_executable_mode(self, monkeypatch):
        """Test get_default_config_path on Windows in executable mode (alternative test)."""
        # Mock Windows environment
        monkeypatch.setattr("os.name", "nt")
        monkeypatch.setenv("APPDATA", "C:/Users/Test/AppData/Roaming")

        # Mock getattr to return True for sys.frozen check (executable mode)
        import sys

        original_getattr = getattr

        def mock_getattr(obj, name, default=None):
            if obj is sys and name == "frozen":
                return True
            return original_getattr(obj, name, default)

        monkeypatch.setattr("builtins.getattr", mock_getattr)

        path = ConfigManager.get_default_config_path()

        assert "Trainer" in str(path)
        assert "config.json" in str(path)
        assert "AppData" in str(path)

    def test_get_default_config_path_non_windows_development(self, monkeypatch):
        """Test get_default_config_path on non-Windows in development (lines 125-126)."""
        # Mock non-Windows environment
        monkeypatch.setattr("os.name", "posix")

        # Mock getattr to return False for sys.frozen check (development mode)
        import sys

        original_getattr = getattr

        def mock_getattr(obj, name, default=None):
            if obj is sys and name == "frozen":
                return False
            return original_getattr(obj, name, default)

        monkeypatch.setattr("builtins.getattr", mock_getattr)

        path = ConfigManager.get_default_config_path()

        assert path == Path("config.json")

    def test_install_default_config_to_appdata_non_windows(self, monkeypatch):
        """Test install_default_config_to_appdata on non-Windows (line 137)."""
        # Mock non-Windows environment
        monkeypatch.setattr("os.name", "posix")

        manager = ConfigManager()
        result = manager.install_default_config_to_appdata()

        # Should return False on non-Windows
        assert result == False

    def test_install_default_config_to_appdata_no_appdata(self, monkeypatch):
        """Test install_default_config_to_appdata without APPDATA (line 141)."""
        # Mock Windows environment without APPDATA
        monkeypatch.setattr("os.name", "nt")
        monkeypatch.delenv("APPDATA", raising=False)

        manager = ConfigManager()
        result = manager.install_default_config_to_appdata()

        # Should return False without APPDATA
        assert result == False

    def test_install_default_config_to_appdata_success(self, monkeypatch):
        """Test install_default_config_to_appdata successful creation (lines 152-162)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock Windows environment with temp APPDATA
            monkeypatch.setattr("os.name", "nt")
            monkeypatch.setenv("APPDATA", temp_dir)

            manager = ConfigManager()
            result = manager.install_default_config_to_appdata()

            # Should return True on success
            assert result == True

            # Check that config file was created
            config_path = Path(temp_dir) / "Trainer" / "config.json"
            assert config_path.exists()

            # Verify config content
            with open(config_path, "r") as f:
                config_data = json.load(f)
            assert config_data["api"]["app_id"] == "YOUR_APP_ID_HERE"
            assert config_data["api"]["app_key"] == "YOUR_APP_KEY_HERE"

    def test_install_default_config_to_appdata_already_exists(self, monkeypatch):
        """Test install_default_config_to_appdata when config already exists (line 164)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock Windows environment with temp APPDATA
            monkeypatch.setattr("os.name", "nt")
            monkeypatch.setenv("APPDATA", temp_dir)

            # Create the config directory and file first
            config_dir = Path(temp_dir) / "Trainer"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "config.json"
            config_path.write_text('{"existing": "config"}')

            manager = ConfigManager()
            result = manager.install_default_config_to_appdata()

            # Should return True (already exists)
            assert result == True

            # Original content should be preserved
            with open(config_path, "r") as f:
                config_data = json.load(f)
            assert config_data == {"existing": "config"}

    def test_install_default_config_to_appdata_exception(self, monkeypatch):
        """Test install_default_config_to_appdata with exception (lines 166-168)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock Windows environment
            monkeypatch.setattr("os.name", "nt")
            monkeypatch.setenv("APPDATA", temp_dir)

            manager = ConfigManager()

            # Mock json.dump to raise an exception during file writing
            original_dump = json.dump

            def mock_dump(*args, **kwargs):
                raise IOError("Cannot write file")

            monkeypatch.setattr("json.dump", mock_dump)

            result = manager.install_default_config_to_appdata()

            # Should return False on exception
            assert result == False

    def test_load_config_json_decode_error(self):
        """Test load_config with JSON decode error (line 198)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Write invalid JSON that will cause JSONDecodeError
            f.write('{"invalid": json content}')  # Missing quotes around 'json'
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert "Invalid JSON in config file" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_load_config_general_exception(self, monkeypatch):
        """Test load_config with general exception (line 199)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Write valid JSON
            json.dump({"api": {"app_id": "test", "app_key": "test"}}, f)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            # Mock ConfigData to raise an exception during initialization
            def mock_config_data(*args, **kwargs):
                raise ValueError("Test exception")

            monkeypatch.setattr(
                "src.managers.config_manager.ConfigData", mock_config_data
            )

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert "Failed to load config" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_validate_api_credentials_no_config_loaded(self):
        """Test validate_api_credentials when config is None (line 291)."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name

        # File doesn't exist, so config will be None initially
        manager = ConfigManager(temp_path)
        # Don't call load_config(), so self.config remains None

        # This should trigger line 291: if not self.config: return False
        # But first it will call load_config() which creates default config
        result = manager.validate_api_credentials()

        # With default config, credentials are invalid
        assert result == False

    def test_validate_api_credentials_config_none_after_load(self, monkeypatch):
        """Test validate_api_credentials when config is None after load (line 291)."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name

        manager = ConfigManager(temp_path)

        # Mock load_config to set self.config to None
        def mock_load_config():
            manager.config = None
            return None

        monkeypatch.setattr(manager, "load_config", mock_load_config)

        result = manager.validate_api_credentials()

        # Should return False when config is None (line 291)
        assert result == False

    def test_get_config_summary_no_config_loaded(self):
        """Test get_config_summary when config is None (line 308)."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name

        # File doesn't exist, so config will be None initially
        manager = ConfigManager(temp_path)
        # Don't call load_config(), so self.config remains None

        # This should trigger line 308: if self.config is None: self.load_config()
        summary = manager.get_config_summary()

        # Should have loaded config and returned summary
        assert isinstance(summary, dict)
        assert "theme" in summary

    def test_get_config_summary_config_none_after_load(self, monkeypatch):
        """Test get_config_summary when config is None after load attempt (line 311)."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name

        manager = ConfigManager(temp_path)

        # Mock load_config to not set self.config
        def mock_load_config():
            # Don't set self.config, leave it as None
            pass

        monkeypatch.setattr(manager, "load_config", mock_load_config)

        summary = manager.get_config_summary()

        # Should return error dict when config is None
        assert summary == {"error": "Configuration not loaded"}


class TestConfigManagerWeatherIntegration:
    """Test weather-related configuration management methods."""

    def test_update_weather_config_success(self, temp_config_file):
        """Test successful weather configuration update."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Ensure weather config exists
        assert config.weather is not None
        original_enabled = config.weather.enabled
        
        # Update weather config
        manager.update_weather_config(enabled=not original_enabled, refresh_interval_minutes=15)
        
        # Verify changes
        updated_config = manager.load_config()
        assert updated_config.weather is not None
        assert updated_config.weather.enabled == (not original_enabled)
        assert updated_config.weather.refresh_interval_minutes == 15

    def test_update_weather_config_no_config_loaded(self):
        """Test update_weather_config when config is None."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name
        
        manager = ConfigManager(temp_path)
        # Don't load config, so self.config is None
        
        # Should load config and then update
        manager.update_weather_config(enabled=False)
        
        # Verify config was loaded and updated
        config = manager.load_config()
        assert config.weather is not None
        assert config.weather.enabled == False

    def test_update_weather_config_invalid_data(self, temp_config_file):
        """Test update_weather_config with invalid data."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Try to update with invalid weather config data
        with pytest.raises(ConfigurationError) as exc_info:
            manager.update_weather_config(refresh_interval_minutes=-1)  # Invalid negative value
        
        assert "Invalid weather configuration" in str(exc_info.value)

    def test_update_weather_config_no_weather_config(self, monkeypatch):
        """Test update_weather_config when weather config is None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Create config without weather section
            config_data = {
                "api": {"app_id": "test", "app_key": "test"},
                "stations": {"from_code": "FLE", "from_name": "Fleet", "to_code": "WAT", "to_name": "London Waterloo"},
                "refresh": {"auto_enabled": True, "interval_minutes": 2, "manual_enabled": True},
                "display": {"max_trains": 50, "time_window_hours": 10, "show_cancelled": True, "theme": "dark"},
                "weather": None,
                "astronomy": None
            }
            json.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            config = manager.load_config()
            
            # Weather config should be created by ConfigData.__init__
            assert config.weather is not None
            
            # Should be able to update weather config
            manager.update_weather_config(enabled=False)
            
            updated_config = manager.load_config()
            assert updated_config.weather is not None
            assert updated_config.weather.enabled == False
        finally:
            os.unlink(temp_path)

    def test_get_weather_config_success(self, temp_config_file):
        """Test successful weather configuration retrieval."""
        manager = ConfigManager(temp_config_file)
        
        weather_config = manager.get_weather_config()
        
        assert weather_config is not None
        assert hasattr(weather_config, 'enabled')
        assert hasattr(weather_config, 'refresh_interval_minutes')

    def test_get_weather_config_no_config_loaded(self):
        """Test get_weather_config when config is None."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name
        
        manager = ConfigManager(temp_path)
        # Don't load config, so self.config is None
        
        # Should load config and return weather config
        weather_config = manager.get_weather_config()
        
        assert weather_config is not None

    def test_get_weather_config_config_none_after_load(self, monkeypatch):
        """Test get_weather_config when config is None after load attempt."""
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = temp_file.name

        manager = ConfigManager(temp_path)

        # Mock load_config to not set self.config
        def mock_load_config():
            # Don't set self.config, leave it as None
            pass

        monkeypatch.setattr(manager, "load_config", mock_load_config)

        weather_config = manager.get_weather_config()

        # Should return None when config is None
        assert weather_config is None

    def test_is_weather_enabled_true(self, temp_config_file):
        """Test is_weather_enabled when weather is enabled."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Ensure weather is enabled
        assert config.weather is not None
        config.weather.enabled = True
        manager.save_config(config)
        
        assert manager.is_weather_enabled() == True

    def test_is_weather_enabled_false(self, temp_config_file):
        """Test is_weather_enabled when weather is disabled."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Disable weather
        assert config.weather is not None
        config.weather.enabled = False
        manager.save_config(config)
        
        assert manager.is_weather_enabled() == False

    def test_is_weather_enabled_no_weather_config(self, monkeypatch):
        """Test is_weather_enabled when weather config is None."""
        manager = ConfigManager()
        
        # Mock get_weather_config to return None
        def mock_get_weather_config():
            return None
        
        monkeypatch.setattr(manager, "get_weather_config", mock_get_weather_config)
        
        assert manager.is_weather_enabled() == False

    def test_get_config_summary_no_weather_config(self, monkeypatch):
        """Test get_config_summary when weather config is None (line 374)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Create config with basic structure
            config_data = {
                "api": {"app_id": "test", "app_key": "test"},
                "stations": {"from_code": "FLE", "from_name": "Fleet", "to_code": "WAT", "to_name": "London Waterloo"},
                "refresh": {"auto_enabled": True, "interval_minutes": 2, "manual_enabled": True},
                "display": {"max_trains": 50, "time_window_hours": 10, "show_cancelled": True, "theme": "dark"},
                "weather": None,
                "astronomy": None
            }
            json.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            
            # Mock the config to have None weather after loading
            def mock_load_config():
                from src.managers.config_manager import ConfigData, APIConfig, StationConfig, RefreshConfig, DisplayConfig
                manager.config = ConfigData(
                    api=APIConfig(app_id="test", app_key="test"),
                    stations=StationConfig(),
                    refresh=RefreshConfig(),
                    display=DisplayConfig()
                )
                # Force weather to None after initialization
                manager.config.weather = None
                return manager.config
            
            monkeypatch.setattr(manager, "load_config", mock_load_config)
            
            summary = manager.get_config_summary()
            
            # Should have weather_enabled = False (line 374)
            assert summary["weather_enabled"] == False
            assert "weather_location" not in summary
            assert "weather_refresh" not in summary
            assert "weather_provider" not in summary
        finally:
            os.unlink(temp_path)


class TestConfigManagerMigration:
    """Test configuration migration functionality."""

    def test_migrate_config_if_needed_no_config(self):
        """Test migrate_config_if_needed when config is None."""
        manager = ConfigManager()
        # Don't load config, so self.config is None
        
        result = manager.migrate_config_if_needed()
        
        # Should return False when config is None
        assert result == False

    def test_migrate_config_if_needed_weather_migration_needed(self, temp_config_file, monkeypatch):
        """Test migrate_config_if_needed when weather migration is needed."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Mock WeatherConfigMigrator to indicate migration is needed
        def mock_is_migration_needed(weather_dict):
            return True
        
        def mock_migrate_to_current_version(weather_dict):
            # Return migrated weather config
            migrated = weather_dict.copy()
            migrated['version'] = '2.0'  # Simulate version update
            return migrated
        
        monkeypatch.setattr("src.managers.config_manager.WeatherConfigMigrator.is_migration_needed", mock_is_migration_needed)
        monkeypatch.setattr("src.managers.config_manager.WeatherConfigMigrator.migrate_to_current_version", mock_migrate_to_current_version)
        
        result = manager.migrate_config_if_needed()
        
        # Should return True indicating migration was performed
        assert result == True

    def test_migrate_config_if_needed_no_weather_config(self, monkeypatch):
        """Test migrate_config_if_needed when weather config is missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Create config without weather section
            config_data = {
                "api": {"app_id": "test", "app_key": "test"},
                "stations": {"from_code": "FLE", "from_name": "Fleet", "to_code": "WAT", "to_name": "London Waterloo"},
                "refresh": {"auto_enabled": True, "interval_minutes": 2, "manual_enabled": True},
                "display": {"max_trains": 50, "time_window_hours": 10, "show_cancelled": True, "theme": "dark"}
                # No weather or astronomy sections
            }
            json.dump(config_data, f)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            
            # Mock the config to simulate missing weather config
            def mock_load_config():
                from src.managers.config_manager import ConfigData, APIConfig, StationConfig, RefreshConfig, DisplayConfig
                manager.config = ConfigData(
                    api=APIConfig(app_id="test", app_key="test"),
                    stations=StationConfig(),
                    refresh=RefreshConfig(),
                    display=DisplayConfig()
                )
                return manager.config
            
            # Load config first
            config = manager.load_config()
            
            # Manually set weather to None to simulate missing config
            config.weather = None
            manager.config = config
            
            result = manager.migrate_config_if_needed()
            
            # Should return True indicating weather config was added
            assert result == True
            
            # Verify weather config was added
            assert manager.config.weather is not None
        finally:
            os.unlink(temp_path)

    def test_migrate_config_if_needed_weather_config_none(self, temp_config_file, monkeypatch):
        """Test migrate_config_if_needed when weather config is explicitly None."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Force weather config to None
        config.weather = None
        manager.config = config
        
        result = manager.migrate_config_if_needed()
        
        # Should return True indicating weather config was added
        assert result == True
        
        # Verify weather config was added
        assert manager.config.weather is not None

    def test_migrate_config_if_needed_no_migration_needed(self, temp_config_file, monkeypatch):
        """Test migrate_config_if_needed when no migration is needed."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Mock WeatherConfigMigrator to indicate no migration is needed
        def mock_is_migration_needed(weather_dict):
            return False
        
        monkeypatch.setattr("src.managers.config_manager.WeatherConfigMigrator.is_migration_needed", mock_is_migration_needed)
        
        result = manager.migrate_config_if_needed()
        
        # Should return False indicating no migration was performed
        assert result == False

    def test_migrate_config_if_needed_exception_handling(self, temp_config_file, monkeypatch):
        """Test migrate_config_if_needed exception handling."""
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Mock WeatherConfigMigrator to raise an exception
        def mock_is_migration_needed(weather_dict):
            raise ValueError("Migration error")
        
        monkeypatch.setattr("src.managers.config_manager.WeatherConfigMigrator.is_migration_needed", mock_is_migration_needed)
        
        result = manager.migrate_config_if_needed()
        
        # Should return False when exception occurs
        assert result == False


@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        # Create a complete test configuration
        config_data = {
            "api": {
                "app_id": "test_id",
                "app_key": "test_key",
                "base_url": "https://transportapi.com/v3/uk",
                "timeout_seconds": 10,
                "max_retries": 3,
                "rate_limit_per_minute": 30,
            },
            "stations": {
                "from_code": "FLE",
                "from_name": "Fleet",
                "to_code": "WAT",
                "to_name": "London Waterloo",
            },
            "refresh": {
                "auto_enabled": True,
                "interval_minutes": 2,
                "manual_enabled": True,
            },
            "display": {
                "max_trains": 50,
                "time_window_hours": 10,
                "show_cancelled": True,
                "theme": "dark",
            },
            "weather": {
                "enabled": True,
                "api_provider": "openweathermap",
                "api_key": "test_weather_key",
                "location": {
                    "name": "London Waterloo",
                    "latitude": 51.5045,
                    "longitude": -0.1097,
                    "country_code": "GB"
                },
                "refresh_interval_minutes": 15,
                "units": "metric",
                "language": "en"
            },
            "astronomy": {
                "enabled": True,
                "location": {
                    "name": "London Waterloo",
                    "latitude": 51.5045,
                    "longitude": -0.1097,
                    "timezone": "Europe/London"
                },
                "refresh_interval_minutes": 60
            }
        }
        json.dump(config_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)
