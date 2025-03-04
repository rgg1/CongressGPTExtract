#!/usr/bin/env python
import os
import sys
import time
import openai
from dotenv import load_dotenv

from gpt_parsing_files.diplomatic_offices import (
    process_diplomatic_offices_file_for_congress,
)

script_dir = os.path.dirname(os.path.abspath(__file__))
gpt_path = os.path.join(script_dir, "gpt_parsing_files")
if gpt_path not in sys.path:
    sys.path.insert(0, gpt_path)
    sys.path.insert(0, script_dir)

def main():
    load_dotenv()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "ERROR: OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
        )
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)

    # Set congress number to the same as in the workflow test (.yml)
    congress_num = "117"

    print(
        f"Processing diplomatic_offices for Congress {congress_num} using interpreter"
    )

    # Measure performance
    start_time = time.time()

    # Run the same processor as the executable test
    process_diplomatic_offices_file_for_congress(congress_num, client, script_dir)

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"\nPerformance metrics:")
    print(f"Execution time (interpreter): {elapsed_time:.4f} seconds")

    # Create a file to store the performance metrics
    with open("interpreter_performance.txt", "w") as f:
        f.write(f"{elapsed_time:.4f}")

if __name__ == "__main__":
    main()
