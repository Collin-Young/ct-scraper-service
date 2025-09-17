#!/usr/bin/env python3
"""
Server PDF Downloader - Downloads court case PDFs and extracts parties pages
Modified for server use from the local CT_summonds_pdf.py script
"""

import os
import re
import time
import pathlib
import traceback
import random
import logging
import sys
from typing import List, Dict, Any, Set

# Database
from sqlalchemy.orm import Session

try:
    # Add the parent directory to the path so we can import from ct_scraper
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from ct_scraper.database import get_session
    from ct_scraper.models import Case, Base
except ImportError as e:
    logging.critical(f"Import error: {e}. Make sure the ct_scraper module is in the parent directory.")
    sys.exit(1)

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# PDFs / OCR
import pdfplumber
from PIL import Image
import pytesseract

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================= CONFIG ========================================

# Database configuration
DOWNLOAD_LIMIT = 100  # Limit number of cases to process per run
BATCH_SIZE = 10  # Process in batches to avoid memory issues

# Show browser while scraping (set to False for production)
SHOW_BROWSER = False

# Stop scanning a PDF after the first matching page
STOP_AFTER_FIRST_MATCH = True

# Paths (server-compatible)
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]  # /home/scraper/apps/ct-scraper-service
OUT_DIR = BASE_DIR / "downloads_ct_summons"
PDF_NAME = "DocumentInquiry.pdf"
DEBUG_DIR = OUT_DIR / "debug_parties_pages"

# Create directories
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# Tesseract path
# On Linux, if tesseract is in the system's PATH (e.g., from `apt install tesseract-ocr`),
# pytesseract can often find it automatically. Explicitly setting it can be a fallback.
# The line below is commented out to encourage using the system PATH first.
# pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# The court site's PDF link xpath
PDF_XPATH = '//*[@id="ctl00_ContentPlaceHolder1_CaseDetailDocuments1_gvDocuments_ctl02_hlnkDocument"]'

# How long to wait for downloads
DOWNLOAD_TIMEOUT_SEC = 60
DOWNLOAD_STABLE_SEC = 2

# =============================================================================


def chrome(download_dir: pathlib.Path) -> webdriver.Chrome:
    """Launch Chrome with a custom download directory."""
    opts = Options()
    if not SHOW_BROWSER:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    prefs = {
        "download.default_directory": str(download_dir.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
    }
    opts.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    return driver


# ---------------------- TEXT NORMALIZATION & MATCHING ------------------------

WS = r"[ \t\r\n]+"
def _compile(rx: str) -> re.Pattern:
    return re.compile(rx, re.IGNORECASE)

PAT_DEF = _compile(rf"total{WS}number{WS}of{WS}defendant[s]?\s*[:\-]\s*\d+")
PAT_PLA = _compile(rf"total{WS}number{WS}of{WS}plaintiff[s]?\s*[:\-]\s*\d+")
PAT_HEADER = _compile(
    r"name\s*\(\s*last\s*,\s*first\s*,\s*middle\s*initial\s*\)\s*and\s*address\s*of\s*each\s*party"
)
PAT_DEF_ROLE = _compile(rf"(first|additional){WS}defendant")


def normalize_text(txt: str) -> str:
    txt = txt.replace("‐", "-").replace("–", "-").replace("—", "-").replace("•", " ")
    txt = re.sub(r"[ \t\f\v]+", " ", txt)
    return txt


def looks_like_parties_page(text: str) -> bool:
    t = normalize_text(text or "")
    if PAT_DEF.search(t) and PAT_PLA.search(t):
        return True
    if PAT_HEADER.search(t) and PAT_DEF_ROLE.search(t):
        return True
    return False


# ----------------------------- PDF HELPERS -----------------------------------

def pdf_pages_text(pdf_path: pathlib.Path):
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                yield i, page.extract_text() or ""
            except Exception:
                yield i, ""


def ocr_page_image(pdf_path: pathlib.Path, page_index: int, dpi: int = 300) -> str:
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_index]
        im = page.to_image(resolution=dpi).original
        gray = im.convert("L")
        return pytesseract.image_to_string(gray)


def save_page_png(pdf_path: pathlib.Path, page_index: int, out_png: pathlib.Path, dpi: int = 200):
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_index]
        im = page.to_image(resolution=dpi).original
        im.save(str(out_png))


# ---------------------------- CORE FINDER ------------------------------------

def find_and_save_parties_page(pdf_path: pathlib.Path, docket_no: str) -> bool:
    """
    Scan a PDF for the Parties table page and save it as <docket>_parties.png.
    Returns True if saved; else writes <docket>_no_parties_found.txt and returns False.
    """
    try:
        candidates = []
        # First pass: text
        for idx, txt in pdf_pages_text(pdf_path):
            if looks_like_parties_page(txt):
                out_png = DEBUG_DIR / f"{docket_no}_parties.png"
                save_page_png(pdf_path, idx, out_png)
                logger.info(f"MATCH FOUND — PDF text (page {idx+1}) for {docket_no}")
                return True
            candidates.append((idx, txt))

        # Second pass: OCR
        for idx, _ in candidates:
            try:
                ocr_txt = ocr_page_image(pdf_path, idx, dpi=300)
                if looks_like_parties_page(ocr_txt):
                    out_png = DEBUG_DIR / f"{docket_no}_parties.png"
                    save_page_png(pdf_path, idx, out_png)
                    logger.info(f"MATCH FOUND — OCR (page {idx+1}) for {docket_no}")
                    return True
            except Exception:
                continue

        miss_file = DEBUG_DIR / f"{docket_no}_no_parties_found.txt"
        with open(miss_file, "w", encoding="utf-8") as f:
            f.write("No parties table found.\n")
        logger.info(f"Parties page NOT found for {docket_no}")
        return False

    except Exception:
        miss_file = DEBUG_DIR / f"{docket_no}_no_parties_found.txt"
        with open(miss_file, "w", encoding="utf-8") as f:
            f.write("ERROR scanning PDF:\n")
            f.write(traceback.format_exc())
        logger.error(f"ERROR scanning PDF for {docket_no}: {traceback.format_exc()}")
        return False


# ----------------------------- RESUME LOGIC ----------------------------------

def already_processed_dockets() -> Set[str]:
    """
    Look in DEBUG_DIR for existing outputs:
      - <DOCKET>_parties.png
      - <DOCKET>_no_parties_found.txt
    If either exists, consider that docket processed.
    """
    done = set()
    for p in DEBUG_DIR.glob("*_parties.png"):
        done.add(p.name.replace("_parties.png", ""))
    for p in DEBUG_DIR.glob("*_no_parties_found.txt"):
        done.add(p.name.replace("_no_parties_found.txt", ""))
    return done


# ------------------------------ DOWNLOAD WAIT --------------------------------

def wait_for_download(pdf_path: pathlib.Path, timeout: int = DOWNLOAD_TIMEOUT_SEC) -> bool:
    """
    Wait for chrome to finish downloading a PDF.
    - Waits for file to exist
    - Then waits for file size to stabilize for DOWNLOAD_STABLE_SEC
    """
    cr = pdf_path.with_suffix(pdf_path.suffix + ".crdownload")
    t0 = time.time()

    # 1) wait for file to appear
    while time.time() - t0 < timeout:
        if pdf_path.exists() and pdf_path.stat().st_size > 0 and not cr.exists():
            break
        time.sleep(0.25)
    else:
        return False

    # 2) wait for stable size
    last_size = -1
    stable_start = None
    while time.time() - t0 < timeout:
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


# -------------------------------- SCRAPER ------------------------------------

def get_unprocessed_cases(session: Session, limit: int) -> List[Dict[str, Any]]:
    """Get cases that haven't been processed for PDF download yet."""
    processed_dockets = already_processed_dockets()
    logger.info(f"Found {len(processed_dockets)} already processed dockets in output directory.")

    # Get cases from DB that are not in the processed list on disk
    unprocessed_cases = session.query(Case).filter(
        ~Case.docket_no.in_(processed_dockets)
    ).limit(limit).all()

    return [
        {
            "docket_no": case.docket_no,
            "url": f"https://civilinquiry.jud.ct.gov/CaseDetail.aspx?DocketNo={case.docket_no}",
        }
        for case in unprocessed_cases
    ]


def run_pdf_downloader(limit: int):
    """Main function to download PDFs and extract parties pages."""

    logger.info("Starting PDF downloader...")

    with get_session() as session:
        cases_to_process = get_unprocessed_cases(session, limit)

    if not cases_to_process:
        logger.info("No new cases to process for PDF download.")
        return

    logger.info(f"Found {len(cases_to_process)} new cases to process for PDF download.")

    driver = chrome(OUT_DIR)
    wait = WebDriverWait(driver, 25)

    processed = 0
    successes = 0
    failures = 0

    try:
        for i, case in enumerate(cases_to_process, 1):
            docket = case["docket_no"]
            url = case["url"]
            logger.info(f"[{i}/{len(cases_to_process)}] Processing {docket} at {url}")

            # Open case
            try:
                driver.get(url)
            except Exception as e:
                logger.error(f"Navigation error for {docket}: {e}")
                failures += 1
                continue

            # Click PDF link
            try:
                link = wait.until(EC.element_to_be_clickable((By.XPATH, PDF_XPATH)))
                logger.info(f"Found PDF link for {docket}, clicking...")
                link.click()
            except Exception as e:
                logger.warning(f"Could not click document link for {docket}. It may not have one. Error: {e}")
                failures += 1
                continue

            # Remove any old pdf to avoid confusion
            pdf_path = OUT_DIR / PDF_NAME
            try:
                if pdf_path.exists():
                    pdf_path.unlink()
            except Exception:
                pass

            # Wait for download to finish
            if not wait_for_download(pdf_path, timeout=DOWNLOAD_TIMEOUT_SEC):
                logger.warning(f"PDF download timeout for {docket}")
                failures += 1
                continue

            logger.info(f"Downloaded PDF for {docket} to {pdf_path}")

            # Find parties page
            try:
                ok = find_and_save_parties_page(pdf_path, docket)
                successes += int(ok)
                failures += int(not ok)
            finally:
                # Clean up PDF so next case can reuse filename
                try:
                    pdf_path.unlink(missing_ok=True)
                except Exception:
                    pass

            processed += 1

            # Polite delay
            time.sleep(random.uniform(0.3, 0.8))

    finally:
        driver.quit()
        logger.info("PDF downloader completed.")
        logger.info(f"Processed: {processed} | Successes: {successes} | Failures: {failures}")
        logger.info(f"Outputs saved to: {DEBUG_DIR}")


import typer

def main(limit: int = typer.Option(DOWNLOAD_LIMIT, help="Limit number of cases to process per run.")):
    """
    Run the PDF downloader to find, download, and process PDFs for new cases.
    """
    run_pdf_downloader(limit)


if __name__ == "__main__":
    typer.run(main)