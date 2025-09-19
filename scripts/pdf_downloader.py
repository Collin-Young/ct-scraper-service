#!/usr/bin/env python3

"""Download case PDFs and store them per docket."""



from __future__ import annotations



import logging

import os

import pathlib

import random

import shutil

import subprocess

import chromedriver_autoinstaller

import sys

import time

from typing import Any, Dict, List, Set



from sqlalchemy.orm import Session



try:

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    from ct_scraper.database import session_scope

    from ct_scraper.models import Case

except ImportError as exc:  # pragma: no cover

    logging.critical("Import error: %s. Make sure the ct_scraper module is in the parent directory.", exc)

    sys.exit(1)



from selenium import webdriver

from selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Service

from selenium.webdriver.common.by import By

from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.support.ui import WebDriverWait



logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("pdf_downloader")



DOWNLOAD_LIMIT = 100

SHOW_BROWSER = False

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]

OUT_DIR = BASE_DIR / "downloads_ct_summons"

PDF_NAME = "DocumentInquiry.pdf"

PDF_OUTPUT_DIR = OUT_DIR / "pdfs"



OUT_DIR.mkdir(parents=True, exist_ok=True)

PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)



PDF_XPATH = '//*[@id="ctl00_ContentPlaceHolder1_CaseDetailDocuments1_gvDocuments_ctl02_hlnkDocument"]'

DOWNLOAD_TIMEOUT_SEC = 60

DOWNLOAD_STABLE_SEC = 2





def chrome(download_dir: pathlib.Path) -> webdriver.Chrome:

    """Launch Chrome/Chromium with a custom download directory."""

    opts = Options()

    if not SHOW_BROWSER:

        opts.add_argument("--headless=new")

    opts.add_argument("--disable-gpu")

    opts.add_argument("--no-sandbox")

    opts.add_argument("--disable-dev-shm-usage")

    opts.add_argument("--window-size=1366,768")

    opts.add_argument("--disable-blink-features=AutomationControlled")

    opts.add_argument("--remote-debugging-port=0")



    binary_path: str | None = None

    candidates: List[str | None] = []

    if sys.platform.startswith("win"):

        candidates.extend(

            [

                os.environ.get("GOOGLE_CHROME_BIN"),

                r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",

                r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",

                shutil.which("chrome"),

                shutil.which("chrome.exe"),

                shutil.which("google-chrome"),

            ]

        )

    else:

        candidates.extend(

            [

                "/snap/chromium/3248/usr/lib/chromium-browser/chrome",

                "/snap/google-chrome/current/chrome",

                shutil.which("google-chrome"),

                shutil.which("chromium-browser"),

                shutil.which("chromium"),

            ]

        )

    for candidate in candidates:

        if candidate and os.path.isfile(candidate):

            binary_path = candidate

            break

    if binary_path:

        opts.binary_location = binary_path

        logger.info("Using Chrome binary: %s", binary_path)

    else:

        logger.warning("Chrome binary not located via defaults; relying on system PATH")



    prefs = {

        "download.default_directory": str(download_dir.resolve()),

        "download.prompt_for_download": False,

        "download.directory_upgrade": True,

        "plugins.always_open_pdf_externally": True,

    }

    opts.add_experimental_option("prefs", prefs)



    version_target = binary_path or shutil.which("google-chrome") or shutil.which("chrome") or shutil.which("chrome.exe")

    if version_target:

        try:

            version = subprocess.check_output([version_target, "--version"], text=True).strip()

            logger.info("Detected Chrome version: %s", version)

        except (FileNotFoundError, subprocess.CalledProcessError) as exc:

            logger.warning("Could not determine Chrome version: %s", exc)

    else:

        logger.warning("Could not determine Chrome version: binary path unknown")



    driver_path = chromedriver_autoinstaller.install()

    service = Service(driver_path)

    driver = webdriver.Chrome(service=service, options=opts)

    logger.info("Chrome started with browser version: %s", driver.capabilities.get("browserVersion"))

    chrome_info = driver.capabilities.get("chrome") or {}

    logger.info("Chromedriver version: %s", chrome_info.get("chromedriverVersion"))

    driver.set_page_load_timeout(60)

    return driver





def wait_for_download(pdf_path: pathlib.Path, timeout: int = DOWNLOAD_TIMEOUT_SEC) -> bool:

    """Wait until the browser finishes downloading the PDF."""

    end_time = time.time() + timeout

    last_size = -1

    stable_start: float | None = None



    while time.time() < end_time:

        if not pdf_path.exists():

            time.sleep(0.25)

            continue

        size = pdf_path.stat().st_size

        if size == last_size:

            if stable_start is None:

                stable_start = time.time()

            if time.time() - stable_start >= DOWNLOAD_STABLE_SEC:

                return True

        else:

            stable_start = None

            last_size = size

        time.sleep(0.25)

    return False





def already_processed_dockets() -> Set[str]:

    processed: Set[str] = set()

    for pdf_file in PDF_OUTPUT_DIR.glob("*.pdf"):

        processed.add(pdf_file.stem)

    return processed





def get_unprocessed_cases(session: Session, limit: int | None) -> List[Dict[str, Any]]:
    processed_dockets = already_processed_dockets()
    logger.info("Found %s already processed dockets in output directory.", len(processed_dockets))

    query = session.query(Case).order_by(Case.id)
    results: List[Dict[str, Any]] = []
    for case in query.yield_per(500):
        if case.docket_no in processed_dockets:
            continue

        results.append(
            {
                "docket_no": case.docket_no,
                "url": f"https://civilinquiry.jud.ct.gov/CaseDetail/PublicCaseDetail.aspx?DocketNo={case.docket_no}",
            }
        )

        if limit is not None and limit > 0 and len(results) >= limit:
            break

    return results

def run_pdf_downloader(limit: int | None) -> None:

    limit_desc = "unlimited" if limit is None or limit <= 0 else str(limit)

    logger.info("Starting PDF downloader (limit=%s)...", limit_desc)

    with session_scope() as session:

        effective_limit = None if limit is None or limit <= 0 else limit

        cases_to_process = get_unprocessed_cases(session, effective_limit)

    if not cases_to_process:

        logger.info("No new cases to process for PDF download.")

        return



    logger.info("Found %s new cases to process for PDF download.", len(cases_to_process))

    driver = chrome(OUT_DIR)

    wait = WebDriverWait(driver, 25)



    processed = successes = failures = 0



    try:

        for i, case in enumerate(cases_to_process, start=1):

            docket = case["docket_no"]

            url = case["url"]

            logger.info("[%s/%s] Processing %s at %s", i, len(cases_to_process), docket, url)



            try:

                driver.get(url)

            except Exception as exc:

                logger.error("Navigation error for %s: %s", docket, exc)

                failures += 1

                continue



            try:

                link = wait.until(EC.element_to_be_clickable((By.XPATH, PDF_XPATH)))

                logger.info("Found PDF link for %s, clicking...", docket)

                link.click()

            except Exception as exc:

                logger.warning("Could not click document link for %s. Error: %s", docket, exc)

                failures += 1

                continue



            pdf_path = OUT_DIR / PDF_NAME

            if pdf_path.exists():

                pdf_path.unlink(missing_ok=True)



            if not wait_for_download(pdf_path):

                logger.warning("PDF download timeout for %s", docket)

                failures += 1

                continue



            logger.info("Downloaded PDF for %s to %s", docket, pdf_path)

            dest_pdf = PDF_OUTPUT_DIR / f"{docket}.pdf"

            dest_pdf.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(pdf_path), dest_pdf)

            logger.info("Saved PDF for %s => %s", docket, dest_pdf)

            successes += 1

            processed += 1



            time.sleep(random.uniform(0.3, 0.8))

    finally:

        driver.quit()

        logger.info("PDF downloader completed.")

        logger.info("Processed: %s | Successes: %s | Failures: %s", processed, successes, failures)

        logger.info("Outputs saved to: %s", PDF_OUTPUT_DIR)





def main(limit: int = DOWNLOAD_LIMIT) -> None:

    run_pdf_downloader(limit)





if __name__ == "__main__":

    import typer



    typer.run(main)








