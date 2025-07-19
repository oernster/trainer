# 🚂 Trainer - Train Times with Weather Integration & Astronomical Events

**Author: Oliver Ernster**

### If you like it please buy me a coffee: [Donation link](https://www.paypal.com/ncp/payment/7XYN6DCYK24VY)

A modern PySide6 desktop application that displays real-time train departure information with integrated weather forecasting and astronomical events, featuring a sleek dark theme interface with automatic refresh capabilities. Built with a robust object-oriented architecture following SOLID principles and modern design patterns.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Architecture](https://img.shields.io/badge/architecture-SOLID%20OOP-brightgreen.svg)

## 🖼️ Screenshots
<img width="1098" height="1230" alt="image" src="https://github.com/user-attachments/assets/207e67b4-f8a4-4748-a01e-31f406686553" />
<img width="896" height="862" alt="image" src="https://github.com/user-attachments/assets/a53fe595-726e-45d8-80ea-a8df73de1006" />
<img width="895" height="853" alt="image" src="https://github.com/user-attachments/assets/141d3def-2efd-479d-90cd-01b9d2eedc05" />
<img width="745" height="581" alt="image" src="https://github.com/user-attachments/assets/06b6e1f3-49da-41ea-9fc6-af7a7e48df8b" />

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher

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
- **[🏗️ Architecture Overview](docs/architecture.md)** - Complete system architecture with Mermaid diagrams
- **[🖥️ UI Architecture](docs/ui-architecture.md)** - User interface design and manager patterns
- **[⚙️ Service Architecture](docs/service-architecture.md)** - Business logic and service layer design
- **[🧩 Widget System](docs/widget-system.md)** - Widget hierarchy and component relationships
- **[🔄 Data Flow](docs/data-flow.md)** - Information flow through the application
- **[🎨 Design Patterns](docs/design-patterns.md)** - Implemented patterns and their usage
- **[🌐 API Integration](docs/api-integration.md)** - External service integration patterns

## ✨ Key Features

### 🚂 Train Information
- **Real-time Departures**: Live train data with 16-hour window
- **Comprehensive Details**: Platform numbers, delays, cancellations, operators
- **Route Planning**: Advanced route calculation with interchange support
- **Journey Details**: Detailed calling points and service information
- **Smart Filtering**: Configurable preferences for route optimization
- **Automatic Refresh**: Intelligent refresh with configurable intervals

### 🌤️ Weather Integration
- **Real-time Weather**: Current conditions with detailed metrics
- **7-Day Forecast**: Extended weather predictions
- **Location-based Data**: Automatic location detection using Open-Meteo API
- **Weather Alerts**: Severe weather notifications and warnings
- **No API Key Required**: Free weather data integration
- **Responsive Updates**: Automatic weather refresh with error handling

### 🌟 Astronomy Features
- **Astronomy Picture of the Day**: Daily astronomical images with full metadata
- **ISS Tracking**: Real-time International Space Station tracking
- **Space Events**: Near-Earth objects and astronomical events
- **Interactive Forecast**: 7-day astronomy event calendar
- **Moon Phases**: Detailed lunar phase calculations
- **Celestial Objects**: Visible planets and deep-sky objects
- **Educational Links**: Direct links to astronomical resources and explanations

### 🎨 User Interface
- **Modern Design**: Clean, responsive interface with accessibility support
- **Theme System**: Light/Dark theme switching with consistent styling
- **Manager Architecture**: Modular UI management with specialized managers
- **Responsive Layout**: Adaptive design for different screen sizes
- **Custom Widgets**: Specialized components for optimal user experience
- **Keyboard Shortcuts**: Full keyboard navigation support (Ctrl+T for theme, F5 for refresh)

### 🔧 Technical Excellence
- **Object-Oriented Design**: SOLID principles implementation throughout
- **Service-Oriented Architecture**: Clean separation of concerns
- **Design Patterns**: Factory, Observer, Strategy, Manager, and Service Layer patterns
- **Error Handling**: Comprehensive error management with graceful degradation
- **Performance Optimization**: Efficient caching, lazy loading, and resource management
- **Extensible Architecture**: Plugin-ready design for future enhancements

## 🏗️ Architecture

The application follows a modern, layered Object-Oriented architecture with SOLID principles:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  MainWindow, UI Managers, Widget System, Theme Management  │
├─────────────────────────────────────────────────────────────┤
│                 Application Layer                           │
│  UI Layout Manager, Widget Lifecycle, Event Handlers       │
├─────────────────────────────────────────────────────────────┤
│                 Business Logic Layer                        │
│  Train Manager, Weather Manager, Astronomy Manager         │
├─────────────────────────────────────────────────────────────┤
│                  Service Layer                              │
│  Route Calculation, Train Data, Configuration, Timetable   │
├─────────────────────────────────────────────────────────────┤
│                  Data Access Layer                          │
│  API Services, Cache Management, Error Handling            │
├─────────────────────────────────────────────────────────────┤
│                    Data Models                              │
│  TrainData, WeatherData, AstronomyData, Configuration      │
├─────────────────────────────────────────────────────────────┤
│                  External Services                          │
│  Open-Meteo API, Astronomy APIs (4 services)               │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Improvements

- **Manager Pattern**: UI responsibilities delegated to specialized managers
- **Service Layer**: Business logic encapsulated in focused service classes
- **Widget System**: Modular, reusable UI components with consistent theming
- **SOLID Compliance**: Single responsibility, dependency injection, interface segregation
- **Design Patterns**: Factory, Observer, Strategy, Facade, and Command patterns
- **Error Resilience**: Multi-level error handling with fallback strategies

## 📁 Project Structure

```
trainer/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── config.json                      # Configuration file
├── README.md                        # This file
├── version.py                       # Version and metadata
├── build.py                         # Build script for executable
├── REFACTORING_DOCUMENTATION.md    # Complete refactoring overview
├── docs/                            # Comprehensive documentation
│   ├── architecture.md              # Main architecture overview
│   ├── ui-architecture.md           # UI design and managers
│   ├── service-architecture.md      # Service layer design
│   ├── widget-system.md             # Widget components
│   ├── data-flow.md                 # Data flow patterns
│   ├── design-patterns.md           # Design pattern usage
│   ├── api-integration.md           # API integration patterns
│   ├── INSTALLATION.md              # Installation guide
│   ├── CONFIGURATION.md             # Configuration guide
│   ├── FEATURES.md                  # Features overview
│   ├── DEVELOPMENT.md               # Development guide
│   ├── TROUBLESHOOTING.md           # Troubleshooting guide
│   └── ARCHITECTURE.md              # Legacy architecture doc
├── assets/                          # Application assets
│   ├── train_icon.svg               # SVG train icon
│   └── train_icon_*.png             # PNG icons (multiple sizes)
├── src/                             # Source code
│   ├── models/                      # Data models and entities
│   ├── api/                         # API integration services
│   ├── ui/                          # User interface components
│   │   ├── managers/                # UI management classes
│   │   │   ├── ui_layout_manager.py         # Layout and widget management
│   │   │   ├── widget_lifecycle_manager.py  # Widget lifecycle
│   │   │   ├── event_handler_manager.py     # Event handling
│   │   │   └── settings_dialog_manager.py   # Settings management
│   │   ├── widgets/                 # Modular widget system
│   │   │   ├── train_widgets_base.py        # Base widget classes
│   │   │   ├── custom_scroll_bar.py         # Custom scrollbar
│   │   │   ├── train_item_widget.py         # Individual train display
│   │   │   ├── train_list_widget.py         # Train list container
│   │   │   ├── route_display_dialog.py      # Route details dialog
│   │   │   └── empty_state_widget.py        # Empty state display
│   │   ├── components/              # Reusable UI components
│   │   ├── handlers/                # Event and interaction handlers
│   │   └── state/                   # UI state management
│   ├── managers/                    # Business logic managers
│   │   ├── services/                # Service layer implementation
│   │   │   ├── route_calculation_service.py # Route finding logic
│   │   │   ├── train_data_service.py        # Train data processing
│   │   │   ├── configuration_service.py     # Configuration management
│   │   │   └── timetable_service.py         # Timetable operations
│   │   └── train_manager.py         # Main train coordination
│   ├── core/                        # Core application services
│   │   ├── interfaces/              # Abstract interfaces
│   │   ├── models/                  # Core data models
│   │   └── services/                # Core services
│   ├── cache/                       # Caching implementation
│   ├── services/                    # External service integrations
│   ├── utils/                       # Utility functions
│   └── workers/                     # Background processing
├── tests/                           # Comprehensive test suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   └── fixtures/                    # Test data
└── licenses/                        # License files
```

## 📊 API Integration

### Integrated Services
- **Open-Meteo API** - Weather forecasting with alerts (no API key required)
- **Astronomy APIs** - Multi-service astronomy integration:
  - **APOD** - Astronomy Picture of the Day
  - **ISS** - International Space Station tracking
  - **NeoWs** - Near-Earth Object Web Service
  - **EPIC** - Earth Polychromatic Imaging Camera

### API Features
- **Rate Limiting** - Intelligent request throttling and backoff strategies
- **Caching** - Multi-level caching with TTL and dependency invalidation
- **Error Handling** - Comprehensive error recovery with fallback data
- **Performance** - Request batching, connection pooling, and response optimization
- **Security** - Secure API key management and request validation

## 🔧 Development Features

### Code Quality
- **SOLID Principles** - Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Design Patterns** - Factory, Observer, Strategy, Manager, Service Layer, Adapter, Decorator patterns
- **Clean Architecture** - Clear separation of concerns with defined layer boundaries
- **Dependency Injection** - Loose coupling through constructor injection
- **Error Handling** - Comprehensive error management with graceful degradation

### Performance Optimizations
- **Lazy Loading** - Components loaded on demand for faster startup
- **Widget Pooling** - Efficient widget reuse for smooth scrolling
- **Caching Strategy** - Multi-level caching with intelligent invalidation
- **Memory Management** - Proper resource cleanup and lifecycle management
- **Responsive Design** - Adaptive layouts for different screen sizes

### Testing & Maintainability
- **Modular Design** - All files under 600 lines for better maintainability
- **Unit Testing** - Comprehensive test coverage with mockable dependencies
- **Integration Testing** - End-to-end testing of component interactions
- **Documentation** - Complete architectural documentation with visual diagrams
- **Extensibility** - Plugin-ready architecture for future enhancements

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Oliver Ernster** - *Author/Developer*

## 🙏 Acknowledgments

- [Open-Meteo](https://open-meteo.com/) for free weather data
- [PySide6](https://doc.qt.io/qtforpython/) for Qt Python bindings
- Various astronomy data providers for space and celestial information

---

**Ready to track your trains in style with modern architecture! 🚂✨**

For detailed technical information, see the comprehensive [documentation](docs/) directory with visual architecture diagrams and implementation details.
