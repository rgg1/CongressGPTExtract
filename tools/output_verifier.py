"""
Verifies the output of either a specific JSON file or all JSON files for a Congress number.
Prints out analysis of the JSON files to identify issues with the data.
"""
import os
import json
import re
import collections
import glob
import argparse

def extract_names(data: dict | list, role: str = "unknown") -> list:
    """
    Extract people's names from the JSON data based on the JSON structure with role 
    information.

    Different file types have different structures for storing names:
    - departments.py: "member_name" fields
    - judiciary.py: "name" fields inside "court_personnel" or "circuit_personnel"
    - international_organizations.py: "name" fields inside "organization_personnel" or
      "department_personnel"
    - house_senate_committees.py: "member_name" and "staff_name" fields in subcommittees
    - diplomatic_offices.py: "name" fields directly in diplomatic_representatives array

    Args:
        data: The JSON data to extract names from
        role: The role of the person (member, staff, or unknown)

    Returns: Tuples of (name, role)
    """
    names = []

    # List of country names and common non-person entries to filter out
    country_names = [
        "Albania",
        "Algeria",
        "Angola",
        "Argentina",
        "Armenia",
        "Australia",
        "Austria",
        "Azerbaijan",
        "Afghanistan",
        "Andorra",
        "Bahamas",
        "Bahrain",
        "Bangladesh",
        "Belarus",
        "Belgium",
        "Belize",
        "Benin",
        "Bhutan",
        "Bolivia",
        "Bosnia",
        "Brazil",
        "Brunei",
        "Bulgaria",
        "Burkina Faso",
        "Burundi",
        "Cambodia",
        "Cameroon",
        "Canada",
        "Cape Verde",
        "Chad",
        "Chile",
        "China",
        "Colombia",
        "Comoros",
        "Congo",
        "Costa Rica",
        "Croatia",
        "Cuba",
        "Cyprus",
        "Czech Republic",
        "Denmark",
        "Djibouti",
        "Dominica",
        "Dominican Republic",
        "Ecuador",
        "Egypt",
        "El Salvador",
        "Equatorial Guinea",
        "Eritrea",
        "Estonia",
        "Ethiopia",
        "Fiji",
        "Finland",
        "France",
        "Gabon",
        "Gambia",
        "Georgia",
        "Germany",
        "Ghana",
        "Greece",
        "Grenada",
        "Guatemala",
        "Guinea",
        "Guinea-Bissau",
        "Guyana",
        "Haiti",
        "Honduras",
        "Hungary",
        "Iceland",
        "India",
        "Indonesia",
        "Iran",
        "Iraq",
        "Ireland",
        "Israel",
        "Italy",
        "Ivory Coast",
        "Jamaica",
        "Japan",
        "Jordan",
        "Kazakhstan",
        "Kenya",
        "Kiribati",
        "Korea",
        "Kosovo",
        "Kuwait",
        "Kyrgyzstan",
        "Laos",
        "Latvia",
        "Lebanon",
        "Lesotho",
        "Liberia",
        "Libya",
        "Lithuania",
        "Luxembourg",
        "Macedonia",
        "Madagascar",
        "Malawi",
        "Malaysia",
        "Maldives",
        "Mali",
        "Malta",
        "Marshall Islands",
        "Mauritania",
        "Mauritius",
        "Mexico",
        "Micronesia",
        "Moldova",
        "Monaco",
        "Mongolia",
        "Montenegro",
        "Morocco",
        "Mozambique",
        "Myanmar",
        "Namibia",
        "Nauru",
        "Nepal",
        "Netherlands",
        "New Zealand",
        "Nicaragua",
        "Niger",
        "Nigeria",
        "North Korea",
        "Norway",
        "Oman",
        "Pakistan",
        "Palau",
        "Palestine",
        "Panama",
        "Papua New Guinea",
        "Paraguay",
        "Peru",
        "Philippines",
        "Poland",
        "Portugal",
        "Qatar",
        "Romania",
        "Russia",
        "Rwanda",
        "Samoa",
        "San Marino",
        "Saudi Arabia",
        "Senegal",
        "Serbia",
        "Seychelles",
        "Sierra Leone",
        "Singapore",
        "Slovakia",
        "Slovenia",
        "Solomon Islands",
        "Somalia",
        "South Africa",
        "South Korea",
        "South Sudan",
        "Spain",
        "Sri Lanka",
        "St. Kitts",
        "St. Lucia",
        "St. Vincent",
        "Sudan",
        "Suriname",
        "Swaziland",
        "Sweden",
        "Switzerland",
        "Syria",
        "Taiwan",
        "Tajikistan",
        "Tanzania",
        "Thailand",
        "Timor-Leste",
        "Togo",
        "Tonga",
        "Trinidad",
        "Tunisia",
        "Turkey",
        "Turkmenistan",
        "Tuvalu",
        "Uganda",
        "Ukraine",
        "United Arab Emirates",
        "United Kingdom",
        "United States",
        "Uruguay",
        "Uzbekistan",
        "Vanuatu",
        "Vatican City",
        "Venezuela",
        "Vietnam",
        "Yemen",
        "Yugoslavia",
        "Zambia",
        "Zimbabwe",
        "Office",
        "Member",
        "Observer",
    ]

    # Handle diplomatic representatives - these have a direct "name" field
    if isinstance(data, dict) and "diplomatic_representatives" in data:
        for representative in data["diplomatic_representatives"]:
            if isinstance(representative, dict) and "name" in representative:
                name = representative["name"]
                # Skip country names and non-person entries
                if (
                    name not in country_names
                    and not name.startswith("Office")
                    and name != "Member"
                ):
                    # Use the role if available, otherwise "diplomatic representative"
                    rep_role = representative.get("role", "diplomatic representative")
                    names.append((name, rep_role))
        return names

    if isinstance(data, dict):
        current_role = role  # Default to passed-in role

        # Try to determine role from structure
        if "member_role" in data:
            if any(
                staff_term in str(data.get("member_role", "")).lower()
                for staff_term in [
                    "staff",
                    "counsel",
                    "director",
                    "secretary",
                    "clerk",
                    "assistant",
                    "aide",
                    "advisor",
                ]
            ):
                current_role = "staff"
            else:
                current_role = "member"

        # Department files use member_name for people
        if "member_name" in data and data["member_name"] is not None:
            name = data["member_name"]
            if (
                name not in country_names
                and not name.startswith("Office")
                and name != "Member"
            ):
                names.append((name, current_role))

        # Files with personnel lists (courts, organizations)
        for field in [
            "court_personnel",
            "circuit_personnel",
            "organization_personnel",
            "department_personnel",
            "office_personnel",
        ]:
            if field in data and isinstance(data[field], list):
                # These are typically staff
                staff_role = "staff"
                for person in data[field]:
                    if (
                        isinstance(person, dict)
                        and "name" in person
                        and person["name"] is not None
                    ):
                        name = person["name"]
                        # Skip country names and non-person entries
                        if name not in country_names and not name.startswith("Office"):
                            person_role = staff_role
                            if "role" in person:
                                role_str = str(person.get("role", "")).lower()
                                if any(
                                    member_term in role_str
                                    for member_term in [
                                        "chair",
                                        "member",
                                        "ranking",
                                        "vice",
                                        "president",
                                        "representative",
                                        "senator",
                                    ]
                                ):
                                    person_role = "member"
                            names.append((name, person_role))

        # Cabinet and executive office structures
        if "cabinet" in data and isinstance(data["cabinet"], list):
            for member in data["cabinet"]:
                if (
                    isinstance(member, dict)
                    and "member_name" in member
                    and member["member_name"] is not None
                ):
                    name = member["member_name"]
                    if name not in country_names and not name.startswith("Office"):
                        # Cabinet members are typically members, not staff
                        names.append((name, "member"))

        if "members" in data and isinstance(data["members"], list):
            for member in data["members"]:
                if (
                    isinstance(member, dict)
                    and "name" in member
                    and member["name"] is not None
                ):
                    name = member["name"]
                    if name not in country_names and not name.startswith("Office"):
                        names.append((name, "member"))

        if "staff" in data and isinstance(data["staff"], list):
            for staff in data["staff"]:
                if (
                    isinstance(staff, dict)
                    and "name" in staff
                    and staff["name"] is not None
                ):
                    name = staff["name"]
                    if name not in country_names and not name.startswith("Office"):
                        names.append((name, "staff"))

        for key, value in data.items():
            # Skip organization_name, department_name, court_name, etc. to avoid
            # analyzing non-person names
            if key not in [
                "organization_name",
                "department_name",
                "court_name",
                "circuit_name",
                "office_name",
                "officers",
                "state",
                "role",
                "member_role",
            ] and (isinstance(value, dict) or isinstance(value, list)):
                # Pass down role information for nested elements
                nested_role = current_role
                # Check if we're entering a specifically role-defined section
                if key == "staff":
                    nested_role = "staff"
                elif key == "members":
                    nested_role = "member"
                names.extend(extract_names(value, nested_role))

    elif isinstance(data, list):
        for item in data:
            names.extend(extract_names(item, role))

    return names

def analyze_names_in_json_file(json_file: str) -> dict | None:
    """
    Analyze names in a specific JSON file for quality and characteristics.

    Args:
        json_file: Path to the JSON file to analyze

    Returns: Mapping of analysis results
    """
    empty_names = []
    short_names = []
    single_word_names = []
    non_alpha_names = []
    long_word_names = []
    long_names = []
    special_characters = {}
    duplicate_names = {}
    name_frequencies = collections.Counter()

    short_name_threshold = 2  # Length in characters
    long_word_threshold = 15  # Length of a single word in a name
    long_name_threshold = 5  # Number of words in a name

    non_alpha_pattern = re.compile(
        r"[^a-zA-Z\s\'\-\.,()]"
    )  # Pattern to find special characters apart from periods, commas, and parentheses

    try:
        with open(json_file, "r") as f:
            data = json.load(f)
            file_names = []

            # Extract names from the JSON structure - now returns (name, role) tuples
            names_with_roles = extract_names(data)

            # For backwards compatibility with the rest of this function
            # Strip off the role information and just use the names
            names = [name for name, _ in names_with_roles]

            file_names.extend(names)

            # Update name frequency counter
            name_frequencies.update(file_names)

            # Check for duplicate names
            name_counts = collections.Counter(file_names)
            duplicates = {
                name: count for name, count in name_counts.items() if count > 1
            }
            if duplicates:
                duplicate_names[os.path.basename(json_file)] = duplicates

            for name in file_names:
                # Check for empty names or placeholders
                if (
                    not name
                    or name.strip() == ""
                    or name.lower() in ["[vacant]", "n/a"]
                ):
                    empty_names.append((os.path.basename(json_file), name))
                    continue

                # Check for short names
                if len(name) <= short_name_threshold:
                    short_names.append((os.path.basename(json_file), name))

                # Check for single-word names
                words = [w for w in name.split() if w]
                if len(words) == 1:
                    single_word_names.append((os.path.basename(json_file), name))

                # Check for non-alphabetic characters (excluding spaces, hyphens,
                # apostrophes, and periods)
                non_alpha_match = non_alpha_pattern.search(name)
                if non_alpha_match:
                    non_alpha_names.append((os.path.basename(json_file), name))
                    char = name[non_alpha_match.start()]
                    special_characters[char] = special_characters.get(char, 0) + 1

                # Check for words that are extremely long
                for word in words:
                    # Handle hyphenated names by treating each part as a separate word
                    if "-" in word:
                        parts = word.split("-")
                        if any(len(part) > long_word_threshold for part in parts):
                            long_word_names.append(
                                (os.path.basename(json_file), name, word)
                            )
                    elif len(word) > long_word_threshold:
                        long_word_names.append(
                            (os.path.basename(json_file), name, word)
                        )

                # Check for names with many words
                if len(words) > long_name_threshold:
                    long_names.append((os.path.basename(json_file), name))

    except Exception as e:
        print(f"Error analyzing names in {json_file}: {str(e)}")
        return None

    result = {
        "total_unique_names": len(name_frequencies),
        "total_name_occurrences": sum(name_frequencies.values()),
        "empty_names": empty_names,
        "short_names": short_names,
        "single_word_names": single_word_names,
        "non_alpha_names": non_alpha_names,
        "long_word_names": long_word_names,
        "long_names": long_names,
        "special_characters": special_characters,
        "duplicate_names": duplicate_names,
        "name_frequencies": name_frequencies,
    }

    return result

def analyze_member_staff_overlap(json_file: str) -> dict | None:
    """
    Analyze if people appear as both members and staff in a House or Senate committee file.

    Args:
        json_file: Path to the JSON file to analyze

    Returns: Mapping of analysis results
    """
    # {name: {"member": [files], "staff": [files], "unknown": [files]}}
    people_roles = {}

    file_name = os.path.basename(json_file)
    if not ("HOUSECOMMITTEES" in file_name or "SENATECOMMITTEES" in file_name):
        return {"error": "Not a House or Senate committee file"}

    try:
        with open(json_file, "r") as f:
            data = json.load(f)

            # Process committee files looking for members and staff
            if "committees" in data:
                for committee in data["committees"]:
                    # Process each subcommittee (including main committee which is
                    # stored as a subcommittee)
                    if "subcommittees" in committee:
                        for subcommittee in committee["subcommittees"]:
                            if "subcommittee_members" in subcommittee:
                                for person in subcommittee["subcommittee_members"]:
                                    # Check if it's a member or staff based on field names
                                    if (
                                        "member_name" in person
                                        and person["member_name"]
                                    ):
                                        name = person["member_name"]
                                        role = "member"
                                    elif (
                                        "staff_name" in person and person["staff_name"]
                                    ):
                                        name = person["staff_name"]
                                        role = "staff"
                                    else:
                                        continue

                                    # Skip placeholders and empty names
                                    if (
                                        not name
                                        or name.strip() == ""
                                        or name.lower() in ["[vacant]", "n/a"]
                                    ):
                                        continue

                                    # Initialize entry for this person if it doesn't exist
                                    if name not in people_roles:
                                        people_roles[name] = {
                                            "member": [],
                                            "staff": [],
                                            "unknown": [],
                                        }

                                    # Add this file to the appropriate role list
                                    if file_name not in people_roles[name][role]:
                                        people_roles[name][role].append(file_name)

    except Exception as e:
        print(f"Error analyzing member/staff overlap in {json_file}: {str(e)}")
        return None

    # Find people who appear as both member and staff
    dual_role_people = {}
    for name, roles in people_roles.items():
        if roles["member"] and roles["staff"]:
            member_count = len(roles["member"])
            staff_count = len(roles["staff"])
            total_dual_roles = member_count + staff_count

            dual_role_people[name] = {
                "member_files": roles["member"],
                "staff_files": roles["staff"],
                "member_count": member_count,
                "staff_count": staff_count,
                "total_dual_roles": total_dual_roles,
            }

    result = {
        "total_people": len(people_roles),
        "dual_role_people": dual_role_people,
        "dual_role_count": len(dual_role_people),
        "dual_role_percentage": (len(dual_role_people) / len(people_roles) * 100)
        if people_roles
        else 0,
    }

    return result

def verify_json_file(json_file: str) -> dict:
    """
    Verify the quality and structure of a JSON output file.

    Args:
        json_file: Path to the JSON file to verify

    Returns: Verification results. Uses return values from
        analyze_names_in_json_file and analyze_member_staff_overlap
    """
    results = {}

    # Basic file info
    file_size = os.path.getsize(json_file)
    results["file_info"] = {
        "file_name": os.path.basename(json_file),
        "file_size": file_size,
        "file_size_kb": file_size / 1024,
    }

    try:
        with open(json_file, "r") as f:
            data = json.load(f)

            # Find the type of JSON file based on keys
            json_type = None
            if "committees" in data:
                json_type = "committees"
                count = len(data["committees"])
            elif "diplomatic_representatives" in data:
                json_type = "diplomatic_representatives"
                count = len(data["diplomatic_representatives"])
            elif "courts" in data:
                json_type = "courts"
                count = len(data["courts"])
            elif "agencies" in data:
                json_type = "agencies"
                count = len(data["agencies"])
            elif "organizations" in data:
                json_type = "organizations"
                count = len(data["organizations"])
            elif "cabinet" in data or "departments" in data:
                json_type = "departments"
                count = len(data.get("departments", [])) + len(data.get("cabinet", []))
            elif "government_bodies" in data:
                json_type = "government_bodies"
                count = len(data["government_bodies"])
            else:
                json_type = "unknown"
                count = 0

            results["content_info"] = {"json_type": json_type, "entry_count": count}

            # Analyze names
            name_analysis = analyze_names_in_json_file(json_file)
            if name_analysis:
                results["name_analysis"] = name_analysis

            # Analyze member/staff overlap for committee files
            if json_type == "committees":
                member_staff_analysis = analyze_member_staff_overlap(json_file)
                if member_staff_analysis:
                    results["member_staff_analysis"] = member_staff_analysis

    except json.JSONDecodeError as e:
        results["error"] = f"Invalid JSON format: {str(e)}"
    except Exception as e:
        results["error"] = f"Error analyzing file: {str(e)}"

    return results

def print_verification_results(results: dict) -> None:
    """
    Print formatted verification results.

    Args:
        results: Results from verify_json_file
    """
    print("\nJSON File Verification Results")
    print("=" * 80)

    if "file_info" in results:
        info = results["file_info"]
        print(f"\nFile: {info['file_name']}")
        print(f"Size: {info['file_size_kb']:.2f} KB")

    if "content_info" in results:
        info = results["content_info"]
        print(f"\nContent Type: {info['json_type']}")
        print(f"Number of Entries: {info['entry_count']}")

    if "name_analysis" in results:
        analysis = results["name_analysis"]
        print("\nName Quality Analysis:")
        print("-" * 50)
        print(f"Total unique names: {analysis['total_unique_names']}")
        print(f"Total name occurrences: {analysis['total_name_occurrences']}")

        # Empty names
        empty_names = analysis["empty_names"]
        if empty_names:
            print(f"\nEmpty or placeholder names: {len(empty_names)}")
            for i, (_, name) in enumerate(empty_names[:5]):
                print(f'  • "{name}"')
            if len(empty_names) > 5:
                print(f"  ... and {len(empty_names) - 5} more")

        # Short names
        short_names = analysis["short_names"]
        if short_names:
            print(f"\nShort names (≤ 2 characters): {len(short_names)}")
            for i, (_, name) in enumerate(short_names[:5]):
                print(f'  • "{name}"')
            if len(short_names) > 5:
                print(f"  ... and {len(short_names) - 5} more")

        # Single-word names
        single_word_names = analysis["single_word_names"]
        if single_word_names:
            print(f"\nSingle-word names: {len(single_word_names)}")
            for i, (_, name) in enumerate(single_word_names[:5]):
                print(f'  • "{name}"')
            if len(single_word_names) > 5:
                print(f"  ... and {len(single_word_names) - 5} more")

        # Non-alphabetic characters
        non_alpha_names = analysis["non_alpha_names"]
        if non_alpha_names:
            print(f"\nNames with special characters: {len(non_alpha_names)}")
            for i, (_, name) in enumerate(non_alpha_names[:5]):
                print(f'  • "{name}"')
            if len(non_alpha_names) > 5:
                print(f"  ... and {len(non_alpha_names) - 5} more")

            # Show special characters
            print("\nSpecial characters found:")
            for char, count in list(
                sorted(
                    analysis["special_characters"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )[:10]:
                print(f"  '{char}': {count} occurrences")

        # Long word names
        long_word_names = analysis["long_word_names"]
        if long_word_names:
            print(f"\nNames with very long words: {len(long_word_names)}")
            for i, (_, name, word) in enumerate(long_word_names[:5]):
                print(f'  • "{name}" (long word: "{word}")')
            if len(long_word_names) > 5:
                print(f"  ... and {len(long_word_names) - 5} more")

        # Long names
        long_names = analysis["long_names"]
        if long_names:
            print(f"\nNames with many words: {len(long_names)}")
            for i, (_, name) in enumerate(long_names[:5]):
                print(f'  • "{name}"')
            if len(long_names) > 5:
                print(f"  ... and {len(long_names) - 5} more")

        # Duplicate names
        duplicate_names = analysis["duplicate_names"]
        if duplicate_names:
            print(
                f"\nDuplicate names found: {sum(len(dups) for dups in duplicate_names.values())}"
            )
            for _, duplicates in duplicate_names.items():
                # Sort duplicates by count (highest first)
                sorted_dups = sorted(
                    duplicates.items(), key=lambda x: x[1], reverse=True
                )
                for name, count in sorted_dups[:5]:
                    print(f'  • "{name}": {count} occurrences')
                if len(sorted_dups) > 5:
                    print(f"  ... and {len(sorted_dups) - 5} more duplicates")

        # Most frequent names
        print("\nMost frequent names:")
        for name, count in analysis["name_frequencies"].most_common(5):
            print(f'  • "{name}": {count} occurrences')

    if "member_staff_analysis" in results:
        analysis = results["member_staff_analysis"]
        if "error" not in analysis:
            print("\nMember and Staff Role Analysis:")
            print("-" * 50)
            print(f"Total people found: {analysis['total_people']}")
            print(
                f"People with both member and staff roles: {analysis['dual_role_count']}"
            )
            print(
                f"Percentage with dual roles: {analysis['dual_role_percentage']:.2f}%"
            )

            # Show top dual-role people
            if analysis["dual_role_people"]:
                print("\nTop people appearing as both member and staff:")
                sorted_people = sorted(
                    analysis["dual_role_people"].items(),
                    key=lambda x: x[1]["total_dual_roles"],
                    reverse=True,
                )
                for i, (name, data) in enumerate(sorted_people[:5]):
                    print(f'  {i+1}. "{name}":')
                    print(f"     - Member in {data['member_count']} places")
                    print(f"     - Staff in {data['staff_count']} places")

                if len(sorted_people) > 5:
                    print(
                        f"  ... and {len(sorted_people) - 5} more people with dual roles"
                    )
        else:
            print(f"\nMember/Staff Analysis: {analysis['error']}")

    if "error" in results:
        print(f"\nERROR: {results['error']}")

def verify_output_file(json_file: str) -> dict:
    """
    Verify a specific JSON output file.

    Args:
        json_file: Path to the JSON file to verify

    Returns: Mapping of verification results
        returned from verify_json_file
    """
    print(f"Verifying file: {json_file}")

    if not os.path.isfile(json_file):
        print(f"Error: File not found - {json_file}")
        return {"error": "File not found"}

    results = verify_json_file(json_file)

    print_verification_results(results)

    return results

def verify_output_files_for_congress(congress_number: int | str) -> list:
    """
    Verify all JSON output files for the specified Congress number.

    Args:
        congress_number: Congress number to verify

    Returns: Verification results for each file
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    output_dir = os.path.join(root_dir, "outputs", str(congress_number))

    if not os.path.exists(output_dir):
        print(
            f"Error: Output directory for Congress {congress_number} not found: {output_dir}"
        )
        return []

    json_files = []
    for file in glob.glob(os.path.join(output_dir, "*.json")):
        # Skip files that are themselves the result of adding bioguide or Thomas IDs
        if "with_bioguide" in file or "with_thomas_ids" in file:
            continue
        json_files.append(file)

    if not json_files:
        print(f"No JSON files found for Congress {congress_number} in {output_dir}")
        return []

    print(f"Verifying {len(json_files)} JSON files for Congress {congress_number}...")
    all_results = []

    for file in json_files:
        print(f"\nVerifying {os.path.basename(file)}...")
        results = verify_output_file(file)
        all_results.append(results)

    return all_results

def main():
    """
    Main function that verifies either a specific file or all files for a congress number.
    Can be called in two ways:
    1. With a specific file path: Verify that file
    2. With --congress argument: Verify all JSON files for that congress
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Verify output JSON files. Defaults to 108th Congress if no json_file or congress is specified.")
    parser.add_argument("json_file", nargs="?", help="JSON file to verify (optional)")
    parser.add_argument(
        "--congress", type=str, help="Verify all JSON files for this Congress number"
    )
    args = parser.parse_args()

    # Process based on arguments
    if args.congress:
        verify_output_files_for_congress(args.congress)
    elif args.json_file:
        verify_output_file(args.json_file)
    else:
        print("No file or congress specified. Defaulting to 108th Congress...")
        verify_output_files_for_congress("108")

if __name__ == "__main__":
    main()
