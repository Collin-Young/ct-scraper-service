"""High-level scraper facade."""
from __future__ import annotations

import random
import re
import time
import tempfile
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional
from urllib.parse import parse_qs, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import chromedriver_autoinstaller
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "https://civilinquiry.jud.ct.gov/PropertyAddressSearch.aspx"
ROLE_RE = re.compile(r"^[PD]-\d{1,2}$", re.IGNORECASE)


def pause(a: float = 0.2, b: float = 0.6) -> None:
    time.sleep(random.uniform(a, b))


@dataclass
class CaseRow:
    town: str
    docket_link: str
    case_type: str
    court_location: str
    property_address: str
    list_type: str
    trial_list_claim: str
    last_action_date: str
    parties: List[Dict[str, str]]


class CaseScraper:
    """Wrap Selenium scraping so workers can call into it."""

    def __init__(self, *, headless: bool = True, driver_path: Optional[str] = None) -> None:
        self.headless = headless
        self.driver_path = driver_path
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self._profile_dir: Optional[str] = None

    def __enter__(self) -> "CaseScraper":
        self.driver = self._build_driver()
        self.wait = WebDriverWait(self.driver, 12)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
        if self._profile_dir:
            shutil.rmtree(self._profile_dir, ignore_errors=True)
            self._profile_dir = None

    def _build_driver(self) -> webdriver.Chrome:
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1366,768")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        binary = (shutil.which("google-chrome") or shutil.which("google-chrome-stable") or shutil.which("chromium-browser") or shutil.which("chromium"))
        if binary:
            chrome_options.binary_location = binary

        self._profile_dir = tempfile.mkdtemp(prefix="chrome-profile-")
        chrome_options.add_argument(f"--user-data-dir={self._profile_dir}")
        chrome_options.add_argument("--remote-debugging-port=0")

        driver_exec = self.driver_path
        if not driver_exec:
            try:
                driver_exec = chromedriver_autoinstaller.install()
            except Exception:
                driver_exec = shutil.which("chromium.chromedriver") or shutil.which("chromedriver")

        service = Service(driver_exec) if driver_exec else Service()
        return webdriver.Chrome(service=service, options=chrome_options)

    @contextmanager
    def _new_tab(self, href: str) -> Iterator[None]:
        assert self.driver is not None
        self.driver.execute_script("window.open(arguments[0], '_blank');", href)
        self.driver.switch_to.window(self.driver.window_handles[-1])
        try:
            yield
        finally:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

    # ---------- Public API ----------
    def scrape_towns(self, towns: Iterable[str]) -> Iterator[CaseRow]:
        assert self.driver is not None and self.wait is not None
        driver = self.driver
        wait = self.wait

        for town in towns:
            driver.get(BASE_URL)
            wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtCityTown")))
            city = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtCityTown")
            city.clear()
            city.send_keys(town)
            pause()
            driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnSubmit").click()
            pause()

            while True:
                try:
                    wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_gvPropertyResults")))
                except Exception:
                    break

                links = driver.find_elements(By.XPATH, "//a[contains(@id,'hlnkDocketNo')]")
                hrefs = [lnk.get_attribute("href") for lnk in links]

                for href in hrefs:
                    with self._new_tab(href):
                        pause()
                        yield self._build_case_row(town)
                        pause()

                next_candidates = driver.find_elements(
                    By.XPATH,
                    "//a[contains(normalize-space(.), 'Next')]",
                )
                if next_candidates:
                    marker = links[0] if links else driver.find_element(By.TAG_NAME, "body")
                    next_candidates[0].click()
                    try:
                        wait.until(EC.staleness_of(marker))
                    except Exception:
                        pause(0.6, 1.0)
                else:
                    break

    # ---------- Helpers ----------
    def _build_case_row(self, town: str) -> CaseRow:
        case_info = self._parse_case_info()
        parties = self._parse_parties()
        docket_link = self._make_docket_link_from_page()
        return CaseRow(
            town=town,
            docket_link=docket_link,
            case_type=case_info.get("Case Type", ""),
            court_location=case_info.get("Court Location", ""),
            property_address=case_info.get("Property Address", ""),
            list_type=case_info.get("List Type", ""),
            trial_list_claim=case_info.get("Trial List Claim", ""),
            last_action_date=case_info.get("Last Action Date", ""),
            parties=parties,
        )

    def _parse_case_info(self) -> Dict[str, str]:
        assert self.wait is not None
        wait = self.wait
        info = {
            "Case Type": "",
            "Court Location": "",
            "Property Address": "",
            "List Type": "",
            "Trial List Claim": "",
            "Last Action Date": "",
        }
        tbl = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[@id='ctl00_ContentPlaceHolder1_CaseDetailBasicInfo1_pnlCVInfo']")
            )
        )
        rows = tbl.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 2:
                key = cells[0].text.strip().rstrip(":")
                val = cells[1].text.strip()
                if key in info:
                    info[key] = val
        return info

    def _parse_parties(self) -> List[Dict[str, str]]:
        assert self.wait is not None
        wait = self.wait
        parties: List[Dict[str, str]] = []
        current: Optional[Dict[str, str]] = None

        tbody = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[@id='ctl00_ContentPlaceHolder1_CaseDetailParties1_pnlParties']/table/tbody/tr[2]/td/table/tbody",
                )
            )
        )
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if not tds:
                continue
            first = tds[0].text.strip()
            second = tds[1].text.strip() if len(tds) > 1 else ""
            third = tds[2].text.strip() if len(tds) > 2 else ""

            if ROLE_RE.match(first):
                if current:
                    parties.append(current)
                current = {
                    "role": first,
                    "name": second,
                    "attorney": "",
                    "address": "",
                    "file_date": third,
                }
            elif current:
                if first.lower().startswith("attorney"):
                    current["attorney"] = second or third
                elif first.lower().startswith("address"):
                    current["address"] = " ".join(filter(None, [second, third])).strip()
                elif first.lower().startswith("appearance attorney"):
                    current["attorney"] = second or third
                elif first.lower().startswith("filed"):
                    current["file_date"] = second or third
                elif not second and ROLE_RE.match(first):
                    # fallback new role row with empty cells
                    parties.append(current)
                    current = {
                        "role": first,
                        "name": third,
                        "attorney": "",
                        "address": "",
                        "file_date": "",
                    }
        if current:
            parties.append(current)

        defendants = [p for p in parties if p["role"].upper().startswith("D-")]
        plaintiffs = [p for p in parties if p["role"].upper().startswith("P-")]
        ordered = defendants + plaintiffs
        return ordered[:10]

    def _make_docket_link_from_page(self) -> str:
        assert self.driver is not None
        driver = self.driver
        docket_no = ""
        try:
            d_elem = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_CaseDetailBasicInfo1_lblDocketNo")
            docket_no = d_elem.text.strip()
        except Exception:
            pass
        if not docket_no:
            try:
                qs = parse_qs(urlparse(driver.current_url).query)
                docket_no = qs.get("DocketNo", [""])[0]
            except Exception:
                docket_no = ""
        if docket_no:
            return (
                f'=HYPERLINK("https://civilinquiry.jud.ct.gov/CaseDetail.aspx?DocketNo={docket_no}", '
                f'"{docket_no}")'
            )
        return ""


import datetime
def scrape_cases(towns: Iterable[str]) -> List[CaseRow]:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ct_cases_{timestamp}.csv"
    with CaseScraper(headless=True) as scraper:
        cases = list(scraper.scrape_towns(towns))
        with open(filename, "w") as f:
            f.write(str(cases)) # Simple output for testing
        return cases







