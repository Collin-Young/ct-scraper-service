#!/bin/bash
# Helper script to run the MO scraper with block detection and auto-resume
# Usage: ./run_mo_scraper.sh [county] [start_date] [continue]

# Set your Windows PC's IP address here
WINDOWS_IP="${MO_SCRAPER_REMOTE_DEBUGGING_ADDRESS:-192.168.86.43}"
REMOTE_PORT="${MO_SCRAPER_REMOTE_DEBUGGING_PORT:-9222}"

export MO_SCRAPER_REMOTE_DEBUGGING_ADDRESS=$WINDOWS_IP
export MO_SCRAPER_REMOTE_DEBUGGING_PORT=$REMOTE_PORT

# Optional: Set these to customize behavior
export MO_SCRAPER_BLOCK_CHECK_INTERVAL=${MO_SCRAPER_BLOCK_CHECK_INTERVAL:-30}
export MO_SCRAPER_MAX_BLOCK_WAIT=${MO_SCRAPER_MAX_BLOCK_WAIT:-10}

COUNTY="${1:-all}"
START_DATE="${2:-01/01/2025}"
CONTINUE="${3:-continue}"

echo "=========================================="
echo "MO Court Scraper with Block Detection"
echo "=========================================="
echo "Windows IP: $WINDOWS_IP"
echo "Remote Port: $REMOTE_PORT"
echo "County: $COUNTY"
echo "Start Date: $START_DATE"
echo "Continue: $CONTINUE"
echo "=========================================="
echo ""
echo "Make sure Chrome is running on Windows with:"
echo "  chrome.exe --user-data-dir=\"%LOCALAPPDATA%\\Google\\Chrome\\User Data\" --remote-debugging-port=9222"
echo ""

cd /home/pi/ct-scraper-service
source .venv/bin/activate
python mo_scraper/fetch_mo_cases.py "$COUNTY" "$START_DATE" "$CONTINUE"

echo ""
echo "Scraper finished. Check output above for results."
