"""
Comprehensive test runner for astronomy module tests.

This script runs all astronomy-related tests and provides coverage reporting
to ensure we achieve the 100% test coverage goal for the NASA astronomy integration.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests():
    """Run all astronomy tests with coverage reporting."""

    print("🚀 Running NASA Astronomy Integration Tests")
    print("=" * 60)

    # Test directories to run
    test_dirs = [
        "tests/unit/test_astronomy/test_models/",
        "tests/unit/test_astronomy/test_api/",
        "tests/unit/test_astronomy/test_managers/",
        "tests/unit/test_astronomy/test_ui/",
    ]

    # Source directories for coverage
    source_dirs = [
        "src/models/astronomy_data.py",
        "src/models/combined_forecast_data.py",
        "src/api/nasa_api_manager.py",
        "src/managers/astronomy_config.py",
        "src/managers/astronomy_manager.py",
        "src/managers/combined_forecast_manager.py",
        "src/ui/astronomy_widgets.py",
    ]

    try:
        # Run tests with coverage
        cmd = [
            "python",
            "-m",
            "pytest",
            "--verbose",
            "--tb=short",
            "--cov=" + ",".join(source_dirs),
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/astronomy",
            "--cov-fail-under=95",  # Aim for 95%+ coverage
        ] + test_dirs

        print(f"Running command: {' '.join(cmd)}")
        print("-" * 60)

        result = subprocess.run(cmd, cwd=project_root, capture_output=False)

        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ All astronomy tests passed!")
            print("📊 Coverage report generated in htmlcov/astronomy/")
            print("🎯 NASA Astronomy Integration: COMPLETE")
        else:
            print("\n" + "=" * 60)
            print("❌ Some tests failed or coverage is below target")
            print("📋 Check the output above for details")

        return result.returncode

    except FileNotFoundError:
        print(
            "❌ pytest not found. Please install it with: pip install pytest pytest-cov"
        )
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def run_specific_test_category(category):
    """Run tests for a specific category."""

    category_map = {
        "models": "tests/unit/test_astronomy/test_models/",
        "api": "tests/unit/test_astronomy/test_api/",
        "managers": "tests/unit/test_astronomy/test_managers/",
        "ui": "tests/unit/test_astronomy/test_ui/",
    }

    if category not in category_map:
        print(f"❌ Unknown category: {category}")
        print(f"Available categories: {', '.join(category_map.keys())}")
        return 1

    test_dir = category_map[category]

    print(f"🧪 Running {category.upper()} tests")
    print("=" * 40)

    try:
        cmd = ["python", "-m", "pytest", "--verbose", "--tb=short", test_dir]

        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode

    except Exception as e:
        print(f"❌ Error running {category} tests: {e}")
        return 1


def show_test_structure():
    """Show the test structure for astronomy module."""

    print("📁 NASA Astronomy Integration Test Structure")
    print("=" * 50)

    test_structure = {
        "tests/unit/test_astronomy/": {
            "test_models/": [
                "test_astronomy_data.py - Core astronomy data models",
                "test_combined_forecast_data.py - Combined weather/astronomy models",
            ],
            "test_api/": [
                "test_nasa_api_manager.py - NASA API integration and services"
            ],
            "test_managers/": [
                "test_astronomy_config.py - Configuration management",
                "test_astronomy_manager.py - Business logic coordination",
                "test_combined_forecast_manager.py - Weather/astronomy integration",
            ],
            "test_ui/": ["test_astronomy_widgets.py - UI components and interactions"],
        }
    }

    def print_structure(structure, indent=0):
        for key, value in structure.items():
            print("  " * indent + f"📂 {key}")
            if isinstance(value, dict):
                print_structure(value, indent + 1)
            elif isinstance(value, list):
                for item in value:
                    print("  " * (indent + 1) + f"📄 {item}")

    print_structure(test_structure)

    print("\n🎯 Test Coverage Goals:")
    print("  • 100% line coverage for all astronomy modules")
    print("  • Comprehensive unit tests with mocking")
    print("  • Integration tests for component interaction")
    print("  • UI tests with pytest-qt")
    print("  • Error handling and edge case coverage")


def main():
    """Main entry point for test runner."""

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "all":
            return run_tests()
        elif command == "structure":
            show_test_structure()
            return 0
        elif command in ["models", "api", "managers", "ui"]:
            return run_specific_test_category(command)
        else:
            print("❌ Unknown command:", command)
            print("\nUsage:")
            print("  python tests/run_astronomy_tests.py all        # Run all tests")
            print("  python tests/run_astronomy_tests.py models     # Run model tests")
            print("  python tests/run_astronomy_tests.py api        # Run API tests")
            print(
                "  python tests/run_astronomy_tests.py managers   # Run manager tests"
            )
            print("  python tests/run_astronomy_tests.py ui         # Run UI tests")
            print(
                "  python tests/run_astronomy_tests.py structure  # Show test structure"
            )
            return 1
    else:
        # Default: run all tests
        return run_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
