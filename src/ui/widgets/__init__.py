"""
UI Widgets package for the Train Times application.

This package contains specialized UI widgets extracted from the main train_widgets.py
file to improve maintainability and follow object-oriented design principles.
"""

from .train_widgets_base import BaseTrainWidget
from .custom_scroll_bar import CustomScrollBar
from .train_item_widget import TrainItemWidget
from .train_list_widget import TrainListWidget
from .route_display_dialog import RouteDisplayDialog
from .empty_state_widget import EmptyStateWidget

__all__ = [
    'BaseTrainWidget',
    'ThemeableWidget',
    'CustomScrollBar',
    'TrainItemWidget',
    'TrainListWidget',
    'RouteDisplayDialog',
    'EmptyStateWidget',
]