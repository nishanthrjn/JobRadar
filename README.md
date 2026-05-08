# JobRadar — Daily .NET Job Digest for Germany & Benelux

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Automated](https://img.shields.io/badge/Runs-Daily%208am-green.svg)](.github/workflows/daily.yml)

> Aggregates English-language .NET/C# developer jobs from Germany, Netherlands,
> Belgium and Luxembourg. Filters out German-language-required roles, deduplicates,
> and writes fresh results to a Google Sheet every morning at 8am automatically.

---

## What It Does
```text
Runs daily at 8am via GitHub Actions
↓
Searches Adzuna API across DE, NL, BE
↓
Searches 30 target company career pages directly
↓
Filters: English only + .NET/C# + last 7 days
↓
Removes duplicates
↓
Writes to Google Sheet — 3 tabs:
Sheet1     → All aggregated jobs (Adzuna)
AllJobs    → All jobs from target company search
DirectJobs → Jobs from Siemens, SAP, Bosch etc only
```
---

## Job Sources
```bash
| Source | Coverage | Method |
|--------|----------|--------|
| Adzuna API | Germany, Netherlands, Belgium | Official free API |
| Arbeitsagentur | Germany | Official government API |
| Jooble | Germany, Netherlands, Belgium, Luxembourg | Official free API |
| Remotive | Remote worldwide | Official free API |
| 30 Company career pages | Direct | Adzuna company filter |
```
---

## Target Companies

Large enterprises, mid-size consultancies, and remote-friendly firms:

Siemens, Bosch, SAP, Continental, Capgemini, Atos, IBM, Microsoft,
Amazon, msg systems, GFT, Atruvia, Adesso, Bechtle, CGI, Deloitte,
KPMG, Thoughtworks, Accenture, Infosys, Wipro, HCL, Deutsche Telekom,
Deutsche Bank, Allianz, BMW, Mercedes, Volkswagen, Lufthansa, T-Systems

---

## Filters Applied

- English-language jobs only (German-indicator word detection)
- Roles requiring German B2/C1/C2 are excluded
- Irrelevant titles filtered (KFZ, Mechatroniker, Fahrer etc)
- Only jobs posted in the last 7 days
- Duplicates removed by title + company key

---

## Setup

### Prerequisites
- Python 3.12
- Google Cloud project with Sheets API enabled
- Adzuna free API account (developer.adzuna.com)
- Jooble free API key (jooble.org/api/about)

### Install

```bash
pip install requests google-auth google-auth-oauthlib google-api-python-client python-dotenv beautifulsoup4
```

### Configure
```text
Create a `.env` file (never commit this):

ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key
JOOBLE_KEY=your_jooble_key
GOOGLE_SHEET_ID=your_sheet_id
EMAIL_FROM=your_gmail@gmail.com
EMAIL_TO=your_gmail@gmail.com
EMAIL_PASSWORD=your_gmail_app_password

Place your Google service account `credentials.json` in the project root.
```
### Run manually

```bash
python job_radar.py       # aggregated job search
python career_scraper.py  # target company search
python daily_jobs.py      # career page scraper + email digest
```

---

## Automation
```text
GitHub Actions runs all three scripts daily at 8am German time.
Add these GitHub Secrets to your repo:

ADZUNA_APP_ID
ADZUNA_APP_KEY
JOOBLE_KEY
GOOGLE_SHEET_ID
GOOGLE_CREDENTIALS   (full contents of credentials.json)
EMAIL_FROM
EMAIL_TO
EMAIL_PASSWORD
```
---

## Project Structure
```text
JobRadar/
├── job_radar.py          # Main aggregator — Adzuna, Arbeitsagentur, Jooble, Remotive
├── career_scraper.py     # Target company search — 30 companies
├── daily_jobs.py         # Career page scraper + HTML email digest
├── seen_jobs.json        # Tracks seen jobs to avoid re-sending (auto-generated)
├── .env                  # Credentials — never commit
├── credentials.json      # Google service account — never commit
├── .gitignore            # Excludes .env and credentials.json
└── .github/
└── workflows/
└── daily.yml     # GitHub Actions — runs at 8am daily
```
---

## Why This Exists

Built as part of a job search toolkit for a senior .NET engineer
targeting English-speaking roles in Germany and Benelux.

---

## Author

**Nishanth Rajan** — Software Engineer
https://linkedin.com/in/nishanthrajan
