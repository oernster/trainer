import json
import os
import sys
from colorama import init, Fore, Style

# Initialize colorama for colored terminal output
init()

def check_file(file_path):
    """
    Check if a JSON file has the required time and frequency data
    Returns a tuple of (is_valid, issues)
    """
    issues = []
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check if metadata has frequency information
        if "metadata" not in data:
            issues.append(f"Missing metadata section")
            return False, issues
        
        if "frequency" not in data["metadata"]:
            issues.append(f"Missing frequency information in metadata")
        else:
            # Check if frequency has all required fields
            frequency = data["metadata"]["frequency"]
            required_frequency_fields = ["weekday_peak", "weekday_off_peak", "weekend", "night"]
            for field in required_frequency_fields:
                if field not in frequency:
                    issues.append(f"Missing {field} in frequency data")
        
        # Check if stations have time information
        if "stations" not in data:
            issues.append(f"Missing stations section")
            return False, issues
        
        for i, station in enumerate(data["stations"]):
            if "name" not in station:
                station_name = f"Station #{i+1}"
            else:
                station_name = station["name"]
                
            if "times" not in station:
                issues.append(f"Station '{station_name}' is missing time information")
            else:
                # Check if times has all required fields
                times = station["times"]
                required_time_fields = ["morning", "afternoon", "evening", "night"]
                for field in required_time_fields:
                    if field not in times:
                        issues.append(f"Station '{station_name}' is missing {field} in time data")
        
        return len(issues) == 0, issues
    
    except Exception as e:
        issues.append(f"Error processing file: {str(e)}")
        return False, issues

def main():
    """
    Main function to verify all JSON files in the lines directory
    """
    lines_dir = "src/data/lines"
    
    # Get list of JSON files
    json_files = [os.path.join(lines_dir, f) for f in os.listdir(lines_dir) if f.endswith('.json')]
    
    print(f"Found {len(json_files)} JSON files to verify")
    
    # Track statistics
    valid_files = 0
    invalid_files = 0
    files_with_issues = []
    
    # Process each file
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        is_valid, issues = check_file(file_path)
        
        if is_valid:
            valid_files += 1
            print(f"{Fore.GREEN}✓ {file_name} - Valid{Style.RESET_ALL}")
        else:
            invalid_files += 1
            print(f"{Fore.RED}✗ {file_name} - Invalid{Style.RESET_ALL}")
            for issue in issues:
                print(f"  {Fore.YELLOW}• {issue}{Style.RESET_ALL}")
            files_with_issues.append((file_name, issues))
    
    # Print summary
    print("\n" + "="*50)
    print(f"Verification Summary:")
    print(f"  Total files: {len(json_files)}")
    print(f"  Valid files: {valid_files}")
    print(f"  Invalid files: {invalid_files}")
    
    if invalid_files > 0:
        print("\nFiles with issues:")
        for file_name, issues in files_with_issues:
            print(f"  {Fore.RED}{file_name}{Style.RESET_ALL} - {len(issues)} issues")
        
        print(f"\n{Fore.RED}Verification failed!{Style.RESET_ALL} Please fix the issues listed above.")
        sys.exit(1)
    else:
        print(f"\n{Fore.GREEN}Verification successful!{Style.RESET_ALL} All files have the required time and frequency data.")
        sys.exit(0)

if __name__ == "__main__":
    main()