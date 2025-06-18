"""
Simple unit tests for TrainerSplashScreen class.

This test suite focuses on core functionality with minimal mocking.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    HAS_QT = True
except ImportError:
    HAS_QT = False

if HAS_QT:
    from src.ui.splash_screen import TrainerSplashScreen


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
def temp_assets_dir():
    """Create temporary assets directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        assets_dir = Path(temp_dir) / "assets"
        assets_dir.mkdir()
        yield assets_dir


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
class TestTrainerSplashScreenSimple:
    """Simple test suite for TrainerSplashScreen class."""

    def test_init_basic(self, qapp):
        """Test basic initialization of splash screen."""
        with patch('src.ui.splash_screen.logger') as mock_logger:
            splash = TrainerSplashScreen()
            
            # Check basic properties
            assert splash is not None
            assert splash.size().width() == 400
            assert splash.size().height() == 300
            
            # Check logger was called
            mock_logger.info.assert_called_with("Splash screen initialized")
            
            splash.close()

    def test_create_icon_widget_no_icons(self, qapp):
        """Test icon widget creation when no icons exist."""
        with patch('src.ui.splash_screen.Path') as mock_path:
            # Mock Path to return non-existent files
            mock_path_obj = Mock()
            mock_path_obj.exists.return_value = False
            mock_path.return_value = mock_path_obj
            
            with patch('src.ui.splash_screen.logger') as mock_logger:
                splash = TrainerSplashScreen()
                
                # Should warn about no icon found
                mock_logger.warning.assert_any_call("No train icon found for splash screen")
                
                splash.close()

    def test_create_icon_widget_svg_exists(self, qapp, temp_assets_dir):
        """Test icon widget creation when SVG file exists."""
        # Create dummy SVG file
        svg_file = temp_assets_dir / "train_icon.svg"
        svg_file.write_text("<svg><rect width='100' height='100'/></svg>")
        
        with patch('src.ui.splash_screen.Path') as mock_path:
            def path_side_effect(path_str):
                if path_str == "assets/train_icon.svg":
                    return svg_file
                return Path(path_str)
            
            mock_path.side_effect = path_side_effect
            
            with patch('src.ui.splash_screen.logger') as mock_logger:
                splash = TrainerSplashScreen()
                
                # Check that SVG widget was created and logger called
                mock_logger.info.assert_any_call("Splash screen using SVG icon")
                
                splash.close()

    def test_show_message(self, qapp):
        """Test show_message method."""
        splash = TrainerSplashScreen()
        
        with patch('src.ui.splash_screen.logger') as mock_logger:
            with patch.object(splash, 'repaint') as mock_repaint:
                splash.show_message("Test message")
                
                # Check message was set and repaint called
                assert splash.loading_label.text() == "Test message"
                mock_repaint.assert_called_once()
                mock_logger.debug.assert_called_with("Splash screen message: Test message")
        
        splash.close()

    def test_close_splash(self, qapp):
        """Test close_splash method."""
        splash = TrainerSplashScreen()
        
        with patch('src.ui.splash_screen.logger') as mock_logger:
            with patch.object(splash, 'close') as mock_close:
                splash.close_splash()
                
                # Check logger and close were called
                mock_logger.info.assert_called_with("Closing splash screen")
                mock_close.assert_called_once()
        
        splash.close()

    def test_apply_styling(self, qapp):
        """Test that styling is applied correctly."""
        splash = TrainerSplashScreen()
        
        # Check that main widget has stylesheet applied
        stylesheet = splash.main_widget.styleSheet()
        assert stylesheet != ""
        assert "#1a1a1a" in stylesheet  # Background color
        assert "#ffffff" in stylesheet  # Text color
        assert "#4fc3f7" in stylesheet  # Border color
        assert "border-radius: 8px" in stylesheet
        
        splash.close()

    def test_window_properties(self, qapp):
        """Test window properties are set correctly."""
        splash = TrainerSplashScreen()
        
        # Check window flags
        flags = splash.windowFlags()
        assert Qt.WindowType.SplashScreen in flags
        assert Qt.WindowType.WindowStaysOnTopHint in flags
        assert Qt.WindowType.FramelessWindowHint in flags
        
        splash.close()

    def test_pixmap_initialization(self, qapp):
        """Test that the base pixmap is properly initialized."""
        splash = TrainerSplashScreen()
        
        # Check that splash screen has a pixmap
        pixmap = splash.pixmap()
        assert not pixmap.isNull()
        assert pixmap.width() == 400
        assert pixmap.height() == 300
        
        splash.close()

    def test_ui_components_exist(self, qapp):
        """Test that all UI components are properly set up."""
        splash = TrainerSplashScreen()
        
        # Check main widget exists and has correct size
        assert hasattr(splash, 'main_widget')
        assert splash.main_widget.size().width() == 400
        assert splash.main_widget.size().height() == 300
        
        # Check loading label exists
        assert hasattr(splash, 'loading_label')
        assert splash.loading_label.text() == "Loading..."
        
        splash.close()

    def test_create_icon_widget_method_directly(self, qapp):
        """Test create_icon_widget method directly."""
        splash = TrainerSplashScreen()
        
        # Test when no icons exist
        with patch('src.ui.splash_screen.Path') as mock_path:
            def path_side_effect(path_str):
                mock_path_obj = Mock()
                mock_path_obj.exists.return_value = False
                return mock_path_obj
            
            mock_path.side_effect = path_side_effect
            
            result = splash.create_icon_widget()
            assert result is None
        
        splash.close()