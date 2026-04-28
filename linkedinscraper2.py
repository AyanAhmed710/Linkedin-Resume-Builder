from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from urllib.parse import quote_plus
from dotenv import load_dotenv
import time
import csv
import os
import re

load_dotenv()

# =============================================================================
# --- CONFIG ---
# =============================================================================
SEARCH_KEYWORD   = "AI engineer"
COUNTRIES        = ["Belgium", "Netherlands"]
JOBS_PER_COUNTRY = 5
DATE_POSTED      = "week"    # "any" | "24h" | "week" | "month"

# =============================================================================
# --- CREDENTIALS ---
# =============================================================================
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# =============================================================================
# --- RELEVANCE FILTER ---
# =============================================================================
# ONLY pure AI/ML domain terms are listed here.
# Generic role words like "engineer", "developer", "intern", "consultant"
# are intentionally absent — they must NOT trigger a match on their own.
# A job title must contain at least one term from this set to be accepted.
AI_ML_DOMAIN_TERMS = {
    # Core AI / ML
    "ai", "artificial intelligence",
    "machine learning", "ml",
    "deep learning",
    "neural network", "neural networks",
    "nlp", "natural language processing",
    "llm", "large language model",
    "generative ai", "gen ai", "genai",
    "computer vision",
    "reinforcement learning",
    "mlops",
    "ai/ml", "ml/ai",
    # Frameworks — these never appear in non-AI job titles
    "pytorch", "tensorflow", "transformers",
    # Unambiguously AI-specific roles
    "prompt engineer", "prompt engineering",
    "applied scientist",
    "research scientist",
    "data scientist",
    # Data engineering (closely related)
    "data engineer", "data engineering",
    "analytics engineer",
    "big data", "etl",
}

def is_relevant_job(title: str) -> bool:
    """
    Return True only if the job title contains at least one pure
    AI/ML domain term.  Titles like 'Software Developer', 'Sales Intern',
    or 'IT Consultant' will never match because they contain none of
    the domain terms above.
    """
    title_lower = title.lower()
    return any(term in title_lower for term in AI_ML_DOMAIN_TERMS)

# =============================================================================
# --- CHROME SETUP ---
# =============================================================================
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
wait = WebDriverWait(driver, 15)

# =============================================================================
# --- HELPERS ---
# =============================================================================
def login():
    print("🔐 Logging in...")
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)
    driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(5)
    print(f"✅ Logged in → {driver.current_url}")

def build_url(keyword, location, date_posted):
    date_param = {"24h": "r86400", "week": "r604800", "month": "r2592000"}.get(date_posted, "")
    url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
    if date_param:
        url += f"&f_TPR={date_param}"
    return url

print(f"🔎 Domain filter active: {len(AI_ML_DOMAIN_TERMS)} terms")

def collect_job_data(country):
    url = build_url(SEARCH_KEYWORD, country, DATE_POSTED)
    print(f"  🔗 {url}")
    driver.get(url)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-occludable-job-id]")))
        time.sleep(3)
    except:
        print("  ⚠️ Timed out waiting for cards.")
        return []

    cards = driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")
    print(f"  📋 {len(cards)} cards found")

    jobs = []
    skipped = 0
    for card in cards:
        if len(jobs) >= JOBS_PER_COUNTRY:
            break
        try:
            try:
                a       = card.find_element(By.CSS_SELECTOR, "a.job-card-list__title--link")
                job_url = a.get_attribute("href")
                title   = a.find_element(By.CSS_SELECTOR, "strong").text.strip()
            except:
                a       = card.find_element(By.CSS_SELECTOR, "a[href*='/jobs/view/']")
                job_url = a.get_attribute("href")
                title   = a.text.strip()

            if not is_relevant_job(title):
                skipped += 1
                print(f"  ⏭️ Skipped: {title}")
                continue

            try:
                company = card.find_element(By.CSS_SELECTOR, "span.job-card-container__primary-description").text.strip()
            except:
                company = ""
            try:
                location = card.find_element(By.CSS_SELECTOR, "li.job-card-container__metadata-item").text.strip()
            except:
                location = ""

            if job_url:
                jobs.append({
                    "country":      country,
                    "job_title":    title,
                    "company_name": company,
                    "location":     location,
                    "job_url":      job_url,
                })
        except Exception as e:
            print(f"  ⚠️ Card parse error: {e}")

    if skipped:
        print(f"  🚫 Filtered {skipped} irrelevant jobs")
    return jobs

def click_all_expanders():
    """
    Click every possible expand/show-more button so the full
    description is visible before we read body.text.
    """
    # 1. Known CSS selectors
    for sel in ["button.show-more-less-html__button--more",
                "button[aria-label='Show more']"]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
        except:
            pass

    # 2. Any button with expand-like text
    try:
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            if btn.text.strip().lower() in ["…more", "… more", "more", "see more", "show more"]:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.5)
    except:
        pass

    # 3. Any element containing "…more" text (LinkedIn's inline truncation)
    try:
        for el in driver.find_elements(By.XPATH,
                "//*[contains(text(),'…more') or contains(text(),'… more')]"):
            try:
                driver.execute_script("arguments[0].click();", el)
                time.sleep(0.5)
            except:
                pass
    except:
        pass

def extract_about_the_job(body_text: str) -> str:
    """
    Slice out everything between 'About the job' heading and the
    first known LinkedIn boilerplate stopper.
    """
    marker = "about the job"
    idx = body_text.lower().find(marker)
    if idx == -1:
        return ""

    desc = body_text[idx + len(marker):].strip()

    stoppers = [
        "Set alert for similar jobs",
        "Job search faster with Premium",
        "Show more jobs like this",
        "Report this job",
        "See more jobs",
        "Similar jobs",
        "People also viewed",
        "Meet the team",
        "About the company",
        "How you match",
    ]
    for stopper in stoppers:
        i = desc.find(stopper)
        if i != -1:
            desc = desc[:i].strip()

    return desc

def get_description(job_url):
    """
    1. Load job page and wait for full render
    2. Scroll to trigger lazy-loaded content
    3. Click ALL expand buttons (removes '… more' truncation)
    4. Read body.text and extract 'About the job' block
    """
    driver.get(job_url)
    time.sleep(6)   # wait for initial render

    # Scroll down 1/3 of page to trigger lazy-load
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
    time.sleep(2)

    # Click all expanders to get full text
    click_all_expanders()
    time.sleep(1)

    # Read and extract
    body_text = driver.find_element(By.TAG_NAME, "body").text
    desc = extract_about_the_job(body_text)

    # If empty, retry once with longer wait (page may still be loading)
    if not desc:
        print("    🔄 Retrying after longer wait...")
        time.sleep(6)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
        time.sleep(1)
        click_all_expanders()
        time.sleep(1)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        desc = extract_about_the_job(body_text)

    if not desc:
        print("    ⚠️ Could not extract description")

    return desc

# =============================================================================
# --- MAIN ---
# =============================================================================
login()
all_jobs = []

for country in COUNTRIES:
    print(f"\n{'='*60}")
    print(f"  Country: {country}  |  Target: {JOBS_PER_COUNTRY} jobs")
    print(f"{'='*60}")

    jobs = collect_job_data(country)
    if not jobs:
        print(f"  ⚠️ No jobs found for {country}")
        continue

    print(f"  ✅ Metadata collected — fetching descriptions...")

    for idx, job in enumerate(jobs):
        print(f"\n  🔍 ({idx+1}/{len(jobs)}) {job['job_title']} @ {job['company_name']}")
        desc = get_description(job["job_url"])
        job["job_description"] = desc
        if desc:
            print(f"       ✅ {len(desc)} chars")
            print(f"       Preview: {desc[:120]}...")
        else:
            print(f"       ⚠️ Empty description")
        time.sleep(3)

    all_jobs.extend(jobs)

# =============================================================================
# --- SAVE CSV ---
# =============================================================================
if all_jobs:
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M")
    country_str = "_".join(c.replace(" ", "") for c in COUNTRIES)
    csv_file    = f"linkedin_AI_jobs_{country_str}_{DATE_POSTED}_{timestamp}.csv"

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_jobs[0].keys())
        writer.writeheader()
        writer.writerows(all_jobs)

    empty = sum(1 for j in all_jobs if not j["job_description"])
    print(f"\n{'='*60}")
    print(f"📁 Saved {len(all_jobs)} jobs → {csv_file}")
    print(f"📊 With description: {len(all_jobs) - empty}/{len(all_jobs)}")
    if empty:
        print(f"⚠️  {empty} jobs had empty descriptions")
    print(f"{'='*60}")
else:
    print("\n⚠️ No jobs collected.")

driver.quit()
print("🏁 Done.")