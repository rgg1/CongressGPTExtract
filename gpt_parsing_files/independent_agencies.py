"""
Extracts information about independent agencies from the Congressional Directory files.
Uses OpenAI's API to extract agencies, member names, and roles from the given text.
Outputs the information in JSON format as specified by the implementation.
"""

import os
import json
import openai
from tqdm import tqdm
from dotenv import load_dotenv
from pydantic import BaseModel

def chunk_text(text: str, max_chunk_size: int = 15000) -> list[str]:
    """
    Split the text into chunks.

    Args:
        text: The text to split into chunks.
        max_chunk_size: The minimum size of each chunk.

    Returns:
        chunks: A list of text chunks.
    """
    chunks = []
    current_chunk = ""
    lines = text.split("\n")

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

    def split_oversized_text(text, max_size):
        """Helper function to split oversized text into chunks"""
        result_chunks = []
        text_lines = text.split("\n")
        temp_chunk = ""

        for line in text_lines:
            if len(temp_chunk) + len(line) > max_size:
                result_chunks.append(temp_chunk)
                temp_chunk = line + "\n"
            else:
                temp_chunk += line + "\n"

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
            prev_nonempty = find_prev_nonempty_line(i - 1)
            if prev_nonempty != -1:
                # Look back 3 non-empty lines from there
                for j in range(max(0, prev_nonempty - 2), prev_nonempty + 1):
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
                        prev_nonempty = find_prev_nonempty_line(look_ahead - 1)
                        if prev_nonempty != -1:
                            for k in range(
                                max(0, prev_nonempty - 2), prev_nonempty + 1
                            ):
                                if k >= 0 and "phone" in lines[k].lower():
                                    is_next_continuation = True
                                    break
                        if not is_next_continuation:
                            next_committee_start = (
                                look_ahead - 10
                            )  # Back up to committee header
                            break
                    look_ahead += 1

                # If we found next committee, get all content up to it
                if next_committee_start != -1:
                    committee_content = "\n".join(
                        lines[committee_start_index:next_committee_start]
                    )
                else:
                    # No next committee found, get rest of content
                    committee_content = "\n".join(lines[committee_start_index:])

                # Check if committee_content is too large (2 * max_chunk_size)
                if len(committee_content) > 2 * max_chunk_size:
                    # If there's an existing chunk, add it first
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = ""

                    # Split the oversized committee content
                    split_chunks = split_oversized_text(
                        committee_content, 2 * max_chunk_size
                    )
                    chunks.extend(split_chunks)

                # If current chunk plus this committee exceeds min size, start new chunk
                elif (
                    current_chunk
                    and len(current_chunk + committee_content) >= max_chunk_size
                ):
                    chunks.append(current_chunk)
                    current_chunk = committee_content
                else:
                    # Add to current chunk
                    if current_chunk:
                        current_chunk += "\n" + committee_content
                    else:
                        current_chunk = committee_content

                committee_start_index = (
                    next_committee_start if next_committee_start != -1 else len(lines)
                )
                i = (
                    committee_start_index - 1
                    if next_committee_start != -1
                    else len(lines)
                )

    # Add any remaining content
    if committee_start_index < len(lines):
        remaining_content = "\n".join(lines[committee_start_index:])

        # Check if remaining content is too large
        if len(remaining_content) > 2 * max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
            split_chunks = split_oversized_text(remaining_content, 2 * max_chunk_size)
            chunks.extend(split_chunks)
        else:
            current_chunk += "\n" + remaining_content

    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks

class Member(BaseModel):
    member_name: str
    member_role: str
    member_state: str

class Agency(BaseModel):
    agency_name: str
    agency_members: list[Member]


class AgenciesJsonSchema(BaseModel):
    agencies: list[Agency]

def extract_independent_agencies_info(text_chunk: str, client: openai.OpenAI) -> str:
    """
    Uses OpenAI's API to extract agencies, member names, and roles from the given text.
    Returns the information in JSON format as specified by the implementation.

    Args:
        text_chunk: Chunk of text to process
        client: OpenAI API client

    Returns:
        response: Extracted information in JSON format

    Raises:
        Exception: If an error occurs during the API call
    """
    print(f"Processing chunk of size: {len(text_chunk)} characters")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                    Extract agency and member information from this text into JSON format.
                    Be thorough in extracting all relevant information (don't miss any names).
                    
                    For each agency:
                    1. Find the agency name (marked by ALL CAPS titles with contact information)
                    2. Include all organizational units under that agency until the next main agency appears
                    3. Process ALL names and roles hierarchically from the start of the agency section until the next agency section, including:
                    - Agency heads (Chair, Administrator, Director, etc.)
                    - Board members/Commissioners
                    - Executive staff
                    - Office directors
                    - Division heads
                    - Regional administrators
                    - All other listed personnel

                    MEMBER PROCESSING INSTRUCTIONS:
                    - Process every single name that appears under an agency until the next agency section begins
                    - Record each person's full title/role exactly as listed
                    - Look for state information (marked by "of [State]" or similar)
                    - Process ALL sections including:
                        - Board of Directors/Trustees
                        - Commissioners
                        - Executive Leadership
                        - Office Directors
                        - Regional Offices
                        - Field Offices
                        - Administrative sections
                        - Advisory committees/boards
                        - Ex officio members
                        - Any other listed sections

                    For lines with multiple names/roles:
                    - Process all names on the line
                    - Look for names separated by commas or semicolons
                    - Check for continuing entries on next lines
                    - Watch for indented entries that may relate to previous entries

                    For each name entry, record:
                    - Full name
                    - Complete role/title as listed (leave as 'Member' if no specific role listed)
                    - State if provided (use 'N/A' if none listed)

                    Important details:
                    - Include EVERY name that appears under an agency section
                    - Maintain the exact titles/roles as written
                    - Process names in ALL subsections (don't skip organizational units)
                    - Check for names in address/contact blocks
                    - Look for continuing entries across page breaks
                    - Process both primary and alternate/deputy positions
                    - Don't distinguish between political appointees and career staff - list all names
                    - Include ex officio members and their roles
                    - Include temporary/acting roles (marked with "acting" or similar)
                    - Process regional/field office personnel
                    - Check for names in footnotes or supplementary sections

                    Output the results in the existing JSON structure provided.
                    """,
                },
                {"role": "user", "content": text_chunk},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "_",
                    "schema": AgenciesJsonSchema.model_json_schema(),
                },
            },
            temperature=0.3,
            timeout=600,  # 10 minute timeout per chunk
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during API call: {str(e)}")
        raise


def process_independent_agency_file(
    file_name: str, input_dir: str, output_dir: str, client: openai.OpenAI
) -> None:
    """
    Processes the given independent agency file by using the `chunk_text` function to split the
    content into chunks, and then extracting independent agency information in JSON format using
    the `extract_independent_agencies_info` function. The results are combined and saved in a
    JSON file.

    Args:
        file_name: The name of the file to process.
        input_dir: The directory containing the input file.
        output_dir: The directory to save the output JSON file.
        client: OpenAI API client
    """
    # Read file content
    file_path = os.path.join(input_dir, file_name)
    with open(file_path, "r") as file:
        content = file.read()
        print(f"File loaded. Size: {len(content)} characters")

    print("Splitting content into chunks...")
    chunks = chunk_text(content)
    print(f"Split into {len(chunks)} chunks")

    all_committees = {"agencies": []}

    # Process each chunk
    for chunk_num, chunk in enumerate(chunks, 1):
        print(f"\nProcessing chunk {chunk_num}/{len(chunks)}")
        try:
            # Extract independent agency information in JSON format
            agency_info = extract_independent_agencies_info(chunk, client)

            try:
                # Parse the JSON response
                chunk_data = json.loads(agency_info)

                # Merge agencies from this chunk
                if "agencies" in chunk_data:
                    all_committees["agencies"].extend(chunk_data["agencies"])

                print(f"Successfully processed chunk {chunk_num}")

            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in chunk {chunk_num}: {str(e)}")
                # Save the problematic chunk
                error_file_path = os.path.join(
                    output_dir, f"{file_name}_chunk{chunk_num}_error.txt"
                )
                with open(error_file_path, "w") as error_file:
                    error_file.write(agency_info)
                print(f"Problematic chunk saved to {error_file_path}")
                continue

        except Exception as e:
            print(f"Error processing chunk {chunk_num}: {str(e)}")
            continue

    # Save the combined results
    json_file_path = os.path.join(
        output_dir, f"{file_name}_output.json"
    )  # output file name

    os.makedirs(output_dir, exist_ok=True)

    with open(json_file_path, "w") as json_file:
        json.dump(all_committees, json_file, indent=2)
    print(f"\nCombined results saved to {json_file_path}")


def process_independent_agency_file_for_congress(
    congress_num: int, client: openai.OpenAI, base_directory: str = "."
) -> None:
    """
    Processes the independent agency file for the given Congress number by calling the
    `process_independent_agency_file` function for all relevant files in the directory
    corresponding to the Congress number.

    Args:
        congress_num: The number of the Congress to process.
        client: OpenAI API client
        base_directory: The base directory where the files are located.
    """
    print(f"Processing independent agency file for Congress {congress_num}...")

    for filename in os.listdir(
        f"{base_directory}/congressional_directory_files/congress_{congress_num}/txt"
    ):
        if "INDEPENDENTAGENCIES" in filename:
            process_independent_agency_file(
                filename,
                f"{base_directory}/congressional_directory_files/congress_{congress_num}/txt",
                f"{base_directory}/outputs/{congress_num}",
                client,
            )


if __name__ == "__main__":
    load_dotenv()

    input_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    print("Processing independent agency file...")
    # process_independent_agency_file('CDIR-2022-10-26-INDEPENDENTAGENCIES.txt',
    # 'congressional_directory_files/congress_117/txt', 'outputs/117')
    process_independent_agency_file_for_congress(congress_num=117, client=input_client)
