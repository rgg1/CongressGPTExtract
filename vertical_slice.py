"""
This script demonstrates the complete pipeline from raw text to processed JSON with verification
checks. It can run for either house committees or diplomatic offices file from the 117th Congress
(These are imply the files I decided to test, you could make slight modifications to
do the same for other file types/from other congresses).
"""

import os
import sys
import json
import argparse
import textwrap
from pathlib import Path

# Add the tools directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.join(script_dir, "tools")
sys.path.insert(0, tools_dir)

# Import functions from files in tools directory
try:
    from add_bioguide_id import add_bioguide_ids_to_file
    from add_thomas_id import add_thomas_ids_to_file
    from bioguide_id_checker import check_bioguide_matches
    from thomas_id_checker import check_thomas_id_matches
    from output_verifier import verify_output_file
except ImportError:
    print(
        "Error: Required tool files not found. Make sure the tools directory contains the updated files."
    )
    sys.exit(1)

def get_project_root():
    """Get the project root directory."""
    # If running as script
    return Path(os.path.dirname(os.path.abspath(__file__)))

def load_sample_text(file_path: str, max_lines: int = 100) -> str:
    """
    Load a sample from the original text file to demonstrate input format.

    Args:
        file_path: Path to the input text file
        max_lines: Maximum number of lines to load

    Returns: Sample text
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line)
            return "".join(lines)
    except Exception as e:
        return f"Error loading sample text: {str(e)}"

def extract_prompts() -> dict:
    """
    Extract prompt templates from the parsing files to show how GPT is instructed.

    Returns: Mapping of prompt names to the extracted prompts
    """
    prompts = {}

    root_dir = get_project_root()
    parsing_dir = root_dir / "gpt_parsing_files"

    files_to_check = {
        "house_senate_committees.py": "house_committees",
        "diplomatic_offices.py": "diplomatic_offices",
    }

    # Extract prompts from each file
    for file_name, key in files_to_check.items():
        file_path = parsing_dir / file_name
        try:
            with open(file_path, "r") as f:
                content = f.read()
                # Look for the system prompt in the extract_* function
                if 'content": """' in content:
                    start = content.find('content": """') + 13
                    end = content.find('""",', start)
                    if start > 0 and end > start:
                        prompt = content[start:end].strip()
                        # Clean up and format the prompt
                        prompts[key] = textwrap.dedent(prompt)
        except Exception as e:
            prompts[key] = f"Error extracting prompt: {str(e)}"

    return prompts

def sample_json_output(json_file: str, max_entries: int = 2) -> str:
    """
    Create a sample of the JSON output by extracting a few entries.

    Args:
        json_file: Path to the JSON file
        max_entries: Maximum number of entries to include in the sample

    Returns: Mapping of prompt names to the extracted prompts
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        sample = {}

        # Handle different types of files
        if "committees" in data:
            sample["committees"] = data["committees"][:max_entries]
            for committee in sample["committees"]:
                if (
                    "subcommittees" in committee
                    and len(committee["subcommittees"]) > max_entries
                ):
                    committee["subcommittees"] = committee["subcommittees"][
                        :max_entries
                    ]
                    committee["subcommittees"].append(
                        {
                            "note": f"... {len(committee['subcommittees']) - max_entries} more subcommittees not shown"
                        }
                    )

        elif "diplomatic_representatives" in data:
            sample["diplomatic_representatives"] = data["diplomatic_representatives"][
                : max_entries * 3
            ]  # Show more for diplomatic since they're simpler
            if len(data["diplomatic_representatives"]) > max_entries * 3:
                sample["diplomatic_representatives"].append(
                    {
                        "note": f"... {len(data['diplomatic_representatives']) - max_entries * 3} more representatives not shown"
                    }
                )

        return json.dumps(sample, indent=2)

    except Exception as e:
        return f"Error creating sample JSON: {str(e)}"

def get_vertical_slice_house_committees() -> bool:
    """
    Run a vertical slice for the House Committees file from the 117th Congress.

    Returns: True if the slice was successful
    """
    root_dir = get_project_root()

    input_text_path = (
        root_dir
        / "congressional_directory_files"
        / "congress_117"
        / "txt"
        / "CDIR-2022-10-26-HOUSECOMMITTEES.txt"
    )
    output_json_path = (
        root_dir / "outputs" / "117" / "CDIR-2022-10-26-HOUSECOMMITTEES.txt_output.json"
    )
    legislators_csv_path = root_dir / "legislators.csv"
    committee_names_csv_path = root_dir / "committee_names.csv"

    required_files = [
        input_text_path,
        output_json_path,
        legislators_csv_path,
        committee_names_csv_path,
    ]
    for file_path in required_files:
        if not file_path.exists():
            print(f"Error: Required file not found - {file_path}")
            return False

    bioguide_output_path = (
        root_dir / "CDIR-2022-10-26-HOUSECOMMITTEES.txt_with_bioguide.json"
    )
    thomas_output_path = (
        root_dir / "CDIR-2022-10-26-HOUSECOMMITTEES.txt_with_thomas_ids.json"
    )

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
        print(
            prompts["house_committees"][:1500] + "\n...\n"
        )  # Show first 1500 characters
    else:
        print("Prompt not found for house_committees")

    # Step 3: Show sample of GPT output
    print("\n" + "=" * 80)
    print("STEP 3: SAMPLE JSON OUTPUT FROM GPT")
    print("=" * 80)
    json_sample = sample_json_output(output_json_path)
    print(json_sample[:1500] + "\n...\n")  # Show first 1500 characters

    # Step 4: Run verification on the output using the function
    # from the tools/output_verifier.py file
    print("\n" + "=" * 80)
    print("STEP 4: OUTPUT VERIFICATION")
    print("=" * 80)
    verify_output_file(str(output_json_path))

    # Step 5: Add BioGuide IDs and check matches
    print("\n" + "=" * 80)
    print("STEP 5: ADD AND VERIFY BIOGUIDE IDs")
    print("=" * 80)
    add_bioguide_ids_to_file(
        str(output_json_path), str(legislators_csv_path), str(bioguide_output_path)
    )
    check_bioguide_matches(str(bioguide_output_path))

    # Step 6: Add Thomas IDs and check matches
    print("\n" + "=" * 80)
    print("STEP 6: ADD AND VERIFY THOMAS IDs")
    print("=" * 80)
    add_thomas_ids_to_file(
        str(output_json_path), str(committee_names_csv_path), str(thomas_output_path)
    )
    check_thomas_id_matches(str(thomas_output_path))

    # Step 7: Show sample of final output (JSON with Thomas IDs)
    print("\n" + "=" * 80)
    print("STEP 7: SAMPLE OF FINAL ENRICHED OUTPUT")
    print("=" * 80)
    enriched_json_sample = sample_json_output(str(thomas_output_path))
    print(enriched_json_sample[:1500] + "\n...\n")  # Show first 1500 characters

    return True

def get_vertical_slice_diplomatic_offices() -> bool:
    """
    Run a vertical slice for the Diplomatic Offices file from the 117th Congress.

    Returns: True if the slice was successful
    """
    root_dir = get_project_root()

    input_text_path = (
        root_dir
        / "congressional_directory_files"
        / "congress_117"
        / "txt"
        / "CDIR-2022-10-26-DIPLOMATICOFFICES.txt"
    )
    output_json_path = (
        root_dir
        / "outputs"
        / "117"
        / "CDIR-2022-10-26-DIPLOMATICOFFICES.txt_output.json"
    )

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
        print(
            prompts["diplomatic_offices"][:1500] + "\n...\n"
        )  # Show first 1500 characters
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
    parser = argparse.ArgumentParser(
        description="Run a vertical slice for the Congressional Data Extraction project."
    )
    parser.add_argument(
        "--type",
        choices=["house", "diplomatic", "both"],
        default="both",
        help="Type of data to process: 'house' for House Committees, 'diplomatic' for Diplomatic Offices, or 'both' for both (default)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("CONGRESSIONAL DATA EXTRACTION - VERTICAL SLICE")
    print("=" * 80)
    print(
        "This script demonstrates the complete pipeline from raw text to processed JSON with verification checks."
    )

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
