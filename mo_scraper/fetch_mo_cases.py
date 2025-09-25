import os
import time
import random
import json
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pandas as pd
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Page,
)

from mo_scraper.database import init_db, get_session
from mo_scraper.models import Case, Party

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DEBUG_DIR = os.path.join(BASE_DIR, "debug_artifacts")
DEFAULT_PROFILE_DIR = os.path.join(BASE_DIR, "playwright_profile")
PROFILE_DIR = os.path.abspath(os.environ.get("MO_SCRAPER_PROFILE_DIR", DEFAULT_PROFILE_DIR))
STORAGE_STATE_PATH = os.path.join(PROFILE_DIR, "storage_state.json")
SEARCH_URL = "https://www.courts.mo.gov/cnet/filingDateSearch.do?newSearch=Y"
BLOCK_PAGE_PATTERNS = (
    "verify you are a human",
    "checking your browser",
    "just a moment",
    "attention required",
    "enable javascript to use",
    "access denied",
)


def _read_delay(var_name: str, default: float) -> float:
    try:
        return float(os.environ.get(var_name, default))
    except (TypeError, ValueError):
        return default


MIN_DELAY = _read_delay("MO_SCRAPER_MIN_WAIT", 0.75)
MAX_DELAY = _read_delay("MO_SCRAPER_MAX_WAIT", 1.35)


def gentle_wait(min_delay: float | None = None, max_delay: float | None = None) -> None:
    lower = min_delay if min_delay is not None else MIN_DELAY
    upper = max_delay if max_delay is not None else MAX_DELAY
    if upper < lower:
        upper = lower
    time.sleep(random.uniform(lower, upper))


def ensure_directories() -> None:
    os.makedirs(DEBUG_DIR, exist_ok=True)
    os.makedirs(PROFILE_DIR, exist_ok=True)


def get_browser_context(headless: str):
    ensure_directories()
    headless_flag = headless.lower() == "headless"
    playwright = sync_playwright().start()

    launch_args = [
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--lang=en-US",
        "--window-size=1920,1080",
    ]

    proxy_setting = None
    proxy_url = os.environ.get("MO_SCRAPER_PROXY")
    if proxy_url:
        proxy_arg = proxy_url if "://" in proxy_url else f"http://{proxy_url}"
        parsed_proxy = urlparse(proxy_arg)
        if parsed_proxy.hostname:
            proxy_server = f"{parsed_proxy.scheme or 'http'}://{parsed_proxy.hostname}"
            if parsed_proxy.port:
                proxy_server += f":{parsed_proxy.port}"
        else:
            proxy_server = proxy_arg
        proxy_setting = {"server": proxy_server}
        if parsed_proxy.username:
            proxy_setting["username"] = parsed_proxy.username
        if parsed_proxy.password:
            proxy_setting["password"] = parsed_proxy.password
        print(f"[DEBUG] Routing traffic through proxy: {proxy_server}")

    browser = playwright.chromium.launch(headless=headless_flag, args=launch_args, proxy=proxy_setting)

    context_kwargs = {
        "locale": "en-US",
        "timezone_id": "America/Chicago",
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "extra_http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    if os.path.exists(STORAGE_STATE_PATH):
        context_kwargs["storage_state"] = STORAGE_STATE_PATH
        print(f"[DEBUG] Re-using storage state from {STORAGE_STATE_PATH}")

    context = browser.new_context(**context_kwargs)
    context.set_default_timeout(30000)
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    page = context.new_page()
    page.set_default_timeout(30000)
    return playwright, browser, context, page


def dump_debug_artifacts(page: Page, label: str) -> None:
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{label}"
        screenshot_path = os.path.join(DEBUG_DIR, f"{base_name}.png")
        html_path = os.path.join(DEBUG_DIR, f"{base_name}.html")
        page.screenshot(path=screenshot_path, full_page=True)
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(page.content())
        print(f"[DEBUG] Saved debug artifacts to {screenshot_path} and {html_path}")
    except Exception as debug_error:
        print(f"[WARN] Unable to persist debug artifacts: {debug_error}")


def is_block_page(page_source: str) -> bool:
    lowered = page_source.lower()
    return any(pattern in lowered for pattern in BLOCK_PAGE_PATTERNS)


def ensure_search_form_ready(page: Page, label: str) -> bool:
    try:
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_selector("#mainContent", state="visible", timeout=15000)
        page.wait_for_selector("#courtCode", state="visible", timeout=15000)
        page.wait_for_selector("#courtCode option[value]", timeout=15000)
        page.wait_for_selector("#findButton", state="visible", timeout=15000)
        return True
    except PlaywrightTimeoutError:
        print("[TIMEOUT] Search form did not become ready in time.")
        dump_debug_artifacts(page, f"form_ready_{label}")
        raise


def fill_date_input(page: Page, date_str: str) -> None:
    date_input = page.wait_for_selector("#datepicker", timeout=15000)
    date_input.click()
    page.fill("#datepicker", "")
    gentle_wait(0.1, 0.2)
    page.type("#datepicker", date_str, delay=75)
    gentle_wait(0.2, 0.4)
    page.click("body", position={"x": 5, "y": 5})


def scrape_party_details(context, url: str) -> list[dict[str, str]]:
    for attempt in range(2):
        detail_page = context.new_page()
        try:
            print(f"[SEARCH] Accessing URL: {url}")
            detail_page.goto(url, wait_until="domcontentloaded", timeout=45000)
            gentle_wait(0.8, 1.2)

            page_source = detail_page.content()
            if is_block_page(page_source):
                print("[WARN] Block page detected while fetching party details.")
                dump_debug_artifacts(detail_page, "party_block")
                gentle_wait(10, 12)
                continue

            detail_page.wait_for_selector("#mainContent", state="visible", timeout=15000)
            detail_page.evaluate("""
                (function() {
                    var css = '* { transition: none !important; }';
                    var style = document.createElement('style');
                    style.type = 'text/css';
                    style.appendChild(document.createTextNode(css));
                    document.head.appendChild(style);
                })();
            """)

            parties_tab = detail_page.wait_for_selector("text=Parties & Attorneys", timeout=15000)
            parties_tab.click()
            gentle_wait(0.5, 0.9)

            detail_page.wait_for_selector("#actualPartytData > div", timeout=15000)
            print("[SUCCESS] Party cards loaded successfully")

            cards = detail_page.query_selector_all("#actualPartytData > div")
            if not cards:
                print("[ERROR] No party cards found.")
                return []

            refined_data: list[dict[str, str]] = []
            for idx, card in enumerate(cards, start=1):
                try:
                    attorney_present = False
                    party_container = card

                    nested_containers = card.query_selector_all(":scope > div")
                    if nested_containers:
                        row_container = nested_containers[0]
                        child_divs = row_container.query_selector_all(":scope > div")
                        if len(child_divs) >= 2:
                            party_container = child_divs[0]
                            attorney_present = True
                        elif child_divs:
                            party_container = child_divs[0]

                    name_el = party_container.query_selector("css=p:nth-of-type(1) span:nth-of-type(1)")
                    type_el = party_container.query_selector("css=p:nth-of-type(1) span:nth-of-type(2)")
                    address_el = party_container.query_selector("css=p:nth-of-type(2)")

                    party_name = name_el.inner_text().strip() if name_el else ""
                    party_type = type_el.inner_text().strip() if type_el else ""
                    party_address = address_el.inner_text().strip() if address_el else ""

                    refined_data.append({
                        "Name": party_name,
                        "Party Role": party_type,
                        "Address": party_address,
                        "Has Attorney": attorney_present,
                    })
                except Exception as inner_error:
                    print(f"[WARNING] Error extracting details from card {idx}: {inner_error}")

            return refined_data
        except PlaywrightTimeoutError as exc:
            print(f"[TIMEOUT] scraping URL {url}: {exc}")
            dump_debug_artifacts(detail_page, "party_timeout")
        except Exception as exc:
            print(f"[ERROR] scraping URL {url}: {exc}")
            dump_debug_artifacts(detail_page, "party_error")
        finally:
            detail_page.close()
        gentle_wait(4, 6)
    return []


def scrape_court_cases_and_parties(county_name, start_date, continue_search="no", headless="no", filter_case_type="all"):
    ensure_directories()
    init_db()
    session = get_session()
    playwright, browser, context, page = get_browser_context(headless)

    dropdown_path = os.path.join(STATIC_DIR, "dropdown_options.json")
    dropdown_df = pd.read_json(dropdown_path)
    if county_name.lower() == "all":
        counties_to_scrape = [
            option["text"]
            for option in dropdown_df.to_dict(orient="records")
            if option["text"].lower() != "please select..."
        ]
    else:
        matching_counties = [
            option["text"]
            for option in dropdown_df.to_dict(orient="records")
            if county_name.lower() in option["text"].lower()
        ]
        if not matching_counties:
            raise ValueError(f"No county found matching '{county_name}' in dropdown options.")
        if len(matching_counties) > 1:
            print(f"Multiple counties match '{county_name}': {matching_counties}. Using the first one.")
        counties_to_scrape = [matching_counties[0]]

    case_keywords: list[str] = []
    if filter_case_type != "all":
        case_types_path = os.path.join(STATIC_DIR, "case_types.json")
        with open(case_types_path, "r", encoding="utf-8") as handle:
            case_types_data = json.load(handle)
        case_keywords = case_types_data.get(filter_case_type, [])

    saved_count = 0
    try:
        for county in counties_to_scrape:
            county_start_date = start_date
            consecutive_no_cases = 0
            max_consecutive_no_cases = 8

            while True:
                print(f"\nScraping data for county: {county}, start date: {county_start_date}")
                form_label = f"{county.replace(' ', '_')}_{county_start_date.replace('/', '-')}"
                form_ready = False
                for attempt in range(3):
                    attempt_num = attempt + 1
                    if attempt == 0:
                        print("[DEBUG] Loading search form")
                    else:
                        print(f"[DEBUG] Reloading search form (attempt {attempt_num})")
                    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=45000)
                    gentle_wait(1.0, 1.4)

                    current_source = page.content()
                    if is_block_page(current_source):
                        print("[WARN] Potential block page detected. Waiting 15 seconds before retry.")
                        dump_debug_artifacts(page, "form_block")
                        gentle_wait(15, 18)
                        continue

                    try:
                        ensure_search_form_ready(page, f"{form_label}_attempt{attempt_num}")
                        form_ready = True
                        print("[DEBUG] Search form ready")
                        break
                    except PlaywrightTimeoutError as timeout_exc:
                        if attempt == 2:
                            dump_debug_artifacts(page, f"form_load_failed_{form_label}")
                        print(f"[WARN] Search form still loading (attempt {attempt_num}): {timeout_exc}")
                        gentle_wait(5, 6)

                if not form_ready:
                    print(f"[ERROR] Unable to load search form for {county} on {county_start_date}.")
                    break

                extracted_cases: list[dict[str, str]] = []
                try:
                    select_success = False
                    for select_attempt in range(3):
                        try:
                            page.wait_for_selector("#courtCode", state="visible", timeout=10000)
                            selected_values = page.select_option("#courtCode", label=county)
                            if not selected_values:
                                raise ValueError("Select returned no value")
                            select_success = True
                            print("[DEBUG] County selected")
                            gentle_wait(0.6, 0.9)
                            break
                        except Exception as select_error:
                            print(f"[WARN] Retrying county selection ({select_attempt + 1}/3): {select_error}")
                            gentle_wait(2, 3)
                    if not select_success:
                        print(f"[ERROR] Unable to select county {county}.")
                        dump_debug_artifacts(page, f"county_select_{form_label}")
                        break

                    fill_date_input(page, county_start_date)
                    print("[DEBUG] Date entered")

                    find_button = page.wait_for_selector("#findButton", state="visible", timeout=10000)
                    find_button.scroll_into_view_if_needed()
                    gentle_wait(0.3, 0.5)
                    find_button.click()
                    print(f"[DEBUG] Find button clicked for {county_start_date}")
                    gentle_wait(2.5, 3.5)

                    page.wait_for_selector("select[name='searchResult_length']", timeout=20000)
                    page.select_option("select[name='searchResult_length']", value="100")
                    gentle_wait(1.0, 1.4)

                    while True:
                        page.wait_for_selector("#searchResult tbody tr", timeout=20000)
                        rows = page.query_selector_all("#searchResult tbody tr")

                        if not rows:
                            print("No cases found on current page.")
                            break

                        for row in rows:
                            columns = row.query_selector_all("td")
                            if len(columns) <= 5:
                                continue
                            case_type = columns[4].inner_text().strip()
                            if case_keywords and not any(keyword.lower() in case_type.lower() for keyword in case_keywords):
                                continue

                            case_number_link = columns[2].query_selector("a")
                            if not case_number_link:
                                continue

                            case_number = case_number_link.inner_text().strip()
                            href = case_number_link.get_attribute("href") or ""
                            if not href:
                                continue

                            if href.startswith("https://www.courts.mo.gov"):
                                case_url = href
                            else:
                                case_url = "https://www.courts.mo.gov" + href

                            case_entry = {
                                "date_filed": columns[1].inner_text().strip(),
                                "case_number": case_number,
                                "case_url": case_url,
                                "style_of_case": columns[3].inner_text().strip(),
                                "case_type": case_type,
                                "location": columns[5].inner_text().strip(),
                            }
                            print(f"Found: {case_number} ({case_type})")
                            extracted_cases.append(case_entry)

                        next_button = page.query_selector("#searchResult_next")
                        if not next_button:
                            break
                        next_button_class = next_button.get_attribute("class") or ""
                        if "disabled" in next_button_class:
                            print("No more pages.")
                            break

                        next_button.scroll_into_view_if_needed()
                        gentle_wait(0.4, 0.6)
                        next_button.click()
                        gentle_wait(2.0, 2.5)

                    if extracted_cases:
                        consecutive_no_cases = 0
                        print(f"Found {len(extracted_cases)} cases for {county_start_date}")
                        for case_entry in extracted_cases:
                            party_details = scrape_party_details(context, case_entry["case_url"])

                            existing_case = session.query(Case).filter_by(case_number=case_entry["case_number"]).first()
                            if existing_case:
                                print(f"Case {case_entry['case_number']} already exists, skipping.")
                                continue

                            try:
                                new_case = Case(**case_entry)
                                session.add(new_case)
                                session.commit()
                                case_id = new_case.id
                                for idx, party in enumerate(party_details, start=1):
                                    if idx > 10:
                                        break
                                    if party.get("Name"):
                                        new_party = Party(
                                            case_id=case_id,
                                            party_index=idx,
                                            name=party.get("Name"),
                                            role=party.get("Party Role"),
                                            address=party.get("Address"),
                                            has_attorney=bool(party.get("Has Attorney")),
                                        )
                                        session.add(new_party)
                                session.commit()
                                saved_count += 1
                                print(f"Saved case {case_entry['case_number']} with {len(party_details)} parties.")
                            except Exception as save_error:
                                session.rollback()
                                print(f"Error saving case {case_entry['case_number']}: {save_error}")
                    else:
                        consecutive_no_cases += 1
                        print(f"No cases found for {county_start_date}")

                    if consecutive_no_cases > max_consecutive_no_cases:
                        print("No cases found for several consecutive dates. Stopping.")
                        break

                    if continue_search == "continue":
                        print(f"Updating to next date from {county_start_date}")
                        try:
                            dt = datetime.strptime(county_start_date, "%m/%d/%Y")
                            next_dt = dt - timedelta(days=7)
                            if next_dt < datetime.today() - timedelta(days=365):
                                print("Reached 1 year back. Stopping.")
                                break
                            county_start_date = next_dt.strftime("%m/%d/%Y")
                            print(f"Next date: {county_start_date}")
                        except Exception as date_error:
                            print(f"Date update error: {date_error}")
                            break
                    else:
                        break
                except PlaywrightTimeoutError as timeout_exc:
                    print(f"[TIMEOUT] Element not found for {county_start_date}: {timeout_exc}")
                except Exception as unexpected_exc:
                    print(f"[ERROR] Unexpected error for {county_start_date}: {unexpected_exc}")

    finally:
        try:
            session.close()
        finally:
            try:
                context.storage_state(path=STORAGE_STATE_PATH)
                print(f"[DEBUG] Persisted storage state to {STORAGE_STATE_PATH}")
            except Exception as state_error:
                print(f"[WARN] Failed to persist storage state: {state_error}")
            context.close()
            browser.close()
            playwright.stop()

    print(f"\n[SUCCESS] Scraped and saved {saved_count} new cases to MO database.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        county_name = "all"
        start_date = "01/01/2025"
        continue_search = "continue"
        headless = "no"
        filter_case_type = "all"
        print("Using default settings for test run:")
        print(f"  County: {county_name}")
        print(f"  Start Date: {start_date}")
        print(f"  Continue Search: {continue_search}")
        print(f"  Headless: {headless}")
        print(f"  Filter Case Type: {filter_case_type}")
    elif len(sys.argv) < 3 or len(sys.argv) > 6:
        print("Usage: python fetch_mo_cases.py [CountyName] [StartDate] [continue|no] [headless|no] [filter_case_type]")
        sys.exit(1)
    else:
        county_name = sys.argv[1]
        start_date = sys.argv[2]
        continue_search = "no"
        headless = "no"
        filter_case_type = "all"
        if len(sys.argv) >= 4:
            if sys.argv[3].lower() in ["continue", "no"]:
                continue_search = sys.argv[3]
                headless_idx = 4
            else:
                headless_idx = 3
        else:
            headless_idx = 3

        if len(sys.argv) >= headless_idx + 1:
            if sys.argv[headless_idx].lower() == "headless":
                headless = "headless"

        if len(sys.argv) == 6:
            filter_case_type = sys.argv[5]

    try:
        scrape_court_cases_and_parties(county_name, start_date, continue_search, headless, filter_case_type)
    except Exception as exc:
        print(f"Error: {exc}")
        import traceback
        traceback.print_exc()

