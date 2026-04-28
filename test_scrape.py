"""
Minimal test: login, search 1 job, get its description.
Prints every step so we can see exactly where it fails.
"""
import time, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus
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
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
wait = WebDriverWait(driver, 15)

# ── 1. Login ──
print("1. Logging in...")
driver.get("https://www.linkedin.com/login")
time.sleep(3)
driver.find_element(By.ID, "username").send_keys(EMAIL)
driver.find_element(By.ID, "password").send_keys(PASSW)
driver.find_element(By.XPATH, "//button[@type='submit']").click()
time.sleep(5)
print(f"   ✅ Logged in → {driver.current_url}")

# ── 2. Search ──
keyword = "AI engineer"
country = "Belgium"
url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&location={quote_plus(country)}&f_TPR=r604800"
print(f"\n2. Opening search: {url}")
driver.get(url)
try:
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-occludable-job-id]")))
    time.sleep(3)
except:
    print("   ⚠️ Timed out waiting for cards")

cards = driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")
print(f"   📋 {len(cards)} cards found")

# ── 3. Get first 3 job URLs ──
job_urls = []
for card in cards[:5]:
    try:
        a = card.find_element(By.CSS_SELECTOR, "a[href*='/jobs/view/']")
        href = a.get_attribute("href")
        title = a.text.strip()
        if href:
            job_urls.append((title, href))
    except:
        pass

print(f"   Extracted {len(job_urls)} job URLs:")
for i, (t, u) in enumerate(job_urls):
    print(f"     {i+1}. {t[:50]} → {u[:80]}...")

# ── 4. Get descriptions for first 3 ──
def expand_more():
    for sel in ["button.show-more-less-html__button--more", "button[aria-label='Show more']"]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1)
        except: pass
    try:
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            if btn.text.strip().lower() in ["…more","… more","more","see more","show more"]:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
    except: pass

for i, (title, job_url) in enumerate(job_urls[:3]):
    print(f"\n{'='*60}")
    print(f"  JOB {i+1}: {title}")
    print(f"{'='*60}")
    
    print(f"  → Navigating...")
    driver.get(job_url)
    
    print(f"  → Waiting 8s for page load...")
    time.sleep(8)
    
    print(f"  → Current URL: {driver.current_url}")
    print(f"  → Page title: {driver.title}")
    
    print(f"  → Scrolling down...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
    time.sleep(2)
    
    print(f"  → Expanding 'more' buttons...")
    expand_more()
    time.sleep(1)
    
    print(f"  → Reading body text...")
    body = driver.find_element(By.TAG_NAME, "body").text
    print(f"  → Body length: {len(body)} chars")
    
    marker = "about the job"
    idx = body.lower().find(marker)
    print(f"  → 'About the job' at index: {idx}")
    
    if idx != -1:
        desc = body[idx + len(marker):].strip()
        # Trim boilerplate
        for stopper in ["Set alert for similar jobs","Job search faster with Premium",
                        "Show more jobs like this","Report this job","See more jobs",
                        "Similar jobs","People also viewed","Meet the team","About the company"]:
            si = desc.find(stopper)
            if si != -1:
                desc = desc[:si].strip()
        print(f"  ✅ DESCRIPTION EXTRACTED: {len(desc)} chars")
        print(f"  Preview: {desc[:200]}...")
    else:
        print(f"  ❌ NO DESCRIPTION FOUND")
        print(f"  First 300 chars of body: {body[:300]}")
    
    # Screenshot
    driver.save_screenshot(f"test_job_{i+1}.png")
    print(f"  📸 Screenshot: test_job_{i+1}.png")
    
    print(f"  → Cooling down 4s...")
    time.sleep(4)

print("\n🏁 Test complete!")
input("Press Enter to close...")
driver.quit()
