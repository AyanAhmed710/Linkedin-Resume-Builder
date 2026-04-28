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

# ✏️ Paste any LinkedIn job URL here to debug
TEST_JOB_URL = "https://www.linkedin.com/jobs/view/4373755064/?alternateChannel=search&eBP=BUDGET_EXHAUSTED_JOB&trk=d_flagship3_search_srp_jobs&refId=qi4YTIqEd4RoGT7JeJ%2FZ7g%3D%3D&trackingId=skaWeg4LAT5i%2FNs79ynpng%3D%3D"

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

# Login
print("🔐 Logging in...")
driver.get("https://www.linkedin.com/login")
time.sleep(3)
driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
driver.find_element(By.XPATH, "//button[@type='submit']").click()
time.sleep(5)
print(f"✅ Logged in")

# Open job page
driver.get(TEST_JOB_URL)
time.sleep(5)
print(f"📄 Page title: {driver.title}")

# Try clicking show more
try:
    btn = driver.find_element(By.CSS_SELECTOR, "button.show-more-less-html__button--more")
    driver.execute_script("arguments[0].click();", btn)
    time.sleep(1)
    print("✅ Clicked show more")
except:
    print("ℹ️ No show more button found")

# --- Test every selector ---
selectors = [
    "div.show-more-less-html__markup",
    "div#job-details",
    "div.jobs-description-content__text",
    "div.jobs-description__content",
    "section.jobs-description",
    "div.jobs-description",
    "div[class*='description']",
    "article",
    "div.jobs-box__html-content",
]

print("\n🔎 Selector results:")
for sel in selectors:
    try:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            text = els[0].text.strip()[:80]
            print(f"  ✅ FOUND ({len(els)}) → {sel}")
            print(f"     Text preview: {text}")
        else:
            print(f"  ❌ not found  → {sel}")
    except Exception as e:
        print(f"  ❌ error       → {sel}: {e}")

# --- Save full page source ---
with open("job_page_source.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("\n💾 Full page HTML saved to job_page_source.html")

# --- Print all text around 'About the job' ---
body_text = driver.find_element(By.TAG_NAME, "body").text
idx = body_text.lower().find("about the job")
if idx != -1:
    snippet = body_text[idx:idx+500]
    print(f"\n📝 Text around 'About the job':\n{'-'*50}")
    print(snippet)
else:
    print("\n⚠️ 'About the job' text not found in body")
    print("📝 Full body text (first 3000 chars):")
    print(body_text[:3000])

driver.quit()
print("\n🏁 Done.")