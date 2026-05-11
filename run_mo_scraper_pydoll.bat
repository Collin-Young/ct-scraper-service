@echo off
REM Script to install pydoll and run the Pydoll-based MO scraper on Windows
REM Usage: run_mo_scraper_pydoll.bat [county] [start_date] [continue]

set COUNTY=%1
if "%COUNTY%"=="" set COUNTY=all

set START_DATE=%2
if "%START_DATE%"=="" set START_DATE=01/01/2026

set CONTINUE=%3
if "%CONTINUE%"=="" set CONTINUE=continue

echo ==========================================
echo MO Court Scraper - Pydoll Version (CDP-based)
echo ==========================================
echo County: %COUNTY%
echo Start Date: %START_DATE%
echo Continue: %CONTINUE%
echo ==========================================
echo.

REM Disable proxy until Bright Data KYC is approved
set MO_SCRAPER_PROXY=

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install or update pydoll
echo Installing pydoll...
pip install pydoll

REM Run the Pydoll-based scraper
echo.
echo Starting Pydoll-based scraper...
python mo_scraper/fetch_mo_cases_pydoll.py %COUNTY% %START_DATE% %CONTINUE%

echo.
echo Scraper finished. Check output above for results.
pause
