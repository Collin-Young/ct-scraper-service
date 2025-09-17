#!/usr/bin/env python3
import sys
from ct_scraper.scrape_cases import scrape_cases

if __name__ == "__main__":
    if len(sys.argv) < 2:
        towns = ["Andover"]  # Default small town for testing
    else:
        towns = sys.argv[1:]

    print("Scraping towns: {}".format(towns))
    scrape_cases(towns)
    print("Scraping complete. Check database and CSV output.")