@echo off
REM Simple script to run the MO scraper on Windows
REM Uses fresh profile but loads saved cookies to bypass Cloudflare
REM Usage: run_mo_scraper_simple.bat [county] [start_date] [continue]

set COUNTY=%1
if "%COUNTY%"=="" set COUNTY=all

set START_DATE=%2
if "%START_DATE%"=="" set START_DATE=01/01/2026

set CONTINUE=%3
if "%CONTINUE%"=="" set CONTINUE=continue

echo ==========================================
echo MO Court Scraper with Block Detection
echo ==========================================
echo County: %COUNTY%
echo Start Date: %START_DATE%
echo Continue: %CONTINUE%
echo ==========================================
echo.

REM Disable proxy until Bright Data KYC is approved
set MO_SCRAPER_PROXY=

REM Use fresh profile (avoids lock issues)
set MO_SCRAPER_PROFILE_COPY=false

REM Set headless mode (yes or no)
set MO_SCRAPER_HEADLESS=no

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install requirements if needed
if not exist .venv\Scripts\chromedriver.exe (
    echo Installing requirements...
    pip install -r requirements.txt
)

echo Starting scraper...
python mo_scraper/fetch_mo_cases.py %COUNTY% %START_DATE% %CONTINUE%

echo.
echo Scraper finished. Check output above for results.
pause
