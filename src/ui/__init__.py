"""
User interface components for the Train Times application.

This module contains all the UI components including the main window,
train display widgets, and theme styling.
"""

from .main_window import MainWindow
from .widgets.train_list_widget import TrainListWidget
from .widgets.train_item_widget import TrainItemWidget

__all__ = ["MainWindow", "TrainListWidget", "TrainItemWidget"]
