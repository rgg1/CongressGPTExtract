#!/usr/bin/env python
import os
import sys
import argparse
from dotenv import load_dotenv
import openai

# Import only diplomatic_offices for testing
from gpt_parsing_files.diplomatic_offices import process_diplomatic_offices_file_for_congress

# Add the current directory to the Python path
if getattr(sys, "frozen", False):
    # Running as executable
    base_path = os.path.dirname(sys.executable)
else:
    # Running as script
    base_path = os.path.dirname(os.path.abspath(__file__))

# Make sure gpt_parsing_files is in the path
gpt_path = os.path.join(base_path, "gpt_parsing_files")
if gpt_path not in sys.path:
    sys.path.insert(0, gpt_path)
    sys.path.insert(0, base_path)

def get_base_directory():
    """Get the base directory of the project."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Simplified main function for CI testing - only supports diplomatic_offices"""
    parser = argparse.ArgumentParser(description='Process congressional data')
    parser.add_argument('--congress', required=True, help='Congress number')
    parser.add_argument('--processors', nargs='*', help='Specific processors to run')
    parser.add_argument('--api_key', help='OpenAI API key. If not provided, will check the .env file.')
    args = parser.parse_args()

    # Initialize environment
    load_dotenv()

    # Get the API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OpenAI API key not found. Please provide it via --api_key or set OPENAI_API_KEY environment variable.")
        sys.exit(1)

    # Initialize client
    client = openai.OpenAI(api_key=api_key)

    # Get base directory
    base_directory = get_base_directory()

    print(f"Base directory: {base_directory}")
    print(f"Processing for Congress: {args.congress}")

    # For CI testing, we only run diplomatic_offices
    if args.processors and "diplomatic_offices" in args.processors:
        print(f"Processing diplomatic_offices for Congress {args.congress}")
        process_diplomatic_offices_file_for_congress(args.congress, client, base_directory)
    else:
        print("This build supports the diplomatic_offices processor")
        process_diplomatic_offices_file_for_congress(args.congress, client, base_directory)

if __name__ == "__main__":
    main()
