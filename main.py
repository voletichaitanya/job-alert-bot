from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import smtplib
import os

# ================== ENV VARIABLES ==================

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
APP_PASSWORD = os.getenv("APP_PASSWORD")

# ✅ Validate env variables
if not EMAIL or not PASSWORD or not APP_PASSWORD:
    raise Exception("❌ Missing environment variables")

print("✅ ENV VARIABLES LOADED")

# ================== EMAIL FUNCTION ==================

def send_email(new_jobs):
    sender = EMAIL
    password = APP_PASSWORD
    receiver = EMAIL

    message = "Subject: 🚨 New Job Alert!\n\n"

    for job in new_jobs:
        message += job + "\n"

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, message)
        server.quit()

        print("📧 Email sent successfully!")

    except Exception as e:
        print("❌ Email error:", e)

# ================== MEMORY FUNCTIONS ==================

def load_old_jobs():
    try:
        with open("jobs.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_jobs(jobs):
    with open("jobs.json", "w") as f:
        json.dump(jobs, f)

# ================== MAIN LOGIC ==================

def check_jobs():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 10)

    try:
        print("🌐 Opening login page...")
        driver.get("https://www.placements.codegnan.com/student/login")

        # Wait for login fields
        wait.until(EC.presence_of_element_located((By.ID, "username")))

        print("🔐 Logging in...")
        driver.find_element(By.ID, "username").send_keys(EMAIL)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # Handle logout popup (optional)
        try:
            wait.until(EC.presence_of_element_located(
                (By.XPATH, "//button[contains(text(),'Logout All Sessions')]")
            ))
            driver.find_element(By.XPATH, "//button[contains(text(),'Logout All Sessions')]").click()
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
        except:
            pass

        print("📄 Opening job listings...")
        driver.get("https://www.placements.codegnan.com/student/job-listings")

        wait.until(EC.presence_of_element_located((By.XPATH, "//table/tbody/tr")))

        # EXTRACT JOBS
        rows = driver.find_elements(By.XPATH, "//table/tbody/tr")

        current_jobs = []

        for row in rows:
            columns = row.find_elements(By.TAG_NAME, "td")
            if len(columns) >= 2:
                company = columns[0].text.strip()
                job_title = columns[1].text.strip()
                job = f"{company} - {job_title}"
                current_jobs.append(job)

        print(f"📊 Found {len(current_jobs)} jobs")

        # COMPARE
        old_jobs = load_old_jobs()
        new_jobs = [job for job in current_jobs if job not in old_jobs]

        if new_jobs:
            print("\n🔥 NEW JOBS FOUND:\n")
            for job in new_jobs:
                print(job)

            send_email(new_jobs)
        else:
            print("\nNo new jobs")

        # SAVE
        save_jobs(current_jobs)

    except Exception as e:
        print("❌ ERROR:", e)

    finally:
        driver.quit()
        print("🧹 Browser closed")

# ================== RUN ==================

if __name__ == "__main__":
    check_jobs()
