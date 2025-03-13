# Congressional Directory Data Extraction Tool

A tool that uses GPT-4o-mini to extract structured data from United States Congressional Directory text files, converting unstructured information into searchable JSON files.

## Overview

The Congressional Directory is a comprehensive set of text files containing information about the personnel of the U.S. federal government. This tool:

1. Processes raw `.txt` files extracted from Congressional Directory PDFs
2. Uses OpenAI's GPT-4o-mini to identify and extract structured information
3. Outputs standardized JSON files with details about individuals and organizations
4. Provides utilities to enhance data with BioGuide IDs and Thomas IDs

## Features

- **Comprehensive extraction** from key sections:
  - Judiciary (courts and judges)
  - House and Senate committees
  - Executive departments
  - Independent agencies
  - Diplomatic offices
  - International organizations
  - Boards and commissions
- **Flexible processing options** to target specific sections or congress numbers
- **Historical coverage** from the 105th through 117th Congress
- **Efficient text chunking** for large documents
- **Robust error handling** when processing problematic documents

## Installation

```bash
# Clone the repository
git clone https://github.com/rgg1/CongressGPTExtract.git
cd CongressGPTExtract

# Install dependencies
pip install -r requirements.txt

# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

## Usage

### Run with Python

```bash
# Process all sections for the 117th Congress
python run.py --congress 117

# Process only judiciary and departments for multiple congresses
python run.py --congress 114-117 --processors judiciary departments

# Use a specific API key
python run.py --congress 116 --api_key sk-your-key-here
```

### Data Enrichment Tools

The `tools/` directory contains utilities for data enrichment, verification, and analysis:

```bash
# Add BioGuide IDs to a specific JSON file or all committee files for a Congress
python tools/add_bioguide_id.py [input_file]
python tools/add_bioguide_id.py --congress 117

# Add Thomas IDs to a specific JSON file or all committee files for a Congress
python tools/add_thomas_id.py [input_file]
python tools/add_thomas_id.py --congress 117

# Verify BioGuide ID matching statistics for a file or Congress
python tools/bioguide_id_checker.py [json_file]
python tools/bioguide_id_checker.py --congress 117

# Verify Thomas ID matching statistics for a file or Congress
python tools/thomas_id_checker.py [json_file]
python tools/thomas_id_checker.py --congress 117

# Run output verification tool on a file or all files for a Congress
python tools/output_verifier.py [json_file]
python tools/output_verifier.py --congress 117

# Enrich data with both BioGuide and Thomas IDs in one step
python tools/enrich_data.py --congress 117 
python tools/enrich_data.py --congress 117 --skip-bioguide # Skip BioGuide ID enrichment
python tools/enrich_data.py --congress 117 --skip-thomas # Skip Thomas ID enrichment
```

### Vertical Slice Demonstration

The vertical slice script demonstrates the complete data extraction and processing pipeline:

```bash
# Run the complete pipeline demonstration for both House Committees and Diplomatic Offices
python vertical_slice.py

# Run for only House Committees or Diplomatic Offices
python vertical_slice.py --type house
python vertical_slice.py --type diplomatic

# Specify a custom output file
python vertical_slice.py --output custom_output.txt
```

### Windows Executable

For Windows users, the included batch file provides an interactive experience:

```
run_extractor.bat
```

The executable is built and tested via GitHub Actions.

## Output Structure

The tool produces JSON files in the `outputs/<congress_number>/` directory. Each file follows a standardized schema for its file type.

## Project Structure

The repository is organized as follows:
- `gpt_parsing_files/`: Core extraction modules for each type of content
- `tools/`: Utility scripts for enriching and validating outputs
- `congressional_directory_files/`: Source text files organized by congress
- `outputs/`: JSON output files organized by congress
- Root: Main entry points and configuration files

Output sample:

```json
{
  "courts": [
    {
      "court_name": "Supreme Court of the United States",
      "court_personnel": [
        {"name": "John G. Roberts", "role": "Chief Justice"},
        {"name": "Sonia Sotomayor", "role": "Associate Justice"}
      ]
    }
  ]
}
```

## GitHub Actions Integration

This repository includes a CI/CD workflow that:
- Builds a Windows executable and a macOS .app file
- Tests the executable and .app file using `test_validator.py`
