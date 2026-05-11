@echo off
REM Helper script to run the MO scraper directly on Windows (no remote debugging needed)
REM Usage: run_mo_scraper_windows.bat [county] [start_date] [continue]

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

REM Use your existing Chrome profile (where you've already passed Cloudflare)
set MO_SCRAPER_PROFILE_DIR=%LOCALAPPDATA%\Google\Chrome\User Data

REM Set headless mode (yes or no)
set MO_SCRAPER_HEADLESS=no

cd /d "%~dp0"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating one...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing requirements...
    pip install -r requirements.txt
)

echo Starting scraper...
python mo_scraper/fetch_mo_cases.py %COUNTY% %START_DATE% %CONTINUE%

echo.
echo Scraper finished. Check output above for results.
pause
