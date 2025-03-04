"""
Add BioGuide IDs to JSON data based on legislator mappings.
Accepts a specific JSON file or processes all committee files for a Congress.
"""
import json
import csv
import copy
import string
import os
import sys
import glob
from collections import defaultdict
import argparse

def clean_name(name: str) -> str:
    """
    Clean a name by removing punctuation, standardizing format, and converting to lowercase.

    Args:
        name: The name to clean.

    Returns: The cleaned name.
    """
    # Convert to lowercase
    name = name.lower()

    # Remove parentheses and their contents
    while "(" in name and ")" in name:
        start = name.find("(")
        end = name.find(")")
        if start < end:
            name = name[:start] + name[end + 1 :]

    # Remove punctuation except hyphens
    for char in string.punctuation:
        if char != "-":
            name = name.replace(char, " ")

    # Standardize whitespace
    name = " ".join(name.split())

    return name.strip()

def load_legislator_mappings(csv_file: str) -> dict:
    """
    Load legislator names and their BioGuide IDs from CSV file.

    Args:
        csv_file: The path to the CSV file.

    Returns:A mapping of cleaned names to BioGuide IDs.
    """
    mappings = defaultdict(list)

    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bioguide_id = row["bioguide_id"]
            if not bioguide_id:  # Skip if no bioguide_id
                continue

            # Clean and store full name
            full_name = clean_name(row["full_name"])
            mappings[full_name].append(bioguide_id)

            # Clean and store first + last name combination
            first_name = clean_name(row["first_name"])
            last_name = clean_name(row["last_name"])
            combined_name = f"{first_name} {last_name}"
            mappings[combined_name].append(bioguide_id)

            # Store variation with middle initial removed
            name_parts = full_name.split()
            if len(name_parts) > 2:
                # Try removing middle parts
                first_last_only = f"{name_parts[0]} {name_parts[-1]}"
                mappings[first_last_only].append(bioguide_id)

    # Convert defaultdict to regular dict and remove duplicates from lists
    return {k: list(set(v)) for k, v in mappings.items()}

def update_person_with_bioguide(person: dict, name_mappings: dict) -> bool:
    """
    Update a person's entry with bioguide_id(s) if match(es) found.

    Args:
        person: The person's entry in the JSON data.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.

    Returns: True if a match was found and updated, False otherwise.
    """
    if (not person.get("member_name")) and (not person.get("staff_name")):
        return False

    if "member_name" in person:
        input_name = person["member_name"]
    elif "staff_name" in person:
        input_name = person["staff_name"]
    else:
        return False

    cleaned_name = clean_name(input_name)

    # Try to find match
    if cleaned_name in name_mappings:
        bioguide_ids = name_mappings[cleaned_name]
        if len(bioguide_ids) == 1:
            # If only one match, store as string
            person["bioguide_id"] = bioguide_ids[0]
        else:
            # If multiple matches, store as list
            person["bioguide_id"] = bioguide_ids
        return True

    return False

def update_json_with_bioguides(data: dict, name_mappings: dict) -> tuple:
    """
    Recursively update all people in the JSON with BioGuide IDs.

    Args:
        data: The JSON data to update.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.

    Returns: A tuple containing the updated data and statistics (showing matched, unmatched,
        multiple matches, etc).
    """
    # Create a deep copy to avoid modifying original
    updated_data = copy.deepcopy(data)

    # Track statistics
    stats = {
        "total_people": 0,
        "matched_people": 0,
        "multiple_matches": 0,
        "unmatched_people": [],
        "matched_details": [],
        "multiple_match_details": [],
    }

    # Process each committee
    for committee in updated_data["committees"]:
        # Process committee members
        if "members" in committee:
            for member in committee["members"]:
                stats["total_people"] += 1
                if update_person_with_bioguide(member, name_mappings):
                    stats["matched_people"] += 1
                    if isinstance(member.get("bioguide_id"), list):
                        stats["multiple_matches"] += 1
                        stats["multiple_match_details"].append(
                            f"Committee '{committee['committee_name']}' member: {member['member_name']} -> {member['bioguide_id']}"
                        )
                    else:
                        stats["matched_details"].append(
                            f"Committee '{committee['committee_name']}' member: {member['member_name']} -> {member['bioguide_id']}"
                        )
                else:
                    stats["unmatched_people"].append(
                        f"Committee '{committee['committee_name']}' member: {member['member_name']}"
                    )

        # Process committee staff
        if "staff" in committee:
            for staff in committee["staff"]:
                stats["total_people"] += 1
                if update_person_with_bioguide(staff, name_mappings):
                    stats["matched_people"] += 1
                    if isinstance(staff.get("bioguide_id"), list):
                        stats["multiple_matches"] += 1
                        stats["multiple_match_details"].append(
                            f"Committee '{committee['committee_name']}' staff: {staff['staff_name']} -> {staff['bioguide_id']}"
                        )
                    else:
                        stats["matched_details"].append(
                            f"Committee '{committee['committee_name']}' staff: {staff['staff_name']} -> {staff['bioguide_id']}"
                        )
                else:
                    stats["unmatched_people"].append(
                        f"Committee '{committee['committee_name']}' staff: {staff['staff_name']}"
                    )

        # Process each subcommittee
        if "subcommittees" in committee:
            for subcommittee in committee["subcommittees"]:
                # Process subcommittee members
                if "subcommittee_members" in subcommittee:
                    for member in subcommittee["subcommittee_members"]:
                        stats["total_people"] += 1
                        member_name = (
                            member["member_name"]
                            if "member_name" in member
                            else member["staff_name"]
                        )
                        if update_person_with_bioguide(member, name_mappings):
                            stats["matched_people"] += 1
                            if isinstance(member.get("bioguide_id"), list):
                                stats["multiple_matches"] += 1
                                stats["multiple_match_details"].append(
                                    f"Subcommittee '{subcommittee['subcommittee_name']}' of '{committee['committee_name']}' member: {member_name} -> {member['bioguide_id']}"
                                )
                            else:
                                stats["matched_details"].append(
                                    f"Subcommittee '{subcommittee['subcommittee_name']}' of '{committee['committee_name']}' member: {member_name} -> {member['bioguide_id']}"
                                )
                        else:
                            stats["unmatched_people"].append(
                                f"Subcommittee '{subcommittee['subcommittee_name']}' of '{committee['committee_name']}' member: {member_name}"
                            )

    return updated_data, stats

def add_bioguide_ids_to_file(
        input_file: str,
        legislators_file: str,
        output_file: str = None
    ) -> tuple:
    """
    Add BioGuide IDs to a specific JSON file.

    Args:
        input_file: Path to the input JSON file.
        legislators_file: Path to the legislators CSV file.
        output_file: Path to the output JSON file (optional).

    Returns: The updated data and statistics.
    """
    try:
        with open(input_file, "r") as f:
            committee_data = json.load(f)

        name_mappings = load_legislator_mappings(legislators_file)
        updated_data, stats = update_json_with_bioguides(committee_data, name_mappings)

        if output_file:
            with open(output_file, "w") as f:
                json.dump(updated_data, f, indent=2)
            print(f"Updated data saved to {output_file}")

        # Print statistics
        print("\nBioGuide ID Matching Statistics:")
        print("=" * 80)
        print(f"Total people processed: {stats['total_people']}")
        print(f"Successfully matched: {stats['matched_people']}")
        print(f"Multiple matches found: {stats['multiple_matches']}")
        print(
            f"Match rate: {(stats['matched_people'] / stats['total_people'] * 100):.1f}%"
        )

        if stats["multiple_matches"] > 0:
            print("\nMultiple Matches Found:")
            print("=" * 80)
            for detail in stats['multiple_match_details'][:5]:
                print(f"• {detail}")
            if len(stats['multiple_match_details']) > 5:
                print(f"... and {len(stats['multiple_match_details']) - 5} more")

        print("\nUnmatched People Examples:")
        print("=" * 80)
        for person in stats['unmatched_people'][:5]:
            print(f"• {person}")
        if len(stats['unmatched_people']) > 5:
            print(f"... and {len(stats['unmatched_people']) - 5} more")

        return updated_data, stats

    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None

def add_bioguide_ids_for_congress(congress_number: int, legislators_file: str = None) -> None:
    """
    Add BioGuide IDs to all committee files for the specified Congress number.

    Args:
        congress_number: Congress number to process
        legislators_file: Path to the legislators CSV file (optional)
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    if legislators_file is None:
        legislators_file = os.path.join(root_dir, "legislators.csv")

    output_dir = os.path.join(root_dir, "outputs", str(congress_number))

    if not os.path.exists(output_dir):
        print(f"Error: Output directory for Congress {congress_number} not found: {output_dir}")
        return

    if not os.path.exists(legislators_file):
        print(f"Error: Legislators file not found: {legislators_file}")
        return

    committee_files = []
    for file in glob.glob(os.path.join(output_dir, "*COMMITTEES*.json")):
        committee_files.append(file)

    if not committee_files:
        print(f"No committee files found for Congress {congress_number} in {output_dir}")
        return

    print(f"Adding BioGuide IDs to {len(committee_files)} committee files for Congress {congress_number}...")
    for file in committee_files:
        output_file = file.replace('.json', '_with_bioguide.json')
        print(f"Processing {os.path.basename(file)}...")
        add_bioguide_ids_to_file(file, legislators_file, output_file)

    print("Completed adding BioGuide IDs to all committee files.")

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
    parser = argparse.ArgumentParser(description="Add BioGuide IDs to committee JSON files")
    parser.add_argument("input_file", nargs="?", help="Input JSON file to process (optional)")
    parser.add_argument("--congress", type=str, help="Process all committee files for this Congress number")
    parser.add_argument("--legislators", help="Path to legislators CSV file (optional)")
    args = parser.parse_args()

    legislators_file = args.legislators or os.path.join(root_dir, "legislators.csv")

    # Process based on arguments
    if args.congress:
        add_bioguide_ids_for_congress(args.congress, legislators_file)
    elif args.input_file:
        output_file = args.input_file.replace('.json', '_with_bioguide.json')
        add_bioguide_ids_to_file(args.input_file, legislators_file, output_file)
    else:
        json_file = os.path.join(root_dir, "outputs/117/CDIR-2022-10-26-HOUSECOMMITTEES.txt_output.json")
        output_file = os.path.join(root_dir, "CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_bioguide.json")
        try:
            add_bioguide_ids_to_file(json_file, legislators_file, output_file)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            print("Default file not found. Please specify an input file or use --congress option.")
            sys.exit(1)

if __name__ == "__main__":
    main()
