"""
Train widgets for displaying train information in the UI.

This module provides backward compatibility by importing and re-exporting
all train widget components from the new modular structure.

The widgets have been refactored into separate modules for better maintainability:
- CustomScrollBar: Custom scroll bar with theme support
- TrainItemWidget: Individual train information display
- TrainListWidget: Scrollable train list container
- RouteDisplayDialog: Complete journey details dialog
- EmptyStateWidget: Empty state display

All widgets support both dark and light themes and follow consistent design patterns.
"""

# Import all components from the new modular structure
from .widgets.custom_scroll_bar import CustomScrollBar
from .widgets.train_item_widget import TrainItemWidget
from .widgets.train_list_widget import TrainListWidget
from .widgets.route_display_dialog import RouteDisplayDialog
from .widgets.empty_state_widget import EmptyStateWidget

# Re-export all components for backward compatibility
__all__ = [
    'CustomScrollBar',
    'TrainItemWidget', 
    'TrainListWidget',
    'RouteDisplayDialog',
    'EmptyStateWidget'
]

# Legacy aliases for backward compatibility (if needed)
# These can be removed in future versions once all imports are updated
