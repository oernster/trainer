"""
Comprehensive tests for train_widgets.py with 100% coverage.

This module tests all three widget classes: TrainItemWidget, TrainListWidget,
and EmptyStateWidget, focusing on exercising actual code rather than mocking.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QFrame
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QCursor

from src.ui.train_widgets import TrainItemWidget, TrainListWidget, EmptyStateWidget
from src.models.train_data import TrainData, TrainStatus, ServiceType


class TestTrainItemWidget:
    """Test cases for TrainItemWidget class."""

    @pytest.fixture
    def sample_train_on_time(self):
        """Create sample on-time train data."""
        base_time = datetime.now().replace(second=0, microsecond=0)
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
        )

    @pytest.fixture
    def sample_train_delayed(self):
        """Create sample delayed train data."""
        base_time = datetime.now().replace(second=0, microsecond=0)
        return TrainData(
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
        )

    @pytest.fixture
    def sample_train_cancelled(self):
        """Create sample cancelled train data."""
        base_time = datetime.now().replace(second=0, microsecond=0)
        return TrainData(
            departure_time=base_time + timedelta(minutes=35),
            scheduled_departure=base_time + timedelta(minutes=35),
            destination="London Waterloo",
            platform=None,  # No platform for cancelled train
            operator="South Western Railway",
            service_type=ServiceType.EXPRESS,
            status=TrainStatus.CANCELLED,
            delay_minutes=0,
            estimated_arrival=None,  # No arrival for cancelled train
            journey_duration=None,  # No duration for cancelled train
            current_location=None,  # No location for cancelled train
            train_uid="W12347",
            service_id="24673006",
        )

    @pytest.fixture
    def sample_train_minimal(self):
        """Create train data with minimal information."""
        base_time = datetime.now().replace(second=0, microsecond=0)
        return TrainData(
            departure_time=base_time + timedelta(minutes=45),
            scheduled_departure=base_time + timedelta(minutes=45),
            destination="London Waterloo",
            platform=None,
            operator="South Western Railway",
            service_type=ServiceType.SLEEPER,
            status=TrainStatus.UNKNOWN,
            delay_minutes=0,
            estimated_arrival=None,
            journey_duration=None,
            current_location=None,
            train_uid="W12348",
            service_id="24673007",
        )

    def test_init_dark_theme(self, qapp, sample_train_on_time):
        """Test TrainItemWidget initialization with dark theme."""
        widget = TrainItemWidget(sample_train_on_time, "dark")

        assert widget.train_data == sample_train_on_time
        assert widget.current_theme == "dark"
        assert widget.frameStyle() == QFrame.Shape.Box
        assert widget.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_init_light_theme(self, qapp, sample_train_on_time):
        """Test TrainItemWidget initialization with light theme."""
        widget = TrainItemWidget(sample_train_on_time, "light")

        assert widget.train_data == sample_train_on_time
        assert widget.current_theme == "light"

    def test_init_default_theme(self, qapp, sample_train_on_time):
        """Test TrainItemWidget initialization with default theme."""
        widget = TrainItemWidget(sample_train_on_time)

        assert widget.current_theme == "dark"

    def test_setup_ui_with_all_data(self, qapp, sample_train_on_time):
        """Test UI setup with complete train data."""
        widget = TrainItemWidget(sample_train_on_time, "dark")

        # Verify widget has been set up
        layout = widget.layout()
        assert layout is not None
        assert layout.count() > 0

    def test_setup_ui_with_minimal_data(self, qapp, sample_train_minimal):
        """Test UI setup with minimal train data."""
        widget = TrainItemWidget(sample_train_minimal, "dark")

        # Verify widget has been set up even with minimal data
        layout = widget.layout()
        assert layout is not None
        assert layout.count() > 0

    def test_setup_ui_cancelled_train(self, qapp, sample_train_cancelled):
        """Test UI setup with cancelled train (no platform, arrival, etc.)."""
        widget = TrainItemWidget(sample_train_cancelled, "dark")

        # Verify widget handles None values gracefully
        layout = widget.layout()
        assert layout is not None
        assert layout.count() > 0

    def test_apply_theme_dark(self, qapp, sample_train_on_time):
        """Test applying dark theme."""
        widget = TrainItemWidget(sample_train_on_time, "light")
        widget.current_theme = "dark"
        widget.apply_theme()

        # Verify dark theme is applied
        stylesheet = widget.styleSheet()
        assert "#2d2d2d" in stylesheet  # Dark background color
        assert "#ffffff" in stylesheet  # White text color

    def test_apply_theme_light(self, qapp, sample_train_on_time):
        """Test applying light theme."""
        widget = TrainItemWidget(sample_train_on_time, "dark")
        widget.current_theme = "light"
        widget.apply_theme()

        # Verify light theme is applied
        stylesheet = widget.styleSheet()
        assert "#f5f5f5" in stylesheet  # Light background color
        assert "#212121" in stylesheet  # Dark text color

    def test_get_dark_style(self, qapp, sample_train_on_time):
        """Test dark theme stylesheet generation."""
        widget = TrainItemWidget(sample_train_on_time, "dark")
        style = widget.get_dark_style()

        assert "#2d2d2d" in style  # Dark background
        assert "#ffffff" in style  # White text
        assert "#4fc3f7" in style  # Hover color
        assert "border-radius: 8px" in style

    def test_get_light_style(self, qapp, sample_train_on_time):
        """Test light theme stylesheet generation."""
        widget = TrainItemWidget(sample_train_on_time, "light")
        style = widget.get_light_style()

        assert "#f5f5f5" in style  # Light background
        assert "#212121" in style  # Dark text
        assert "#1976d2" in style  # Hover color
        assert "border-radius: 8px" in style

    def test_get_dark_style_different_statuses(self, qapp):
        """Test dark style with different train statuses."""
        base_time = datetime.now().replace(second=0, microsecond=0)

        # Test each status
        for status in [
            TrainStatus.ON_TIME,
            TrainStatus.DELAYED,
            TrainStatus.CANCELLED,
            TrainStatus.UNKNOWN,
        ]:
            train = TrainData(
                departure_time=base_time,
                scheduled_departure=base_time,
                destination="Test",
                platform="1",
                operator="Test",
                service_type=ServiceType.FAST,
                status=status,
                delay_minutes=0,
                estimated_arrival=None,
                journey_duration=None,
                current_location=None,
                train_uid="TEST",
                service_id="TEST",
            )

            widget = TrainItemWidget(train, "dark")
            style = widget.get_dark_style()

            # Verify status color is included
            status_color = train.get_status_color("dark")
            assert status_color in style

    def test_get_light_style_different_statuses(self, qapp):
        """Test light style with different train statuses."""
        base_time = datetime.now().replace(second=0, microsecond=0)

        # Test each status
        for status in [
            TrainStatus.ON_TIME,
            TrainStatus.DELAYED,
            TrainStatus.CANCELLED,
            TrainStatus.UNKNOWN,
        ]:
            train = TrainData(
                departure_time=base_time,
                scheduled_departure=base_time,
                destination="Test",
                platform="1",
                operator="Test",
                service_type=ServiceType.FAST,
                status=status,
                delay_minutes=0,
                estimated_arrival=None,
                journey_duration=None,
                current_location=None,
                train_uid="TEST",
                service_id="TEST",
            )

            widget = TrainItemWidget(train, "light")
            style = widget.get_light_style()

            # Verify status color is included
            status_color = train.get_status_color("light")
            assert status_color in style

    def test_update_theme(self, qapp, sample_train_on_time):
        """Test theme update functionality."""
        widget = TrainItemWidget(sample_train_on_time, "dark")
        original_style = widget.styleSheet()

        # Update to light theme
        widget.update_theme("light")

        assert widget.current_theme == "light"
        assert widget.styleSheet() != original_style
        assert "#f5f5f5" in widget.styleSheet()  # Light theme color

    def test_mouse_press_event_left_click(self, qapp, sample_train_on_time):
        """Test mouse press event with left click."""
        widget = TrainItemWidget(sample_train_on_time, "dark")

        # Connect signal to capture emission
        signal_emitted = False
        emitted_train = None

        def on_train_clicked(train_data):
            nonlocal signal_emitted, emitted_train
            signal_emitted = True
            emitted_train = train_data

        widget.train_clicked.connect(on_train_clicked)

        # Create left mouse button press event
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(10, 10),
            QPoint(10, 10),  # globalPos
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Trigger mouse press event
        widget.mousePressEvent(event)

        assert signal_emitted
        assert emitted_train == sample_train_on_time

    def test_mouse_press_event_right_click(self, qapp, sample_train_on_time):
        """Test mouse press event with right click (should not emit signal)."""
        widget = TrainItemWidget(sample_train_on_time, "dark")

        # Connect signal to capture emission
        signal_emitted = False

        def on_train_clicked(train_data):
            nonlocal signal_emitted
            signal_emitted = True

        widget.train_clicked.connect(on_train_clicked)

        # Create right mouse button press event
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(10, 10),
            QPoint(10, 10),  # globalPos
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Trigger mouse press event
        widget.mousePressEvent(event)

        assert not signal_emitted

    def test_all_service_types_display(self, qapp):
        """Test that all service types display correctly."""
        base_time = datetime.now().replace(second=0, microsecond=0)

        for service_type in ServiceType:
            train = TrainData(
                departure_time=base_time,
                scheduled_departure=base_time,
                destination="Test Destination",
                platform="1",
                operator="Test Operator",
                service_type=service_type,
                status=TrainStatus.ON_TIME,
                delay_minutes=0,
                estimated_arrival=base_time + timedelta(minutes=30),
                journey_duration=timedelta(minutes=30),
                current_location="Test Location",
                train_uid="TEST",
                service_id="TEST",
            )

            widget = TrainItemWidget(train, "dark")

            # Verify widget is created successfully for each service type
            assert widget.train_data.service_type == service_type
            assert widget.layout() is not None


class TestTrainListWidget:
    """Test cases for TrainListWidget class."""

    def test_init_default(self, qapp):
        """Test TrainListWidget initialization with defaults."""
        widget = TrainListWidget()

        assert widget.max_trains == 50
        assert widget.current_theme == "dark"
        assert widget.train_items == []
        assert widget.container_widget is not None
        assert widget.container_layout is not None

    def test_init_custom_max_trains(self, qapp):
        """Test TrainListWidget initialization with custom max_trains."""
        widget = TrainListWidget(max_trains=25)

        assert widget.max_trains == 25

    def test_setup_ui(self, qapp):
        """Test UI setup."""
        widget = TrainListWidget()

        # Verify scroll area configuration
        assert widget.widgetResizable()
        assert (
            widget.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        assert widget.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        assert widget.widget() == widget.container_widget

    def test_apply_theme_dark_default(self, qapp):
        """Test applying dark theme (default)."""
        widget = TrainListWidget()
        widget.apply_theme()

        stylesheet = widget.styleSheet()
        assert "#1a1a1a" in stylesheet  # Dark background
        assert "#2d2d2d" in stylesheet  # Scrollbar background

    def test_apply_theme_light(self, qapp):
        """Test applying light theme."""
        widget = TrainListWidget()
        widget.apply_theme("light")

        assert widget.current_theme == "light"
        stylesheet = widget.styleSheet()
        assert "#ffffff" in stylesheet  # Light background
        assert "#f5f5f5" in stylesheet  # Light scrollbar background

    def test_apply_theme_with_existing_items(self, qapp, sample_train_data):
        """Test applying theme with existing train items."""
        widget = TrainListWidget()
        widget.update_trains(sample_train_data[:2])  # Add some trains

        # Change theme
        widget.apply_theme("light")

        # Verify all train items have updated theme
        for train_item in widget.train_items:
            assert train_item.current_theme == "light"

    def test_get_dark_scroll_style(self, qapp):
        """Test dark scroll area stylesheet."""
        widget = TrainListWidget()
        style = widget.get_dark_scroll_style()

        assert "#1a1a1a" in style  # Background color
        assert "#2d2d2d" in style  # Scrollbar background
        assert "#555555" in style  # Handle color
        assert "border-radius" in style

    def test_get_light_scroll_style(self, qapp):
        """Test light scroll area stylesheet."""
        widget = TrainListWidget()
        style = widget.get_light_scroll_style()

        assert "#ffffff" in style  # Background color
        assert "#f5f5f5" in style  # Scrollbar background
        assert "#bdbdbd" in style  # Handle color
        assert "border-radius" in style

    def test_update_trains_empty_list(self, qapp):
        """Test updating with empty train list."""
        widget = TrainListWidget()
        widget.update_trains([])

        assert widget.get_train_count() == 0
        assert len(widget.train_items) == 0

    def test_update_trains_normal_list(self, qapp, sample_train_data):
        """Test updating with normal train list."""
        widget = TrainListWidget()
        widget.update_trains(sample_train_data)

        assert widget.get_train_count() == len(sample_train_data)
        assert len(widget.train_items) == len(sample_train_data)

    def test_update_trains_exceeds_max(self, qapp, large_train_dataset):
        """Test updating with more trains than max_trains."""
        widget = TrainListWidget(max_trains=10)
        widget.update_trains(large_train_dataset)

        assert widget.get_train_count() == 10
        assert len(widget.train_items) == 10

    def test_update_trains_replaces_existing(self, qapp, sample_train_data):
        """Test that updating trains replaces existing ones."""
        widget = TrainListWidget()

        # Add initial trains
        widget.update_trains(sample_train_data[:2])
        assert widget.get_train_count() == 2

        # Update with different trains
        widget.update_trains(sample_train_data[1:])
        assert widget.get_train_count() == 2  # Should still be 2, but different trains

    def test_clear_trains(self, qapp, sample_train_data):
        """Test clearing all trains."""
        widget = TrainListWidget()
        widget.update_trains(sample_train_data)

        assert widget.get_train_count() > 0

        widget.clear_trains()

        assert widget.get_train_count() == 0
        assert len(widget.train_items) == 0

    def test_add_train_item(self, qapp, sample_train_data):
        """Test adding individual train item."""
        widget = TrainListWidget()
        train = sample_train_data[0]

        widget.add_train_item(train)

        assert widget.get_train_count() == 1
        assert widget.train_items[0].train_data == train

    def test_add_train_item_signal_connection(self, qapp, sample_train_data):
        """Test that train item signals are connected properly."""
        widget = TrainListWidget()
        train = sample_train_data[0]

        # Connect to capture signal
        signal_emitted = False
        emitted_train = None

        def on_train_selected(train_data):
            nonlocal signal_emitted, emitted_train
            signal_emitted = True
            emitted_train = train_data

        widget.train_selected.connect(on_train_selected)

        # Add train item
        widget.add_train_item(train)

        # Simulate clicking the train item
        widget.train_items[0].train_clicked.emit(train)

        assert signal_emitted
        assert emitted_train == train

    def test_get_train_count(self, qapp, sample_train_data):
        """Test getting train count."""
        widget = TrainListWidget()

        assert widget.get_train_count() == 0

        widget.update_trains(sample_train_data[:2])
        assert widget.get_train_count() == 2

        widget.clear_trains()
        assert widget.get_train_count() == 0

    def test_scroll_to_top(self, qapp, large_train_dataset):
        """Test scrolling to top."""
        widget = TrainListWidget(max_trains=10)
        widget.update_trains(large_train_dataset)

        # Scroll to bottom first
        widget.scroll_to_bottom()

        # Then scroll to top
        widget.scroll_to_top()

        assert widget.verticalScrollBar().value() == 0

    def test_scroll_to_bottom(self, qapp, large_train_dataset):
        """Test scrolling to bottom."""
        widget = TrainListWidget(max_trains=10)
        widget.update_trains(large_train_dataset)

        widget.scroll_to_bottom()

        # Should be at maximum scroll position
        assert (
            widget.verticalScrollBar().value() == widget.verticalScrollBar().maximum()
        )

    def test_container_layout_stretch(self, qapp):
        """Test that container layout has stretch at the end."""
        widget = TrainListWidget()

        # The stretch should be the last item in the layout
        last_item = widget.container_layout.itemAt(widget.container_layout.count() - 1)
        assert last_item.spacerItem() is not None  # Stretch is a spacer item

    def test_train_item_insertion_order(self, qapp, sample_train_data):
        """Test that train items are inserted in correct order."""
        widget = TrainListWidget()

        for i, train in enumerate(sample_train_data):
            widget.add_train_item(train)

            # Verify the train was inserted before the stretch (last item)
            train_item_index = widget.container_layout.indexOf(widget.train_items[i])
            assert train_item_index == i  # Should be at index i

            # Verify stretch is still at the end
            last_item = widget.container_layout.itemAt(
                widget.container_layout.count() - 1
            )
            assert last_item.spacerItem() is not None


class TestEmptyStateWidget:
    """Test cases for EmptyStateWidget class."""

    def test_init_dark_theme(self, qapp):
        """Test EmptyStateWidget initialization with dark theme."""
        widget = EmptyStateWidget("dark")

        assert widget.current_theme == "dark"
        assert widget.layout() is not None

    def test_init_light_theme(self, qapp):
        """Test EmptyStateWidget initialization with light theme."""
        widget = EmptyStateWidget("light")

        assert widget.current_theme == "light"

    def test_init_default_theme(self, qapp):
        """Test EmptyStateWidget initialization with default theme."""
        widget = EmptyStateWidget()

        assert widget.current_theme == "dark"

    def test_setup_ui(self, qapp):
        """Test UI setup."""
        widget = EmptyStateWidget()

        # Verify layout exists and has items
        layout = widget.layout()
        assert layout is not None
        assert layout.count() == 3  # Icon, message, subtitle

    def test_apply_theme_dark(self, qapp):
        """Test applying dark theme."""
        widget = EmptyStateWidget("dark")
        widget.apply_theme()

        stylesheet = widget.styleSheet()
        assert "#b0b0b0" in stylesheet  # Dark theme text color

    def test_apply_theme_light(self, qapp):
        """Test applying light theme."""
        widget = EmptyStateWidget("light")
        widget.apply_theme()

        stylesheet = widget.styleSheet()
        assert "#757575" in stylesheet  # Light theme text color

    def test_update_theme(self, qapp):
        """Test theme update functionality."""
        widget = EmptyStateWidget("dark")
        original_style = widget.styleSheet()

        # Update to light theme
        widget.update_theme("light")

        assert widget.current_theme == "light"
        assert widget.styleSheet() != original_style
        assert "#757575" in widget.styleSheet()  # Light theme color

    def test_layout_alignment(self, qapp):
        """Test that layout is center-aligned."""
        widget = EmptyStateWidget()

        layout = widget.layout()
        assert layout is not None
        assert layout.alignment() & Qt.AlignmentFlag.AlignCenter


# Integration tests
class TestWidgetIntegration:
    """Integration tests for widget interactions."""

    def test_train_list_with_empty_state_workflow(self, qapp, sample_train_data):
        """Test workflow from empty state to populated list."""
        train_list = TrainListWidget()
        empty_state = EmptyStateWidget()

        # Start with empty state
        assert train_list.get_train_count() == 0

        # Add trains
        train_list.update_trains(sample_train_data)
        assert train_list.get_train_count() == len(sample_train_data)

        # Clear trains (back to empty state)
        train_list.clear_trains()
        assert train_list.get_train_count() == 0

    def test_theme_consistency_across_widgets(self, qapp, sample_train_data):
        """Test that theme changes are consistent across all widgets."""
        train_list = TrainListWidget()
        empty_state = EmptyStateWidget()

        # Add some trains
        train_list.update_trains(sample_train_data[:2])

        # Change to light theme
        train_list.apply_theme("light")
        empty_state.update_theme("light")

        # Verify all widgets have light theme
        assert train_list.current_theme == "light"
        assert empty_state.current_theme == "light"

        # Verify train items also have light theme
        for train_item in train_list.train_items:
            assert train_item.current_theme == "light"

    def test_signal_propagation(self, qapp, sample_train_data):
        """Test signal propagation from train item to train list."""
        train_list = TrainListWidget()

        # Connect signal
        selected_trains = []

        def on_train_selected(train_data):
            selected_trains.append(train_data)

        train_list.train_selected.connect(on_train_selected)

        # Add trains
        train_list.update_trains(sample_train_data[:2])

        # Simulate clicking each train
        for i, train in enumerate(sample_train_data[:2]):
            train_list.train_items[i].train_clicked.emit(train)

        # Verify signals were received
        assert len(selected_trains) == 2
        assert selected_trains[0] == sample_train_data[0]
        assert selected_trains[1] == sample_train_data[1]

    @patch("src.ui.train_widgets.logger")
    def test_logging_integration(self, mock_logger, qapp, sample_train_data):
        """Test that logging works correctly."""
        train_list = TrainListWidget(max_trains=25)

        # Verify initialization logging
        mock_logger.info.assert_called_with(
            "TrainListWidget initialized with max_trains=25"
        )

        # Update trains and verify logging
        train_list.update_trains(sample_train_data)
        mock_logger.info.assert_called_with(
            f"Updated train list with {len(sample_train_data)} trains"
        )
