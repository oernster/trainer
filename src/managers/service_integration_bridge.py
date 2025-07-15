"""
Service Integration Bridge

Bridge between new core services and existing managers for backward compatibility.
"""

import logging
import time
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

# Import core services
from src.core import (
    get_station_service, get_route_service, get_data_repository,
    validate_services, refresh_all_services
)

# Import existing manager for fallback
from .station_database_manager import StationDatabaseManager


class ServiceIntegrationBridge:
    """
    Bridge that integrates new core services with existing manager interfaces.
    
    This provides backward compatibility while gradually migrating to the new architecture.
    """
    
    def __init__(self):
        """Initialize the service integration bridge."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize core services
        try:
            self.station_service = get_station_service()
            self.route_service = get_route_service()
            self.data_repository = get_data_repository()
            
            # Validate services are working
            validation_results = validate_services()
            if not all(validation_results.values()):
                self.logger.warning(f"Service validation issues: {validation_results}")
            
            self.core_services_available = True
            self.logger.info("Core services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            self.core_services_available = False
        
        # Fallback to existing manager
        self.fallback_manager = StationDatabaseManager()
        self.fallback_loaded = False
        
        self.logger.info("ServiceIntegrationBridge initialized")
    
    def _ensure_fallback_loaded(self) -> bool:
        """Ensure fallback manager is loaded."""
        if not self.fallback_loaded:
            try:
                self.fallback_loaded = self.fallback_manager.load_database()
                if not self.fallback_loaded:
                    self.logger.error("Failed to load fallback database manager")
            except Exception as e:
                self.logger.error(f"Error loading fallback manager: {e}")
                self.fallback_loaded = False
        
        return self.fallback_loaded
    
    def search_stations(self, query: str, limit: int = 10) -> List[str]:
        """Search for stations matching the query."""
        if self.core_services_available:
            try:
                # Use new core service
                suggestions = self.station_service.get_station_suggestions(query, limit)
                self.logger.debug(f"Core service returned {len(suggestions)} suggestions for '{query}'")
                return suggestions
                
            except Exception as e:
                self.logger.warning(f"Core service search failed: {e}, falling back to legacy")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.search_stations(query, limit)
        
        return []
    
    def get_station_by_name(self, station_name: str):
        """Get station object by name."""
        if self.core_services_available:
            try:
                # Use new core service
                station = self.station_service.get_station_by_name(station_name)
                if station:
                    return station
                    
            except Exception as e:
                self.logger.warning(f"Core service station lookup failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.get_station_by_name(station_name)
        
        return None
    
    def validate_station_exists(self, station_name: str) -> bool:
        """Validate that a station exists."""
        if self.core_services_available:
            try:
                return self.station_service.validate_station_exists(station_name)
            except Exception as e:
                self.logger.warning(f"Core service validation failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            station = self.fallback_manager.get_station_by_name(station_name)
            return station is not None
        
        return False
    
    def resolve_station_name(self, input_name: str, strict: bool = False) -> Optional[str]:
        """Resolve a station name from user input."""
        if self.core_services_available:
            try:
                return self.station_service.resolve_station_name(input_name, strict)
            except Exception as e:
                self.logger.warning(f"Core service name resolution failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            parsed_name = self.fallback_manager.parse_station_name(input_name)
            if self.fallback_manager.get_station_by_name(parsed_name):
                return parsed_name
        
        return None
    
    def find_route_between_stations(self, from_station: str, to_station: str,
                                   max_changes: int = 3, departure_time: Optional[str] = None) -> List[List[str]]:
        """Find routes between stations."""
        if self.core_services_available:
            try:
                # Use new core service
                routes = self.route_service.calculate_multiple_routes(
                    from_station, to_station, max_routes=5, max_changes=max_changes
                )
                
                # Convert Route objects to station name lists
                route_lists = []
                for route in routes:
                    # Build station list from route segments
                    station_list = [route.from_station]
                    for segment in route.segments:
                        if segment.to_station != station_list[-1]:
                            station_list.append(segment.to_station)
                    route_lists.append(station_list)
                
                if route_lists:
                    self.logger.debug(f"Core service found {len(route_lists)} routes")
                    return route_lists
                    
            except Exception as e:
                self.logger.warning(f"Core service routing failed: {e}, falling back to legacy")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.find_route_between_stations(
                from_station, to_station, max_changes, departure_time
            )
        
        return []
    
    def get_railway_lines_for_station(self, station_name: str) -> List[str]:
        """Get all railway lines that serve a given station."""
        if self.core_services_available:
            try:
                return self.station_service.get_railway_lines_for_station(station_name)
            except Exception as e:
                self.logger.warning(f"Core service line lookup failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.get_railway_lines_for_station(station_name)
        
        return []
    
    def suggest_via_stations(self, from_station: str, to_station: str, limit: int = 10) -> List[str]:
        """Suggest via stations for a route."""
        if self.core_services_available:
            try:
                # Use route service to find interchange stations
                interchanges = self.route_service.get_interchange_stations(from_station, to_station)
                return interchanges[:limit]
            except Exception as e:
                self.logger.warning(f"Core service via station suggestion failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.suggest_via_stations(from_station, to_station, limit)
        
        return []
    
    def identify_train_changes(self, route: List[str]) -> List[str]:
        """Identify stations where train changes are required."""
        if self.core_services_available and len(route) >= 2:
            try:
                # Use route service to validate and analyze route
                from_station = route[0]
                to_station = route[-1]
                
                calculated_route = self.route_service.calculate_route(from_station, to_station)
                if calculated_route:
                    return calculated_route.interchange_stations
                    
            except Exception as e:
                self.logger.warning(f"Core service change identification failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.identify_train_changes(route)
        
        return []
    
    def get_operator_for_segment(self, from_station: str, to_station: str) -> Optional[str]:
        """Get operator for a segment between two stations."""
        if self.core_services_available:
            try:
                # Find common lines and get operator from first line
                common_lines = self.station_service.find_common_lines(from_station, to_station)
                if common_lines:
                    line = self.data_repository.get_railway_line_by_name(common_lines[0])
                    if line:
                        return line.operator
                        
            except Exception as e:
                self.logger.warning(f"Core service operator lookup failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.get_operator_for_segment(from_station, to_station)
        
        return None
    
    def get_all_stations_with_context(self) -> List[str]:
        """Get all stations with disambiguation context where needed."""
        if self.core_services_available:
            try:
                # Use station service to get all stations
                all_stations = self.station_service.get_all_station_names()
                
                # Add context for stations that might need disambiguation
                stations_with_context = []
                for station_name in all_stations:
                    lines = self.station_service.get_railway_lines_for_station(station_name)
                    if len(lines) > 1:
                        # Add primary line context for disambiguation
                        primary_line = lines[0]
                        disambiguated_name = f"{station_name} ({primary_line})"
                        stations_with_context.append(disambiguated_name)
                    else:
                        stations_with_context.append(station_name)
                
                return sorted(stations_with_context)
                
            except Exception as e:
                self.logger.warning(f"Core service station listing failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.get_all_stations_with_context()
        
        return []
    
    def parse_station_name(self, station_name: str) -> str:
        """Parse station name to remove disambiguation context."""
        if self.core_services_available:
            try:
                # Use station service normalization if available
                try:
                    if hasattr(self.station_service, 'normalize_station_name'):
                        normalize_method = getattr(self.station_service, 'normalize_station_name')
                        return normalize_method(station_name)
                except (AttributeError, TypeError):
                    pass
                
                # Basic normalization fallback
                return station_name.strip()
            except Exception as e:
                self.logger.warning(f"Core service name parsing failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.parse_station_name(station_name)
        
        return station_name.strip()
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        if self.core_services_available:
            try:
                # Use core services for statistics
                stats = self.data_repository.get_network_statistics()
                return {
                    'total_stations': stats.get('total_stations', 0),
                    'total_lines': stats.get('total_lines', 0),
                    'lines_with_service_patterns': 0  # Not tracked in new system yet
                }
            except Exception as e:
                self.logger.warning(f"Core service stats failed: {e}")
        
        # Fallback to existing manager
        if self._ensure_fallback_loaded():
            return self.fallback_manager.get_database_stats()
        
        return {'total_stations': 0, 'total_lines': 0, 'lines_with_service_patterns': 0}
    
    def refresh_data(self) -> bool:
        """Refresh all data sources."""
        success = True
        
        if self.core_services_available:
            try:
                success = refresh_all_services()
                if not success:
                    self.logger.warning("Core services refresh failed")
            except Exception as e:
                self.logger.error(f"Core services refresh error: {e}")
                success = False
        
        # Also refresh fallback manager
        if self._ensure_fallback_loaded():
            try:
                self.fallback_loaded = self.fallback_manager.load_database()
                success = success and self.fallback_loaded
            except Exception as e:
                self.logger.error(f"Fallback manager refresh error: {e}")
                success = False
        
        return success
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        status = {
            'core_services_available': self.core_services_available,
            'fallback_manager_loaded': self.fallback_loaded,
            'timestamp': str(time.time())
        }
        
        if self.core_services_available:
            try:
                validation_results = validate_services()
                status['core_service_validation'] = validation_results
            except Exception as e:
                status['core_service_error'] = str(e)
        
        return status


# Global bridge instance
_service_bridge: Optional[ServiceIntegrationBridge] = None


def get_service_bridge() -> ServiceIntegrationBridge:
    """Get the global service integration bridge instance."""
    global _service_bridge
    
    if _service_bridge is None:
        _service_bridge = ServiceIntegrationBridge()
    
    return _service_bridge


def refresh_service_bridge() -> bool:
    """Refresh the service bridge and all underlying services."""
    bridge = get_service_bridge()
    return bridge.refresh_data()