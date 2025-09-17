from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from ct_scraper.scrape_cases import CaseScraper, BASE_URL

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
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_gvPropertyResults")))
        html = driver.page_source
        Path('hartford_page.html').write_text(html, encoding='utf-8')

if __name__ == '__main__':
    from pathlib import Path
    main()
