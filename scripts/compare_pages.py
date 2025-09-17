from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from ct_scraper.scrape_cases import CaseScraper, BASE_URL


def main():
    with CaseScraper(headless=True) as scraper:
        driver = scraper.driver
        wait = scraper.wait
        town = "Hartford"
        driver.get(BASE_URL)
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtCityTown")))
        city = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtCityTown")
        city.clear()
        city.send_keys(town)
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnSubmit").click()
        wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_gvPropertyResults")))
        first_page = [elem.text for elem in driver.find_elements(By.XPATH, "//a[contains(@id,'hlnkDocketNo')]")[:5]]
        driver.find_element(By.XPATH, "//a[@href=\"javascript:__doPostBack('ctl00$ContentPlaceHolder1$gvPropertyResults','Page$2')\"]").click()
        wait.until(EC.presence_of_element_located((By.XPATH, "//table[@id='ctl00_ContentPlaceHolder1_gvPropertyResults']//span[text()='2']")))
        second_page = [elem.text for elem in driver.find_elements(By.XPATH, "//a[contains(@id,'hlnkDocketNo')]")[:5]]
        print('first page first 5:', first_page)
        print('second page first 5:', second_page)

if __name__ == '__main__':
    main()
