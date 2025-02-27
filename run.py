#!/usr/bin/env python
# Entry point for the executable

import os
import sys

# Add the repository root to the Python path
repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo_root)

# Import and run the main function from orchestrator
from gpt_parsing_files.orchestrator import main

if __name__ == "__main__":
    main()