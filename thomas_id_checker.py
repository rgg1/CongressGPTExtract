"""
Prints statistics on the number of committees and subcommittees that have been matched to a Thomas
ID. Analyzes the result of running the add_thomas_id.py script.
"""
import json
from typing import Dict, List, Tuple


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

        # Print unmapped entities
        print("\nUnmapped Committees:")
        print("=" * 80)
        if unmapped_committees:
            for committee in unmapped_committees:
                print(f"  • {committee}")
        else:
            print("  All committees were successfully mapped!")

        print("\nUnmapped Subcommittees:")
        print("=" * 80)
        if unmapped_subcommittees:
            # Group by parent committee for better readability
            current_parent = None
            for parent, subcommittee in sorted(
                unmapped_subcommittees, key=lambda x: x[0]
            ):
                if parent != current_parent:
                    print(f"\n  Under {parent}:")
                    current_parent = parent
                print(f"    • {subcommittee}")
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


def main():
    """
    Main function to analyze the coverage of Thomas IDs in committee data.
    """
    input_file = "updated_committees.json"  # Use the updated JSON file with thomas_ids
    # input_files = ["CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_thomas_ids.json"]
    input_file = "CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_thomas_ids.json"

    # Run analysis
    # for input_file in input_files:
    _, _, _ = analyze_committee_coverage(
        input_file
    )


if __name__ == "__main__":
    main()
