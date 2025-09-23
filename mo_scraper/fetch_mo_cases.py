from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

import pandas as pd
import time
import os
from datetime import datetime, timedelta
import json
import sys
from mo_scraper.database import init_db, get_session
from mo_scraper.models import Case, Party

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

def get_driver(headless):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    if headless.lower() == 'headless':
        chrome_options.add_argument("--headless")
        print("Running in headless mode.")
    else:
        print("Running in non-headless mode.")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

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

def scrape_court_cases_and_parties(county_name, start_date, continue_search="no", headless="no", filter_case_type="all"):
    init_db()
    session = get_session()
    url = "https://www.courts.mo.gov/cnet/filingDateSearch.do?newSearch=Y"
    driver = get_driver(headless)
    wait = WebDriverWait(driver, 20)

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
            driver.get(url)
            time.sleep(5)  # Wait for page to fully load
            print("[DEBUG] Page loaded")
            extracted_cases = []
            try:
                wait.until(EC.presence_of_element_located((By.ID, "courtCode")))
                print("[DEBUG] CourtCode element found")
                Select(driver.find_element(By.ID, "courtCode")).select_by_visible_text(county)
                print("[DEBUG] County selected")
                time.sleep(2)

                date_input = driver.find_element(By.ID, "datepicker")
                driver.execute_script("arguments[0].removeAttribute('readonly')", date_input)
                date_input.clear()
                date_input.send_keys(county_start_date)
                time.sleep(1)
                driver.find_element(By.TAG_NAME, "body").click()
                print("[DEBUG] Date entered")
                try:
                    driver.execute_script("document.querySelector('.picker__holder').style.display='none';")
                except:
                    pass

                find_button = driver.find_element(By.ID, "findButton")
                driver.execute_script("arguments[0].scrollIntoView();", find_button)
                find_button.click()
                print(f"[DEBUG] Find button clicked for {county_start_date}")
                time.sleep(3)

                wait.until(EC.element_to_be_clickable((By.NAME, "searchResult_length")))
                Select(driver.find_element(By.NAME, "searchResult_length")).select_by_value("100")
                time.sleep(1)  # Just a nudge to ensure the table loads

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