"""
Geocoding service for converting city names to coordinates.
Author: Oliver Ernster

This module provides geocoding functionality using OpenStreetMap's Nominatim API.
"""

import logging
import asyncio
import aiohttp
from typing import Optional, Tuple
from urllib.parse import quote

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for converting city names to latitude/longitude coordinates."""
    
    def __init__(self):
        """Initialize the geocoding service."""
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.timeout = 10
        
    async def geocode_city(self, city_name: str) -> Optional[Tuple[float, float]]:
        """
        Convert a city name to latitude/longitude coordinates.
        
        Args:
            city_name: Name of the city to geocode
            
        Returns:
            Tuple of (latitude, longitude) if successful, None if failed
        """
        if not city_name or not city_name.strip():
            return None
            
        try:
            # Clean and encode the city name
            clean_city = city_name.strip()
            encoded_city = quote(clean_city)
            
            # Build the request URL
            url = f"{self.base_url}?q={encoded_city}&format=json&limit=1&addressdetails=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={'User-Agent': 'TrainTimesApp/1.0'}
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        if data and len(data) > 0:
                            result = data[0]
                            lat = float(result.get('lat', 0))
                            lon = float(result.get('lon', 0))
                            
                            # Validate coordinates
                            if -90 <= lat <= 90 and -180 <= lon <= 180:
                                logger.info(f"Successfully geocoded '{city_name}' to ({lat:.4f}, {lon:.4f})")
                                return (lat, lon)
                            else:
                                logger.warning(f"Invalid coordinates returned for '{city_name}': ({lat}, {lon})")
                                return None
                        else:
                            logger.warning(f"No results found for city '{city_name}'")
                            return None
                    else:
                        logger.error(f"Geocoding API returned status {response.status} for '{city_name}'")
                        return None
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error during geocoding for '{city_name}': {e}")
            return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout during geocoding for '{city_name}'")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Data parsing error during geocoding for '{city_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during geocoding for '{city_name}': {e}")
            return None
    
    def geocode_city_sync(self, city_name: str) -> Optional[Tuple[float, float]]:
        """
        Synchronous wrapper for geocoding a city name.
        
        Args:
            city_name: Name of the city to geocode
            
        Returns:
            Tuple of (latitude, longitude) if successful, None if failed
        """
        try:
            # Create a new event loop for this thread if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async geocoding
            return loop.run_until_complete(self.geocode_city(city_name))
            
        except Exception as e:
            logger.error(f"Error in synchronous geocoding for '{city_name}': {e}")
            return None


class GeocodingThread:
    """Thread-safe geocoding utility for Qt applications."""
    
    def __init__(self):
        """Initialize the geocoding thread utility."""
        self.service = GeocodingService()
    
    async def geocode_async(self, city_name: str) -> Optional[Tuple[float, float]]:
        """
        Async geocoding method for use in Qt threads.
        
        Args:
            city_name: Name of the city to geocode
            
        Returns:
            Tuple of (latitude, longitude) if successful, None if failed
        """
        return await self.service.geocode_city(city_name)


# Predefined coordinates for common cities to reduce API calls
CITY_COORDINATES = {
    # UK Cities
    "london": (51.5074, -0.1278),
    "manchester": (53.4808, -2.2426),
    "birmingham": (52.4862, -1.8904),
    "glasgow": (55.8642, -4.2518),
    "edinburgh": (55.9533, -3.1883),
    "cardiff": (51.4816, -3.1791),
    "belfast": (54.5973, -5.9301),
    "liverpool": (53.4084, -2.9916),
    "leeds": (53.8008, -1.5491),
    "sheffield": (53.3811, -1.4701),
    "bristol": (51.4545, -2.5879),
    "newcastle": (54.9783, -1.6178),
    "nottingham": (52.9548, -1.1581),
    "york": (53.9600, -1.0873),
    "bath": (51.3758, -2.3599),
    "cambridge": (52.2053, 0.1218),
    "oxford": (51.7520, -1.2577),
    "brighton": (50.8225, -0.1372),
    "canterbury": (51.2802, 1.0789),
    "winchester": (51.0632, -1.3080),
    
    # Major European Cities
    "paris": (48.8566, 2.3522),
    "berlin": (52.5200, 13.4050),
    "madrid": (40.4168, -3.7038),
    "rome": (41.9028, 12.4964),
    "amsterdam": (52.3676, 4.9041),
    "brussels": (50.8503, 4.3517),
    "vienna": (48.2082, 16.3738),
    "zurich": (47.3769, 8.5417),
    "stockholm": (59.3293, 18.0686),
    "copenhagen": (55.6761, 12.5683),
    "oslo": (59.9139, 10.7522),
    "helsinki": (60.1699, 24.9384),
    "dublin": (53.3498, -6.2603),
    "lisbon": (38.7223, -9.1393),
    "athens": (37.9838, 23.7275),
    "prague": (50.0755, 14.4378),
    "budapest": (47.4979, 19.0402),
    "warsaw": (52.2297, 21.0122),
    
    # Major World Cities
    "new york": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "sydney": (-33.8688, 151.2093),
    "melbourne": (-37.8136, 144.9631),
    "tokyo": (35.6762, 139.6503),
    "beijing": (39.9042, 116.4074),
    "shanghai": (31.2304, 121.4737),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.7041, 77.1025),
    "singapore": (1.3521, 103.8198),
    "hong kong": (22.3193, 114.1694),
    "dubai": (25.2048, 55.2708),
    "moscow": (55.7558, 37.6176),
    "istanbul": (41.0082, 28.9784),
    "cairo": (30.0444, 31.2357),
    "cape town": (-33.9249, 18.4241),
    "johannesburg": (-26.2041, 28.0473),
    "sao paulo": (-23.5505, -46.6333),
    "rio de janeiro": (-22.9068, -43.1729),
    "buenos aires": (-34.6118, -58.3960),
    "mexico city": (19.4326, -99.1332),
}


def get_city_coordinates(city_name: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a city, checking predefined list first, then online geocoding.
    
    Args:
        city_name: Name of the city
        
    Returns:
        Tuple of (latitude, longitude) if found, None otherwise
    """
    if not city_name:
        return None
        
    clean_name = city_name.strip().lower()
    
    # First check predefined coordinates
    coords = CITY_COORDINATES.get(clean_name)
    if coords:
        return coords
    
    # If not found, try online geocoding as fallback
    try:
        service = GeocodingService()
        return service.geocode_city_sync(city_name)
    except Exception as e:
        logger.error(f"Error in fallback geocoding for '{city_name}': {e}")
        return None


def get_available_cities() -> list[str]:
    """
    Get list of available cities for autocomplete.
    
    Returns:
        List of city names sorted alphabetically
    """
    return sorted(CITY_COORDINATES.keys())


def get_cities_matching(prefix: str) -> list[str]:
    """
    Get cities that match the given prefix for autocomplete.
    
    Args:
        prefix: The prefix to match against
        
    Returns:
        List of matching city names
    """
    if not prefix:
        return get_available_cities()
    
    prefix_lower = prefix.lower().strip()
    matching_cities = [
        city for city in CITY_COORDINATES.keys()
        if city.startswith(prefix_lower)
    ]
    return sorted(matching_cities)