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
}


def get_city_coordinates(city_name: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a city, checking predefined list first.
    
    Args:
        city_name: Name of the city
        
    Returns:
        Tuple of (latitude, longitude) if found, None otherwise
    """
    if not city_name:
        return None
        
    clean_name = city_name.strip().lower()
    return CITY_COORDINATES.get(clean_name)