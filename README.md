# 🚂 Trainer train times application

**Author: Oliver Ernster**

A modern PySide6 desktop application that displays real-time train departure information from Fleet to London Waterloo using the Transport API, featuring a sleek dark theme interface with automatic refresh capabilities.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- **🌙☀️ Light/Dark Theme Switching** - Defaults to dark theme, toggle with Ctrl+T or menu option
- **🚂 Custom Train Icon** - Beautiful SVG train icon for the application
- **⏰ Extended Time Window** - View trains up to 10 hours ahead for better planning
- **🔄 Real-time Updates** - Automatic refresh every 2 minutes + manual refresh
- **📊 Comprehensive Information** - Platform numbers, delays, cancellations, operators
- **📍 Live Tracking** - Current train locations when available
- **🎨 Unicode Icons** - Beautiful visual indicators throughout the interface
- **⚙️ Easy Configuration** - Simple JSON-based configuration system
- **🛡️ Robust Error Handling** - Graceful degradation and clear error messages
- **♿ Accessibility** - Keyboard navigation and high contrast support

## 🖼️ Screenshots
![Trainer](https://github.com/user-attachments/assets/03f30926-d067-4c4d-9480-01f38b87ae37)

## 🚀 Quick Start

### Note that you can build an exe as well using ```python build.py``` which uses nuitka --onefile.

### Prerequisites

- Python 3.8 or higher
- Transport API account (free tier available)

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

1. Visit [Transport API Developer Portal](https://developer.transportapi.com/)
2. Sign up for a free account (30 requests/day limit)
3. Create a new application to get your `app_id` and `app_key`
4. Add these credentials to your `config.json` file

### Configuration File Structure

```json
{
  "api": {
    "app_id": "your_app_id_here",
    "app_key": "your_app_key_here",
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
  }
}
```

### Application Icon

The application uses a custom SVG train icon located at `assets/train_icon.svg`. This icon appears in:
- Window title bar
- System taskbar/dock
- Alt+Tab application switcher
- System notifications (if implemented)

If the SVG icon is not found, the application gracefully falls back to using the Unicode train emoji (🚂) in the window title.

## 🏗️ Architecture

The application follows a clean, layered architecture:

```
┌─────────────────────────────────────────┐
│           Presentation Layer            │
│  MainWindow, TrainWidgets, ThemeStyler  │
├─────────────────────────────────────────┤
│          Business Logic Layer           │
│  TrainManager, UpdateManager, Config    │
├─────────────────────────────────────────┤
│           Data Access Layer             │
│   APIManager, CacheManager, DataMgr     │
├─────────────────────────────────────────┤
│             Data Models                 │
│   TrainData, ConfigData, Enums          │
└─────────────────────────────────────────┘
```

### Key Components

- **TrainData** - Immutable data class for train information
- **APIManager** - Handles Transport API communication with rate limiting
- **TrainManager** - Core business logic for data processing
- **UpdateManager** - Manages automatic and manual refresh operations
- **MainWindow** - Primary UI with dark theme styling
- **ConfigManager** - JSON-based configuration management

## 📁 Project Structure

```
train_times/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── config.json            # Configuration file
├── README.md              # This file
├── TRAIN_TIMES_APP_PLAN.md # Master project plan
├── docs/                  # Detailed documentation
│   ├── ARCHITECTURE.md    # System architecture
│   ├── API_INTEGRATION.md # API integration details
│   ├── UI_DESIGN.md       # UI specifications
│   └── IMPLEMENTATION.md  # Implementation guidelines
├── src/                   # Source code
│   ├── __init__.py
│   ├── models/            # Data models
│   │   ├── __init__.py
│   │   └── train_data.py
│   ├── api/               # API integration
│   │   ├── __init__.py
│   │   └── api_manager.py
│   ├── ui/                # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── train_widgets.py
│   │   └── theme_styler.py
│   ├── managers/          # Business logic
│   │   ├── __init__.py
│   │   ├── train_manager.py
│   │   ├── update_manager.py
│   │   └── config_manager.py
│   └── utils/             # Utility functions
│       ├── __init__.py
│       └── helpers.py
└── tests/                 # Test files
    ├── unit/
    ├── integration/
    └── mocks/
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

### Development Workflow

1. **Phase 1**: Core infrastructure and data models
2. **Phase 2**: API integration and data processing
3. **Phase 3**: UI foundation and dark theme
4. **Phase 4**: Business logic and update system
5. **Phase 5**: Integration, testing, and polish

See [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) for detailed development guidelines.

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

### Transport API Endpoints Used

- **Live Departures**: Real-time departure information
- **Service Details**: Detailed train service information
- **Station Data**: Station codes and information

### Rate Limiting
- Automatic rate limiting (30 requests/minute for free tier)
- Exponential backoff retry strategy
- Graceful degradation when limits exceeded

### Error Handling
- Network connectivity issues
- API authentication errors
- Service unavailability
- Malformed response handling

## 🔒 Security & Privacy

- API credentials stored locally in configuration file
- No personal data collection or transmission
- Secure HTTPS communication with Transport API
- Input validation and sanitization

## 🐛 Troubleshooting

### Common Issues

**Application won't start**
- Check Python version (3.8+ required)
- Verify all dependencies are installed
- Ensure config.json exists and is valid

**No train data displayed**
- Verify API credentials in config.json
- Check internet connection
- Confirm Transport API service status

**High CPU usage**
- Reduce refresh frequency in config.json
- Check for memory leaks in logs
- Restart application if needed

### Logging

Application logs are written to `train_times.log` with detailed error information and debugging data.

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
- [PySide6](https://doc.qt.io/qtforpython/) for the excellent Qt Python bindings
- [South Western Railway](https://www.southwesternrailway.com/) for the train services
- The Python community for amazing libraries and tools

## 📞 Support

For support, please:
1. Check the [troubleshooting section](#-troubleshooting)
2. Review the [documentation](docs/)
3. Search existing [issues](../../issues)
4. Create a new issue if needed

---

**Ready to track your trains in style! 🚂✨**
