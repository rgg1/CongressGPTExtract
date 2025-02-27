@echo off
echo Congressional Data Extraction Tool
echo ================================

echo Current directory: %CD%
echo.

REM Check if .env file exists
if not exist .env (
    echo WARNING: No .env file found with OpenAI API key
    echo You can either:
    echo  1. Create a .env file with your OpenAI API key (OPENAI_API_KEY=your_key_here)
    echo  2. Enter your API key in the prompt below
    echo.
    
    set /p api_key="Enter your OpenAI API key (leave blank to exit): "
    if "%api_key%"=="" (
        echo No API key provided. Exiting.
        goto end
    )
)

set /p congress="Enter Congress range (e.g., 117 or 114-117): "
if "%congress%"=="" (
    echo No Congress number provided. Exiting.
    goto end
)

echo Available processors:
echo  - diplomatic_offices
echo  - judiciary
echo  - international_organizations
echo  - independent_agencies
echo  - house_senate_committees
echo  - departments
echo  - boards_and_commissions
echo.
set /p processors="Enter processors to run (leave blank for all, or space-separated list): "

echo.
echo Starting extraction process...
echo.

REM Check if we should pass the API key
if defined api_key (
    if "%processors%"=="" (
        congressional_extractor.exe --congress "%congress%" --api_key "%api_key%"
    ) else (
        congressional_extractor.exe --congress "%congress%" --processors %processors% --api_key "%api_key%"
    )
) else (
    if "%processors%"=="" (
        congressional_extractor.exe --congress "%congress%" 
    ) else (
        congressional_extractor.exe --congress "%congress%" --processors %processors%
    )
)

echo.
echo Process completed. 
echo Output files can be found in the "outputs/%congress%" directory.
echo.

:end
echo Press any key to exit.
pause > nul