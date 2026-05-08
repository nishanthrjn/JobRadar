import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
SHEET_ID       = os.getenv("GOOGLE_SHEET_ID")
CREDS_FILE     = os.path.join(os.path.dirname(__file__), "credentials.json")

TARGET_COMPANIES = [
    "siemens", "bosch", "sap", "continental", "capgemini",
    "atos", "ibm", "microsoft", "amazon", "msg systems",
    "gft", "atruvia", "adesso", "bechtle", "cgi",
    "deloitte", "kpmg", "thoughtworks", "accenture",
    "infosys", "wipro", "hcl", "deutsche telekom",
    "deutsche bank", "allianz", "bmw", "mercedes",
    "volkswagen", "lufthansa", "t-systems"
]

SEARCH_TERMS = [".NET developer", "C# developer", "software engineer", "backend developer"]
COUNTRIES    = {"de": "Germany", "nl": "Netherlands", "be": "Belgium"}

GERMAN_HIGH = [
    "c1", "c2", "b2", "fließend deutsch", "fluent german",
    "verhandlungssicher", "muttersprache", "german required",
    "strong german", "communication skills in german"
]

IRRELEVANT = [
    "kfz", "mechatroniker", "fahrer", "driver", "nurse",
    "pflege", "arzt", "lehrer", "verkäufer",
    "buchhalter", "elektriker", "schweißer"
]

def is_relevant(title):
    t = title.lower()
    return not any(w in t for w in IRRELEVANT)

def requires_high_german(text):
    t = text.lower()
    return any(k in t for k in GERMAN_HIGH)

def is_target_company(company_name):
    c = company_name.lower()
    return any(target in c for target in TARGET_COMPANIES)

def fetch_jobs(term, country_code, country_name):
    jobs = []
    try:
        # Fetch multiple pages to get more results
        for page in range(1, 4):
            url = (
                f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/{page}"
                f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
                f"&results_per_page=50&what={term.replace(' ', '+')}"
                f"&content-type=application/json"
            )
            r    = requests.get(url, timeout=10)
            data = r.json()
            results = data.get("results", [])
            if not results:
                break

            for item in results:
                title   = item.get("title", "")
                desc    = item.get("description", "")
                company = item.get("company", {}).get("display_name", "")

                if not is_relevant(title):
                    continue
                if requires_high_german(title + " " + desc):
                    continue

                posted = item.get("created", "")[:10]
                try:
                    days_old = (datetime.now() - datetime.strptime(posted, "%Y-%m-%d")).days
                except:
                    days_old = ""

                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    item.get("location", {}).get("display_name", ""),
                    "country":     country_name,
                    "posted":      posted,
                    "days_old":    days_old,
                    "salary":      f"{item.get('salary_min','')}-{item.get('salary_max','')}".strip("-"),
                    "url":         item.get("redirect_url", ""),
                    "is_target":   is_target_company(company),
                })

    except Exception as e:
        print(f"  Error ({term}/{country_code}): {e}")

    return jobs

def deduplicate(jobs):
    seen, unique = set(), []
    for job in jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen and job["title"]:
            seen.add(key)
            unique.append(job)
    return unique

def write_to_sheet(jobs, tab_name, target_only=False):
    creds   = service_account.Credentials.from_service_account_file(
        CREDS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    service = build("sheets", "v4", credentials=creds).spreadsheets()

    meta          = service.get(spreadsheetId=SHEET_ID).execute()
    existing_tabs = [s["properties"]["title"] for s in meta["sheets"]]

    if tab_name not in existing_tabs:
        service.batchUpdate(
            spreadsheetId=SHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]}
        ).execute()

    filtered = [j for j in jobs if j["is_target"]] if target_only else jobs

    headers = [["Title", "Company", "Location", "Country",
                 "Posted", "Days Old", "Salary", "Apply URL"]]
    rows    = [[
        j["title"], j["company"], j["location"], j["country"],
        j["posted"], j["days_old"], j["salary"], j["url"]
    ] for j in filtered]

    service.values().clear(spreadsheetId=SHEET_ID, range=tab_name).execute()

    if not rows:
        service.values().update(
            spreadsheetId=SHEET_ID,
            range=f"{tab_name}!A1",
            valueInputOption="RAW",
            body={"values": [["No new jobs found in the last 7 days."],
                             ["Check back tomorrow — updates daily at 8am."]]}
        ).execute()
        print(f"No jobs in last 7 days — wrote message to tab: {tab_name}")
        return

    service.values().update(
        spreadsheetId=SHEET_ID,
        range=f"{tab_name}!A1",
        valueInputOption="RAW",
        body={"values": headers + rows}
    ).execute()

    print(f"Written {len(rows)} jobs to tab: {tab_name}")

def main():
    print(f"Direct Company Search — {datetime.now()}")
    all_jobs = []

    for term in SEARCH_TERMS:
        for code, name in COUNTRIES.items():
            print(f"  Searching: {term} in {name}")
            all_jobs += fetch_jobs(term, code, name)

    all_jobs = deduplicate(all_jobs)
    all_jobs.sort(key=lambda j: j["posted"], reverse=True)

    from datetime import timedelta
    cutoff    = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    all_jobs  = [j for j in all_jobs if j.get("posted", "") >= cutoff]

    target_jobs = [j for j in all_jobs if j["is_target"]]
    other_jobs  = [j for j in all_jobs if not j["is_target"]]

    print(f"\nAfter 7-day filter:         {len(all_jobs)}")
    print(f"From target companies:      {len(target_jobs)}")
    print(f"From other companies:       {len(other_jobs)}")

    write_to_sheet(all_jobs,    "AllJobs",    target_only=False)
    write_to_sheet(target_jobs, "DirectJobs", target_only=False)
    print("Done.")

if __name__ == "__main__":
    main()
