"""
Enriches Congressional data JSON files with BioGuide IDs and Thomas IDs.
This tool operates on already processed JSON files to add identifiers.
"""
import os
import sys
import json
import glob
import argparse
from pathlib import Path

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    from add_bioguide_id import add_bioguide_ids_to_file, detect_file_type
    from add_thomas_id import add_thomas_ids_to_file
except ImportError:
    print("Error: Required tool files not found.")
    sys.exit(1)


def get_project_root():
    """Get the project root directory."""
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def enrich_congressional_data(
    congress_num,
    legislators_file=None,
    committees_file=None,
    output_dir=None,
    bioguide=True,
    thomas=True,
    base_directory=None,
) -> bool:
    """
    Enrich all JSON files for a Congress with BioGuide IDs and Thomas IDs where applicable.

    Args:
        congress_num: Congress number to process
        legislators_file: Path to legislators CSV file
        committees_file: Path to committee names CSV file
        output_dir: Directory to save enriched files (default: outputs/{congress_num}_enriched)
        bioguide: Whether to add BioGuide IDs (default: True)
        thomas: Whether to add Thomas IDs (default: True)
        base_directory: Base directory for input/output files

    Returns:
        bool: True if enrichment was successful, False otherwise
    """
    # Set up file paths
    if base_directory is None:
        base_directory = get_project_root()

    if not output_dir:
        output_dir = os.path.join(base_directory, "outputs", f"{congress_num}_enriched")

    input_dir = os.path.join(base_directory, "outputs", str(congress_num))

    if not legislators_file:
        legislators_file = os.path.join(base_directory, "legislators.csv")

    if not committees_file:
        committees_file = os.path.join(base_directory, "committee_names.csv")

    # Check if required files exist
    if bioguide and not os.path.exists(legislators_file):
        print(f"Error: Legislators file not found: {legislators_file}")
        return False

    if thomas and not os.path.exists(committees_file):
        print(f"Error: Committee names file not found: {committees_file}")
        return False

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Find all JSON files in the input directory
    json_files = []
    for file in glob.glob(os.path.join(input_dir, "*.json")):
        # Skip files that are already enriched
        if "_with_bioguide" in file or "_with_thomas_ids" in file:
            continue
        json_files.append(file)

    if not json_files:
        print(f"No JSON files found for Congress {congress_num}")
        return False

    print(f"Found {len(json_files)} JSON files to enrich for Congress {congress_num}")

    # Process each file
    for input_file in json_files:
        file_name = os.path.basename(input_file)
        output_file = os.path.join(output_dir, file_name)

        # Check file type and skip invalid files
        file_type = detect_file_type(input_file)
        if file_type == "invalid":
            print(f"  Skipping invalid file: {file_name}")
            continue

        print(f"Processing {file_name} (detected type: {file_type})...")

        # Copy the input file to output directory first
        try:
            with open(input_file, "r") as infile:
                try:
                    data = json.load(infile)
                except json.JSONDecodeError:
                    print(f"  Error: {file_name} is not a valid JSON file, skipping")
                    continue

            with open(output_file, "w") as outfile:
                json.dump(data, outfile, indent=2)
        except Exception as e:
            print(f"  Error opening or writing file {file_name}: {str(e)}")
            continue

        # Add BioGuide IDs if requested (all file types)
        if bioguide:
            print("  Adding BioGuide IDs...")
            try:
                temp_output = os.path.join(output_dir, f"{file_name}_temp")
                success = add_bioguide_ids_to_file(
                    output_file, legislators_file, temp_output
                )

                if success and os.path.exists(temp_output):
                    # Replace the output file with the enriched version
                    os.replace(temp_output, output_file)
                    print("  Successfully added BioGuide IDs")
                else:
                    print("  Warning: Failed to add BioGuide IDs")
            except Exception as e:
                print(f"  Error adding BioGuide IDs: {str(e)}")

        # Add Thomas IDs if requested AND it's a committee file
        if thomas and file_type == "committee":
            print("  Adding Thomas IDs...")
            try:
                temp_output = os.path.join(output_dir, f"{file_name}_temp")
                success = add_thomas_ids_to_file(
                    output_file, committees_file, temp_output
                )

                if success and os.path.exists(temp_output):
                    # Replace the output file with the enriched version
                    os.replace(temp_output, output_file)
                    print("  Successfully added Thomas IDs")
                else:
                    print("  Warning: Failed to add Thomas IDs")
            except Exception as e:
                print(f"  Error adding Thomas IDs: {str(e)}")

        print(f"  Saved enriched file to {output_file}")

    print(f"Enrichment complete. Enriched files saved to {output_dir}")
    return True


def main():
    """
    Main function to enrich Congressional data files with BioGuide IDs and Thomas IDs.
    """
    parser = argparse.ArgumentParser(
        description="Enrich Congressional data files with BioGuide IDs and Thomas IDs."
    )
    parser.add_argument(
        "--congress", required=True, help="Congress number to process (e.g., '117')"
    )
    parser.add_argument("--output-dir", help="Directory to save enriched files")
    parser.add_argument("--legislators", help="Path to legislators CSV file")
    parser.add_argument("--committees", help="Path to committee names CSV file")
    parser.add_argument(
        "--skip-bioguide", action="store_true", help="Skip adding BioGuide IDs"
    )
    parser.add_argument(
        "--skip-thomas", action="store_true", help="Skip adding Thomas IDs"
    )

    args = parser.parse_args()

    enrich_congressional_data(
        args.congress,
        legislators_file=args.legislators,
        committees_file=args.committees,
        output_dir=args.output_dir,
        bioguide=not args.skip_bioguide,
        thomas=not args.skip_thomas,
    )


if __name__ == "__main__":
    main()
