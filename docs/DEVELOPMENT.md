# 🔧 Development Guide

## Recent Updates

- **Fixed broken test cases** (December 2024): Updated test expectations to match recent changes:
  - Configuration defaults: refresh interval changed from 2 to 30 minutes, time window from 10 to 16 hours
  - UI sizing: astronomy widget icon sizes and panel heights adjusted for better display
  - Train emoji: removed from window title but kept in executable icon
  - Splash screen: simplified to use emoji directly instead of external icon files


## Project Structure

```
trainer/
├── src/                    # Main application source code
│   ├── managers/          # Data and configuration managers
│   ├── models/            # Data models and schemas
│   ├── ui/                # PySide6 user interface components
│   └── utils/             # Utility functions and helpers
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data and fixtures
├── docs/                  # Documentation
├── assets/                # Application assets (icons, etc.)
├── licenses/              # Third-party licenses
├── requirements.txt       # All dependencies (runtime + development)
├── pytest.ini           # Test configuration
├── build.py              # Nuitka build script
├── main.py               # Application entry point
└── version.py            # Version information
```

## Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd trainer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup development tools
pre-commit install

# 4. Run tests to verify setup
pytest -m unit

# 5. Run the application
python main.py

# 6. Build executable (optional)
python build.py
```

## Setting up Development Environment

```bash
# Install all dependencies (includes development tools)
pip install -r requirements.txt

# Setup pre-commit hooks
pre-commit install

# Run code formatting
black src/
flake8 src/

# Type checking
mypy src/
```

### Development Dependencies

The project includes all development dependencies in [`requirements.txt`](../requirements.txt):

**Code Quality & Formatting:**
- [`black`](../requirements.txt:6) - Code formatter
- [`flake8`](../requirements.txt:20) - Linting and style checking
- [`mypy`](../requirements.txt:30) - Static type checking
- [`pre-commit`](../requirements.txt:41) - Git hooks for code quality

**Testing Framework:**
- [`pytest`](../requirements.txt:54) - Testing framework
- [`pytest-asyncio`](../requirements.txt:55) - Async testing support
- [`pytest-benchmark`](../requirements.txt:56) - Performance testing
- [`pytest-cov`](../requirements.txt:57) - Coverage reporting
- [`pytest-mock`](../requirements.txt:58) - Mocking utilities
- [`pytest-qt`](../requirements.txt:59) - PySide6 UI testing
- [`pytest-xvfb`](../requirements.txt:60) - Headless display for UI tests
- [`coverage`](../requirements.txt:15) - Code coverage analysis

**Build Tools:**
- [`Nuitka`](../requirements.txt:33) - Python compiler for standalone executables

**Performance & Profiling:**
- [`memory-profiler`](../requirements.txt:28) - Memory usage profiling
- [`psutil`](../requirements.txt:43) - System and process utilities
- [`py-cpuinfo`](../requirements.txt:44) - CPU information

**Testing Utilities:**
- [`freezegun`](../requirements.txt:21) - Time mocking for tests
- [`responses`](../requirements.txt:65) - HTTP request mocking
- [`PyVirtualDisplay`](../requirements.txt:62) - Virtual display for headless testing

## 🧪 Testing

### Running Tests

```bash
# Run all tests with coverage (default configuration)
pytest

# Run all tests with verbose output and coverage report
python -m pytest tests/ -v --cov

# Run specific test categories using markers
pytest -m unit          # Fast unit tests only
pytest -m integration   # Integration tests
pytest -m ui            # UI tests (requires PySide6)
pytest -m api           # Tests requiring real API access

# Run specific test file
pytest tests/unit/test_train_data.py

# Run tests by directory
pytest tests/unit/
pytest tests/integration/

# Performance and benchmarking
pytest -m performance
pytest -m slow

# Generate detailed coverage report
pytest --cov-report=html
```

**Current Test Coverage: 95.8%**

The test suite provides comprehensive coverage across all major components including configuration management, UI widgets, data models, and API integrations.

### Test Categories & Markers

The project uses pytest markers defined in [`pytest.ini`](../pytest.ini:14-23):

- **`unit`** - Fast unit tests with no external dependencies
- **`integration`** - Integration tests (may be slow, real components)
- **`ui`** - User interface testing with pytest-qt
- **`performance`** - Performance benchmarking tests
- **`api`** - Tests requiring real API access
- **`slow`** - Tests that may take several seconds
- **`astronomy`** - NASA astronomy integration tests
- **`weather`** - Weather system tests
- **`combined`** - Combined weather/astronomy tests

### Coverage Reporting

Coverage is automatically generated with each test run:
- **Terminal**: Coverage summary displayed after tests
- **HTML**: Detailed report in [`htmlcov/`](../htmlcov/) directory
- **XML**: Machine-readable report in [`coverage.xml`](../coverage.xml)

## Build and Deployment

### Building Standalone Executable

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

Nuitka is included in [`requirements.txt`](../requirements.txt:33), so no separate installation is needed:

```bash
# All build dependencies are included in requirements.txt
pip install -r requirements.txt
```

**Platform-specific compiler requirements:**
- **Windows**: Visual Studio Build Tools or Visual Studio Community
- **Linux**: gcc/g++ compiler toolchain (`sudo apt install build-essential` on Ubuntu)
- **macOS**: Xcode Command Line Tools (`xcode-select --install`)

**Advanced Build Options:**
```bash
# Debug build with console output
python build.py --debug

# Build with specific Python optimization
python build.py --optimize

# Clean build (removes previous build artifacts)
python build.py --clean
```

### Distribution

The built executable is completely portable and includes:
- ✅ All Python dependencies
- ✅ Application assets and icons
- ✅ Configuration templates
- ✅ No Python installation required
- ✅ Single file deployment

## Development Workflow

1. **Phase 1**: Core infrastructure and data models ✅
2. **Phase 2**: API integration and data processing ✅
3. **Phase 3**: UI foundation and dark theme ✅
4. **Phase 4**: Business logic and update system ✅
5. **Phase 5**: Integration, testing, and polish ✅
6. **Phase 6**: Astronomy integration and NASA APIs ✅

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for detailed technical documentation.

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