"""
Core Interfaces Package

Interface definitions for the railway application services.
"""

from .i_station_service import IStationService
from .i_route_service import IRouteService
from .i_data_repository import IDataRepository

__all__ = [
    'IStationService',
    'IRouteService',
    'IDataRepository'
]