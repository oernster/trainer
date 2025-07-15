"""
UI Managers Package

This package contains manager classes that handle different aspects
of the main window functionality in a modular, object-oriented way.
"""

from .ui_layout_manager import UILayoutManager
from .widget_lifecycle_manager import WidgetLifecycleManager
from .event_handler_manager import EventHandlerManager
from .settings_dialog_manager import SettingsDialogManager

__all__ = [
    'UILayoutManager',
    'WidgetLifecycleManager', 
    'EventHandlerManager',
    'SettingsDialogManager'
]