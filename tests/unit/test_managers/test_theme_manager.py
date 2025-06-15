"""
Tests for ThemeManager class.

This module contains comprehensive tests for the ThemeManager class,
focusing on achieving 100% code coverage while exercising actual code
rather than using mocks where feasible.
"""

import pytest
from unittest.mock import Mock
from PySide6.QtCore import QObject

from src.managers.theme_manager import ThemeManager


class TestThemeManager:
    """Test cases for ThemeManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.theme_manager = ThemeManager()

    def test_initialization(self):
        """Test ThemeManager initialization."""
        assert self.theme_manager.current_theme == "dark"
        assert isinstance(self.theme_manager, QObject)
        assert hasattr(self.theme_manager, 'theme_changed')
        
        # Test that theme colors are properly initialized
        colors = self.theme_manager._theme_colors
        assert "dark" in colors
        assert "light" in colors
        assert "background_primary" in colors["dark"]
        assert "background_primary" in colors["light"]

    def test_switch_theme(self):
        """Test theme switching functionality."""
        # Mock the signal to verify it's emitted
        signal_mock = Mock()
        self.theme_manager.theme_changed.connect(signal_mock)
        
        # Start with dark theme, switch to light
        assert self.theme_manager.current_theme == "dark"
        self.theme_manager.switch_theme()
        assert self.theme_manager.current_theme == "light"
        signal_mock.assert_called_with("light")
        
        # Switch back to dark
        self.theme_manager.switch_theme()
        assert self.theme_manager.current_theme == "dark"
        signal_mock.assert_called_with("dark")

    def test_set_theme_valid_different_theme(self):
        """Test set_theme with valid theme that's different from current."""
        # This tests lines 96-97 which were uncovered
        signal_mock = Mock()
        self.theme_manager.theme_changed.connect(signal_mock)
        
        # Start with dark, set to light
        assert self.theme_manager.current_theme == "dark"
        self.theme_manager.set_theme("light")
        assert self.theme_manager.current_theme == "light"
        signal_mock.assert_called_with("light")
        
        # Set back to dark
        self.theme_manager.set_theme("dark")
        assert self.theme_manager.current_theme == "dark"
        signal_mock.assert_called_with("dark")

    def test_set_theme_same_theme(self):
        """Test set_theme with same theme as current (should not change)."""
        signal_mock = Mock()
        self.theme_manager.theme_changed.connect(signal_mock)
        
        # Try to set to same theme
        self.theme_manager.set_theme("dark")
        assert self.theme_manager.current_theme == "dark"
        signal_mock.assert_not_called()

    def test_set_theme_invalid_theme(self):
        """Test set_theme with invalid theme name."""
        signal_mock = Mock()
        self.theme_manager.theme_changed.connect(signal_mock)
        
        original_theme = self.theme_manager.current_theme
        self.theme_manager.set_theme("invalid_theme")
        assert self.theme_manager.current_theme == original_theme
        signal_mock.assert_not_called()

    def test_get_theme_icon(self):
        """Test theme icon retrieval."""
        # Dark theme should show sun icon (to switch to light)
        self.theme_manager.current_theme = "dark"
        assert self.theme_manager.get_theme_icon() == "☀️"
        
        # Light theme should show moon icon (to switch to dark)
        self.theme_manager.current_theme = "light"
        assert self.theme_manager.get_theme_icon() == "🌙"

    def test_get_theme_tooltip(self):
        """Test theme tooltip text."""
        # Dark theme should suggest switching to light
        self.theme_manager.current_theme = "dark"
        assert self.theme_manager.get_theme_tooltip() == "Switch to Light Theme"
        
        # Light theme should suggest switching to dark
        self.theme_manager.current_theme = "light"
        assert self.theme_manager.get_theme_tooltip() == "Switch to Dark Theme"

    def test_get_color_existing_key(self):
        """Test getting color for existing key."""
        # Test with dark theme
        self.theme_manager.current_theme = "dark"
        color = self.theme_manager.get_color("background_primary")
        assert color == "#1a1a1a"
        
        # Test with light theme
        self.theme_manager.current_theme = "light"
        color = self.theme_manager.get_color("background_primary")
        assert color == "#ffffff"

    def test_get_color_nonexistent_key(self):
        """Test getting color for non-existent key."""
        color = self.theme_manager.get_color("nonexistent_key")
        assert color == "#000000"  # Default fallback color

    def test_get_colors_for_theme_valid_theme(self):
        """Test getting colors for valid theme."""
        dark_colors = self.theme_manager.get_colors_for_theme("dark")
        assert dark_colors["background_primary"] == "#1a1a1a"
        
        light_colors = self.theme_manager.get_colors_for_theme("light")
        assert light_colors["background_primary"] == "#ffffff"

    def test_get_colors_for_theme_invalid_theme(self):
        """Test getting colors for invalid theme - tests line 143."""
        # This should return dark theme colors as fallback
        colors = self.theme_manager.get_colors_for_theme("invalid_theme")
        assert colors == self.theme_manager._theme_colors["dark"]
        assert colors["background_primary"] == "#1a1a1a"

    def test_get_current_colors(self):
        """Test getting current theme colors."""
        # Test dark theme
        self.theme_manager.current_theme = "dark"
        colors = self.theme_manager.get_current_colors()
        assert colors["background_primary"] == "#1a1a1a"
        
        # Test light theme
        self.theme_manager.current_theme = "light"
        colors = self.theme_manager.get_current_colors()
        assert colors["background_primary"] == "#ffffff"

    def test_is_dark_theme(self):
        """Test dark theme detection - tests line 161."""
        self.theme_manager.current_theme = "dark"
        assert self.theme_manager.is_dark_theme() is True
        
        self.theme_manager.current_theme = "light"
        assert self.theme_manager.is_dark_theme() is False

    def test_is_light_theme(self):
        """Test light theme detection - tests line 170."""
        self.theme_manager.current_theme = "light"
        assert self.theme_manager.is_light_theme() is True
        
        self.theme_manager.current_theme = "dark"
        assert self.theme_manager.is_light_theme() is False

    def test_get_status_color_mapped_statuses(self):
        """Test get_status_color with mapped status values - tests lines 182-190."""
        # Test all mapped statuses
        self.theme_manager.current_theme = "dark"
        
        # Test on_time -> success
        color = self.theme_manager.get_status_color("on_time")
        expected_color = self.theme_manager.get_color("success")
        assert color == expected_color
        assert color == "#4caf50"
        
        # Test delayed -> warning
        color = self.theme_manager.get_status_color("delayed")
        expected_color = self.theme_manager.get_color("warning")
        assert color == expected_color
        assert color == "#ff9800"
        
        # Test cancelled -> error
        color = self.theme_manager.get_status_color("cancelled")
        expected_color = self.theme_manager.get_color("error")
        assert color == expected_color
        assert color == "#f44336"
        
        # Test unknown -> text_disabled
        color = self.theme_manager.get_status_color("unknown")
        expected_color = self.theme_manager.get_color("text_disabled")
        assert color == expected_color
        assert color == "#666666"

    def test_get_status_color_direct_status(self):
        """Test get_status_color with direct status color keys."""
        self.theme_manager.current_theme = "dark"
        
        # Test direct status colors
        color = self.theme_manager.get_status_color("success")
        assert color == "#4caf50"
        
        color = self.theme_manager.get_status_color("warning")
        assert color == "#ff9800"
        
        color = self.theme_manager.get_status_color("error")
        assert color == "#f44336"
        
        color = self.theme_manager.get_status_color("info")
        assert color == "#2196f3"

    def test_get_status_color_unmapped_status(self):
        """Test get_status_color with unmapped status (fallback to get_color)."""
        color = self.theme_manager.get_status_color("nonexistent_status")
        assert color == "#000000"  # Should fallback to default color

    def test_get_main_window_stylesheet(self):
        """Test main window stylesheet generation."""
        # Test dark theme stylesheet
        self.theme_manager.current_theme = "dark"
        stylesheet = self.theme_manager.get_main_window_stylesheet()
        
        assert "QMainWindow" in stylesheet
        assert "#1a1a1a" in stylesheet  # dark background_primary
        assert "#ffffff" in stylesheet  # dark text_primary
        
        # Test light theme stylesheet
        self.theme_manager.current_theme = "light"
        stylesheet = self.theme_manager.get_main_window_stylesheet()
        
        assert "QMainWindow" in stylesheet
        assert "#ffffff" in stylesheet  # light background_primary
        assert "#212121" in stylesheet  # light text_primary

    def test_get_widget_stylesheet(self):
        """Test widget stylesheet generation."""
        # Test dark theme stylesheet
        self.theme_manager.current_theme = "dark"
        stylesheet = self.theme_manager.get_widget_stylesheet()
        
        assert "QWidget" in stylesheet
        assert "QPushButton" in stylesheet
        assert "QScrollArea" in stylesheet
        assert "#2d2d2d" in stylesheet  # dark background_secondary
        
        # Test light theme stylesheet
        self.theme_manager.current_theme = "light"
        stylesheet = self.theme_manager.get_widget_stylesheet()
        
        assert "QWidget" in stylesheet
        assert "#f5f5f5" in stylesheet  # light background_secondary

    def test_theme_colors_completeness(self):
        """Test that both themes have all required color keys."""
        dark_colors = self.theme_manager._theme_colors["dark"]
        light_colors = self.theme_manager._theme_colors["light"]
        
        # Both themes should have the same keys
        assert set(dark_colors.keys()) == set(light_colors.keys())
        
        # Check for essential color categories
        essential_keys = [
            "background_primary", "background_secondary", "background_tertiary",
            "text_primary", "text_secondary", "text_disabled",
            "success", "warning", "error", "info",
            "primary_accent", "secondary_accent", "tertiary_accent",
            "border_primary", "border_secondary", "border_accent"
        ]
        
        for key in essential_keys:
            assert key in dark_colors
            assert key in light_colors
            assert dark_colors[key].startswith("#")
            assert light_colors[key].startswith("#")

    def test_signal_inheritance(self):
        """Test that ThemeManager properly inherits from QObject and has signals."""
        assert isinstance(self.theme_manager, QObject)
        assert hasattr(self.theme_manager, 'theme_changed')
        
        # Test signal connection and emission
        signal_received = []
        
        def signal_handler(theme_name):
            signal_received.append(theme_name)
        
        self.theme_manager.theme_changed.connect(signal_handler)
        self.theme_manager.switch_theme()
        
        assert len(signal_received) == 1
        assert signal_received[0] == "light"

    def test_theme_persistence_across_operations(self):
        """Test that theme state persists across various operations."""
        # Set to light theme
        self.theme_manager.set_theme("light")
        assert self.theme_manager.current_theme == "light"
        
        # Perform various operations and ensure theme stays consistent
        self.theme_manager.get_color("background_primary")
        assert self.theme_manager.current_theme == "light"
        
        self.theme_manager.get_theme_icon()
        assert self.theme_manager.current_theme == "light"
        
        self.theme_manager.is_dark_theme()
        assert self.theme_manager.current_theme == "light"
        
        self.theme_manager.get_status_color("on_time")
        assert self.theme_manager.current_theme == "light"