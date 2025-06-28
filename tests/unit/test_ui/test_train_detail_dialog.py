"""
Comprehensive tests for TrainDetailDialog with 100% coverage.

This test suite covers all functionality of the train detail dialog
including CallingPointWidget and TrainDetailDialog classes.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import cast
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from src.ui.train_detail_dialog import CallingPointWidget, TrainDetailDialog
from src.models.train_data import TrainData, TrainStatus, ServiceType, CallingPoint


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def sample_calling_point():
    """Create a sample calling point."""
    return CallingPoint(
        station_name="Woking",
        station_code="WOK",
        scheduled_arrival=datetime.now() + timedelta(minutes=20),
        scheduled_departure=datetime.now() + timedelta(minutes=21),
        expected_arrival=datetime.now() + timedelta(minutes=22),
        expected_departure=datetime.now() + timedelta(minutes=23),
        platform="2",
        is_origin=False,
        is_destination=False,
    )


@pytest.fixture
def origin_calling_point():
    """Create an origin calling point."""
    return CallingPoint(
        station_name="Fleet",
        station_code="FLE",
        scheduled_arrival=None,
        scheduled_departure=datetime.now(),
        expected_arrival=None,
        expected_departure=datetime.now() + timedelta(minutes=2),
        platform="1",
        is_origin=True,
        is_destination=False,
    )


@pytest.fixture
def destination_calling_point():
    """Create a destination calling point."""
    return CallingPoint(
        station_name="London Waterloo",
        station_code="WAT",
        scheduled_arrival=datetime.now() + timedelta(minutes=47),
        scheduled_departure=None,
        expected_arrival=datetime.now() + timedelta(minutes=49),
        expected_departure=None,
        platform=None,
        is_origin=False,
        is_destination=True,
    )


@pytest.fixture
def sample_train_data(origin_calling_point, sample_calling_point, destination_calling_point):
    """Create sample train data with calling points."""
    base_time = datetime.now()
    return TrainData(
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
        calling_points=[origin_calling_point, sample_calling_point, destination_calling_point],
    )


@pytest.fixture
def delayed_train_data():
    """Create delayed train data."""
    base_time = datetime.now()
    calling_point = CallingPoint(
        station_name="Test Station",
        station_code="TST",
        scheduled_arrival=base_time + timedelta(minutes=30),
        scheduled_departure=base_time + timedelta(minutes=31),
        expected_arrival=base_time + timedelta(minutes=35),
        expected_departure=base_time + timedelta(minutes=36),
        platform=None,
        is_origin=False,
        is_destination=False,
    )
    
    return TrainData(
        departure_time=base_time + timedelta(minutes=20),
        scheduled_departure=base_time + timedelta(minutes=15),
        destination="London Waterloo",
        platform=None,  # TBA platform
        operator="Test Railway",
        service_type=ServiceType.STOPPING,
        status=TrainStatus.DELAYED,
        delay_minutes=5,
        estimated_arrival=base_time + timedelta(minutes=67),
        journey_duration=timedelta(minutes=47),
        current_location="Fleet",
        train_uid="W12346",
        service_id="24673005",
        calling_points=[calling_point],
    )


class TestCallingPointWidget:
    """Test cases for CallingPointWidget class."""

    def test_init_regular_calling_point_dark_theme(self, qapp, sample_calling_point):
        """Test initialization with regular calling point in dark theme."""
        widget = CallingPointWidget(sample_calling_point, "dark")
        
        assert widget.calling_point == sample_calling_point
        assert widget.current_theme == "dark"
        assert widget.layout() is not None

    def test_init_regular_calling_point_light_theme(self, qapp, sample_calling_point):
        """Test initialization with regular calling point in light theme."""
        widget = CallingPointWidget(sample_calling_point, "light")
        
        assert widget.calling_point == sample_calling_point
        assert widget.current_theme == "light"

    def test_init_origin_calling_point(self, qapp, origin_calling_point):
        """Test initialization with origin calling point."""
        widget = CallingPointWidget(origin_calling_point, "dark")
        
        assert widget.calling_point == origin_calling_point
        assert widget.calling_point.is_origin is True

    def test_init_destination_calling_point(self, qapp, destination_calling_point):
        """Test initialization with destination calling point."""
        widget = CallingPointWidget(destination_calling_point, "dark")
        
        assert widget.calling_point == destination_calling_point
        assert widget.calling_point.is_destination is True

    def test_setup_ui_with_platform(self, qapp, sample_calling_point):
        """Test UI setup with platform information."""
        widget = CallingPointWidget(sample_calling_point, "dark")
        
        # Check that layout has widgets
        layout = cast(QHBoxLayout, widget.layout())
        assert layout.count() > 0
        
        # Find platform label
        platform_labels = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget_item = item.widget()
                if isinstance(widget_item, QLabel) and "Plat" in widget_item.text():
                    platform_labels.append(widget_item)
        
        assert len(platform_labels) == 1
        assert "Plat 2" in platform_labels[0].text()

    def test_setup_ui_without_platform(self, qapp, destination_calling_point):
        """Test UI setup without platform information."""
        widget = CallingPointWidget(destination_calling_point, "dark")
        
        # Check that layout has widgets
        layout = cast(QHBoxLayout, widget.layout())
        assert layout.count() > 0
        
        # Should not have platform label
        platform_labels = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget_item = item.widget()
                if isinstance(widget_item, QLabel) and "Plat" in widget_item.text():
                    platform_labels.append(widget_item)
        
        assert len(platform_labels) == 0

    def test_setup_ui_with_time_display(self, qapp):
        """Test UI setup with time display."""
        # Create a calling point that will have a time display
        calling_point = CallingPoint(
            station_name="Test Station",
            station_code="TST",
            scheduled_arrival=datetime.now() + timedelta(minutes=20),
            scheduled_departure=datetime.now() + timedelta(minutes=21),
            expected_arrival=datetime.now() + timedelta(minutes=22),
            expected_departure=datetime.now() + timedelta(minutes=23),
            platform="2",
            is_origin=False,
            is_destination=False,
        )
        
        widget = CallingPointWidget(calling_point, "dark")
        
        # Find time label - should exist since calling point has times
        layout = cast(QHBoxLayout, widget.layout())
        time_labels = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget_item = item.widget()
                if isinstance(widget_item, QLabel):
                    text = widget_item.text()
                    # Check if it looks like a time (contains colon and digits)
                    if ":" in text and any(c.isdigit() for c in text):
                        time_labels.append(widget_item)
        
        assert len(time_labels) >= 1

    def test_setup_ui_without_time_display(self, qapp):
        """Test UI setup without time display."""
        # Create a calling point with no times (origin with only departure)
        calling_point = CallingPoint(
            station_name="Test Station",
            station_code="TST",
            scheduled_arrival=None,
            scheduled_departure=None,
            expected_arrival=None,
            expected_departure=None,
            platform="2",
            is_origin=True,
            is_destination=False,
        )
        
        widget = CallingPointWidget(calling_point, "dark")
        
        # Should still create the widget successfully
        layout = cast(QHBoxLayout, widget.layout())
        assert layout.count() > 0
        
        # Should have station name but no time labels
        station_labels = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget_item = item.widget()
                if isinstance(widget_item, QLabel) and calling_point.station_name in widget_item.text():
                    station_labels.append(widget_item)
        
        assert len(station_labels) == 1

    def test_setup_ui_bold_font_for_origin(self, qapp, origin_calling_point):
        """Test that origin stations have bold font."""
        widget = CallingPointWidget(origin_calling_point, "dark")
        
        # Find station label
        layout = cast(QHBoxLayout, widget.layout())
        station_labels = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget_item = item.widget()
                if isinstance(widget_item, QLabel) and origin_calling_point.station_name in widget_item.text():
                    station_labels.append(widget_item)
        
        assert len(station_labels) == 1
        assert station_labels[0].font().bold() is True

    def test_setup_ui_bold_font_for_destination(self, qapp, destination_calling_point):
        """Test that destination stations have bold font."""
        widget = CallingPointWidget(destination_calling_point, "dark")
        
        # Find station label
        layout = cast(QHBoxLayout, widget.layout())
        station_labels = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget_item = item.widget()
                if isinstance(widget_item, QLabel) and destination_calling_point.station_name in widget_item.text():
                    station_labels.append(widget_item)
        
        assert len(station_labels) == 1
        assert station_labels[0].font().bold() is True

    def test_setup_ui_normal_font_for_intermediate(self, qapp, sample_calling_point):
        """Test that intermediate stations have normal font."""
        widget = CallingPointWidget(sample_calling_point, "dark")
        
        # Find station label
        layout = cast(QHBoxLayout, widget.layout())
        station_labels = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget_item = item.widget()
                if isinstance(widget_item, QLabel) and sample_calling_point.station_name in widget_item.text():
                    station_labels.append(widget_item)
        
        assert len(station_labels) == 1
        assert station_labels[0].font().bold() is False

    def test_apply_theme_dark_origin(self, qapp, origin_calling_point):
        """Test dark theme styling for origin station."""
        widget = CallingPointWidget(origin_calling_point, "dark")
        
        stylesheet = widget.styleSheet()
        assert "#2d4a2d" in stylesheet  # Green background
        assert "#4caf50" in stylesheet  # Green border
        assert "#ffffff" in stylesheet  # White text

    def test_apply_theme_dark_destination(self, qapp, destination_calling_point):
        """Test dark theme styling for destination station."""
        widget = CallingPointWidget(destination_calling_point, "dark")
        
        stylesheet = widget.styleSheet()
        assert "#4a2d2d" in stylesheet  # Red background
        assert "#f44336" in stylesheet  # Red border
        assert "#ffffff" in stylesheet  # White text

    def test_apply_theme_dark_intermediate(self, qapp, sample_calling_point):
        """Test dark theme styling for intermediate station."""
        widget = CallingPointWidget(sample_calling_point, "dark")
        
        stylesheet = widget.styleSheet()
        assert "#2d2d2d" in stylesheet  # Gray background
        assert "#666666" in stylesheet  # Gray border
        assert "#cccccc" in stylesheet  # Light gray text

    def test_apply_theme_light_origin(self, qapp, origin_calling_point):
        """Test light theme styling for origin station."""
        widget = CallingPointWidget(origin_calling_point, "light")
        
        stylesheet = widget.styleSheet()
        assert "#e8f5e8" in stylesheet  # Light green background
        assert "#388e3c" in stylesheet  # Green border
        assert "#212121" in stylesheet  # Dark text

    def test_apply_theme_light_destination(self, qapp, destination_calling_point):
        """Test light theme styling for destination station."""
        widget = CallingPointWidget(destination_calling_point, "light")
        
        stylesheet = widget.styleSheet()
        assert "#fde8e8" in stylesheet  # Light red background
        assert "#d32f2f" in stylesheet  # Red border
        assert "#212121" in stylesheet  # Dark text

    def test_apply_theme_light_intermediate(self, qapp, sample_calling_point):
        """Test light theme styling for intermediate station."""
        widget = CallingPointWidget(sample_calling_point, "light")
        
        stylesheet = widget.styleSheet()
        assert "#f5f5f5" in stylesheet  # Light gray background
        assert "#9e9e9e" in stylesheet  # Gray border
        assert "#424242" in stylesheet  # Dark gray text


class TestTrainDetailDialog:
    """Test cases for TrainDetailDialog class."""

    def test_init_with_train_data_dark_theme(self, qapp, sample_train_data):
        """Test initialization with train data in dark theme."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        assert dialog.train_data == sample_train_data
        assert dialog.current_theme == "dark"
        assert dialog.windowTitle() == f"Train Details - {sample_train_data.destination}"
        assert dialog.isModal() is True
        assert dialog.size().width() == 500
        assert dialog.size().height() == 600

    def test_init_with_train_data_light_theme(self, qapp, sample_train_data):
        """Test initialization with train data in light theme."""
        dialog = TrainDetailDialog(sample_train_data, "light")
        
        assert dialog.current_theme == "light"

    def test_init_with_parent(self, qapp, sample_train_data):
        """Test initialization with parent widget."""
        from PySide6.QtWidgets import QWidget
        parent = QWidget()
        dialog = TrainDetailDialog(sample_train_data, "dark", parent)
        
        assert dialog.train_data == sample_train_data
        parent.deleteLater()  # Clean up

    def test_init_default_theme(self, qapp, sample_train_data):
        """Test initialization with default theme."""
        dialog = TrainDetailDialog(sample_train_data)
        
        assert dialog.current_theme == "dark"

    def test_setup_ui_header_content(self, qapp, sample_train_data):
        """Test that header contains correct train information."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find labels in the dialog
        labels = dialog.findChildren(QLabel)
        
        # Check for main info label
        main_info_labels = [
            label for label in labels
            if sample_train_data.destination in label.text()
            and sample_train_data.get_service_icon() in label.text()
        ]
        assert len(main_info_labels) >= 1

    def test_setup_ui_service_details(self, qapp, sample_train_data):
        """Test that service details are displayed correctly."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find labels in the dialog
        labels = dialog.findChildren(QLabel)
        
        # Check for service info label
        service_info_labels = [
            label for label in labels
            if sample_train_data.operator in label.text()
            and sample_train_data.service_type.value.title() in label.text()
        ]
        assert len(service_info_labels) >= 1

    def test_setup_ui_service_details_with_platform_tba(self, qapp, delayed_train_data):
        """Test service details with TBA platform."""
        dialog = TrainDetailDialog(delayed_train_data, "dark")
        
        # Find labels in the dialog
        labels = dialog.findChildren(QLabel)
        
        # Check for service info label with TBA platform
        service_info_labels = [
            label for label in labels
            if "Platform TBA" in label.text()
        ]
        assert len(service_info_labels) >= 1

    def test_setup_ui_status_information(self, qapp, sample_train_data):
        """Test that status information is displayed correctly."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find labels in the dialog
        labels = dialog.findChildren(QLabel)
        
        # Check for status info label
        status_info_labels = [
            label for label in labels
            if sample_train_data.get_status_icon() in label.text()
        ]
        assert len(status_info_labels) >= 1

    def test_setup_ui_status_color_application(self, qapp, delayed_train_data):
        """Test that status color is applied correctly."""
        dialog = TrainDetailDialog(delayed_train_data, "dark")
        
        # Find labels in the dialog
        labels = dialog.findChildren(QLabel)
        
        # Check for status info label with color styling
        status_info_labels = [
            label for label in labels
            if delayed_train_data.get_status_icon() in label.text()
            and label.styleSheet()  # Should have color styling
        ]
        assert len(status_info_labels) >= 1
        
        # Verify the color matches the train's status color
        expected_color = delayed_train_data.get_status_color("dark")
        assert expected_color in status_info_labels[0].styleSheet()

    def test_setup_ui_calling_points_label(self, qapp, sample_train_data):
        """Test that calling points label is present."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find labels in the dialog
        labels = dialog.findChildren(QLabel)
        
        # Check for calling points label
        calling_points_labels = [
            label for label in labels
            if "Calling Points:" in label.text()
        ]
        assert len(calling_points_labels) == 1
        assert calling_points_labels[0].font().bold() is True

    def test_setup_ui_calling_point_widgets(self, qapp, sample_train_data):
        """Test that calling point widgets are created."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find calling point widgets
        calling_point_widgets = dialog.findChildren(CallingPointWidget)
        
        # Should have one widget for each calling point
        assert len(calling_point_widgets) == len(sample_train_data.calling_points)
        
        # Verify each widget has the correct calling point
        for i, widget in enumerate(calling_point_widgets):
            assert widget.calling_point == sample_train_data.calling_points[i]
            assert widget.current_theme == "dark"

    def test_setup_ui_scroll_area_configuration(self, qapp, sample_train_data):
        """Test that scroll area is configured correctly."""
        from PySide6.QtWidgets import QScrollArea
        
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find scroll area
        scroll_areas = dialog.findChildren(QScrollArea)
        assert len(scroll_areas) == 1
        
        scroll_area = scroll_areas[0]
        assert scroll_area.widgetResizable() is True
        assert scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    def test_setup_ui_close_button(self, qapp, sample_train_data):
        """Test that close button is present and functional."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find close button
        buttons = dialog.findChildren(QPushButton)
        close_buttons = [button for button in buttons if button.text() == "Close"]
        assert len(close_buttons) == 1
        
        close_button = close_buttons[0]
        
        # Test button click
        with patch.object(dialog, 'accept') as mock_accept:
            close_button.click()
            mock_accept.assert_called_once()

    def test_apply_theme_dark(self, qapp, sample_train_data):
        """Test dark theme styling application."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        stylesheet = dialog.styleSheet()
        assert "#1a1a1a" in stylesheet  # Dark background
        assert "#ffffff" in stylesheet  # White text
        assert "#4fc3f7" in stylesheet  # Button color

    def test_apply_theme_light(self, qapp, sample_train_data):
        """Test light theme styling application."""
        dialog = TrainDetailDialog(sample_train_data, "light")
        
        stylesheet = dialog.styleSheet()
        assert "#ffffff" in stylesheet  # Light background
        assert "#212121" in stylesheet  # Dark text
        assert "#1976d2" in stylesheet  # Button color

    def test_dialog_modal_behavior(self, qapp, sample_train_data):
        """Test that dialog is modal."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        assert dialog.isModal() is True

    def test_dialog_window_title_formatting(self, qapp, sample_train_data):
        """Test window title formatting."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        expected_title = f"Train Details - {sample_train_data.destination}"
        assert dialog.windowTitle() == expected_title

    def test_dialog_size_configuration(self, qapp, sample_train_data):
        """Test dialog size configuration."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        assert dialog.size().width() == 500
        assert dialog.size().height() == 600

    def test_layout_spacing_configuration(self, qapp, sample_train_data):
        """Test that layout spacing is configured correctly."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        layout = cast(QVBoxLayout, dialog.layout())
        assert layout.spacing() == 12

    def test_header_frame_structure(self, qapp, sample_train_data):
        """Test header frame structure."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find frames in the dialog
        frames = dialog.findChildren(QFrame)
        
        # Should have at least one frame for the header
        assert len(frames) >= 1

    def test_font_configurations(self, qapp, sample_train_data):
        """Test that fonts are configured correctly."""
        dialog = TrainDetailDialog(sample_train_data, "dark")
        
        # Find labels with different font sizes
        labels = dialog.findChildren(QLabel)
        
        # Check for main info label (16pt, bold)
        main_info_labels = [
            label for label in labels
            if label.font().pointSize() == 16 and label.font().bold()
        ]
        assert len(main_info_labels) >= 1
        
        # Check for service info labels (12pt)
        service_info_labels = [
            label for label in labels
            if label.font().pointSize() == 12
        ]
        assert len(service_info_labels) >= 1
        
        # Check for calling points label (14pt, bold)
        calling_points_labels = [
            label for label in labels
            if label.font().pointSize() == 14 and label.font().bold()
        ]
        assert len(calling_points_labels) >= 1

    def test_empty_calling_points_handling(self, qapp):
        """Test handling of train data with no calling points."""
        base_time = datetime.now()
        train_data = TrainData(
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
            calling_points=[],  # Empty calling points
        )
        
        dialog = TrainDetailDialog(train_data, "dark")
        
        # Should still create dialog successfully
        assert dialog.train_data == train_data
        
        # Should have no calling point widgets
        calling_point_widgets = dialog.findChildren(CallingPointWidget)
        assert len(calling_point_widgets) == 0

    def test_integration_with_different_service_types(self, qapp):
        """Test dialog with different service types."""
        base_time = datetime.now()
        
        for service_type in [ServiceType.FAST, ServiceType.STOPPING, ServiceType.EXPRESS, ServiceType.SLEEPER]:
            train_data = TrainData(
                departure_time=base_time + timedelta(minutes=15),
                scheduled_departure=base_time + timedelta(minutes=15),
                destination="London Waterloo",
                platform="2",
                operator="South Western Railway",
                service_type=service_type,
                status=TrainStatus.ON_TIME,
                delay_minutes=0,
                estimated_arrival=base_time + timedelta(minutes=62),
                journey_duration=timedelta(minutes=47),
                current_location="Fleet",
                train_uid="W12345",
                service_id="24673004",
                calling_points=[],
            )
            
            dialog = TrainDetailDialog(train_data, "dark")
            
            # Find service info labels
            labels = dialog.findChildren(QLabel)
            service_labels = [
                label for label in labels
                if service_type.value.title() in label.text()
            ]
            assert len(service_labels) >= 1

    def test_integration_with_different_statuses(self, qapp):
        """Test dialog with different train statuses."""
        base_time = datetime.now()
        
        for status in [TrainStatus.ON_TIME, TrainStatus.DELAYED, TrainStatus.CANCELLED, TrainStatus.UNKNOWN]:
            train_data = TrainData(
                departure_time=base_time + timedelta(minutes=15),
                scheduled_departure=base_time + timedelta(minutes=15),
                destination="London Waterloo",
                platform="2",
                operator="South Western Railway",
                service_type=ServiceType.FAST,
                status=status,
                delay_minutes=5 if status == TrainStatus.DELAYED else 0,
                estimated_arrival=base_time + timedelta(minutes=62),
                journey_duration=timedelta(minutes=47),
                current_location="Fleet",
                train_uid="W12345",
                service_id="24673004",
                calling_points=[],
            )
            
            dialog = TrainDetailDialog(train_data, "dark")
            
            # Should create dialog successfully for all statuses
            assert dialog.train_data.status == status