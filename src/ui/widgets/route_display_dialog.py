"""
Route display dialog for showing complete train journey details.

This module provides a dialog that displays all calling points for a train route
with comprehensive station information and interchange detection.
"""

import logging
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ...models.train_data import TrainData, CallingPoint
from ...core.services.interchange_detection_service import InterchangeDetectionService
# Underground formatter removed as part of underground code removal
from .train_widgets_base import BaseTrainWidget

logger = logging.getLogger(__name__)


class RouteDisplayDialog(QDialog):
    """Dialog to display all calling points for a train route."""

    def __init__(self, train_data: TrainData, theme: str = "dark", 
                 parent: Optional[QWidget] = None, train_manager=None):
        """
        Initialize route display dialog.

        Args:
            train_data: Train data to display route for
            theme: Current theme ("dark" or "light")
            parent: Parent widget
            train_manager: Train manager instance for detailed route generation
        """
        super().__init__(parent)
        self.train_data = train_data
        self.current_theme = theme
        self.train_manager = train_manager
        
        # Underground formatter removed
        
        # Cache for station data to avoid repeated loading
        self._station_to_files_cache: Optional[Dict] = None
        self._line_to_file_cache: Optional[Dict] = None
        self._station_coordinates_cache: Optional[Dict] = None
        
        # Format destination with underground indicator if needed
        destination_text = self._format_station_name(train_data.destination)
        self.setWindowTitle(f"Route - {train_data.format_departure_time()} to {destination_text}")
        self.setModal(True)
        self.resize(450, 400)
        
        # Center the dialog on Linux
        if sys.platform.startswith('linux'):
            self._center_on_screen()
        
        self._setup_ui()
        self._apply_theme()
    
    def _center_on_screen(self):
        """Center the dialog on the primary screen."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            dialog_geometry = self.frameGeometry()
            x = (screen_geometry.width() - dialog_geometry.width()) // 2
            y = (screen_geometry.height() - dialog_geometry.height()) // 2
            self.move(x, y)
            logger.debug(f"Centered route display dialog at ({x}, {y})")

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header with train info
        self._create_header(layout)
        
        # Route title
        self._create_route_title(layout)
        
        # Scrollable calling points list
        self._create_calling_points_section(layout)
        
        # Close button
        self._create_close_button(layout)

    def _create_header(self, layout: QVBoxLayout) -> None:
        """Create the dialog header with train information."""
        destination_text = self._format_station_name(self.train_data.destination)
        header_label = QLabel(
            f"🚂 {self.train_data.format_departure_time()} → {destination_text}"
        )
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

    def _create_route_title(self, layout: QVBoxLayout) -> None:
        """Create the route title section."""
        route_label = QLabel("Complete Journey with All Stops:")
        route_font = QFont()
        route_font.setPointSize(12)
        route_font.setBold(True)
        route_label.setFont(route_font)
        layout.addWidget(route_label)

    def _create_calling_points_section(self, layout: QVBoxLayout) -> None:
        """Create the scrollable calling points section."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        calling_points_widget = QWidget()
        calling_points_layout = QVBoxLayout(calling_points_widget)
        calling_points_layout.setSpacing(4)

        # Get filtered calling points
        filtered_calling_points = self._get_filtered_calling_points()
        
        # Display all stations in the route
        for i, calling_point in enumerate(filtered_calling_points):
            station_frame = self._create_station_frame(calling_point, i)
            calling_points_layout.addWidget(station_frame)

        calling_points_layout.addStretch()
        scroll_area.setWidget(calling_points_widget)
        layout.addWidget(scroll_area)

    def _get_filtered_calling_points(self) -> List[CallingPoint]:
        """Get filtered calling points for display."""
        # First check if we can get the full route path from the train manager
        full_path = None
        if self.train_manager and hasattr(self.train_manager, 'route_path') and self.train_manager.route_path:
            full_path = self.train_manager.route_path
            logger.info(f"Using full route path from train manager with {len(full_path)} stations")
        
        # If we have a full path, use it to create a more comprehensive display
        if full_path and len(full_path) >= 2:
            return self._create_calling_points_from_full_path(full_path)
        else:
            # Fall back to using original calling points
            return self._filter_original_calling_points()

    def _create_calling_points_from_full_path(self, full_path: List[str]) -> List[CallingPoint]:
        """Create calling points from the full route path."""
        original_calling_points = self.train_data.calling_points
        origin_cp = None
        destination_cp = None
        
        # Find origin and destination calling points
        for cp in original_calling_points:
            if cp.is_origin:
                origin_cp = cp
            elif cp.is_destination:
                destination_cp = cp
        
        # Create a mapping of station names to calling points for intermediate stations
        station_to_cp = {}
        for cp in original_calling_points:
            if not cp.is_origin and not cp.is_destination:
                station_to_cp[cp.station_name] = cp
        
        # Create new calling points list using the full path
        filtered_calling_points = []
        
        # Add each station from the full path
        for i, station_name in enumerate(full_path):
            is_origin = (i == 0)
            is_destination = (i == len(full_path) - 1)
            
            # Use existing calling point if available
            if is_origin and origin_cp:
                filtered_calling_points.append(origin_cp)
            elif is_destination and destination_cp:
                filtered_calling_points.append(destination_cp)
            elif station_name in station_to_cp:
                # Use existing intermediate calling point
                filtered_calling_points.append(station_to_cp[station_name])
            else:
                # Create a new calling point without timing info
                new_cp = CallingPoint(
                    station_name=station_name,
                    scheduled_arrival=None,
                    scheduled_departure=None,
                    expected_arrival=None,
                    expected_departure=None,
                    platform=None,
                    is_origin=is_origin,
                    is_destination=is_destination
                )
                filtered_calling_points.append(new_cp)
        
        logger.info(f"Created {len(filtered_calling_points)} calling points from full route path")
        return filtered_calling_points

    def _filter_original_calling_points(self) -> List[CallingPoint]:
        """Filter original calling points to remove duplicates."""
        calling_points = self.train_data.calling_points
        logger.info(f"Falling back to original {len(calling_points)} calling points in route dialog")
        
        # Remove duplicate stations (keep the one with more complete information)
        seen_stations = set()
        filtered_calling_points = []
        
        for calling_point in calling_points:
            station_name = calling_point.station_name
            if station_name not in seen_stations:
                seen_stations.add(station_name)
                filtered_calling_points.append(calling_point)
            else:
                # If we've seen this station before, check if this one has more info
                for j, existing_cp in enumerate(filtered_calling_points):
                    if existing_cp.station_name == station_name:
                        # Prefer origin/destination over intermediate, or one with platform info
                        if (calling_point.is_origin or calling_point.is_destination or
                            (calling_point.platform and not existing_cp.platform)):
                            filtered_calling_points[j] = calling_point
                        break

        logger.info(f"Filtered to {len(filtered_calling_points)} unique stations")
        return filtered_calling_points

    def _create_station_frame(self, calling_point: CallingPoint, index: int) -> QFrame:
        """Create a frame for displaying station information."""
        station_frame = QFrame()
        station_layout = QHBoxLayout(station_frame)
        station_layout.setContentsMargins(8, 4, 8, 4)

        # Station name with special formatting for origin/destination
        station_label = QLabel()
        
        # Format station name with underground indicator if needed
        formatted_name = self._format_station_name(calling_point.station_name)
        station_label.setText(formatted_name)
        station_label.setTextFormat(Qt.TextFormat.RichText)
        
        station_font = QFont()
        station_font.setPointSize(11)
        
        # Check if this is origin or destination
        is_origin = calling_point.is_origin
        is_destination = calling_point.is_destination
        
        if is_origin or is_destination:
            station_font.setBold(True)
        station_label.setFont(station_font)
        station_layout.addWidget(station_label)

        # Add CHANGE indicator for major interchange stations (but not origin/destination)
        if self._is_major_interchange(calling_point.station_name) and not is_origin and not is_destination:
            change_label = QLabel("CHANGE")
            change_font = QFont()
            change_font.setPointSize(9)
            change_font.setBold(True)
            change_label.setFont(change_font)
            change_label.setStyleSheet(
                "color: #f57f17; background-color: rgba(255, 235, 59, 0.3); "
                "padding: 2px 4px; border-radius: 2px;"
            )
            station_layout.addWidget(change_label)

        station_layout.addStretch()

        # Time (if available)
        time_text = calling_point.get_display_time()
        if time_text:
            time_label = QLabel(time_text)
            time_font = QFont()
            time_font.setPointSize(11)
            time_font.setFamily("monospace")
            time_label.setFont(time_font)
            station_layout.addWidget(time_label)

        # Platform (if available)
        if calling_point.platform:
            platform_label = QLabel(f"Plat {calling_point.platform}")
            platform_font = QFont()
            platform_font.setPointSize(9)
            platform_label.setFont(platform_font)
            station_layout.addWidget(platform_label)

        # Apply styling based on station type
        self._style_station_frame(station_frame, calling_point)

        return station_frame

    def _style_station_frame(self, frame: QFrame, calling_point: CallingPoint) -> None:
        """Apply styling to station frame based on station type."""
        station_name = calling_point.station_name
        is_walking = ("<font color='#f44336'" in station_name)
        
        if calling_point.is_origin:
            frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(76, 175, 80, 0.2);
                    border-left: 3px solid #4caf50;
                    border-radius: 4px;
                    margin: 1px;
                }
            """)
        elif calling_point.is_destination:
            frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(244, 67, 54, 0.2);
                    border-left: 3px solid #f44336;
                    border-radius: 4px;
                    margin: 1px;
                }
            """)
        elif is_walking:
            frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(244, 67, 54, 0.1);
                    border-left: 3px solid #f44336;
                    border-radius: 4px;
                    margin: 1px;
                }
            """)
        elif self._is_major_interchange(calling_point.station_name):
            # Highlight interchange stations with theme-aware color
            if self.current_theme == "light":
                frame.setStyleSheet("""
                    QFrame {
                        background-color: rgba(76, 175, 80, 0.2);
                        border-left: 3px solid #4caf50;
                        border-radius: 4px;
                        margin: 1px;
                    }
                """)
            else:
                frame.setStyleSheet("""
                    QFrame {
                        background-color: rgba(255, 235, 59, 0.2);
                        border-left: 3px solid #ffeb3b;
                        border-radius: 4px;
                        margin: 1px;
                    }
                """)
        else:
            frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(158, 158, 158, 0.1);
                    border-left: 3px solid #9e9e9e;
                    border-radius: 4px;
                    margin: 1px;
                }
            """)

    def _create_close_button(self, layout: QVBoxLayout) -> None:
        """Create the close button."""
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def _apply_theme(self) -> None:
        """Apply theme styling to the dialog."""
        if self.current_theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #1976d2;
                    color: #000000;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QScrollArea {
                    border: 1px solid #404040;
                    border-radius: 4px;
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    color: #212121;
                }
                QLabel {
                    color: #212121;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #1976d2;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QScrollArea {
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: #ffffff;
                }
            """)
    
    def _is_major_interchange(self, station_name: str) -> bool:
        """Check if a station is where the passenger actually changes trains/lines during this journey."""
        clean_name = station_name.replace(" (Cross Country Line)", "").strip()
        
        logger.debug(f"[RouteDialog] Checking interchange status for station: {clean_name}")
        
        # Check if we have route_segments data for line changes
        if hasattr(self.train_data, 'route_segments') and self.train_data.route_segments:
            # Use the InterchangeDetectionService for intelligent detection
            interchange_service = InterchangeDetectionService()
            interchanges = interchange_service.detect_user_journey_interchanges(self.train_data.route_segments)
            
            # Check if this station is marked as a user journey change
            for interchange in interchanges:
                if interchange.station_name == clean_name and interchange.is_user_journey_change:
                    logger.debug(f"[RouteDialog] Station {clean_name} is a valid user journey interchange")
                    return True
            
            logger.debug(f"[RouteDialog] Station {clean_name} is not a user journey interchange")
            return False
        else:
            logger.debug(f"[RouteDialog] No route segments available for {clean_name}")
            return False

    def _get_station_to_json_files_mapping(self) -> Dict:
        """Create a mapping of station names to the JSON files they appear in."""
        if self._station_to_files_cache is not None:
            return self._station_to_files_cache
        
        self._station_to_files_cache = self._build_station_to_files_mapping()
        return self._station_to_files_cache
    
    def _build_station_to_files_mapping(self) -> Dict:
        """Build the mapping of stations to JSON files by loading all line data."""
        station_to_files = {}
        
        lines_dir = Path(__file__).parent.parent.parent / "data" / "lines"
        
        if not lines_dir.exists():
            logger.error(f"Lines directory not found: {lines_dir}")
            return {}
        
        try:
            for json_file in lines_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Get stations from this JSON file
                    stations = data.get('stations', [])
                    file_name = json_file.stem  # Get filename without extension
                    
                    for station in stations:
                        station_name = station.get('name', '')
                        if station_name:
                            if station_name not in station_to_files:
                                station_to_files[station_name] = []
                            station_to_files[station_name].append(file_name)
            
            logger.debug(f"Built station-to-files mapping with {len(station_to_files)} stations")
            return station_to_files
            
        except Exception as e:
            logger.error(f"Failed to build station-to-files mapping: {e}")
            return {}
    
    def _format_station_name(self, station_name: str) -> str:
        """Format station name - underground detection removed."""
        return station_name