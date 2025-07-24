"""
Service Factory

Factory for creating and managing core service instances.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from ..interfaces.i_data_repository import IDataRepository
from ..interfaces.i_station_service import IStationService
from ..interfaces.i_route_service import IRouteService

from .json_data_repository import JsonDataRepository
from .station_service import StationService
from .route_service_refactored import RouteServiceRefactored


class ServiceFactory:
    """Factory for creating and managing core service instances."""
    
    def __init__(self, data_directory: Optional[str] = None):
        """
        Initialize the service factory.
        
        Args:
            data_directory: Path to data directory, defaults to src/data
        """
        self.logger = logging.getLogger(__name__)
        
        # Set default data directory
        if data_directory is None:
            # Try to use data path resolver
            try:
                from ...utils.data_path_resolver import get_data_directory
                data_directory = str(get_data_directory())
            except (ImportError, FileNotFoundError):
                # Fallback to old method
                data_directory = str(Path(__file__).parent.parent.parent / "data")
        
        self.data_directory = data_directory
        
        # Service instances (singletons)
        self._data_repository: Optional[IDataRepository] = None
        self._station_service: Optional[IStationService] = None
        self._route_service: Optional[IRouteService] = None
        
        self.logger.info(f"Initialized ServiceFactory with data directory: {data_directory}")
    
    def get_data_repository(self) -> IDataRepository:
        """Get or create the data repository instance."""
        if self._data_repository is None:
            self._data_repository = JsonDataRepository(self.data_directory)
            self.logger.info("Created JsonDataRepository instance")
        
        return self._data_repository
    
    def get_station_service(self) -> IStationService:
        """Get or create the station service instance."""
        if self._station_service is None:
            data_repo = self.get_data_repository()
            self._station_service = StationService(data_repo)
            self.logger.info("Created StationService instance")
        
        return self._station_service
    
    def get_route_service(self) -> IRouteService:
        """Get or create the route service instance."""
        if self._route_service is None:
            data_repo = self.get_data_repository()
            self._route_service = RouteServiceRefactored(data_repo)
            self.logger.info("Created RouteServiceRefactored instance")
        
        return self._route_service
    
    def refresh_all_services(self) -> bool:
        """Refresh all service instances by clearing caches and reloading data."""
        try:
            # Refresh data repository
            if self._data_repository:
                success = self._data_repository.refresh_data()
                if not success:
                    self.logger.error("Failed to refresh data repository")
                    return False
            
            # Clear station service cache
            if self._station_service and hasattr(self._station_service, 'clear_cache'):
                self._station_service.clear_cache()
            
            # Clear route service cache
            if self._route_service and hasattr(self._route_service, 'clear_route_cache'):
                self._route_service.clear_route_cache()
            
            self.logger.info("All services refreshed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to refresh services: {e}")
            return False
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get statistics from all services."""
        stats = {}
        
        try:
            # Data repository stats
            if self._data_repository:
                stats['data_repository'] = self._data_repository.get_network_statistics()
            
            # Station service stats
            if self._station_service and hasattr(self._station_service, 'get_station_statistics'):
                stats['station_service'] = self._station_service.get_station_statistics()
            
            # Route service stats
            if self._route_service:
                stats['route_service'] = self._route_service.get_route_statistics()
            
        except Exception as e:
            self.logger.error(f"Failed to get service statistics: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def precompute_common_routes(self, station_pairs: Optional[List[Tuple[str, str]]] = None) -> None:
        """Precompute routes for common station pairs."""
        if station_pairs is None:
            # Default common routes
            station_pairs = [
                ("London Waterloo", "Woking"),
                ("London Waterloo", "Guildford"),
                ("London Waterloo", "Portsmouth Harbour"),
                ("London Waterloo", "Southampton Central"),
                ("Clapham Junction", "Woking"),
                ("Woking", "Guildford"),
                ("London Victoria", "Brighton"),
                ("London Bridge", "East Croydon"),
                ("London Paddington", "Reading"),
                ("London King's Cross", "Cambridge")
            ]
        
        route_service = self.get_route_service()
        route_service.precompute_common_routes(station_pairs)
    
    def validate_services(self) -> Dict[str, bool]:
        """Validate that all services are working correctly."""
        validation_results = {}
        
        try:
            # Test data repository
            data_repo = self.get_data_repository()
            test_stations = data_repo.load_stations()
            validation_results['data_repository'] = len(test_stations) > 0
            
            # Test station service
            station_service = self.get_station_service()
            test_suggestions = station_service.get_station_suggestions("London", limit=5)
            validation_results['station_service'] = len(test_suggestions) > 0
            
            # Test route service
            route_service = self.get_route_service()
            test_route = route_service.calculate_route("London Waterloo", "Woking")
            validation_results['route_service'] = test_route is not None
            
        except Exception as e:
            self.logger.error(f"Service validation failed: {e}")
            validation_results['error'] = str(e)
        
        return validation_results
    
    def shutdown(self) -> None:
        """Shutdown all services and clean up resources."""
        try:
            # Clear all caches
            if self._station_service and hasattr(self._station_service, 'clear_cache'):
                self._station_service.clear_cache()
            
            if self._route_service and hasattr(self._route_service, 'clear_route_cache'):
                self._route_service.clear_route_cache()
            
            # Reset instances
            self._data_repository = None
            self._station_service = None
            self._route_service = None
            
            self.logger.info("All services shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error during service shutdown: {e}")


# Global service factory instance
_service_factory: Optional[ServiceFactory] = None


def get_service_factory(data_directory: Optional[str] = None) -> ServiceFactory:
    """Get the global service factory instance."""
    global _service_factory
    
    if _service_factory is None:
        _service_factory = ServiceFactory(data_directory)
    
    return _service_factory


def get_data_repository() -> IDataRepository:
    """Get the data repository service."""
    return get_service_factory().get_data_repository()


def get_station_service() -> IStationService:
    """Get the station service."""
    return get_service_factory().get_station_service()


def get_route_service() -> IRouteService:
    """Get the route service."""
    return get_service_factory().get_route_service()


def refresh_all_services() -> bool:
    """Refresh all services."""
    return get_service_factory().refresh_all_services()


def validate_services() -> Dict[str, bool]:
    """Validate all services."""
    return get_service_factory().validate_services()


def shutdown_services() -> None:
    """Shutdown all services."""
    global _service_factory
    
    if _service_factory:
        _service_factory.shutdown()
        _service_factory = None