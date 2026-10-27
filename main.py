
import os
import json
import time
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# ================= CONFIGURATION =================

EMAIL = os.getenv("EMAIL", "").strip()
PASSWORD = os.getenv("PASSWORD", "").strip()
APP_PASSWORD = os.getenv("APP_PASSWORD", "").replace(" ", "")

LOGIN_URL = (
    "https://placements.codegnan.com/"
    "login?from=%2Fstudent%2Fdashboard"
)

JOBS_URL = (
    "https://placements.codegnan.com/"
    "student/cr/job-listings?tab=open"
)

JOBS_FILE = Path("jobs.json")
DEBUG_DIR = Path("debug")


# ================= EMAIL ALERT =================

def send_email(new_jobs):
    if not EMAIL or not APP_PASSWORD:
        raise RuntimeError(
            "EMAIL or APP_PASSWORD is missing from GitHub Secrets."
        )

    body = "NEW CODEGNAN JOB OPPORTUNITIES\n\n"

    for index, job in enumerate(new_jobs, start=1):
        body += f"{index}. {job}\n\n"

    message = MIMEMultipart()
    message["From"] = EMAIL
    message["To"] = EMAIL
    message["Subject"] = (
        f"{len(new_jobs)} New Codegnan Job Alert(s)"
    )
    message.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(EMAIL, APP_PASSWORD)
        server.send_message(message)

    print("Email sent successfully.")


# ================= JOB HISTORY =================

def load_old_jobs():
    if not JOBS_FILE.exists():
        return []

    try:
        data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise ValueError("jobs.json must contain a list.")

        return data

    except (json.JSONDecodeError, OSError, ValueError) as exc:
        raise RuntimeError(
            f"Cannot safely read jobs.json: {exc}"
        ) from exc


def save_jobs(jobs):
    temporary = JOBS_FILE.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(jobs, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    temporary.replace(JOBS_FILE)


# ================= DIAGNOSTICS =================

def save_debug(driver, name):
    DEBUG_DIR.mkdir(exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    prefix = DEBUG_DIR / f"{name}_{timestamp}"

    (prefix.with_suffix(".html")).write_text(
        driver.page_source,
        encoding="utf-8"
    )

    driver.save_screenshot(str(prefix.with_suffix(".png")))

    print(f"Debug files saved: {prefix}")


# ================= LOGIN =================

def find_visible(driver, selectors):
    for by, selector in selectors:
        for element in driver.find_elements(by, selector):
            if element.is_displayed() and element.is_enabled():
                return element

    return None


def login(driver):
    if not EMAIL or not PASSWORD:
        raise RuntimeError(
            "Configure EMAIL and PASSWORD in GitHub Secrets."
        )

    wait = WebDriverWait(driver, 25)

    # Open the direct login URL.
    driver.get(LOGIN_URL)

    print("Login URL:", driver.current_url)

    username = wait.until(
        lambda d: find_visible(d, [
            (By.ID, "username"),
            (By.NAME, "username"),
            (By.NAME, "email"),
            (By.ID, "email"),
            (By.CSS_SELECTOR, "input[type='email']")
        ])
    )

    password = wait.until(
        lambda d: find_visible(d, [
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']")
        ])
    )

    username.clear()
    username.send_keys(EMAIL)

    password.clear()
    password.send_keys(PASSWORD)

    submit = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[type='submit']")
        )
    )

    submit.click()

    # Wait for login to leave the login page.
    try:
        wait.until(
            lambda d: "/login" not in d.current_url.lower()
        )
    except TimeoutException:
        save_debug(driver, "login_failed")
        raise RuntimeError(
            "Login did not complete. Check the saved diagnostics."
        )

    print("Login successful. Current URL:", driver.current_url)


# ================= OPEN TO APPLY =================

def open_active_jobs(driver):
    # Navigate directly to the Open to Apply listings.
    driver.get(JOBS_URL)

    WebDriverWait(driver, 25).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    time.sleep(3)

    if "/login" in driver.current_url.lower():
        save_debug(driver, "session_redirect")
        raise RuntimeError("The job portal redirected to login.")

    # Select the correct tab if the website has not selected it
    # automatically from ?tab=open.
    tabs = driver.find_elements(
        By.XPATH,
        "//*[self::a or self::button or @role='tab']"
        "[contains(translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
        "'open to apply')]"
    )

    for tab in tabs:
        if tab.is_displayed() and tab.is_enabled():
            try:
                tab.click()
                time.sleep(2)
                break
            except Exception:
                continue

    print("Active jobs URL:", driver.current_url)
    print("Page title:", driver.title)


# ================= EXTRACT ACTIVE JOBS =================

def clean_text(value):
    return " ".join(value.replace("\u00a0", " ").split()).strip()


def extract_jobs(driver):
    jobs = {}

    # Strategy 1: Read table rows.
    rows = driver.find_elements(
        By.CSS_SELECTOR,
        "table tbody tr"
    )

    for row in rows:
        if not row.is_displayed():
            continue

        cells = row.find_elements(By.TAG_NAME, "td")

        values = [
            clean_text(cell.text)
            for cell in cells
            if clean_text(cell.text)
        ]

        if len(values) >= 2:
            # Retain the visible job details for comparison.
            job = " | ".join(values)

            if job:
                jobs[job.casefold()] = job

    if jobs:
        print("Extracted listings from table:", len(jobs))
        return list(jobs.values())

    # Strategy 2: Common job-card layouts.
    # These selectors are fallbacks, not verified Codegnan selectors.
    selectors = [
        "[data-testid*='job']",
        "[class*='job-card']",
        "[class*='jobCard']",
        "[class*='job-listing']",
        "[class*='JobCard']"
    ]

    for selector in selectors:
        for card in driver.find_elements(By.CSS_SELECTOR, selector):
            if not card.is_displayed():
                continue

            text = clean_text(card.text)

            if 8 <= len(text) <= 2500:
                jobs[text.casefold()] = text

        if jobs:
            print(
                f"Extracted candidate cards using {selector}: "
                f"{len(jobs)}"
            )
            return list(jobs.values())

    # Distinguish a genuinely empty Open to Apply tab from
    # an extraction failure.
    body = clean_text(
        driver.find_element(By.TAG_NAME, "body").text
    ).lower()

    valid_empty_messages = [
        "no opportunities at the moment",
        "no eligible roles open for application",
        "no jobs available"
    ]

    if any(message in body for message in valid_empty_messages):
        print("Portal explicitly reports no active opportunities.")
        return []

    save_debug(driver, "job_extraction_failed")

    raise RuntimeError(
        "No listings extracted and no confirmed empty-state message "
        "was found. Inspect the debug HTML before changing jobs.json."
    )


# ================= MAIN =================

def check_jobs():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        # 1. Login through the direct login URL.
        login(driver)

        # 2. Open only Open to Apply.
        open_active_jobs(driver)

        # 3. Extract currently active opportunities.
        current_jobs = extract_jobs(driver)

        # 4. Compare with the previous saved results.
        old_jobs = load_old_jobs()
        old_set = {str(job).casefold() for job in old_jobs}

        new_jobs = [
            job for job in current_jobs
            if job.casefold() not in old_set
        ]

        print("Previously saved active listings:", len(old_jobs))
        print("Current active listings:", len(current_jobs))
        print("New active listings:", len(new_jobs))

        # 5. Email only newly discovered active opportunities.
        if new_jobs:
            send_email(new_jobs)
        else:
            print("No new Open to Apply opportunities.")

        # 6. Update history after successful extraction and alerting.
        save_jobs(current_jobs)

        print("Job history updated successfully.")

    except Exception as exc:
        print("ERROR:", str(exc))
        raise

    finally:
        driver.quit()


if __name__ == "__main__":
    check_jobs()
