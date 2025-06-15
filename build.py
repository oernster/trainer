#!/usr/bin/env python3
"""
Build script for Trainer application using Nuitka.
Author: Oliver Ernster

This script creates a standalone executable with proper icon integration
and all necessary dependencies bundled using the --onefile option.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from version import (
    __version__,
    __app_name__,
    __company__,
    __copyright__,
    __description__,
)


def check_nuitka():
    """Check if Nuitka is installed."""
    # Try nuitka command first
    try:
        result = subprocess.run(
            ["nuitka", "--version"], capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            print(f"✅ Nuitka found: {result.stdout.strip()}")
            return "nuitka"
    except FileNotFoundError:
        pass

    # Try python -m nuitka (common in virtual environments)
    try:
        result = subprocess.run(
            ["python", "-m", "nuitka", "--version"],
            capture_output=True,
            text=True,
            shell=True,
        )
        if result.returncode == 0:
            print(f"✅ Nuitka found via python -m: {result.stdout.strip()}")
            return "python -m nuitka"
    except FileNotFoundError:
        pass

    print("❌ Nuitka not found. Please install with: pip install nuitka")
    return None


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("🔍 Checking dependencies...")

    # Map package names to their import names
    required_packages = {
        "PySide6": "PySide6",
        "requests": "requests",
        "aiohttp": "aiohttp",
        "python-dateutil": "dateutil",
        "pydantic": "pydantic",
        "imageio": "imageio",
    }

    missing_packages = []

    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name}")
            missing_packages.append(package_name)

    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install with: pip install -r requirements.txt")
        return False

    print("✅ All dependencies found")
    return True


def prepare_build_directory():
    """Prepare build directory and clean previous builds."""
    print("🧹 Cleaning previous builds...")

    # Remove previous build artifacts including onefile build dirs
    build_dirs = ["build", "dist", "main.dist", "main.build", "main.onefile-build"]
    for build_dir in build_dirs:
        if Path(build_dir).exists():
            shutil.rmtree(build_dir)
            print(f"  Removed {build_dir}")

    # Remove previous executable
    exe_files = ["trainer.exe", "Trainer.exe", "main.exe", "train_times.exe"]
    for exe_file in exe_files:
        if Path(exe_file).exists():
            os.remove(exe_file)
            print(f"  Removed {exe_file}")

    # Clean any leftover .pyd files in root
    for pyd_file in Path(".").glob("*.pyd"):
        pyd_file.unlink()
        print(f"  Removed {pyd_file}")

    # Clean any leftover .dll files in root
    for dll_file in Path(".").glob("*.dll"):
        dll_file.unlink()
        print(f"  Removed {dll_file}")


def create_lgpl_license_files():
    """Create LGPL3 license files for PySide6 compliance."""
    print("📄 Creating LGPL3 license files for PySide6 compliance...")

    # Create licenses directory
    licenses_dir = Path("licenses")
    licenses_dir.mkdir(exist_ok=True)

    # Create LGPL3 license file
    lgpl3_file = licenses_dir / "LGPL-3.0.txt"
    with open(lgpl3_file, "w", encoding="utf-8") as f:
        f.write(
            """GNU LESSER GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

This application uses PySide6, which is licensed under the LGPL v3.
The full text of the LGPL v3 license can be found at:
https://www.gnu.org/licenses/lgpl-3.0.html

PySide6 source code is available at:
https://code.qt.io/cgit/pyside/pyside-setup.git/

For LGPL compliance, this application provides the following:
1. This license notice
2. Information about PySide6 usage
3. Links to obtain PySide6 source code

If you wish to obtain the source code for PySide6 or modify it,
please visit the official PySide6 repository.
"""
        )

    # Create third-party licenses file
    third_party_file = licenses_dir / "THIRD_PARTY_LICENSES.txt"
    with open(third_party_file, "w", encoding="utf-8") as f:
        f.write(
            f"""{__app_name__} Third-Party Licenses

This application includes the following third-party components:

1. PySide6 (Qt for Python)
   License: LGPL v3
   Website: https://www.qt.io/qt-for-python
   Source: https://code.qt.io/cgit/pyside/pyside-setup.git/

2. Python Standard Library
   License: Python Software Foundation License
   Website: https://www.python.org/

3. Other dependencies as listed in requirements.txt
   Please check individual package licenses for details.

For complete license texts, see the licenses/ directory.
"""
        )

    print(f"  Created {lgpl3_file}")
    print(f"  Created {third_party_file}")


def build_executable(nuitka_command):
    """Build the executable using Nuitka with --onefile option."""
    print("🔨 Building executable with Nuitka...")

    # Create LGPL license files first
    create_lgpl_license_files()

    # Determine the best icon file to use
    icon_file = None
    icon_candidates = [
        "assets/train_icon_32.png",  # PNG for Windows compatibility
        "assets/train_icon.ico",  # ICO if available
        "assets/train_icon.svg",  # SVG fallback
    ]

    for candidate in icon_candidates:
        if Path(candidate).exists():
            icon_file = candidate
            print(f"  Using icon: {icon_file}")
            break

    if not icon_file:
        print("  ⚠️ No icon file found, building without icon")

    # Build Nuitka command based on how nuitka was found
    if nuitka_command == "python -m nuitka":
        nuitka_cmd = ["python", "-m", "nuitka"]
    else:
        nuitka_cmd = ["nuitka"]

    # Add Nuitka options for proper onefile build
    nuitka_options = [
        "--onefile",  # Create single executable file
        "--enable-plugin=pyside6",  # Enable PySide6 plugin
        "--windows-console-mode=disable",  # Hide console window on Windows
        "--output-filename=trainer.exe",  # Custom executable name
        "--follow-imports",  # Follow all imports automatically
        "--assume-yes-for-downloads",  # Auto-download dependencies
        f"--company-name={__company__}",
        f"--product-name={__app_name__}",
        f"--file-version={__version__}",
        f"--product-version={__version__}",
        f"--file-description={__description__}",
        f"--copyright={__copyright__}",
    ]

    nuitka_cmd.extend(nuitka_options)

    # Add icon if available
    if icon_file:
        nuitka_cmd.append(f"--windows-icon-from-ico={icon_file}")

    # Add main script
    nuitka_cmd.append("main.py")

    print(f"  Command: {' '.join(nuitka_cmd)}")
    print("  This may take several minutes...")

    try:
        # Run Nuitka build with live output
        print("  Starting Nuitka build...")
        result = subprocess.run(nuitka_cmd, shell=True)

        if result.returncode == 0:
            print("✅ Build completed successfully!")
            return True
        else:
            print(f"❌ Build failed with error code {result.returncode}")
            return False

    except Exception as e:
        print(f"❌ Build failed with exception: {e}")
        return False


def create_clean_distribution():
    """Create a clean main.dist directory with only exe, licenses, and icon."""
    print("📦 Creating clean distribution in main.dist...")

    # Create main.dist directory
    dist_dir = Path("main.dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(exist_ok=True)

    # Find and copy the executable
    exe_found = False
    for exe_name in ["trainer.exe", "main.exe"]:
        exe_path = Path(exe_name)
        if exe_path.exists():
            dest_exe = dist_dir / "trainer.exe"
            shutil.copy2(exe_path, dest_exe)
            print(f"  Copied {exe_path} → {dest_exe}")
            exe_found = True
            break

    if not exe_found:
        print("  ❌ No executable found to copy")
        return False

    # Copy license files
    licenses_src = Path("licenses")
    if licenses_src.exists():
        licenses_dest = dist_dir / "licenses"
        shutil.copytree(licenses_src, licenses_dest)
        print(f"  Copied {licenses_src} → {licenses_dest}")

    # Copy icon file
    icon_candidates = [
        "assets/train_icon.ico",
        "assets/train_icon_32.png",
        "assets/train_icon.svg",
    ]

    for icon_path in icon_candidates:
        icon_src = Path(icon_path)
        if icon_src.exists():
            icon_dest = dist_dir / icon_src.name
            shutil.copy2(icon_src, icon_dest)
            print(f"  Copied {icon_src} → {icon_dest}")
            break

    return True


def verify_build():
    """Verify the built executable exists and get its size."""
    # First check if exe exists in root
    exe_path = Path("trainer.exe")
    if not exe_path.exists():
        exe_path = Path("main.exe")

    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ Executable created: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Location: {exe_path.absolute()}")

        # Create clean distribution
        if create_clean_distribution():
            print("✅ Clean distribution created in main.dist/")

            # List contents of main.dist
            dist_dir = Path("main.dist")
            print("  Contents:")
            for item in sorted(dist_dir.rglob("*")):
                if item.is_file():
                    size_mb = item.stat().st_size / (1024 * 1024)
                    print(f"    {item.relative_to(dist_dir)} ({size_mb:.1f} MB)")

        return True
    else:
        print("❌ Executable not found after build")
        return False


def main():
    """Main build process."""
    print(f"🚂 {__app_name__} - Nuitka Build Script")
    print("=" * 50)

    # Check prerequisites
    nuitka_command = check_nuitka()
    if not nuitka_command:
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    # Prepare for build
    prepare_build_directory()

    # Build executable
    if not build_executable(nuitka_command):
        print("\n❌ Build failed. Please check the error messages above.")
        sys.exit(1)

    # Verify build
    if not verify_build():
        print("\n❌ Executable not created. Build may have failed silently.")
        sys.exit(1)

    print("\n🎉 Build completed successfully!")
    print("\nDistribution created in main.dist/ containing:")
    print("- trainer.exe (single executable)")
    print("- licenses/ (LGPL3 compliance files)")
    print("- train_icon.ico (application icon)")
    print("\nNext steps:")
    print("1. Test the executable: main.dist/trainer.exe")
    print("2. Distribute the entire main.dist/ folder")
    print("\nNote: The executable is self-contained with all dependencies.")


if __name__ == "__main__":
    main()
