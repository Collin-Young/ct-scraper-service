#!/usr/bin/env python3
import sys
from ct_scraper.scrape_cases import scrape_cases
import subprocess
import os

if __name__ == "__main__":
    if len(sys.argv) < 2:
        towns = ["Andover"]  # Default small town for testing
    else:
        towns = sys.argv[1:]

    print("Scraping towns: {}".format(towns))
    scrape_cases(towns)
    print("Scraping complete. Check database and CSV output.")

    # Run Missouri scraper for all counties starting from January 1, 2025
    print("Running Missouri court cases scraper...")
    mo_script = os.path.join(os.path.dirname(__file__), "fetch_cases_with_parties.py")
    cmd = [
        sys.executable, mo_script, "all", "01/01/2025", "continue", "no", "all"
    ]
    subprocess.run(cmd, check=True)
    print("Missouri scraper complete.")