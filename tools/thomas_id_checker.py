"""
Prints statistics on the number of committees and subcommittees that have been matched to a Thomas
ID. Analyzes the result of running the add_thomas_id.py script.
"""
import json
import sys
from typing import Dict, List, Tuple
import os
import glob
import argparse

def analyze_committee_coverage(
    json_file: str,
) -> Tuple[Dict[str, int], List[str], List[Tuple[str, str]]]:
    """
    Analyze the coverage of Thomas IDs in the committee JSON file.

    Args:
        json_file: Path to the JSON file containing committee data.

    Returns:A tuple containing the statistics for committee and subcommittee mapping,
            a list of unmapped committees, and a list of unmapped subcommittees
    """
    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        # Initialize counters
        stats = {
            "total_committees": 0,
            "total_subcommittees": 0,
            "mapped_committees": 0,
            "mapped_subcommittees": 0,
        }

        # Track unmapped entities
        unmapped_committees = []
        unmapped_subcommittees = (
            []
        )  # Will store tuples of (parent_committee, subcommittee)

        # Analyze main committees
        stats["total_committees"] = len(data["committees"])

        # Count mapped committees and track unmapped ones
        for committee in data["committees"]:
            committee_name = committee["committee_name"]

            if "thomas_id" in committee:
                stats["mapped_committees"] += 1
            else:
                unmapped_committees.append(committee_name)

            # Count and analyze subcommittees
            if "subcommittees" in committee:
                subcommittees = committee["subcommittees"]
                stats["total_subcommittees"] += len(subcommittees)

                # Count mapped subcommittees and track unmapped ones
                for subcommittee in subcommittees:
                    subcommittee_name = subcommittee["subcommittee_name"]

                    if "thomas_id" in subcommittee:
                        stats["mapped_subcommittees"] += 1
                    else:
                        unmapped_subcommittees.append(
                            (committee_name, subcommittee_name)
                        )

        # Calculate percentages
        committee_percentage = (
            (stats["mapped_committees"] / stats["total_committees"] * 100)
            if stats["total_committees"] > 0
            else 0
        )
        subcommittee_percentage = (
            (stats["mapped_subcommittees"] / stats["total_subcommittees"] * 100)
            if stats["total_subcommittees"] > 0
            else 0
        )

        # Print results
        print("\nCommittee Mapping Statistics:")
        print("=" * 80)
        print("Main Committees:")
        print(f"  Total: {stats['total_committees']}")
        print(f"  Mapped: {stats['mapped_committees']}")
        print(f"  Coverage: {committee_percentage:.1f}%")

        print(f"\nSubcommittees:")
        print(f"  Total: {stats['total_subcommittees']}")
        print(f"  Mapped: {stats['mapped_subcommittees']}")
        print(f"  Coverage: {subcommittee_percentage:.1f}%")

        print(f"\nOverall:")
        total = stats["total_committees"] + stats["total_subcommittees"]
        mapped = stats["mapped_committees"] + stats["mapped_subcommittees"]
        overall_percentage = (mapped / total * 100) if total > 0 else 0
        print(f"  Total Entities: {total}")
        print(f"  Total Mapped: {mapped}")
        print(f"  Overall Coverage: {overall_percentage:.1f}%")

        print("\nUnmapped Committees Examples:")
        print("=" * 80)
        if unmapped_committees:
            for committee in unmapped_committees[:5]:
                print(f"  • {committee}")
            if len(unmapped_committees) > 5:
                print(f"  ... and {len(unmapped_committees) - 5} more")
        else:
            print("  All committees were successfully mapped!")

        print("\nUnmapped Subcommittees Examples:")
        print("=" * 80)
        if unmapped_subcommittees:
            # Group by parent committee for better readability
            grouped_examples = {}
            for parent, subcommittee in sorted(
                unmapped_subcommittees, key=lambda x: x[0]
            )[:5]:
                if parent not in grouped_examples:
                    grouped_examples[parent] = []
                grouped_examples[parent].append(subcommittee)

            for parent, subs in grouped_examples.items():
                print(f"\n  Under {parent}:")
                for sub in subs[:3]:
                    print(f"    • {sub}")
                if len(subs) > 3:
                    print(f"    ... and {len(subs) - 3} more")

            if len(unmapped_subcommittees) > 5:
                print(f"\n  ... and more unmapped subcommittees in other committees")
        else:
            print("  All subcommittees were successfully mapped!")

        return stats, unmapped_committees, unmapped_subcommittees

    except FileNotFoundError:
        print(f"Error: Could not find file {json_file}")
        return None, [], []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {json_file}")
        return None, [], []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, [], []

def check_thomas_id_matches(json_file: str) -> tuple:
    """
    Check Thomas ID matches for a specific JSON file.

    Args:
        json_file: Path to the JSON file with Thomas IDs.

    Returns: Contains the statistics, unmapped committees, and unmapped subcommittees.
    """
    return analyze_committee_coverage(json_file)

def check_thomas_id_matches_for_congress(congress_number: int) -> List[Dict[str, int]]:
    """
    Check Thomas ID matches for all committee files with Thomas IDs for a specific congress.

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

    thomas_files = []
    for file in glob.glob(os.path.join(output_dir, "*with_thomas_ids*.json")):
        thomas_files.append(file)

    if not thomas_files:
        for file in glob.glob(os.path.join(root_dir, "*with_thomas_ids*.json")):
            thomas_files.append(file)

    if not thomas_files:
        print(f"No files with Thomas IDs found for Congress {congress_number}")
        return []

    print(
        f"Checking Thomas ID matches in {len(thomas_files)} files for Congress {congress_number}..."
    )
    all_stats = []

    for file in thomas_files:
        print(f"\nChecking {os.path.basename(file)}...")
        stats, _, _ = check_thomas_id_matches(file)
        if stats:
            all_stats.append(stats)

    return all_stats

def main():
    """
    Main function that checks either a specific file or all files for a congress number.
    Can be called in three ways:
    1. No arguments: Check the default House committees file with Thomas IDs (testing)
    2. With a specific file path: Check that file
    3. With --congress argument: Check all files with Thomas IDs for that congress
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Check Thomas ID matches in committee JSON files"
    )
    parser.add_argument(
        "json_file", nargs="?", help="JSON file with Thomas IDs to check (optional)"
    )
    parser.add_argument(
        "--congress",
        type=str,
        help="Check all files with Thomas IDs for this Congress number",
    )
    args = parser.parse_args()

    # Process based on arguments
    if args.congress:
        check_thomas_id_matches_for_congress(args.congress)
    elif args.json_file:
        check_thomas_id_matches(args.json_file)
    else:
        json_file = os.path.join(
            root_dir, "CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_thomas_ids.json"
        )
        try:
            check_thomas_id_matches(json_file)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            print(
                "Default file not found. Please specify an input file or use --congress option."
            )
            sys.exit(1)

if __name__ == "__main__":
    main()
