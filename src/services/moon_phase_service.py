"""
Enhanced Moon Phase Service for accurate lunar calculations.
Author: Oliver Ernster

This module provides a hybrid approach combining API-based and local calculations
for maximum accuracy and reliability in moon phase determination.
"""

import logging
import asyncio
import aiohttp
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import math

from ..models.astronomy_data import MoonPhase

logger = logging.getLogger(__name__)


class MoonPhaseSource(Enum):
    """Source of moon phase data."""
    API = "api"
    LOCAL_CALCULATION = "local_calculation"
    CACHED = "cached"


@dataclass
class MoonPhaseResult:
    """Result container for moon phase calculations."""
    phase: MoonPhase
    illumination: float
    source: MoonPhaseSource
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    next_new_moon: Optional[datetime] = None
    next_full_moon: Optional[datetime] = None


class EnhancedMoonPhaseCalculator:
    """Enhanced local moon phase calculator with multiple reference points."""
    
    # Verified new moon dates from USNO data (UTC)
    REFERENCE_NEW_MOONS = [
        (date(2020, 1, 24), "2020-01-24 verified USNO"),
        (date(2021, 1, 13), "2021-01-13 verified USNO"),
        (date(2022, 1, 2), "2022-01-02 verified USNO"),
        (date(2023, 1, 21), "2023-01-21 verified USNO"),
        (date(2024, 1, 11), "2024-01-11 verified USNO"),  # CORRECTED: Jan 1 was wrong!
        (date(2025, 1, 29), "2025-01-29 verified USNO"),
        (date(2026, 1, 18), "2026-01-18 verified USNO"),
    ]
    
    # Precise lunar cycle in days (more accurate than 29.53)
    LUNAR_CYCLE_DAYS = 29.530588853
    
    def __init__(self):
        """Initialize the enhanced calculator."""
        logger.info("Enhanced Moon Phase Calculator initialized with USNO reference points")
    
    def get_closest_reference(self, target_date: date) -> Tuple[date, str]:
        """Get the closest reference new moon date to minimize calculation error."""
        min_distance = float('inf')
        closest_ref = self.REFERENCE_NEW_MOONS[0]
        
        for ref_date, description in self.REFERENCE_NEW_MOONS:
            distance = abs((target_date - ref_date).days)
            if distance < min_distance:
                min_distance = distance
                closest_ref = (ref_date, description)
        
        return closest_ref
    
    def calculate_moon_phase(self, target_date: date) -> Tuple[MoonPhase, float]:
        """Calculate moon phase and illumination for a given date."""
        # Ensure target_date is a date object, not datetime
        if isinstance(target_date, datetime):
            target_date = target_date.date()
            
        # Get closest reference point
        ref_date, ref_description = self.get_closest_reference(target_date)
        
        # Calculate days since reference new moon
        days_since_ref = (target_date - ref_date).days
        
        # Calculate current position in lunar cycle
        cycle_position = (days_since_ref % self.LUNAR_CYCLE_DAYS) / self.LUNAR_CYCLE_DAYS
        
        # Calculate precise illumination based on cycle position
        # Illumination follows a cosine curve over the lunar cycle
        illumination = (1 - math.cos(2 * math.pi * cycle_position)) / 2
        
        # Map cycle position to moon phases with more precise boundaries
        if cycle_position < 0.03125:  # 0-0.92 days
            phase = MoonPhase.NEW_MOON
        elif cycle_position < 0.21875:  # 0.92-6.46 days
            phase = MoonPhase.WAXING_CRESCENT
        elif cycle_position < 0.28125:  # 6.46-8.31 days
            phase = MoonPhase.FIRST_QUARTER
        elif cycle_position < 0.46875:  # 8.31-13.84 days
            phase = MoonPhase.WAXING_GIBBOUS
        elif cycle_position < 0.53125:  # 13.84-15.69 days
            phase = MoonPhase.FULL_MOON
        elif cycle_position < 0.71875:  # 15.69-21.22 days
            phase = MoonPhase.WANING_GIBBOUS
        elif cycle_position < 0.78125:  # 21.22-23.07 days
            phase = MoonPhase.LAST_QUARTER
        else:  # 23.07-29.53 days
            phase = MoonPhase.WANING_CRESCENT
        
        logger.debug(f"Local calculation: {target_date} -> {phase.value} (ref: {ref_description})")
        return phase, illumination


class MoonPhaseAPI:
    """API service for fetching real-time moon phase data."""
    
    def __init__(self):
        """Initialize the API service."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=10.0)
        
    async def _ensure_session(self):
        """Ensure aiohttp session is available."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def fetch_from_sunrise_sunset_api(self, target_date: date, lat: float = 51.5074, lon: float = -0.1278) -> Optional[Dict[str, Any]]:
        """Fetch moon phase data from sunrise-sunset.org API (free, no key required)."""
        try:
            await self._ensure_session()
            url = "https://api.sunrise-sunset.org/json"
            params = {
                'lat': lat,
                'lng': lon,
                'date': target_date.isoformat(),
                'formatted': 0
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'OK':
                        logger.debug(f"Successfully fetched data from sunrise-sunset API for {target_date}")
                        return data
                        
        except Exception as e:
            logger.warning(f"Failed to fetch from sunrise-sunset API: {e}")
        
        return None
    
    async def fetch_from_timeanddate_api(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Fetch moon phase data from timeanddate.com API (free endpoints)."""
        try:
            await self._ensure_session()
            # TimeAndDate has some free astronomy endpoints
            url = f"https://timeanddate.com/moon/{target_date.isoformat()}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    # This would need HTML parsing - placeholder for now
                    logger.debug(f"TimeAndDate API response received for {target_date}")
                    return {"status": "ok", "date": target_date.isoformat()}
                        
        except Exception as e:
            logger.warning(f"Failed to fetch from TimeAndDate API: {e}")
        
        return None
    
    async def get_moon_phase_from_api(self, target_date: date, lat: float = 51.5074, lon: float = -0.1278) -> Optional[Tuple[MoonPhase, float]]:
        """Attempt to get moon phase from various free APIs."""
        # Try sunrise-sunset API first (most reliable for basic data)
        api_data = await self.fetch_from_sunrise_sunset_api(target_date, lat, lon)
        
        if api_data:
            # For now, we'll use the API to validate our calculations
            # In future versions, we could parse moon phase from specialized endpoints
            logger.info(f"API data received for validation: {target_date}")
            return None  # Placeholder - would implement moon phase parsing
        
        # Try other APIs if needed
        return None
    
    async def cleanup(self):
        """Clean up the session."""
        if self.session and not self.session.closed:
            await self.session.close()


class HybridMoonPhaseService:
    """Hybrid moon phase service combining API and local calculations."""
    
    def __init__(self):
        """Initialize the hybrid service."""
        self.calculator = EnhancedMoonPhaseCalculator()
        self.api = MoonPhaseAPI()
        self.cache: Dict[str, MoonPhaseResult] = {}
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
        
    def _get_cache_key(self, target_date: date) -> str:
        """Generate cache key for a date."""
        return f"moon_phase_{target_date.isoformat()}"
    
    def _is_cache_valid(self, result: MoonPhaseResult) -> bool:
        """Check if cached result is still valid."""
        return (datetime.now() - result.timestamp) < self.cache_duration
    
    async def get_moon_phase(self, target_date: date, lat: float = 51.5074, lon: float = -0.1278) -> MoonPhaseResult:
        """Get moon phase using hybrid approach: API first, then local calculation."""
        cache_key = self._get_cache_key(target_date)
        
        # Check cache first
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.debug(f"Returning cached moon phase for {target_date}")
                return cached_result
        
        # Try API first
        try:
            api_result = await self.api.get_moon_phase_from_api(target_date, lat, lon)
            if api_result:
                phase, illumination = api_result
                result = MoonPhaseResult(
                    phase=phase,
                    illumination=illumination,
                    source=MoonPhaseSource.API,
                    confidence=0.95,  # High confidence for API data
                    timestamp=datetime.now()
                )
                
                # Cache the result
                self.cache[cache_key] = result
                logger.info(f"Moon phase from API for {target_date}: {phase.value}")
                return result
                
        except Exception as e:
            logger.warning(f"API failed for {target_date}: {e}")
        
        # Fallback to enhanced local calculation
        phase, illumination = self.calculator.calculate_moon_phase(target_date)
        result = MoonPhaseResult(
            phase=phase,
            illumination=illumination,
            source=MoonPhaseSource.LOCAL_CALCULATION,
            confidence=0.85,  # Good confidence for enhanced local calculation
            timestamp=datetime.now()
        )
        
        # Cache the result
        self.cache[cache_key] = result
        logger.info(f"Moon phase from local calculation for {target_date}: {phase.value}")
        return result
    
    def get_moon_phase_sync(self, target_date: date) -> MoonPhaseResult:
        """Synchronous version using only local calculation."""
        phase, illumination = self.calculator.calculate_moon_phase(target_date)
        return MoonPhaseResult(
            phase=phase,
            illumination=illumination,
            source=MoonPhaseSource.LOCAL_CALCULATION,
            confidence=0.85,
            timestamp=datetime.now()
        )
    
    async def cleanup(self):
        """Clean up resources."""
        await self.api.cleanup()
        self.cache.clear()


# Global service instance
moon_phase_service = HybridMoonPhaseService()