# 📦 Installation Guide

## Prerequisites

- Python 3.8 or higher
- Transport API account (free tier available)
- NASA API key (completely free, 1000 requests/hour)

## 🖥️ Platform-Specific Installation

### 🐧 Linux Distributions

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update

# Install Python 3 and pip
sudo apt install python3 python3-pip python3-venv git

# Clone and setup
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
python3 main.py
```

#### Fedora
```bash
# Install Python 3 and pip
sudo dnf install python3 python3-pip python3-virtualenv git

# Clone and setup
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
python3 main.py
```

#### RHEL/CentOS/Rocky Linux
```bash
# Enable EPEL repository (if not already enabled)
sudo dnf install epel-release

# Install Python 3 and pip
sudo dnf install python3 python3-pip python3-virtualenv git

# Clone and setup
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
python3 main.py
```

#### openSUSE
```bash
# Install Python 3 and pip
sudo zypper install python3 python3-pip python3-virtualenv git

# Clone and setup
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
python3 main.py
```

#### Void Linux
```bash
# Install Python 3 and pip
sudo xbps-install -S python3 python3-pip python3-virtualenv git

# Clone and setup
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
python3 main.py
```

### 🍎 macOS

#### Using Homebrew (Recommended)
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3
brew install python3 git

# Clone and setup
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
python3 main.py
```

#### Using macOS System Python
```bash
# macOS comes with Python 3 pre-installed (macOS 12.3+)
# Install pip if needed
python3 -m ensurepip --upgrade

# Clone and setup
git clone <repository-url>
cd trainer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the application
python3 main.py
```

### 🪟 Windows

#### Using Python.org Installer
```powershell
# Download and install Python from python.org
# Make sure to check "Add Python to PATH" during installation

# Clone and setup
git clone <repository-url>
cd trainer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run the application
python main.py
```

### Universal Installation (All Platforms)

Once you have Python 3.8+ installed:

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd trainer
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python3 main.py  # On Windows: python main.py
   ```

## 📦 Building Executable

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