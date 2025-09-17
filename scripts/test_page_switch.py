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
        pager = driver.find_element(By.XPATH, "//table[@id='ctl00_ContentPlaceHolder1_gvPropertyResults']/tbody/tr[last()]/td/table/tbody/tr")
        print('pager html before:', pager.get_attribute('innerHTML'))
        next_link = driver.find_element(By.XPATH, "//a[@href=\"javascript:__doPostBack('ctl00$ContentPlaceHolder1$gvPropertyResults','Page$2')\"]")
        next_link.click()
        wait.until(EC.presence_of_element_located((By.XPATH, "//table[@id='ctl00_ContentPlaceHolder1_gvPropertyResults']/tbody/tr[last()]/td/table/tbody/tr//span[text()='2']")))
        pager_after = driver.find_element(By.XPATH, "//table[@id='ctl00_ContentPlaceHolder1_gvPropertyResults']/tbody/tr[last()]/td/table/tbody/tr")
        print('pager after:', pager_after.get_attribute('innerHTML'))

if __name__ == '__main__':
    main()
