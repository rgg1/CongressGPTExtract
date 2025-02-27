import os
import json
import openai
from dotenv import load_dotenv
from pydantic import BaseModel

class Personnel(BaseModel):
    name: str
    role: str

class Department(BaseModel):
    department_name: str
    department_personnel: list[Personnel]

class Organization(BaseModel):
    organization_name: str
    organization_personnel: list[Personnel]
    departments: list[Department] = [] # Some organizations won't have departments

class organizations_json_schema(BaseModel):
    organizations: list[Organization]

def extract_international_organizations_info(text_chunk, client):
    """
    Uses OpenAI's API to extract international organizations, departments, and personnel information from the given text.
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
                    Extract international organizations, their departments, and personnel information from this text into JSON format. Be thorough in extracting all relevant information (don't miss any names). For each organization:

                    1. Find the main organization name (typically in ALL CAPS)

                    2. IMPORTANT: First process the main organization personnel
                    - Create a department with the same name as the organization
                    - Include all personnel listed at the start of the organization section

                    3. Then process any departments/sub-organizations
                    - Look for sections that indicate different offices, centers, or divisions
                    - Process regional offices as departments
                    - Include representative offices and specialized agencies
                    
                    PERSONNEL PROCESSING INSTRUCTIONS:
                    - Look for sections with titles like "OFFICERS", "MANAGEMENT", "BOARD OF DIRECTORS", etc.
                    - Process ALL personnel hierarchically:
                    * Executive level (Secretary-General, President, Director)
                    * Deputy level
                    * Department heads
                    * Representatives and delegates
                    * Professional staff
                    - Pay attention to indented listings which indicate reporting relationships
                    - Look for personnel listings in location-specific sections
                    - Process member country representatives as personnel
                    - Watch for personnel sections that continue across multiple pages

                    For personnel entries:
                    * Process both titles and names when separated by periods, dashes, or other delimiters
                    * Look for multiple personnel entries per line
                    * Check for entries where additional information appears on subsequent lines

                    For each organization/department, record:
                    - Personnel names and their roles (use exact role if listed, 'Member' if no explicit role)
                    - When processing member country sections:
                    * Include country representatives as personnel
                    * Use country name + role (e.g., "Representative from France") if specific role not given
                    * Use 'N/A' for role if neither specific role nor country role is given

                    Important details:
                    - Include EVERY name that appears in the text in some organization/department
                    - Process ALL sections thoroughly - headquarters, regional offices, specialized bodies
                    - Watch for:
                    * Multiple roles for same person (list them all in one string for that one role)
                    * Acting or interim roles (include this in role description)
                    * Alternate representatives or deputies
                    * Member country delegations
                    * Board members and alternates
                    * Regional representatives
                    - Don't miss personnel listed in:
                    * Contact information sections
                    * Regional office listings
                    * Member country sections
                    * Board/Council member listings
                    * Representative/delegate sections

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
                        "schema": organizations_json_schema.model_json_schema()
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

def chunk_international_organizations_text(text, max_chunk_size=15000):
    chunks = []
    organizations = []  # Initialize the organizations list
    lines = text.split('\n')
    
    def is_organization_header(line, prev_line="", next_line=""):
        """Check if line appears to be a main organization header"""
        line = line.strip()
        if not line or line.startswith('[Page') or line.startswith('[[Page'):
            return False
            
        # Common sub-sections that should not be treated as new organizations
        exclusions = [
            'HEADQUARTERS', 'MEMBER STATES', 'BOARD OF DIRECTORS',
            'EXECUTIVE DIRECTORS', 'OFFICERS', 'STAFF', 'MANAGEMENT',
            'COMMISSIONERS', 'PERMANENT MISSIONS', 'DUTY STATIONS',
            'REGIONAL OFFICES', 'FIELD OFFICES', 'CENTERS', 'FUNDS AND PROGRAMS'
        ]
        if any(excl in line for excl in exclusions):
            return False

        is_caps = line.isupper() and len(line) > 10
        
        # Check for organization indicators
        indicators = [
            'ORGANIZATION', 'AGENCY', 'COMMISSION', 'COMMITTEE',
            'BANK', 'FUND', 'PROGRAMME', 'COUNCIL', 'UNION',
            'INSTITUTE', 'ASSOCIATION', 'SECRETARIAT', 'BOARD',
            'NATIONS', 'OFFICE', 'DEVELOPMENT', 'AUTHORITY'
        ]
        
        has_indicator = any(ind in line for ind in indicators)
        
        # Check if followed by contact/location info
        has_contact = any(ind in next_line.lower() for ind in [
            'phone', 'address', 'fax', 'avenue', 'street',
            'headquarters', 'p.o. box', 'http', 'www'
        ])
        
        # Avoid splitting in the middle of a section
        is_continuation = prev_line.strip() and prev_line.strip()[-1] in ',:;'
        
        return is_caps and (has_indicator or has_contact) and not is_continuation

    def find_organization_end(start_idx):
        """Find where the current organization section ends"""
        depth = 0
        i = start_idx
        
        while i < len(lines):
            # Check if next line starts a new main organization
            if i > start_idx and is_organization_header(
                lines[i],
                lines[i-1] if i > 0 else "",
                lines[i+1] if i+1 < len(lines) else ""
            ):
                # Look back for last non-empty line
                while i > start_idx and not lines[i-1].strip():
                    i -= 1
                return i
                
            # Track nested depth for sub-sections
            line = lines[i].strip()
            if line and not line.startswith('['):
                if line.endswith(':'):
                    depth += 1
                elif depth > 0 and not any(c.isspace() for c in line[:4]):
                    depth -= 1
            
            i += 1
            
        return len(lines)

    # Process text into organizations
    current_start = 0
    while current_start < len(lines):
        if is_organization_header(
            lines[current_start],
            lines[current_start-1] if current_start > 0 else "",
            lines[current_start+1] if current_start+1 < len(lines) else ""
        ):
            org_end = find_organization_end(current_start)
            org_content = '\n'.join(lines[current_start:org_end])
            if org_content.strip():
                organizations.append(org_content)
            current_start = org_end
        else:
            current_start += 1

    # Combine organizations into chunks while respecting max size
    current_chunk = ""
    for org in organizations:
        if len(org) > 2 * max_chunk_size:
            # If there's an existing chunk, add it first
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Split the oversized organization text into smaller pieces
            org_lines = org.split('\n')
            temp_chunk = ""
            for line in org_lines:
                if len(temp_chunk) + len(line) > 2 * max_chunk_size:
                    chunks.append(temp_chunk)
                    temp_chunk = line + '\n'
                else:
                    temp_chunk += line + '\n'
            if temp_chunk:
                chunks.append(temp_chunk)
            continue

        # If single organization exceeds max size, keep it as its own chunk
        if len(org) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            chunks.append(org)
            continue
            
        # If adding organization would exceed max size
        if len(current_chunk) + len(org) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = org
        else:
            if current_chunk:
                current_chunk += "\n\n" + org
            else:
                current_chunk = org
                
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def process_international_organizations_file(file_name, input_dir, output_dir, client):
    # Read file content
    file_path = os.path.join(input_dir, file_name)
    with open(file_path, 'r') as file:
        content = file.read()
        print(f"File loaded. Size: {len(content)} characters")
    
    print("Splitting content into chunks...")
    chunks = chunk_international_organizations_text(content)
    print(f"Split into {len(chunks)} chunks")

    all_organizations = {"organizations": []}

    # Process each chunk
    for chunk_num, chunk in enumerate(chunks, 1):
        print(f"\nProcessing chunk {chunk_num}/{len(chunks)}")
        try:
            # Extract international organizations information in JSON format
            organizations_info = extract_international_organizations_info(chunk, client)
            
            try:
                # Parse the JSON response
                organizations_data = json.loads(organizations_info)
                
                # Merge organizations from this chunk
                if "organizations" in organizations_data:
                    all_organizations["organizations"].extend(organizations_data["organizations"])
                
                print(f"Successfully processed chunk {chunk_num}")
                
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in chunk {chunk_num}: {str(e)}")
                # Save the problematic chunk
                error_file_path = os.path.join(output_dir, f'{file_name}_chunk{chunk_num}_error.txt')
                with open(error_file_path, 'w') as error_file:
                    error_file.write(organizations_info)
                print(f"Problematic chunk saved to {error_file_path}")
                continue
            
        except Exception as e:
            print(f"Error processing chunk {chunk_num}: {str(e)}")
            continue

    # Save the combined results
    json_file_path = os.path.join(output_dir, f'{file_name}_output.json') # output file name

    os.makedirs(output_dir, exist_ok=True)

    with open(json_file_path, 'w') as json_file:
        json.dump(all_organizations, json_file, indent=2)
        print(f"\nCombined results saved to {json_file_path}")

def process_international_organizations_file_for_congress(congress_number, client, base_directory):
    print(f"Processing international organizations file for Congress {congress_number}...")

    for filename in os.listdir(f'{base_directory}/congressional_directory_files/congress_{congress_number}/txt'):
        if 'INTERNATIONALORGANIZATIONS' in filename:
            process_international_organizations_file(
                filename,
                f'{base_directory}/congressional_directory_files/congress_{congress_number}/txt',
                f'{base_directory}/outputs/{congress_number}',
                client
            )

if __name__ == "__main__":
    load_dotenv()

    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    print("Processing international organizations file...")
    # process_international_organizations_file('CDIR-2022-10-26-INTERNATIONALORGANIZATIONS.txt', 'congressional_directory_files/congress_117/txt', 'outputs/117')
    process_international_organizations_file_for_congress(117)
