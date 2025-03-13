"""
Prints statistics on the number of committee and subcommittee members and staff that have been
matched to a BioGuide ID. Analyzes the result of running the add_bioguide_id.py script.
"""
import json
import sys
import glob
import os
import argparse

def analyze_matching_stats(json_file: str) -> dict:
    """
    Analyze matching statistics from the already-processed JSON with bioguide IDs.

    Args:
        json_file: Path to the JSON file with bioguide IDs.

    Returns: The statistics for committee and subcommittee members and staff.
    """
    with open(json_file, "r") as f:
        data = json.load(f)

    stats = {
        "committee_members": {"total": 0, "matched": 0, "multi_match": 0},
        "committee_staff": {"total": 0, "matched": 0, "multi_match": 0},
        "subcommittee_members": {"total": 0, "matched": 0, "multi_match": 0},
        "subcommittee_staff": {"total": 0, "matched": 0, "multi_match": 0},
    }

    for committee in data["committees"]:
        # Committee members
        if "members" in committee:
            for member in committee["members"]:
                if (
                    member.get("member_name")
                    and member.get("member_name").lower() != "vacant"
                ):
                    stats["committee_members"]["total"] += 1
                    if "bioguide_id" in member:
                        stats["committee_members"]["matched"] += 1
                        if isinstance(member["bioguide_id"], list):
                            stats["committee_members"]["multi_match"] += 1

        # Committee staff
        if "staff" in committee:
            for staff in committee["staff"]:
                if (
                    staff.get("staff_name")
                    and staff.get("staff_name").lower() != "vacant"
                ):
                    stats["committee_staff"]["total"] += 1
                    if "bioguide_id" in staff:
                        stats["committee_staff"]["matched"] += 1
                        if isinstance(staff["bioguide_id"], list):
                            stats["committee_staff"]["multi_match"] += 1

        # Subcommittees
        if "subcommittees" in committee:
            for subcommittee in committee["subcommittees"]:
                # Subcommittee members and staff
                if "subcommittee_members" in subcommittee:
                    for item in subcommittee["subcommittee_members"]:
                        # Check if this is a member
                        if (
                            item.get("member_name")
                            and item.get("member_name").lower() != "vacant"
                        ):
                            stats["subcommittee_members"]["total"] += 1
                            if "bioguide_id" in item:
                                stats["subcommittee_members"]["matched"] += 1
                                if isinstance(item["bioguide_id"], list):
                                    stats["subcommittee_members"]["multi_match"] += 1

                        # Check if this is a staff member
                        if (
                            item.get("staff_name")
                            and item.get("staff_name").lower() != "vacant"
                        ):
                            stats["subcommittee_staff"]["total"] += 1
                            if "bioguide_id" in item:
                                stats["subcommittee_staff"]["matched"] += 1
                                if isinstance(item["bioguide_id"], list):
                                    stats["subcommittee_staff"]["multi_match"] += 1

    return stats

def print_stats(stats: dict) -> None:
    """
    Print formatted statistics.

    Args:
        stats: The statistics to print, as returned by `analyze_matching_stats`.
    """
    print("\nBioGuide ID Matching Statistics")
    print("=" * 50)

    # Members stats
    total_members = (
        stats["committee_members"]["total"] + stats["subcommittee_members"]["total"]
    )
    matched_members = (
        stats["committee_members"]["matched"] + stats["subcommittee_members"]["matched"]
    )
    print(f"\nMEMBERS:")
    print("Committee Members:")
    print(f"  Total: {stats['committee_members']['total']}")
    print(f"  Matched: {stats['committee_members']['matched']} ")
    if stats["committee_members"]["total"] > 0:
        print(
            f"  ({(stats['committee_members']['matched'] / stats['committee_members']['total'] * 100):.1f}%)"
        )

    print(f"\nSubcommittee Members:")
    print(f"  Total: {stats['subcommittee_members']['total']}")

    if stats["subcommittee_members"]["total"] > 0:
        print(
            f"  Matched: {stats['subcommittee_members']['matched']} "
            + f"({(stats['subcommittee_members']['matched'] / stats['subcommittee_members']['total'] * 100):.1f}%)"
        )
    else:
        print(f"  Matched: {stats['subcommittee_members']['matched']} (0.0%)")

    print(f"\nAll Members Combined:")
    print(f"  Total: {total_members}")

    if total_members > 0:
        print(
            f"  Matched: {matched_members} ({(matched_members / total_members * 100):.1f}%)"
        )
    else:
        print(f"  Matched: {matched_members} (0.0%)")

    # Staff stats
    total_staff = (
        stats["committee_staff"]["total"] + stats["subcommittee_staff"]["total"]
    )
    matched_staff = (
        stats["committee_staff"]["matched"] + stats["subcommittee_staff"]["matched"]
    )
    print(f"\nSTAFF:")
    print("Committee Staff:")
    print(f"  Total: {stats['committee_staff']['total']}")

    if stats["committee_staff"]["total"] > 0:
        print(
            f"  Matched: {stats['committee_staff']['matched']} "
            + f"({(stats['committee_staff']['matched'] / stats['committee_staff']['total'] * 100):.1f}%)"
        )
    else:
        print(f"  Matched: {stats['committee_staff']['matched']} (0.0%)")

    print(f"\nSubcommittee Staff:")
    print(f"  Total: {stats['subcommittee_staff']['total']}")

    if stats["subcommittee_staff"]["total"] > 0:
        print(
            f"  Matched: {stats['subcommittee_staff']['matched']} "
            + f"({(stats['subcommittee_staff']['matched'] / stats['subcommittee_staff']['total'] * 100):.1f}%)"
        )
    else:
        print(f"  Matched: {stats['subcommittee_staff']['matched']} (0.0%)")

    print(f"\nAll Staff Combined:")
    print(f"  Total: {total_staff}")

    if total_staff > 0:
        print(
            f"  Matched: {matched_staff} ({(matched_staff / total_staff * 100):.1f}%)"
        )
    else:
        print(f"  Matched: {matched_staff} (0.0%)")

    # Multiple matches stats
    total_multi = (
        stats["committee_members"]["multi_match"]
        + stats["committee_staff"]["multi_match"]
        + stats["subcommittee_members"]["multi_match"]
        + stats["subcommittee_staff"]["multi_match"]
    )

    print(f"\nMULTIPLE MATCHES:")
    print(f"Total instances: {total_multi}")
    print(f"  Committee Members: {stats['committee_members']['multi_match']}")
    print(f"  Committee Staff: {stats['committee_staff']['multi_match']}")
    print(f"  Subcommittee Members: {stats['subcommittee_members']['multi_match']}")
    print(f"  Subcommittee Staff: {stats['subcommittee_staff']['multi_match']}")

def check_bioguide_matches(json_file: str) -> dict | None:
    """
    Check BioGuide ID matches for a specific JSON file.

    Args:
        json_file: Path to the JSON file with BioGuide IDs.

    Returns: The statistics for BioGuide ID matches.
    """
    try:
        stats = analyze_matching_stats(json_file)
        print_stats(stats)
        return stats
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def check_bioguide_matches_for_congress(congress_number: int) -> list:
    """
    Check BioGuide ID matches for all committee files with BioGuide IDs for a specific congress.

    Args:
        congress_number: Congress number to check

    Returns: Statistics dictionaries for each file
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    output_dir = os.path.join(root_dir, "outputs", str(congress_number))

    if not os.path.exists(output_dir):
        print(
            f"Error: Output directory for Congress {congress_number} not found: {output_dir}"
        )
        return []

    # Find all files with BioGuide IDs
    bioguide_files = []
    for file in glob.glob(os.path.join(output_dir, "*with_bioguide*.json")):
        bioguide_files.append(file)

    if not bioguide_files:
        for file in glob.glob(os.path.join(root_dir, "*with_bioguide*.json")):
            bioguide_files.append(file)

    if not bioguide_files:
        print(f"No files with BioGuide IDs found for Congress {congress_number}")
        return []

    print(
        f"Checking BioGuide ID matches in {len(bioguide_files)} files for Congress {congress_number}..."
    )
    all_stats = []

    for file in bioguide_files:
        print(f"\nChecking {os.path.basename(file)}...")
        stats = check_bioguide_matches(file)
        if stats:
            all_stats.append(stats)

    return all_stats

def main():
    """
    Main function that checks either a specific file or all files for a congress number.
    Can be called in three ways:
    1. No arguments: Check the default House committees file with BioGuide IDs (testing)
    2. With a specific file path: Check that file
    3. With --congress argument: Check all files with BioGuide IDs for that congress
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Check BioGuide ID matches in committee JSON files"
    )
    parser.add_argument(
        "json_file", nargs="?", help="JSON file with BioGuide IDs to check (optional, default: CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_bioguide.json)"
    )
    parser.add_argument(
        "--congress",
        type=str,
        help="Check all files with BioGuide IDs for this Congress number",
    )
    args = parser.parse_args()

    # Process based on arguments
    if args.congress:
        check_bioguide_matches_for_congress(args.congress)
    elif args.json_file:
        check_bioguide_matches(args.json_file)
    else:
        json_file = os.path.join(
            root_dir, "CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_bioguide.json"
        )
        try:
            check_bioguide_matches(json_file)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            print(
                "Default file not found. Please specify an input file or use --congress option."
            )
            sys.exit(1)

if __name__ == "__main__":
    main()
