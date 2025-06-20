"""
Installation and setup script for Trainer train times application.

This script helps set up the application environment and dependencies.
"""

import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False

    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is compatible")
    return True


def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")

    try:
        # Install main dependencies
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("✅ Main dependencies installed successfully")

        # Ask about development dependencies
        install_dev = (
            input("\n🔧 Install development dependencies? (y/N): ").lower().strip()
        )
        if install_dev in ["y", "yes"]:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"]
            )
            print("✅ Development dependencies installed successfully")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_configuration():
    """Setup configuration file."""
    print("\n⚙️ Setting up configuration...")

    config_path = Path("config.json")
    if config_path.exists():
        print("✅ Configuration file already exists")
        return True

    # Config file should already exist from our creation
    if config_path.exists():
        print("✅ Default configuration file created")
        print("\n📝 Next steps for configuration:")
        print(
            "1. Get Transport API credentials from https://developer.transportapi.com/"
        )
        print("2. Edit config.json and replace YOUR_APP_ID_HERE and YOUR_APP_KEY_HERE")
        print("3. Optionally adjust other settings like refresh interval and theme")
        return True
    else:
        print("❌ Configuration file not found")
        return False


def check_assets():
    """Check if assets directory exists."""
    print("\n🎨 Checking assets...")

    assets_path = Path("assets")
    if not assets_path.exists():
        assets_path.mkdir()
        print("✅ Created assets directory")

    # Note: Application now uses Unicode train emoji (🚂) as primary icon
    # Icon files are only needed for building standalone executables
    icon_path = assets_path / "train_icon.svg"
    if icon_path.exists():
        print("✅ Train icon found (for executable builds)")
    else:
        print("ℹ️ No train icon file - application uses Unicode emoji (🚂)")

    return True


def run_basic_test():
    """Run basic structure test."""
    print("\n🧪 Running basic tests...")

    try:
        # Test without Qt dependencies
        result = subprocess.run(
            [sys.executable, "test_basic.py"], capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ Basic tests passed")
            return True
        else:
            print("❌ Basic tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False


def main():
    """Main installation process."""
    print("🚂 Trainer train times application - Installation")
    print("=" * 60)

    # Check Python version
    if not check_python_version():
        return 1

    # Install dependencies
    if not install_dependencies():
        return 1

    # Setup configuration
    if not setup_configuration():
        return 1

    # Check assets
    if not check_assets():
        return 1

    # Run basic tests
    if not run_basic_test():
        print("\n⚠️ Basic tests failed, but installation may still work")

    print("\n" + "=" * 60)
    print("🎉 Installation completed!")
    print("\n📋 Next steps:")
    print("1. Configure API credentials in config.json")
    print("2. Run the application: python main.py")
    print("3. Or run tests: python test_basic.py")

    print("\n📚 Documentation:")
    print("- Architecture: docs/ARCHITECTURE.md")
    print("- API Integration: docs/API_INTEGRATION.md")
    print("- UI Design: docs/UI_DESIGN.md")
    print("- Implementation: docs/IMPLEMENTATION.md")
    print("- Testing: docs/TESTING_STRATEGY.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
