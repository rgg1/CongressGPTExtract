import os
import json
import sys

def validate_output(congress):
    """
    Validates the output files produced by the executable.
    
    Args:
        congress: Congress session number
    
    Returns:
        True if valid output is found, False otherwise
    """
    output_dir = os.path.join('outputs', congress)
    
    # Check if directory exists
    if not os.path.exists(output_dir):
        print('ERROR: Output directory does not exist')
        return False
    
    # List files in directory
    files = os.listdir(output_dir)
    json_files = [f for f in files if f.endswith('.json')]
    
    print('Files in output directory:')
    for f in files:
        print(f'  - {f}')
    
    if not json_files:
        print('ERROR: No JSON files found')
        return False
    
    # Check if any JSON file has content
    for filename in json_files:
        filepath = os.path.join(output_dir, filename)
        print(f'Checking file: {filepath}')
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if data and isinstance(data, dict) and 'diplomatic_representatives' in data:
                    print(f'SUCCESS: File contains valid JSON data with {len(data["diplomatic_representatives"])} entries')
                    return True
        except Exception as e:
            print(f'Error checking file: {str(e)}')
    
    print('ERROR: No valid output files found')
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_validator.py <congress_number>")
        sys.exit(1)
    
    congress = sys.argv[1]
    print(f"Validating output for Congress {congress}...")
    
    if validate_output(congress):
        print('Test passed: Executable generated valid output')
        sys.exit(0)
    else:
        print('Test failed: Executable did not generate valid output')
        sys.exit(1)