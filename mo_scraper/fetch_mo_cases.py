from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd
import time
import os
import uuid
from datetime import datetime, timedelta
import json
import sys
from mo_scraper.database import init_db, get_session
from mo_scraper.models import Case, Party

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DEBUG_DIR = os.path.join(BASE_DIR, 'debug_artifacts')
BLOCK_PAGE_PATTERNS = (
    'verify you are a human',
    'checking your browser',
    'just a moment',
    'attention required',
    'enable javascript to use',
    'access denied'
)


def get_driver(headless):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    proxy_url = os.environ.get("MO_SCRAPER_PROXY")
    if proxy_url:
        chrome_options.add_argument(f"--proxy-server={proxy_url}")
        print(f"[DEBUG] Routing traffic through proxy: {proxy_url}")

    # Add unique user data dir to avoid session conflicts
    headless_flag = headless.lower() == "headless"
    forced_profile_dir = os.environ.get("MO_SCRAPER_PROFILE_DIR")
    if forced_profile_dir:
        user_data_dir = forced_profile_dir
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        print(f"[DEBUG] Using supplied user data dir: {user_data_dir}")
    elif headless_flag:
        unique_token = f"{os.getpid()}_{int(time.time())}_{uuid.uuid4().hex}"
        user_data_dir = f"/tmp/chrome_profile_{unique_token}"
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        print(f"[DEBUG] Using unique user data dir: {user_data_dir}")
    if headless_flag:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        print("Running in headless mode.")
    else:
        print("Running in non-headless mode.")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": '''
                Object.defineProperty(navigator, "webdriver", {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, "languages", { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3] });
            '''
        },
    )
    driver.set_page_load_timeout(60)
    return driver

def scrape_party_details(driver, url):
    try:
        print(f"[SEARCH] Accessing URL: {url}")
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "mainContent"))
        )

        # Kill transitions for rendering stability
        driver.execute_script("""
            var css = '* { -webkit-transition: none !important; transition: none !important; }';
            var style = document.createElement('style');
            style.type = 'text/css';
            style.appendChild(document.createTextNode(css));
            document.head.appendChild(style);
        """)

        # Click the tab
        parties_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Parties & Attorneys"))
        )
        parties_tab.click()

        # Wait until a party card div appears inside the container
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='actualPartytData']/div"))
        )
        print("[SUCCESS] Party cards loaded successfully")

        party_data_container = driver.find_element(By.ID, "actualPartytData")
        cards = party_data_container.find_elements(By.XPATH, "./div")
        if not cards:
            print("[ERROR] No party cards found.")
            return []

        refined_data = []
        for idx, card in enumerate(cards, start=1):
            try:
                attorney_present = False
                party_container = card

                nested_containers = card.find_elements(By.XPATH, "./div")
                if nested_containers:
                    row_container = card.find_element(By.XPATH, "./div")
                    child_divs = row_container.find_elements(By.XPATH, "./div")
                    if len(child_divs) >= 2:
                        party_container = child_divs[0]
                        attorney_present = True
                    elif child_divs:
                        party_container = child_divs[0]

                party_name = party_container.find_element(By.XPATH, "./p[1]/span[1]").text.strip()
                party_type = party_container.find_element(By.XPATH, "./p[1]/span[2]").text.strip()
                party_address = party_container.find_element(By.XPATH, "./p[2]").text.strip()

                refined_data.append({
                    "Name": party_name,
                    "Party Role": party_type,
                    "Address": party_address,
                    "Has Attorney": attorney_present
                })
            except Exception as e:
                print(f"[WARNING] Error extracting details from card {idx}: {e}")

        return refined_data

    except Exception as e:
        print(f"[ERROR] scraping URL {url}: {e}")
        return []


def dump_debug_artifacts(driver, label):
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{label}"
        screenshot_path = os.path.join(DEBUG_DIR, f"{base_name}.png")
        html_path = os.path.join(DEBUG_DIR, f"{base_name}.html")
        driver.save_screenshot(screenshot_path)
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(driver.page_source)
        print(f"[DEBUG] Saved debug artifacts to {screenshot_path} and {html_path}")
    except Exception as debug_error:
        print(f"[WARN] Unable to persist debug artifacts: {debug_error}")


def is_block_page(page_source):
    lowered = page_source.lower()
    return any(pattern in lowered for pattern in BLOCK_PAGE_PATTERNS)


def ensure_search_form_ready(driver, wait, label):
    try:
        wait.until(lambda drv: drv.execute_script("return document.readyState") == "complete")
        wait.until(EC.presence_of_element_located((By.ID, "mainContent")))
        wait.until(EC.visibility_of_element_located((By.ID, "courtCode")))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#courtCode option[value]")))
        wait.until(EC.element_to_be_clickable((By.ID, "findButton")))
        return True
    except TimeoutException as exc:
        print("[TIMEOUT] Search form did not become ready in time.")
        dump_debug_artifacts(driver, f"form_ready_{label}")
        raise exc

def scrape_court_cases_and_parties(county_name, start_date, continue_search="no", headless="no", filter_case_type="all"):
    init_db()
    session = get_session()
    url = "https://www.courts.mo.gov/cnet/filingDateSearch.do?newSearch=Y"
    driver = get_driver(headless)
    wait = WebDriverWait(driver, 30)

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
        if len(matching_counties) > 1:
            print(f"Multiple counties match '{county_name}': {matching_counties}. Using the first one.")
        counties_to_scrape = [matching_counties[0]]

    case_keywords = []
    if filter_case_type != "all":
        CASE_TYPES_FILE = os.path.join(STATIC_DIR, "case_types.json")
        with open(CASE_TYPES_FILE, "r") as f:
            case_types_data = json.load(f)
        case_keywords = case_types_data.get(filter_case_type, [])

    saved_count = 0
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
                driver.get(url)
                try:
                    ensure_search_form_ready(driver, wait, f"{form_label}_attempt{attempt_num}")
                    form_ready = True
                    print("[DEBUG] Search form ready")
                    break
                except TimeoutException as timeout_exc:
                    page_source = driver.page_source
                    if is_block_page(page_source):
                        print("[WARN] Potential block page detected. Waiting 15 seconds before retry.")
                        time.sleep(15)
                    else:
                        print(f"[WARN] Search form still loading (attempt {attempt_num}): {timeout_exc}")
                        time.sleep(5)
                    if attempt == 2:
                        dump_debug_artifacts(driver, f"form_load_failed_{form_label}")
            if not form_ready:
                print(f"[ERROR] Unable to load search form for {county} on {county_start_date}.")
                break

            extracted_cases = []
            try:
                select_success = False
                for select_attempt in range(3):
                    try:
                        wait.until(EC.element_to_be_clickable((By.ID, "courtCode")))
                        Select(driver.find_element(By.ID, "courtCode")).select_by_visible_text(county)
                        select_success = True
                        print("[DEBUG] County selected")
                        time.sleep(2)
                        break
                    except (NoSuchElementException, StaleElementReferenceException) as select_error:
                        print(f"[WARN] Retrying county selection ({select_attempt + 1}/3): {select_error}")
                        time.sleep(2)
                if not select_success:
                    print(f"[ERROR] Unable to select county {county}.")
                    dump_debug_artifacts(driver, f"county_select_{form_label}")
                    break

                date_input = wait.until(EC.presence_of_element_located((By.ID, "datepicker")))
                print(f"[DEBUG] Date input found with ID: {date_input.get_attribute('id')}")
                print(f"[DEBUG] Initial readonly attribute: {date_input.get_attribute('readonly')}")

                driver.execute_script("arguments[0].removeAttribute('readonly')", date_input)
                print(f"[DEBUG] Readonly after removal: {date_input.get_attribute('readonly')}")

                driver.execute_script("arguments[0].click();", date_input)
                time.sleep(1)
                print("[DEBUG] Clicked date input to open calendar")

                try:
                    picker_holder = driver.find_element(By.CSS_SELECTOR, ".picker__holder")
                    print(f"[DEBUG] Picker holder visible after click: {picker_holder.is_displayed()}")
                except Exception:
                    print("[DEBUG] Picker holder not found after click")

                date_input.clear()
                date_input.send_keys(county_start_date)
                time.sleep(1)
                print(f"[DEBUG] Sent keys: {county_start_date}")
                print(f"[DEBUG] Input value after send_keys: {date_input.get_attribute('value')}")

                driver.find_element(By.TAG_NAME, "body").click()
                print("[DEBUG] Clicked body to close any picker")
                print("[DEBUG] Date entered")

                try:
                    picker_holder = driver.find_element(By.CSS_SELECTOR, ".picker__holder")
                    print(f"[DEBUG] Picker holder visible after input: {picker_holder.is_displayed()}")
                except Exception:
                    print("[DEBUG] Picker holder not found after input")

                try:
                    driver.execute_script("document.querySelector('.picker__holder').style.display='none';")
                except Exception:
                    pass

                find_button = driver.find_element(By.ID, "findButton")
                driver.execute_script("arguments[0].scrollIntoView();", find_button)
                find_button.click()
                print(f"[DEBUG] Find button clicked for {county_start_date}")
                time.sleep(3)

                wait.until(EC.element_to_be_clickable((By.NAME, "searchResult_length")))
                Select(driver.find_element(By.NAME, "searchResult_length")).select_by_value("100")
                time.sleep(1)

                while True:
                    case_table = wait.until(EC.presence_of_element_located((By.ID, "searchResult")))
                    rows = case_table.find_elements(By.TAG_NAME, "tr")

                    for row in rows[1:]:
                        columns = row.find_elements(By.TAG_NAME, "td")
                        if len(columns) > 5:
                            case_type = columns[4].text.strip()
                            if not case_keywords or any(keyword.lower() in case_type.lower() for keyword in case_keywords):
                                case_number_element = columns[2].find_element(By.TAG_NAME, "a")
                                case_number = case_number_element.text.strip()
                                href = case_number_element.get_attribute("href")
                                case_url = "https://www.courts.mo.gov" + href.replace("https://www.courts.mo.gov", "")
                                case_entry = {
                                    "date_filed": columns[1].text.strip(),
                                    "case_number": case_number,
                                    "case_url": case_url,
                                    "style_of_case": columns[3].text.strip(),
                                    "case_type": case_type,
                                    "location": columns[5].text.strip()
                                }
                                print(f"Found: {case_number} ({case_type})")
                                extracted_cases.append(case_entry)

                    try:
                        next_button = driver.find_element(By.ID, "searchResult_next")
                        if "disabled" in next_button.get_attribute("class"):
                            print("No more pages.")
                            break
                        wait.until(EC.element_to_be_clickable((By.ID, "searchResult_next")))
                        wait.until(EC.visibility_of(next_button))
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                        time.sleep(1)
                        next_button.click()
                        wait.until(EC.presence_of_element_located((By.ID, "searchResult")))
                        time.sleep(2)
                    except Exception as e:
                        print(f"Pagination error: {e}")
                        break
            except TimeoutException as e:
                print(f"[TIMEOUT] Element not found for {county_start_date}: {e}")
            except Exception as e:
                print(f"[ERROR] Unexpected error for {county_start_date}: {e}")
            if len(extracted_cases) > 0:
                consecutive_no_cases = 0
                print(f"Found {len(extracted_cases)} cases for {county_start_date}")
                # Now scrape party details for each case
                for case_entry in extracted_cases:
                    party_details = scrape_party_details(driver, case_entry['case_url'])
                    # Check if case already exists
                    existing_case = session.query(Case).filter_by(case_number=case_entry['case_number']).first()
                    if existing_case:
                        print(f"Case {case_entry['case_number']} already exists, skipping.")
                        continue
                    try:
                        new_case = Case(**case_entry)
                        session.add(new_case)
                        session.commit()
                        case_id = new_case.id
                        for i, party in enumerate(party_details, start=1):
                            if i > 10:
                                break
                            if party['Name']:
                                new_party = Party(
                                    case_id=case_id,
                                    party_index=i,
                                    name=party['Name'],
                                    role=party['Party Role'],
                                    address=party['Address'],
                                    has_attorney=party['Has Attorney']
                                )
                                session.add(new_party)
                        session.commit()
                        saved_count += 1
                        print(f"Saved case {case_entry['case_number']} with {len(party_details)} parties.")
                    except Exception as e:
                        session.rollback()
                        print(f"Error saving case {case_entry['case_number']}: {e}")
            else:
                consecutive_no_cases += 1
                print(f"No cases found for {county_start_date}")
            if consecutive_no_cases > max_consecutive_no_cases:
                print("No cases found for several consecutive dates. Stopping.")
                break

            if continue_search == 'continue':
                print(f"Updating to next date from {county_start_date}")
                try:
                    dt = datetime.strptime(county_start_date, '%m/%d/%Y')
                    next_dt = dt - timedelta(days=7)
                    if next_dt < datetime.today() - timedelta(days=365):
                        print("Reached 1 year back. Stopping.")
                        break
                    county_start_date = next_dt.strftime('%m/%d/%Y')
                    print(f"Next date: {county_start_date}")
                except Exception as e:
                    print(f"Date update error: {e}")
                    break
            else:
                break

    session.close()
    driver.quit()
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
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

