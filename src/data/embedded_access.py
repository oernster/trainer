
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
