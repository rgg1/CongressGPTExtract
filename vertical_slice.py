"""
This script demonstrates the complete pipeline from raw text to processed JSON with verification
checks. It can run for either house committees or diplomatic offices file from the 117th Congress.
All output is written to a text file instead of the console.
"""

import os
import sys
import json
import argparse
import textwrap
from pathlib import Path
from io import StringIO
import contextlib

script_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.join(script_dir, "tools")
sys.path.insert(0, tools_dir)

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

output_file = None

# capture print output
@contextlib.contextmanager
def capture_output():
    old_stdout = sys.stdout
    stdout_buffer = StringIO()
    sys.stdout = stdout_buffer
    try:
        yield stdout_buffer
    finally:
        sys.stdout = old_stdout
        if output_file:
            output_file.write(stdout_buffer.getvalue())

def write_to_file(text: str):
    """
    Write text to the output file.
    
    Args:
        text: Text to write
    """
    if output_file:
        output_file.write(text + "\n")

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
            return "".join(lines) + "\n[...truncated...]"
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

def sample_json_output(json_file: str) -> str:
    """
    Create a sample of the JSON output, approximately 100 lines.

    Args:
        json_file: Path to the JSON file

    Returns: Sample of the JSON data as a formatted string, ~100 lines
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        formatted_json = json.dumps(data, indent=2)
        lines = formatted_json.split('\n')
        
        # Truncate
        if len(lines) > 100:
            sample_lines = lines[:100]
            sample_lines.append("...")
            sample_lines.append(f"[...truncated {len(lines) - 100} more lines...]")
            return '\n'.join(sample_lines)
        else:
            return formatted_json

    except Exception as e:
        return f"Error creating sample JSON: {str(e)}"

def get_vertical_slice_house_committees() -> bool:
    """
    Run a vertical slice for the House Committees file from the 117th Congress.
    Saves all output to a file.

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
            write_to_file(f"Error: Required file not found - {file_path}")
            return False

    bioguide_output_path = (
        root_dir / "CDIR-2022-10-26-HOUSECOMMITTEES.txt_with_bioguide.json"
    )
    thomas_output_path = (
        root_dir / "CDIR-2022-10-26-HOUSECOMMITTEES.txt_with_thomas_ids.json"
    )

    # Step 1: Show sample of input text
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 1: SAMPLE INPUT TEXT (HOUSE COMMITTEES)")
    write_to_file("=" * 80)
    sample_text = load_sample_text(input_text_path)
    write_to_file(sample_text)

    # Step 2: Show the prompt used for GPT
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 2: GPT PROMPT TEMPLATE FOR HOUSE COMMITTEES")
    write_to_file("=" * 80)
    prompts = extract_prompts()
    if "house_committees" in prompts:
        write_to_file(prompts["house_committees"])
    else:
        write_to_file("Prompt not found for house_committees")

    # Step 3: Show sample of GPT output
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 3: SAMPLE JSON OUTPUT FROM GPT")
    write_to_file("=" * 80)
    json_sample = sample_json_output(output_json_path)
    write_to_file(json_sample)

    # Step 4: Run verification on the output using the function
    # from the tools/output_verifier.py file
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 4: OUTPUT VERIFICATION")
    write_to_file("=" * 80)
    with capture_output():
        verify_output_file(str(output_json_path))

    # Step 5: Add BioGuide IDs and check matches
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 5: ADD AND VERIFY BIOGUIDE IDs")
    write_to_file("=" * 80)
    with capture_output():
        add_bioguide_ids_to_file(
            str(output_json_path), str(legislators_csv_path), str(bioguide_output_path)
        )
        check_bioguide_matches(str(bioguide_output_path))

    # Step 6: Add Thomas IDs and check matches
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 6: ADD AND VERIFY THOMAS IDs")
    write_to_file("=" * 80)
    with capture_output():
        add_thomas_ids_to_file(
            str(output_json_path), str(committee_names_csv_path), str(thomas_output_path)
        )
        check_thomas_id_matches(str(thomas_output_path))

    # Step 7: Show sample of final output (JSON with Thomas IDs)
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 7: SAMPLE OF ENRICHED OUTPUT")
    write_to_file("=" * 80)
    enriched_json_sample = sample_json_output(str(thomas_output_path))
    write_to_file(enriched_json_sample)

    return True

def get_vertical_slice_diplomatic_offices() -> bool:
    """
    Run a vertical slice for the Diplomatic Offices file from the 117th Congress.
    Saves all output to a file.

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
            write_to_file(f"Error: Required file not found - {file_path}")
            return False

    # Step 1: Show sample of input text
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 1: SAMPLE INPUT TEXT (DIPLOMATIC OFFICES)")
    write_to_file("=" * 80)
    sample_text = load_sample_text(input_text_path)
    write_to_file(sample_text)

    # Step 2: Show the prompt used for GPT
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 2: GPT PROMPT TEMPLATE FOR DIPLOMATIC OFFICES")
    write_to_file("=" * 80)
    prompts = extract_prompts()
    if "diplomatic_offices" in prompts:
        write_to_file(prompts["diplomatic_offices"])
    else:
        write_to_file("Prompt not found for diplomatic_offices")

    # Step 3: Show sample of GPT output
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 3: SAMPLE JSON OUTPUT FROM GPT")
    write_to_file("=" * 80)
    json_sample = sample_json_output(output_json_path)
    write_to_file(json_sample)

    # Step 4: Run verification on the output
    write_to_file("\n" + "=" * 80)
    write_to_file("STEP 4: OUTPUT VERIFICATION")
    write_to_file("=" * 80)
    with capture_output():
        verify_output_file(str(output_json_path))

    return True

def main():
    """Main function to run the vertical slice and save all output to a file."""
    parser = argparse.ArgumentParser(
        description="Run a vertical slice for the Congressional Data Extraction project and save output to a file."
    )
    parser.add_argument(
        "--type",
        choices=["house", "diplomatic", "both"],
        default="both",
        help="Type of data to process: 'house' for House Committees, 'diplomatic' for Diplomatic Offices, or 'both' for both (default)",
    )
    parser.add_argument(
        "--output",
        default="vertical_slice_output.txt",
        help="Path to the output file (default: vertical_slice_output.txt)",
    )

    args = parser.parse_args()

    global output_file
    output_file = open(args.output, "w")

    write_to_file("\n" + "=" * 80)
    write_to_file("CONGRESSIONAL DATA EXTRACTION - VERTICAL SLICE")
    write_to_file("=" * 80)
    write_to_file(f"All output is being saved to: {args.output}")

    if args.type in ["house", "both"]:
        write_to_file("\n" + "=" * 80)
        write_to_file("VERTICAL SLICE: HOUSE COMMITTEES")
        write_to_file("=" * 80)
        get_vertical_slice_house_committees()

    if args.type in ["diplomatic", "both"]:
        write_to_file("\n" + "=" * 80)
        write_to_file("VERTICAL SLICE: DIPLOMATIC OFFICES")
        write_to_file("=" * 80)
        get_vertical_slice_diplomatic_offices()

    write_to_file("\n" + "=" * 80)
    write_to_file("VERTICAL SLICE COMPLETE")
    write_to_file("=" * 80)

    output_file.close()
    print(f"Vertical slice complete. All output has been saved to {args.output}")

if __name__ == "__main__":
    main()
