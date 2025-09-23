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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_driver(headless):
    chrome_options = Options()
    if headless.lower() == 'headless':
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        print("Running in headless mode.")
    else:
        print("Running in non-headless mode.")

    # Use direct path to ChromeDriver to avoid 32/64-bit issues
    chrome_driver_path = r"C:\Users\Collin\.wdm\drivers\chromedriver\win64\140.0.7339.128\chromedriver-win32\chromedriver.exe"
    return webdriver.Chrome(service=Service(chrome_driver_path), options=chrome_options)

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
    url = "https://www.courts.mo.gov/cnet/filingDateSearch.do?newSearch=Y"
    driver = get_driver(headless)
    wait = WebDriverWait(driver, 20)

    DROPDOWN_OPTIONS_FILE = os.path.join(BASE_DIR, "static", "dropdown_options.json")
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
        CASE_TYPES_FILE = os.path.join(BASE_DIR, "static", "case_types.json")
        with open(CASE_TYPES_FILE, "r") as f:
            case_types_data = json.load(f)
        case_keywords = case_types_data.get(filter_case_type, [])

    all_results = []
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
                                    "Date Filed": columns[1].text.strip(),
                                    "Case Number": case_number,
                                    "Case URL": case_url,
                                    "Style of Case": columns[3].text.strip(),
                                    "Case Type": case_type,
                                    "Location": columns[5].text.strip()
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
                for case in extracted_cases:
                    party_details = scrape_party_details(driver, case["Case URL"])
                    result_row = case.copy()
                    for i, party in enumerate(party_details, start=1):
                        result_row[f"Party Name {i}"] = party.get("Name", "")
                        result_row[f"Party Role {i}"] = party.get("Party Role", "")
                        result_row[f"Party Address {i}"] = party.get("Address", "")
                        result_row[f"Has Attorney {i}"] = party.get("Has Attorney", False)
                    all_results.append(result_row)
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

    # Output
    if all_results:
        output_df = pd.DataFrame(all_results)
        output_dir = r"C:\Users\Collin\Documents\court case scraper\output data"
        os.makedirs(output_dir, exist_ok=True)
        output_file_name = f"test_merged_cases_parties_{int(time.time())}.csv"
        output_file_path = os.path.join(output_dir, output_file_name)
        output_df.to_csv(output_file_path, index=False)
        print(f"\n[SUCCESS] Scraped data saved to:\n'{output_file_path}'")
    else:
        print("No matching cases found.")

    driver.quit()
    print("\nScraper finished successfully!")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        county_name = "Adair"
        start_date = "09/17/2025"
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
        print("Usage: python fetch_cases_with_parties.py [CountyName] [StartDate] [continue|no] [headless] [filter_case_type]")
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