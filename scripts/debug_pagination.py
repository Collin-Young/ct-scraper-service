from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from ct_scraper.scrape_cases import CaseScraper, BASE_URL
from ct_scraper.towns import TOWNS

def main():
    town = "Hartford"
    with CaseScraper(headless=True) as scraper:
        driver = scraper.driver
        wait = scraper.wait
        driver.get(BASE_URL)
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtCityTown")))
        city = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtCityTown")
        city.clear()
        city.send_keys(town)
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnSubmit").click()
        page = 1
        while True:
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_gvPropertyResults")))
            rows = driver.find_elements(By.XPATH, "//a[contains(@id,'hlnkDocketNo')]")
            print(f"Page {page}: {len(rows)} dockets")
            next_candidates = driver.find_elements(By.XPATH, "//a[contains(text(),'Next')]")
            print(f"Next candidates count: {len(next_candidates)}")
            for cand in next_candidates:
                print(" candidate text:", cand.text)
            if next_candidates:
                next_candidates[0].click()
                page += 1
            else:
                break

if __name__ == "__main__":
    main()
