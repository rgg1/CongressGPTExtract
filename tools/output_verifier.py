import os
import json
import re
import statistics
import collections
import sys
from pathlib import Path

def analyze_directory_files(congress_number=None):
    """
    Analyze the output files for a specific congress number or the default (108).
    
    Args:
        congress_number: The congress number to analyze.
    """
    # Get the root directory
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    root_dir = script_dir.parent
    
    # Use the provided congress number or default to 108
    congress = congress_number or "108"
    
    # Define the directories
    txt_dir = root_dir / f"congressional_directory_files/congress_{congress}/txt"
    json_dir = root_dir / f"outputs/{congress}"
    
    # Get all text files
    txt_files = [f for f in txt_dir.glob("*.txt")]
    
    # Get all JSON files
    json_files = [f for f in json_dir.glob("*.json")]
    
    # Create a set of expected JSON filenames based on text files
    expected_json_names = {txt_file.name + "_output.json" for txt_file in txt_files}
    
    # Create a set of actual JSON filenames
    actual_json_names = {json_file.name for json_file in json_files}
    
    # Find missing JSON files
    missing_jsons = expected_json_names - actual_json_names
    
    # Calculate JSON file line counts
    json_line_counts = []
    json_line_map = {}
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            # Count the number of lines in the file
            line_count = sum(1 for _ in f)
            json_line_counts.append(line_count)
            json_line_map[json_file.name] = line_count
    
    # Print basic report
    print(f"Total text files: {len(txt_files)}")
    print(f"Total JSON files: {len(json_files)}")
    print(f"Text files with matching JSON: {len(txt_files) - len(missing_jsons)}")
    print(f"Text files without matching JSON: {len(missing_jsons)}")
    
    if json_line_counts:
        print("\nJSON file line count statistics:")
        print(f"  Minimum lines: {min(json_line_counts):,}")
        print(f"  Maximum lines: {max(json_line_counts):,}")
        print(f"  Average lines: {statistics.mean(json_line_counts):,.2f}")
        print(f"  Median lines: {statistics.median(json_line_counts):,.2f}")
        if len(json_line_counts) > 1:
            print(f"  Standard deviation: {statistics.stdev(json_line_counts):,.2f}")
    
    if missing_jsons:
        print("\nText files without matching JSON:")
        for missing in sorted(missing_jsons):
            # Convert back to original txt filename
            original_txt = missing.replace("_output.json", "")
            print(f"  - {original_txt}")
    
    print("\nJSON file line counts:")
    for name, count in sorted(json_line_map.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name}: {count:,} lines")
    
    # Analyze names in the JSON files
    print("\n" + "="*50)
    print("NAME QUALITY ANALYSIS")
    print("="*50)
    
    analyze_names_in_json_files(json_files)
    
    # Check for people who appear as both members and staff
    print("\n" + "="*50)
    print("MEMBER AND STAFF ROLE ANALYSIS")
    print("="*50)
    
    analyze_member_staff_overlap(json_files)

def analyze_names_in_json_files(json_files):
    # Initialize counters and containers for name analysis
    empty_names = []
    short_names = []
    single_word_names = []
    non_alpha_names = []
    long_word_names = []
    long_names = []
    special_characters = {}
    name_count_by_file = {}
    duplicate_names = {}
    name_frequencies = collections.Counter()
    
    # Set thresholds for analysis
    short_name_threshold = 2  # Length in characters
    long_word_threshold = 15  # Length of a single word in a name
    long_name_threshold = 5   # Number of words in a name
    max_examples = 10         # Maximum number of examples to show per category
    
    # Regular expressions
    non_alpha_pattern = re.compile(r'[^a-zA-Z\s\'\-\.,()]')  # Pattern to find special characters apart from periods, commas, and parentheses
    
    # Process each JSON file
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                file_names = []
                
                # Extract names from the JSON structure - now returns (name, role) tuples
                names_with_roles = extract_names(data)
                
                # For backwards compatibility with the rest of this function
                # Strip off the role information and just use the names
                names = [name for name, _ in names_with_roles]
                
                file_names.extend(names)
                
                # Update the counter for each file
                name_count_by_file[json_file.name] = len(file_names)
                
                # Update global name frequency counter
                name_frequencies.update(file_names)
                
                # Check for duplicate names within the same file
                name_counts = collections.Counter(file_names)
                duplicates = {name: count for name, count in name_counts.items() if count > 1}
                if duplicates:
                    duplicate_names[json_file.name] = duplicates
                
                # Analyze each name
                for name in file_names:
                    # Check for empty names or placeholders
                    if not name or name.strip() == "" or name.lower() in ["[vacant]", "n/a"]:
                        empty_names.append((json_file.name, name))
                        continue
                    
                    # Check for short names
                    if len(name) <= short_name_threshold:
                        short_names.append((json_file.name, name))
                    
                    # Check for single-word names
                    words = [w for w in name.split() if w]
                    if len(words) == 1:
                        single_word_names.append((json_file.name, name))
                    
                    # Check for non-alphabetic characters (excluding spaces, hyphens, apostrophes, and periods)
                    non_alpha_match = non_alpha_pattern.search(name)
                    if non_alpha_match:
                        non_alpha_names.append((json_file.name, name))
                        char = name[non_alpha_match.start()]
                        special_characters[char] = special_characters.get(char, 0) + 1
                    
                    # Check for words that are extremely long
                    for word in words:
                        # Handle hyphenated names by treating each part as a separate word
                        if '-' in word:
                            # Split on hyphens and check each part
                            parts = word.split('-')
                            if any(len(part) > long_word_threshold for part in parts):
                                long_word_names.append((json_file.name, name, word))
                        elif len(word) > long_word_threshold:
                            long_word_names.append((json_file.name, name, word))
                    
                    # Check for names with many words
                    if len(words) > long_name_threshold:
                        long_names.append((json_file.name, name))
                
            except json.JSONDecodeError:
                print(f"Error: Could not parse JSON file {json_file.name}")
    
    # Print analysis results
    print("\nSummary of Name Analysis:")
    print(f"Total unique names found: {len(name_frequencies)}")
    print(f"Total name occurrences: {sum(name_frequencies.values())}")
    
    # Separate truly empty names from placeholder names
    truly_empty_names = [(file, name) for file, name in empty_names if not name or name.strip() == ""]
    placeholder_names = [(file, name) for file, name in empty_names if name and name.strip() != "" and name.lower() in ["[vacant]", "n/a"]]
    
    # Empty names (truly empty or just whitespace)
    if truly_empty_names:
        print(f"\nTruly empty names found: {len(truly_empty_names)}")
        for i, (file_name, name) in enumerate(truly_empty_names[:max_examples]):
            print(f"  {file_name}: \"{name}\"")
        if len(truly_empty_names) > max_examples:
            print(f"  ... and {len(truly_empty_names) - max_examples} more")
    
    # Placeholder names
    if placeholder_names:
        print(f"\nPlaceholder names found (names like \"[vacant]\" or \"n/a\"): {len(placeholder_names)}")
        for i, (file_name, name) in enumerate(placeholder_names[:max_examples]):
            print(f"  {file_name}: \"{name}\"")
        if len(placeholder_names) > max_examples:
            print(f"  ... and {len(placeholder_names) - max_examples} more")
    
    # Short names
    if short_names:
        print(f"\nShort names (≤ {short_name_threshold} characters): {len(short_names)}")
        for i, (file_name, name) in enumerate(short_names[:max_examples]):
            print(f"  {file_name}: \"{name}\"")
        if len(short_names) > max_examples:
            print(f"  ... and {len(short_names) - max_examples} more")
    
    # Single-word names
    if single_word_names:
        print(f"\nSingle-word names: {len(single_word_names)}")
        for i, (file_name, name) in enumerate(single_word_names[:max_examples]):
            print(f"  {file_name}: \"{name}\"")
        if len(single_word_names) > max_examples:
            print(f"  ... and {len(single_word_names) - max_examples} more")
    
    # Non-alphabetic characters
    if non_alpha_names:
        print(f"\nNames with non-alphabetic characters (excluding spaces, hyphens, apostrophes, periods, commas, parentheses): {len(non_alpha_names)}")
        for i, (file_name, name) in enumerate(non_alpha_names[:max_examples]):
            print(f"  {file_name}: \"{name}\"")
        if len(non_alpha_names) > max_examples:
            print(f"  ... and {len(non_alpha_names) - max_examples} more")
        
        print("\nSpecial characters found:")
        for char, count in sorted(special_characters.items(), key=lambda x: x[1], reverse=True):
            print(f"  '{char}': {count} occurrences")
    
    # Long word names
    if long_word_names:
        print(f"\nNames with extremely long words (> {long_word_threshold} characters, hyphenated words analyzed by parts): {len(long_word_names)}")
        for i, (file_name, name, word) in enumerate(long_word_names[:max_examples]):
            print(f"  {file_name}: \"{name}\" (long word: \"{word}\")")
        if len(long_word_names) > max_examples:
            print(f"  ... and {len(long_word_names) - max_examples} more")
    
    # Long names (many words)
    if long_names:
        print(f"\nLong names (> {long_name_threshold} words): {len(long_names)}")
        for i, (file_name, name) in enumerate(long_names[:max_examples]):
            print(f"  {file_name}: \"{name}\"")
        if len(long_names) > max_examples:
            print(f"  ... and {len(long_names) - max_examples} more")
    
    # Files with duplicate names (excluding placeholders)
    if duplicate_names:
        print(f"\nFiles with duplicate names: {len(duplicate_names)}")
        # Create a list of tuples (file_name, duplicates, max_non_placeholder_count) for sorting
        sorted_duplicates = []
        for file_name, duplicates in duplicate_names.items():
            # Filter out placeholders
            non_placeholder_dups = {name: count for name, count in duplicates.items() 
                                   if name.lower() not in ["[vacant]", "n/a"]}
            
            # Get max count of non-placeholder duplicates
            max_non_placeholder_count = max(non_placeholder_dups.values()) if non_placeholder_dups else 0
            sorted_duplicates.append((file_name, duplicates, max_non_placeholder_count))
        
        # Sort by the maximum count of non-placeholder duplicates in each file (highest first)
        sorted_duplicates.sort(key=lambda x: x[2], reverse=True)
        
        for file_name, duplicates, _ in sorted_duplicates[:max_examples]:
            print(f"  {file_name}:")
            # Sort duplicates by count (highest first)
            sorted_dups = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)
            for name, count in sorted_dups[:3]:
                print(f"    \"{name}\": {count} occurrences")
            if len(duplicates) > 3:
                print(f"    ... and {len(duplicates) - 3} more duplicates")
        if len(duplicate_names) > max_examples:
            print(f"  ... and {len(duplicate_names) - max_examples} more files with duplicates")
    
    # Files with most placeholder names
    print("\nFiles with most placeholder names ([vacant] or n/a):")
    placeholder_counts = {}
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                names_with_roles = extract_names(data)
                names = [name for name, _ in names_with_roles]
                
                # Count placeholder names
                placeholder_count = sum(1 for name in names if name.lower() in ["[vacant]", "n/a"])
                
                if placeholder_count > 0:
                    placeholder_counts[json_file.name] = placeholder_count
                    
            except json.JSONDecodeError:
                pass
    
    # Display top files with most placeholders
    display_count = min(10, len(placeholder_counts))
    if placeholder_counts:
        for file_name, count in sorted(placeholder_counts.items(), key=lambda x: x[1], reverse=True)[:display_count]:
            print(f"  {file_name}: {count} placeholders")
    else:
        print("  No placeholder names found in any file")
    
    # Most frequent names across all files
    print("\nMost frequent names across all files:")
    for name, count in name_frequencies.most_common(max_examples):
        print(f"  \"{name}\": {count} occurrences")

def extract_names(data, role="unknown"):
    """
    Extract people's names from the JSON data based on the file schema with role information.
    
    This function is now only used by analyze_names_in_json_files() since analyze_member_staff_overlap()
    has been updated to only process house/senate committee files directly.
    
    Different file types have different schema for storing people's names:
    - departments.py: "member_name" fields
    - judiciary.py: "name" fields inside "court_personnel" or "circuit_personnel" 
    - international_organizations.py: "name" fields inside "organization_personnel" or "department_personnel"
    - house_senate_committees.py: "member_name" and "staff_name" fields in subcommittees
    
    Args:
        data: The JSON data to extract names from
        role: The role of the person (member, staff, or unknown)
    
    Returns:
        List of tuples of (name, role)
    """
    names = []
    
    # List of country names and common non-person entries to filter out
    country_names = ["Albania", "Algeria", "Angola", "Argentina", "Armenia", "Australia", "Austria", 
                     "Azerbaijan", "Afghanistan", "Andorra", "Bahamas", "Bahrain", "Bangladesh", "Belarus", 
                     "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia", "Brazil", "Brunei",
                     "Bulgaria", "Burkina Faso", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", 
                     "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia", 
                     "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic",
                     "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia", 
                     "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", 
                     "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", 
                     "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Ivory Coast",
                     "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Korea", "Kosovo",
                     "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Lithuania", 
                     "Luxembourg", "Macedonia", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", 
                     "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", 
                     "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", 
                     "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "Norway", 
                     "Oman", "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", 
                     "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda", "Samoa", 
                     "San Marino", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", 
                     "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan",
                     "Spain", "Sri Lanka", "St. Kitts", "St. Lucia", "St. Vincent", "Sudan", "Suriname", "Swaziland", 
                     "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste",
                     "Togo", "Tonga", "Trinidad", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", 
                     "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu",
                     "Vatican City", "Venezuela", "Vietnam", "Yemen", "Yugoslavia", "Zambia", "Zimbabwe", 
                     "Office", "Member", "Observer"]
    
    if isinstance(data, dict):
        current_role = role  # Default to passed-in role

        # Try to determine role from structure
        if "member_role" in data:
            if any(staff_term in str(data.get("member_role", "")).lower() for staff_term in 
                  ["staff", "counsel", "director", "secretary", "clerk", "assistant", "aide", "advisor"]):
                current_role = "staff"
            else:
                current_role = "member"
        
        # Department files use member_name for people
        if "member_name" in data and data["member_name"] is not None:
            name = data["member_name"]
            if name not in country_names and not name.startswith("Office") and name != "Member":
                names.append((name, current_role))
        
        # Files with personnel lists (courts, organizations)
        for field in ["court_personnel", "circuit_personnel", "organization_personnel", "department_personnel", "office_personnel"]:
            if field in data and isinstance(data[field], list):
                # These are typically staff
                staff_role = "staff"
                for person in data[field]:
                    if isinstance(person, dict) and "name" in person and person["name"] is not None:
                        name = person["name"]
                        # Skip country names and non-person entries
                        if name not in country_names and not name.startswith("Office"):
                            # Check if role is specified in the person data
                            person_role = staff_role
                            if "role" in person:
                                role_str = str(person.get("role", "")).lower()
                                if any(member_term in role_str for member_term in 
                                      ["chair", "member", "ranking", "vice", "president", "representative", "senator"]):
                                    person_role = "member"
                            names.append((name, person_role))
        
        # Cabinet and executive office structures
        if "cabinet" in data and isinstance(data["cabinet"], list):
            for member in data["cabinet"]:
                if isinstance(member, dict) and "member_name" in member and member["member_name"] is not None:
                    name = member["member_name"]
                    if name not in country_names and not name.startswith("Office"):
                        # Cabinet members are typically members, not staff
                        names.append((name, "member"))
        
        # House and Senate committees - members are in members list, staff in staff list
        if "members" in data and isinstance(data["members"], list):
            for member in data["members"]:
                if isinstance(member, dict) and "name" in member and member["name"] is not None:
                    name = member["name"]
                    if name not in country_names and not name.startswith("Office"):
                        names.append((name, "member"))
        
        if "staff" in data and isinstance(data["staff"], list):
            for staff in data["staff"]:
                if isinstance(staff, dict) and "name" in staff and staff["name"] is not None:
                    name = staff["name"]
                    if name not in country_names and not name.startswith("Office"):
                        names.append((name, "staff"))
        
        # Process nested elements
        for key, value in data.items():
            # Skip organization_name, department_name, court_name, etc. to avoid analyzing non-person names
            if key not in ["organization_name", "department_name", "court_name", "circuit_name", "office_name", 
                          "officers", "state", "role", "member_role"] and (
                isinstance(value, dict) or isinstance(value, list)):
                # Pass down role information for nested elements
                nested_role = current_role
                # Check if we're entering a specifically role-defined section
                if key == "staff":
                    nested_role = "staff"
                elif key == "members":
                    nested_role = "member"
                names.extend(extract_names(value, nested_role))
    
    elif isinstance(data, list):
        # Process each item in the list
        for item in data:
            names.extend(extract_names(item, role))
    
    return names

def analyze_member_staff_overlap(json_files):
    """
    Analyzes if people appear as both members and staff across House and Senate committee files.
    Only analyzes files from house_senate_committees.py schema which have explicit member/staff distinctions.
    Ignores member/staff distinctions in departments, judiciary, and international organizations.
    
    Args:
        json_files: List of JSON file paths to analyze
    """
    # Dictionary to keep track of each person's roles and the files they appear in
    # {name: {"member": [files], "staff": [files], "unknown": [files]}}
    people_roles = {}
    
    # Only process House and Senate committee files which have explicit member/staff distinction
    house_senate_committee_files = []
    
    # Classify files based on their type
    for json_file in json_files:
        file_name = json_file.name
        if "HOUSECOMMITTEES" in file_name or "SENATECOMMITTEES" in file_name:
            house_senate_committee_files.append(json_file)
    
    # Process committee files (these have explicit member/staff distinction)
    for json_file in house_senate_committee_files:
        file_name = json_file.name
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                
                # Process committee files looking for members and staff
                if "committees" in data:
                    for committee in data["committees"]:
                        # Process each subcommittee (including main committee which is stored as a subcommittee)
                        if "subcommittees" in committee:
                            for subcommittee in committee["subcommittees"]:
                                if "subcommittee_members" in subcommittee:
                                    for person in subcommittee["subcommittee_members"]:
                                        # Check if it's a member or staff based on field names
                                        if "member_name" in person and person["member_name"]:
                                            name = person["member_name"]
                                            role = "member"
                                        elif "staff_name" in person and person["staff_name"]:
                                            name = person["staff_name"]
                                            role = "staff"
                                        else:
                                            continue
                                            
                                        # Skip placeholders and empty names
                                        if not name or name.strip() == "" or name.lower() in ["[vacant]", "n/a"]:
                                            continue
                                        
                                        # Initialize entry for this person if it doesn't exist
                                        if name not in people_roles:
                                            people_roles[name] = {"member": [], "staff": [], "unknown": []}
                                        
                                        # Add this file to the appropriate role list
                                        if file_name not in people_roles[name][role]:
                                            people_roles[name][role].append(file_name)
            except json.JSONDecodeError:
                print(f"Error: Could not parse JSON file {file_name}")
                continue
            except KeyError as e:
                print(f"Error: Missing expected key in {file_name}: {e}")
                continue
    
    # Find people who appear as both member and staff
    dual_role_people = {}
    for name, roles in people_roles.items():
        if roles["member"] and roles["staff"]:
            # Count total occurrences as both member and staff
            member_count = len(roles["member"])
            staff_count = len(roles["staff"])
            total_dual_roles = member_count + staff_count
            
            dual_role_people[name] = {
                "member_files": roles["member"],
                "staff_files": roles["staff"],
                "member_count": member_count,
                "staff_count": staff_count,
                "total_dual_roles": total_dual_roles
            }
    
    # Print analysis results
    print(f"\nTotal people found who appear as both member and staff: {len(dual_role_people)}")
    print(f"Total unique people found in all House/Senate committee files: {len(people_roles)}")
    percentage = (len(dual_role_people) / len(people_roles)) * 100 if people_roles else 0
    print(f"Percentage of people with dual roles: {percentage:.2f}%")
    print(f"Number of House/Senate committee files analyzed: {len(house_senate_committee_files)}")
    print("\nNote: Only analyzing House/Senate committee files for member/staff overlap")
    print("Other file types (departments, judiciary, international organizations) are not checked")
    print("as requested, since those don't have the same member/staff distinction.")
    
    # Show top people with most dual role occurrences
    max_examples = 10
    print("\nTop people appearing as both member and staff (sorted by total occurrences):")
    
    sorted_dual_roles = sorted(
        dual_role_people.items(), 
        key=lambda x: x[1]["total_dual_roles"], 
        reverse=True
    )
    
    for i, (name, data) in enumerate(sorted_dual_roles[:max_examples]):
        print(f"  {i+1}. \"{name}\":")
        print(f"     - Member in {data['member_count']} files")
        print(f"     - Staff in {data['staff_count']} files")
        
        # Show sample files (up to 3) for each role
        if data['member_files']:
            print(f"     - Member example files: {', '.join(data['member_files'][:3])}")
            if len(data['member_files']) > 3:
                print(f"       and {len(data['member_files']) - 3} more files")
                
        if data['staff_files']:
            print(f"     - Staff example files: {', '.join(data['staff_files'][:3])}")
            if len(data['staff_files']) > 3:
                print(f"       and {len(data['staff_files']) - 3} more files")
    
    if len(sorted_dual_roles) > max_examples:
        print(f"  ... and {len(sorted_dual_roles) - max_examples} more people with dual roles")
    
    # Count dual roles by file
    files_with_dual_roles = {}
    for name, data in dual_role_people.items():
        all_files = set(data["member_files"] + data["staff_files"])
        for file_name in all_files:
            if file_name not in files_with_dual_roles:
                files_with_dual_roles[file_name] = []
            files_with_dual_roles[file_name].append(name)
    
    # Show files with most dual-role people
    print("\nFiles with the most people appearing in dual roles:")
    sorted_files = sorted(
        files_with_dual_roles.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    for file_name, names in sorted_files[:max_examples]:
        print(f"  {file_name}: {len(names)} people with dual roles")
        
    if len(sorted_files) > max_examples:
        print(f"  ... and {len(sorted_files) - max_examples} more files with dual-role people")

if __name__ == "__main__":
    # Check if congress number is provided via command line
    if len(sys.argv) > 1:
        congress_number = sys.argv[1]
        analyze_directory_files(congress_number)
    else:
        analyze_directory_files()