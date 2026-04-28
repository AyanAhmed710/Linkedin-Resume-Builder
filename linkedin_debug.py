from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import time
import os

load_dotenv()

LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# Login
print("🔐 Logging in...")
driver.get("https://www.linkedin.com/login")
time.sleep(3)
driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
driver.find_element(By.XPATH, "//button[@type='submit']").click()
time.sleep(5)
print(f"✅ Logged in. URL: {driver.current_url}")

# Go to jobs search
url = "https://www.linkedin.com/jobs/search/?keywords=AI&location=Belgium"
driver.get(url)
print(f"\n🔗 Navigated to: {url}")

# Wait 10 seconds for page to fully load
print("⏳ Waiting 10 seconds for page to render...")
time.sleep(10)

print(f"\n📄 Page title: {driver.title}")
print(f"📄 Current URL: {driver.current_url}")

# --- Try every possible job card selector and report what's found ---
selectors_to_try = [
    "a.base-card__full-link",
    "div.base-card",
    "li.jobs-search-results__list-item",
    "div.job-card-container",
    "a.job-card-list__title",
    "div[data-job-id]",
    "li[data-occludable-job-id]",
    "div.scaffold-layout__list-container li",
    "ul.jobs-search__results-list li",
    "div.jobs-search-results-list li",
]

print("\n🔎 Testing selectors:")
for sel in selectors_to_try:
    els = driver.find_elements(By.CSS_SELECTOR, sel)
    status = f"✅ FOUND {len(els)}" if els else "❌ not found"
    print(f"  {status:20s} → {sel}")

# --- Save page source to file so you can inspect it ---
with open("linkedin_page_source.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("\n💾 Full page source saved to: linkedin_page_source.html")
print("    Open this file in browser or text editor to find correct selectors.")

# --- Print first 3000 chars of body text so we can see structure ---
body_text = driver.find_element(By.TAG_NAME, "body").text
print(f"\n📝 Body text (first 2000 chars):\n{'-'*50}")
print(body_text[:2000])

driver.quit()
print("\n🏁 Debug done.")