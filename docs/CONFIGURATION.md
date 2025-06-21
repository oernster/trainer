# ⚙️ Configuration Guide

## Getting API Credentials

### Transport API (Required for Train Data)
1. Visit [Transport API Developer Portal](https://developer.transportapi.com/)
2. Sign up for a free account (30 requests/day limit)
3. Create a new application to get your `app_id` and `app_key`
4. Add these credentials to your `config.json` file

### NASA API (Required for Astronomy Features)
1. Visit [NASA API Portal](https://api.nasa.gov/)
2. Click "Generate API Key"
3. Fill out the simple form with:
   - **First Name**: Your first name
   - **Last Name**: Your last name
   - **Email**: Your email address
4. Click "Signup" - your API key will be displayed immediately
5. **No verification required** - the key is active instantly
6. Add the API key to your `config.json` file

**NASA API Benefits:**
- ✅ **Completely Free** - No payment required ever
- ✅ **Generous Limits** - 1,000 requests per hour
- ✅ **No Verification** - Instant activation
- ✅ **Multiple Services** - Access to all NASA APIs with one key
- ✅ **No Expiration** - Keys don't expire unless unused for 30+ days

**NASA APIs Used:**
- **APOD**: Astronomy Picture of the Day with professional explanations
- **NeoWs**: Near Earth Object Web Service for asteroid tracking
- **ISS**: International Space Station location and pass predictions
- **EPIC**: Earth Polychromatic Imaging Camera for satellite imagery

## Configuration File Structure

```json
{
  "api": {
    "app_id": "your_transport_api_app_id_here",
    "app_key": "your_transport_api_app_key_here",
    "base_url": "https://transportapi.com/v3/uk",
    "timeout_seconds": 10,
    "max_retries": 3,
    "rate_limit_per_minute": 30
  },
  "stations": {
    "from_code": "FLE",
    "from_name": "Fleet",
    "to_code": "WAT",
    "to_name": "London Waterloo"
  },
  "refresh": {
    "auto_enabled": true,
    "interval_minutes": 30,
    "manual_enabled": true
  },
  "display": {
    "max_trains": 50,
    "time_window_hours": 16,
    "show_cancelled": true,
    "theme": "dark"
  },
  "weather": {
    "enabled": true,
    "location_name": "London",
    "location_latitude": 51.5074,
    "location_longitude": -0.1278,
    "update_interval_minutes": 30,
    "cache_duration_seconds": 1800,
    "timeout_seconds": 10
  },
  "astronomy": {
    "enabled": true,
    "nasa_api_key": "your_nasa_api_key_here",
    "services": {
      "apod": true,
      "neows": true,
      "iss": true,
      "epic": false
    },
    "display": {
      "show_in_forecast": true,
      "default_expanded": false,
      "max_events_per_day": 3,
      "icon_size": "medium"
    },
    "cache": {
      "duration_hours": 6,
      "max_entries": 100
    }
  }
}
```

## Configuration Options Explained

### Weather Configuration
- **enabled**: Enable/disable weather integration
- **location_name**: Display name for your location
- **location_latitude/longitude**: GPS coordinates for weather data
- **update_interval_minutes**: How often to refresh weather data (default: 30)
- **cache_duration_seconds**: How long to cache weather data (default: 1800 = 30 minutes)

### Astronomy Configuration
- **enabled**: Enable/disable astronomy features
- **nasa_api_key**: Your NASA API key from https://api.nasa.gov/
- **services**: Enable/disable individual NASA services
  - **apod**: Astronomy Picture of the Day
  - **neows**: Near Earth Object tracking
  - **iss**: International Space Station passes
  - **epic**: Earth satellite imagery
- **display**: UI preferences for astronomy panel
- **cache**: Caching settings for astronomy data

## Application Icon

The application uses a custom SVG train icon located at `assets/train_icon.svg`. This icon appears in:
- Window title bar
- System taskbar/dock
- Alt+Tab application switcher
- System notifications (if implemented)

If the SVG icon is not found, the application gracefully falls back to using the Unicode train emoji (🚂) in the window title.