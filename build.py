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
    print("🚂 Checking dependencies...")

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
    print("🚂 Cleaning previous builds...")

    # Remove previous build artifacts including onefile build dirs
    build_dirs = ["build", "dist"]
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
    print("🚂 Creating LGPL3 license files for PySide6 compliance...")

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
    print("🚂 Building executable with Nuitka...")

    # Create LGPL license files first
    create_lgpl_license_files()
    
    # Create a helper module for accessing embedded data files
    print("  🔧 Creating helper module for embedded data access...")
    helper_module = Path("src/data/embedded_access.py")
    with open(helper_module, "w", encoding="utf-8") as f:
        f.write("""
# Automatically generated module to help access embedded data files
import os
import sys
import json
from pathlib import Path
import importlib.resources as pkg_resources

def get_json_data(json_path):
    '''
    Access JSON data that works both in development and when embedded in executable.
    
    Args:
        json_path: Path to JSON file relative to project root (e.g., "src/data/some_file.json")
    
    Returns:
        Parsed JSON data
    '''
    # Method 1: Direct file access (works in development)
    try:
        if Path(json_path).exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
        
    # Method 2: Check in data directory relative to executable (for clean dist structure)
    try:
        exe_dir = os.path.dirname(sys.executable)
        
        # If the path starts with src/data, adjust for our clean structure
        if json_path.startswith('src/data/'):
            # Handle paths like src/data/file.json -> data/file.json
            clean_path = json_path.replace('src/data/', 'data/')
            
            # Special case for lines directory
            if 'lines/' in clean_path:
                data_path = os.path.join(exe_dir, clean_path)
            else:
                data_path = os.path.join(exe_dir, clean_path)
                
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
    except Exception as e:
        print(f"Error accessing data in clean structure: {e}")
        
    # Method 3: Package resource access (works when embedded)
    try:
        # Convert path to package path format
        if json_path.startswith('src/data/'):
            # Handle src/data/* paths
            resource_path = json_path.replace('src/data/', '')
            package = 'src.data'
            
            # Special case for lines directory
            if resource_path.startswith('lines/'):
                line_file = resource_path.replace('lines/', '')
                with pkg_resources.open_text('src.data.lines', line_file) as f:
                    return json.load(f)
            
            # Root data directory files
            with pkg_resources.open_text(package, resource_path) as f:
                return json.load(f)
    except Exception as e:
        print(f"Error accessing embedded resource {json_path}: {e}")
        
    # Method 4: Last resort - try other paths relative to executable
    try:
        # Try original path
        base_dir = os.path.dirname(sys.executable)
        alt_path = os.path.join(base_dir, json_path)
        if os.path.exists(alt_path):
            with open(alt_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        # Try just the filename
        filename = os.path.basename(json_path)
        filename_path = os.path.join(base_dir, 'data', filename)
        if os.path.exists(filename_path):
            with open(filename_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error in fallback data access: {e}")
        
    raise FileNotFoundError(f"Could not access JSON data: {json_path}")
""")
    print(f"  ✅ Created embedded data access helper: {helper_module}")
    
    # Make sure the lines directory is a proper package
    lines_init = Path("src/data/lines/__init__.py")
    if not lines_init.exists():
        lines_init.parent.mkdir(exist_ok=True)
        with open(lines_init, "w", encoding="utf-8") as f:
            f.write('"""Lines package for railway line JSON data."""\n')
        print(f"  ✅ Created lines package: {lines_init}")

    # Use the emoji-based train icon file
    icon_file = "assets/train_emoji.ico"
    if Path(icon_file).exists():
        print(f"  🚂 Using emoji-based train icon: {icon_file}")
    else:
        print("  🚂 Creating emoji-based train icon...")
        # Create the emoji icon if it doesn't exist
        result = subprocess.run(["python", "create_emoji_icon.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ Created emoji icon: {icon_file}")
        else:
            print("  ⚠️ Failed to create emoji icon, building without icon")
            icon_file = None

    # Build Nuitka command based on how nuitka was found
    if nuitka_command == "python -m nuitka":
        nuitka_cmd = ["python", "-m", "nuitka"]
    else:
        nuitka_cmd = ["nuitka"]

    # Add Nuitka options for onefile build with clean directory structure
    nuitka_options = [
        "--onefile",  # Create single executable file
        "--enable-plugin=pyside6",  # Enable PySide6 plugin
        "--windows-console-mode=disable",  # Hide console window on Windows
        "--output-filename=trainer.exe",  # Name the executable trainer.exe
        "--assume-yes-for-downloads",  # Auto-download dependencies
        "--follow-imports",  # Follow imports automatically
        "--include-package=src",  # Include entire src package
        "--include-module=src",  # Include top-level src module
        
        # Include data files - we need these to be accessible
        "--include-data-dir=src/data=src/data",  # Include all JSON data files
        
        # Include assets directory for icons
        "--include-data-dir=assets=assets",
        
        # Ensure PySide6 components are included
        "--include-package=PySide6",
        
        # Application metadata
        f"--company-name={__company__}",
        f"--product-name={__app_name__}",
        f"--file-version={__version__}",
        f"--product-version={__version__}",
        f"--file-description={__description__}",
        f"--copyright={__copyright__}",
    ]

    nuitka_cmd.extend(nuitka_options)

    # Add emoji icon if available
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
    """Create a clean distribution with only essential files in root."""
    print("🚂 Creating clean distribution in dist...")

    # Create a clean dist directory
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Find the executable - search in various possible locations
    exe_found = False
    possible_locations = [
        Path("trainer.exe"),
        Path("main.exe"),
        Path("./__pycache__/trainer.exe"),
        Path("./dist/trainer.exe"),
        Path("./build/trainer.exe"),
        Path("./main.onefile-build/trainer.exe"),
        Path("./main.dist/trainer.exe")
    ]
    
    exe_path = None
    for possible_exe in possible_locations:
        if possible_exe.exists():
            exe_path = possible_exe
            dest_exe = dist_dir / "trainer.exe"
            shutil.copy2(exe_path, dest_exe)
            print(f"  Copied {exe_path} → {dest_exe}")
            exe_found = True
            break
    
    if not exe_found:
        # Try a more general search
        print("  Searching for executable...")
        for exe_file in Path(".").glob("**/*.exe"):
            if "trainer" in exe_file.name.lower() or "main" in exe_file.name.lower():
                exe_path = exe_file
                dest_exe = dist_dir / "trainer.exe"
                shutil.copy2(exe_path, dest_exe)
                print(f"  Found and copied {exe_path} → {dest_exe}")
                exe_found = True
                break
    
    if not exe_found:
        print("  ❌ Executable not found in any location")
        return False
    
    # Create data directory and copy JSON files
    data_dir = dist_dir / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Copy data files from source
    src_data = Path("src/data")
    if src_data.exists():
        # Create lines subdirectory
        (data_dir / "lines").mkdir(exist_ok=True)
        
        # Copy main JSON files
        for json_file in src_data.glob("*.json"):
            shutil.copy2(json_file, data_dir / json_file.name)
            print(f"  Copied {json_file} → {data_dir / json_file.name}")
        
        # Copy lines directory JSON files
        lines_src = src_data / "lines"
        if lines_src.exists():
            for json_file in lines_src.glob("*.json"):
                if not json_file.name.endswith(".backup"):  # Skip backup files
                    shutil.copy2(json_file, data_dir / "lines" / json_file.name)
                    print(f"  Copied {json_file} → {data_dir / 'lines' / json_file.name}")
    
    # Copy license files to the root
    for license_file in ["LGPL-3.0.txt", "THIRD_PARTY_LICENSES.txt"]:
        src_license = Path("licenses") / license_file
        if src_license.exists():
            dest_license = dist_dir / license_file
            shutil.copy2(src_license, dest_license)
            print(f"  Copied {src_license} → {dest_license}")
    
    # Copy train emoji icon to the root
    icon_file = Path("assets/train_emoji.ico")
    if icon_file.exists():
        dest_icon = dist_dir / "train_emoji.ico"
        shutil.copy2(icon_file, dest_icon)
        print(f"  Copied {icon_file} → {dest_icon}")
    
    # Count files in each directory for verification
    exe_count = len(list(dist_dir.glob("*.exe")))
    license_count = len(list(dist_dir.glob("*.txt")))
    json_count = len(list(data_dir.rglob("*.json")))
    
    print("\n  ✅ Final directory structure:")
    print(f"  📁 Root: {exe_count} executable, {license_count} license files, 1 icon")
    print(f"  📁 data/: {json_count} JSON files")
    
    return True


def verify_build():
    """Verify the built executable exists and get its size."""
    # Look for the executable in various possible locations
    possible_locations = [
        Path("trainer.exe"),
        Path("main.exe"),
        Path("./__pycache__/trainer.exe"),
        Path("./dist/trainer.exe"),
        Path("./build/trainer.exe"),
        Path("./main.onefile-build/trainer.exe"),
        Path("./main.dist/trainer.exe")
    ]
    
    exe_path = None
    for possible_exe in possible_locations:
        if possible_exe.exists():
            exe_path = possible_exe
            break
    
    if not exe_path:
        # Try a more general search
        print("Searching for executable...")
        for exe_file in Path(".").glob("**/*.exe"):
            if "trainer" in exe_file.name.lower() or "main" in exe_file.name.lower():
                exe_path = exe_file
                print(f"  Found executable at: {exe_path}")
                break
    
    if exe_path and exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ Executable found: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Location: {exe_path.absolute()}")

        # Create clean distribution with only essential files
        if create_clean_distribution():
            print("✅ Clean distribution created in dist/")

            # List top-level contents of dist
            dist_dir = Path("dist")
            print("  Top-level contents:")
            for item in dist_dir.glob("*"):
                if item.is_file():
                    size_mb = item.stat().st_size / (1024 * 1024)
                    print(f"    {item.name} ({size_mb:.1f} MB)")
                else:
                    # Count files in subdirectories
                    file_count = len(list(item.rglob("*.*")))
                    print(f"    {item.name}/ ({file_count} files)")
                    
            # Clean up build artifacts in root directory
            print("\n🧹 Cleaning up build artifacts...")
            cleaned_files = 0
            
            # Remove any leftover .pyd files in root
            for pyd_file in Path(".").glob("*.pyd"):
                pyd_file.unlink()
                cleaned_files += 1
                
            # Remove any leftover .dll files in root
            for dll_file in Path(".").glob("*.dll"):
                dll_file.unlink()
                cleaned_files += 1
                
            # Clean up Nuitka cache if present
            build_dirs = [Path("main.build"), Path("main.dist"), Path("main.onefile-build")]
            for build_dir in build_dirs:
                if build_dir.exists() and build_dir.is_dir():
                    shutil.rmtree(build_dir)
                    print(f"  Cleaned up {build_dir}")
                
            if cleaned_files > 0:
                print(f"  Removed {cleaned_files} build artifact files from root directory")
            else:
                print("  No build artifacts found to clean")

        return True
    else:
        print("❌ Executable not found in any location")
        return False


def create_verification_file():
    """Create a verification file to help with debugging data access."""
    print("🚂 Creating data access verification file...")
    
    # Create a file in the data directory to verify the executable can find it
    data_dir = Path("dist/data")
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    
    verify_file = data_dir / "verify_data_access.json"
    with open(verify_file, "w", encoding="utf-8") as f:
        import datetime
        f.write('{"verification": "Data directory is accessible", "timestamp": "' +
                datetime.datetime.now().isoformat() + '"}')
    
    print(f"  ✅ Created verification file: {verify_file}")


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
        
    # Create verification file for data access testing
    create_verification_file()

    print("\n🎉 Build completed successfully!")
    print("\nClean distribution created in dist/ with minimal structure:")
    print("- trainer.exe (single executable with all dependencies bundled inside)")
    print("- LGPL-3.0.txt and THIRD_PARTY_LICENSES.txt (license files in root)")
    print("- train_emoji.ico (application icon in root)")
    print("- data/ (subdirectory with all JSON railway data)")
    
    # Check if emoji icon was copied to distribution
    dist_dir = Path("dist")
    emoji_icon_files = list(dist_dir.glob("**/train_emoji.ico"))
    if emoji_icon_files:
        print(f"- {emoji_icon_files[0].name} (train icon for shortcuts)")
    
    # Verify data files
    data_dir = dist_dir / "data"
    if data_dir.exists():
        json_count = len(list(data_dir.rglob("*.json")))
        lines_count = len(list((data_dir / 'lines').glob('*.json'))) if (data_dir / 'lines').exists() else 0
        index_count = len(list(data_dir.glob('railway_lines_*.json')))
        
        print(f"\n📊 Data directory contents:")
        print(f"  📄 {json_count} total JSON files")
        print(f"  🚂 {lines_count} railway line definitions in data/lines/")
        print(f"  📋 {index_count} railway index files")
        
    print("\nNext steps:")
    print("1. Test the executable: dist/trainer.exe")
    print("2. Distribute the entire dist/ folder")
    
    print("\n✨ The application is now packaged with a clean, minimal directory structure!")
    print("   The executable is a single file with all dependencies bundled inside it")
    print("   No external DLLs or .pyd files are needed - everything is in the executable")


if __name__ == "__main__":
    main()
