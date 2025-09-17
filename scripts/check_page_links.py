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
        links = driver.find_elements(By.XPATH, "//a[contains(@id,'hlnkDocketNo')]")
        hrefs = [lnk.get_attribute("href") for lnk in links]
        print("links count:", len(links))
        print("unique hrefs:", len(set(hrefs)))

if __name__ == '__main__':
    main()
