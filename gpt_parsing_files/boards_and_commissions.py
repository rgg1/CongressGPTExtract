"""
This script processes boards and commissions files from the Congressional Directory
to extract government bodies (boards and commissions), member names, and roles.
The extracted information is saved to a JSON file.
"""

import os
import json
import openai
from dotenv import load_dotenv
from pydantic import BaseModel

# class definitions for the JSON schema

class Member(BaseModel):
    member_name: str
    member_role: str
    member_state: str


class GovernmentBody(BaseModel):
    government_body_name: str
    government_body_members: list[Member]

class BoardsAndCommissions(BaseModel):
    government_bodies: list[GovernmentBody]


def extract_boards_and_commissions_info(text_chunk: str, client: openai.OpenAI) -> str:
    """
    Uses OpenAI's API to extract government bodies (boards and commissions), member names,
    and roles from the given text. Returns the information in JSON format as specified by
    the implementation.

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
                    Extract government bodies (boards, commissions, offices, etc.) and member information from this text into JSON format.
                    Be thorough in extracting all relevant information (don't miss any names). For each government body:

                    1. Find the government body name (typically in ALL CAPS)

                    2. Process ALL members and their roles under each body until the next ALL CAPS heading appears:
                    - Look for members listed with explicit roles/titles
                    - Process appointed positions with appointing authority noted (e.g., "Appointed by the President:")
                    - Include ex-officio members
                    - Process staff sections if present
                    - Process liaison positions

                    MEMBER AND STAFF PROCESSING INSTRUCTIONS:
                    - Look for hierarchical listings (Chair, Vice Chair, Directors, Deputies, etc.)
                    - Process both leadership and regular members
                    - Include military ranks/titles when present
                    - Watch for members listed in office-specific sections
                    - Process ALL names until the next government body heading
                    - Pay attention to indentation which may indicate reporting relationships
                    - Look for sections that continue across multiple pages

                    For lines with multiple entries:
                    * Process all names on the line, separated by commas or other delimiters
                    * Look for "and" joining multiple names
                    * Check for titles shared across multiple names

                    For biographical entries:
                    * Extract the name and role from biographical text blocks
                    * Don't miss names mentioned within biographical descriptions

                    3. For each entry, record:
                    - Full name (including titles/ranks if present)
                    - Role (explicit role or position listed, use 'Member' if none specified)
                    - State (if listed, use 'N/A' if not)

                    Important details:
                    - Include EVERY name that appears under a government body
                    - Process ALL sections until the next government body heading
                    - Look for multiple names per line
                    - Keep hierarchical relationships when present
                    - Include both permanent and acting positions
                    - Don't miss names in contact information sections
                    - Process both civilian and military titles
                    - Include biographical information when relevant
                    - Check for continuation of entries across pages
                    - For positions with multiple holders, include all names

                    NOTE: Every single name in the document should appear in the JSON output under some government body. If you're unsure where a name belongs, include it under the most recently mentioned government body.

                    Output the results in the existing JSON structure provided.
                    """,
                },
                {"role": "user", "content": text_chunk},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "_",
                    "schema": BoardsAndCommissions.model_json_schema(),
                },
            },
            temperature=0.3,
            timeout=600,  # 10 minute timeout per chunk
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during API call: {str(e)}")
        raise


def chunk_boards_and_commissions_text(
    text: str, max_chunk_size: int = 15000
) -> list[str]:
    """
    Split the text into chunks of a maximum size.
    The chunking is done by identifying government body headers.

    Args:
        text: Text to split into chunks
        max_chunk_size: Maximum size of each chunk

    Returns:
        chunks: List of text chunks
    """
    chunks = []
    lines = text.split("\n")

    def is_government_body_header(line, next_line=""):
        """Check if line appears to be a government body header"""
        line = line.strip()
        if not line:
            return False

        is_caps = line.isupper() and len(line) > 10

        # Check for common board/commission indicators
        indicators = [
            "BOARD",
            "COMMISSION",
            "GROUP",
            "COMMITTEE",
            "PARLIAMENTARY",
            "OFFICE",
            "FOUNDATION",
            "INSTITUTE",
            "ASSOCIATION",
            "SENATE",
            "HOUSE",
        ]

        has_indicator = any(ind in line for ind in indicators)

        # Check if followed by contact info
        has_contact = (
            "phone" in next_line.lower()
            or "address" in next_line.lower()
            or "fax" in next_line.lower()
        )

        return is_caps and (has_indicator or has_contact)

    def find_next_body(start_idx):
        """Find the index of the next government body header"""
        for i in range(start_idx + 1, len(lines)):
            next_line = next((line for line in lines[i + 1 :] if line.strip()), "")
            if is_government_body_header(lines[i], next_line):
                return i
        return len(lines)

    def split_oversized_text(text, max_size):
        """Split oversized text into smaller chunks"""
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

    # Process the text into bodies
    bodies = []
    current_start = 0

    while current_start < len(lines):
        next_body_start = find_next_body(current_start)
        if next_body_start == current_start:
            next_body_start = find_next_body(current_start + 1)

        body_content = "\n".join(lines[current_start:next_body_start])
        if body_content.strip():
            bodies.append(body_content)

        current_start = next_body_start

    # Combine bodies into chunks while respecting max size
    current_chunk = ""

    for body in bodies:
        # If a body is longer than 2 * max_chunk_size, split it
        if len(body) > 2 * max_chunk_size:
            # If there's an existing chunk, add it first
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # Split the oversized body text into smaller pieces
            split_chunks = split_oversized_text(body, 2 * max_chunk_size)
            chunks.extend(split_chunks)
            continue

        # If single body exceeds max size, keep it whole
        if len(body) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            chunks.append(body)
            continue

        # If adding body would exceed max size
        if len(current_chunk) + len(body) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = body
        else:
            if current_chunk:
                current_chunk += "\n\n" + body
            else:
                current_chunk = body

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def process_boards_and_commissions_file(
    file_name: str, input_dir: str, output_dir: str, client: openai.OpenAI
) -> None:
    """
    Process a boards and commissions file, extracting government bodies and member information using
    the function `extract_boards_and_commissions_info` and chunking the text using the function
    `chunk_boards_and_commissions_text`. The extracted information is saved to a JSON file.

    Args:
        file_name: Name of the file to process
        input_dir: Directory containing the input file
        output_dir: Directory to save the output JSON file
        client: OpenAI API client
    """
    # Read file content
    file_path = os.path.join(input_dir, file_name)
    with open(file_path, "r") as file:
        content = file.read()
        print(f"File loaded. Size: {len(content)} characters")

    print("Splitting content into chunks...")
    chunks = chunk_boards_and_commissions_text(content)
    print(f"Split into {len(chunks)} chunks")

    all_government_bodies = {"government_bodies": []}

    # Process each chunk
    for chunk_num, chunk in enumerate(chunks, 1):
        print(f"\nProcessing chunk {chunk_num}/{len(chunks)}")
        try:
            # Extract boards and commissions information in JSON format
            boards_and_commissions_info = extract_boards_and_commissions_info(
                chunk, client
            )

            try:
                # Parse the JSON response
                chunk_data = json.loads(boards_and_commissions_info)

                # Merge agencies from this chunk
                if "government_bodies" in chunk_data:
                    all_government_bodies["government_bodies"].extend(
                        chunk_data["government_bodies"]
                    )

                print(f"Successfully processed chunk {chunk_num}")

            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in chunk {chunk_num}: {str(e)}")
                # Save the problematic chunk
                error_file_path = os.path.join(
                    output_dir, f"{file_name}_chunk{chunk_num}_error.txt"
                )
                with open(error_file_path, "w") as error_file:
                    error_file.write(boards_and_commissions_info)
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
        json.dump(all_government_bodies, json_file, indent=2)
    print(f"\nCombined results saved to {json_file_path}")


def process_boards_and_commissions_files_for_congress(
    congress_num: int, client: openai.OpenAI, base_directory: str = "."
):
    """
    Uses the function `process_boards_and_commissions_file` to process all boards and commissions
    files for a given Congress session.

    Args:
        congress_num: Congress session number (e.g., 117)
        client: OpenAI API client
        base_directory: Base directory containing the congressional directory files
    """
    print(f"Processing boards and commissions files for Congress {congress_num}...")

    for filename in os.listdir(
        f"{base_directory}/congressional_directory_files/congress_{congress_num}/txt"
    ):
        if "BOARDSANDCOMMISSIONS" in filename:
            process_boards_and_commissions_file(
                filename,
                f"{base_directory}/congressional_directory_files/congress_{congress_num}/txt",
                f"{base_directory}/outputs/{congress_num}",
                client,
            )


if __name__ == "__main__":
    load_dotenv()

    input_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    process_boards_and_commissions_files_for_congress(congress_num=117, client=input_client)
