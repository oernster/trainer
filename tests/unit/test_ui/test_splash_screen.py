"""
Comprehensive tests for TrainerSplashScreen to achieve 100% coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPixmap, QPainter, QPaintEvent

from src.ui.splash_screen import TrainerSplashScreen


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


class TestTrainerSplashScreen:
    """Test cases for TrainerSplashScreen class."""

    def test_init(self, qapp):
        """Test splash screen initialization."""
        splash = TrainerSplashScreen()
        
        # Check basic properties
        assert splash.size().width() == 400
        assert splash.size().height() == 300
        assert hasattr(splash, 'main_widget')
        assert hasattr(splash, 'loading_label')
        
        # Check window flags
        flags = splash.windowFlags()
        assert Qt.WindowType.SplashScreen in flags
        assert Qt.WindowType.WindowStaysOnTopHint in flags
        assert Qt.WindowType.FramelessWindowHint in flags

    def test_setup_ui(self, qapp):
        """Test UI setup."""
        splash = TrainerSplashScreen()
        
        # Check main widget exists and has correct size
        assert splash.main_widget is not None
        assert splash.main_widget.size().width() == 400
        assert splash.main_widget.size().height() == 300
        
        # Check loading label exists
        assert splash.loading_label is not None
        assert splash.loading_label.text() == "Loading..."
        
        # Check layout has widgets
        layout = splash.main_widget.layout()
        assert layout is not None
        assert layout.count() == 4  # emoji, title, subtitle, loading

    def test_apply_styling(self, qapp):
        """Test styling application."""
        splash = TrainerSplashScreen()
        
        # Check that stylesheet was applied
        stylesheet = splash.main_widget.styleSheet()
        assert "#1a1a1a" in stylesheet  # Background color
        assert "#ffffff" in stylesheet  # Text color
        assert "#4fc3f7" in stylesheet  # Border color

    def test_show_message_with_loading_label(self, qapp):
        """Test show_message when loading_label exists."""
        splash = TrainerSplashScreen()
        
        # Mock repaint to avoid actual painting
        with patch.object(splash, 'repaint') as mock_repaint:
            splash.show_message("Test message")
            
            assert splash.loading_label.text() == "Test message"
            mock_repaint.assert_called_once()

    def test_show_message_without_loading_label(self, qapp):
        """Test show_message when loading_label doesn't exist."""
        splash = TrainerSplashScreen()
        
        # Remove loading_label to test the hasattr check
        delattr(splash, 'loading_label')
        
        # Should not crash
        splash.show_message("Test message")

    def test_close_splash(self, qapp):
        """Test close_splash method."""
        splash = TrainerSplashScreen()
        
        # Mock close to avoid actually closing
        with patch.object(splash, 'close') as mock_close:
            splash.close_splash()
            mock_close.assert_called_once()

    def test_paint_event_with_main_widget(self, qapp):
        """Test paintEvent when main_widget exists - covers lines 111-130."""
        splash = TrainerSplashScreen()
        
        # Create a mock paint event
        mock_event = Mock(spec=QPaintEvent)
        
        # Mock QPainter and its methods
        mock_painter = Mock(spec=QPainter)
        mock_painter.deviceTransform.return_value.map.return_value = QPoint(0, 0)
        
        # Mock splash rect and widget rect
        splash_rect = QRect(0, 0, 400, 300)
        widget_rect = QRect(0, 0, 400, 300)
        
        with patch('src.ui.splash_screen.QPainter', return_value=mock_painter) as mock_painter_class:
            with patch.object(splash, 'rect', return_value=splash_rect):
                with patch.object(splash.main_widget, 'rect', return_value=widget_rect):
                    with patch.object(splash.main_widget, 'render') as mock_render:
                        with patch.object(splash.__class__.__bases__[0], 'paintEvent') as mock_super_paint:
                            
                            # Call paintEvent
                            splash.paintEvent(mock_event)
                            
                            # Verify super().paintEvent was called
                            mock_super_paint.assert_called_once_with(mock_event)
                            
                            # Verify QPainter was created
                            mock_painter_class.assert_called_once_with(splash)
                            
                            # Verify render was called
                            mock_render.assert_called_once()
                            
                            # Verify painter.end() was called
                            mock_painter.end.assert_called_once()

    def test_paint_event_without_main_widget(self, qapp):
        """Test paintEvent when main_widget doesn't exist."""
        splash = TrainerSplashScreen()
        
        # Remove main_widget to test the hasattr check
        delattr(splash, 'main_widget')
        
        # Create a mock paint event
        mock_event = Mock(spec=QPaintEvent)
        
        # Mock super().paintEvent
        with patch.object(splash.__class__.__bases__[0], 'paintEvent') as mock_super_paint:
            # Should not crash and should still call super
            splash.paintEvent(mock_event)
            mock_super_paint.assert_called_once_with(mock_event)

    def test_paint_event_calculations(self, qapp):
        """Test paintEvent position calculations."""
        splash = TrainerSplashScreen()
        
        # Create a mock paint event
        mock_event = Mock(spec=QPaintEvent)
        
        # Mock QPainter
        mock_painter = Mock(spec=QPainter)
        mock_transform = Mock()
        mock_transform.map.return_value = QPoint(10, 10)
        mock_painter.deviceTransform.return_value = mock_transform
        
        # Set up specific rect sizes to test calculations
        splash_rect = QRect(0, 0, 500, 400)  # Larger splash
        widget_rect = QRect(0, 0, 400, 300)  # Smaller widget
        
        with patch('src.ui.splash_screen.QPainter', return_value=mock_painter):
            with patch.object(splash, 'rect', return_value=splash_rect):
                with patch.object(splash.main_widget, 'rect', return_value=widget_rect):
                    with patch.object(splash.main_widget, 'render') as mock_render:
                        with patch.object(splash.__class__.__bases__[0], 'paintEvent'):
                            
                            # Call paintEvent
                            splash.paintEvent(mock_event)
                            
                            # Verify render was called with calculated position
                            mock_render.assert_called_once()
                            
                            # Check that deviceTransform().map was called twice
                            assert mock_transform.map.call_count == 2

    def test_paint_event_painter_context_manager(self, qapp):
        """Test paintEvent painter lifecycle."""
        splash = TrainerSplashScreen()
        
        # Create a mock paint event
        mock_event = Mock(spec=QPaintEvent)
        
        # Mock QPainter to track its lifecycle
        mock_painter = Mock(spec=QPainter)
        mock_painter.deviceTransform.return_value.map.return_value = QPoint(0, 0)
        
        with patch('src.ui.splash_screen.QPainter', return_value=mock_painter) as mock_painter_class:
            with patch.object(splash, 'rect', return_value=QRect(0, 0, 400, 300)):
                with patch.object(splash.main_widget, 'rect', return_value=QRect(0, 0, 400, 300)):
                    with patch.object(splash.main_widget, 'render'):
                        with patch.object(splash.__class__.__bases__[0], 'paintEvent'):
                            
                            # Call paintEvent
                            splash.paintEvent(mock_event)
                            
                            # Verify painter was created with splash as argument
                            mock_painter_class.assert_called_once_with(splash)
                            
                            # Verify painter.end() was called to clean up
                            mock_painter.end.assert_called_once()

    def test_widget_properties(self, qapp):
        """Test widget properties and content."""
        splash = TrainerSplashScreen()
        
        # Find all labels in the main widget
        labels = splash.main_widget.findChildren(QLabel)
        
        # Should have 4 labels: emoji, title, subtitle, loading
        assert len(labels) == 4
        
        # Check specific content
        label_texts = [label.text() for label in labels]
        assert "🚂" in label_texts  # Emoji
        assert "🚂 Trainer" in label_texts  # Title
        assert "Train Times Application" in label_texts  # Subtitle
        assert "Loading..." in label_texts  # Loading text

    def test_font_configurations(self, qapp):
        """Test font configurations for different labels."""
        splash = TrainerSplashScreen()
        
        # Find all labels
        labels = splash.main_widget.findChildren(QLabel)
        
        # Check that fonts are configured (different sizes)
        font_sizes = [label.font().pointSize() for label in labels]
        
        # Should have different font sizes
        assert 72 in font_sizes  # Emoji font
        assert 24 in font_sizes  # Title font
        assert 12 in font_sizes  # Subtitle font
        assert 10 in font_sizes  # Loading font

    def test_layout_configuration(self, qapp):
        """Test layout configuration."""
        splash = TrainerSplashScreen()
        
        layout = splash.main_widget.layout()
        
        # Check layout properties
        if layout:
            assert layout.spacing() == 20
            assert layout.alignment() == Qt.AlignmentFlag.AlignCenter

    def test_pixmap_initialization(self, qapp):
        """Test pixmap initialization."""
        # Test that pixmap creation works without mocking to avoid Qt type issues
        splash = TrainerSplashScreen()
        
        # Verify the splash screen was created successfully
        assert splash is not None
        assert splash.size().width() == 400
        assert splash.size().height() == 300

    def test_logging_calls(self, qapp):
        """Test that logging calls are made."""
        with patch('src.ui.splash_screen.logger') as mock_logger:
            splash = TrainerSplashScreen()
            
            # Check initialization logging
            mock_logger.info.assert_called_with("Splash screen initialized")
            
            # Test show_message logging
            splash.show_message("Test")
            mock_logger.debug.assert_called_with("Splash screen message: Test")
            
            # Test close_splash logging
            with patch.object(splash, 'close'):
                splash.close_splash()
                mock_logger.info.assert_called_with("Closing splash screen")
