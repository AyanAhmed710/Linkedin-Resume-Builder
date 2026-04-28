"""
Quick debug script — logs into LinkedIn, opens a job page,
takes a screenshot & dumps what the scraper actually sees.
"""

import time, os, csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSW = os.getenv("LINKEDIN_PASSWORD")

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=options)
driver.execute_script(
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
)
wait = WebDriverWait(driver, 15)

# ── Login ──
print("🔐 Logging in...")
driver.get("https://www.linkedin.com/login")
time.sleep(3)
driver.find_element(By.ID, "username").send_keys(EMAIL)
driver.find_element(By.ID, "password").send_keys(PASSW)
driver.find_element(By.XPATH, "//button[@type='submit']").click()
time.sleep(5)
print(f"✅ Logged in → {driver.current_url}")

# ── Pick a job URL from the existing CSV ──
csv_file = "linkedin_AI_jobs_Belgium_Netherlands_week_20260221_2349.csv"
if not os.path.exists(csv_file):
    # try any CSV in directory
    for f in os.listdir("."):
        if f.startswith("linkedin_") and f.endswith(".csv"):
            csv_file = f
            break

print(f"\n📂 Using CSV: {csv_file}")
with open(csv_file, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

if not rows:
    print("❌ No rows in CSV")
    driver.quit()
    exit()

# Test with first 2 jobs
for i, row in enumerate(rows[:2]):
    job_url = row.get("job_url", "")
    title   = row.get("job_title", "?")
    print(f"\n{'='*70}")
    print(f"  JOB {i+1}: {title}")
    print(f"  URL:  {job_url}")
    print(f"{'='*70}")

    # Navigate
    print("  → Navigating to job page...")
    driver.get(job_url)

    # Wait a good amount of time
    print("  → Waiting 8 seconds for page load...")
    time.sleep(8)

    # Screenshot
    ss_path = os.path.abspath(f"debug_job_{i+1}.png")
    driver.save_screenshot(ss_path)
    print(f"  📸 Screenshot saved: {ss_path}")

    # Page info
    print(f"  📍 Current URL:   {driver.current_url}")
    print(f"  📄 Page title:    {driver.title}")

    # Check what CSS selectors exist
    selectors_to_check = [
        "div.jobs-description",
        "div.jobs-box__html-content",
        "article.jobs-description__container",
        "div#job-details",
        "div.show-more-less-html",
        "div.jobs-description-content",
        "section.show-more-less-html",
    ]
    print("\n  🔍 Checking CSS selectors:")
    for sel in selectors_to_check:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            text_preview = els[0].text[:150].replace("\n", " ↵ ")
            print(f"    ✅ {sel}  ({len(els)} found)")
            print(f"       Preview: {text_preview}")
        else:
            print(f"    ❌ {sel}  (not found)")

    # Body text — look for "about the job"
    body = driver.find_element(By.TAG_NAME, "body").text
    marker = "about the job"
    idx = body.lower().find(marker)
    print(f"\n  🔎 Body text length: {len(body)} chars")
    print(f"  🔎 'About the job' found at index: {idx}")

    if idx != -1:
        snippet = body[idx:idx+300].replace("\n", " ↵ ")
        print(f"  📝 Snippet: {snippet}")
    else:
        # Show the first 500 chars of body to see what IS there
        preview = body[:500].replace("\n", " ↵ ")
        print(f"  📝 First 500 chars of body:\n     {preview}")

    print(f"\n  ⏳ Waiting 4s before next job...")
    time.sleep(4)

print("\n🏁 Debug complete. Check the screenshots!")
input("Press Enter to close browser...")
driver.quit()
