# 🚂 Trainer train times application

**Author: Oliver Ernster**

A modern PySide6 desktop application that displays real-time train departure information from Fleet to London Waterloo using the Transport API, featuring a sleek dark theme interface with automatic refresh capabilities.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

### 🚂 Train Information
- **⏰ Extended Time Window** - View trains up to 10 hours ahead for better planning
- **🔄 Real-time Updates** - Automatic refresh every 2 minutes + manual refresh
- **📊 Comprehensive Information** - Platform numbers, delays, cancellations, operators
- **📍 Live Tracking** - Current train locations when available

### 🌤️ Weather Integration
- **🌡️ Real-time Weather** - Current conditions and 7-day forecast using Open-Meteo API
- **🌧️ Weather Icons** - Beautiful emoji weather indicators
- **📍 Location-based** - Weather data for your specific location
- **⚡ Fast Updates** - Efficient caching with 30-minute refresh intervals

### 🌟 Astronomy Features (Fully Implemented)
- **🌙 Daily Astronomy** - NASA Astronomy Picture of the Day (APOD) with HD imagery
- **🛰️ ISS Tracking** - Real-time International Space Station pass predictions
- **☄️ Space Events** - Near-Earth objects, asteroids, and potentially hazardous objects
- **🌍 Earth Imagery** - EPIC satellite imagery from DSCOVR satellite
- **📅 7-Day Forecast** - Interactive astronomy panel with clickable event icons
- **🔗 NASA Integration** - Direct links to NASA websites and current sky events
- **🌕 Moon Phases** - Accurate moon phase calculations and illumination data
- **⭐ Event Prioritization** - High-priority events highlighted with visual indicators
- **🎯 Interactive UI** - Large, clickable astronomy event icons with hover effects
- **🌐 Current Events** - Direct access to tonight's astronomical phenomena

### 🎨 User Interface
- **🌙☀️ Light/Dark Theme Switching** - Defaults to dark theme, toggle with Ctrl+T or menu option
- **🚂 Custom Train Icon** - Beautiful SVG train icon for the application
- **🎨 Unicode Icons** - Beautiful visual indicators throughout the interface
- **♿ Accessibility** - Keyboard navigation and high contrast support

### 🔧 Technical Features
- **⚙️ Easy Configuration** - Simple JSON-based configuration system
- **🛡️ Robust Error Handling** - Graceful degradation and clear error messages
- **🧪 100% Test Coverage** - Comprehensive testing with pytest
- **🏗️ Object-Oriented Design** - Clean architecture with proven design patterns

## 🖼️ Screenshots
![Trainer](https://github.com/user-attachments/assets/d5c64911-ecdd-4c2a-b3a9-45a8e36c63f9)

## 🚀 Quick Start

### 📦 Building Executable

You can build a standalone executable using Nuitka for easy distribution:

```bash
python build.py
```

This uses Nuitka with the `--onefile` option to create a single executable file that includes all dependencies. The build script automatically:
- Compiles the Python application to optimized machine code
- Bundles all dependencies into a single executable
- Includes all necessary assets and configuration files
- Creates a portable executable that doesn't require Python installation

**Build Requirements:**
- Nuitka compiler (`pip install nuitka`)
- C++ compiler (Visual Studio Build Tools on Windows)
- All project dependencies installed

**Output:** The executable will be created in the `dist/` directory.

### Prerequisites

- Python 3.8 or higher
- Transport API account (free tier available)
- NASA API key (completely free, 1000 requests/hour)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd train_times
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API credentials**
   ```bash
   cp config.json.template config.json
   # Edit config.json with your Transport API credentials
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Getting API Credentials

#### Transport API (Required for Train Data)
1. Visit [Transport API Developer Portal](https://developer.transportapi.com/)
2. Sign up for a free account (30 requests/day limit)
3. Create a new application to get your `app_id` and `app_key`
4. Add these credentials to your `config.json` file

#### NASA API (Required for Astronomy Features)
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

### Configuration File Structure

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
    "interval_minutes": 2,
    "manual_enabled": true
  },
  "display": {
    "max_trains": 50,
    "time_window_hours": 10,
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

### Configuration Options Explained

#### Weather Configuration
- **enabled**: Enable/disable weather integration
- **location_name**: Display name for your location
- **location_latitude/longitude**: GPS coordinates for weather data
- **update_interval_minutes**: How often to refresh weather data (default: 30)
- **cache_duration_seconds**: How long to cache weather data (default: 1800 = 30 minutes)

#### Astronomy Configuration
- **enabled**: Enable/disable astronomy features
- **nasa_api_key**: Your NASA API key from https://api.nasa.gov/
- **services**: Enable/disable individual NASA services
  - **apod**: Astronomy Picture of the Day
  - **neows**: Near Earth Object tracking
  - **iss**: International Space Station passes
  - **epic**: Earth satellite imagery
- **display**: UI preferences for astronomy panel
- **cache**: Caching settings for astronomy data

### Application Icon

The application uses a custom SVG train icon located at `assets/train_icon.svg`. This icon appears in:
- Window title bar
- System taskbar/dock
- Alt+Tab application switcher
- System notifications (if implemented)

If the SVG icon is not found, the application gracefully falls back to using the Unicode train emoji (🚂) in the window title.

## 🏗️ Architecture

The application follows a clean, layered Object-Oriented architecture with fully integrated weather and astronomy systems:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  MainWindow, TrainWidgets, WeatherWidget, AstronomyWidget   │
│  AstronomyForecastPanel, DailyAstronomyPanel, EventIcons    │
├─────────────────────────────────────────────────────────────┤
│                 Business Logic Layer                        │
│  TrainManager, WeatherManager, AstronomyManager             │
│  CombinedForecastManager, ConfigManager, ThemeManager       │
├─────────────────────────────────────────────────────────────┤
│                  Data Access Layer                          │
│  APIManager, WeatherAPIManager, NASAAPIManager              │
│  APODService, ISSService, NeoWsService, EPICService         │
├─────────────────────────────────────────────────────────────┤
│                    Data Models                              │
│  TrainData, WeatherData, AstronomyData, AstronomyEvent      │
│  CombinedForecastData, Location, MoonPhase                  │
├─────────────────────────────────────────────────────────────┤
│                  External Services                          │
│  Transport API, Open-Meteo API, NASA APIs (4 services)     │
│  APOD, ISS Tracking, NeoWs, EPIC Satellite Imagery         │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### Core System
- **TrainData** - Immutable data class for train information
- **APIManager** - Handles Transport API communication with rate limiting
- **TrainManager** - Core business logic for train data processing
- **UpdateManager** - Manages automatic and manual refresh operations
- **MainWindow** - Primary UI with integrated weather and astronomy display

#### Weather Integration
- **WeatherData** - Immutable weather data models
- **WeatherAPIManager** - Open-Meteo API integration with caching
- **WeatherManager** - Business logic for weather data management
- **WeatherWidget** - UI component for weather display

#### Astronomy Integration (Fully Implemented)
- **AstronomyData** - Comprehensive astronomy event models with validation
- **NASAAPIManager** - Complete NASA API integration (APOD, ISS, NeoWs, EPIC)
- **AstronomyManager** - Advanced business logic with caching and auto-refresh
- **AstronomyWidget** - Interactive UI with 7-day forecast and event icons
- **AstronomyForecastPanel** - 7-day astronomy forecast with clickable events
- **DailyAstronomyPanel** - Individual day panels with moon phases
- **AstronomyEventIcon** - Large, interactive event icons with hover effects
- **CombinedForecastManager** - Unified weather + astronomy forecasting
- **AstronomyConfig** - Comprehensive configuration with service toggles

#### Design Patterns Used
- **Strategy Pattern** - Pluggable data sources (Weather, Astronomy)
- **Factory Pattern** - Component creation and dependency injection
- **Observer Pattern** - Qt signals/slots for real-time updates
- **Facade Pattern** - Simplified interfaces for complex subsystems
- **Decorator Pattern** - Caching and rate limiting cross-cutting concerns

## 📁 Project Structure

```
trainer/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── requirements-dev.txt             # Development dependencies
├── config.json                      # Configuration file
├── README.md                        # This file
├── version.py                       # Version and metadata
├── build.py                         # Build script for executable
├── install.py                       # Installation script
├── docs/                            # Detailed documentation
│   ├── ARCHITECTURE.md              # Enhanced system architecture
│   └── NASA_ASTRONOMY_INTEGRATION_PLAN.md  # Astronomy integration plan
├── assets/                          # Application assets
│   ├── train_icon.svg               # SVG train icon
│   ├── train_icon_*.png             # PNG icons (multiple sizes)
│   └── train_icon.ico               # Windows icon
├── src/                             # Source code
│   ├── __init__.py
│   ├── models/                      # Data models
│   │   ├── __init__.py
│   │   ├── train_data.py            # Train data models
│   │   ├── weather_data.py          # Weather data models
│   │   ├── astronomy_data.py        # Comprehensive astronomy data models
│   │   └── combined_forecast_data.py # Combined weather + astronomy models
│   ├── api/                         # API integration
│   │   ├── __init__.py
│   │   ├── api_manager.py           # Transport API manager
│   │   ├── weather_api_manager.py   # Weather API manager
│   │   └── nasa_api_manager.py      # Complete NASA API integration
│   ├── ui/                          # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py           # Enhanced main window
│   │   ├── train_widgets.py         # Train display widgets
│   │   ├── weather_widgets.py       # Weather display widgets
│   │   ├── astronomy_widgets.py     # Complete astronomy UI components
│   │   ├── settings_dialog.py       # Settings configuration
│   │   └── splash_screen.py         # Application splash screen
│   ├── managers/                    # Business logic
│   │   ├── __init__.py
│   │   ├── train_manager.py         # Train data management
│   │   ├── weather_manager.py       # Weather data management
│   │   ├── astronomy_manager.py     # Complete astronomy management
│   │   ├── astronomy_config.py      # Astronomy configuration
│   │   ├── combined_forecast_manager.py # Combined forecast coordination
│   │   ├── config_manager.py        # Configuration management
│   │   ├── theme_manager.py         # Theme management
│   │   └── weather_config.py        # Weather configuration
│   └── utils/                       # Utility functions
│       ├── __init__.py
│       └── helpers.py               # Helper utilities
├── tests/                           # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py                  # Test configuration
│   ├── unit/                        # Unit tests (100% coverage goal)
│   │   ├── test_models/             # Model tests
│   │   ├── test_api/                # API tests
│   │   ├── test_ui/                 # UI tests
│   │   ├── test_managers/           # Manager tests
│   │   ├── test_weather/            # Weather integration tests
│   │   └── test_astronomy/          # Comprehensive astronomy tests
│   │       ├── test_api/            # NASA API service tests
│   │       ├── test_managers/       # Astronomy manager tests
│   │       ├── test_models/         # Astronomy data model tests
│   │       └── test_ui/             # Astronomy widget tests
│   ├── integration/                 # Integration tests
│   │   └── test_api_integration.py  # API integration tests
│   ├── performance/                 # Performance tests
│   │   └── test_large_datasets.py   # Performance testing
│   └── fixtures/                    # Test data
│       ├── sample_api_responses.json
│       ├── sample_weather_responses.json
│       └── sample_astronomy_responses.json
└── licenses/                        # License files
    ├── LGPL-3.0.txt
    └── THIRD_PARTY_LICENSES.txt
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/unit/test_train_data.py

# Run integration tests
pytest tests/integration/
```

### Test Categories

- **Unit Tests** - Individual component testing
- **Integration Tests** - API and component interaction testing
- **UI Tests** - User interface testing with pytest-qt
- **Mock Tests** - Testing with simulated API responses

## 🔧 Development

### Setting up Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Run code formatting
black src/
flake8 src/

# Type checking
mypy src/
```

### Build and Deployment

#### Building Standalone Executable

The project includes a comprehensive build system using Nuitka for creating optimized standalone executables:

```bash
# Build standalone executable
python build.py

# The build script will:
# 1. Install required build dependencies
# 2. Compile Python code to optimized machine code
# 3. Bundle all dependencies and assets
# 4. Create a single executable file
```

**Build Configuration:**
- **Compiler**: Nuitka with `--onefile` optimization
- **Output**: Single executable in `dist/` directory
- **Size**: Optimized for minimal file size
- **Performance**: Native machine code execution
- **Dependencies**: All Python packages and assets bundled

**Build Requirements:**
```bash
# Install Nuitka compiler
pip install nuitka

# Windows: Install Visual Studio Build Tools
# Linux: Install gcc/g++
# macOS: Install Xcode Command Line Tools
```

**Advanced Build Options:**
```bash
# Debug build with console output
python build.py --debug

# Build with specific Python optimization
python build.py --optimize

# Clean build (removes previous build artifacts)
python build.py --clean
```

#### Distribution

The built executable is completely portable and includes:
- ✅ All Python dependencies
- ✅ Application assets and icons
- ✅ Configuration templates
- ✅ No Python installation required
- ✅ Single file deployment

### Development Workflow

1. **Phase 1**: Core infrastructure and data models ✅
2. **Phase 2**: API integration and data processing ✅
3. **Phase 3**: UI foundation and dark theme ✅
4. **Phase 4**: Business logic and update system ✅
5. **Phase 5**: Integration, testing, and polish ✅
6. **Phase 6**: Astronomy integration and NASA APIs ✅

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for detailed technical documentation.

## 🎨 UI Features

### Dark Theme
- Modern dark color palette optimized for readability
- Status-based color coding (green=on-time, orange=delayed, red=cancelled)
- Smooth animations and transitions
- Responsive layout adapting to window size

### Unicode Icons
- 🚂 Train services
- 🚉 Platform information
- 📍 Current locations
- 🏁 Destinations
- ✅⚠️❌ Status indicators
- ⚡🚌 Service types

### Accessibility
- Keyboard navigation support
- High contrast mode option
- Screen reader compatibility
- Configurable font sizes

## 📊 API Integration

### Transport API (Train Data)
- **Live Departures**: Real-time departure information
- **Service Details**: Detailed train service information
- **Station Data**: Station codes and information
- **Rate Limiting**: 30 requests/minute for free tier
- **Error Handling**: Graceful degradation with retry logic

### Open-Meteo API (Weather Data)
- **Current Weather**: Real-time weather conditions
- **Hourly Forecast**: 3-hourly weather data for precision
- **Daily Forecast**: 7-day weather outlook
- **No API Key Required**: Completely free service
- **High Performance**: Optimized for fast responses

### NASA APIs (Astronomy Data - Fully Implemented)
- **APOD (Astronomy Picture of the Day)**: Daily space imagery with HD photos and detailed explanations
- **NeoWs (Near Earth Object Web Service)**: Comprehensive asteroid and comet tracking with hazard detection
- **ISS (International Space Station)**: Real-time ISS pass predictions with visibility duration and quality
- **EPIC (Earth Polychromatic Imaging Camera)**: Daily Earth satellite imagery from DSCOVR at L1 Lagrange point
- **Rate Limiting**: 1,000 requests/hour with intelligent request management
- **Caching Strategy**: 6-hour intelligent cache with configurable duration
- **Error Handling**: Comprehensive graceful fallback with cached data and service-specific error recovery
- **Concurrent Processing**: Parallel API calls for optimal performance
- **Data Validation**: Complete integrity checks and astronomy data validation
- **Moon Phase Calculations**: Accurate lunar phase and illumination calculations

### API Integration Patterns
- **Strategy Pattern**: Pluggable API sources for different data types
- **Factory Pattern**: Centralized API client creation
- **Decorator Pattern**: Caching and rate limiting as cross-cutting concerns
- **Circuit Breaker**: Automatic failover when APIs are unavailable

## 🔒 Security & Privacy

- API credentials stored locally in configuration file
- No personal data collection or transmission
- Secure HTTPS communication with Transport API
- Input validation and sanitization

## 🐛 Troubleshooting

### Common Issues

**Application won't start**
- Check Python version (3.8+ required)
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Ensure config.json exists and is valid JSON
- Check that all required API keys are configured

**No train data displayed**
- Verify Transport API credentials in config.json
- Check internet connection
- Confirm Transport API service status at https://developer.transportapi.com/

**Weather not showing**
- Ensure weather.enabled is true in config.json
- Check location coordinates are valid (latitude: -90 to 90, longitude: -180 to 180)
- Verify internet connection for Open-Meteo API

**Astronomy features not working**
- Verify NASA API key in config.json is valid and properly formatted
- Check that astronomy.enabled is true in configuration
- Ensure NASA API key is valid at https://api.nasa.gov/ (should be 40+ characters)
- Check individual service toggles in astronomy.services (apod, iss, neows, epic)
- Verify location coordinates are valid (latitude: -90 to 90, longitude: -180 to 180)
- Check internet connection for NASA API access
- Review logs for specific NASA API service errors
- Ensure at least one astronomy service is enabled
- Check cache duration and update interval settings

**High CPU usage**
- Reduce refresh frequency in config.json
- Disable unused features (weather, astronomy services)
- Check for memory leaks in logs
- Restart application if needed

**Theme issues**
- Try switching themes with Ctrl+T
- Check display.theme setting in config.json
- Restart application to reset theme state

### Logging

Application logs are written to the console and include:
- API request/response information
- Weather and astronomy data updates
- Error messages with stack traces
- Performance metrics and timing information

### Getting Help

1. Check the [troubleshooting section](#-troubleshooting) above
2. Review the [configuration documentation](#️-configuration)
3. Check the logs for specific error messages
4. Verify all API keys and credentials are correct
5. Test with minimal configuration (disable weather/astronomy temporarily)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation
- Use type hints
- Add logging for debugging

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Oliver Ernster** - *Initial work and development*

## 🙏 Acknowledgments

- [Transport API](https://www.transportapi.com/) for providing UK transport data
- [Open-Meteo](https://open-meteo.com/) for free, high-quality weather data
- [NASA](https://api.nasa.gov/) for providing free access to space and astronomy data
- [PySide6](https://doc.qt.io/qtforpython/) for the excellent Qt Python bindings
- [South Western Railway](https://www.southwesternrailway.com/) for the train services
- The Python community for amazing libraries and tools
- The open-source community for inspiration and best practices

## 📞 Support

For support, please:
1. Check the [troubleshooting section](#-troubleshooting)
2. Review the [documentation](docs/)
3. Search existing [issues](../../issues)
4. Create a new issue if needed

---

**Ready to track your trains in style! 🚂✨**
