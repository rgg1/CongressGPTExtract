import json

def analyze_matching_stats(json_file):
    """
    Analyze matching statistics from the already-processed JSON with bioguide IDs.
    
    Args:
        json_file (str): Path to the JSON file with bioguide IDs.

    Returns:
        dict: A dictionary containing the statistics for committee and subcommittee members and staff.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    stats = {
        'committee_members': {'total': 0, 'matched': 0, 'multi_match': 0},
        'committee_staff': {'total': 0, 'matched': 0, 'multi_match': 0},
        'subcommittee_members': {'total': 0, 'matched': 0, 'multi_match': 0},
        'subcommittee_staff': {'total': 0, 'matched': 0, 'multi_match': 0}
    }
    
    for committee in data['committees']:
        # Committee members
        if 'members' in committee:
            for member in committee['members']:
                if member.get('member_name') and member.get('member_name').lower() != 'vacant':
                    stats['committee_members']['total'] += 1
                    if 'bioguide_id' in member:
                        stats['committee_members']['matched'] += 1
                        if isinstance(member['bioguide_id'], list):
                            stats['committee_members']['multi_match'] += 1
        
        # Committee staff
        if 'staff' in committee:
            for staff in committee['staff']:
                if staff.get('staff_name') and staff.get('staff_name').lower() != 'vacant':
                    stats['committee_staff']['total'] += 1
                    if 'bioguide_id' in staff:
                        stats['committee_staff']['matched'] += 1
                        if isinstance(staff['bioguide_id'], list):
                            stats['committee_staff']['multi_match'] += 1
        
        # Subcommittees
        if 'subcommittees' in committee:
            for subcommittee in committee['subcommittees']:
                # Subcommittee members
                if 'subcommittee_members' in subcommittee:
                    for member in subcommittee['subcommittee_members']:
                        if member.get('member_name') and member.get('member_name').lower() != 'vacant':
                            stats['subcommittee_members']['total'] += 1
                            if 'bioguide_id' in member:
                                stats['subcommittee_members']['matched'] += 1
                                if isinstance(member['bioguide_id'], list):
                                    stats['subcommittee_members']['multi_match'] += 1
                        
                
                # Subcommittee staff
                        if staff.get('staff_name') and staff.get('staff_name').lower() != 'vacant':
                            stats['subcommittee_staff']['total'] += 1
                            if 'bioguide_id' in staff:
                                stats['subcommittee_staff']['matched'] += 1
                                if isinstance(staff['bioguide_id'], list):
                                    stats['subcommittee_staff']['multi_match'] += 1
    
    return stats

def print_stats(stats):
    """Print formatted statistics."""
    print("\nBioGuide ID Matching Statistics")
    print("=" * 50)
    
    # Members stats
    total_members = stats['committee_members']['total'] + stats['subcommittee_members']['total']
    matched_members = stats['committee_members']['matched'] + stats['subcommittee_members']['matched']
    print(f"\nMEMBERS:")
    print(f"Committee Members:")
    print(f"  Total: {stats['committee_members']['total']}")
    print(f"  Matched: {stats['committee_members']['matched']} ")
    
    print(f"\nSubcommittee Members:")
    print(f"  Total: {stats['subcommittee_members']['total']}")
    print(f"  Matched: {stats['subcommittee_members']['matched']} " +
          f"({(stats['subcommittee_members']['matched'] / stats['subcommittee_members']['total'] * 100):.1f}%)")
    
    print(f"\nAll Members Combined:")
    print(f"  Total: {total_members}")
    print(f"  Matched: {matched_members} ({(matched_members / total_members * 100):.1f}%)")
    
    # Staff stats
    total_staff = stats['committee_staff']['total'] + stats['subcommittee_staff']['total']
    matched_staff = stats['committee_staff']['matched'] + stats['subcommittee_staff']['matched']
    print(f"\nSTAFF:")
    print(f"Committee Staff:")
    print(f"  Total: {stats['committee_staff']['total']}")
    print(f"  Matched: {stats['committee_staff']['matched']} " +
          f"({(stats['committee_staff']['matched'] / stats['committee_staff']['total'] * 100):.1f}%)")
    
    print(f"\nSubcommittee Staff:")
    print(f"  Total: {stats['subcommittee_staff']['total']}")
    print(f"  Matched: {stats['subcommittee_staff']['matched']} " +
          f"({(stats['subcommittee_staff']['matched'] / stats['subcommittee_staff']['total'] * 100):.1f}%)")
    
    print(f"\nAll Staff Combined:")
    print(f"  Total: {total_staff}")
    print(f"  Matched: {matched_staff} ({(matched_staff / total_staff * 100):.1f}%)")
    
    # Multiple matches stats
    total_multi = (stats['committee_members']['multi_match'] + 
                  stats['committee_staff']['multi_match'] +
                  stats['subcommittee_members']['multi_match'] + 
                  stats['subcommittee_staff']['multi_match'])
    
    print(f"\nMULTIPLE MATCHES:")
    print(f"Total instances: {total_multi}")
    print(f"  Committee Members: {stats['committee_members']['multi_match']}")
    print(f"  Committee Staff: {stats['committee_staff']['multi_match']}")
    print(f"  Subcommittee Members: {stats['subcommittee_members']['multi_match']}")
    print(f"  Subcommittee Staff: {stats['subcommittee_staff']['multi_match']}")

def main():
    # Use the output file from our previous script
    json_files = ["CDIR-2022-10-26-HOUSECOMMITTEES.txt_output_with_bioguide.json"]
    
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