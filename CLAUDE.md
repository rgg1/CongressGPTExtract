# Congressional Directory Parsing - Development Guide

## Commands
- **Run parser**: `python run.py --congress 117 --processors judiciary departments`
- **Run single test**: `python test_validator.py 111 judiciary`
- **Install dependencies**: `pip install -r requirements.txt`
- **Build executable**: `pyinstaller --onefile --name extraction run.py`

## Code Style
- **Imports**: Standard library first, then third-party, then local modules
- **Type Hints**: Use Pydantic models for structured data; use typing for function signatures
- **Naming**: snake_case for functions/variables; CamelCase for classes; ALL_CAPS for constants
- **Error Handling**: Use try/except blocks with specific exceptions and detailed error messages
- **Documentation**: All functions should have docstrings with Args/Returns sections
- **Processors**: Follow established patterns in existing processor files
- **Environment**: Use dotenv for configuration and environment variables
- **API Usage**: Use the OpenAI client consistently with error handling for API calls