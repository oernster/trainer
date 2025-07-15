# 🚂 Trainer - Train Times with Weather Integration & Astronomical Events

**Author: Oliver Ernster**

### If you like it please buy me a coffee: [Donation link](https://www.paypal.com/ncp/payment/7XYN6DCYK24VY)

A modern PySide6 desktop application that displays real-time train departure information with integrated weather forecasting and astronomical events, featuring a sleek dark theme interface with automatic refresh capabilities.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🖼️ Screenshots
<img width="1098" height="1230" alt="image" src="https://github.com/user-attachments/assets/207e67b4-f8a4-4748-a01e-31f406686553" />
<img width="896" height="862" alt="image" src="https://github.com/user-attachments/assets/a53fe595-726e-45d8-80ea-a8df73de1006" />
<img width="900" height="858" alt="image" src="https://github.com/user-attachments/assets/8896a74d-1d1e-4176-a655-a44eb89162d4" />
<img width="746" height="581" alt="image" src="https://github.com/user-attachments/assets/44733ce2-4b23-4b27-8ec4-823a160bc281" />

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Transport API account (free tier available)
- NASA API key (completely free, 1000 requests/hour)

### Installation
```bash
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py  # On Windows: python main.py
```

### Building Executable
```bash
python build.py
```

## 📚 Documentation

### Core Documentation
- **[📦 Installation Guide](docs/INSTALLATION.md)** - Detailed installation instructions for all platforms
- **[⚙️ Configuration](docs/CONFIGURATION.md)** - API setup and configuration options
- **[✨ Features](docs/FEATURES.md)** - Complete feature overview and UI guide
- **[🐛 Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Technical Documentation
- **[🔧 Development Guide](docs/DEVELOPMENT.md)** - Development setup, testing, and building
- **[🏗️ Architecture](docs/ARCHITECTURE.md)** - System architecture and design patterns

## ✨ Key Features

### 🚂 Train Information
- Real-time departures with 16-hour window
- Platform numbers, delays, cancellations
- Automatic refresh every 30 minutes

### 🌤️ Weather Integration
- Real-time weather and 7-day forecast
- Location-based data using Open-Meteo API
- No API key required for weather

### 🌟 Astronomy Features
- NASA Astronomy Picture of the Day
- ISS tracking and pass predictions
- Near-Earth objects and space events
- Interactive 7-day astronomy forecast
- Moon phases and astronomical calculations

### 🎨 User Interface
- Light/Dark theme switching (Ctrl+T)
- Custom train icon and Unicode indicators
- Responsive design with accessibility support

## 🏗️ Architecture

The application follows a clean, layered Object-Oriented architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  MainWindow, TrainWidgets, WeatherWidget, AstronomyWidget   │
├─────────────────────────────────────────────────────────────┤
│                 Business Logic Layer                        │
│  TrainManager, WeatherManager, AstronomyManager             │
├─────────────────────────────────────────────────────────────┤
│                  Data Access Layer                          │
│  APIManager, WeatherAPIManager, NASAAPIManager              │
├─────────────────────────────────────────────────────────────┤
│                    Data Models                              │
│  TrainData, WeatherData, AstronomyData, AstronomyEvent      │
├─────────────────────────────────────────────────────────────┤
│                  External Services                          │
│  Transport API, Open-Meteo API, NASA APIs (4 services)     │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
trainer/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── config.json                      # Configuration file
├── README.md                        # This file
├── version.py                       # Version and metadata
├── build.py                         # Build script for executable
├── docs/                            # Documentation
│   ├── INSTALLATION.md              # Installation guide
│   ├── CONFIGURATION.md             # Configuration guide
│   ├── FEATURES.md                  # Features overview
│   ├── DEVELOPMENT.md               # Development guide
│   ├── TROUBLESHOOTING.md           # Troubleshooting guide
│   └── ARCHITECTURE.md              # System architecture
├── assets/                          # Application assets
│   ├── train_icon.svg               # SVG train icon
│   └── train_icon_*.png             # PNG icons (multiple sizes)
├── src/                             # Source code
│   ├── models/                      # Data models
│   ├── api/                         # API integration
│   ├── ui/                          # User interface
│   ├── managers/                    # Business logic
│   └── utils/                       # Utility functions
├── tests/                           # Comprehensive test suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   └── fixtures/                    # Test data
└── licenses/                        # License files
```

## 📊 API Integration

- **Transport API** - Real-time UK train departure data
- **Open-Meteo API** - Weather forecasting (no API key required)
- **NASA APIs** - Astronomy data (APOD, ISS, NeoWs, EPIC)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Oliver Ernster** - *Initial work and development*

## 🙏 Acknowledgments

- [Transport API](https://www.transportapi.com/) for UK transport data
- [Open-Meteo](https://open-meteo.com/) for free weather data
- [NASA](https://api.nasa.gov/) for space and astronomy data
- [PySide6](https://doc.qt.io/qtforpython/) for Qt Python bindings

---

**Ready to track your trains in style! 🚂✨**

For detailed information, see the [documentation](docs/) directory.
