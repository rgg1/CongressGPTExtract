"""
Vertical slice implementation for the Congressional Data Extraction project.
This script demonstrates the complete pipeline from raw text to processed JSON with verification checks.
It can run for either house committees or diplomatic offices file from the 117th Congress.
"""

import os
import sys
import json
import argparse
import textwrap
from pathlib import Path

# Import modified tools
try:
    from add_bioguide_id_for_file import add_bioguide_ids_to_file
    from add_thomas_id_for_file import add_thomas_ids_to_file
    from bioguide_id_checker_for_file import check_bioguide_matches
    from thomas_id_checker_for_file import check_thomas_id_matches
    from output_verifier_for_file import verify_output_file
except ImportError:
    print("Error: Required tool files not found. Make sure they are in the same directory as this script.")
    sys.exit(1)

def get_project_root():
    """Get the project root directory."""
    # If running as script
    return Path(os.path.dirname(os.path.abspath(__file__)))

def load_sample_text(file_path, max_lines=100):
    """
    Load a sample from the original text file to demonstrate input format.
    
    Args:
        file_path: Path to the input text file
        max_lines: Maximum number of lines to load
        
    Returns:
        String with the sample text
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line)
            return ''.join(lines)
    except Exception as e:
        return f"Error loading sample text: {str(e)}"

def extract_prompts():
    """
    Extract prompt templates from the parsing files to show how GPT is instructed.
    
    Returns:
        Dictionary with prompts for each file type
    """
    prompts = {}
    
    # Path to the gpt_parsing_files directory
    root_dir = get_project_root()
    parsing_dir = root_dir / "gpt_parsing_files"
    
    # Files to check for prompts
    files_to_check = {
        "house_senate_committees.py": "house_committees",
        "diplomatic_offices.py": "diplomatic_offices"
    }
    
    # Extract prompts from each file
    for file_name, key in files_to_check.items():
        file_path = parsing_dir / file_name
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                # Look for the system prompt in the extract_* function
                if "content\": \"\"\"" in content:
                    start = content.find("content\": \"\"\"") + 13
                    end = content.find("\"\"\",", start)
                    if start > 0 and end > start:
                        prompt = content[start:end].strip()
                        # Clean up and format the prompt
                        prompts[key] = textwrap.dedent(prompt)
        except Exception as e:
            prompts[key] = f"Error extracting prompt: {str(e)}"
    
    return prompts

def sample_json_output(json_file, max_entries=2):
    """
    Create a sample of the JSON output by extracting a few entries.
    
    Args:
        json_file: Path to the JSON file
        max_entries: Maximum number of entries to include in the sample
        
    Returns:
        Dictionary with a sample of the output
    """
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Create a copy of the data
        sample = {}
        
        # Handle different types of files
        if "committees" in data:
            sample["committees"] = data["committees"][:max_entries]
            # Limit subcommittees too
            for committee in sample["committees"]:
                if "subcommittees" in committee and len(committee["subcommittees"]) > max_entries:
                    committee["subcommittees"] = committee["subcommittees"][:max_entries]
                    # Add a note that this is a subset
                    committee["subcommittees"].append({"note": f"... {len(committee['subcommittees']) - max_entries} more subcommittees not shown"})
                    
        elif "diplomatic_representatives" in data:
            sample["diplomatic_representatives"] = data["diplomatic_representatives"][:max_entries * 3]  # Show more for diplomatic since they're simpler
            # Add a note that this is a subset
            if len(data["diplomatic_representatives"]) > max_entries * 3:
                sample["diplomatic_representatives"].append({"note": f"... {len(data['diplomatic_representatives']) - max_entries * 3} more representatives not shown"})
        
        # Return pretty-printed JSON
        return json.dumps(sample, indent=2)
    
    except Exception as e:
        return f"Error creating sample JSON: {str(e)}"

def get_vertical_slice_house_committees():
    """
    Run a vertical slice for the House Committees file from the 117th Congress.
    This demonstrates the complete pipeline from raw text to processed JSON with verification checks.
    """
    root_dir = get_project_root()
    
    # Paths for House Committees
    input_text_path = root_dir / "congressional_directory_files" / "congress_117" / "txt" / "CDIR-2022-10-26-HOUSECOMMITTEES.txt"
    output_json_path = root_dir / "outputs" / "117" / "CDIR-2022-10-26-HOUSECOMMITTEES.txt_output.json"
    legislators_csv_path = root_dir / "legislators.csv"
    committee_names_csv_path = root_dir / "committee_names.csv"
    
    # Check if required files exist
    required_files = [input_text_path, output_json_path, legislators_csv_path, committee_names_csv_path]
    for file_path in required_files:
        if not file_path.exists():
            print(f"Error: Required file not found - {file_path}")
            return False
    
    # Output paths for the enriched files
    bioguide_output_path = root_dir / "CDIR-2022-10-26-HOUSECOMMITTEES.txt_with_bioguide.json"
    thomas_output_path = root_dir / "CDIR-2022-10-26-HOUSECOMMITTEES.txt_with_thomas_ids.json"
    
    # Step 1: Show sample of input text
    print("\n" + "=" * 80)
    print("STEP 1: SAMPLE INPUT TEXT (HOUSE COMMITTEES)")
    print("=" * 80)
    sample_text = load_sample_text(input_text_path)
    print(sample_text[:1500] + "\n...\n")  # Show first 1500 characters
    
    # Step 2: Show the prompt used for GPT
    print("\n" + "=" * 80)
    print("STEP 2: GPT PROMPT TEMPLATE FOR HOUSE COMMITTEES")
    print("=" * 80)
    prompts = extract_prompts()
    if "house_committees" in prompts:
        print(prompts["house_committees"][:1500] + "\n...\n")  # Show first 1500 characters
    else:
        print("Prompt not found for house_committees")
    
    # Step 3: Show sample of GPT output
    print("\n" + "=" * 80)
    print("STEP 3: SAMPLE JSON OUTPUT FROM GPT")
    print("=" * 80)
    json_sample = sample_json_output(output_json_path)
    print(json_sample[:1500] + "\n...\n")  # Show first 1500 characters
    
    # Step 4: Run verification on the output
    print("\n" + "=" * 80)
    print("STEP 4: OUTPUT VERIFICATION")
    print("=" * 80)
    verify_output_file(str(output_json_path))
    
    # Step 5: Add BioGuide IDs and check matches
    print("\n" + "=" * 80)
    print("STEP 5: ADD AND VERIFY BIOGUIDE IDs")
    print("=" * 80)
    add_bioguide_ids_to_file(str(output_json_path), str(legislators_csv_path), str(bioguide_output_path))
    check_bioguide_matches(str(bioguide_output_path))
    
    # Step 6: Add Thomas IDs and check matches
    print("\n" + "=" * 80)
    print("STEP 6: ADD AND VERIFY THOMAS IDs")
    print("=" * 80)
    add_thomas_ids_to_file(str(output_json_path), str(committee_names_csv_path), str(thomas_output_path))
    check_thomas_id_matches(str(thomas_output_path))
    
    # Step 7: Show sample of final enriched output
    print("\n" + "=" * 80)
    print("STEP 7: SAMPLE OF FINAL ENRICHED OUTPUT")
    print("=" * 80)
    enriched_json_sample = sample_json_output(str(thomas_output_path))
    print(enriched_json_sample[:1500] + "\n...\n")  # Show first 1500 characters
    
    return True

def get_vertical_slice_diplomatic_offices():
    """
    Run a vertical slice for the Diplomatic Offices file from the 117th Congress.
    This demonstrates the complete pipeline from raw text to processed JSON with verification checks.
    """
    root_dir = get_project_root()
    
    # Paths for Diplomatic Offices
    input_text_path = root_dir / "congressional_directory_files" / "congress_117" / "txt" / "CDIR-2022-10-26-DIPLOMATICOFFICES.txt"
    output_json_path = root_dir / "outputs" / "117" / "CDIR-2022-10-26-DIPLOMATICOFFICES.txt_output.json"
    
    # Check if required files exist
    required_files = [input_text_path, output_json_path]
    for file_path in required_files:
        if not file_path.exists():
            print(f"Error: Required file not found - {file_path}")
            return False
    
    # Step 1: Show sample of input text
    print("\n" + "=" * 80)
    print("STEP 1: SAMPLE INPUT TEXT (DIPLOMATIC OFFICES)")
    print("=" * 80)
    sample_text = load_sample_text(input_text_path)
    print(sample_text[:1500] + "\n...\n")  # Show first 1500 characters
    
    # Step 2: Show the prompt used for GPT
    print("\n" + "=" * 80)
    print("STEP 2: GPT PROMPT TEMPLATE FOR DIPLOMATIC OFFICES")
    print("=" * 80)
    prompts = extract_prompts()
    if "diplomatic_offices" in prompts:
        print(prompts["diplomatic_offices"][:1500] + "\n...\n")  # Show first 1500 characters
    else:
        print("Prompt not found for diplomatic_offices")
    
    # Step 3: Show sample of GPT output
    print("\n" + "=" * 80)
    print("STEP 3: SAMPLE JSON OUTPUT FROM GPT")
    print("=" * 80)
    json_sample = sample_json_output(output_json_path)
    print(json_sample[:1500] + "\n...\n")  # Show first 1500 characters
    
    # Step 4: Run verification on the output
    print("\n" + "=" * 80)
    print("STEP 4: OUTPUT VERIFICATION")
    print("=" * 80)
    verify_output_file(str(output_json_path))
    
    return True

def main():
    """Main function to run the vertical slice for either House Committees or Diplomatic Offices."""
    parser = argparse.ArgumentParser(description="Run a vertical slice for the Congressional Data Extraction project.")
    parser.add_argument("--type", choices=["house", "diplomatic", "both"], default="both",
                      help="Type of data to process: 'house' for House Committees, 'diplomatic' for Diplomatic Offices, or 'both' for both (default)")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("CONGRESSIONAL DATA EXTRACTION - VERTICAL SLICE")
    print("=" * 80)
    print("This script demonstrates the complete pipeline from raw text to processed JSON with verification checks.")
    
    if args.type in ["house", "both"]:
        print("\n" + "=" * 80)
        print("VERTICAL SLICE: HOUSE COMMITTEES")
        print("=" * 80)
        get_vertical_slice_house_committees()
    
    if args.type in ["diplomatic", "both"]:
        print("\n" + "=" * 80)
        print("VERTICAL SLICE: DIPLOMATIC OFFICES")
        print("=" * 80)
        get_vertical_slice_diplomatic_offices()
    
    print("\n" + "=" * 80)
    print("VERTICAL SLICE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()