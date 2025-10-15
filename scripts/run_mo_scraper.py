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
    parser.add_argument('--skip-non-empty', action='store_true', help='Skip MO counties that already have entries in the database')
    parser.add_argument(
        '--force-county',
        action='append',
        default=[],
        help='County name to always run even if skipping non-empty counties (can be used multiple times)'
    )
    parser.add_argument(
        '--force-county-start',
        action='append',
        default=[],
        metavar='NAME=MM/DD/YYYY',
        help='Override start date for specific counties (repeatable, format NAME=MM/DD/YYYY)'
    )

    args = parser.parse_args()
    force_start_overrides = {}
    for entry in args.force_county_start:
        if '=' not in entry:
            parser.error(f"--force-county-start entries must use NAME=DATE format (got '{entry}')")
        county_name, start_date_override = entry.split('=', 1)
        county_name = county_name.strip()
        start_date_override = start_date_override.strip()
        if not county_name or not start_date_override:
            parser.error(f"--force-county-start entries must include both county and date (got '{entry}')")
        force_start_overrides[county_name] = start_date_override

    if args.mo or args.both:
        scrape_court_cases_and_parties(
            county_name=args.county,
            start_date=args.start_date,
            continue_search=args.continue_search,
            headless='headless' if args.headless else 'no',
            filter_case_type=args.filter_case_type,
            skip_non_empty=args.skip_non_empty,
            force_counties=args.force_county,
            force_county_start_dates=force_start_overrides,
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
