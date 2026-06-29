"""
scraper_service.py
==================
Importable LinkedIn job scraper service.
Wraps linkedinscraper2.py logic into a callable function with log callbacks.
"""

import time
import csv
import os
from datetime import datetime
from urllib.parse import quote_plus
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# --- RELEVANCE FILTER ---
# =============================================================================
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
# --- SHARED DESCRIPTION HELPERS (used by run_scraper) ---
# =============================================================================
def _click_all_expanders(driver):
    """Click every show-more / … more button to expand full description."""
    for sel in ["button.show-more-less-html__button--more",
                "button[aria-label='Show more']"]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
        except:
            pass
    try:
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            if btn.text.strip().lower() in ["…more", "… more", "more", "see more", "show more"]:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.5)
    except:
        pass
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

def _extract_about_the_job(body_text: str) -> str:
    """Slice out the 'About the job' block from full body text."""
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


# =============================================================================
# --- MAIN SERVICE FUNCTION ---
# =============================================================================
def run_scraper(search_keyword, countries, jobs_per_country, date_posted,
                log_callback=None, output_dir=None, email=None, password=None):
    """
    Run the LinkedIn job scraper.

    Parameters
    ----------
    search_keyword   : str
    countries        : list[str]
    jobs_per_country : int
    date_posted      : str   ("24h" | "week" | "month" | "any")
    log_callback     : callable(str) — receives log messages
    output_dir       : str — directory for the CSV; defaults to BASE_DIR
    email            : str — LinkedIn email (overrides .env)
    password         : str — LinkedIn password (overrides .env)

    Returns
    -------
    str — filename of the generated CSV (or None)
    """
    if output_dir is None:
        output_dir = BASE_DIR

    # Use passed credentials; fall back to .env if not provided
    load_dotenv(override=True)
    LINKEDIN_EMAIL    = email    or os.getenv("LINKEDIN_EMAIL")
    LINKEDIN_PASSWORD = password or os.getenv("LINKEDIN_PASSWORD")

    def log(msg):
        if log_callback:
            log_callback(str(msg))

    # ── Chrome setup ──────────────────────────────────────────────────────
    log("🌐 Launching Chrome...")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options, version_main=149)
    wait = WebDriverWait(driver, 15)

    # ── internal helpers ──────────────────────────────────────────────────
    def build_url(keyword, location, dp):
        date_param = {"24h": "r86400", "week": "r604800", "month": "r2592000"}.get(dp, "")
        url = (f"https://www.linkedin.com/jobs/search/"
               f"?keywords={quote_plus(keyword)}&location={quote_plus(location)}")
        if date_param:
            url += f"&f_TPR={date_param}"
        return url

    def login():
        log("🔐 Logging in to LinkedIn...")
        driver.get("https://www.linkedin.com/login")

        # Wait for the login form to render
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username webauthn']"))
        )
        log("  ✔ Login form rendered")

        # Use JS to fill fields — avoids interactability issues with React's dual mobile/desktop DOM
        def js_fill(css_selector, value):
            # Find the LAST matching element (desktop version is last in DOM)
            script = """
                var inputs = document.querySelectorAll(arguments[0]);
                var el = inputs[inputs.length - 1];
                var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                setter.call(el, arguments[1]);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                return el;
            """
            return driver.execute_script(script, css_selector, value)

        js_fill("input[autocomplete='username webauthn']", LINKEDIN_EMAIL)
        log("  ✔ Email filled")
        time.sleep(0.3)
        js_fill("input[autocomplete='current-password']", LINKEDIN_PASSWORD)
        log("  ✔ Password filled")
        time.sleep(0.3)

        # Click Sign in — LinkedIn uses type="button" not type="submit"
        sign_in_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "(//button[@type='button'][.//span[text()='Sign in']])[last()]"))
        )
        sign_in_btn.click()
        time.sleep(4)

        # Handle LinkedIn email verification / security challenge
        verification_keywords = ["checkpoint", "challenge", "verification", "verify", "pin"]
        if any(kw in driver.current_url for kw in verification_keywords):
            log("⚠️  LinkedIn sent a verification code to your email.")
            log("👉 Enter the code in the browser window, then click 'Submit'.")
            log("⏳ Waiting up to 3 minutes for you to complete verification...")
            try:
                # Wait until URL leaves the verification page (user submitted code)
                WebDriverWait(driver, 180).until(
                    lambda d: not any(kw in d.current_url for kw in verification_keywords)
                )
                log("✅ Verification complete!")
            except:
                raise RuntimeError("Verification timed out — code was not entered within 3 minutes")

        log(f"✅ Logged in → {driver.current_url}")

    log(f"🔎 Domain filter active: {len(AI_ML_DOMAIN_TERMS)} terms")

    def collect_job_data(country):
        url = build_url(search_keyword, country, date_posted)
        log(f"  🔗 {url}")
        driver.get(url)
        try:
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "li[data-occludable-job-id]")
            ))
            time.sleep(3)
        except:
            log("  ⚠️ Timed out waiting for cards.")
            return []

        cards = driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")
        log(f"  📋 {len(cards)} cards found")

        jobs, skipped = [], 0
        for card in cards:
            if len(jobs) >= jobs_per_country:
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
                    log(f"  ⏭️ Skipped: {title}")
                    continue

                try:
                    company = card.find_element(By.CSS_SELECTOR,
                        "span.job-card-container__primary-description").text.strip()
                except:
                    company = ""
                try:
                    loc = card.find_element(By.CSS_SELECTOR,
                        "li.job-card-container__metadata-item").text.strip()
                except:
                    loc = ""

                if job_url:
                    jobs.append({
                        "country":      country,
                        "job_title":    title,
                        "company_name": company,
                        "location":     loc,
                        "job_url":      job_url,
                    })
            except Exception as e:
                log(f"  ⚠️ Card parse error: {e}")

        if skipped:
            log(f"  🚫 Filtered {skipped} irrelevant jobs")
        return jobs

    def get_description(job_url):
        """
        1. Load job page, wait for render
        2. Scroll to trigger lazy-loaded content
        3. Click ALL expand buttons (removes '… more' truncation)
        4. Read body.text and extract 'About the job' block
        """
        driver.get(job_url)
        time.sleep(6)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
        time.sleep(2)

        _click_all_expanders(driver)
        time.sleep(1)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        desc = _extract_about_the_job(body_text)

        # Retry once if empty
        if not desc:
            log("    🔄 Retrying after longer wait...")
            time.sleep(6)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
            time.sleep(1)
            _click_all_expanders(driver)
            time.sleep(1)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            desc = _extract_about_the_job(body_text)

        if not desc:
            log("    ⚠️ Could not extract description")

        return desc

    # ── main flow ─────────────────────────────────────────────────────────
    try:
        login()
        all_jobs = []

        for country in countries:
            log(f"\n{'='*60}")
            log(f"  🌍 Country: {country}  |  Target: {jobs_per_country} jobs")
            log(f"{'='*60}")

            jobs = collect_job_data(country)
            if not jobs:
                log(f"  ⚠️ No jobs found for {country}")
                continue

            log("  ✅ Metadata collected — fetching descriptions...")

            for idx, job in enumerate(jobs):
                log(f"\n  🔍 ({idx+1}/{len(jobs)}) {job['job_title']} @ {job['company_name']}")
                desc = get_description(job["job_url"])
                job["job_description"] = desc
                if desc:
                    log(f"       ✅ {len(desc)} chars")
                    log(f"       Preview: {desc[:120]}...")
                else:
                    log("       ⚠️ Empty description")
                time.sleep(3)

            all_jobs.extend(jobs)

        # ── save CSV ──────────────────────────────────────────────────────
        csv_filename = None
        if all_jobs:
            timestamp    = datetime.now().strftime("%Y%m%d_%H%M")
            country_str  = "_".join(c.replace(" ", "") for c in countries)
            csv_filename = f"linkedin_AI_jobs_{country_str}_{date_posted}_{timestamp}.csv"
            csv_path     = os.path.join(output_dir, csv_filename)

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=all_jobs[0].keys())
                writer.writeheader()
                writer.writerows(all_jobs)

            empty = sum(1 for j in all_jobs if not j.get("job_description"))
            log(f"\n{'='*60}")
            log(f"📁 Saved {len(all_jobs)} jobs → {csv_filename}")
            log(f"📊 With description: {len(all_jobs) - empty}/{len(all_jobs)}")
            if empty:
                log(f"⚠️  {empty} jobs had empty descriptions")
            log(f"{'='*60}")
        else:
            log("\n⚠️ No jobs collected.")

        return csv_filename

    except Exception as e:
        log(f"❌ Error: {e}")
        raise
    finally:
        try:
            driver.quit()
        except:
            pass
        log("🏁 Done. Browser closed.")
