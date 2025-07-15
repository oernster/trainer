"""
Core Services Package

Service implementations for the railway application.
"""

from .json_data_repository import JsonDataRepository
from .station_service import StationService
from .route_service import RouteService
from .service_factory import (
    ServiceFactory,
    get_service_factory,
    get_data_repository,
    get_station_service,
    get_route_service,
    refresh_all_services,
    validate_services,
    shutdown_services
)

__all__ = [
    'JsonDataRepository',
    'StationService',
    'RouteService',
    'ServiceFactory',
    'get_service_factory',
    'get_data_repository',
    'get_station_service',
    'get_route_service',
    'refresh_all_services',
    'validate_services',
    'shutdown_services'
]