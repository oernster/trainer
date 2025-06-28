"""
Train detail dialog for displaying comprehensive train information.

This module provides a detailed view of train information including
all calling points, times, and service details.
"""

import logging
from typing import List
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QWidget,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ..models.train_data import TrainData, CallingPoint

logger = logging.getLogger(__name__)


class CallingPointWidget(QFrame):
    """Widget to display a single calling point."""

    def __init__(self, calling_point: CallingPoint, theme: str = "dark"):
        """
        Initialize calling point widget.

        Args:
            calling_point: Calling point data to display
            theme: Current theme ("dark" or "light")
        """
        super().__init__()
        self.calling_point = calling_point
        self.current_theme = theme
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        """Setup the calling point UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Station name
        station_label = QLabel(self.calling_point.station_name)
        station_font = QFont()
        station_font.setPointSize(11)
        if self.calling_point.is_origin or self.calling_point.is_destination:
            station_font.setBold(True)
        station_label.setFont(station_font)
        layout.addWidget(station_label)

        layout.addStretch()

        # Time
        time_text = self.calling_point.get_display_time()
        if time_text:
            time_label = QLabel(time_text)
            time_font = QFont()
            time_font.setPointSize(11)
            time_font.setFamily("monospace")
            time_label.setFont(time_font)
            layout.addWidget(time_label)

        # Platform if available
        if self.calling_point.platform:
            platform_label = QLabel(f"Plat {self.calling_point.platform}")
            platform_font = QFont()
            platform_font.setPointSize(9)
            platform_label.setFont(platform_font)
            layout.addWidget(platform_label)

    def apply_theme(self):
        """Apply theme styling."""
        if self.current_theme == "dark":
            if self.calling_point.is_origin:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #2d4a2d;
                        border-left: 3px solid #4caf50;
                        border-radius: 4px;
                        margin: 1px;
                    }
                    QLabel { color: #ffffff; }
                """)
            elif self.calling_point.is_destination:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #4a2d2d;
                        border-left: 3px solid #f44336;
                        border-radius: 4px;
                        margin: 1px;
                    }
                    QLabel { color: #ffffff; }
                """)
            else:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #2d2d2d;
                        border-left: 3px solid #666666;
                        border-radius: 4px;
                        margin: 1px;
                    }
                    QLabel { color: #cccccc; }
                """)
        else:
            if self.calling_point.is_origin:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #e8f5e8;
                        border-left: 3px solid #388e3c;
                        border-radius: 4px;
                        margin: 1px;
                    }
                    QLabel { color: #212121; }
                """)
            elif self.calling_point.is_destination:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #fde8e8;
                        border-left: 3px solid #d32f2f;
                        border-radius: 4px;
                        margin: 1px;
                    }
                    QLabel { color: #212121; }
                """)
            else:
                self.setStyleSheet("""
                    QFrame {
                        background-color: #f5f5f5;
                        border-left: 3px solid #9e9e9e;
                        border-radius: 4px;
                        margin: 1px;
                    }
                    QLabel { color: #424242; }
                """)


class TrainDetailDialog(QDialog):
    """Dialog showing detailed train information including all calling points."""

    def __init__(self, train_data: TrainData, theme: str = "dark", parent=None):
        """
        Initialize train detail dialog.

        Args:
            train_data: Train data to display
            theme: Current theme ("dark" or "light")
            parent: Parent widget
        """
        super().__init__(parent)
        self.train_data = train_data
        self.current_theme = theme
        
        self.setWindowTitle(f"Train Details - {train_data.destination}")
        self.setModal(True)
        self.resize(500, 600)
        
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header with train summary
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        
        # Main train info
        main_info = QLabel(
            f"{self.train_data.get_service_icon()} {self.train_data.format_departure_time()} → {self.train_data.destination}"
        )
        main_font = QFont()
        main_font.setPointSize(16)
        main_font.setBold(True)
        main_info.setFont(main_font)
        header_layout.addWidget(main_info)

        # Service details
        service_info = QLabel(
            f"{self.train_data.operator} • {self.train_data.service_type.value.title()} • Platform {self.train_data.platform or 'TBA'}"
        )
        service_font = QFont()
        service_font.setPointSize(12)
        service_info.setFont(service_font)
        header_layout.addWidget(service_info)

        # Status
        status_info = QLabel(
            f"{self.train_data.get_status_icon()} {self.train_data.format_delay()}"
        )
        status_font = QFont()
        status_font.setPointSize(12)
        status_font.setBold(True)
        status_info.setFont(status_font)
        status_color = self.train_data.get_status_color(self.current_theme)
        status_info.setStyleSheet(f"color: {status_color};")
        header_layout.addWidget(status_info)

        layout.addWidget(header_frame)

        # Calling points section
        calling_points_label = QLabel("Calling Points:")
        calling_points_font = QFont()
        calling_points_font.setPointSize(14)
        calling_points_font.setBold(True)
        calling_points_label.setFont(calling_points_font)
        layout.addWidget(calling_points_label)

        # Scrollable calling points list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        calling_points_widget = QWidget()
        calling_points_layout = QVBoxLayout(calling_points_widget)
        calling_points_layout.setSpacing(2)

        # Add calling point widgets
        for calling_point in self.train_data.calling_points:
            cp_widget = CallingPointWidget(calling_point, self.current_theme)
            calling_points_layout.addWidget(cp_widget)

        calling_points_layout.addStretch()
        scroll_area.setWidget(calling_points_widget)
        layout.addWidget(scroll_area)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def apply_theme(self):
        """Apply theme styling to the dialog."""
        if self.current_theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    border-radius: 8px;
                    padding: 8px;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #4fc3f7;
                    color: #000000;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #29b6f6;
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
                QFrame {
                    background-color: #f5f5f5;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 8px;
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