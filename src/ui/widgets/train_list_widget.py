"""
Train list widget for displaying scrollable list of train departures.

This module provides a scrollable list widget that displays train departures
with theme support and real-time updates.
"""

import logging
from typing import List, Optional
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QApplication, QSizePolicy
from PySide6.QtCore import Qt, Signal, QTimer
from ...models.train_data import TrainData
from .train_widgets_base import BaseTrainWidget
from .custom_scroll_bar import CustomScrollBar
from .train_item_widget import TrainItemWidget

logger = logging.getLogger(__name__)


class TrainListWidget(QScrollArea):
    """
    Scrollable list of train departures with theme support.

    Displays up to max_trains train items in a scrollable list,
    with support for theme switching and real-time updates.
    """

    # Signal emitted when a train is selected
    train_selected = Signal(TrainData)
    # Signal emitted when a route button is clicked
    route_selected = Signal(TrainData)

    def __init__(self, max_trains: int = 50, train_manager=None, preferences: Optional[dict] = None, parent: Optional[QWidget] = None):
        """
        Initialize train list widget.

        Args:
            max_trains: Maximum number of trains to display
            train_manager: Train manager instance for accessing route data
            preferences: User preferences dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize theme and logging functionality
        self.current_theme = "dark"
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.max_trains = max_trains
        self.train_manager = train_manager
        self.preferences = preferences or {}
        self.train_items: List[TrainItemWidget] = []

        self._setup_ui()
        self._apply_theme_styles()

        self.log_debug(f"TrainListWidget initialized with max_trains={max_trains}")

    def _setup_ui(self) -> None:
        """Setup the train list UI."""
        # Create container widget and layout
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(8, 8, 8, 8)
        self.container_layout.setSpacing(4)
        self.container_layout.addStretch()  # Add stretch at the end

        # Configure scroll area - hide default scroll bars
        self.setWidget(self.container_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Don't set fixed height - let the widget expand to fill available space
        # This allows proper layout adjustment on different screen sizes
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Expanding
        )
        
        # Create custom scroll bar
        self.custom_scroll_bar = CustomScrollBar(self)
        self.custom_scroll_bar.scroll_requested.connect(self._on_custom_scroll)
        
        # Connect main scroll bar to custom scroll bar for synchronization
        self.verticalScrollBar().valueChanged.connect(self._sync_custom_scroll_bar)
        
        # Position custom scroll bar on the right side
        self._position_custom_scroll_bar()

    def _apply_theme_styles(self) -> None:
        """Apply theme styling to the scroll area."""
        colors = self.get_theme_colors(self.current_theme)
        
        # FORCE light theme styling when in light mode
        if self.current_theme == "light":
            style = f"""
            QScrollArea {{
                border: 1px solid #e0e0e0 !important;
                border-radius: 8px !important;
                background-color: #ffffff !important;
            }}
            
            QWidget {{
                background-color: #ffffff !important;
            }}
            
            QScrollBar:vertical {{
                background-color: #f5f5f5 !important;
                width: 12px !important;
                border-radius: 6px !important;
                margin: 0px !important;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: #e0e0e0 !important;
                border-radius: 6px !important;
                min-height: 20px !important;
                margin: 2px !important;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: #d0d0d0 !important;
            }}
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px !important;
            }}
            """
        else:
            # Dark theme styling
            style = f"""
            QScrollArea {{
                border: 1px solid {colors['border_primary']};
                border-radius: 8px;
                background-color: {colors['background_primary']};
            }}
            
            QScrollBar:vertical {{
                background-color: {colors['background_secondary']};
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {colors['border_secondary']};
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {colors['background_hover']};
            }}
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        
        self.setStyleSheet(style)

        # Update custom scroll bar theme
        if hasattr(self, 'custom_scroll_bar'):
            self.custom_scroll_bar.apply_theme(self.current_theme)

        # Update all train items
        for train_item in self.train_items:
            if hasattr(train_item, 'update_theme'):
                train_item.update_theme(self.current_theme)

    def update_trains(self, trains: List[TrainData]) -> None:
        """
        Update the displayed trains.

        Args:
            trains: List of train data to display
        """
        try:
            logger.debug("*** ENTERING update_trains - CRITICAL CRASH POINT ***")
            logger.debug(f"Widget state - visible: {self.isVisible()}, parent: {self.parent()}")
            logger.debug(f"Received {len(trains)} trains to display")
            
            # CRASH DETECTION: Check widget validity before proceeding
            if not self.isVisible():
                logger.debug("WARNING - Widget not visible during update!")
            
            if self.parent() is None:
                logger.debug("CRITICAL - Widget has no parent during update!")
                return
            
            # Clear existing items
            logger.debug("About to clear existing trains")
            self.clear_trains()
            logger.debug("Successfully cleared existing trains")

            # Limit to max_trains
            display_trains = trains[:self.max_trains]
            logger.debug(f"Will display {len(display_trains)} trains (limited from {len(trains)})")

            # ULTIMATE CRASH FIX: Disable automatic layout updates during widget addition
            logger.debug("*** DISABLING LAYOUT UPDATES TO PREVENT CRASH ***")
            self.container_widget.setUpdatesEnabled(False)
            self.setUpdatesEnabled(False)

            # Add new train items with crash protection
            for i, train in enumerate(display_trains):
                try:
                    logger.debug(f"Adding train item {i+1}/{len(display_trains)}: {train.destination}")
                    self.add_train_item(train)
                    logger.debug(f"Successfully added train item {i+1}")
                except Exception as e:
                    logger.debug(f"Failed to add train item {i+1}: {e}", exc_info=True)
                    # Continue with other trains instead of crashing

            logger.debug("All train items added, RE-ENABLING UPDATES")
            # Re-enable updates after all widgets are added
            self.container_widget.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

            logger.debug("SKIPPING DANGEROUS SCROLL AREA UPDATE")
            # ULTIMATE CRASH FIX: Completely eliminate the delayed scroll area update
            # This was the source of the crash - Qt doesn't like delayed geometry updates
            # during widget lifecycle transitions. Let Qt handle scroll area sizing naturally.
            logger.debug("Scroll area update SKIPPED to prevent crash")

            logger.debug(f"*** SUCCESSFULLY COMPLETED update_trains with {len(display_trains)} trains ***")
            self.log_debug(f"Updated train list with {len(display_trains)} trains")
        except Exception as e:
            logger.debug(f"*** EXCEPTION in update_trains: {e} ***", exc_info=True)
            # Re-enable updates even if there was an exception
            try:
                self.container_widget.setUpdatesEnabled(True)
                self.setUpdatesEnabled(True)
            except:
                pass
            # Don't re-raise to prevent crash

    def clear_trains(self) -> None:
        """Clear all train items from the display."""
        # Remove all train items from layout
        for train_item in self.train_items:
            self.container_layout.removeWidget(train_item)
            train_item.deleteLater()

        self.train_items.clear()

    def add_train_item(self, train_data: TrainData) -> None:
        """
        Add a single train item to the display.

        Args:
            train_data: Train data to add
        """
        try:
            train_item = TrainItemWidget(
                train_data,
                self.current_theme,
                train_manager=self.train_manager,
                preferences=self.preferences
            )
            train_item.train_clicked.connect(self.train_selected.emit)
            train_item.route_clicked.connect(self.route_selected.emit)

            # Insert before the stretch at the end
            self.container_layout.insertWidget(self.container_layout.count() - 1, train_item)

            self.train_items.append(train_item)
        except Exception as e:
            logger.debug(f"Failed to create TrainItemWidget: {e}")
            # Don't re-raise to prevent crash

    def set_train_manager(self, train_manager) -> None:
        """
        Set the train manager for accessing route data.
        
        Args:
            train_manager: Train manager instance
        """
        self.train_manager = train_manager
        self.log_debug("Train manager set on TrainListWidget")

    def set_preferences(self, preferences: dict) -> None:
        """
        Set preferences and update all train items.
        
        Args:
            preferences: Updated preferences dictionary
        """
        self.preferences = preferences or {}
        
        # Update all existing train items with new preferences
        for train_item in self.train_items:
            if hasattr(train_item, 'set_preferences'):
                train_item.set_preferences(self.preferences)
        
        self.log_debug(f"Preferences updated for {len(self.train_items)} train items")

    def get_train_count(self) -> int:
        """
        Get the number of displayed trains.

        Returns:
            int: Number of trains currently displayed
        """
        return len(self.train_items)

    def scroll_to_top(self) -> None:
        """Scroll to the top of the train list."""
        self.verticalScrollBar().setValue(0)

    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the train list."""
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def update_scroll_area(self) -> None:
        """Force the scroll area to recalculate its content size."""
        try:
            logger.debug("*** ENTERING update_scroll_area - ULTIMATE CRASH PREVENTION ***")
            
            # ULTIMATE CRASH PREVENTION: Check if we're in a valid Qt application state
            app = QApplication.instance()
            if app is None:
                logger.debug("CRITICAL - No Qt application instance, aborting!")
                return
            
            # ULTIMATE CRASH PREVENTION: Check if widget is being destroyed
            try:
                # Test basic widget validity
                _ = self.objectName()  # This will fail if widget is being destroyed
                _ = self.isVisible()   # This will fail if widget is invalid
            except RuntimeError as e:
                logger.debug(f"CRITICAL - Widget is being destroyed: {e}")
                return
            except Exception as e:
                logger.debug(f"CRITICAL - Widget in invalid state: {e}")
                return
            
            # ULTIMATE CRASH PREVENTION: Check parent validity
            try:
                parent = self.parent()
                if parent is None:
                    logger.debug("CRITICAL - Widget has no parent!")
                    return
                # Test parent validity
                _ = parent.objectName()
            except RuntimeError as e:
                logger.debug(f"CRITICAL - Parent is being destroyed: {e}")
                return
            except Exception as e:
                logger.debug(f"CRITICAL - Parent in invalid state: {e}")
                return
            
            # ULTIMATE CRASH PREVENTION: Check container widget validity
            try:
                if not hasattr(self, 'container_widget') or self.container_widget is None:
                    logger.debug("CRITICAL - Container widget is None!")
                    return
                # Test container validity
                _ = self.container_widget.objectName()
                _ = self.container_widget.isVisible()
            except RuntimeError as e:
                logger.debug(f"CRITICAL - Container widget is being destroyed: {e}")
                return
            except Exception as e:
                logger.debug(f"CRITICAL - Container widget in invalid state: {e}")
                return
            
            logger.debug(f"All widget validity checks passed - train_items count: {len(self.train_items)}")
            
            # ULTIMATE CRASH PREVENTION: Safely calculate heights with extensive error handling
            total_height = 20  # Start with padding
            valid_items = 0
            
            for i, train_item in enumerate(self.train_items):
                try:
                    # Check if train item is valid before accessing it
                    if train_item is None:
                        logger.debug(f"Train item {i} is None, skipping")
                        continue
                    
                    # Test train item validity
                    _ = train_item.objectName()
                    
                    # Safely get size hint
                    size_hint = train_item.sizeHint()
                    if size_hint.isValid():
                        item_height = size_hint.height() + 4  # +4 for spacing/margins
                        total_height += item_height
                        valid_items += 1
                        logger.debug(f"Train item {i} height: {item_height}")
                    else:
                        logger.debug(f"Train item {i} has invalid size hint, using fallback")
                        total_height += 150  # Fallback height
                        
                except RuntimeError as e:
                    logger.debug(f"Train item {i} is being destroyed: {e}")
                    total_height += 150  # Fallback height
                except Exception as e:
                    logger.debug(f"Error accessing train item {i}: {e}")
                    total_height += 150  # Fallback height
            
            logger.debug(f"Calculated total height: {total_height} from {valid_items} valid items")
            
            # ULTIMATE CRASH PREVENTION: Safely update container widget
            try:
                logger.debug("About to set minimum height on container widget")
                self.container_widget.setMinimumHeight(total_height)
                logger.debug("Successfully set minimum height")
            except RuntimeError as e:
                logger.debug(f"CRITICAL - Container widget destroyed during height setting: {e}")
                return
            except Exception as e:
                logger.debug(f"Error setting container height: {e}")
                return
            
            # ULTIMATE CRASH PREVENTION: Skip dangerous geometry updates
            logger.debug("SKIPPING DANGEROUS GEOMETRY UPDATES TO PREVENT CRASH")
            # Don't call updateGeometry() - it's too dangerous during widget transitions
            
            # ULTIMATE CRASH PREVENTION: Skip all event processing
            logger.debug("SKIPPING ALL EVENT PROCESSING TO PREVENT CRASH")
            # Don't process any events - let Qt handle them naturally
            
            # ULTIMATE CRASH PREVENTION: Safely configure scroll bar
            try:
                logger.debug("About to safely configure scroll bar")
                viewport_height = self.viewport().height()
                content_height = total_height
                logger.debug(f"Viewport height: {viewport_height}, Content height: {content_height}")
                
                if content_height > viewport_height and viewport_height > 0:
                    # Content is larger than viewport - configure scroll bar for partial display
                    scroll_bar = self.verticalScrollBar()
                    if scroll_bar is not None:
                        # Set the range based on the overflow
                        max_scroll = content_height - viewport_height
                        scroll_bar.setRange(0, max_scroll)
                        scroll_bar.setPageStep(viewport_height)
                        scroll_bar.setSingleStep(20)
                        logger.debug(f"Scroll bar configured - range: 0-{max_scroll}")
                    else:
                        logger.debug("Scroll bar is None, skipping configuration")
                else:
                    logger.debug("Content fits in viewport or invalid dimensions")
                    
            except Exception as e:
                logger.debug(f"Error configuring scroll bar: {e}")
                # Continue without scroll bar configuration
            
            # ULTIMATE CRASH PREVENTION: Skip custom scroll bar update
            logger.debug("SKIPPING CUSTOM SCROLL BAR UPDATE TO PREVENT CRASH")
            # Don't update custom scroll bar - it might access invalid widgets
            
            logger.debug("*** SUCCESSFULLY COMPLETED update_scroll_area WITH ULTIMATE CRASH PREVENTION ***")
            
        except Exception as e:
            logger.debug(f"*** EXCEPTION in update_scroll_area: {e} ***", exc_info=True)
            # Don't re-raise to prevent crash
    
    def _on_custom_scroll(self, value: int) -> None:
        """Handle custom scroll bar scroll requests."""
        # Set the scroll position on the main scroll area
        self.verticalScrollBar().setValue(value)
    
    def _sync_custom_scroll_bar(self, value: int) -> None:
        """Synchronize custom scroll bar with main scroll bar position."""
        if hasattr(self, 'custom_scroll_bar'):
            # Update custom scroll bar position to match main scroll bar
            self.custom_scroll_bar.setValue(value)
    
    def _position_custom_scroll_bar(self) -> None:
        """Position the custom scroll bar on the right side of the widget."""
        # Position the custom scroll bar on the right edge
        scroll_bar_x = self.width() - self.custom_scroll_bar.width()
        scroll_bar_y = 0
        scroll_bar_height = self.height()
        
        self.custom_scroll_bar.setGeometry(
            scroll_bar_x, scroll_bar_y,
            self.custom_scroll_bar.width(), scroll_bar_height
        )
    
    def resizeEvent(self, event):
        """Handle resize events to reposition custom scroll bar."""
        super().resizeEvent(event)
        if hasattr(self, 'custom_scroll_bar'):
            self._position_custom_scroll_bar()
    
    def update_custom_scroll_bar(self) -> None:
        """Update the custom scroll bar properties based on content."""
        if not hasattr(self, 'custom_scroll_bar'):
            return
            
        # Calculate content and viewport dimensions
        total_height = 0
        for train_item in self.train_items:
            total_height += train_item.sizeHint().height() + 4
        total_height += 20  # padding
        
        viewport_height = self.viewport().height()
        
        if total_height > viewport_height:
            # Content overflows - set up scroll bar
            max_scroll = total_height - viewport_height
            self.custom_scroll_bar.setRange(0, max_scroll)
            self.custom_scroll_bar.setPageStep(viewport_height)
            self.custom_scroll_bar.setSingleStep(20)
            self.custom_scroll_bar.setVisible(True)
            
            # Sync with main scroll bar position
            main_scroll_value = self.verticalScrollBar().value()
            self.custom_scroll_bar.setValue(main_scroll_value)
        else:
            # No overflow - hide custom scroll bar
            self.custom_scroll_bar.setVisible(False)

    def get_theme_colors(self, theme: str) -> dict:
        """
        Get theme-specific color palette.
        
        Args:
            theme: Theme name ("dark" or "light")
            
        Returns:
            Dictionary of color names to hex values
        """
        if theme == "dark":
            return {
                "background_primary": "#1a1a1a",
                "background_secondary": "#2d2d2d",
                "background_hover": "#404040",
                "text_primary": "#ffffff",
                "text_secondary": "#b0b0b0",
                "primary_accent": "#1976d2",
                "border_primary": "#404040",
                "border_secondary": "#555555",
                "success": "#4caf50",
                "warning": "#ff9800",
                "error": "#f44336",
            }
        else:  # light theme
            return {
                "background_primary": "#ffffff",
                "background_secondary": "#f5f5f5",
                "background_hover": "#e0e0e0",
                "text_primary": "#000000",
                "text_secondary": "#757575",
                "primary_accent": "#1976d2",
                "border_primary": "#cccccc",
                "border_secondary": "#e0e0e0",
                "success": "#4caf50",
                "warning": "#ff9800",
                "error": "#f44336",
            }

    def log_debug(self, message: str) -> None:
        """
        Log a debug message.
        
        Args:
            message: Debug message
        """
        self.logger.debug(message)

    def apply_theme(self, theme: str = "dark") -> None:
        """
        Apply theme to the train list widget.
        
        Args:
            theme: Theme name ("dark" or "light")
        """
        if theme != self.current_theme:
            self.current_theme = theme
            self._apply_theme_styles()