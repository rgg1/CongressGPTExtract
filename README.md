# Congressional Directory Data Extraction Tool

A tool that uses GPT-4o-mini to extract structured data from United States Congressional Directory text files, converting unstructured information about personnel and organizations into searchable JSON datasets.

## Overview

The Congressional Directory is a comprehensive publication containing information about the personnel and structures of the U.S. federal government. This tool:

1. Processes raw `.txt` files extracted from Congressional Directory PDFs
2. Uses OpenAI's GPT-4o-mini to identify and extract structured information
3. Outputs standardized JSON data files with details about individuals and organizations

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

### Windows Executable

For Windows users, the included batch file provides an interactive experience:

```
run_extractor.bat
```

The executable is built and tested via GitHub Actions to ensure functionality.

## Output Structure

The tool produces JSON files in the `outputs/<congress_number>/` directory. Each file follows a standardized schema for its section type:

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
- Builds a Windows executable
- Tests the executable using `test_validator.py`
- Creates a distributable package

## License

This project is licensed under the MIT License.