# CLAUDE.md - Assistant Guide

## Commands
- Run extractor: `python run.py --congress <number> [--processors <list>] [--api_key <key>]`
  - Example: `python run.py --congress 117 --processors "judiciary departments"`
- Test outputs: `python test_validator.py <congress_number>`
- Windows: `run_extractor.bat` (interactive)

## Code Style Guidelines
- **Imports**: Standard lib → Third-party → Local (alphabetical within groups)
- **Type hints**: Use throughout with Pydantic models for validation
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Error handling**: Specific try/except blocks with fallbacks for API failures
- **Functions**: Clear docstrings with Args/Returns sections
- **Data processing pattern**:
  1. Locate input files
  2. Process in chunks
  3. Extract via OpenAI API
  4. Save JSON outputs
  5. Handle errors with fallbacks

## Project Structure
The codebase processes Congressional Directory PDF/TXT files into structured JSON data using OpenAI's API.