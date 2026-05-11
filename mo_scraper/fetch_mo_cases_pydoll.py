#!/usr/bin/env python3
"""
Missouri Court Case Scraper using Pydoll (CDP-based, harder to detect than Selenium)
Connects to existing Chrome browser with remote debugging.
"""

import asyncio
import os
import json
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

import pandas as pd
import aiohttp
from pydoll.browser.chromium import Chrome
from pydoll.exceptions import ElementNotFound

# Import existing database models
from mo_scraper.database import init_db, get_session
from mo_scraper.models import Case, Party

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
COOKIES_FILE = os.path.join(BASE_DIR, 'browser_cookies.json')
PROGRESS_FILE = os.path.join(BASE_DIR, 'mo_scraper_county_progress.txt')
STATE_FILE = os.path.join(BASE_DIR, 'mo_scraper_state.json')

# Configuration
BLOCK_CHECK_INTERVAL = int(os.environ.get('MO_SCRAPER_BLOCK_CHECK_INTERVAL', '30'))
MAX_BLOCK_WAIT_MINUTES = int(os.environ.get('MO_SCRAPER_MAX_BLOCK_WAIT', '10'))
DEFAULT_WAIT_SECONDS = int(os.environ.get('MO_SCRAPER_WAIT_SECONDS', '60'))

BLOCK_PAGE_PATTERNS = (
    'verify you are a human',
    'checking your browser',
    'just a moment',
    'attention required',
    'enable javascript to use',
    'access denied',
    'cloudflare',
    'please stand by',
    'checking your browser before accessing',
    'ddos protection',
    'security check',
    'automated access is not allowed',
    'unusual traffic',
    'suspicious activity',
)

ALLOWED_PARTY_CASE_TYPES = {
    "CC FORECLOSURE",
    "CC QUIET TITLE",
    "CC MECHANICS LIEN",
    "AC APPL TO ENF MECHANICS LIEN",
    "CC APPL TO ENF MECHANICS LIEN",
    "AC LANDLORD COMPLAINT",
    "AC LANDLORD ACTIONS (BULK)",
    "AC RENT AND POSSESSION",
    "AC UNLAWFUL DETAINER",
    "AC UNLAWFUL OCCUPANT",
    "CC RENT AND POSSESSION",
    "CC UNLAWFUL DETAINER",
    "AC REPLEVIN",
    "CC REPLEVIN",
}

ALLOWED_PARTY_CASE_TYPES_NORMALIZED = {t.replace(" ", "").upper() for t in ALLOWED_PARTY_CASE_TYPES}


def normalize_case_type(value: str) -> str:
    """Normalize case type strings for reliable comparisons."""
    if not value:
        return ""
    sanitized = (
        value.replace('\u2013', '-')
        .replace('\u2014', '-')
        .replace('\xa0', ' ')
    )
    collapsed = " ".join(sanitized.split())
    return collapsed.upper()


def is_block_page(page_source: str) -> bool:
    """Check if page source contains block page patterns."""
    page_lower = page_source.lower()
    return any(pattern in page_lower for pattern in BLOCK_PAGE_PATTERNS)


def save_scraping_state(county, date, county_index=None, total_counties=None):
    """Save current scraping state to allow resume after block."""
    state = {
        'current_county': county,
        'current_date': date,
        'county_index': county_index,
        'total_counties': total_counties,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'block_detected': True
    }
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        print(f"[STATE] Saved scraping state: {county} @ {date}")
    except Exception as e:
        print(f"[WARN] Failed to save state: {e}")


def load_scraping_state():
    """Load saved scraping state if available."""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        print(f"[STATE] Loaded saved state: {state.get('current_county')} @ {state.get('current_date')}")
        return state
    except Exception as e:
        print(f"[WARN] Failed to load state: {e}")
        return None


def clear_scraping_state():
    """Clear saved state after successful completion."""
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            print("[STATE] Cleared saved state")
        except Exception as e:
            print(f"[WARN] Failed to clear state: {e}")


async def get_remote_browser_and_tab(remote_address: str, remote_port: str):
    """Connect to existing Chrome browser with remote debugging."""
    chrome = Chrome()
    
    server_ip = remote_address
    server_port = remote_port
    
    async with aiohttp.ClientSession() as session:
        url = f"http://{server_ip}:{server_port}/json/version"
        async with session.get(url) as response:
            data = await response.json()
            ws_url = data['webSocketDebuggerUrl']
            print(f"[CONNECT] Connecting to Chrome at {server_ip}:{server_port}")
            print(f"[CONNECT] Browser: {data.get('Browser')}")
    
    tab = await chrome.connect(ws_url)
    print(f"[CONNECT] Successfully connected to remote Chrome!")
    
    return chrome, tab


async def human_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Add random delay to simulate human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


async def is_page_ready(tab) -> bool:
    """Check if page is ready (not a block page)."""
    try:
        page_source = await tab.execute_script('return document.documentElement.outerHTML')
        if is_block_page(page_source):
            return False
        return True
    except:
        return False


async def select_county(tab, county: str):
    """Select county from dropdown using JavaScript."""
    escaped_county = county.replace("'", "\\'")
    js_code = """
        var select = document.getElementById('courtCode');
        if (!select) return false;
        for (var i = 0; i < select.options.length; i++) {
            if (select.options[i].text === '""" + escaped_county + """') {
                select.selectedIndex = i;
                select.dispatchEvent(new Event('change'));
                return true;
            }
        }
        return false;
    """
    result = await tab.execute_script(js_code)
    return result


async def scrape_party_details_pydoll(tab, case_url: str) -> List[Dict[str, Any]]:
    """Scrape party details from case page using Pydoll."""
    try:
        await tab.go_to(case_url, timeout=30)
        await human_delay(2, 4)
        
        if not await is_page_ready(tab):
            print(f"[BLOCK] Block page detected on party details page")
            return []
        
        # Execute JavaScript to extract party data
        parties_js = await tab.execute_script("""
            var parties = [];
            var rows = document.querySelectorAll('#partyInfo tr, .partyInfo tr, tr.party-row');
            for (var i = 0; i < rows.length; i++) {
                var cells = rows[i].querySelectorAll('td');
                if (cells.length >= 2) {
                    parties.push({
                        Name: cells[0]?.textContent?.trim() || '',
                        PartyRole: cells[1]?.textContent?.trim() || '',
                        Address: cells[2]?.textContent?.trim() || '',
                        HasAttorney: cells[0]?.textContent?.includes('Attorney') || false
                    });
                }
            }
            return parties;
        """)
        
        return parties_js[:10] if parties_js else []
        
    except Exception as e:
        print(f"[PARTY] Error scraping party details: {e}")
        return []


async def scrape_court_cases_pydoll(
    county_name: str,
    start_date: str,
    continue_search: str = "no",
    filter_case_type: str = "all",
    skip_non_empty: bool = False,
    force_counties: Optional[List[str]] = None,
    force_county_start_dates: Optional[Dict[str, str]] = None,
):
    """Main scraping function using Pydoll."""
    
    init_db()
    session = get_session()
    
    remote_address = os.environ.get('MO_SCRAPER_REMOTE_DEBUGGING_ADDRESS', '127.0.0.1')
    remote_port = os.environ.get('MO_SCRAPER_REMOTE_DEBUGGING_PORT', '9222')
    
    chrome, tab = await get_remote_browser_and_tab(remote_address, remote_port)
    
    url = "https://www.courts.mo.gov/casenet/filingDateSearch.do?newSearch=Y"
    
    DROPDOWN_OPTIONS_FILE = os.path.join(STATIC_DIR, "dropdown_options.json")
    dropdown_df = pd.read_json(DROPDOWN_OPTIONS_FILE)
    
    if county_name.lower() == "all":
        counties_to_scrape = [
            option['text'] for option in dropdown_df.to_dict(orient="records")
            if option['text'].lower() != "please select..."
        ]
    else:
        matching_counties = [
            option['text'] for option in dropdown_df.to_dict(orient="records")
            if county_name.lower() in option['text'].lower()
        ]
        if not matching_counties:
            raise ValueError(f"No county found matching '{county_name}' in dropdown options.")
        counties_to_scrape = [matching_counties[0]]
    
    state = load_scraping_state()
    start_index = 0
    if state and state.get('block_detected'):
        print(f"[RESUME] Found saved state, resuming from {state.get('current_county')}")
        await asyncio.sleep(5)
        clear_scraping_state()
    
    if county_name.lower() == "all":
        start_county_env = os.environ.get('MO_SCRAPER_START_COUNTY')
        if start_county_env:
            for idx, name in enumerate(counties_to_scrape):
                if name.lower() == start_county_env.lower():
                    start_index = idx
                    break
    
    saved_count = 0
    
    try:
        for county_idx in range(start_index, len(counties_to_scrape)):
            county = counties_to_scrape[county_idx]
            county_label = county.split(" - ")[0].strip()
            
            print(f"\n[COUNTY] Starting {county}")
            
            county_start_date = start_date
            consecutive_no_cases = 0
            max_consecutive_no_cases = 8
            
            while True:
                print(f"\n[DATE] Scraping {county} for date: {county_start_date}")
                
                await tab.go_to(url, timeout=30)
                await human_delay(2, 4)
                
                if not await is_page_ready(tab):
                    print(f"[BLOCK] Block page detected! Saving state and waiting...")
                    save_scraping_state(county, county_start_date, county_idx, len(counties_to_scrape))
                    print(f"[BLOCK] Please complete any challenges in the browser. Waiting...")
                    cleared = False
                    for _ in range(MAX_BLOCK_WAIT_MINUTES * 2):
                        await asyncio.sleep(BLOCK_CHECK_INTERVAL)
                        await tab.go_to(url, timeout=10)
                        await asyncio.sleep(3)
                        if await is_page_ready(tab):
                            print(f"[BLOCK] Block cleared!")
                            cleared = True
                            clear_scraping_state()
                            break
                    if not cleared:
                        print(f"[ERROR] Block not cleared after {MAX_BLOCK_WAIT_MINUTES} minutes")
                        await chrome.close()
                        session.close()
                        return
                    continue
                
                try:
                    success = await select_county(tab, county)
                    if not success:
                        print(f"[ERROR] Failed to select county {county}")
                        break
                    await human_delay(1, 2)
                    
                    date_input = await tab.find(id='datepicker', timeout=10)
                    await tab.execute_script("arguments[0].removeAttribute('readonly')", date_input)
                    await date_input.clear()
                    await date_input.type_text(county_start_date, interval=0.1)
                    await human_delay(1, 2)
                    
                    find_button = await tab.find(id='findButton', timeout=10)
                    await find_button.click()
                    await human_delay(3, 5)
                    
                    try:
                        await tab.find(id='searchResult', timeout=10)
                        
                        try:
                            await tab.execute_script("""
                                var sel = document.getElementsByName('searchResult_length')[0];
                                if (sel) { sel.value = '100'; sel.dispatchEvent(new Event('change')); }
                            """)
                        except:
                            pass
                        
                        await human_delay(1, 2)
                        
                        cases_js = await tab.execute_script("""
                            var cases = [];
                            var table = document.getElementById('searchResult');
                            if (!table) return cases;
                            var rows = table.querySelectorAll('tr');
                            for (var i = 1; i < rows.length; i++) {
                                var cols = rows[i].querySelectorAll('td');
                                if (cols.length > 5) {
                                    var caseType = cols[4]?.textContent?.trim() || '';
                                    var caseLink = cols[2]?.querySelector('a');
                                    if (caseLink) {
                                        cases.push({
                                            date_filed: cols[1]?.textContent?.trim() || '',
                                            case_number: caseLink.textContent.trim(),
                                            case_url: caseLink.href,
                                            style_of_case: cols[3]?.textContent?.trim() || '',
                                            case_type: caseType,
                                            location: '""" + county_label + """'
                                        });
                                    }
                                }
                            }
                            return cases;
                        """)
                        
                        extracted_cases = cases_js if cases_js else []
                        
                        while True:
                            try:
                                next_disabled = await tab.execute_script("""
                                    var next = document.getElementById('searchResult_next');
                                    return next ? next.classList.contains('disabled') : true;
                                """)
                                
                                if next_disabled:
                                    break
                                
                                await tab.execute_script("document.getElementById('searchResult_next').click()")
                                await human_delay(2, 3)
                                
                                more_cases = await tab.execute_script("""
                                    var cases = [];
                                    var table = document.getElementById('searchResult');
                                    if (!table) return cases;
                                    var rows = table.querySelectorAll('tr');
                                    for (var i = 1; i < rows.length; i++) {
                                        var cols = rows[i].querySelectorAll('td');
                                        if (cols.length > 5) {
                                            var caseType = cols[4]?.textContent?.trim() || '';
                                            var caseLink = cols[2]?.querySelector('a');
                                            if (caseLink) {
                                                cases.push({
                                                    date_filed: cols[1]?.textContent?.trim() || '',
                                                    case_number: caseLink.textContent.trim(),
                                                    case_url: caseLink.href,
                                                    style_of_case: cols[3]?.textContent?.trim() || '',
                                                    case_type: caseType,
                                                    location: '""" + county_label + """'
                                                });
                                            }
                                        }
                                    }
                                    return cases;
                                """)
                                
                                if more_cases:
                                    extracted_cases.extend(more_cases)
                                
                            except Exception as e:
                                print(f"[PAGINATION] Error: {e}")
                                break
                        
                        print(f"[RESULTS] Found {len(extracted_cases)} cases for {county_start_date}")
                        
                        for case_entry in extracted_cases:
                            existing_case = session.query(Case).filter_by(case_number=case_entry['case_number']).first()
                            if existing_case:
                                print(f"[SKIP] Case {case_entry['case_number']} already exists")
                                continue
                            
                            case_type_normalized = normalize_case_type(case_entry['case_type'])
                            should_fetch_parties = case_type_normalized in ALLOWED_PARTY_CASE_TYPES_NORMALIZED
                            
                            party_details = []
                            if should_fetch_parties:
                                party_details = await scrape_party_details_pydoll(tab, case_entry['case_url'])
                            
                            try:
                                new_case = Case(**case_entry)
                                session.add(new_case)
                                session.commit()
                                case_id = new_case.id
                                
                                for i, party in enumerate(party_details[:10], start=1):
                                    if party.get('Name'):
                                        new_party = Party(
                                            case_id=case_id,
                                            party_index=i,
                                            name=party.get('Name', ''),
                                            role=party.get('PartyRole', ''),
                                            address=party.get('Address', ''),
                                            has_attorney=party.get('HasAttorney', False)
                                        )
                                        session.add(new_party)
                                
                                session.commit()
                                saved_count += 1
                                print(f"[SAVED] Case {case_entry['case_number']} with {len(party_details)} parties")
                                
                            except Exception as e:
                                session.rollback()
                                print(f"[ERROR] Saving case {case_entry['case_number']}: {e}")
                        
                        consecutive_no_cases = 0
                        
                    except ElementNotFound:
                        print(f"[NO RESULTS] No cases found for {county_start_date}")
                        consecutive_no_cases += 1
                    
                    if consecutive_no_cases > max_consecutive_no_cases:
                        print(f"[DONE] No cases for several dates. Stopping {county}")
                        break
                    
                    if continue_search == 'continue':
                        try:
                            dt = datetime.strptime(county_start_date, '%m/%d/%Y')
                            next_dt = dt + timedelta(days=7)
                            if next_dt > datetime.today():
                                print(f"[DONE] Reached current date")
                                break
                            county_start_date = next_dt.strftime('%m/%d/%Y')
                        except Exception as e:
                            print(f"[ERROR] Date update: {e}")
                            break
                    else:
                        break
                    
                except Exception as e:
                    print(f"[ERROR] Unexpected error for {county_start_date}: {e}")
                    break
            
            if county_name.lower() == "all":
                with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                    f.write(county)
        
    finally:
        clear_scraping_state()
        session.close()
        await chrome.close()
    
    print(f"\n[SUCCESS] Scraped and saved {saved_count} new cases to MO database.")


def main():
    """Entry point for command-line usage."""
    import sys
    
    if len(sys.argv) == 1:
        county_name = "all"
        start_date = "01/01/2025"
        continue_search = "continue"
        filter_case_type = "all"
        print("Using default settings for test run:")
        print(f"  County: {county_name}")
        print(f"  Start Date: {start_date}")
        print(f"  Continue Search: {continue_search}")
        print(f"  Filter Case Type: {filter_case_type}")
    elif len(sys.argv) < 3 or len(sys.argv) > 5:
        print("Usage: python fetch_mo_cases_pydoll.py [CountyName] [StartDate] [continue|no] [filter_case_type]")
        sys.exit(1)
    else:
        county_name = sys.argv[1]
        start_date = sys.argv[2]
        continue_search = sys.argv[3] if len(sys.argv) > 3 else "no"
        filter_case_type = sys.argv[4] if len(sys.argv) > 4 else "all"
    
    asyncio.run(scrape_court_cases_pydoll(
        county_name=county_name,
        start_date=start_date,
        continue_search=continue_search,
        filter_case_type=filter_case_type
    ))


if __name__ == "__main__":
    main()
