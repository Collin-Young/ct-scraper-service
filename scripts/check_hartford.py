from collections import Counter
from ct_scraper.scrape_cases import CaseScraper

def main():
    town = "Hartford"
    rows = []
    with CaseScraper(headless=True) as scraper:
        for row in scraper.scrape_towns([town]):
            rows.append(row)
    print(f"Town {town} yielded {len(rows)} cases")
    dockets = Counter(r.docket_link for r in rows)
    dupes = {d: c for d, c in dockets.items() if c > 1}
    if dupes:
        print("Duplicate docket link counts:")
        for d, c in dupes.items():
            print(d, c)
    else:
        print("No duplicate docket links")
    blank_addresses = [r for r in rows if not r.property_address]
    print(f"Rows without property address: {len(blank_addresses)}")

if __name__ == "__main__":
    main()
