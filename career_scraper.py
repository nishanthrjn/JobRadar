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

# Target companies — Adzuna searches these directly
TARGET_COMPANIES = [
    "Siemens", "Bosch", "SAP", "Continental", "Capgemini",
    "Atos", "IBM", "Microsoft", "Amazon", "msg systems",
    "GFT", "Atruvia", "Adesso", "Bechtle", "CGI",
    "Deloitte", "KPMG", "Thoughtworks", "Accenture",
    "Infosys", "Wipro", "HCL", "Deutsche Telekom",
    "Deutsche Bank", "Allianz", "BMW", "Mercedes",
    "Volkswagen", "Lufthansa Systems", "T-Systems"
]

SEARCH_TERMS = [".NET developer", "C# developer", "software engineer"]
COUNTRIES    = ["de", "nl", "be"]

GERMAN_HIGH = [
    "c1", "c2", "b2", "fließend deutsch", "fluent german",
    "verhandlungssicher", "muttersprache", "german required",
    "german is required", "strong german"
]

IRRELEVANT = [
    "kfz", "mechatroniker", "fahrer", "driver", "nurse",
    "pflege", "arzt", "doctor", "lehrer", "teacher",
    "verkäufer", "buchhalter", "elektriker", "schweißer"
]

def is_relevant(title):
    t = title.lower()
    return not any(w in t for w in IRRELEVANT)

def requires_high_german(text):
    t = text.lower()
    return any(k in t for k in GERMAN_HIGH)

def fetch_company_jobs(company, term, country):
    jobs = []
    try:
        url = (
            f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
            f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
            f"&results_per_page=20"
            f"&what={term.replace(' ', '+')}"
            f"&who={company.replace(' ', '+')}"
            f"&content-type=application/json"
        )
        r    = requests.get(url, timeout=10)
        data = r.json()

        country_names = {"de": "Germany", "nl": "Netherlands", "be": "Belgium"}

        for item in data.get("results", []):
            title = item.get("title", "")
            desc  = item.get("description", "")

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
                "title":    title,
                "company":  item.get("company", {}).get("display_name", company),
                "location": item.get("location", {}).get("display_name", ""),
                "country":  country_names.get(country, country),
                "posted":   posted,
                "days_old": days_old,
                "salary":   f"{item.get('salary_min','')}-{item.get('salary_max','')}".strip("-"),
                "url":      item.get("redirect_url", ""),
            })

    except Exception as e:
        print(f"  Error {company}/{term}/{country}: {e}")

    return jobs

def deduplicate(jobs):
    seen, unique = set(), []
    for job in jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen and job["title"]:
            seen.add(key)
            unique.append(job)
    return unique

def write_to_sheet(jobs, tab_name="DirectJobs"):
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

    headers = [["Title", "Company", "Location", "Country",
                 "Posted", "Days Old", "Salary", "Apply URL"]]
    rows    = [[
        j["title"], j["company"], j["location"], j["country"],
        j["posted"], j["days_old"], j["salary"], j["url"]
    ] for j in jobs]

    service.values().clear(spreadsheetId=SHEET_ID, range=tab_name).execute()
    service.values().update(
        spreadsheetId=SHEET_ID,
        range=f"{tab_name}!A1",
        valueInputOption="RAW",
        body={"values": headers + rows}
    ).execute()

    print(f"Written {len(rows)} jobs to tab: {tab_name}")

def main():
    print(f"Direct Company Search starting — {datetime.now()}")
    all_jobs = []

    for company in TARGET_COMPANIES:
        company_jobs = []
        for term in SEARCH_TERMS:
            for country in COUNTRIES:
                company_jobs += fetch_company_jobs(company, term, country)
        
        company_jobs = deduplicate(company_jobs)
        if company_jobs:
            print(f"  {company}: {len(company_jobs)} jobs")
        all_jobs += company_jobs

    all_jobs = deduplicate(all_jobs)
    all_jobs.sort(key=lambda j: j["posted"], reverse=True)
    print(f"\nTotal unique jobs from target companies: {len(all_jobs)}")

    write_to_sheet(all_jobs, tab_name="DirectJobs")
    print("Done.")

if __name__ == "__main__":
    main()
