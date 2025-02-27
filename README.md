# Congressional Directory Parsing Tool

This tool extracts structured data from congressional directory PDF/text files using AI, converting unstructured text information into structured JSON data.

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Data Structure](#data-structure)
- [Examples](#examples)
- [CI/CD](#ci-cd)
- [Contributing](#contributing)
- [License](#license)

## Introduction
The Congressional Directory is a comprehensive publication listing key personnel and organizational information for the U.S. federal government. This tool automates the extraction of information from the text versions of these directories, producing structured JSON outputs that can be used for analysis and research.

## Features
- Extracts information from various sections of the Congressional Directory:
  - Judiciary (courts and judges)
  - House and Senate committees
  - Executive departments
  - Independent agencies
  - Diplomatic offices
  - International organizations
  - Boards and commissions
- Processes text files by Congress number (105th through 117th Congress)
- Outputs structured JSON data
- Configurable to process specific sections or entire directories

## Installation
### From Source
1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

### Using the Executable
Download the pre-built executable from the GitHub releases page. The executable includes all necessary dependencies except for the OpenAI API key.

## Usage
### Command-line Interface
Run the tool with the following command-line arguments:
```
congressional_extractor --congress 117 --processors judiciary departments
```

Arguments:
- `--congress`: Congress number or range (e.g., "117" or "114-117")
- `--processors`: Optional list of specific processors to run (if omitted, all processors are run)
  - Available processors: `judiciary`, `house_senate_committees`, `departments`, `independent_agencies`, `diplomatic_offices`, `international_organizations`, `boards_and_commissions`

### Using the Batch File (Windows)
If you downloaded the executable, you can use the included `run_extractor.bat` file, which provides a simple interactive prompt.

## Data Structure
The tool produces JSON files in the `outputs/[congress_number]` directory with standardized schemas for each section type. For example, judiciary output follows this structure:
```json
{
  "courts": [
    {
      "court_name": "Supreme Court of the United States",
      "court_personnel": [
        {"name": "John G. Roberts", "role": "Chief Justice"}
      ]
    }
  ]
}
```

## Examples
Extract judiciary data from the 111th Congress:
```
python run.py --congress 111 --processors judiciary
```

Process all sections for multiple congresses:
```
python run.py --congress 114-117
```

## CI/CD
This project uses GitHub Actions for continuous integration, which:
1. Builds the executable for Windows
2. Tests the executable's functionality
3. Packages the executable with supporting files
4. Makes the package available as an artifact

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## License
This project is licensed under the MIT License.