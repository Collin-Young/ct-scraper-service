"""Run MO scraper independently or alongside CT."""
import argparse
import sys
import os
from mo_scraper.fetch_mo_cases import scrape_court_cases_and_parties

def main():
    parser = argparse.ArgumentParser(description="Run MO or CT scraper.")
    parser.add_argument('--mo', action='store_true', help='Run MO scraper')
    parser.add_argument('--ct', action='store_true', help='Run CT scraper')
    parser.add_argument('--both', action='store_true', help='Run both scrapers')
    parser.add_argument('--county', default='Adair', help='County for MO scraper')
    parser.add_argument('--start-date', default='09/17/2025', help='Start date for MO scraper')
    parser.add_argument('--continue-search', default='continue', choices=['continue', 'no'], help='Continue search for MO scraper')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--filter-case-type', default='all', help='Filter case type for MO scraper')

    args = parser.parse_args()

    if args.mo or args.both:
        scrape_court_cases_and_parties(
            county_name=args.county,
            start_date=args.start_date,
            continue_search=args.continue_search,
            headless='headless' if args.headless else 'no',
            filter_case_type=args.filter_case_type
        )

    if args.ct or args.both:
        # Run CT scraper using existing script
        ct_script = os.path.join('ct-scraper-service', 'run_scraper.py')
        if os.path.exists(ct_script):
            os.system(f'python {ct_script}')
        else:
            print("CT scraper script not found.")

if __name__ == "__main__":
    main()