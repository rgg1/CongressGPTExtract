# orchestrator.py
import argparse
from typing import List, Optional
import importlib
from dotenv import load_dotenv
import openai
import os
import sys

from judiciary import process_all_courts_files
from international_organizations import process_international_organizations_file_for_congress
from independent_agencies import process_independent_agency_file_for_congress
from house_senate_committees import process_all_committees_for_congress
from diplomatic_offices import process_diplomatic_offices_file_for_congress
from departments import process_all_departments_files
from boards_and_commissions import process_boards_and_commissions_files_for_congress

def get_base_directory():
    """Get the base directory of the project."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ProcessingOrchestrator:
    def __init__(self, api_key=None):
        # Initialize OpenAI client
        load_dotenv()
        # self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please provide it via command line argument or .env file.")
            
        self.client = openai.OpenAI(api_key=self.api_key)

        base_directory = get_base_directory()

        self.processors = {
            'judiciary': lambda congress: process_all_courts_files(congress, self.client, base_directory),
            'international_organizations': lambda congress: process_international_organizations_file_for_congress(congress, self.client, base_directory),
            'independent_agencies': lambda congress: process_independent_agency_file_for_congress(congress, self.client, base_directory),
            'house_senate_committees': lambda congress: process_all_committees_for_congress(congress, self.client, base_directory),
            'diplomatic_offices': lambda congress: process_diplomatic_offices_file_for_congress(congress, self.client, base_directory),
            'departments': lambda congress: process_all_departments_files(congress, self.client, base_directory),
            'boards_and_commissions':lambda congress: process_boards_and_commissions_files_for_congress(congress, self.client, base_directory)
        }

    def run_processors(
        self,
        congress_range: List[str],
        selected_processors: Optional[List[str]] = None
    ) -> None:
        """
        Run selected processors for specified congress sessions.
        
        Args:
            congress_range: List of congress sessions (e.g., ['114', '115', '116'])
            selected_processors: List of processor names to run. If None, runs all processors.
        """
        # Use all processors if none specified
        processors_to_run = selected_processors or list(self.processors.keys())
        
        # Validate processor names
        invalid_processors = set(processors_to_run) - set(self.processors.keys())
        if invalid_processors:
            raise ValueError(f"Invalid processor names: {invalid_processors}")

        # Run each processor for each congress session
        for congress in congress_range:
            print(f"\nProcessing {congress}th Congress data...")
            for processor_name in processors_to_run:
                print(f"Running {processor_name} processor...")
                try:
                    self.processors[processor_name](congress)
                except Exception as e:
                    print(f"Error in {processor_name} processor for {congress}th Congress: {str(e)}")

def parse_congress_range(range_str: str) -> List[str]:
    """Convert a range string like '114-117' or '117' into a list of congress numbers."""
    if '-' in range_str:
        start, end = map(int, range_str.split('-'))
        return [str(x) for x in range(start, end + 1)]
    return [range_str]

def main():
    parser = argparse.ArgumentParser(description='Process congressional data across multiple processors')
    parser.add_argument(
        '--congress',
        required=True,
        help='Congress range (e.g., "117" for single congress or "114-117" for range)'
    )
    parser.add_argument(
        '--processors',
        nargs='*',
        help='Specific processors to run (e.g., judiciary executive). If not specified, runs all processors.'
    )

    parser.add_argument(
        '--api_key',
        help='OpenAI API key. If not provided, will check the .env file.'
    )

    args = parser.parse_args()
    
    # Initialize environment
    load_dotenv()

    # Create orchestrator and run processors
    try:
        orchestrator = ProcessingOrchestrator(api_key=args.api_key)
        congress_range = parse_congress_range(args.congress)
        orchestrator.run_processors(congress_range, args.processors)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()