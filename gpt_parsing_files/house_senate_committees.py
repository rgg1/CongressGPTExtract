import os
import json
import openai
from tqdm import tqdm
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Union

# get file paths to senate and house committee files
def get_committee_files(chamber, base_directory):
    chamber_committee_files = {}
    for folder in os.listdir(f'{base_directory}/congressional_directory_files'):
        if folder.startswith('congress'):
            chamber_committee_files[folder] = []
            for file in os.listdir(f'{base_directory}/congressional_directory_files/{folder}/txt'):
                if f"{chamber}COMMITTEES" in file:
                    chamber_committee_files[folder].append(file)
    return chamber_committee_files

def chunk_text(text, min_chunk_size=15000):
    chunks = []
    current_chunk = ""
    lines = text.split('\n')
    
    # Initialize variables
    committee_start_index = 0

    def find_next_nonempty_line(start_idx):
        """Find the next non-empty line starting from start_idx"""
        for i in range(start_idx, len(lines)):
            if lines[i].strip():
                return i
        return len(lines)
        
    def find_prev_nonempty_line(start_idx):
        """Find the previous non-empty line starting from start_idx"""
        for i in range(start_idx, -1, -1):
            if lines[i].strip():
                return i
        return -1

    # Helper function to split oversized text
    def split_oversized_text(text, max_size):
        result_chunks = []
        text_lines = text.split('\n')
        temp_chunk = ""
        
        for line in text_lines:
            if len(temp_chunk) + len(line) > max_size:
                result_chunks.append(temp_chunk)
                temp_chunk = line + '\n'
            else:
                temp_chunk += line + '\n'
                
        if temp_chunk:
            result_chunks.append(temp_chunk)
            
        return result_chunks
    
    # Use tqdm for progress tracking
    for i in tqdm(range(len(lines)), desc="Processing lines"):
        line = lines[i]
        
        # Check if current line contains "phone"
        if "phone" in line.lower():
            # Check if this is actually a continuation of previous phone lines
            is_continuation = False
            prev_nonempty = find_prev_nonempty_line(i-1)
            if prev_nonempty != -1:
                # Look back 3 non-empty lines from there
                for j in range(max(0, prev_nonempty-2), prev_nonempty + 1):
                    if j >= 0 and "phone" in lines[j].lower():
                        is_continuation = True
                        break
            
            if not is_continuation:
                # Found start of new committee
                # Look ahead to find start of NEXT committee
                next_committee_start = -1
                look_ahead = i + 1
                while look_ahead < len(lines):
                    # Find next non-empty line
                    look_ahead = find_next_nonempty_line(look_ahead)
                    if look_ahead >= len(lines):
                        break
                        
                    if "phone" in lines[look_ahead].lower():
                        # Verify it's not a continuation
                        is_next_continuation = False
                        prev_nonempty = find_prev_nonempty_line(look_ahead-1)
                        if prev_nonempty != -1:
                            for k in range(max(0, prev_nonempty-2), prev_nonempty + 1):
                                if k >= 0 and "phone" in lines[k].lower():
                                    is_next_continuation = True
                                    break
                        if not is_next_continuation:
                            next_committee_start = look_ahead - 10  # Back up to committee header
                            break
                    look_ahead += 1
                
                # If we found next committee, get all content up to it
                if next_committee_start != -1:
                    committee_content = '\n'.join(lines[committee_start_index:next_committee_start])
                else:
                    # No next committee found, get rest of content
                    committee_content = '\n'.join(lines[committee_start_index:])

                # Check if committee_content is too large (2 * min_chunk_size)
                if len(committee_content) > 2 * min_chunk_size:
                    # If there's an existing chunk, add it first
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = ""
                    
                    # Split the oversized committee content
                    split_chunks = split_oversized_text(committee_content, 2 * min_chunk_size)
                    chunks.extend(split_chunks)
                
                # If current chunk plus this committee exceeds min size, start new chunk
                elif current_chunk and len(current_chunk + committee_content) >= min_chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = committee_content
                else:
                    # Add to current chunk
                    if current_chunk:
                        current_chunk += '\n' + committee_content
                    else:
                        current_chunk = committee_content
                
                committee_start_index = next_committee_start if next_committee_start != -1 else len(lines)
                i = committee_start_index - 1 if next_committee_start != -1 else len(lines)
    
    # Add any remaining content
    if committee_start_index < len(lines):
        remaining_content = '\n'.join(lines[committee_start_index:])

        # Check if remaining content is too large
        if len(remaining_content) > 2 * min_chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
            split_chunks = split_oversized_text(remaining_content, 2 * min_chunk_size)
            chunks.extend(split_chunks)
        else:
            current_chunk += '\n' + remaining_content
    
    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

class Member(BaseModel):
    member_name: str
    member_role: str
    member_state: str

class Staff(BaseModel):
    staff_name: str
    staff_role: str
    staff_state: str

class Subcommittee(BaseModel):
    subcommittee_name: str
    subcommittee_members: list[Union[Member, Staff]]

class Committee(BaseModel):
    committee_name: str
    subcommittees: list[Subcommittee]

class committees_json_schema(BaseModel):
    committees: list[Committee]

def extract_committee_info(text_chunk, client):
    """
    Uses OpenAI's API to extract committees, subcommittees, staff, member names, and roles from the given text.
    Returns the information in JSON format as specified by the implementation.

    Args:
        text_chunk: str
            Chunk of text to process
    
    Returns:
        response: str
            Extracted information in JSON format
    """
    print(f"Processing chunk of size: {len(text_chunk)} characters")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                    Extract committees, subcommittees, member information, and staff information from this text into JSON format.
                    Be thorough in extracting all relevant information (don't miss any names).
                    For each committee:
                    1. Find the committee name
                    2. IMPORTANT: First process the main committee members and staff (all members and staff listed BEFORE any subcommittee section)
                    - Create a subcommittee with the same name as the committee
                    - Include all members and staff listed at the start of the committee section

                    STAFF PROCESSING INSTRUCTIONS:
                    - Look for major staff sections marked by 'STAFF', 'Majority Staff', 'Minority Staff', or similar headers
                    - Process ALL staff hierarchically - Director level, Deputy level, Professional Staff, Administrative Staff, etc.
                    - Pay special attention to indented staff listings which indicate reporting relationships
                    - Look for staff listings in office-specific sections (e.g., "Clerk's Office:", "Communications:", etc.)
                    - Process ALL contact information sections as they often contain additional staff listings
                    - Watch for staff sections that continue across multiple pages

                    For lines with two-column formats:
                    * Process both the left and right sides of the line
                    * Look for names separated by multiple spaces or tabs
                    * Each side typically ends with a state and period

                    For names that are split across lines with state information:
                    * Check for entries where the state appears indented on the next line
                    * Combine name and state information even when split by line breaks

                    3. Then process any subcommittee section if it exists
                    4. For committees with NO subcommittees, use the committee name as the subcommittee name
                    5. Include everything until the next committee name appears
                    6. After processing main sections, check for:
                    - Additional staff listings at the end of committee sections
                    - Staff listings in footnotes or supplementary sections
                    - Professional staff members listed under special sections


                    For each committee/subcommittee, record:
                    - Members and their roles (Chair, Vice Chair, etc., use 'Member' if no explicit role listed)
                    - States for members (use 'N/A' if no state listed)
                    - Staff (names listed under 'STAFF' sections) and their roles (use 'Staff' if no explicit role listed)
                    - States for staff (use 'N/A' if no state listed)

                    Important details:
                    - Include each name in every committee/subcommittee they appear in
                    - Process BOTH columns when lines are formatted in two columns
                    - Look for multiple names per line (separated by commas, periods, or large spaces)
                    - Check if entries continue on next line
                    - Keep line indentation in mind when grouping information
                    - Remember that the main committee members and staff come BEFORE any subcommittee listings
                    - For two-column layouts, process right column with same care as left column
                    - DON'T FORGET TO INCLUDE THE STAFF, most committees/subcommittees have staff listed under 'STAFF' sections

                    Output the results in the existing JSON structure provided.
                    """,
                },
                {
                    "role": "user",
                    "content": text_chunk
                }
            ],
            response_format={
                'type': 'json_schema',
                'json_schema': 
                    {
                        "name":"_", 
                        "schema": committees_json_schema.model_json_schema()
                    }
            },  
            temperature=0.3,
            # max_tokens=10000,
            timeout=600  # 10 minute timeout per chunk
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during API call: {str(e)}")
        raise

def process_committee_file(file_name, input_dir, output_dir, client):
    # Read file content
    file_path = os.path.join(input_dir, file_name)
    with open(file_path, 'r') as file:
        content = file.read()
        print(f"File loaded. Size: {len(content)} characters")
    
    print("Splitting content into chunks...")
    chunks = chunk_text(content)
    print(f"Split into {len(chunks)} chunks")
    
    all_committees = {"committees": []}
    
    # Process each chunk
    for chunk_num, chunk in enumerate(chunks, 1):
        print(f"\nProcessing chunk {chunk_num}/{len(chunks)}")
        try:
            # Extract committee information in JSON format
            committee_info = extract_committee_info(chunk, client)
            
            try:
                # Parse the JSON response
                chunk_data = json.loads(committee_info)
                
                # Merge committees from this chunk
                if "committees" in chunk_data:
                    all_committees["committees"].extend(chunk_data["committees"])
                
                print(f"Successfully processed chunk {chunk_num}")
                
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in chunk {chunk_num}: {str(e)}")
                # Save the problematic chunk
                error_file_path = os.path.join(output_dir, f'{file_name}_chunk{chunk_num}_error.txt')
                with open(error_file_path, 'w') as error_file:
                    error_file.write(committee_info)
                print(f"Problematic chunk saved to {error_file_path}")
                continue
            
        except Exception as e:
            print(f"Error processing chunk {chunk_num}: {str(e)}")
            continue
    
    # Save the combined results
    json_file_path = os.path.join(output_dir, f'{file_name}_output.json') # output file name

    os.makedirs(output_dir, exist_ok=True)

    with open(json_file_path, 'w') as json_file:
        json.dump(all_committees, json_file, indent=2)
    print(f"\nCombined results saved to {json_file_path}")

def process_committee_files(congress_number, committee_files, client, base_directory):
    """
    Process committee files for a given Congress number and type (Senate or House).
    Extract committee information from each file and save the output in JSON format.

    Args:
        congress_number: int
            Congress number to process
        committee_files: dict
            Dictionary containing committee file names for Senate or House
    """
    # folder to save the output JSON files
    output_dir = f"{base_directory}/outputs/{congress_number}"
    os.makedirs(output_dir, exist_ok=True)

    for file_name in tqdm(committee_files[f'congress_{congress_number}']):
        input_dir = f'{base_directory}/congressional_directory_files/congress_{congress_number}/txt'
        process_committee_file(file_name, input_dir, output_dir, client)

def process_all_committees_for_congress(congress_number, client, base_directory):
    """
    Process all committee files for a given Congress number.
    Extract committee information from each file and save the output in JSON format.

    Args:
        congress_number: int
            Congress number to process
    """
    print(f"Processing all house committee files from {congress_number}th congress...")
    process_committee_files(congress_number, get_committee_files('HOUSE', base_directory), client, base_directory)

    print(f"Processing all senate committee files from {congress_number}th congress...")
    process_committee_files(congress_number, get_committee_files('SENATE', base_directory), client, base_directory)

if __name__ == "__main__":
    load_dotenv()

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # senate_committee_files = get_committee_files('SENATE')
    # house_committee_files = get_committee_files('HOUSE')

    # print("processing all house committee files from 117th congress...")
    # process_committee_files('117', house_committee_files)

    # print("processing all senate committee files from 117th congress...")
    # process_committee_files('117', senate_committee_files)
    process_all_committees_for_congress(117, client)
