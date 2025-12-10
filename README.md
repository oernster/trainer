# Trainer - Train Times with Weather Integration & Astronomical Events

**Author: Oliver Ernster**

### If you like it please buy me a coffee: [Donation link](https://www.paypal.com/ncp/payment/7XYN6DCYK24VY)

A modern PySide6 desktop application that displays real-time train departure information with integrated weather forecasting and astronomical events. Features include a dark theme, automatic refresh, and a clean architecture following SOLID principles and modern design patterns.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Architecture](https://img.shields.io/badge/architecture-SOLID%20OOP-brightgreen.svg)

## Screenshots
<img width="1098" height="1230" src="https://github.com/user-attachments/assets/207e67b4-f8a4-4748-a01e-31f406686553" />
<img width="896" height="862" src="https://github.com/user-attachments/assets/a53fe595-726e-45d8-80ea-a8df73de1006" />
<img width="895" height="853" src="https://github.com/user-attachments/assets/141d3def-2efd-479d-90cd-01b9d2eedc05" />
<img width="745" height="581" src="https://github.com/user-attachments/assets/06b6e1f3-49da-41ea-9fc6-af7a7e48df8b" />

## Quick Start

### Prerequisites
- Python 3.8 or higher

### Installation
```bash
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py  # Windows: python main.py
```

### Building Executable
```bash
python build.py
```

## Documentation

### Core Documentation
- **Installation Guide** (docs/INSTALLATION.md)
- **Configuration** (docs/CONFIGURATION.md)
- **Features** (docs/FEATURES.md)
- **Troubleshooting** (docs/TROUBLESHOOTING.md)

### Technical Documentation
- **Development Guide** (docs/DEVELOPMENT.md)
- **Architecture Overview** (docs/architecture.md)
- **UI Architecture** (docs/ui-architecture.md)
- **Service Architecture** (docs/service-architecture.md)
- **Widget System** (docs/widget-system.md)
- **Data Flow** (docs/data-flow.md)
- **Design Patterns** (docs/design-patterns.md)
- **API Integration** (docs/api-integration.md)

## Key Features

### Train Information
- Real-time departures with a 16-hour window
- Platform numbers, delays, cancellations, and operator info
- Route planning with interchange support
- Calling points and full service details
- Smart route filtering
- Automatic refresh with configurable intervals

### Weather Integration
- Real-time conditions with detailed metrics
- Seven-day forecast
- Automatic location detection via Open-Meteo
- Weather alerts and warnings
- No API key required
- Automatic refresh with error handling

### Astronomy Features
- Astronomy Picture of the Day with metadata
- ISS real-time tracking
- Space and astronomical events
- Seven-day astronomy calendar
- Moon phases and celestial object visibility
- Educational resource links

### User Interface
- Clean, responsive design with accessibility support
- Light/Dark theme switching
- Modular manager-based architecture
- Adaptive layout for different screen sizes
- Custom widgets for optimal usability
- Keyboard shortcuts (Ctrl+T for theme, F5 for refresh)

### Technical Excellence
- SOLID object-oriented architecture
- Service-oriented design with clear separation of concerns
- Design patterns including Factory, Observer, Strategy, Manager
- Robust error handling with graceful fallbacks
- Optimized performance via caching and lazy loading
- Extensible architecture for future plugins

## Architecture

The application follows a layered, SOLID-compliant architecture:

```
Presentation Layer       - MainWindow, UI Managers, Widget System
Application Layer        - UI Layout, Widget Lifecycle, Event Handlers
Business Logic Layer     - Train, Weather, Astronomy Managers
Service Layer            - Route Calculation, Train Data, Config, Timetable
Data Access Layer        - API Services, Cache, Error Handling
Data Models              - TrainData, WeatherData, AstronomyData, Configuration
External Services        - Open-Meteo, Astronomy APIs
```

### Key Architectural Improvements
- Manager Pattern for UI responsibilities
- Encapsulated business logic via service classes
- Modular widget system with consistent theming
- SOLID-compliant layering and design
- Use of Factory, Observer, Strategy, Facade, and Command patterns
- Multi-level error handling with fallback mechanisms

## Project Structure

```
trainer/
├── main.py
├── requirements.txt
├── config.json
├── README.md
├── version.py
├── build.py
├── REFACTORING_DOCUMENTATION.md
├── docs/
│   ├── architecture.md
│   ├── ui-architecture.md
│   ├── service-architecture.md
│   ├── widget-system.md
│   ├── data-flow.md
│   ├── design-patterns.md
│   ├── api-integration.md
│   ├── INSTALLATION.md
│   ├── CONFIGURATION.md
│   ├── FEATURES.md
│   ├── DEVELOPMENT.md
│   ├── TROUBLESHOOTING.md
│   └── ARCHITECTURE.md
├── assets/
│   ├── train_icon.svg
│   └── train_icon_*.png
├── src/
│   ├── models/
│   ├── api/
│   ├── ui/
│   │   ├── managers/
│   │   ├── widgets/
│   │   ├── components/
│   │   ├── handlers/
│   │   └── state/
│   ├── managers/
│   ├── core/
│   ├── cache/
│   ├── services/
│   ├── utils/
│   └── workers/
├── tests/
└── licenses/
```

## API Integration

### Integrated Services
- Open-Meteo API
- Astronomy APIs:
  - APOD
  - ISS
  - NeoWs
  - EPIC

### API Features
- Rate limiting with backoff
- Multi-level caching and invalidation
- Robust error recovery
- Request batching and connection pooling
- Secure key handling

## Development Features

### Code Quality
- SOLID design
- Design patterns throughout
- Clean architecture separation
- Dependency injection
- Detailed error handling

### Performance
- Lazy loading
- Widget pooling
- Intelligent caching
- Memory-efficient resource management
- Responsive layouts

### Testing & Maintainability
- Modular design
- Unit and integration tests
- Complete documentation with diagrams
- Plugin-ready extensibility

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Author

**Oliver Ernster**

## Acknowledgments

- Open-Meteo for weather data
- PySide6 for Qt Python bindings
- Astronomy data providers

---

For full technical details, see the documentation directory.
