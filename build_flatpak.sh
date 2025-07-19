#!/bin/bash

# Exit on error
set -e

# Function to detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/redhat-release ]; then
        # More specific check for RHEL-based systems
        if grep -q "Rocky Linux" /etc/redhat-release; then
            DISTRO="rocky"
        elif grep -q "AlmaLinux" /etc/redhat-release; then
            DISTRO="alma"
        else
            DISTRO="rhel"
        fi
    else
        DISTRO="unknown"
    fi
    echo $DISTRO
}

# Function to detect desktop environment
detect_desktop() {
    if [ -n "$XDG_CURRENT_DESKTOP" ]; then
        DESKTOP=$XDG_CURRENT_DESKTOP
    elif [ -n "$DESKTOP_SESSION" ]; then
        DESKTOP=$DESKTOP_SESSION
    else
        # Try to detect using ps
        if pgrep -x "cinnamon" > /dev/null; then
            DESKTOP="Cinnamon"
        elif pgrep -x "gnome-shell" > /dev/null; then
            DESKTOP="GNOME"
        elif pgrep -x "plasmashell" > /dev/null; then
            DESKTOP="KDE"
        else
            DESKTOP="unknown"
        fi
    fi
    echo $DESKTOP
}

# Function to display installation instructions for flatpak-builder
install_instructions() {
    DISTRO=$(detect_distro)
    echo "flatpak-builder not found. Please install it first."
    
    case $DISTRO in
        "ubuntu" | "debian" | "linuxmint" | "pop")
            echo "On Debian/Ubuntu/Mint/Pop_OS!: sudo apt install flatpak flatpak-builder"
            ;;
        "fedora")
            echo "On Fedora: sudo dnf install flatpak flatpak-builder"
            ;;
        "rhel" | "centos" | "rocky" | "alma")
            echo "On RHEL/CentOS/Rocky/Alma Linux:"
            echo "1. Enable EPEL repository: sudo dnf install epel-release"
            echo "2. Install flatpak: sudo dnf install flatpak flatpak-builder"
            ;;
        "arch" | "manjaro" | "endeavouros")
            echo "On Arch/Manjaro/EndeavourOS: sudo pacman -S flatpak flatpak-builder"
            ;;
        "opensuse" | "opensuse-leap" | "opensuse-tumbleweed")
            echo "On openSUSE: sudo zypper install flatpak flatpak-builder"
            ;;
        "gentoo")
            echo "On Gentoo: sudo emerge --ask dev-util/flatpak dev-util/flatpak-builder"
            ;;
        "void")
            echo "On Void Linux: sudo xbps-install -S flatpak flatpak-builder"
            ;;
        "slackware")
            echo "On Slackware: Use SlackBuilds from https://slackbuilds.org/"
            ;;
        *)
            echo "For other distributions, please check your package manager or visit https://flatpak.org/setup/"
            ;;
    esac
    
    echo "After installation, you may need to log out and log back in to update your environment."
    exit 1
}

# Check if flatpak is installed
if ! command -v flatpak &> /dev/null; then
    echo "flatpak not found!"
    install_instructions
fi

# Check if flatpak-builder is installed
if ! command -v flatpak-builder &> /dev/null; then
    echo "flatpak-builder not found!"
    install_instructions
fi

# Check if required files exist
if [ ! -f "main.py" ]; then
    echo "main.py not found. Please run this script from your source directory."
    exit 1
fi

# Verify essential directories exist
if [ ! -d "src" ]; then
    echo "src directory not found. Please run this script from your source directory."
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "requirements.txt not found. Please ensure requirements.txt exists."
    exit 1
fi

# Detect distribution and desktop environment
DISTRO=$(detect_distro)
DESKTOP=$(detect_desktop)
echo "Detected distribution: $DISTRO"
echo "Detected desktop environment: $DESKTOP"

# Get source directory (where the script is being run from)
SOURCE_DIR="$(pwd)"
echo "Building from source directory: $SOURCE_DIR"

# Create simple runner script to start trainer directly
cat > trainer-runner.sh << 'EOL'
#!/bin/bash

# Set Python path to include app directory and site-packages
export PYTHONPATH="/app:/app/lib/python3.12/site-packages:$PYTHONPATH"

# PySide6/Qt6 Configuration for KDE Platform
export QT_PLUGIN_PATH="/app/lib/python3.12/site-packages/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="/app/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms"

# Platform detection for PySide6 on KDE runtime
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$FORCE_X11" ]; then
    export QT_QPA_PLATFORM=wayland
    echo 'Trainer: Using Wayland platform'
elif [ -n "$DISPLAY" ]; then
    export QT_QPA_PLATFORM=xcb
    echo 'Trainer: Using X11/XCB platform'
else
    export QT_QPA_PLATFORM=xcb
    echo 'Trainer: Using XCB as fallback'
fi

# Additional Qt6 environment variables
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_ENABLE_HIGHDPI_SCALING=1

# Change to app directory and run Trainer
cd /app
exec python3 main.py "$@"
EOL

# Make runner script executable
chmod +x trainer-runner.sh

# Create Flatpak manifest with KDE Platform for better Qt6/PySide6 support
cat > com.oliverernster.Trainer.json << 'EOL'
{
    "app-id": "com.oliverernster.Trainer",
    "runtime": "org.kde.Platform",
    "runtime-version": "6.8",
    "sdk": "org.kde.Sdk",
    "command": "trainer",
    "finish-args": [
        "--share=ipc",
        "--socket=x11",
        "--socket=wayland",
        "--socket=fallback-x11",
        "--device=dri",
        "--share=network",
        "--filesystem=home",
        "--filesystem=xdg-documents",
        "--filesystem=xdg-download",
        "--talk-name=org.freedesktop.Notifications",
        "--talk-name=org.kde.StatusNotifierWatcher",
        "--own-name=com.oliverernster.Trainer"
    ],
    "build-options": {
        "env": {
            "PIP_CACHE_DIR": "/run/build/trainer/pip-cache"
        },
        "build-args": [
            "--share=network"
        ]
    },
    "modules": [
        {
            "name": "python3-pip",
            "buildsystem": "simple",
            "build-commands": [
                "python3 -m ensurepip --upgrade"
            ]
        },
        {
            "name": "python-dependencies",
            "buildsystem": "simple",
            "build-commands": [
                "echo 'Installing PySide6 and dependencies for Trainer...'",
                "pip3 install --no-cache-dir --prefix=${FLATPAK_DEST} PySide6>=6.5.0",
                "echo 'Verifying PySide6 installation...'",
                "python3 -c 'import PySide6; print(\"PySide6 version:\", PySide6.__version__)'",
                "echo 'Installing other Python dependencies...'",
                "pip3 install --no-cache-dir --prefix=${FLATPAK_DEST} requests>=2.31.0",
                "pip3 install --no-cache-dir --prefix=${FLATPAK_DEST} aiohttp>=3.8.0",
                "pip3 install --no-cache-dir --prefix=${FLATPAK_DEST} python-dateutil>=2.8.0",
                "pip3 install --no-cache-dir --prefix=${FLATPAK_DEST} pydantic>=2.0.0",
                "pip3 install --no-cache-dir --prefix=${FLATPAK_DEST} imageio>=2.31.0",
                "echo 'Checking PySide6 Qt plugins...'",
                "find ${FLATPAK_DEST}/lib/python3.12/site-packages/PySide6/Qt/plugins -name '*platform*' -type d || echo 'Platform plugins not found in expected location'"
            ]
        },
        {
            "name": "trainer",
            "buildsystem": "simple",
            "build-commands": [
                "echo 'Installing Trainer application files to /app...'",
                "cp -rv main.py ${FLATPAK_DEST}/",
                "cp -rv src ${FLATPAK_DEST}/",
                "if [ -f version.py ]; then cp -rv version.py ${FLATPAK_DEST}/; fi",
                "if [ -d assets ]; then cp -rv assets ${FLATPAK_DEST}/; fi",
                "if [ -f LICENSE ]; then cp -rv LICENSE ${FLATPAK_DEST}/; fi",
                "if [ -d licenses ]; then cp -rv licenses ${FLATPAK_DEST}/; fi",
                "echo 'Verifying main.py exists:'",
                "test -f ${FLATPAK_DEST}/main.py && echo 'main.py successfully copied' || (echo 'ERROR: main.py not found!' && exit 1)",
                "echo 'Verifying src directory exists:'",
                "test -d ${FLATPAK_DEST}/src && echo 'src directory successfully copied' || (echo 'ERROR: src directory not found!' && exit 1)",
                "echo 'Installing launcher script...'",
                "mkdir -p ${FLATPAK_DEST}/bin",
                "cp trainer-runner.sh ${FLATPAK_DEST}/bin/trainer",
                "chmod +x ${FLATPAK_DEST}/bin/trainer",
                "echo 'Verifying launcher script:'",
                "test -x ${FLATPAK_DEST}/bin/trainer && echo 'Launcher script created successfully' || (echo 'ERROR: Launcher script creation failed!' && exit 1)",
                "echo 'Final verification - listing /app contents:'",
                "ls -la ${FLATPAK_DEST}/",
                "echo 'Testing Python can find main.py:'",
                "cd ${FLATPAK_DEST} && python3 -c 'import os; print(\"main.py exists:\", os.path.exists(\"main.py\"))'",
                "install -Dm644 com.oliverernster.Trainer.desktop ${FLATPAK_DEST}/share/applications/com.oliverernster.Trainer.desktop",
                "install -Dm644 com.oliverernster.Trainer.metainfo.xml ${FLATPAK_DEST}/share/metainfo/com.oliverernster.Trainer.metainfo.xml",
                "echo 'Installing application icons...'",
                "if [ -f assets/trainer_icon.png ]; then install -Dm644 assets/trainer_icon.png ${FLATPAK_DEST}/share/icons/hicolor/256x256/apps/com.oliverernster.Trainer.png; echo 'Installed 256x256 icon'; fi",
                "for size in 16 32 64 128; do if [ -f assets/trainer_icon_${size}.png ]; then install -Dm644 assets/trainer_icon_${size}.png ${FLATPAK_DEST}/share/icons/hicolor/${size}x${size}/apps/com.oliverernster.Trainer.png; echo \"Installed ${size}x${size} icon\"; fi; done"
            ],
            "sources": [
                {
                    "type": "dir",
                    "path": "."
                }
            ]
        }
    ]
}
EOL

# Create desktop file following Flatpak conventions
cat > com.oliverernster.Trainer.desktop << EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=Trainer
GenericName=Train Times Application
Comment=Train times application with integrated weather forecasting and astronomical events
Icon=com.oliverernster.Trainer
Exec=trainer
Terminal=false
Categories=Utility;Education;
Keywords=train;railway;times;schedule;weather;astronomy;transport;
StartupNotify=true
StartupWMClass=trainer
X-Flatpak=com.oliverernster.Trainer
EOL

# Add desktop environment specific entries
case "$DESKTOP" in
    *"Cinnamon"* | *"CINNAMON"* | *"X-Cinnamon"*)
        echo "Adding Cinnamon-specific desktop entries..."
        cat >> com.oliverernster.Trainer.desktop << 'EOL'
X-Cinnamon-UsesNotifications=true
X-GNOME-UsesNotifications=true
EOL
        ;;
    *"GNOME"* | *"UBUNTU"*)
        echo "Adding GNOME-specific desktop entries..."
        cat >> com.oliverernster.Trainer.desktop << 'EOL'
X-GNOME-UsesNotifications=true
EOL
        ;;
    *"KDE"* | *"PLASMA"*)
        echo "Adding KDE-specific desktop entries..."
        cat >> com.oliverernster.Trainer.desktop << 'EOL'
X-KDE-FormFactor=desktop,tablet,handset
X-KDE-StartupNotify=true
EOL
        ;;
    *)
        # Default entries for other desktop environments
        cat >> com.oliverernster.Trainer.desktop << 'EOL'
X-GNOME-UsesNotifications=true
EOL
        ;;
esac

# Extract version from version.py
APP_VERSION=""
if [ -f "version.py" ]; then
    APP_VERSION=$(python3 -c "exec(open('version.py').read()); print(__version__)" 2>/dev/null || echo "4.0.0")
else
    APP_VERSION="4.0.0"
fi

echo "Using version: $APP_VERSION"

# Create metainfo file
cat > com.oliverernster.Trainer.metainfo.xml << EOL
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>com.oliverernster.Trainer</id>
  <metadata_license>MIT</metadata_license>
  <project_license>MIT</project_license>
  <name>Trainer</name>
  <summary>Train times application with integrated weather forecasting and astronomical events</summary>
  <description>
    <p>
      Trainer is a comprehensive train times application that provides real-time train schedules,
      route planning, and journey information for the UK railway network. It includes integrated
      weather forecasting and astronomical event tracking to help you plan your journeys better.
    </p>
    <p>Features:</p>
    <ul>
      <li>Real-time train departure and arrival times</li>
      <li>Route planning with multiple journey options</li>
      <li>Station search and information</li>
      <li>Integrated weather forecasts for journey planning</li>
      <li>Astronomical event tracking (sunrise, sunset, moon phases)</li>
      <li>Support for via stations and complex routes</li>
      <li>Offline route calculation capabilities</li>
      <li>Comprehensive UK railway network coverage</li>
      <li>Modern Qt6-based user interface</li>
    </ul>
  </description>
  <launchable type="desktop-id">com.oliverernster.Trainer.desktop</launchable>
  <provides>
    <binary>trainer</binary>
  </provides>
  <url type="homepage">https://github.com/oliverernster/trainer</url>
  <url type="bugtracker">https://github.com/oliverernster/trainer/issues</url>
  <url type="help">https://github.com/oliverernster/trainer/blob/main/README.md</url>
  <developer_name>Oliver Ernster</developer_name>
  <update_contact>oliver.ernster@example.com</update_contact>
  <releases>
    <release version="$APP_VERSION" date="2025-07-19">
      <description>
        <p>Version $APP_VERSION with improved data loading and clean distribution structure.</p>
      </description>
    </release>
  </releases>
  <content_rating type="oars-1.1"/>
  <supports>
    <control>pointing</control>
    <control>keyboard</control>
  </supports>
  <categories>
    <category>Utility</category>
    <category>Travel</category>
    <category>Qt</category>
  </categories>
</component>
EOL

# Function to setup Flathub repository
setup_flathub() {
    # Remove existing Flathub remote if it exists and is causing issues
    echo "Removing existing Flathub remote if it exists..."
    flatpak remote-delete --force flathub 2>/dev/null || true

    # Add Flathub repository with the correct URL based on distribution
    echo "Adding Flathub repository with correct URL..."
    if [[ "$DISTRO" == "arch" || "$DISTRO" == "manjaro" || "$DISTRO" == "endeavouros" ]]; then
        flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    else
        flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    fi

    # Verify the remote is correctly added
    echo "Verifying Flathub remote configuration..."
    flatpak remotes
}

# Setup Flathub repository
setup_flathub

# Install required KDE 6.8 runtimes with specific distribution handling
echo "Installing KDE 6.8 Platform and SDK (optimized for Qt6/PySide6)..."

# Check for Arch-based systems with special handling
if [[ "$DISTRO" == "arch" || "$DISTRO" == "manjaro" || "$DISTRO" == "endeavouros" ]]; then
    echo "Detected Arch-based system. Using special installation procedure..."
    
    # First try to install the runtime with user installation
    if ! flatpak install --user -y flathub org.kde.Platform//6.8; then
        echo "User installation failed. Trying system installation..."
        if ! sudo flatpak install -y flathub org.kde.Platform//6.8; then
            echo "Failed to install KDE Platform runtime. Please check your internet connection."
            echo "You may need to install the ca-certificates package: sudo pacman -S ca-certificates"
            echo "Also ensure your Flathub repository is correctly configured."
            exit 1
        fi
    fi
    
    # Then install the SDK
    if ! flatpak install --user -y flathub org.kde.Sdk//6.8; then
        echo "User installation failed. Trying system installation..."
        if ! sudo flatpak install -y flathub org.kde.Sdk//6.8; then
            echo "Failed to install KDE SDK runtime. Please check your internet connection."
            exit 1
        fi
    fi
else
    # For non-Arch systems, use the original method
    if ! flatpak install --user -y flathub org.kde.Platform//6.8; then
        echo "Failed to install KDE Platform runtime. Please check your internet connection."
        case $DISTRO in
            "ubuntu" | "debian" | "linuxmint" | "pop")
                echo "You may need to install the ca-certificates package: sudo apt install ca-certificates"
                ;;
            "fedora" | "rhel" | "centos" | "rocky" | "alma")
                echo "You may need to install the ca-certificates package: sudo dnf install ca-certificates"
                ;;
        esac
        exit 1
    fi

    if ! flatpak install --user -y flathub org.kde.Sdk//6.8; then
        echo "Failed to install KDE SDK runtime. Please check your internet connection."
        exit 1
    fi
fi

echo "Building Flatpak..."

# Create build directory if it doesn't exist
mkdir -p build

# Clean any previous builds
rm -rf build/* 2>/dev/null || true

# Build the Flatpak with dependencies from Flathub
echo "Building with flatpak-builder..."
if ! flatpak-builder --verbose --user --install-deps-from=flathub --force-clean build com.oliverernster.Trainer.json; then
    echo "Flatpak build failed. Trying with alternative build options..."
    
    # Attempt with different options for Arch
    if [[ "$DISTRO" == "arch" || "$DISTRO" == "manjaro" || "$DISTRO" == "endeavouros" ]]; then
        echo "Trying alternate build for Arch systems..."
        if ! flatpak-builder --verbose --user --install-deps-from=flathub --force-clean --keep-build-dirs build com.oliverernster.Trainer.json; then
            echo "Alternative build also failed. This could be due to network issues or missing dependencies."
            echo "Check the build logs in the build directory for more details."
            exit 1
        fi
    else
        echo "Flatpak build failed. This could be due to network issues or missing dependencies."
        echo "If you're behind a proxy, make sure to set the http_proxy and https_proxy environment variables."
        exit 1
    fi
fi

echo "Creating repository..."
flatpak-builder --repo=repo --force-clean --user build com.oliverernster.Trainer.json

echo "Creating single-file bundle..."

# Get repository size for estimation
REPO_SIZE_BYTES=$(du -sb repo 2>/dev/null | cut -f1 || echo "0")
REPO_SIZE_MB=$(( REPO_SIZE_BYTES / 1048576 ))
echo "Repository size: ${REPO_SIZE_MB} MB"

echo "Running: flatpak build-bundle repo trainer.flatpak com.oliverernster.Trainer"
echo ""

# Start bundle creation with verbose output
flatpak build-bundle --verbose repo trainer.flatpak com.oliverernster.Trainer > /tmp/flatpak-bundle.log 2>&1 &
BUNDLE_PID=$!

# Monitor progress
last_milestone=""
last_size=0
no_progress_count=0

while kill -0 $BUNDLE_PID 2>/dev/null; do
    # Check for milestones in the log
    if [ -f /tmp/flatpak-bundle.log ]; then
        # Look for key progress indicators with case-insensitive matching
        if grep -qi "export" /tmp/flatpak-bundle.log && [ "$last_milestone" != "exporting" ]; then
            echo ""
            echo "[1/4] Exporting files..."
            last_milestone="exporting"
        elif grep -qi "writ" /tmp/flatpak-bundle.log && [ "$last_milestone" != "writing" ]; then
            echo ""
            echo "[2/4] Writing bundle data..."
            last_milestone="writing"
        elif grep -qi "commit" /tmp/flatpak-bundle.log && [ "$last_milestone" != "committing" ]; then
            echo ""
            echo "[3/4] Committing changes..."
            last_milestone="committing"
        elif grep -qi "compress\|pack" /tmp/flatpak-bundle.log && [ "$last_milestone" != "compressing" ]; then
            echo ""
            echo "[4/4] Compressing bundle..."
            last_milestone="compressing"
        fi
    fi
    
    # Monitor bundle file size
    if [ -f "trainer.flatpak" ]; then
        current_size=$(stat -c%s "trainer.flatpak" 2>/dev/null || echo "0")
        if [ "$current_size" -gt "$last_size" ]; then
            size_mb=$(( current_size / 1048576 ))
            if [ $REPO_SIZE_BYTES -gt 0 ]; then
                percent=$(( current_size * 100 / REPO_SIZE_BYTES ))
                printf "\r📦 Bundle progress: %d MB (%d%% of repository size)" "$size_mb" "$percent"
            else
                printf "\r📦 Bundle progress: %d MB" "$size_mb"
            fi
            last_size=$current_size
            no_progress_count=0
        else
            no_progress_count=$((no_progress_count + 1))
            if [ $no_progress_count -gt 20 ]; then
                echo ""
                echo "⏳ Finalizing bundle..."
                break
            fi
        fi
    fi
    
    sleep 0.5
done

# Wait for completion
wait $BUNDLE_PID
BUNDLE_EXIT_CODE=$?

echo ""  # New line after progress

# Check result
if [ $BUNDLE_EXIT_CODE -eq 0 ] && [ -f "trainer.flatpak" ]; then
    echo "✅ Bundle creation completed successfully!"
    BUNDLE_SIZE=$(du -h trainer.flatpak | cut -f1)
    echo "📦 Final bundle size: $BUNDLE_SIZE"
    
    # If no milestones were shown, display what was in the log
    if [ "$last_milestone" = "" ] && [ -f /tmp/flatpak-bundle.log ]; then
        echo ""
        echo "Note: Progress milestones were not detected. Log tail:"
        tail -n 5 /tmp/flatpak-bundle.log
    fi
else
    echo "❌ Bundle creation failed"
    echo "You can still install from the repo with: flatpak install --user repo com.oliverernster.Trainer"
    echo "Or try creating the bundle manually with: flatpak build-bundle repo trainer.flatpak com.oliverernster.Trainer"
    
    # Show error details from log
    if [ -f /tmp/flatpak-bundle.log ]; then
        echo ""
        echo "Error details from log:"
        tail -n 10 /tmp/flatpak-bundle.log
    fi
    # Don't exit - the repo is still valid
fi

echo "Done! You can install the Flatpak with:"
echo "flatpak install --user trainer.flatpak"

# Ask if user wants to install the Flatpak
read -p "Do you want to install the Flatpak now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing Flatpak..."
    flatpak install --user -y trainer.flatpak
    
    # Check if installation was successful
    if flatpak list | grep -q com.oliverernster.Trainer; then
        echo "Flatpak installed successfully."
        
        echo "You can run it with: flatpak run com.oliverernster.Trainer"
        
        # Enhanced desktop integration
        echo "Setting up desktop integration..."
        
        # Get the location of the exported desktop file
        EXPORTED_DESKTOP_FILE=$(find ~/.local/share/flatpak/exports/share/applications -name "com.oliverernster.Trainer.desktop" 2>/dev/null)
        
        if [ -n "$EXPORTED_DESKTOP_FILE" ]; then
            mkdir -p ~/.local/share/applications
            cp "$EXPORTED_DESKTOP_FILE" ~/.local/share/applications/com.oliverernster.Trainer.desktop
            
            # Update the desktop database
            update-desktop-database ~/.local/share/applications 2>/dev/null || true
            
            echo "Desktop file created successfully."
            
            # Copy icon to standard locations
            mkdir -p ~/.local/share/icons/hicolor/256x256/apps/
            
            # Install the pre-generated PNG icons
            if [ -f "$SOURCE_DIR/assets/trainer_icon.png" ]; then
                cp "$SOURCE_DIR/assets/trainer_icon.png" "$HOME/.local/share/icons/hicolor/256x256/apps/com.oliverernster.Trainer.png"
            fi
            
            # Also install other icon sizes
            for size in 16 32 64 128; do
                if [ -f "$SOURCE_DIR/assets/trainer_icon_${size}.png" ]; then
                    mkdir -p "$HOME/.local/share/icons/hicolor/${size}x${size}/apps/"
                    cp "$SOURCE_DIR/assets/trainer_icon_${size}.png" "$HOME/.local/share/icons/hicolor/${size}x${size}/apps/com.oliverernster.Trainer.png"
                fi
            done
            
            if command -v gtk-update-icon-cache &> /dev/null; then
                gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor 2>/dev/null || true
            fi
        fi
        
        # Test the installation
        echo ""
        echo "🧪 Testing the installation..."
        echo "Running: flatpak run com.oliverernster.Trainer --version"
        timeout 10s flatpak run com.oliverernster.Trainer --version 2>/dev/null || echo "Version check completed (or timed out)"
        
    else
        echo "Installation failed. Please try installing manually with: flatpak install --user trainer.flatpak"
    fi
fi

# Print information about distributing the Flatpak
echo ""
echo "================================================================"
echo "DISTRIBUTION INFORMATION"
echo "================================================================"
echo "The generated Flatpak package 'trainer.flatpak' can now be distributed"
echo "to other users and systems. Users can install it with:"
echo ""
echo "flatpak install trainer.flatpak"
echo ""
echo "The Flatpak is self-contained and works on any Linux distribution"
echo "that supports Flatpak, regardless of the user's home directory or username."
echo "The necessary KDE runtime will be automatically downloaded if needed."
echo ""
echo "Runtime used: org.kde.Platform//6.8 (includes complete Qt6 support for PySide6)"
echo "================================================================"