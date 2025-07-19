"""
Data path resolver for finding data files in both development and packaged environments.
"""
import os
import sys
from pathlib import Path


def get_data_directory() -> Path:
    """
    Get the data directory path that works in both development and packaged environments.
    
    Returns:
        Path to the data directory
    """
    # Method 1: Check if we're running from a packaged executable
    if getattr(sys, 'frozen', False):
        # We're running from a packaged executable
        # Data should be in a 'data' directory next to the executable
        exe_dir = Path(sys.executable).parent
        data_dir = exe_dir / "data"
        if data_dir.exists():
            return data_dir
            
        # Also check for src/data structure (for compatibility)
        src_data_dir = exe_dir / "src" / "data"
        if src_data_dir.exists():
            return src_data_dir
    
    # Method 2: Development environment - relative to this file
    # This file is in src/utils/, so data is at ../data/
    dev_data_dir = Path(__file__).parent.parent / "data"
    if dev_data_dir.exists():
        return dev_data_dir
    
    # Method 3: Check current working directory
    cwd_data_dir = Path.cwd() / "src" / "data"
    if cwd_data_dir.exists():
        return cwd_data_dir
        
    # Method 4: Check one level up from current working directory
    parent_data_dir = Path.cwd().parent / "src" / "data"
    if parent_data_dir.exists():
        return parent_data_dir
    
    # Method 5: Last resort - check common locations
    possible_locations = [
        Path("data"),
        Path("src/data"),
        Path("../data"),
        Path("../src/data"),
    ]
    
    for location in possible_locations:
        if location.exists() and location.is_dir():
            return location.resolve()
    
    # If we still can't find it, raise an error
    raise FileNotFoundError(
        "Could not find data directory. Searched in:\n" +
        f"- Executable directory: {Path(sys.executable).parent if getattr(sys, 'frozen', False) else 'N/A'}\n" +
        f"- Development path: {Path(__file__).parent.parent / 'data'}\n" +
        f"- Current directory: {Path.cwd()}\n" +
        "Please ensure the data directory exists in the expected location."
    )


def get_lines_directory() -> Path:
    """Get the lines subdirectory within the data directory."""
    return get_data_directory() / "lines"


def get_data_file_path(filename: str) -> Path:
    """
    Get the full path to a data file.
    
    Args:
        filename: Name of the file (e.g., 'railway_lines_index.json')
        
    Returns:
        Full path to the file
    """
    return get_data_directory() / filename


def get_line_file_path(line_filename: str) -> Path:
    """
    Get the full path to a line data file.
    
    Args:
        line_filename: Name of the line file (e.g., 'central_line.json')
        
    Returns:
        Full path to the line file
    """
    return get_lines_directory() / line_filename