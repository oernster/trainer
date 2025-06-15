"""
Data models for the Train Times application.

This module contains all the data structures used throughout the application,
including train data, configuration data, and enums.
"""

from .train_data import TrainData, TrainStatus, ServiceType

__all__ = ["TrainData", "TrainStatus", "ServiceType"]
