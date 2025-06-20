"""
Version information for Trainer application.
Author: Oliver Ernster

Centralized version management for the entire application including
weather integration features and build system information.
"""

# Core application information
__version__ = "3.0.2"  # Major version bump for weather integration
__version_info__ = (3, 0, 2)
__app_name__ = "Trainer"
__app_display_name__ = "Trainer - Train Times with Weather Integration"
__author__ = "Oliver Ernster"
__company__ = "Trainer by Oliver Ernster"
__copyright__ = "© 2025 Oliver Ernster"
__description__ = "Train times application with integrated weather forecasting"

# Feature information
__features__ = [
    "Real-time train departure information",
    "3-hourly weather forecasts for current day",
    "7-day weather outlook",
    "Dark/Light theme support",
    "Configurable refresh intervals",
    "Weather data for destination location",
    "No API key required for weather data",
    "Astronomical information with a 7 day outlook",
]

# Weather integration information
__weather_version__ = "1.0.0"
__weather_api_provider__ = "Open-Meteo"
__weather_api_url__ = "https://open-meteo.com/"
__weather_features__ = [
    "3-hourly forecasts",
    "7-day daily forecasts",
    "Temperature and humidity display",
    "Weather icons for each forecast",
    "Configurable location settings",
    "Automatic refresh intervals",
]

# Build system information
__build_system__ = "Nuitka"
__build_profiles__ = ["debug", "release", "minimal"]
__supported_platforms__ = ["Windows 10+"]
__python_version_required__ = "3.9+"

# API information
__train_api_provider__ = "Transport API"
__train_api_url__ = "https://transportapi.com/"

# License information
__license__ = "Proprietary"
__license_weather_compliance__ = "LGPL v3 (PySide6)"

# Development information
__development_status__ = "Production"
__architecture_pattern__ = "Layered MVC with SOLID principles"
__design_patterns__ = ["Factory", "Observer", "Strategy", "Command"]

# Distribution information
__distribution_type__ = "Single executable"
__estimated_size_mb__ = "55-60"
__installation_required__ = False


def get_version_string() -> str:
    """Get formatted version string."""
    return f"{__app_name__} v{__version__}"


def get_full_version_info() -> str:
    """Get comprehensive version information."""
    return f"""
{__app_display_name__}
Version: {__version__}
Weather Integration: v{__weather_version__}
Author: {__author__}
Build System: {__build_system__}
Weather Provider: {__weather_api_provider__}
Train Data Provider: {__train_api_provider__}
"""


def get_about_text() -> str:
    """Get formatted about text for dialogs."""
    features_list = "\n".join(f"<li>{feature}</li>" for feature in __features__)

    return f"""
<h3>{__app_display_name__}</h3>
<p><b>Version {__version__}</b></p>
<p><b>Author: {__author__}</b></p>
<p>{__description__}</p>

<p><b>Features:</b></p>
<ul>
{features_list}
</ul>

<p><b>Weather Integration:</b></p>
<ul>
<li>Powered by {__weather_api_provider__} ({__weather_api_url__})</li>
<li>No API key required for weather data</li>
<li>3-hourly and daily forecasts</li>
</ul>

<p><b>Technical Information:</b></p>
<ul>
<li>Built with {__build_system__} for optimal performance</li>
<li>Architecture: {__architecture_pattern__}</li>
<li>Single-file executable distribution</li>
</ul>

<p><b>Data Sources:</b></p>
<ul>
<li>Train data: {__train_api_provider__}</li>
<li>Weather data: {__weather_api_provider__}</li>
</ul>

<p>{__copyright__}</p>
"""


def get_build_metadata() -> dict:
    """Get metadata for build system."""
    return {
        "app_name": __app_name__,
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "company": __company__,
        "copyright": __copyright__,
        "build_system": __build_system__,
        "weather_version": __weather_version__,
        "estimated_size": __estimated_size_mb__,
    }


def get_weather_info() -> dict:
    """Get weather integration information."""
    return {
        "version": __weather_version__,
        "provider": __weather_api_provider__,
        "api_url": __weather_api_url__,
        "features": __weather_features__,
        "api_key_required": False,
    }


def is_weather_enabled() -> bool:
    """Check if weather integration is enabled in this build."""
    return __weather_version__ is not None and __weather_api_provider__ is not None
