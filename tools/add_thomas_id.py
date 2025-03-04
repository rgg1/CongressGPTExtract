"""
Adds Thomas IDs to committee data based on a CSV file containing mappings between committee names
and Thomas IDs. Accepts either a specific JSON file or processes all committee files for a
Congress number.
"""
import os
import json
import csv
import copy
import sys
import glob
from collections import defaultdict
import string
import argparse

def clean_committee_name(name: str) -> str:
    """
    Clean committee name by removing irrelevant prefixes, punctuation, and standardizing format.

    Args:
        name: The committee name to clean.

    Returns: The cleaned committee name
    """
    # lowercase
    name = name.lower()

    # handle special cases that need exact matching (discrepancies in tCSV vs text file)
    special_cases = {
        "house select subcommittee on the coronavirus crisis": "coronavirus crisis",
        "coronavirus crisis subcommittee": "coronavirus crisis",
        "select subcommittee on the coronavirus crisis": "coronavirus crisis",
        "coronavirus crisis": "coronavirus crisis",
    }

    # Check special cases
    name_lower = name.lower()
    for case, replacement in special_cases.items():
        if case in name_lower:
            return replacement

    # Remove punctuation except hyphens
    for char in string.punctuation:
        if char != "-":
            name = name.replace(char, " ")

    # irrelevant prefixes to remove
    prefixes_to_remove = [
        "house select subcommittee on the ",
        "house select subcommittee on ",
        "select subcommittee on the ",
        "select subcommittee on ",
        "house committee on ",
        "senate committee on ",
        "house select committee on ",
        "house select committee to ",
        "house permanent select committee on ",
        "subcommittee for ",
        "subcommittee on ",
        "select committee on ",
        "select committee to ",
        "permanent select committee on ",
        "subcommittee ",
        "committee on ",
        "the ",
    ]

    # Remove prefixes
    for prefix in prefixes_to_remove:
        if name.startswith(prefix):
            name = name.replace(prefix, "", 1)

    # Remove word "subcommittee" if it appears at the end
    name = name.replace(" subcommittee", "")

    # Additional word replacements
    replacements = {
        "for indigenous peoples of the united states": "indigenous peoples",
        ", and": " and",
        "&": "and",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    # Remove parentheses and their contents
    while "(" in name and ")" in name:
        start = name.find("(")
        end = name.find(")")
        if start < end:
            name = name[:start] + name[end + 1 :]

    # Additional cleaning for specific cases
    name = name.replace("environment subcommittee", "environment")
    name = name.replace("government operations subcommittee", "government operations")
    name = name.replace("national security subcommittee", "national security")

    # Standardize whitespace
    name = " ".join(name.split())

    # Handle specific edge cases
    if "indigenous peoples" in name:
        name = "indigenous peoples"

    return name.strip()

def load_committee_mappings(
    csv_file: str,
) -> tuple[dict[str, str], dict[str, set[str]]]:
    """
    Load committee names and their Thomas IDs from CSV file with additional variations
    that can be used for matching.

    Args:
        csv_file: The path to the CSV file containing committee mappings.

    Returns: A mapping of committee names to Thomas IDs and a dictionary mapping original
        names to cleaned variations for validation.
    """
    mappings = {}
    original_to_cleaned = defaultdict(set)

    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            original_name = row["representative_name"]
            thomas_id = row["thomas_id"]
            house_id = row["house_committee_id"]

            # Special case for Coronavirus Crisis
            if thomas_id == "HSVC" or house_id == "VC":
                mappings["coronavirus crisis"] = house_id or thomas_id
                continue

            # Use house committee ID if available, otherwise use thomas_id
            committee_id = house_id if house_id else thomas_id

            if not committee_id:
                continue

            # Store different variations of the name
            variations = {
                original_name.lower(),
                clean_committee_name(original_name),
                clean_committee_name(
                    original_name.replace("House Committee on ", "").replace(
                        "Senate Committee on ", ""
                    )
                ),
                clean_committee_name(
                    original_name.split("Committee")[-1]
                    if "Committee" in original_name
                    else original_name
                ),
            }

            # Add additional variations
            additional_variations = set()
            for variation in variations:
                additional_variations.add(variation.replace(" ", ""))
                additional_variations.add(variation.replace(" and ", " & "))

            variations.update(additional_variations)

            # Add variations to mappings
            for variation in variations:
                mappings[variation] = committee_id
                original_to_cleaned[original_name].add(variation)

    return mappings, original_to_cleaned

def update_committees_with_thomas_ids(
    data: dict, mappings: dict
) -> tuple[dict, list, list]:
    """
    Update committee data with Thomas IDs based on the provided mappings.

    Args:
        data: The committee data to update.
        mappings: The dictionary mapping committee names to Thomas IDs.

    Returns: The updated committee data, list of unmatched committees, and list of matched
    """
    updated_data = copy.deepcopy(data)
    unmatched = []
    matched = []

    for committee in updated_data["committees"]:
        committee_name = clean_committee_name(committee["committee_name"])
        original_name = committee["committee_name"]

        if committee_name in mappings:
            committee["thomas_id"] = mappings[committee_name]
            matched.append(
                f"Main Committee: {original_name} -> {mappings[committee_name]}"
            )
        else:
            unmatched.append(
                f"Main Committee: {original_name} (cleaned: {committee_name})"
            )

        if "subcommittees" in committee:
            for subcommittee in committee["subcommittees"]:
                subcommittee_name = clean_committee_name(
                    subcommittee["subcommittee_name"]
                )
                original_subname = subcommittee["subcommittee_name"]

                # Try variations for subcommittees
                found_match = False
                variations = [
                    subcommittee_name,
                    subcommittee_name.replace("subcommittee", "").strip(),
                    clean_committee_name(
                        original_subname + " " + committee["committee_name"]
                    ),
                ]

                for variation in variations:
                    if variation in mappings:
                        subcommittee["thomas_id"] = mappings[variation]
                        matched.append(
                            f"Subcommittee: {original_subname} -> {mappings[variation]}"
                        )
                        found_match = True
                        break

                if not found_match:
                    unmatched.append(
                        f"Subcommittee: {original_subname} (cleaned: {subcommittee_name})"
                    )

    return updated_data, unmatched, matched

def add_thomas_ids_to_file(
        input_file: str,
        committee_csv_file: str,
        output_file: str = None
    ) -> tuple:
    """
    Add Thomas IDs to a specific committee JSON file.

    Args:
        input_file: Path to the input JSON file.
        committee_csv_file: Path to the committee mappings CSV file.
        output_file: Path to the output JSON file (optional).

    Returns: The updated data, unmatched committees, and matched committees.
    """
    try:
        with open(input_file, "r") as f:
            committee_data = json.load(f)

        mappings, _ = load_committee_mappings(committee_csv_file)

        updated_data, unmatched, matched = update_committees_with_thomas_ids(
            committee_data, mappings
        )

        if output_file:
            with open(output_file, "w") as f:
                json.dump(updated_data, f, indent=2)
            print(f"Successfully updated committee data and saved to {output_file}")

        # Print statistics
        print("\nThomas ID Mapping Statistics:")
        print("=" * 80)
        print(f"Total committees and subcommittees matched: {len(matched)}")
        print(f"Total committees and subcommittees unmatched: {len(unmatched)}")

        if unmatched:
            print("\nExample unmatched committees/subcommittees:")
            for item in unmatched[:5]:
                print(f"• {item}")
            if len(unmatched) > 5:
                print(f"... and {len(unmatched) - 5} more")

        if matched:
            print("\nExample matched committees/subcommittees:")
            for item in matched[:5]:
                print(f"• {item}")
            if len(matched) > 5:
                print(f"... and {len(matched) - 5} more")

        return updated_data, unmatched, matched

    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        return None, None, None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return None, None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None, None

def add_thomas_ids_for_congress(congress_number: int, committee_csv_file: str = None) -> None:
    """
    Add Thomas IDs to all committee files for the specified Congress number.

    Args:
        congress_number: Congress number to process
        committee_csv_file: Path to the committee mappings CSV file (optional)
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    if committee_csv_file is None:
        committee_csv_file = os.path.join(root_dir, "committee_names.csv")

    output_dir = os.path.join(root_dir, "outputs", str(congress_number))

    if not os.path.exists(output_dir):
        print(f"Error: Output directory for Congress {congress_number} not found: {output_dir}")
        return

    if not os.path.exists(committee_csv_file):
        print(f"Error: Committee names file not found: {committee_csv_file}")
        return

    committee_files = []
    for file in glob.glob(os.path.join(output_dir, "*COMMITTEES*.json")):
        committee_files.append(file)

    if not committee_files:
        print(f"No committee files found for Congress {congress_number} in {output_dir}")
        return

    print(f"Adding Thomas IDs to {len(committee_files)} committee files for Congress {congress_number}...")
    for file in committee_files:
        output_file = file.replace('.json', '_with_thomas_ids.json')
        print(f"Processing {os.path.basename(file)}...")
        add_thomas_ids_to_file(file, committee_csv_file, output_file)

    print("Completed adding Thomas IDs to all committee files.")

def main():
    """
    Main function that processes either a specific file or all files for a congress number.
    Can be called in three ways:
    1. No arguments: Process the default House committees file from 117th Congress (testing)
    2. With a specific file path: Process that file
    3. With --congress argument: Process all committee files for that congress
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Add Thomas IDs to committee JSON files")
    parser.add_argument("input_file", nargs="?", help="Input JSON file to process (optional)")
    parser.add_argument("--congress", type=str,
                        help="Process all committee files for this Congress number")
    parser.add_argument("--committee-csv", help="Path to committee names CSV file (optional)")
    args = parser.parse_args()

    committee_csv_file = args.committee_csv or os.path.join(root_dir, "committee_names.csv")

    # Process based on arguments
    if args.congress:
        add_thomas_ids_for_congress(args.congress, committee_csv_file)
    elif args.input_file:
        output_file = args.input_file.replace('.json', '_with_thomas_ids.json')
        add_thomas_ids_to_file(args.input_file, committee_csv_file, output_file)
    else:
        json_file = os.path.join(root_dir,
                                 "outputs/117/CDIR-2022-10-26-HOUSECOMMITTEES.txt_output.json")
        output_file = os.path.join(root_dir,
                                "CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_thomas_ids.json")
        try:
            add_thomas_ids_to_file(json_file, committee_csv_file, output_file)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            print("Default file not found. Please specify an input file or use --congress option.")
            sys.exit(1)

if __name__ == "__main__":
    main()
