# 🔧 Development Guide

## Setting up Development Environment

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