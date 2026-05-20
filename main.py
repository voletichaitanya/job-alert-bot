from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

import time
import json
import smtplib

# ================== ENV VARIABLES ==================

EMAIL = "chaituvoleti6300@gmail.com"
PASSWORD = "Chaitu@6300397558"
APP_PASSWORD = "hgzbsrkrfemrywvy"

# ================== EMAIL FUNCTION ==================

def send_email(new_jobs):

    sender = EMAIL
    receiver = EMAIL
    password = APP_PASSWORD

    message = "Subject: New Job Alert!\n\n"
    message += "NEW JOBS FOUND:\n\n"

    for job in new_jobs:

        # Convert special characters to normal ASCII
        clean_job = job.replace("–", "-")

        message += clean_job + "\n"

    server = smtplib.SMTP("smtp.gmail.com", 587)

    server.starttls()

    server.login(sender, password)

    server.sendmail(
        sender,
        receiver,
        message.encode("ascii", "ignore").decode()
    )

    server.quit()

    print("Email sent successfully!")

# ================== MEMORY FUNCTIONS ==================

def load_old_jobs():
    try:
        with open("jobs.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_jobs(jobs):
    with open("jobs.json", "w") as f:
        json.dump(jobs, f, indent=4)

# ================== MAIN LOGIC ==================

def check_jobs():

    options = Options()

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(
        service=service,
        options=options
    )

    # ================== LOGIN ==================

    driver.get("https://www.placements.codegnan.com/student/login")

    time.sleep(3)

    driver.find_element(By.ID, "username").send_keys(EMAIL)

    driver.find_element(By.ID, "password").send_keys(PASSWORD)

    driver.find_element(
        By.XPATH,
        "//button[@type='submit']"
    ).click()

    time.sleep(3)

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

        time.sleep(3)

    except:
        pass

    # ================== NAVIGATE TO JOBS ==================

    driver.get(
        "https://www.placements.codegnan.com/student/cr/job-listings"
    )

    time.sleep(5)

    # ================== EXTRACT JOBS ==================

    rows = driver.find_elements(
        By.XPATH,
        "//table/tbody/tr"
    )

    current_jobs = []

    for row in rows:

        columns = row.find_elements(By.TAG_NAME, "td")

        if len(columns) >= 2:

            company = columns[0].text.strip()

            job_title = columns[1].text.strip()

            # Replace special dash
            job_title = job_title.replace("–", "-")

            job = f"{company} - {job_title}"

            current_jobs.append(job)

    # ================== COMPARE ==================

    old_jobs = load_old_jobs()

    new_jobs = [
        job for job in current_jobs
        if job not in old_jobs
    ]

    # ================== OUTPUT ==================

    if new_jobs:

        print("\nNEW JOBS FOUND:\n")

        for job in new_jobs:
            print(job)

        send_email(new_jobs)

    else:
        print("\nNo new jobs")

    # ================== SAVE ==================

    save_jobs(current_jobs)

    driver.quit()

# ================== RUN ==================

if __name__ == "__main__":
    check_jobs()
