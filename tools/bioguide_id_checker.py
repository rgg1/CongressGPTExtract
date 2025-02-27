"""
Prints statistics on the number of committee and subcommittee members and staff that have been
matched to a BioGuide ID. Analyzes the result of running the add_bioguide_id.py script.
"""
import json

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

    print(f"\nSubcommittee Members:")
    print(f"  Total: {stats['subcommittee_members']['total']}")
    print(
        f"  Matched: {stats['subcommittee_members']['matched']} "
        + f"({(stats['subcommittee_members']['matched'] / stats['subcommittee_members']['total'] * 100):.1f}%)"
    )

    print(f"\nAll Members Combined:")
    print(f"  Total: {total_members}")
    print(
        f"  Matched: {matched_members} ({(matched_members / total_members * 100):.1f}%)"
    )

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
    print(
        f"  Matched: {stats['committee_staff']['matched']} "
        + f"({(stats['committee_staff']['matched'] / stats['committee_staff']['total'] * 100):.1f}%)"
    )

    print(f"\nSubcommittee Staff:")
    print(f"  Total: {stats['subcommittee_staff']['total']}")
    print(
        f"  Matched: {stats['subcommittee_staff']['matched']} "
        + f"({(stats['subcommittee_staff']['matched'] / stats['subcommittee_staff']['total'] * 100):.1f}%)"
    )

    print(f"\nAll Staff Combined:")
    print(f"  Total: {total_staff}")
    print(f"  Matched: {matched_staff} ({(matched_staff / total_staff * 100):.1f}%)")

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

def main():
    """
    Main function to analyze the matching statistics. When called,
    it will analyze the matching statistics from the JSON files in the `json_files` list.
    """
    import os
    
    # Get the root directory of the project
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    json_files = [os.path.join(root_dir, "CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_bioguide.json")]

    for json_file in json_files:
        try:
            stats = analyze_matching_stats(json_file)
            print_stats(stats)

        except FileNotFoundError as e:
            print(f"Error: Could not find file - {e}")
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON format - {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
