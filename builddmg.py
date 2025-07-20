#!/usr/bin/env python3
"""
Script to create a drag-to-install DMG installer for the Trainer app.
This creates a user-friendly DMG with a background image that instructs
users to drag the app to the Applications folder, and applies the Trainer
icon to the DMG file.

This version removes encryption and obfuscation for better maintainability
and adds support for PySide6 instead of PyQt5.
"""

import os
import sys
import shutil
import subprocess
import traceback
import tempfile
import time
from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple


class CommandRunner:
    """Utility class for running shell commands with proper error handling."""

    @staticmethod
    def run_command(command, cwd=None, show_output=True):
        """
        Run a shell command and handle errors with detailed output.

        Args:
            command (List[str]): Command to run
            cwd (str, optional): Working directory
            show_output (bool): Whether to show command output

        Returns:
            Tuple[bool, str]: (Success, Output/Error message)
        """
        command_str = " ".join(str(item) for item in command)
        print(f"Executing: {command_str}")

        try:
            result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)

            # Print standard output
            if show_output and result.stdout:
                print(f"Command output: {result.stdout}")

            # Check for errors
            if result.returncode != 0:
                print(f"Error executing command: {command_str}")
                print(f"Error output: {result.stderr}")
                return False, result.stderr

            return True, result.stdout
        except Exception as e:
            print(f"Exception running command '{command_str}': {str(e)}")
            traceback.print_exc()
            return False, None


class ProcessTerminator:
    """Responsible for terminating running instances of the application."""

    @staticmethod
    def terminate_running_instances(app_name: str = "Trainer") -> bool:
        """
        Terminate any running instances of the application on macOS.

        Args:
            app_name (str): Application name to look for

        Returns:
            bool: True if successful or no instances found, False if error
        """
        print(f"Checking for running instances of {app_name}...")

        try:
            # Check if the process is running
            result = subprocess.run(
                ["pgrep", "-f", app_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            if result.returncode == 0:
                print(f"Found running instances of {app_name}")
                # Kill the process
                subprocess.call(["pkill", "-f", app_name])
                print(f"Terminated {app_name} processes.")
                time.sleep(1)  # Give some time for processes to terminate
            else:
                print(f"No running instances of {app_name} found.")

            return True
        except Exception as e:
            print(f"Error terminating processes: {str(e)}")
            # Return True to continue with the build even if process termination fails
            return True


class BuildCleaner:
    """Handles cleaning of previous build artifacts."""

    @staticmethod
    def clear_builds() -> None:
        """Clear previous builds, cache, and temporary files."""
        # Remove directories
        for directory in ["build", "dist", "__pycache__", "temp_dmg", "staging_dmg"]:
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory)
                    print(f"Removed directory: {directory}")
                except PermissionError:
                    print(
                        f"Permission denied when removing {directory}. Continuing anyway."
                    )
                except Exception as e:
                    print(f"Error removing {directory}: {str(e)}. Continuing anyway.")

        # Remove temporary files
        for temp_file in ["dmg_background.png", "dmg_background.txt", "trainer.dmg"]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"Removed temporary file: {temp_file}")
                except PermissionError:
                    print(
                        f"Permission denied when removing {temp_file}. Continuing anyway."
                    )
                except Exception as e:
                    print(f"Error removing {temp_file}: {str(e)}. Continuing anyway.")


class BackgroundImageCreator:
    """Creates a professional Chrome-background image for the DMG."""

    @staticmethod
    def create_background_image() -> bool:
        """
        Create a Chrome-background image for the DMG with proper layout.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageFilter

            # Create a larger canvas for more space
            width, height = 640, 400

            # Use a light gradient background
            background = Image.new("RGB", (width, height), color=(245, 245, 245))

            # Create a drawing object
            draw = ImageDraw.Draw(background)

            # Try to use system fonts, or fall back to default
            try:
                # Title text - try to use San Francisco (macOS system font) or fallbacks
                title_font = ImageFont.truetype(
                    "/System/Library/Fonts/SFNSDisplay.ttf", 24
                )
            except:
                try:
                    title_font = ImageFont.truetype("/Library/Fonts/Arial Bold.ttf", 24)
                except:
                    title_font = ImageFont.load_default()

            try:
                # Regular text
                regular_font = ImageFont.truetype(
                    "/System/Library/Fonts/SFNSText.ttf", 14
                )
            except:
                try:
                    regular_font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 14)
                except:
                    regular_font = ImageFont.load_default()

            try:
                # Bold text for emphasis
                bold_font = ImageFont.truetype(
                    "/System/Library/Fonts/SFNSTextBold.ttf", 14
                )
            except:
                try:
                    bold_font = ImageFont.truetype("/Library/Fonts/Arial Bold.ttf", 14)
                except:
                    bold_font = ImageFont.load_default()

            # Add a subtle gradient
            for y in range(height):
                # Create a subtle gradient from top to bottom
                color_value = int(245 - (y / height) * 15)
                draw.line(
                    [(0, y), (width, y)], fill=(color_value, color_value, color_value)
                )

            # Add title at the top
            title = "Install Trainer"
            title_width = draw.textlength(title, font=title_font)
            draw.text(
                ((width - title_width) / 2, 40),
                title,
                fill=(50, 50, 50),
                font=title_font,
            )

            # Calculate positions for application and Applications folder icons
            # These positions are just placeholders - the actual positioning will be done in the AppleScript
            app_x, folder_x = 120, 520
            icon_y = 180  # vertical position of both icons

            # Add an arrow pointing from app to Applications folder
            arrow_color = (0, 122, 255)  # Apple's blue color
            arrow_width = 4

            # Draw line with plenty of space
            arrow_start_x = app_x + 80  # Give space after the app icon
            arrow_end_x = folder_x - 80  # Give space bethe folder icon

            # Draw arrow line
            draw.line(
                [(arrow_start_x, icon_y), (arrow_end_x, icon_y)],
                fill=arrow_color,
                width=arrow_width,
            )

            # Draw arrowhead
            arrowhead_size = 12
            draw.polygon(
                [
                    (arrow_end_x - arrowhead_size, icon_y - arrowhead_size),
                    (arrow_end_x, icon_y),
                    (arrow_end_x - arrowhead_size, icon_y + arrowhead_size),
                ],
                fill=arrow_color,
            )

            # Add instruction text at the bottom with better wording
            instruction1 = "To install Trainer, drag it to the Applications folder."
            instruction2 = "After installation, you can eject this disk image."

            # Calculate position to center text
            instr1_width = draw.textlength(instruction1, font=bold_font)
            instr2_width = draw.textlength(instruction2, font=regular_font)

            # Draw instructions
            draw.text(
                ((width - instr1_width) / 2, height - 80),
                instruction1,
                fill=(50, 50, 50),
                font=bold_font,
            )

            draw.text(
                ((width - instr2_width) / 2, height - 50),
                instruction2,
                fill=(80, 80, 80),
                font=regular_font,
            )

            # Apply a slight blur to soften the background
            background = background.filter(ImageFilter.GaussianBlur(radius=0.5))

            # Save the image
            background.save("dmg_background.png")
            print("Successfully created Chrome-background image")
            return True
        except Exception as e:
            print(f"Error creating background image: {str(e)}")
            traceback.print_exc()

            # Fall back to text file method
            try:
                with open("dmg_background.txt", "w") as f:
                    f.write(
                        """
                    =================================
                    
                            INSTALL TRAINER
                    
                    ---------------------------------
                    
                    To install Trainer, drag it to the Applications folder.
                    After installation, you can eject this disk image.
                    
                    =================================
                    """
                    )
                print("Created text background (fallback method)")
                return True
            except Exception as e:
                print(f"Error creating backup text background: {str(e)}")

            return False


class LauncherScriptGenerator:
    """Generates the launcher script for the macOS app."""

    @staticmethod
    def create_launcher_script(
        macos_path: Path, app_name: str, resources_path: Path
    ) -> bool:
        """
        Create a robust launcher script that uses system Python.

        Args:
            macos_path: Path to the MacOS directory in the app bundle
            app_name: Name of the application
            resources_path: Path to the Resources directory

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            launcher_path = macos_path / app_name
            print(f"Creating launcher script at: {launcher_path}")

            with open(launcher_path, "w") as f:
                f.write(
                    f"""#!/bin/bash
# Trainer launcher script that uses Python inside the app bundle

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
APP_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"
SITE_PACKAGES_DIR="$RESOURCES_DIR/site-packages"
PYTHON_BIN_DIR="$RESOURCES_DIR/python_bin"

# Create log file for troubleshooting
LOG_FILE="/tmp/trainer_launch.log"
exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3
exec 1>$LOG_FILE 2>&1

# Log system info
echo "==============================================="
echo "Trainer Launcher - $(date)"
echo "==============================================="
echo "Script directory: $SCRIPT_DIR"
echo "App root: $APP_ROOT"
echo "Resources directory: $RESOURCES_DIR"
echo "Site packages directory: $SITE_PACKAGES_DIR"
echo "Python directory: $PYTHON_BIN_DIR"
echo "Current directory: $(pwd)"
echo "macOS version: $(sw_vers -productVersion)"

# Check if this is the first run from a DMG
if [[ "$APP_ROOT" == *"/Volumes/"* ]]; then
    echo "Running from DMG, showing dialog to user"
    osascript <<EOF
    tell application "Finder"
        activate
        display dialog "Please drag Trainer to your Applications folder before running it." buttons {{"OK"}} default button 1 with icon stop with title "Trainer"
    end tell
EOF
    exit 1
fi

# Skip bundled Python (has library loading issues) and use system Python directly
echo "Using system Python (bundled Python has library dependencies issues)"
SYSTEM_PYTHON=$(command -v python3)
if [ -z "$SYSTEM_PYTHON" ]; then
    # Try to find Python 3 in common locations
    for p in /usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
        if [ -x "$p" ]; then
            SYSTEM_PYTHON="$p"
            break
        fi
    done
fi

if [ -n "$SYSTEM_PYTHON" ]; then
    echo "Using system Python: $SYSTEM_PYTHON"
    PYTHON_EXEC="$SYSTEM_PYTHON"
else
    echo "No Python 3 found on system"
    osascript <<EOF
    tell application "Finder"
        activate
        display dialog "Error: Trainer requires Python 3, but no Python 3 was found on your system. Please install Python 3 from python.org and try again." buttons {{"OK"}} default button 1 with icon stop with title "Trainer Error"
    end tell
EOF
    exit 1
fi

# Set up environment variables - prioritize our bundled packages
export PYTHONPATH="$SITE_PACKAGES_DIR:$RESOURCES_DIR"
echo "PYTHONPATH: $PYTHONPATH"

# List available packages for debugging
echo "Listing available Python packages in site-packages:"
ls -la "$SITE_PACKAGES_DIR"

# Check required packages before executing the main script
REQUIRED_PACKAGES=("PySide6")
MISSING_PACKAGES=()

for pkg in "${{REQUIRED_PACKAGES[@]}}"; do
    echo "Checking for package: $pkg"
    if ! arch -arm64 "$PYTHON_EXEC" -c "import $pkg" 2>/dev/null; then
        echo "Required package '$pkg' not found"
        MISSING_PACKAGES+=("$pkg")
    else
        echo "Package '$pkg' found"
    fi
done

# Check for train application modules
echo "Checking for train application modules..."
if ! arch -arm64 "$PYTHON_EXEC" -c "
import sys
sys.path.insert(0, '$SITE_PACKAGES_DIR')
sys.path.insert(0, '$RESOURCES_DIR')
from src.managers.train_manager import TrainManager
from src.ui.main_window import MainWindow
print('Train application modules loaded successfully')
"; then
    echo "ERROR: Train application modules not found or not importable"
    MISSING_PACKAGES+=("train_modules")
else
    echo "✅ Train application modules found and importable"
fi

# If any packages are missing, show an error
if [ "${{#MISSING_PACKAGES[@]}}" -gt 0 ]; then
    MISSING_LIST=$(IFS=", "; echo "${{MISSING_PACKAGES[*]}}")
    echo "ERROR: Missing required packages: $MISSING_LIST"
    osascript <<EOF
    tell application "Finder"
        activate
        display dialog "Error: Trainer requires the following Python packages: $MISSING_LIST. The application may be damaged or incompletely installed." buttons {{"OK"}} default button 1 with icon stop with title "Trainer Error"
    end tell
EOF
    exit 1
fi

# Check if the main script exists
MAIN_SCRIPT="$RESOURCES_DIR/main.py"
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "ERROR: Main script not found at $MAIN_SCRIPT"
    # List directory contents for debugging
    echo "Resources directory contents:"
    ls -la "$RESOURCES_DIR"
    
    # Show error dialog
    osascript <<EOF
    tell application "Finder"
        activate
        display dialog "Error: Main application script not found. The application may be corrupted." buttons {{"OK"}} default button 1 with icon stop with title "Trainer Error"
    end tell
EOF
    exit 1
fi

# Make main.py executable
chmod +x "$MAIN_SCRIPT"
echo "Made main script executable: $MAIN_SCRIPT"

# Run the application with our Python in ARM64 mode
echo "Launching application with command: arch -arm64 $PYTHON_EXEC $MAIN_SCRIPT $@"
cd "$RESOURCES_DIR"  # Change to Resources directory for proper imports
arch -arm64 "$PYTHON_EXEC" "$MAIN_SCRIPT" "$@"

# Check exit status
EXIT_CODE=$?
echo "Application exited with code: $EXIT_CODE"

if [ $EXIT_CODE -ne 0 ]; then
    echo "Application encountered an error"
    osascript <<EOF
    tell application "Finder"
        activate
        display dialog "Trainer encountered an error. See log file at $LOG_FILE for details." buttons {{"OK", "Show Log"}} default button 1 with icon stop with title "Trainer Error"
    set button_pressed to button returned of the result
    if button_pressed is "Show Log" then
        do shell script "open -a TextEdit $LOG_FILE"
    end if
    end tell
EOF
fi

exit $EXIT_CODE
"""
                )

            # Make launcher executable
            os.chmod(launcher_path, 0o755)
            print(f"Launcher script created successfully at: {launcher_path}")
            return True
        except Exception as e:
            print(f"Error creating launcher script: {str(e)}")
            traceback.print_exc()
            return False


class IconConverter:
    """Handles conversion of icons for the app bundle."""

    @staticmethod
    def convert_png_to_icns(source_path: Path, app_bundle_path: Path) -> bool:
        """
        Convert PNG to ICNS for the app bundle.

        Args:
            source_path: Path to the source directory with the PNG
            app_bundle_path: Path to the app bundle

        Returns:
            bool: True if successful, False otherwise
        """
        icon_dir = app_bundle_path / "icon.iconset"
        resources_path = app_bundle_path / "Contents" / "Resources"

        try:
            # Create iconset directory
            icon_dir.mkdir(parents=True, exist_ok=True)

            # Check if source ICO exists first, then try to convert it to PNG
            ico_path = source_path / "assets" / "train_emoji.ico"
            icon_path = source_path / "assets" / "train_emoji.png"
            
            if not os.path.exists(ico_path):
                print(f"Error: train_emoji.ico not found at {ico_path}")
                return False
            
            # Convert ICO to PNG if PNG doesn't exist
            if not os.path.exists(icon_path):
                print(f"Converting {ico_path} to {icon_path}")
                try:
                    from PIL import Image
                    with Image.open(ico_path) as img:
                        # Get the largest size from the ICO file
                        img.save(icon_path, "PNG")
                        print(f"Successfully converted ICO to PNG: {icon_path}")
                except Exception as e:
                    print(f"Error converting ICO to PNG: {e}")
                    return False

            # Create various icon sizes
            sizes = [16, 32, 128, 256, 512]
            for size in sizes:
                # Check if sips command is available
                success, _ = CommandRunner.run_command(["which", "sips"])
                if not success:
                    print(
                        "ERROR: 'sips' command not found. This script requires macOS and its built-in tools."
                    )
                    return False

                # Create normal and retina (2x) versions
                for scale in [1, 2]:
                    output_size = size * scale
                    output_name = (
                        f"icon_{size}x{size}" + ("@2x" if scale == 2 else "") + ".png"
                    )
                    success, _ = CommandRunner.run_command(
                        [
                            "sips",
                            "-z",
                            str(output_size),
                            str(output_size),
                            str(icon_path),
                            "--out",
                            str(icon_dir / output_name),
                        ]
                    )
                    if not success:
                        print(f"Error creating icon size {output_size}x{output_size}")
                        return False

            # Check if iconutil command is available
            success, _ = CommandRunner.run_command(["which", "iconutil"])
            if not success:
                print(
                    "ERROR: 'iconutil' command not found. This script requires macOS and its built-in tools."
                )
                return False

            # Convert the iconset to icns
            os.makedirs(resources_path, exist_ok=True)
            success, _ = CommandRunner.run_command(
                [
                    "iconutil",
                    "-c",
                    "icns",
                    str(icon_dir),
                    "-o",
                    str(resources_path / "trainer.icns"),
                ]
            )
            if not success:
                print("Error converting iconset to icns file")
                return False

            # Clean up the temporary iconset
            shutil.rmtree(icon_dir)
            print("Icon conversion completed successfully.")
            return True
        except Exception as e:
            print(f"Error during icon conversion: {str(e)}")
            traceback.print_exc()
            return False


class DMGIconSetter:
    """Sets the icon for the DMG file."""

    @staticmethod
    def set_dmg_icon(dmg_path: str, icon_path: str) -> bool:
        """
        Set the icon for the DMG file using multiple methods for reliability.

        Args:
            dmg_path: Path to the DMG file
            icon_path: Path to the icon file

        Returns:
            bool: True if successful, False otherwise
        """
        # Method 1: Try fileicon command (most reliable)
        print(f"Setting icon using fileicon: {dmg_path} with {icon_path}")

        # Check if fileicon is installed
        success, _ = CommandRunner.run_command(["which", "fileicon"])
        if not success:
            print("fileicon not found, installing with brew...")
            CommandRunner.run_command(["brew", "install", "fileicon"])
            success, _ = CommandRunner.run_command(["which", "fileicon"])

        # Try setting icon with fileicon if available
        if success:
            success, output = CommandRunner.run_command(
                ["fileicon", "set", dmg_path, icon_path]
            )
            if success:
                print("Successfully set icon using fileicon")
                return True
            else:
                print(f"fileicon failed: {output}")

        # Method 2: Try using AppleScript
        print("Trying AppleScript method...")
        try:
            # First ensure the icon file is in the right format (PNG)
            png_path = icon_path
            if not png_path.lower().endswith(".png"):
                # If it's an ICNS file, try to convert it
                if png_path.lower().endswith(".icns"):
                    temp_png = os.path.join(tempfile.gettempdir(), "temp_icon.png")
                    CommandRunner.run_command(
                        ["sips", "-s", "format", "png", png_path, "--out", temp_png]
                    )
                    png_path = temp_png

            # Create AppleScript to set icon
            script = f"""
            tell application "Finder"
                set theFile to POSIX file "{dmg_path}"
                set theIcon to POSIX file "{png_path}"
                tell application "Finder" to set icon of file theFile to data of file theIcon
            end tell
            """

            # Write script to temp file
            script_path = os.path.join(tempfile.gettempdir(), "set_icon.scpt")
            with open(script_path, "w") as f:
                f.write(script)

            # Run the script
            success, output = CommandRunner.run_command(["osascript", script_path])
            if success:
                print("Successfully set icon using AppleScript")
                # Clean up
                try:
                    os.remove(script_path)
                except:
                    pass
                return True
            else:
                print(f"AppleScript method failed: {output}")
        except Exception as e:
            print(f"Error with AppleScript method: {str(e)}")

        print("All icon setting methods failed")
        return False


class PackageManager:
    """Manages Python package installation and copying."""

    @staticmethod
    def install_python_in_bundle(resources_path: Path) -> bool:
        """
        Install a minimal Python distribution in the app bundle.

        Args:
            resources_path: Path to the Resources directory

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            python_bin_dir = resources_path / "python_bin"
            os.makedirs(python_bin_dir, exist_ok=True)

            # Determine the current Python version
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            print(f"Current Python version: {python_version}")

            # Check if we're using the system Python
            using_system_python = sys.executable.startswith(
                "/usr/bin/"
            ) or sys.executable.startswith("/usr/local/bin/")

            if using_system_python:
                print("Using system Python - creating a symlink instead of copying")
                # Create a symlink to the system Python
                os.symlink(sys.executable, python_bin_dir / "python3")
                print(f"Created symlink to system Python: {sys.executable}")
                return True

            # Copy the current Python executable
            python_exe = Path(sys.executable)
            if not python_exe.exists():
                print(f"Error: Python executable not found at {python_exe}")
                return False

            # Copy Python binary
            shutil.copy2(python_exe, python_bin_dir / "python3")
            os.chmod(python_bin_dir / "python3", 0o755)
            print(
                f"Copied Python executable from {python_exe} to {python_bin_dir / 'python3'}"
            )

            return True
        except Exception as e:
            print(f"Error installing Python in bundle: {str(e)}")
            traceback.print_exc()
            return False

    @staticmethod
    def copy_packages(resources_path: Path, site_packages_path: Path) -> bool:
        """
        Copy Python packages from requirements.txt to the app bundle using a more robust method.

        Args:
            resources_path: Path to the Resources directory
            site_packages_path: Path to the site-packages directory

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create site-packages directory
            site_packages_path.mkdir(parents=True, exist_ok=True)

            # Check if requirements.txt exists
            if not os.path.exists("requirements.txt"):
                print(
                    "Warning: requirements.txt not found. Skipping package installation."
                )
                return False

            print("Found requirements.txt - Installing packages...")

            # Create a temporary directory for requirements
            temp_dir = os.path.join(os.path.abspath("."), "temp_pip_packages")
            os.makedirs(temp_dir, exist_ok=True)

            # Install packages to the temporary directory
            print(f"Installing packages to temporary directory: {temp_dir}")
            success, _ = CommandRunner.run_command(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements.txt",
                    "--target",
                    temp_dir,
                    "--upgrade",
                    "--no-user",
                ]
            )

            if not success:
                print("Error: Failed to install packages from requirements.txt")
                return False

            # IMPROVED: Use a more thorough method for copying packages, preserving structure
            print(f"Copying packages from {temp_dir} to {site_packages_path}...")
            success = PackageManager._copy_directory_thoroughly(
                temp_dir, site_packages_path
            )

            if not success:
                print("Error: Failed to copy packages thoroughly")
                # Try direct pip installation as fallback
                print("Attempting direct pip installation to site-packages...")
                success, _ = CommandRunner.run_command(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        "requirements.txt",
                        "--target",
                        str(site_packages_path),
                        "--upgrade",
                        "--no-user",
                    ]
                )

                if not success:
                    print("Error: Direct pip installation failed")
                    return False

            # Create an empty __init__.py file in the site-packages directory
            with open(os.path.join(site_packages_path, "__init__.py"), "w") as f:
                f.write("# This file makes the directory a package\n")

            # Special handling for PySide6 modules
            try:
                print("Checking PySide6 modules...")
                pyside_path = os.path.join(site_packages_path, "PySide6")
                if os.path.exists(pyside_path):
                    # Ensure all required PySide6 binaries are properly copied
                    import PySide6

                    print(f"Found PySide6 at: {os.path.dirname(PySide6.__file__)}")

                    # PySide6 has multiple binary files we need to ensure are copied
                    pyside_dir = os.path.dirname(PySide6.__file__)

                    # Log the contents of PySide6 directory for debugging
                    print("PySide6 directory contents:")
                    for item in os.listdir(pyside_dir):
                        print(f"  - {item}")

                    # Make sure Qt plugins are copied (platforms, s, etc.)
                    plugins_dir = os.path.join(pyside_dir, "plugins")
                    if os.path.exists(plugins_dir):
                        dest_plugins_dir = os.path.join(pyside_path, "plugins")
                        os.makedirs(dest_plugins_dir, exist_ok=True)
                        print(
                            f"Copying Qt plugins from {plugins_dir} to {dest_plugins_dir}"
                        )
                        for item in os.listdir(plugins_dir):
                            item_path = os.path.join(plugins_dir, item)
                            dest_item_path = os.path.join(dest_plugins_dir, item)
                            if os.path.isdir(item_path):
                                shutil.copytree(
                                    item_path, dest_item_path, dirs_exist_ok=True
                                )
                            else:
                                shutil.copy2(item_path, dest_item_path)

                    # Make sure Qt resource files are copied (translations, etc.)
                    resources_dir = os.path.join(pyside_dir, "resources")
                    if os.path.exists(resources_dir):
                        dest_resources_dir = os.path.join(pyside_path, "resources")
                        os.makedirs(dest_resources_dir, exist_ok=True)
                        print(
                            f"Copying Qt resources from {resources_dir} to {dest_resources_dir}"
                        )
                        for item in os.listdir(resources_dir):
                            item_path = os.path.join(resources_dir, item)
                            dest_item_path = os.path.join(dest_resources_dir, item)
                            if os.path.isdir(item_path):
                                shutil.copytree(
                                    item_path, dest_item_path, dirs_exist_ok=True
                                )
                            else:
                                shutil.copy2(item_path, dest_item_path)

                    print("PySide6 modules have been processed")
                else:
                    print("PySide6 package not found in site-packages")
            except Exception as e:
                print(f"Warning: Error handling PySide6 modules: {str(e)}")
                traceback.print_exc()

            # Special handling for train application critical dependencies
            try:
                print("Ensuring train application dependencies...")
                critical_packages = ["dateutil", "requests", "pillow", "aiohttp"]
                for pkg_name in critical_packages:
                    # Handle different package directory names
                    pkg_dirs = [pkg_name, pkg_name.replace("-", "_")]
                    found = False
                    for pkg_dir in pkg_dirs:
                        pkg_path = os.path.join(site_packages_path, pkg_dir)
                        if os.path.exists(pkg_path):
                            print(f"✅ Found critical dependency: {pkg_name} (as {pkg_dir})")
                            found = True
                            break
                    if not found:
                        print(f"⚠️ Missing critical dependency: {pkg_name}")
                        
                # Validate train application modules are properly copied
                src_path = os.path.join(resources_path, "src")
                train_manager_path = os.path.join(src_path, "managers", "train_manager.py")
                main_window_path = os.path.join(src_path, "ui", "main_window.py")
                
                if os.path.exists(train_manager_path) and os.path.exists(main_window_path):
                    print("✅ Train application core modules properly copied")
                else:
                    print("⚠️ Train application core modules may be missing")
                    
            except Exception as e:
                print(f"Warning: Error checking train application dependencies: {str(e)}")
                traceback.print_exc()

            # Clean up temporary directory
            print("Cleaning up temporary pip packages directory...")
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory: {str(e)}")

            print("Python packages copied successfully with improved thorough method.")
            return True
        except Exception as e:
            print(f"Error copying packages: {str(e)}")
            traceback.print_exc()
            return False

    @staticmethod
    def _copy_directory_thoroughly(source_dir, dest_dir):
        """
        Copy a directory thoroughly, preserving structure and all files.

        Args:
            source_dir: Source directory
            dest_dir: Destination directory

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create the destination directory if it doesn't exist
            os.makedirs(dest_dir, exist_ok=True)

            # Walk through the source directory
            file_count = 0
            dir_count = 0

            for root, dirs, files in os.walk(source_dir):
                # Calculate the relative path
                rel_path = os.path.relpath(root, source_dir)
                target_dir = (
                    os.path.join(dest_dir, rel_path) if rel_path != "." else dest_dir
                )

                # Create target directory if it doesn't exist
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                    dir_count += 1

                # Copy all files (except cache files)
                for file in files:
                    if file.endswith(".pyc") or file.endswith(".pyo"):
                        continue

                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_dir, file)

                    # Copy the file
                    shutil.copy2(source_file, target_file)
                    file_count += 1

            print(f"Copied {file_count} files and {dir_count} directories")
            return True
        except Exception as e:
            print(f"Error in thorough directory copy: {str(e)}")
            traceback.print_exc()
            return False


class AppBundleBuilder:
    """Builds the app bundle with all required components."""

    def __init__(self, source_path: Path, temp_path: Path):
        """
        Initialize the app bundle builder.

        Args:
            source_path: Path to the source directory
            temp_path: Path to the temporary directory for building
        """
        self.source_path = source_path
        self.temp_path = temp_path
        self.app_name = "Trainer"
        self.app_bundle_path = temp_path / f"{self.app_name}.app"
        self.contents_path = self.app_bundle_path / "Contents"
        self.resources_path = self.contents_path / "Resources"
        self.macos_path = self.contents_path / "MacOS"
        self.frameworks_path = self.contents_path / "Frameworks"
        self.site_packages_path = self.resources_path / "site-packages"


    def check_required_files(self) -> bool:
        """
        Check that essential files exist for Trainer.

        Returns:
            bool: True if essential files exist, False otherwise
        """
        essential_files = [
            "main.py",
            "version.py",
            "requirements.txt",
            "src",
            "assets/train_emoji.ico"
        ]
        
        missing_files = []
        for file in essential_files:
            file_path = self.source_path / file
            if not file_path.exists():
                missing_files.append(file)

        if missing_files:
            print(f"ERROR: The following essential files are missing:")
            for file in missing_files:
                print(f"  - {file}")
            print(
                "\nPlease ensure all essential files are present in the current directory."
            )
            return False

        print("All essential files found in the current directory.")
        return True

    def create_app_structure(self) -> bool:
        """
        Create the basic app bundle structure.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create app bundle directories
            self.macos_path.mkdir(parents=True, exist_ok=True)
            self.resources_path.mkdir(parents=True, exist_ok=True)
            self.frameworks_path.mkdir(parents=True, exist_ok=True)
            print("App bundle structure created successfully.")
            return True
        except Exception as e:
            print(f"Error creating app bundle structure: {str(e)}")
            return False

    def create_info_plist(self) -> bool:
        """
        Create the Info.plist file for the app bundle with enhanced menu bar support.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.contents_path / "Info.plist", "w") as f:
                f.write(
                    f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleExecutable</key>
    <string>{self.app_name}</string>
    <key>CFBundleIconFile</key>
    <string>trainer.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.oliverernster.trainer</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{self.app_name}</string>
    <key>CFBundleDisplayName</key>
    <string>{self.app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.productivity</string>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>"""
                )
            print("Info.plist created successfully with enhanced menu bar support.")
            return True
        except Exception as e:
            print(f"Error creating Info.plist: {str(e)}")
            return False

    def copy_app_files(self) -> bool:
        """
        Copy application files to the app bundle automatically.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Copy essential Python files
            essential_files = ["main.py", "version.py", "requirements.txt"]
            for file in essential_files:
                source_file = self.source_path / file
                dest_file = self.resources_path / file
                if source_file.exists():
                    shutil.copy2(source_file, dest_file)
                    print(f"Copied {file}")

            # Copy entire src directory with all application source
            src_source = self.source_path / "src"
            src_dest = self.resources_path / "src"
            if src_source.exists():
                shutil.copytree(src_source, src_dest, dirs_exist_ok=True)
                print("Copied src directory with all subdirectories and files")

            # Copy assets directory
            assets_source = self.source_path / "assets"
            assets_dest = self.resources_path / "assets"
            if assets_source.exists():
                shutil.copytree(assets_source, assets_dest, dirs_exist_ok=True)
                print("Copied assets directory")

            # Copy complete config.json if it exists, otherwise create basic config
            config_json_path = self.resources_path / "config.json"
            source_config_path = self.source_path / "config.json"
            
            if source_config_path.exists():
                # Copy the complete config file
                shutil.copy2(source_config_path, config_json_path)
                print("Copied complete config.json")
            elif not config_json_path.exists():
                # Fallback: create basic config only if no source config exists
                basic_config = {
                    "app_name": "Trainer",
                    "version": "4.0.0",
                    "bundle_id": "com.oliverernster.trainer",
                    "data_dir": "~/.trainer_app"
                }
                import json
                with open(config_json_path, 'w') as f:
                    json.dump(basic_config, f, indent=2)
                print("Created basic config.json (fallback)")

            print("All application files copied successfully.")
            return True
        except Exception as e:
            print(f"Error copying application files: {str(e)}")
            traceback.print_exc()
            return False

    def add_import_path_fix(self) -> bool:
        """
        Add import path fix to the main script.

        Returns:
            bool: True if successful, False otherwise
        """
        main_script_path = self.resources_path / f"{self.app_name.lower()}.py"

        try:
            if not os.path.exists(main_script_path):
                print(f"Warning: Main script not found at {main_script_path}")
                return False

            # Make the script executable
            os.chmod(main_script_path, 0o755)
            print("Main script is executable")
            return True
        except Exception as e:
            print(f"Error setting up main script: {str(e)}")
            traceback.print_exc()
            return False

    def build(self) -> bool:
        """
        Build the complete app bundle.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.check_required_files():
            return False

        if not self.create_app_structure():
            return False

        if not self.create_info_plist():
            return False

        if not LauncherScriptGenerator.create_launcher_script(
            self.macos_path, self.app_name, self.resources_path
        ):
            return False

        if not self.copy_app_files():
            return False

        # Install Python in the bundle
        if not PackageManager.install_python_in_bundle(self.resources_path):
            print(
                "Warning: Failed to install Python in bundle. Will use system Python instead."
            )

        # Copy all dependencies with the improved thorough method
        if not PackageManager.copy_packages(
            self.resources_path, self.site_packages_path
        ):
            print(
                "Warning: Failed to copy Python packages. Application may not work properly."
            )
            return False

        if not self.add_import_path_fix():
            print("Warning: Failed to set up main script. Continuing anyway.")

        if not IconConverter.convert_png_to_icns(
            self.source_path, self.app_bundle_path
        ):
            print("Warning: Failed to convert icon. Continuing anyway.")

        print("App bundle built successfully.")
        return True


class DMGCommand(ABC):
    """Command pattern base class for DMG operations."""

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.

        Returns:
            bool: True if successful, False otherwise
        """
        pass


class CreateDirectDMGCommand(DMGCommand):
    """Command to create a DMG file directly from the staging folder."""

    def __init__(self, staging_path: Path, final_dmg: str, volume_name: str):
        """
        Initialize the command.

        Args:
            staging_path: Path to the staging directory
            final_dmg: Path to the final DMG file
            volume_name: Name of the volume
        """
        self.staging_path = staging_path
        self.final_dmg = final_dmg
        self.volume_name = volume_name

    def execute(self) -> bool:
        """
        Execute the command to create the DMG directly.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Remove existing DMG if it exists
            if os.path.exists(self.final_dmg):
                os.remove(self.final_dmg)

            # Create the DMG directly
            print(f"Creating DMG directly from {self.staging_path} to {self.final_dmg}")
            success, _ = CommandRunner.run_command(
                [
                    "hdiutil",
                    "create",
                    "-fs",
                    "HFS+",
                    "-volname",
                    self.volume_name,
                    "-srcfolder",
                    str(self.staging_path),
                    "-format",
                    "UDZO",
                    "-imagekey",
                    "zlib-level=9",
                    self.final_dmg,
                ]
            )

            if not success:
                print("Error creating DMG directly")
                return False

            print(f"DMG created successfully: {self.final_dmg}")
            return True
        except Exception as e:
            print(f"Error creating DMG directly: {str(e)}")
            return False


class DMGCreator:
    """Creates a DMG file using the create-dmg tool for professional results."""

    def __init__(self, app_name: str, temp_path: Path, staging_path: Path):
        """
        Initialize the DMG creator.

        Args:
            app_name: Name of the application
            temp_path: Path to the temporary directory
            staging_path: Path to the staging directory
        """
        self.app_name = app_name
        self.temp_path = temp_path
        self.staging_path = staging_path
        self.volume_name = f"Install {app_name}"
        self.final_dmg = f"{app_name.lower()}.dmg"

    def setup_staging_area(self) -> bool:
        """
        Set up the staging area with necessary files.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clean existing staging directory to avoid issues
            if os.path.exists(self.staging_path):
                shutil.rmtree(self.staging_path)
            os.makedirs(self.staging_path, exist_ok=True)

            # Copy the app bundle to the staging directory
            app_bundle_path = self.temp_path / f"{self.app_name}.app"
            if not os.path.exists(app_bundle_path):
                print(f"Error: App bundle not found at {app_bundle_path}")
                return False

            staging_app_path = self.staging_path / f"{self.app_name}.app"
            shutil.copytree(app_bundle_path, staging_app_path)

            print("Staging area prepared with app bundle.")
            return True
        except Exception as e:
            print(f"Error setting up staging area: {str(e)}")
            return False

    def _check_create_dmg_installed(self) -> bool:
        """
        Check if create-dmg is installed, install if necessary.

        Returns:
            bool: True if create-dmg is available, False otherwise
        """
        try:
            # Check if create-dmg is installed
            result = subprocess.run(
                ["which", "create-dmg"], capture_output=True, text=True
            )

            if result.returncode == 0:
                print("create-dmg tool is installed.")
                return True

            # Try to install create-dmg using homebrew
            print("create-dmg not found. Attempting to install using Homebrew...")

            # First check if homebrew is installed
            brew_check = subprocess.run(
                ["which", "brew"], capture_output=True, text=True
            )

            if brew_check.returncode != 0:
                print(
                    "Error: Homebrew is not installed. Please install Homebrew first."
                )
                print("Visit https://brew.sh for installation instructions.")
                return False

            # Install create-dmg
            install_result = subprocess.run(
                ["brew", "install", "create-dmg"], capture_output=True, text=True
            )

            if install_result.returncode != 0:
                print(f"Error installing create-dmg: {install_result.stderr}")
                return False

            print("create-dmg installed successfully.")
            return True
        except Exception as e:
            print(f"Error checking/installing create-dmg: {str(e)}")
            return False

    def _cleanup_mounted_images(self) -> None:
        """Clean up any mounted disk images that might interfere."""
        try:
            # List all mounted volumes and look for any that might be ours
            result = subprocess.run(
                ["df", "-h"], capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if '/Volumes/' in line and ('Install' in line or 'trainer' in line.lower()):
                        # Extract volume path
                        parts = line.split()
                        if len(parts) > 8:
                            volume_path = ' '.join(parts[8:])  # Volume path might contain spaces
                            print(f"Unmounting potentially conflicting volume: {volume_path}")
                            subprocess.run(["hdiutil", "detach", volume_path, "-force"],
                                         capture_output=True)
        except Exception as e:
            print(f"Warning: Could not clean up mounted images: {e}")

    def _create_dmg_with_retry(self, cmd: list, max_retries: int = 3) -> bool:
        """Create DMG with retry logic for Finder busy errors."""
        for attempt in range(max_retries):
            try:
                print(f"DMG creation attempt {attempt + 1}/{max_retries}")
                print("Executing:", " ".join(cmd))
                
                # Add a small delay before each attempt
                if attempt > 0:
                    import time
                    time.sleep(2)
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("Professional DMG created successfully!")
                    return True
                else:
                    error_msg = result.stderr
                    print(f"Attempt {attempt + 1} failed: {error_msg}")
                    
                    # Check if it's a Finder busy error
                    if "Finder is busy" in error_msg or "execution error" in error_msg:
                        if attempt < max_retries - 1:
                            print("Finder busy error detected, cleaning up and retrying...")
                            self._cleanup_mounted_images()
                            continue
                    else:
                        # Different error, might not be worth retrying
                        break
            
            except Exception as e:
                print(f"Attempt {attempt + 1} failed with exception: {e}")
                if attempt == max_retries - 1:
                    break
        
        return False

    def create(self) -> bool:
        """
        Create the DMG file using create-dmg for professional results.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if create-dmg is installed
            if not self._check_create_dmg_installed():
                print("The create-dmg tool is required for professional DMG creation.")
                print("Please install it manually using: brew install create-dmg")
                return False

            # Clean up any mounted disk images first
            self._cleanup_mounted_images()

            # Remove existing DMG if it exists
            if os.path.exists(self.final_dmg):
                os.remove(self.final_dmg)
                print(f"Removed existing DMG: {self.final_dmg}")

            # Create DMG with professional styling and retry logic
            print("\nCreating professional DMG...")

            # Base command
            cmd = [
                "create-dmg",
                "--volname",
                self.volume_name,
                "--window-pos",
                "200",
                "120",
                "--window-size",
                "640",
                "400",
                "--icon-size",
                "100",
                "--text-size",
                "14",
                "--app-drop-link",
                "520",
                "180",  # Position of the Applications shortcut
                "--icon",
                f"{self.app_name}.app",
                "120",
                "180",  # Position of the app
            ]

            # Add background image if it exists
            if os.path.exists("dmg_background.png"):
                cmd.extend(["--background", "dmg_background.png"])

            # Add output DMG and source app
            cmd.extend(
                [self.final_dmg, str(self.staging_path / f"{self.app_name}.app")]
            )

            # Use retry logic for robust DMG creation
            if self._create_dmg_with_retry(cmd):
                # Success with main command
                pass
            else:
                # Try fallback method with basic create-dmg
                print("\nAttempting fallback method...")
                fallback_cmd = [
                    "create-dmg",
                    self.final_dmg,
                    str(self.staging_path / f"{self.app_name}.app"),
                ]

                if self._create_dmg_with_retry(fallback_cmd):
                    print("Created basic DMG using fallback method.")
                else:
                    print("All create-dmg methods failed")
                    return False

            # Set the icon for the DMG if available (check for converted PNG first, then ICO)
            dmg_icon_path = None
            if os.path.exists("assets/train_emoji.png"):
                dmg_icon_path = "assets/train_emoji.png"
            elif os.path.exists("assets/train_emoji.ico"):
                dmg_icon_path = "assets/train_emoji.ico"
                
            if dmg_icon_path:
                try:
                    DMGIconSetter.set_dmg_icon(self.final_dmg, dmg_icon_path)
                    print(f"Set custom icon for DMG using: {dmg_icon_path}")
                except Exception as e:
                    print(f"Warning: Could not set DMG icon: {e}")

            print(f"DMG creation complete: {self.final_dmg}")
            return True

        except Exception as e:
            print(f"Error creating DMG: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


class DMGVerifier:
    """Verifies the created DMG file."""

    @staticmethod
    def verify_dmg(dmg_path: str, app_name: str) -> bool:
        """
        Verify the DMG by mounting it and checking its contents.

        Args:
            dmg_path: Path to the DMG file
            app_name: Name of the application

        Returns:
            bool: True if verification passes, False otherwise
        """
        print("\nVerifying DMG by mounting it...")

        try:
            volume_name = os.path.splitext(os.path.basename(dmg_path))[0]

            # Mount the DMG
            success, _ = CommandRunner.run_command(
                ["hdiutil", "attach", dmg_path, "-nobrowse"]
            )
            if not success:
                print("Warning: Could not mount DMG for verification")
                return False

            volume_path = f"/Volumes/{volume_name}"
            app_path = f"{volume_path}/{app_name}.app"

            # Check if app exists in the DMG
            if not os.path.exists(app_path):
                print(f"Warning: App not found in DMG: {app_path}")
                CommandRunner.run_command(["hdiutil", "detach", volume_path, "-force"])
                return False

            print(f"App found in DMG: {app_path}")

            # Check for required components
            contents_path = f"{app_path}/Contents"
            launcher_path = f"{contents_path}/MacOS/{app_name}"

            # Check for launcher script
            if os.path.exists(launcher_path):
                print(f"✅ Launcher script found: {launcher_path}")

                # Check launcher content
                with open(launcher_path, "r") as f:
                    launcher_content = f.read()

                if "BUNDLED_PYTHON" in launcher_content:
                    print(f"✅ Launcher script contains bundled Python support")
                else:
                    print(f"⚠️ Launcher script may be missing bundled Python support")
            else:
                print(f"❌ Launcher script not found: {launcher_path}")

            # Check for main script
            main_script_path = f"{contents_path}/Resources/main.py"
            if os.path.exists(main_script_path):
                print(f"✅ Main script found: {main_script_path}")
            else:
                print(f"❌ Main script not found: {main_script_path}")

            # Check for bundled Python
            python_bin_path = f"{contents_path}/Resources/python_bin/python3"
            if os.path.exists(python_bin_path):
                print(f"✅ Bundled Python found: {python_bin_path}")
            else:
                print(f"⚠️ Bundled Python not found: {python_bin_path}")

            # Check for required packages
            site_packages_path = f"{contents_path}/Resources/site-packages"
            if os.path.exists(site_packages_path):
                print(f"✅ Site-packages directory found: {site_packages_path}")

                # Check key packages
                for package in ["PySide6"]:
                    if os.path.exists(f"{site_packages_path}/{package}"):
                        print(f"✅ Found package: {package}")
                    else:
                        print(f"❌ Missing package: {package}")

                # Check for essential PySide6 components
                if os.path.exists(f"{site_packages_path}/PySide6"):
                    # Check for QtCore which is essential
                    qt_core_found = False
                    for ext in [".so", ".pyd", ".dylib", ".dll"]:
                        if os.path.exists(f"{site_packages_path}/PySide6/QtCore{ext}"):
                            qt_core_found = True
                            print("✅ Found PySide6 QtCore module")
                            break

                    if not qt_core_found:
                        print("❌ Missing PySide6 QtCore module")

                    # Check for plugins directory
                    if os.path.exists(f"{site_packages_path}/PySide6/plugins"):
                        print("✅ Found PySide6 plugins directory")
                    else:
                        print(
                            "⚠️ Missing PySide6 plugins directory - UI may not display correctly"
                        )
            else:
                print(f"❌ Site-packages directory not found: {site_packages_path}")

            # Unmount the DMG
            print("\nUnmounting DMG...")
            CommandRunner.run_command(["hdiutil", "detach", volume_path, "-force"])
            print("DMG verification completed.")

            return True
        except Exception as e:
            print(f"Error verifying DMG: {str(e)}")
            # Try to unmount anyway
            try:
                CommandRunner.run_command(
                    ["hdiutil", "detach", f"/Volumes/{volume_name}", "-force"]
                )
            except:
                pass
            return False


class BuildFacade:
    """Facade pattern to simplify the DMG build process."""

    def __init__(self):
        """Initialize the build facade."""
        self.app_name = "Trainer"
        self.source_dir = "."
        self.temp_dir = "./temp_dmg"
        self.staging_dir = "./staging_dmg"

        self.source_path = Path(self.source_dir)
        self.temp_path = Path(self.temp_dir)
        self.staging_path = Path(self.staging_dir)

    def setup(self) -> bool:
        """
        Set up the build environment.

        Returns:
            bool: True if setup is successful, False otherwise
        """
        try:
            # Terminate any running instances of the application
            ProcessTerminator.terminate_running_instances(self.app_name)

            # Clean previous builds
            BuildCleaner.clear_builds()

            # Create temporary directories
            for path in [self.temp_path, self.staging_path]:
                path.mkdir(parents=True, exist_ok=True)

            # Create background image
            BackgroundImageCreator.create_background_image()

            return True
        except Exception as e:
            print(f"Error during setup: {e}")
            return False

    def build(self) -> bool:
        """
        Execute the build process.

        Returns:
            bool: True if build is successful, False otherwise
        """
        try:
            # Build the app bundle
            app_builder = AppBundleBuilder(self.source_path, self.temp_path)
            if not app_builder.build():
                print("Error building app bundle")
                return False

            # Create the DMG
            dmg_creator = DMGCreator(self.app_name, self.temp_path, self.staging_path)
            if not dmg_creator.setup_staging_area():
                print("Error setting up DMG staging area")
                return False

            if not dmg_creator.create():
                print("Error creating DMG")
                return False

            # Verify the DMG
            DMGVerifier.verify_dmg(f"{self.app_name.lower()}.dmg", self.app_name)

            print("\nBuild Summary:")
            print("==============")
            print(f"App bundle created: {self.temp_path}/{self.app_name}.app")
            print(f"DMG installer created: {self.app_name.lower()}.dmg")
            print("\nTo install:")
            print(f"1. Open {self.app_name.lower()}.dmg")
            print(f"2. Drag {self.app_name}.app to the Applications folder")
            print(f"3. Eject the disk image")

            return True
        except Exception as e:
            print(f"Error during build: {e}")
            return False
        finally:
            # Clean up temporary files (but keep the DMG and dist folder)
            try:
                for path in ["dmg_background.png", "dmg_background.txt"]:
                    if os.path.exists(path):
                        os.remove(path)
            except Exception as e:
                print(f"Warning: Error cleaning up temporary files: {e}")


def main():
    """
    Build the DMG installer for Trainer.
    """
    print("=" * 60)
    print("TRAINER DMG BUILDER")
    print("=" * 60)

    # Ensure PIL package is installed for background image creation
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter

        print("PIL package found. Continuing with build...")
    except ImportError:
        print("PIL package not found. Installing for the build process...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
            print("PIL package installed successfully.")
        except Exception as e:
            print(f"Error installing PIL package: {e}")
            print("Please install it manually with: pip install pillow")
            return 1

    builder = BuildFacade()
    if not builder.setup():
        print("Setup failed. Cannot continue with build.")
        return 1

    if not builder.build():
        print("Build failed.")
        return 1

    print("\nBuild process completed successfully.")
    print("\nThe application is ready for distribution. Required packages")
    print(
        "have been included in the app bundle, so end users don't need to install them separately."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
