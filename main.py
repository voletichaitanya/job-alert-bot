from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
import time
import json
import smtplib
import os

# ================== ENV VARIABLES ==================

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
APP_PASSWORD = os.getenv("APP_PASSWORD")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ================== EMAIL FUNCTION ==================

def send_email(new_jobs):

    sender = EMAIL
    receiver = EMAIL
    password = APP_PASSWORD

    body = "NEW JOBS FOUND:\n\n"

    for index, job in enumerate(new_jobs, start=1):

        clean_job = job.replace("–", "-")

        body += f"{index}. {clean_job}\n"

    msg = MIMEMultipart()

    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = f"{len(new_jobs)} New Job Alert(s)"

    msg.attach(
        MIMEText(body, "plain", "utf-8")
    )

    server = smtplib.SMTP(
        "smtp.gmail.com",
        587
    )

    server.starttls()

    server.login(
        sender,
        password
    )

    server.sendmail(
        sender,
        receiver,
        msg.as_string()
    )

    server.quit()

    print("Email sent successfully!")

# ================== TELEGRAM FUNCTION ==================

def send_telegram(new_jobs):

    message = f"NEW JOBS FOUND: {len(new_jobs)}\n\n"

    for index, job in enumerate(new_jobs, start=1):

        clean_job = job.replace("–", "-")

        message += f"{index}. {clean_job}\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    response = requests.post(
        url,
        data=data
    )

    print("Telegram response:", response.text)

    print("Telegram alert sent!")

# ================== MEMORY FUNCTIONS ==================

def load_old_jobs():

    try:

        with open("jobs.json", "r") as f:
            return json.load(f)

    except:
        return []

def save_jobs(jobs):

    with open("jobs.json", "w") as f:

        json.dump(
            jobs,
            f,
            indent=4
        )

# ================== MAIN FUNCTION ==================

def check_jobs():

    # ================== CHROME OPTIONS ==================

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # ================== DRIVER ==================

    service = Service(
        ChromeDriverManager().install()
    )

    driver = webdriver.Chrome(
        service=service,
        options=options
    )

    try:

        # ================== LOGIN ==================

        driver.get(
            "https://www.placements.codegnan.com/student/login"
        )

        time.sleep(5)

        print("Opened login page")

        driver.find_element(
            By.ID,
            "username"
        ).send_keys(EMAIL)

        driver.find_element(
            By.ID,
            "password"
        ).send_keys(PASSWORD)

        driver.find_element(
            By.XPATH,
            "//button[@type='submit']"
        ).click()

        time.sleep(8)

        print("Current URL:", driver.current_url)

        # ================== HANDLE LOGOUT SESSIONS ==================

        try:

            logout_btn = driver.find_element(
                By.XPATH,
                "//button[contains(text(),'Logout All Sessions')]"
            )

            logout_btn.click()

            time.sleep(3)

            driver.find_element(
                By.XPATH,
                "//button[@type='submit']"
            ).click()

            time.sleep(5)

            print("Handled logout sessions")

        except:
            print("No logout session popup")

        # ================== NAVIGATE ==================

        driver.get(
            "https://www.placements.codegnan.com/student/cr/job-listings"
        )

        time.sleep(8)

        print("Page title:", driver.title)

        # ================== EXTRACT JOBS ==================

        rows = driver.find_elements(
            By.XPATH,
            "//table/tbody/tr"
        )

        print(f"Rows found: {len(rows)}")

        current_jobs = []

        for row in rows:

            columns = row.find_elements(
                By.TAG_NAME,
                "td"
            )

            print(f"Columns found: {len(columns)}")

            if len(columns) >= 2:

                company = columns[0].text.strip()

                job_title = columns[1].text.strip()

                print("Company:", company)
                print("Job Title:", job_title)

                if company and job_title:

                    job_title = job_title.replace("–", "-")

                    job = f"{company} - {job_title}"

                    current_jobs.append(job)

                    print(job)

        print(f"Current jobs count: {len(current_jobs)}")

        # ================== COMPARE ==================

        old_jobs = load_old_jobs()

        print(f"Old jobs count: {len(old_jobs)}")

        new_jobs = [
            job for job in current_jobs
            if job not in old_jobs
        ]

        print(f"New jobs count: {len(new_jobs)}")

        # ================== OUTPUT ==================

        if current_jobs:

            print("\nNEW JOBS FOUND:\n")

            for job in new_jobs:
                print(job)

            # Send Email
            send_email(new_jobs)

            # Send Telegram
            send_telegram(new_jobs)

        else:

            print("\nNo new jobs")

        # ================== SAVE ==================

        save_jobs(current_jobs)

    except Exception as e:

        print("ERROR:", str(e))

        with open(
            "debug_page.html",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(driver.page_source)

        print("Saved debug_page.html")

    finally:

        driver.quit()

# ================== RUN ==================

if __name__ == "__main__":
    check_jobs()
