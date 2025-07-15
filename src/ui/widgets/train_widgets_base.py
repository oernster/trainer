"""
Base classes and interfaces for train widgets.

This module provides common base classes and interfaces that all train widgets
can inherit from to ensure consistent behavior and theming support.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class BaseTrainWidget(QWidget):
    """
    Base class for all train-related widgets.
    
    Provides common functionality including theme support, logging,
    and standardized initialization patterns.
    """
    
    # Common signals that train widgets might emit
    theme_changed = Signal(str)  # Theme name
    error_occurred = Signal(str)  # Error message
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize base train widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_theme = "dark"
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_base_properties()
    
    def _setup_base_properties(self) -> None:
        """Setup common widget properties."""
        # Set object name for easier debugging and styling
        self.setObjectName(self.__class__.__name__)
    
    def apply_theme(self, theme: str = "dark") -> None:
        """
        Apply theme styling to the widget.
        
        Args:
            theme: Theme name ("dark" or "light")
        """
        if theme != self.current_theme:
            self.current_theme = theme
            self._apply_theme_styles()
            self.theme_changed.emit(theme)
    
    def update_theme(self, theme: str) -> None:
        """
        Update widget theme and refresh styling.
        
        Args:
            theme: New theme name ("dark" or "light")
        """
        self.apply_theme(theme)
    
    def _apply_theme_styles(self) -> None:
        """
        Apply theme-specific styles to the widget.
        
        This method should be implemented by subclasses to define
        their specific theme styling logic.
        """
        pass
    
    def get_theme_colors(self, theme: str) -> Dict[str, str]:
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
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """
        Log an error and emit error signal.
        
        Args:
            message: Error message
            exception: Optional exception object
        """
        if exception:
            self.logger.error(f"{message}: {exception}", exc_info=True)
        else:
            self.logger.error(message)
        self.error_occurred.emit(message)
    
    def log_info(self, message: str) -> None:
        """
        Log an info message.
        
        Args:
            message: Info message
        """
        self.logger.info(message)
    
    def log_debug(self, message: str) -> None:
        """
        Log a debug message.
        
        Args:
            message: Debug message
        """
        self.logger.debug(message)