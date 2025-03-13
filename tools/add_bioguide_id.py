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

def process_person(person: dict, role: str, name_mappings: dict, stats: dict) -> None:
    """
    Process an individual person entry.

    Args:
        person: map of person details
        role: The role of the person (e.g., member, staff, etc.).
        name_mappings: mapping cleaned names to BioGuide IDs.
        stats: store processing statistics.
    """
    if not person:
        return

    name = None
    if "member_name" in person:
        name = person["member_name"]
    elif "staff_name" in person:
        name = person["staff_name"]
    elif "name" in person:
        name = person["name"]
    
    if not name or name.lower() in ["vacant", "n/a", "[vacant]"]:
        return
    
    stats["total_people"] += 1
    
    # Check if already has bioguide_id
    if "bioguide_id" in person:
        stats["preserved_ids"] += 1
        stats["matched_people"] += 1
        return
    
    # Try to match with bioguide id
    cleaned_name = clean_name(name)
    if cleaned_name in name_mappings:
        bioguide_ids = name_mappings[cleaned_name]
        if len(bioguide_ids) == 1:
            person["bioguide_id"] = bioguide_ids[0]
            stats["matched_people"] += 1
            stats["matched_details"].append(f"{role}: {name} -> {bioguide_ids[0]}")
        else:
            person["bioguide_id"] = bioguide_ids
            stats["matched_people"] += 1
            stats["multiple_matches"] += 1
            stats["multiple_match_details"].append(f"{role}: {name} -> {bioguide_ids}")
    else:
        stats["unmatched_people"].append(f"{role}: {name}")

def process_committees(data: dict, name_mappings: dict, stats: dict) -> None:
    """
    Process committee schema directly.

    Args:
        data: The JSON data to process.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.
        stats: A dictionary to store processing statistics.

    Returns: None
    """
    for committee in data.get("committees", []):
        # Process committee members
        for member in committee.get("members", []):
            process_person(member, "member", name_mappings, stats)
        
        # Process committee staff
        for staff in committee.get("staff", []):
            process_person(staff, "staff", name_mappings, stats)
        
        # Process subcommittees
        for subcommittee in committee.get("subcommittees", []):
            for item in subcommittee.get("subcommittee_members", []):
                if "member_name" in item:
                    process_person(item, "member", name_mappings, stats)
                elif "staff_name" in item:
                    process_person(item, "staff", name_mappings, stats)

def process_diplomatic(data: dict, name_mappings: dict, stats: dict) -> None:
    """
    Process diplomatic offices schema directly.

    Args:
        data: The JSON data to process.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.
        stats: A dictionary to store processing statistics.

    Returns: None
    """
    for rep in data.get("diplomatic_representatives", []):
        process_person(rep, "diplomatic", name_mappings, stats)

def process_courts(data: dict, name_mappings: dict, stats: dict) -> None:
    """
    Process courts schema directly.

    Args:
        data: The JSON data to process.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.
        stats: A dictionary to store processing statistics.

    Returns: None
    """
    for court in data.get("courts", []):
        # Process court personnel
        for person in court.get("court_personnel", []):
            process_person(person, "court", name_mappings, stats)
        
        # Process circuit personnel
        for circuit in court.get("circuits", []):
            for person in circuit.get("circuit_personnel", []):
                process_person(person, "circuit", name_mappings, stats)

def process_agencies(data: dict, name_mappings: dict, stats: dict) -> None:
    """
    Process agencies schema directly.

    Args:
        data: The JSON data to process.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.
        stats: A dictionary to store processing statistics.

    Returns: None
    """
    for agency in data.get("agencies", []):
        for member in agency.get("agency_members", []):
            process_person(member, "agency", name_mappings, stats)

def process_organizations(data: dict, name_mappings: dict, stats: dict) -> None:
    """
    Process organizations schema directly.

    Args:
        data: The JSON data to process.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.
        stats: A dictionary to store processing statistics.

    Returns: None
    """
    for org in data.get("organizations", []):
        # Process organization personnel
        for person in org.get("organization_personnel", []):
            process_person(person, "org", name_mappings, stats)
        
        # Process department personnel
        for dept in org.get("departments", []):
            for person in dept.get("department_personnel", []):
                process_person(person, "dept", name_mappings, stats)

def process_departments(data: dict, name_mappings: dict, stats: dict) -> None:
    """
    Process departments schema directly.

    Args:
        data: The JSON data to process.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.
        stats: A dictionary to store processing statistics.

    Returns: None
    """
    # Process cabinet
    for member in data.get("cabinet", []):
        process_person(member, "cabinet", name_mappings, stats)
    
    # Process executive offices
    for office in data.get("executive_office_of_president", []):
        for member in office.get("office_members", []):
            process_person(member, "office", name_mappings, stats)
    
    # Process departments
    for dept in data.get("departments", []):
        for member in dept.get("department_members", []):
            process_person(member, "department", name_mappings, stats)

def process_boards(data: dict, name_mappings: dict, stats: dict) -> None:
    """
    Process boards schema directly.

    Args:
        data: The JSON data to process.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.
        stats: A dictionary to store processing statistics.

    Returns: None
    """
    for body in data.get("government_bodies", []):
        for member in body.get("government_body_members", []):
            process_person(member, "board", name_mappings, stats)

def update_json_with_bioguides(data: dict, name_mappings: dict) -> tuple:
    """
    Update all people in JSON with BioGuide IDs based on the schema type.
    
    Args:
        data: The JSON data to update.
        name_mappings: A dictionary mapping cleaned names to BioGuide IDs.
    
    Returns: A tuple containing the updated data and statistics.
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
        "preserved_ids": 0,
    }
    
    # Process based on schema type
    schema_type = "unknown"
    if "committees" in updated_data:
        schema_type = "committees"
        process_committees(updated_data, name_mappings, stats)
    elif "diplomatic_representatives" in updated_data:
        schema_type = "diplomatic"
        process_diplomatic(updated_data, name_mappings, stats)
    elif "courts" in updated_data:
        schema_type = "courts"
        process_courts(updated_data, name_mappings, stats)
    elif "agencies" in updated_data:
        schema_type = "agencies"
        process_agencies(updated_data, name_mappings, stats)
    elif "organizations" in updated_data:
        schema_type = "organizations"
        process_organizations(updated_data, name_mappings, stats)
    elif "cabinet" in updated_data or "departments" in updated_data:
        schema_type = "departments"
        process_departments(updated_data, name_mappings, stats)
    elif "government_bodies" in updated_data:
        schema_type = "boards"
        process_boards(updated_data, name_mappings, stats)
    
    print(f"Processed schema type: {schema_type}, Found {stats['total_people']} people")
    
    return updated_data, stats

def count_existing_bioguide_ids(data: dict) -> int:
    """
    Count how many bioguide_ids already exist in the data.

    Args:
        data: The JSON data to process.

    Returns: The count of existing bioguide_ids.
    """
    count = 0
    
    def traverse(obj):
        nonlocal count
        if isinstance(obj, dict):
            if "bioguide_id" in obj:
                count += 1
            for value in obj.values():
                traverse(value)
        elif isinstance(obj, list):
            for item in obj:
                traverse(item)
    
    traverse(data)
    return count

def add_bioguide_ids_to_file(
        input_file: str,
        legislators_file: str,
        output_file: str | None = None
    ) -> bool:
    """
    Add BioGuide IDs to a specific JSON file.
    Args:
        input_file: Path to the input JSON file.
        legislators_file: Path to the legislators CSV file.
        output_file: Path to the output JSON file (optional).
    Returns: True if successful, False otherwise.
    """
    try:
        with open(input_file, "r") as f:
            data = json.load(f)
        
        # Count existing bioguide_ids
        existing_ids = count_existing_bioguide_ids(data)
        if existing_ids > 0:
            print(f"Input file already contains {existing_ids} BioGuide IDs")
        
        name_mappings = load_legislator_mappings(legislators_file)
        updated_data, stats = update_json_with_bioguides(data, name_mappings)
        
        if output_file:
            with open(output_file, "w") as f:
                json.dump(updated_data, f, indent=2)
            print(f"Updated data saved to {output_file}")
        
        # Print statistics
        print("\nBioGuide ID Matching Statistics:")
        print("=" * 80)
        print(f"Total people processed: {stats['total_people']}")
        print(f"Successfully matched: {stats['matched_people']}")
        print(f"Preserved existing IDs: {stats.get('preserved_ids', 0)}")
        print(f"Multiple matches found: {stats['multiple_matches']}")
        if stats['total_people'] > 0:
            print(f"Match rate: {(stats['matched_people'] / stats['total_people'] * 100):.1f}%")
        
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
        
        return True
    
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

def detect_file_type(file_path: str) -> str:
    """
    Detect the type of JSON file based on its content.

    Args:
        file_path: The path to the JSON file.

    Returns: The detected file type.
    """
    try:
        with open(file_path, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Unable to parse JSON in {os.path.basename(file_path)}")
                return "invalid"

            if "committees" in data:
                return "committee"
            elif "diplomatic_representatives" in data:
                return "diplomatic"
            elif "courts" in data:
                return "court"
            elif "agencies" in data:
                return "agency"
            elif "organizations" in data:
                return "organization"
            elif "departments" in data or "cabinet" in data:
                return "department"
            elif "government_bodies" in data:
                return "board"
            else:
                return "unknown"
    except Exception as e:
        print(f"Error accessing file {os.path.basename(file_path)}: {str(e)}")
        return "invalid"

def add_bioguide_ids_for_congress(congress_number: int, legislators_file: str | None = None) -> None:
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

def main() -> None:
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
