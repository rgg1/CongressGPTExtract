import os
import json
import openai
from dotenv import load_dotenv
from pydantic import BaseModel

class Member(BaseModel):
    member_name: str
    member_role: str

class Department(BaseModel):
    department_name: str
    department_members: list[Member]

class Cabinet(BaseModel):
    cabinet_members: list[Member]

class ExecutiveOfficeOfPresident(BaseModel):
    office_name: str
    office_members: list[Member]

class departments_json_schema(BaseModel):
    cabinet: list[Member]
    executive_office_of_president: list[ExecutiveOfficeOfPresident]
    departments: list[Department]

def extract_departments_info(text_chunk, client):
    """
    Uses OpenAI's API to extract department/cabinet/office of the president, member names, and roles from the given text.
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
                    Extract cabinet, executive office, department, and member information from this text into JSON format.
                    Be thorough in extracting all relevant information (don't miss any names). Process in this order:

                    1. CABINET SECTION (if present)
                    - Process the explicit Cabinet listing first
                    - Extract each position and corresponding name
                    - Include acting/interim designations if present

                    2. EXECUTIVE OFFICE OF THE PRESIDENT (if present)
                    - Process all offices and positions under the Executive Office section
                    - Process all staff hierarchically within each office

                    3. DEPARTMENTS
                    For each department:
                    - Find the department name (marked in ALL CAPS with address/phone usually)
                    - Process ALL personnel hierarchically until the next department appears:
                    * Department head (Secretary/Director level)
                    * Deputy/Assistant/Under Secretary level
                    * Office heads and their staff
                    * Bureau heads and their staff
                    * Division heads and their staff
                    * ALL other named positions

                    PERSONNEL PROCESSING INSTRUCTIONS:
                    - Look for major organizational sections marked by ALL CAPS headers
                    - Process roles hierarchically:
                    * Secretary/Director level
                    * Deputy/Assistant/Under level
                    * Office/Bureau/Division heads
                    * Staff positions
                    * Any other positions
                    - Look for office-specific sections with additional staff
                    - Process personnel across page breaks

                    For each entry capture:
                    - Full name
                    - Complete position title/role (use 'N/A' if none listed)

                    Important details:
                    - Process EVERY name that appears in the text
                    - Watch for acting/interim designations
                    - Process continuation of entries across pages
                    - Fully check each line of text as some lines have multiple names, and some names/roles are split across lines
                    - Keep hierarchical structure in mind when grouping
                    - Look for additional personnel in footnotes/supplements

                    ENSURE EVERY NAME IN THE TEXT IS INCLUDED IN THE OUTPUT.

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
                        "schema": departments_json_schema.model_json_schema()
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

def chunk_departments_text(text, max_chunk_size=15000):
    chunks = []
    lines = text.split('\n')
    original_char_count = len(text)
    
    def is_organizational_header(line):
        """Check if line appears to be an organizational header"""
        line = line.strip()
        if not line:
            return False
            
        # Major organization indicators
        indicators = [
            'DEPARTMENT OF',
            'OFFICE OF',
            'BUREAU OF',
            'THE CABINET',
            'EXECUTIVE OFFICE',
            'UNDER SECRETARY',
            'ASSISTANT SECRETARY',
            'DIVISION OF'
        ]
        
        # Check if line is all caps and either:
        # 1. Contains one of our indicators
        # 2. Is followed by an address/phone line
        next_line = next((line for line in lines[i+1:] if line.strip()), "")  # Get next non-empty line
        is_header = (line.isupper() and 
                    (any(ind in line for ind in indicators) or
                     (i < len(lines)-1 and 
                      ('phone' in next_line.lower() or
                       'street' in next_line.lower() or
                       'avenue' in next_line.lower()))))
                       
        return is_header
    
    def find_next_header(start_idx):
        """Find the index of the next organizational header"""
        for i in range(start_idx + 1, len(lines)):
            if is_organizational_header(lines[i]):
                return i
        return len(lines)
    
    def split_oversized_text(text, max_size):
        """Split oversized text into smaller chunks"""
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
    
    # Find first content
    start_idx = 0
    for i, line in enumerate(lines):
        if is_organizational_header(line):
            start_idx = i
            break
    
    # Store skipped content for verification
    skipped_content = '\n'.join(lines[:start_idx])
    print(f"Skipped initial content ({len(skipped_content)} chars):")
    print(skipped_content)
    
    # Get organizational units
    organizational_units = []
    current_start = start_idx
    while current_start < len(lines):
        next_section_start = find_next_header(current_start)
        if next_section_start == current_start:
            next_section_start = find_next_header(current_start + 1)
        section_content = '\n'.join(lines[current_start:next_section_start])
        if section_content.strip():
            organizational_units.append(section_content)
        current_start = next_section_start
    
    print(f"\nFound {len(organizational_units)} organizational units")
    
    # Combine units into chunks
    current_chunk = ""
    for unit in organizational_units:
        # If a unit is longer than 2 * max_chunk_size, split it
        if len(unit) > 2 * max_chunk_size:
            # If there's an existing chunk, add it first
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Split the oversized unit text into smaller pieces
            split_chunks = split_oversized_text(unit, 2 * max_chunk_size)
            chunks.extend(split_chunks)
            print(f"Warning: Split oversized unit of size {len(unit)} into {len(split_chunks)} chunks")
            continue

        # If this single unit is larger than max_size, we have to keep it together
        if len(unit) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            chunks.append(unit)
            print(f"Warning: Single unit of size {len(unit)} exceeds max_chunk_size")
            continue
            
        # If adding this unit would exceed max size
        if len(current_chunk) + len(unit) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = unit
        else:
            if current_chunk:
                current_chunk += "\n" + unit
            else:
                current_chunk = unit
    
    if current_chunk:
        chunks.append(current_chunk)

    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i} size: {len(chunk)} chars")
    
    return chunks

def process_departments_file(file_name, input_dir, output_dir, client):
    # Read file content
    file_path = os.path.join(input_dir, file_name)
    with open(file_path, 'r') as file:
        content = file.read()
    print(f"File loaded. Size: {len(content)} characters")

    print("Splitting content into chunks...")
    chunks = chunk_departments_text(content)
    print(f"Split into {len(chunks)} chunks")

    # Initialize structure with all required keys
    all_data = {
        "cabinet": [],
        "executive_office_of_president": [],
        "departments": []
    }

    # Process each chunk
    for chunk_num, chunk in enumerate(chunks, 1):
        print(f"\nProcessing chunk {chunk_num}/{len(chunks)}")
        try:
            # Extract information in JSON format
            chunk_info = extract_departments_info(chunk, client)
            try:
                # Parse the JSON response
                chunk_data = json.loads(chunk_info)
                
                # Merge data from this chunk
                if "cabinet" in chunk_data:
                    all_data["cabinet"].extend(chunk_data["cabinet"])
                if "executive_office_of_president" in chunk_data:
                    all_data["executive_office_of_president"].extend(chunk_data["executive_office_of_president"])
                if "departments" in chunk_data:
                    all_data["departments"].extend(chunk_data["departments"])
                
                print(f"Successfully processed chunk {chunk_num}")
                
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in chunk {chunk_num}: {str(e)}")
                # Save the problematic chunk
                error_file_path = os.path.join(output_dir, f'{file_name}_chunk{chunk_num}_error.txt')
                with open(error_file_path, 'w') as error_file:
                    error_file.write(chunk_info)
                print(f"Problematic chunk saved to {error_file_path}")
                continue
                
        except Exception as e:
            print(f"Error processing chunk {chunk_num}: {str(e)}")
            continue

    # Save the combined results
    json_file_path = os.path.join(output_dir, f'{file_name}_output.json')
    os.makedirs(output_dir, exist_ok=True)
    with open(json_file_path, 'w') as json_file:
        json.dump(all_data, json_file, indent=2)
    print(f"\nCombined results saved to {json_file_path}")

def process_all_departments_files(congress_number, client, base_directory):
   """
   Process all DEPARTMENTS files for a given Congress number.

    Args:
        congress_number: int
            Congress number to process
   """
   print(f"Processing all DEPARTMENTS files for {congress_number}th Congress...")

   input_directory = f'{base_directory}/congressional_directory_files/congress_{congress_number}/txt'
   output_directory = f'{base_directory}/outputs/{congress_number}'

   for filename in os.listdir(input_directory):
       if 'DEPARTMENTS' in filename and filename.endswith('.txt'):
           print(f"Processing {filename}...")
           process_departments_file(filename, input_directory, output_directory, client)

if __name__ == "__main__":
    load_dotenv()

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    print("Processing all departments files from 117th congress...")
    process_all_departments_files(117)
