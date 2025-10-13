"""
Utility runner to re-scrape MO counties that currently have zero stored cases.

This script imports the main scraper entry point and iterates through the
handful of counties that came back with zero counts after merging ambiguous
municipal results. Run this on the Raspberry Pi where the scraper normally
executes, e.g.:

    python scripts/run_zero_counties.py --start-date 01/01/2025 --headless

By default it runs headless and allows the scraper to continue paging forward
through dates.
"""

import argparse

from mo_scraper.fetch_mo_cases import scrape_court_cases_and_parties


# These labels should match (or be contained within) the dropdown text so the
# scraper can resolve them to the exact select option.
ZERO_COUNTIES = (
    "Fine Collection Center",
    "Gasconade",
    "Greene",
    "Grundy",
    "Henry",
    "Hickory",
    "Holt",
    "Howell",
    "Iron",
    "Oregon",
    "Osage",
    "Ozark",
    "Pemiscot",
    "Perry",
    "Pettis",
    "Phelps",
    "Platte",
    "Ralls",
    "Ray",
    "Reynolds",
    "Saline",
    "Schuyler",
    "Scotland",
    "Scott",
    "Shannon",
    "Shelby",
    "St. Charles",
    "St. Francois",
    "St. Louis",
    "Ste. Genevieve",
    "Stone",
    "Sullivan",
    "Taney",
    "Texas",
    "Vernon",
)


def run_queue(counties, start_date, continue_search, headless):
    for label in counties:
        print(f"\n===== Running {label} =====")
        try:
            scrape_court_cases_and_parties(
                county_name=label,
                start_date=start_date,
                continue_search=continue_search,
                headless=headless,
            )
        except Exception as exc:  # noqa: BLE001 - we just want to keep iterating
            print(f"[ERROR] Failed county '{label}': {exc}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the MO scraper for the remaining zero-count counties.",
    )
    parser.add_argument(
        "--start-date",
        default="01/01/2025",
        help="Starting date (MM/DD/YYYY) for each county search.",
    )
    parser.add_argument(
        "--no-continue",
        action="store_true",
        help="Stop each county after the first window instead of paging forward.",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run Chrome with a visible window instead of headless mode.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    continue_flag = "no" if args.no_continue else "continue"
    headless_flag = "no" if args.no_headless else "headless"
    run_queue(ZERO_COUNTIES, args.start_date, continue_flag, headless_flag)


if __name__ == "__main__":
    main()
