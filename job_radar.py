import os
import requests
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
JOOBLE_KEY     = os.getenv("JOOBLE_KEY")
SHEET_ID       = os.getenv("GOOGLE_SHEET_ID")
CREDS_FILE     = os.path.join(os.path.dirname(__file__), "credentials.json")

KEYWORDS = ["C# developer", ".NET developer", "software engineer", "backend developer"]
ADZUNA_COUNTRIES = {"de": "Germany", "nl": "Netherlands", "be": "Belgium"}

# ── Google Sheets ─────────────────────────────────────────────────────────────

def get_sheet_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds).spreadsheets()

def clear_and_write(jobs):
    service = get_sheet_service()

    headers = [["Title", "Company", "Location", "Country", "Source",
                 "Posted", "Salary", "Match Keywords", "Apply URL"]]

    rows = []
    for job in jobs:
        rows.append([
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("country", ""),
            job.get("source", ""),
            job.get("posted", ""),
            job.get("salary", ""),
            job.get("keywords", ""),
            job.get("url", ""),
        ])

    service.values().clear(spreadsheetId=SHEET_ID, range="Sheet1").execute()
    service.values().update(
        spreadsheetId=SHEET_ID,
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": headers + rows}
    ).execute()

    print(f"Written {len(rows)} jobs to Google Sheet")

# ── Adzuna ────────────────────────────────────────────────────────────────────

def fetch_adzuna(keyword, country_code, country_name):
    jobs = []
    try:
        url = (
            f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
            f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
            f"&results_per_page=50&what={keyword.replace(' ', '+')}"
            f"&content-type=application/json"
        )
        r = requests.get(url, timeout=10)
        data = r.json()
        for item in data.get("results", []):
            posted = item.get("created", "")[:10]
            jobs.append({
                "title":    item.get("title", ""),
                "company":  item.get("company", {}).get("display_name", ""),
                "location": item.get("location", {}).get("display_name", ""),
                "country":  country_name,
                "source":   "Adzuna",
                "posted":   posted,
                "salary":   f"{item.get('salary_min','')}-{item.get('salary_max','')}".strip("-"),
                "keywords": keyword,
                "url":      item.get("redirect_url", ""),
            })
    except Exception as e:
        print(f"Adzuna error ({country_code}, {keyword}): {e}")
    return jobs

# ── Arbeitsagentur ────────────────────────────────────────────────────────────

def fetch_arbeitsagentur(keyword):
    jobs = []
    try:
        url = (
            f"https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
            f"?was={keyword.replace(' ', '+')}&angebotsart=1&size=50"
        )
        headers = {"X-API-Key": "jobboerse-jobsuche"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        for item in data.get("stellenangebote", []):
            jobs.append({
                "title":    item.get("titel", ""),
                "company":  item.get("arbeitgeber", ""),
                "location": item.get("arbeitsort", {}).get("ort", ""),
                "country":  "Germany",
                "source":   "Arbeitsagentur",
                "posted":   item.get("eintrittsdatum", "")[:10],
                "salary":   "",
                "keywords": keyword,
                "url":      f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{item.get('hashId','')}",
            })
    except Exception as e:
        print(f"Arbeitsagentur error ({keyword}): {e}")
    return jobs

# ── EURES ─────────────────────────────────────────────────────────────────────

def fetch_eures(keyword):
    jobs = []
    try:
        url = "https://eures.europa.eu/api/jv-search"
        payload = {
            "keywords": keyword,
            "lang": "en",
            "country": ["DE", "NL", "BE", "LU"],
            "resultsPerPage": 50,
            "page": 1
        }
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        for item in data.get("data", {}).get("items", []):
            jobs.append({
                "title":    item.get("title", ""),
                "company":  item.get("employer", {}).get("name", ""),
                "location": item.get("location", {}).get("city", ""),
                "country":  item.get("location", {}).get("countryCode", ""),
                "source":   "EURES",
                "posted":   item.get("publicationDate", "")[:10],
                "salary":   "",
                "keywords": keyword,
                "url":      f"https://eures.europa.eu/jobs/{item.get('id','')}",
            })
    except Exception as e:
        print(f"EURES error ({keyword}): {e}")
    return jobs

# ── Remotive ──────────────────────────────────────────────────────────────────

def fetch_remotive(keyword):
    jobs = []
    try:
        url = f"https://remotive.com/api/remote-jobs?search={keyword.replace(' ','+')}&limit=50"
        r = requests.get(url, timeout=10)
        data = r.json()
        for item in data.get("jobs", []):
            jobs.append({
                "title":    item.get("title", ""),
                "company":  item.get("company_name", ""),
                "location": item.get("candidate_required_location", "Worldwide"),
                "country":  "Remote",
                "source":   "Remotive",
                "posted":   item.get("publication_date", "")[:10],
                "salary":   item.get("salary", ""),
                "keywords": keyword,
                "url":      item.get("url", ""),
            })
    except Exception as e:
        print(f"Remotive error ({keyword}): {e}")
    return jobs

# ── Jooble ────────────────────────────────────────────────────────────────────

def fetch_jooble(keyword):
    jobs = []
    locations = ["Germany", "Netherlands", "Belgium", "Luxembourg"]
    for location in locations:
        try:
            url = f"https://jooble.org/api/{JOOBLE_KEY}"
            payload = {"keywords": keyword, "location": location, "page": "1"}
            r = requests.post(url, json=payload, timeout=10)
            data = r.json()
            for item in data.get("jobs", []):
                jobs.append({
                    "title":    item.get("title", ""),
                    "company":  item.get("company", ""),
                    "location": item.get("location", ""),
                    "country":  location,
                    "source":   "Jooble",
                    "posted":   item.get("updated", "")[:10],
                    "salary":   item.get("salary", ""),
                    "keywords": keyword,
                    "url":      item.get("link", ""),
                })
        except Exception as e:
            print(f"Jooble error ({keyword}, {location}): {e}")
    return jobs

# ── Deduplicate ───────────────────────────────────────────────────────────────

def deduplicate(jobs):
    seen = set()
    unique = []
    for job in jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen and job["title"]:
            seen.add(key)
            unique.append(job)
    return unique

# ── Sort ──────────────────────────────────────────────────────────────────────

def sort_by_date(jobs):
    def parse_date(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d")
        except:
            return datetime.min
    return sorted(jobs, key=lambda j: parse_date(j["posted"]), reverse=True)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"JobRadar starting — {datetime.now()}")
    all_jobs = []

    for keyword in KEYWORDS:
        print(f"Searching: {keyword}")

        for code, name in ADZUNA_COUNTRIES.items():
            all_jobs += fetch_adzuna(keyword, code, name)

        all_jobs += fetch_arbeitsagentur(keyword)
        all_jobs += fetch_eures(keyword)
        all_jobs += fetch_remotive(keyword)
        all_jobs += fetch_jooble(keyword)

    print(f"Total raw jobs: {len(all_jobs)}")

    all_jobs = deduplicate(all_jobs)
    print(f"After deduplication: {len(all_jobs)}")

    all_jobs = sort_by_date(all_jobs)
    print(f"Sorted by date. Writing to Google Sheet...")

    clear_and_write(all_jobs)
    print("Done.")

if __name__ == "__main__":
    main()
