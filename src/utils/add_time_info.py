import json
import os
import random
from datetime import datetime, timedelta

def get_line_frequency(line_name):
    """
    Return appropriate frequency information based on the line type
    """
    # Default frequencies
    default = {
        "weekday_peak": "Every hour",
        "weekday_off_peak": "Every 2 hours",
        "weekend": "Every 2 hours",
        "night": "No service"
    }
    
    # Line-specific frequencies
    frequencies = {
        # Metro/Subway systems
        "Tyne and Wear Metro": {
            "weekday_peak": "Every 12 minutes",
            "weekday_off_peak": "Every 15 minutes",
            "weekend": "Every 15 minutes",
            "night": "Limited service"
        },
        "Glasgow Subway": {
            "weekday_peak": "Every 4 minutes",
            "weekday_off_peak": "Every 6 minutes",
            "weekend": "Every 8 minutes",
            "night": "No service"
        },
        
        # Commuter lines
        "Marston Vale Line": {
            "weekday_peak": "Every 30 minutes",
            "weekday_off_peak": "Every hour",
            "weekend": "Every hour",
            "night": "No service"
        },
        "Severn Beach Line": {
            "weekday_peak": "Every 30 minutes",
            "weekday_off_peak": "Every hour",
            "weekend": "Every hour",
            "night": "No service"
        },
        
        # Rural lines
        "Esk Valley Line": {
            "weekday_peak": "Every 2 hours",
            "weekday_off_peak": "Every 3 hours",
            "weekend": "Every 3 hours",
            "night": "No service"
        },
        "Furness Line": {
            "weekday_peak": "Every hour",
            "weekday_off_peak": "Every 2 hours",
            "weekend": "Every 2 hours",
            "night": "No service"
        },
        "Borders Railway": {
            "weekday_peak": "Every 30 minutes",
            "weekday_off_peak": "Every hour",
            "weekend": "Every hour",
            "night": "No service"
        },
        "Fife Circle Line": {
            "weekday_peak": "Every 30 minutes",
            "weekday_off_peak": "Every hour",
            "weekend": "Every hour",
            "night": "No service"
        },
        "Highland Main Line": {
            "weekday_peak": "Every 2 hours",
            "weekday_off_peak": "Every 3 hours",
            "weekend": "Every 3 hours",
            "night": "No service"
        },
        "Far North Line": {
            "weekday_peak": "Every 3 hours",
            "weekday_off_peak": "Every 4 hours",
            "weekend": "Every 4 hours",
            "night": "No service"
        },
        "Kyle Line": {
            "weekday_peak": "Every 3 hours",
            "weekday_off_peak": "Every 4 hours",
            "weekend": "Every 4 hours",
            "night": "No service"
        },
        "Tarka Line": {
            "weekday_peak": "Every hour",
            "weekday_off_peak": "Every 2 hours",
            "weekend": "Every 2 hours",
            "night": "No service"
        },
        "Cotswold Line": {
            "weekday_peak": "Every hour",
            "weekday_off_peak": "Every 2 hours",
            "weekend": "Every 2 hours",
            "night": "No service"
        }
    }
    
    return frequencies.get(line_name, default)

def generate_times_for_station(station_index, total_stations, line_type):
    """
    Generate realistic time information for a station based on its position and line type
    """
    # Base times for first station
    if line_type == "metro":
        # Metro/Subway - frequent service
        morning_base = ["05:00", "05:10", "05:20", "05:30", "05:40", "05:50",
                        "06:00", "06:10", "06:20", "06:30", "06:40", "06:50",
                        "07:00", "07:10", "07:20", "07:30", "07:40", "07:50",
                        "08:00", "08:10", "08:20", "08:30", "08:40", "08:50",
                        "09:00", "09:10", "09:20", "09:30", "09:40", "09:50",
                        "10:00", "10:10", "10:20", "10:30", "10:40", "10:50",
                        "11:00", "11:10", "11:20", "11:30", "11:40", "11:50"]
        afternoon_base = ["12:00", "12:10", "12:20", "12:30", "12:40", "12:50",
                          "13:00", "13:10", "13:20", "13:30", "13:40", "13:50",
                          "14:00", "14:10", "14:20", "14:30", "14:40", "14:50",
                          "15:00", "15:10", "15:20", "15:30", "15:40", "15:50",
                          "16:00", "16:10", "16:20", "16:30", "16:40", "16:50",
                          "17:00", "17:10", "17:20", "17:30", "17:40", "17:50"]
        evening_base = ["18:00", "18:10", "18:20", "18:30", "18:40", "18:50",
                        "19:00", "19:10", "19:20", "19:30", "19:40", "19:50",
                        "20:00", "20:10", "20:20", "20:30", "20:40", "20:50",
                        "21:00", "21:10", "21:20", "21:30", "21:40", "21:50",
                        "22:00", "22:10", "22:20", "22:30", "22:40", "22:50",
                        "23:00", "23:10", "23:20", "23:30", "23:40", "23:50"]
        night_base = ["00:00", "00:15", "00:30", "00:45"]
    elif line_type == "commuter":
        # Commuter line - regular service
        morning_base = ["05:30", "06:00", "06:30", "07:00", "07:15", "07:30", "07:45",
                        "08:00", "08:15", "08:30", "08:45", "09:00", "09:30", "10:00",
                        "10:30", "11:00", "11:30"]
        afternoon_base = ["12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
                          "15:00", "15:30", "16:00", "16:15", "16:30", "16:45",
                          "17:00", "17:15", "17:30", "17:45"]
        evening_base = ["18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
                        "21:00", "21:30", "22:00", "22:30", "23:00", "23:30"]
        night_base = []
    else:
        # Rural line - less frequent service
        morning_base = ["06:00", "08:00", "10:00"]
        afternoon_base = ["12:00", "14:00", "16:00"]
        evening_base = ["18:00", "20:00", "22:00"]
        night_base = []
    
    # Calculate time offset based on station position
    # Assuming each station adds 5-15 minutes to the journey
    min_offset = 5 * station_index
    max_offset = 15 * station_index
    offset_minutes = random.randint(min_offset, max_offset)
    
    # Apply offset to all times
    def add_minutes(time_str, minutes):
        time_obj = datetime.strptime(time_str, "%H:%M")
        new_time = time_obj + timedelta(minutes=minutes)
        return new_time.strftime("%H:%M")
    
    morning = [add_minutes(t, offset_minutes) for t in morning_base]
    afternoon = [add_minutes(t, offset_minutes) for t in afternoon_base]
    evening = [add_minutes(t, offset_minutes) for t in evening_base]
    night = [add_minutes(t, offset_minutes) for t in night_base] if night_base else []
    
    return {
        "morning": morning,
        "afternoon": afternoon,
        "evening": evening,
        "night": night
    }

def determine_line_type(line_name):
    """
    Determine the type of line based on its name
    """
    metro_lines = ["Tyne and Wear Metro", "Glasgow Subway"]
    commuter_lines = ["Marston Vale Line", "Severn Beach Line", "Borders Railway", "Fife Circle Line"]
    
    if line_name in metro_lines:
        return "metro"
    elif line_name in commuter_lines:
        return "commuter"
    else:
        return "rural"

def process_file(file_path):
    """
    Process a single JSON file to add time information
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Skip if already has frequency information
        if "frequency" in data.get("metadata", {}):
            print(f"Skipping {file_path} - already has frequency information")
            return
        
        line_name = data.get("metadata", {}).get("line_name", "")
        if not line_name:
            print(f"Skipping {file_path} - no line name found")
            return
        
        # Add frequency information
        data["metadata"]["frequency"] = get_line_frequency(line_name)
        
        # Determine line type
        line_type = determine_line_type(line_name)
        
        # Add time information to each station
        total_stations = len(data.get("stations", []))
        for i, station in enumerate(data.get("stations", [])):
            # Skip if already has time information
            if "times" in station:
                continue
            
            station["times"] = generate_times_for_station(i, total_stations, line_type)
        
        # Write updated data back to file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Updated {file_path}")
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    """
    Main function to process all JSON files in the lines directory
    """
    lines_dir = "src/data/lines"
    
    # Get list of JSON files
    json_files = [os.path.join(lines_dir, f) for f in os.listdir(lines_dir) if f.endswith('.json')]
    
    print(f"Found {len(json_files)} JSON files")
    
    # Process each file
    for file_path in json_files:
        process_file(file_path)
    
    print("Done!")

if __name__ == "__main__":
    main()