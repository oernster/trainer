"""
Core Package

Core services, interfaces, and models for the railway application.
"""

# Import interfaces
from .interfaces import IStationService, IRouteService, IDataRepository

# Import models
from .models import Station, Route, RouteSegment, RailwayLine, LineType, LineStatus

# Import services
from .services import (
    JsonDataRepository, StationService, RouteService, ServiceFactory,
    get_service_factory, get_data_repository, get_station_service,
    get_route_service, refresh_all_services, validate_services, shutdown_services
)

__all__ = [
    # Interfaces
    'IStationService',
    'IRouteService',
    'IDataRepository',
    
    # Models
    'Station',
    'Route',
    'RouteSegment',
    'RailwayLine',
    'LineType',
    'LineStatus',
    
    # Services
    'JsonDataRepository',
    'StationService',
    'RouteService',
    'ServiceFactory',
    
    # Service Factory Functions
    'get_service_factory',
    'get_data_repository',
    'get_station_service',
    'get_route_service',
    'refresh_all_services',
    'validate_services',
    'shutdown_services'
]