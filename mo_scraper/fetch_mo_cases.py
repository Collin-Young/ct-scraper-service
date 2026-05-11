from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

import pandas as pd
import time
import os
import random
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
import json
import sys
import base64
import socket
from urllib.parse import urlparse
from mo_scraper.database import init_db, get_session
from mo_scraper.models import Case, Party

# Try to import undetected-chromedriver for better bot detection bypass
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
    print("[DEBUG] undetected-chromedriver imported successfully")
except ImportError:
    UNDETECTED_AVAILABLE = False
    print("[DEBUG] undetected-chromedriver not available")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, 'browser_cookies.json')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DEBUG_DIR = os.path.join(BASE_DIR, 'debug_artifacts')
PROGRESS_FILE = os.path.join(BASE_DIR, 'mo_scraper_county_progress.txt')
STATE_FILE = os.path.join(BASE_DIR, 'mo_scraper_state.json')
BLOCK_CHECK_INTERVAL = int(os.environ.get('MO_SCRAPER_BLOCK_CHECK_INTERVAL', '30'))
MAX_BLOCK_WAIT_MINUTES = int(os.environ.get('MO_SCRAPER_MAX_BLOCK_WAIT', '10'))
PAGE_LOAD_TIMEOUT = int(os.environ.get('MO_SCRAPER_PAGE_LOAD_TIMEOUT', '180'))
NAV_RETRY_ATTEMPTS = int(os.environ.get('MO_SCRAPER_NAV_RETRIES', '5'))
NAV_RETRY_WAIT_SECONDS = int(os.environ.get('MO_SCRAPER_NAV_RETRY_WAIT', '10'))
DEFAULT_WAIT_SECONDS = int(os.environ.get('MO_SCRAPER_WAIT_SECONDS', '60'))
# Only include STRONG Cloudflare block indicators - not legitimate page content
BLOCK_PAGE_PATTERNS = (
    'verify you are a human',
    'checking your browser before accessing',
    'just a moment',
    'ddos protection',
    'automated access is not allowed',
    'cloudflare ray id',
    'please stand by, loading',
)
 

def is_block_page(page_source):
    """Check if page source contains block page patterns."""
    if not page_source:
        return False
    page_lower = page_source.lower()
    # Check for VERY specific block page text unique to MO block page
    # The MO block page says: "Access to any Missouri judicial website...
    # by a site data scraper... is expressly prohibited"
    strong_indicators = [
        'site data scraper',
        'expressly prohibited',
        'verify you are a human',
        'checking your browser before accessing',
        'automated access is not allowed',
    ]
    for indicator in strong_indicators:
        if indicator in page_lower:
            return True
    return False
 

 
def is_debugger_port_reachable(address: str, timeout: float = 3.0) -> bool:
    try:
        host, port_text = address.split(':', 1)
        port = int(port_text)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def save_scraping_state(county, date, county_index=None, total_counties=None):
    """Save current scraping state to allow resume after block."""
    state = {
        'current_county': county,
        'current_date': date,
        'county_index': county_index,
        'total_counties': total_counties,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'block_detected': True
    }
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        print(f"[STATE] Saved scraping state: {county} @ {date}")
    except Exception as e:
        print(f"[WARN] Failed to save state: {e}")


def load_scraping_state():
    """Load saved scraping state if available."""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        print(f"[STATE] Loaded saved state: {state.get('current_county')} @ {state.get('current_date')}")
        return state
    except Exception as e:
        print(f"[WARN] Failed to load state: {e}")
        return None


def clear_scraping_state():
    """Clear saved state after successful completion."""
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            print("[STATE] Cleared saved state")
        except Exception as e:
            print(f"[WARN] Failed to clear state: {e}")



def wait_for_block_clear(driver, wait, max_wait_minutes=MAX_BLOCK_WAIT_MINUTES):
    """Wait for Cloudflare block to clear by polling the page.
    
    Returns True if block cleared, False if timeout.
    """
    print(f"[BLOCK] Detected Cloudflare block. Waiting up to {max_wait_minutes} minutes for clearance...")
    print("[BLOCK] Please complete any challenges in the connected browser.")
    
    url = "https://www.courts.mo.gov/casenet/filingDateSearch.do?newSearch=Y"
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # Don't reload the page - let undetected-chromedriver handle it
            page_source = driver.page_source.lower()
            
            if not is_block_page(page_source):
                print("[BLOCK] Block cleared! Resuming scraping...")
                return True
            
            elapsed = int((time.time() - start_time) / 60)
            print(f"[BLOCK] Still blocked... ({elapsed} min elapsed, waiting 60s for undetected-chromedriver to solve...)")
            time.sleep(60)  # Wait longer for undetected-chromedriver to solve Cloudflare
            
        except Exception as e:
            print(f"[BLOCK] Error checking block status: {e}")
            time.sleep(60)
    
    print(f"[BLOCK] Timeout: Block not cleared after {max_wait_minutes} minutes")
    return False


def normalize_case_type(value: str) -> str:
    """Normalize case type strings for reliable comparisons."""
    if not value:
        return ""
    sanitized = (
        value.replace('\u2013', '-')  # en dash
        .replace('\u2014', '-')       # em dash
        .replace('\xa0', ' ')         # non-breaking space
    )
    collapsed = " ".join(sanitized.split())
    return collapsed.upper()

ALLOWED_PARTY_CASE_TYPES = {
    "CC FORECLOSURE",
    "CC QUIET TITLE",
    "CC MECHANICS LIEN",
    "AC APPL TO ENF MECHANICS LIEN",
    "CC APPL TO ENF MECHANICS LIEN",
    "AC LANDLORD COMPLAINT",
    "AC LANDLORD ACTIONS (BULK)",
    "AC RENT AND POSSESSION",
    "AC UNLAWFUL DETAINER",
    "AC UNLAWFUL OCCUPANT",
    "CC RENT AND POSSESSION",
    "CC UNLAWFUL DETAINER",
    "AC REPLEVIN",
    "CC REPLEVIN",
    "AC OWNR/LIENHLDR PETN PROP REL",
    "AC BREACH OF CONTRACT",
    "AC PROMISSORY NOTE",
    "AC SUIT ON ACCOUNT",
    "AC REVIVAL OF JUDGMENT",
    "CC BREACH OF CONTRACT",
    "CC PROMISSORY NOTE",
    "CC REVIVAL OF JUDGMENT",
    "CC TRANSCRIPT JUDGMENT",
    "AC OTHER REAL ESTATE ACTIONS",
    "CC OTHER REAL ESTATE ACTIONS",
    "CC PARTITION",
    "CC SPECIFIC PERFORMANCE",
    "AC DELINQUENT CITY TAXES",
    "COLLECTOR OF REVENUE TAX CASES",
    "CC CERT OF LIEN-DOR TAXES",
    "CC DISSOLUTION- W/ CHILDREN",
    "CC DISSOLUTION- W/O CHILDREN",
    "CC LEGAL SEP, ANNUL, SEP MAINT",
    "FC DISSOLUTION- W/ CHILDREN",
    "FC DISSOLUTION- W/O CHILDREN",
    "FC LEGAL SEP, ANNUL, SEP MAINT",
    "CC PET FOR CHILD CUSTODY/SUPP",
    "FC PET FOR CHILD CUSTODY/SUPP",
    "CC CS MOTION TO MODIFY",
    "FC CS MOTION TO MODIFY",
    "PR INDEPENDENT WITH WILL",
    "PR INDEPENDENT WITHOUT WILL",
    "PR REFUSAL OF LETTERS-SPOUSE",
    "PR REFUSAL OF LETTERS-CREDITOR",
    "PR SMALL EST AFFIDAVIT W/WILL",
    "PR SMALL EST AFFIDAVIT W/O WIL",
    "PR WILL ADMITTED OR REJECTED",
    "PR REQUIRED ADMINISTRATION",
    "PR DETERMINATION OF HEIRSHIP",
    "PR GUARDIANSHIP - ADULT",
    "PR GUARDIANSHIP - MINOR",
}

ALLOWED_PARTY_CASE_TYPES_NORMALIZED = {
    normalize_case_type(name) for name in ALLOWED_PARTY_CASE_TYPES
}


def prepare_profile_dir(profile_dir: str) -> str:
    if not os.path.exists(profile_dir):
        raise ValueError(f"Chrome profile directory does not exist: {profile_dir}")
    copy_profile = os.environ.get('MO_SCRAPER_PROFILE_COPY', 'true').lower() in ('1', 'true', 'yes')
    if not copy_profile:
        return profile_dir
    temp_dir = tempfile.mkdtemp(prefix='chrome_profile_copy_')
    shutil.copytree(profile_dir, temp_dir, dirs_exist_ok=True)
    print(f"[DEBUG] Copied Chrome profile from {profile_dir} to {temp_dir}")
    return temp_dir


def human_delay(min_seconds: float | None = None, max_seconds: float | None = None) -> None:
    lower = float(os.environ.get('MO_SCRAPER_HUMAN_DELAY_MIN', '2.0')) if min_seconds is None else min_seconds
    upper = float(os.environ.get('MO_SCRAPER_HUMAN_DELAY_MAX', '5.0')) if max_seconds is None else max_seconds
    if upper < lower:
        upper = lower
    time.sleep(random.uniform(lower, upper))


def load_cookies_from_file(driver, url):  # DISABLED
    print("[DEBUG] Cookie loading disabled")
    return False
    # DISABLED:
    """Load cookies from JSON file to bypass bot detection."""
    if os.path.exists(COOKIES_FILE):
        try:
            with open(COOKIES_FILE, 'r') as f:
                cookies = json.load(f)
            
            # Navigate to the main domain first (required for adding cookies)
            print(f"[DEBUG] Navigating to domain to load cookies...")
            driver.get("https://www.courts.mo.gov/casenet/filingDateSearch.do?newSearch=Y")
            time.sleep(2)
            
            # Add cookies one by one with error handling
            loaded_count = 0
            for cookie in cookies:
                try:
                    # Prepare cookie for Selenium - must match current domain
                    cookie_dict = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie['domain'],
                        'path': cookie.get('path', '/'),
                    }
                    # Remove sameSite (causes issues in Selenium)
                    # Don't add secure flag - let Selenium handle it
                    driver.add_cookie(cookie_dict)
                    loaded_count += 1
                except Exception as e:
                    # Ignore cookie errors - some may not apply to current domain
                    pass
            print(f"[DEBUG] Loaded {loaded_count}/{len(cookies)} cookies from {COOKIES_FILE}")
            return True
        except Exception as e:
            print(f"[WARN] Failed to load cookies: {e}")
    else:
        print(f"[INFO] No cookies file found at {COOKIES_FILE}")
        print(f"[INFO] To create one, see instructions in the code comments")
    return False


def simulate_human_behavior(driver):
    """Simulate human-like behavior to avoid bot detection."""
    try:
        # Scroll randomly (small amounts) - safest interaction
        scroll_amount = random.randint(50, 200)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.2, 0.4))
        
        # Scroll back up sometimes
        if random.random() > 0.5:
            driver.execute_script(f"window.scrollBy(0, -{random.randint(30, min(100, scroll_amount))});")
            time.sleep(random.uniform(0.2, 0.4))
        
        # Try mouse movement only if page has loaded and is ready
        try:
            # Reset mouse position to top-left corner first
            actions = webdriver.ActionChains(driver)
            actions.move_by_offset(0, 0).perform()
            time.sleep(0.1)
            
            # Small, safe mouse movements
            for _ in range(random.randint(1, 2)):
                x = random.randint(10, 100)
                y = random.randint(10, 100)
                actions = webdriver.ActionChains(driver)
                actions.move_by_offset(x, y).perform()
                time.sleep(random.uniform(0.1, 0.2))
        except Exception as mouse_error:
            # Mouse movement failed, but that's okay
            pass
            
    except Exception as e:
        print(f"[DEBUG] Human behavior simulation error (non-critical): {e}")


def get_driver(headless):
    # Use undetected-chromedriver if available and not on ARM architecture
    if UNDETECTED_AVAILABLE and not os.environ.get('MO_SCRAPER_REMOTE_DEBUGGING_PORT'):
        # Check if we're on ARM (Raspberry Pi) - undetected-chromedriver doesn't support ARM
        import platform
        if 'arm' not in platform.machine().lower():
            print("[DEBUG] Using undetected-chromedriver for better bot detection bypass")
            try:
                uc_options = uc.ChromeOptions()
                uc_options.add_argument('--no-sandbox')
                uc_options.add_argument('--disable-dev-shm-usage')
                uc_options.add_argument('--disable-gpu')
                uc_options.add_argument('--lang=en-US')
                uc_options.add_argument('--window-size=1920,1080')
                
                headless_flag = headless.lower() == 'headless'
                if headless_flag:
                    uc_options.add_argument('--headless=new')
                    print('Running in headless mode.')
                else:
                    print('Running in non-headless mode.')
                
                chromium_binary = os.environ.get('MO_SCRAPER_CHROMIUM_BINARY')
                if chromium_binary and os.path.exists(chromium_binary):
                    uc_options.binary_location = chromium_binary
                    print(f"[DEBUG] Using Chromium binary: {chromium_binary}")
                
                driver = uc.Chrome(options=uc_options, version_main=None)
                driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                return driver
            except Exception as e:
                print(f"[WARN] Failed to use undetected-chromedriver: {e}. Falling back to regular Chrome.")
        else:
            print("[DEBUG] undetected-chromedriver not supported on ARM architecture, using regular Chrome")
    
    # Fallback to regular Chrome with anti-detection measures
    print("[DEBUG] Using regular Chrome with anti-detection measures")
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--lang=en-US')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--disable-default-apps')
    user_agent = os.environ.get(
        'MO_SCRAPER_USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    )
    chrome_options.add_argument(f'--user-agent={user_agent}')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    # Additional anti-detection arguments
    chrome_options.add_argument('--disable-blink-features')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-service-autorun')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-component-extensions-with-background-pages')
    chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    remote_debug_port = os.environ.get('MO_SCRAPER_REMOTE_DEBUGGING_PORT')
    if not remote_debug_port:
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)

    def first_existing(paths):
        for candidate in paths:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    proxy_url = os.environ.get('MO_SCRAPER_PROXY')
    proxy_auth_header = None
    if proxy_url:
        proxy_arg = proxy_url if '://' in proxy_url else f'http://{proxy_url}'
        parsed_proxy = urlparse(proxy_arg)
        proxy_scheme = parsed_proxy.scheme or 'http'
        proxy_host = parsed_proxy.hostname
        proxy_port = parsed_proxy.port
        host_port = None
        if proxy_host:
            host_port = f"{proxy_host}:{proxy_port}" if proxy_port else proxy_host
        proxy_server_arg = proxy_arg
        display_proxy = proxy_arg
        if host_port:
            proxy_server_arg = f"{proxy_scheme}://{host_port}"
            display_proxy = proxy_server_arg
        chrome_options.add_argument(f'--proxy-server={proxy_server_arg}')
        chrome_options.add_argument('--proxy-bypass-list=<-loopback>')
        # Bright Data SSL certificate handling
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        # Load Bright Data SSL certificate - try multiple locations
        ssl_cert_path = os.environ.get('MO_SCRAPER_SSL_CERT')
        if not ssl_cert_path:
            # Try default location in mo_scraper directory
            default_cert = os.path.join(BASE_DIR, 'brightdata_cert.crt')
            if os.path.exists(default_cert):
                ssl_cert_path = default_cert
        if ssl_cert_path and os.path.exists(ssl_cert_path):
            chrome_options.add_argument(f'--ssl-client-certificate={ssl_cert_path}')
            print(f"[DEBUG] Using SSL certificate: {ssl_cert_path}")
        else:
            print(f"[WARN] Bright Data SSL certificate not found. Will ignore SSL errors.")
            print(f"[WARN] For better reliability, place 'brightdata_cert.crt' in {BASE_DIR}")
        if parsed_proxy.username and parsed_proxy.password:
            credentials = f"{parsed_proxy.username}:{parsed_proxy.password}"
            proxy_auth_header = 'Basic ' + base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        print(f"[DEBUG] Routing traffic through proxy: {display_proxy}")
        print(f"[DEBUG] SSL certificate errors will be ignored (required for Bright Data)")

    headless_flag = headless.lower() == 'headless'
    if remote_debug_port:
        # Use custom address if provided, otherwise default to localhost
        remote_debug_address = os.environ.get('MO_SCRAPER_REMOTE_DEBUGGING_ADDRESS', '127.0.0.1')
        debugger_address = f'{remote_debug_address}:{remote_debug_port}'
        if not is_debugger_port_reachable(debugger_address):
            raise RuntimeError(
                f"MO_SCRAPER_REMOTE_DEBUGGING_PORT={remote_debug_port} set, "
                f"but Chrome is not reachable at {debugger_address}. "
                f"Start Chrome with --remote-debugging-port={remote_debug_port} and ensure the browser is running. "
                f"Set MO_SCRAPER_REMOTE_DEBUGGING_ADDRESS if Chrome is on a different machine."
            )
        chrome_options.debugger_address = debugger_address
        print(f"[DEBUG] Connecting to existing Chrome via remote debugger at {debugger_address}")
    forced_profile_dir = os.environ.get('MO_SCRAPER_PROFILE_DIR')
    if forced_profile_dir and not remote_debug_port:
        user_data_dir = prepare_profile_dir(forced_profile_dir)
        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        print(f"[DEBUG] Using supplied user data dir: {user_data_dir}")
    elif headless_flag and not remote_debug_port:
        unique_token = f"{os.getpid()}_{int(time.time())}_{uuid.uuid4().hex}"
        user_data_dir = f"/tmp/chrome_profile_{unique_token}"
        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        print(f"[DEBUG] Using unique user data dir: {user_data_dir}")
    if headless_flag:
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        print('Running in headless mode.')
    else:
        print('Running in non-headless mode.')

    chromium_binary = first_existing([
        os.environ.get('MO_SCRAPER_CHROMIUM_BINARY'),
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/snap/bin/chromium',
    ])
    if chromium_binary:
        chrome_options.binary_location = chromium_binary
        print(f"[DEBUG] Using Chromium binary: {chromium_binary}")

    chromedriver_path = first_existing([
        os.environ.get('MO_SCRAPER_CHROMEDRIVER'),
        '/usr/lib/chromium-browser/chromedriver',
        '/usr/lib/chromium/chromedriver',
        '/usr/bin/chromedriver',
    ])
    if chromedriver_path:
        print(f"[DEBUG] Using chromedriver at: {chromedriver_path}")
        service = Service(chromedriver_path)
    else:
        service = Service()

    if remote_debug_port:
        driver = webdriver.Chrome(service=service, options=chrome_options)
    elif UNDETECTED_AVAILABLE:
        # Use undetected-chromedriver for better bot detection bypass
        print("[DEBUG] Using undetected-chromedriver for better bot detection bypass")
        # Remove options that conflict with undetected-chromedriver
        chrome_options.add_argument('--no-sandbox')  # Needed for undetected-chromedriver
        driver = uc.Chrome(service=service, options=chrome_options)
    else:
        print("[DEBUG] Using regular Chrome with anti-detection measures")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    if proxy_auth_header:
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': {'Proxy-Authorization': proxy_auth_header}})
    driver.execute_cdp_cmd(
        'Page.addScriptToEvaluateOnNewDocument',
        {
            'source': '''
                // Override webdriver property
                Object.defineProperty(navigator, "webdriver", {get: () => undefined});
                
                // Mock Chrome runtime
                window.navigator.chrome = { runtime: {} };
                
                // Set languages
                Object.defineProperty(navigator, "languages", { get: () => ['en-US', 'en'] });
                
                // Mock plugins
                Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3] });
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override chrome detection
                window.chrome = { runtime: {} };
                
                // Remove automation indicators
                delete navigator.__proto__.webdriver;
                
                // Override iframe contentWindow
                Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                    get() {
                        return window;
                    }
                });
                
                // Canvas fingerprinting protection
                const getImageData = HTMLCanvasElement.prototype.getContext('2d').getImageData;
                HTMLCanvasElement.prototype.getContext('2d').getImageData = function(sx, sy, sw, sh) {
                    const imageData = getImageData.apply(this, arguments);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = imageData.data[i] + Math.floor(Math.random() * 10) - 5;
                        imageData.data[i + 1] = imageData.data[i + 1] + Math.floor(Math.random() * 10) - 5;
                        imageData.data[i + 2] = imageData.data[i + 2] + Math.floor(Math.random() * 10) - 5;
                    }
                    return imageData;
                };
                
                // WebGL fingerprinting protection
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel(R) Iris(TM) Graphics 6100';
                    }
                    return getParameter.apply(this, arguments);
                };
                
                // Override screen properties
                Object.defineProperty(screen, 'width', { get: () => 1920 });
                Object.defineProperty(screen, 'height', { get: () => 1080 });
                Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
                Object.defineProperty(screen, 'availHeight', { get: () => 1040 });
                
                // Override hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
                
                // Override device memory
                Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            '''
        },
    )
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def load_url_with_retries(driver, url, label, retries=NAV_RETRY_ATTEMPTS, wait_seconds=NAV_RETRY_WAIT_SECONDS):
    for attempt in range(1, retries + 1):
        try:
            print(f"[DEBUG] Loading {label} (attempt {attempt}/{retries})")
            
            # Load cookies before navigating (first attempt only)
            if attempt == 1:
                # Navigate to domain first (required for adding cookies)
                domain = url.split('/')[2]
                driver.get(f"https://{domain}")
                load_cookies_from_file(driver, url)
                human_delay(1.0, 2.0)
            
            driver.get(url)
            
            # Simulate human behavior after page load
            human_delay(1.0, 3.0)
            simulate_human_behavior(driver)
            
            # Check for block page
            page_source = driver.page_source.lower()
            if is_block_page(page_source):
                print(f"[BLOCK] Detected a bot-block page after loading {label}.")
                dump_debug_artifacts(driver, f"blocked_{label}_attempt{attempt}")
                
                # If blocked, wait longer and try with a different approach
                if attempt < retries:
                    backoff_time = wait_seconds * attempt * 2
                    print(f"[BLOCK] Waiting {backoff_time} seconds before retry...")
                    time.sleep(backoff_time)
                continue
                
            return True
            
        except TimeoutException as exc:
            print(f"[TIMEOUT] {label} attempt {attempt}/{retries}: {exc}")
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
        except Exception as exc:
            print(f"[ERROR] {label} attempt {attempt}/{retries}: {exc}")
        
        if attempt < retries:
            backoff_time = wait_seconds * attempt
            print(f"[RETRY] Waiting {backoff_time} seconds before next attempt...")
            time.sleep(backoff_time)
    
    print(f"[ERROR] Failed to load {label} after {retries} attempts.")
    return False

def scrape_party_details(driver, url):
    try:
        print(f"[SEARCH] Accessing URL: {url}")
        case_label = "party_page"
        if "caseNumber=" in url:
            case_label = url.split("caseNumber=", 1)[1].split("&", 1)[0]
        if not load_url_with_retries(driver, url, f"party_page_{case_label}"):
            return []

        WebDriverWait(driver, DEFAULT_WAIT_SECONDS).until(
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
        parties_tab = WebDriverWait(driver, DEFAULT_WAIT_SECONDS).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Parties & Attorneys"))
        )
        parties_tab.click()

        # Wait until a party card div appears inside the container
        WebDriverWait(driver, DEFAULT_WAIT_SECONDS).until(
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


def dump_debug_artifacts(driver, label):
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{label}"
        screenshot_path = os.path.join(DEBUG_DIR, f"{base_name}.png")
        html_path = os.path.join(DEBUG_DIR, f"{base_name}.html")
        driver.save_screenshot(screenshot_path)
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(driver.page_source)
        print(f"[DEBUG] Saved debug artifacts to {screenshot_path} and {html_path}")
    except Exception as debug_error:
        print(f"[WARN] Unable to persist debug artifacts: {debug_error}")




def ensure_search_form_ready(driver, wait, label):
    try:
        # Wait for page to fully load
        wait.until(lambda drv: drv.execute_script("return document.readyState") == "complete")
        
        # Check for block page first
        if is_block_page(driver.page_source):
            print(f"[BLOCK] Detected block page in ensure_search_form_ready for {label}")
            dump_debug_artifacts(driver, f"blocked_form_{label}")
            return False
        
        # Simulate human behavior while waiting
        human_delay(0.5, 1.5)
        
        # Wait for main content
        wait.until(EC.presence_of_element_located((By.ID, "mainContent")))
        
        # Simulate a bit more human behavior
        human_delay(0.3, 1.0)
        
        # Wait for court code dropdown
        wait.until(EC.visibility_of_element_located((By.ID, "courtCode")))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#courtCode option[value]")))
        
        # Small delay before checking button
        human_delay(0.3, 0.8)
        
        # Wait for find button to be clickable
        wait.until(EC.element_to_be_clickable((By.ID, "findButton")))
        
        # Final human behavior simulation
        simulate_human_behavior(driver)
        
        return True
    except TimeoutException as exc:
        print("[TIMEOUT] Search form did not become ready in time.")
        dump_debug_artifacts(driver, f"form_ready_{label}")
        raise exc

def scrape_court_cases_and_parties(
    county_name,
    start_date,
    continue_search="no",
    headless="no",
    filter_case_type="all",
    skip_non_empty=False,
    force_counties=None,
    force_county_start_dates=None,
):
    init_db()
    session = get_session()
    url = "https://www.courts.mo.gov/casenet/filingDateSearch.do?newSearch=Y"
    driver = get_driver(headless)
    wait = WebDriverWait(driver, DEFAULT_WAIT_SECONDS)
    remote_debugging_enabled = bool(os.environ.get('MO_SCRAPER_REMOTE_DEBUGGING_PORT'))

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

    def resolve_county_index(candidates, query):
        if not query:
            return None, None
        normalized_query = query.strip().lower()
        for idx, name in enumerate(candidates):
            if name.lower() == normalized_query:
                return idx, name
        for idx, name in enumerate(candidates):
            if normalized_query in name.lower():
                return idx, name
        return None, None

    start_index = 0
    resume_message = None
    if county_name.lower() == "all":
        start_county_env = os.environ.get('MO_SCRAPER_START_COUNTY')
        if start_county_env:
            idx, matched_name = resolve_county_index(counties_to_scrape, start_county_env)
            if idx is not None:
                start_index = idx
                resume_message = f"[RESUME] Starting at specified county '{matched_name}' via MO_SCRAPER_START_COUNTY."
            else:
                print(f"[WARN] MO_SCRAPER_START_COUNTY='{start_county_env}' not found; processing full list.")
        elif os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as progress_handle:
                last_completed = progress_handle.read().strip()
            idx, matched_name = resolve_county_index(counties_to_scrape, last_completed)
            if idx is not None:
                start_index = idx + 1
                if start_index < len(counties_to_scrape):
                    resume_message = f"[RESUME] Skipping {start_index} counties already processed (through '{matched_name}')."
                else:
                    print(f"[RESUME] All counties already processed through '{matched_name}'. Nothing to do.")
            elif last_completed:
                print(f"[RESUME] Stored progress '{last_completed}' not found in dropdown; ignoring.")
        if resume_message:
            print(resume_message)
        if start_index >= len(counties_to_scrape):
            if os.path.exists(PROGRESS_FILE):
                try:
                    os.remove(PROGRESS_FILE)
                except OSError as cleanup_err:
                    print(f"[WARN] Unable to remove progress file: {cleanup_err}")
            session.close()
            driver.quit()
            print("[INFO] No counties left to process.")
            return
        if start_index > 0:
            counties_to_scrape = counties_to_scrape[start_index:]

    case_keywords = []
    if filter_case_type != "all":
        CASE_TYPES_FILE = os.path.join(STATIC_DIR, "case_types.json")
        with open(CASE_TYPES_FILE, "r") as f:
            case_types_data = json.load(f)
        case_keywords = case_types_data.get(filter_case_type, [])

    saved_count = 0
    all_counties_completed = True
    force_counties = force_counties or []
    force_county_start_dates = force_county_start_dates or {}

    def normalize_name(value: str | None) -> str:
        return (value or "").strip().lower()

    forced_normalized = {normalize_name(name) for name in force_counties}
    forced_start_dates_normalized = {
        normalize_name(name): date for name, date in force_county_start_dates.items()
    }

    for county in counties_to_scrape:
        county_label = county.split(" - ")[0].strip()
        county_is_forced = (
            normalize_name(county) in forced_normalized
            or normalize_name(county_label) in forced_normalized
        )
        county_override_start = (
            forced_start_dates_normalized.get(normalize_name(county))
            or forced_start_dates_normalized.get(normalize_name(county_label))
        )
        if skip_non_empty and not county_is_forced:
            existing_case = (
                session.query(Case)
                .filter(Case.location == county_label)
                .first()
            )
            if existing_case:
                print(
                    f"[SKIP] County {county} already has stored cases; skipping."
                )
                continue
        print(f"[COUNTY] Starting {county}")
        county_start_date = county_override_start or start_date
        consecutive_no_cases = 0
        max_consecutive_no_cases = 8
        county_completed = False

        while True:
            print(f"\nScraping data for county: {county}, start date: {county_start_date}")
            form_label = f"{county.replace(' ', '_')}_{county_start_date.replace('/', '-')}"
            form_ready = False
            for attempt in range(3):
                attempt_num = attempt + 1
                use_current_page = (
                    remote_debugging_enabled
                    and attempt == 0
                    and 'filingDateSearch.do' in (driver.current_url or '')
                )
                if use_current_page:
                    print("[DEBUG] Using current remote browser page")
                elif attempt == 0:
                    print("[DEBUG] Loading search form")
                else:
                    print(f"[DEBUG] Reloading search form (attempt {attempt_num})")
                if not use_current_page and not load_url_with_retries(driver, url, f"search_form_{form_label}_attempt{attempt_num}"):
                    human_delay(2.0, 4.0)
                    continue
                try:
                    ensure_search_form_ready(driver, wait, f"{form_label}_attempt{attempt_num}")
                    form_ready = True
                    print("[DEBUG] Search form ready")
                    break
                except TimeoutException as timeout_exc:
                    page_source = driver.page_source
                    if is_block_page(page_source):
                        print("[BLOCK] Block page detected during form load!")
                        # Save state and wait for user to re-authenticate
                        county_idx = counties_to_scrape.index(county) if county in counties_to_scrape else None
                        save_scraping_state(county, county_start_date, county_idx, len(counties_to_scrape))
                        if wait_for_block_clear(driver, wait):
                            clear_scraping_state()
                            # Retry loading the form after block cleared
                            continue
                        else:
                            print(f"[ERROR] Unable to clear block. Exiting.")
                            driver.quit()
                            session.close()
                            return
                    else:
                        print(f"[WARN] Search form still loading (attempt {attempt_num}): {timeout_exc}")
                        time.sleep(5)
                    if attempt == 2:
                        dump_debug_artifacts(driver, f"form_load_failed_{form_label}")
            if not form_ready:
                print(f"[ERROR] Unable to load search form for {county} on {county_start_date}.")
                break

            extracted_cases = []
            try:
                select_success = False
                for select_attempt in range(3):
                    try:
                        wait.until(EC.element_to_be_clickable((By.ID, "courtCode")))
                        Select(driver.find_element(By.ID, "courtCode")).select_by_visible_text(county)
                        select_success = True
                        print("[DEBUG] County selected")
                        human_delay(1.5, 2.5)
                        break
                    except (NoSuchElementException, StaleElementReferenceException) as select_error:
                        print(f"[WARN] Retrying county selection ({select_attempt + 1}/3): {select_error}")
                        human_delay(1.4, 2.2)
                if not select_success:
                    print(f"[ERROR] Unable to select county {county}.")
                    dump_debug_artifacts(driver, f"county_select_{form_label}")
                    break

                date_input = wait.until(EC.presence_of_element_located((By.ID, "datepicker")))
                print(f"[DEBUG] Date input found with ID: {date_input.get_attribute('id')}")
                print(f"[DEBUG] Initial readonly attribute: {date_input.get_attribute('readonly')}")

                driver.execute_script("arguments[0].removeAttribute('readonly')", date_input)
                print(f"[DEBUG] Readonly after removal: {date_input.get_attribute('readonly')}")

                driver.execute_script("arguments[0].click();", date_input)
                human_delay(1.0, 1.5)
                print("[DEBUG] Clicked date input to open calendar")

                try:
                    picker_holder = driver.find_element(By.CSS_SELECTOR, ".picker__holder")
                    print(f"[DEBUG] Picker holder visible after click: {picker_holder.is_displayed()}")
                except Exception:
                    print("[DEBUG] Picker holder not found after click")

                date_input.clear()
                date_input.send_keys(county_start_date)
                human_delay(0.8, 1.3)
                print(f"[DEBUG] Sent keys: {county_start_date}")
                print(f"[DEBUG] Input value after send_keys: {date_input.get_attribute('value')}")

                driver.find_element(By.TAG_NAME, "body").click()
                print("[DEBUG] Clicked body to close any picker")
                print("[DEBUG] Date entered")

                try:
                    picker_holder = driver.find_element(By.CSS_SELECTOR, ".picker__holder")
                    print(f"[DEBUG] Picker holder visible after input: {picker_holder.is_displayed()}")
                except Exception:
                    print("[DEBUG] Picker holder not found after input")

                try:
                    driver.execute_script("document.querySelector('.picker__holder').style.display='none';")
                except Exception:
                    pass

                find_button = driver.find_element(By.ID, "findButton")
                driver.execute_script("arguments[0].scrollIntoView();", find_button)
                find_button.click()
                print(f"[DEBUG] Find button clicked for {county_start_date}")
                time.sleep(3)

                wait.until(EC.element_to_be_clickable((By.NAME, "searchResult_length")))
                Select(driver.find_element(By.NAME, "searchResult_length")).select_by_value("100")
                time.sleep(1)

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
                                    "location": county_label
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
                # Check if this is a block page
                try:
                    page_source = driver.page_source
                    if is_block_page(page_source):
                        print(f"[BLOCK] Block detected during case extraction!")
                        county_idx = counties_to_scrape.index(county) if county in counties_to_scrape else None
                        save_scraping_state(county, county_start_date, county_idx, len(counties_to_scrape))
                        if wait_for_block_clear(driver, wait):
                            clear_scraping_state()
                            continue  # Retry the same date
                        else:
                            print(f"[ERROR] Unable to clear block. Exiting.")
                            driver.quit()
                            session.close()
                            return
                except:
                    pass
            except Exception as e:
                print(f"[ERROR] Unexpected error for {county_start_date}: {e}")
                # Check if this is a block page
                try:
                    page_source = driver.page_source
                    if is_block_page(page_source):
                        print(f"[BLOCK] Block detected during case extraction!")
                        county_idx = counties_to_scrape.index(county) if county in counties_to_scrape else None
                        save_scraping_state(county, county_start_date, county_idx, len(counties_to_scrape))
                        if wait_for_block_clear(driver, wait):
                            clear_scraping_state()
                            continue  # Retry the same date
                        else:
                            print(f"[ERROR] Unable to clear block. Exiting.")
                            driver.quit()
                            session.close()
                            return
                except:
                    pass
            if len(extracted_cases) > 0:
                consecutive_no_cases = 0
                print(f"Found {len(extracted_cases)} cases for {county_start_date}")
                # Now scrape party details for each case
                for case_entry in extracted_cases:
                    # Check if case already exists
                    existing_case = session.query(Case).filter_by(case_number=case_entry['case_number']).first()
                    if existing_case:
                        print(f"Case {case_entry['case_number']} already exists, skipping.")
                        continue
                    case_type_normalized = normalize_case_type(case_entry['case_type'])
                    should_fetch_parties = case_type_normalized in ALLOWED_PARTY_CASE_TYPES_NORMALIZED
                    party_details = []
                    if should_fetch_parties:
                        party_details = scrape_party_details(driver, case_entry['case_url'])
                    else:
                        print(
                            f"[SKIP] Not fetching parties for {case_entry['case_number']} "
                            f"({case_entry['case_type']})"
                        )
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
                county_completed = True
                print("No cases found for several consecutive dates. Stopping.")
                break

            if continue_search == 'continue':
                if remote_debugging_enabled:
                    for back_attempt in range(1, 4):
                        try:
                            print(f"[DEBUG] Returning to search form via browser history (attempt {back_attempt})")
                            driver.back()
                            human_delay(1.5, 2.5)
                            ensure_search_form_ready(driver, wait, f"history_back_{form_label}_{back_attempt}")
                            break
                        except Exception as back_error:
                            print(f"[WARN] Browser history did not return to search form: {back_error}")
                print(f"Updating to next date from {county_start_date}")
                try:
                    dt = datetime.strptime(county_start_date, '%m/%d/%Y')
                    next_dt = dt + timedelta(days=7)
                    if next_dt > datetime.today():
                        county_completed = True
                        print("Reached current date. Stopping.")
                        break
                    county_start_date = next_dt.strftime('%m/%d/%Y')
                    print(f"Next date: {county_start_date}")
                except Exception as e:
                    print(f"Date update error: {e}")
                    break
            else:
                county_completed = True
                break

        if county_completed:
            print(f"[COUNTY] Completed {county}")
            if county_name.lower() == "all":
                with open(PROGRESS_FILE, 'w', encoding='utf-8') as progress_handle:
                    progress_handle.write(county)
        else:
            all_counties_completed = False
            if county_name.lower() == "all":
                print(f"[COUNTY] {county} did not complete successfully; leaving progress marker unchanged.")

    session.close()
    driver.quit()
    clear_scraping_state()  # Clear any saved state on successful completion
    if county_name.lower() == "all" and all_counties_completed and os.path.exists(PROGRESS_FILE):
        try:
            os.remove(PROGRESS_FILE)
        except OSError as cleanup_err:
            print(f"[WARN] Unable to remove progress file: {cleanup_err}")
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

