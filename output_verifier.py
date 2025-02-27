import os
import json
import re
import statistics
import collections
from pathlib import Path

def analyze_directory_files():
    # Define the directories
    txt_dir = Path("congressional_directory_files/congress_108/txt")
    json_dir = Path("outputs/108")
    
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
                
                # Extract names from the JSON structure
                names = extract_names(data)
                
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
                names = extract_names(data)
                
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

def extract_names(data):
    """
    Extract only people's names from the JSON data based on the file schema.
    Different file types have different schema for storing people's names:
    - departments.py: "member_name" fields
    - judiciary.py: "name" fields inside "court_personnel" or "circuit_personnel" 
    - international_organizations.py: "name" fields inside "organization_personnel" or "department_personnel"
    - etc.
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
        # Department files use member_name for people
        if "member_name" in data and data["member_name"] is not None:
            name = data["member_name"]
            if name not in country_names and not name.startswith("Office") and name != "Member":
                names.append(name)
        
        # Files with personnel lists (courts, organizations)
        for field in ["court_personnel", "circuit_personnel", "organization_personnel", "department_personnel", "office_personnel"]:
            if field in data and isinstance(data[field], list):
                for person in data[field]:
                    if isinstance(person, dict) and "name" in person and person["name"] is not None:
                        name = person["name"]
                        # Skip country names and non-person entries
                        if name not in country_names and not name.startswith("Office"):
                            names.append(name)
        
        # Cabinet and executive office structures
        if "cabinet" in data and isinstance(data["cabinet"], list):
            for member in data["cabinet"]:
                if isinstance(member, dict) and "member_name" in member and member["member_name"] is not None:
                    name = member["member_name"]
                    if name not in country_names and not name.startswith("Office"):
                        names.append(name)
        
        # Process nested elements
        for key, value in data.items():
            # Skip organization_name, department_name, court_name, etc. to avoid analyzing non-person names
            if key not in ["organization_name", "department_name", "court_name", "circuit_name", "office_name", 
                          "officers", "state", "role", "member_role"] and (
                isinstance(value, dict) or isinstance(value, list)):
                names.extend(extract_names(value))
    
    elif isinstance(data, list):
        # Process each item in the list
        for item in data:
            names.extend(extract_names(item))
    
    return names

if __name__ == "__main__":
    analyze_directory_files()