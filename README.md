<div align="center">

# 🤖 AI Job Agent

### Live Worldwide Job Discovery • Employer ATS Search • Freshness Filtering • Resume Matching

[![Live App](https://img.shields.io/badge/🚀%20LIVE%20APP-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://job--agent.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Tracking-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-7%20Passed-0A9EDC?style=for-the-badge)](#testing)

**Find fresh jobs. Search employer career systems. Match them against your real resume. Track the opportunities.**

### 🌐 [OPEN THE LIVE JOB AGENT →](https://job--agent.streamlit.app/)

</div>

---

## ⚡ What Changed in the Final Version

This is no longer just a **paste-a-job-description analyzer**.

The final architecture has four discovery layers:

```text
┌─────────────────────────────────────────────────────┐
│                 AI JOB AGENT                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. FREE PUBLIC JOB FEEDS                           │
│     Jobicy • Remotive • RemoteOK • Arbeitnow        │
│     Himalayas • RemoteJobs.org • Nomado24           │
│     Startup Jobs • Remote Landers                   │
│                                                     │
│  2. EMPLOYER ATS / CAREER SYSTEMS                  │
│     Greenhouse • Lever • Ashby • SmartRecruiters   │
│     Workable • Recruitee • Breezy • BambooHR       │
│     Personio • Teamtailor • Rippling                │
│                                                     │
│  3. USER-SUPPLIED PORTAL REGISTRY                  │
│     LinkedIn • Naukri • Indeed • Glassdoor          │
│     SEEK • Bayt • GulfTalent • Wellfound • etc.     │
│                                                     │
│  4. OPTIONAL WEB-INDEX DISCOVERY                    │
│     DuckDuckGo fallback / Serper when configured    │
│                                                     │
└───────────────────────┬─────────────────────────────┘
                        ↓
                  DEDUPLICATION
                        ↓
              FRESHNESS VALIDATION
                 Today / Last 24h
                        ↓
             WORLDWIDE / REGION FILTER
                        ↓
                RESUME ↔ JD MATCH
                        ↓
                MATCH + ATS SCORE
                        ↓
               SQLITE JOB TRACKER
                        ↓
                 EXCEL EXPORT
```

---

# 🚀 Live Application

**[Launch AI Job Agent](https://job--agent.streamlit.app/)**

The application is designed for candidates targeting roles such as:

- Data Analyst
- Data Scientist
- Junior Data Scientist
- BI Analyst
- Business Analyst
- Product Analyst
- Analytics Engineer

The candidate profile can be extended without changing the discovery engine.

---

# 🌍 Discovery Strategy

The application deliberately distinguishes **actual live feeds** from **web discovery**.

### 🟢 Tier 1 — Free direct feeds

These are queried directly without Serper:

- Jobicy
- Remotive
- RemoteOK
- Arbeitnow
- Himalayas
- RemoteJobs.org
- Nomado24
- Startup Jobs
- Remote Landers employer-ATS feed

Himalayas documents a free public JSON API with no authentication and supports pagination, keyword, country, worldwide, seniority and other filters. https://himalayas.app/docs/remote-jobs-api

Remote Landers provides a free public JSON API whose listings are sourced directly from employer ATS systems including Greenhouse, Ashby, Lever, SmartRecruiters and Recruitee. https://remotelanders.com/api

### 🏢 Tier 2 — Employer ATS / first-party postings

The final discovery layer supports public company-board endpoints for:

```text
Greenhouse
Lever
Ashby
SmartRecruiters
Workable
Recruitee
Breezy HR
BambooHR
Personio
Teamtailor
Rippling
```

Public ATS endpoints are preferable to scraping an aggregator when a company exposes them: they are closer to the employer's source of truth and generally require no API key. https://github.com/noble-ronin/ats-job-apis

Ashby officially documents a public Job Postings API including `publishedAt`, remote/workplace type, description and job URL. https://developers.ashbyhq.com/docs/public-job-posting-api

Lever documents a public postings API for published company jobs. https://github.com/lever/postings-api

### 🟠 Tier 3 — Portal discovery

Your supplied portal list is stored in `data/source_registry.json` and includes the requested global, remote, freelance and regional platforms.

Examples include:

```text
LinkedIn
Naukri
Indeed
Glassdoor
Wellfound
Remote.co
Himalayas
We Work Remotely
Working Nomads
FlexJobs
Dynamite Jobs
Pangian
Outsourcely
Virtual Vocations
SEEK
Jora
MyCareersFuture
JobsDB
GulfTalent
Bayt
Naukrigulf
Foundit
Cutshort
Instahyre
Welcome to the Jungle
HiringCafe
Simplify
Handshake
Toptal
Contra
PeoplePerHour
Malt
Codeur
Yunojuno
```

The full registry is preserved from the supplied source list rather than silently replacing it.

### 🔵 Tier 4 — Optional indexed web search

If `SERPER_API_KEY` is configured, the application uses Serper for broader indexed discovery.

Without it, a best-effort public DuckDuckGo HTML fallback is attempted.

**Blunt limitation:** this fallback is not an official API and may be rate-limited or blocked. It is therefore never presented as equivalent to a direct job API.

---

# 🏢 Company Career Search

The final version also has a **company watchlist** derived from the supplied source list.

Current named company targets include:

- TELUS Digital
- Superside
- Hotjar
- GitLab
- Revolut
- Capgemini
- Spotify
- Toptal
- Satypara
- Tailscale
- Kit
- Float
- Webflow
- Affirm
- Help Scout

The company discovery workflow is:

```text
Company
   ↓
Search public career domain
   ↓
Detect ATS board
   ↓
Greenhouse / Lever / Ashby / ...
   ↓
Fetch complete published board
   ↓
Filter role + freshness
   ↓
Deduplicate
```

This is materially different from simply returning a Google/LinkedIn result.

---

# 🕒 Freshness: Today vs Last 24 Hours

The app has two freshness modes:

### 📅 Posted today (UTC)

A job must have a parseable posting timestamp whose UTC date equals the current UTC date.

### ⏱️ Last 24 hours

A job must have a parseable timestamp within the previous 24 hours.

### ❌ No timestamp = no fresh-job claim

A web result with no reliable posting date is **not** treated as a today's job.

This is important because many aggregators expose a page without a trustworthy publication timestamp.

---

# 🌎 Worldwide Hiring vs Remote

The application does not assume:

```text
Remote = Worldwide
```

Instead it keeps location/eligibility information separate.

Potential classifications include:

```text
🌎 Worldwide
🇺🇸 United States
🇬🇧 United Kingdom
🇪🇺 Europe / EU
🇦🇺 Australia
🇸🇬 Singapore
🇦🇪 UAE
🇮🇳 India
⚠️ Location / eligibility unclear
```

The user can search across multiple hiring regions at once.

---

# 📄 Real Resume Matching

The final version fixes an important weakness in the earlier MVP.

You can upload your actual:

- PDF
- DOCX
- TXT

The resume is parsed locally in the Streamlit session.

If no resume is uploaded, the system falls back to the structured candidate profile and explicitly warns that the score is **not a full-CV match**.

```text
Actual CV uploaded
        ↓
Resume text extraction
        ↓
Candidate evidence
        ↓
Job description
        ↓
Skill / text matching
        ↓
Match + ATS estimate
```

No external AI API is required for resume extraction.

---

# 🧠 Matching Engine

The current scoring engine uses:

- Skill overlap
- JD vocabulary overlap
- Communication evidence
- ATS estimate
- Remote/location interpretation

The scores are intended as **decision-support estimates**, not employer ATS scores.

### Current ATS estimate

```text
70%  Requirement / skill match
20%  Text similarity signal
10%  Communication signal
```

### Current overall score

```text
55%  Requirement / skill match
20%  Text similarity
15%  Communication
10%  ATS estimate
```

The model is intentionally transparent rather than pretending to be a proprietary employer ATS.

---

# 🔁 Deduplication

The same job may appear on:

```text
LinkedIn
Indeed
Glassdoor
Company careers
Greenhouse
Remote board
```

The application normalizes URLs and falls back to company/title/location fingerprints.

When duplicate records exist, first-party ATS records are preferred over generic web snippets where the evidence quality is stronger.

---

# 🗃️ Tracking

Every discovered job can be persisted locally in SQLite with:

```text
Job ID
Company
Title
Source
Location
Work mode
Salary
Posted timestamp
Job URL
Application URL
Match score
ATS estimate
Matched skills
Missing skills
Verification state
Application status
```

The Excel exporter includes the same core tracking fields.

---

# ⚠️ Important Reality Check

This is the part I am deliberately **not** going to bullshit you about.

## “All jobs worldwide” is impossible with free public APIs.

No application can guarantee every job on the internet because:

- Some job boards have no public API.
- Some require authentication.
- Some prohibit automated access.
- Some use anti-bot systems.
- Some companies use private ATS configurations.
- Some postings appear only on a company's own website.
- Some feeds delay publication.
- Some pages do not expose a reliable posting timestamp.
- Some jobs disappear before they can be indexed.

Therefore the app aims for **broad, source-diverse coverage**, not a fake claim of universal coverage.

---

# 🔐 Responsible Automation

The application does not:

- bypass CAPTCHA
- bypass MFA
- steal credentials
- create fake accounts
- fabricate qualifications
- fabricate work authorization
- fabricate salary expectations
- automatically accept legal declarations
- blindly mass-submit applications

The goal is:

> **Automate discovery and analysis. Keep consequential application decisions under human control.**

---

# 🛠️ Technology Stack

```text
Python
Streamlit
Requests
SQLite
OpenPyXL
PyPDF
python-docx
Pytest
JSON
```

No paid AI model is required for the core discovery workflow.

---

# 📁 Project Structure

```text
job-agent/
│
├── app.py
├── discovery.py
├── engine.py
├── database.py
├── export.py
├── resume_parser.py
├── config.py
├── requirements.txt
├── .env.example
├── pytest.ini
│
├── data/
│   ├── candidate_profile.json
│   ├── skill_taxonomy.json
│   └── source_registry.json
│
└── tests/
    ├── test_engine.py
    └── test_discovery.py
```

---

# ⚡ Local Setup

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd job-agent

python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest -q
```

Run application:

```bash
streamlit run app.py
```

---

# 🔑 Optional Serper Configuration

Create a `.env`/deployment secret containing:

```text
SERPER_API_KEY=your_serper_api_key_here
```

The direct feeds and ATS adapters do **not** require this key.

Serper is only an expansion layer for broader indexed web discovery.

---

# 🧪 Testing

Current suite:

```text
7 passed
```

Covered areas include:

- matching engine
- remote classification
- deduplication
- freshness logic
- source registry
- major portal registry entries
- company watchlist
- web fallback availability

The network adapters themselves should be tested against mocked responses in CI rather than depending on live websites for every test run.

---

# 🚀 Streamlit Deployment

1. Push the project to GitHub.
2. Open Streamlit Community Cloud.
3. Select the repository.
4. Set the main file to `app.py`.
5. Deploy.
6. If broader web discovery is required, add `SERPER_API_KEY` under Streamlit Secrets.

### Live deployment

**https://job--agent.streamlit.app/**

---

# 📌 What I Would Build Next

If this is going beyond a portfolio demo, the next engineering priorities are **not more random portals**.

They are:

### 1. Persistent cloud database

The current SQLite store is local. Streamlit Cloud should not be treated as a durable production database.

Use a free-tier PostgreSQL/Supabase backend for persistent tracking.

### 2. Scheduled discovery

A scheduled worker should run automatically:

```text
06:00 UTC
12:00 UTC
18:00 UTC
00:00 UTC
```

and store newly discovered jobs.

### 3. Company universe

Build a maintained company watchlist with:

```text
Company
Career URL
ATS provider
ATS slug
Country
Remote policy
Last checked
```

### 4. Better semantic matching

Replace the lightweight text overlap with embeddings and contextual requirement matching.

### 5. Job lifecycle tracking

Detect:

```text
New
Updated
Still Open
Closed
Removed
```

### 6. Application intelligence

Then add:

```text
Resume tailoring
ATS before/after
Cover letter
Recruiter discovery
Application queue
Follow-ups
Analytics
```

---

# 💼 Portfolio Value

This project demonstrates:

**Python • Data Engineering • API Integration • Web Discovery • NLP • Information Extraction • Scoring Systems • Streamlit • SQLite • Excel Automation • Testing • Responsible Automation**

More importantly, it demonstrates the ability to build a system that distinguishes:

```text
REAL DATA
vs
SEARCH RESULTS
vs
ESTIMATES
vs
ASSUMPTIONS
```

That distinction is critical in a real data product.

---

# 👨‍💻 Author

## Shubham Kumar Jha

**Data Analytics / Data Science | Python | SQL | Machine Learning | Streamlit**

- 💼 [LinkedIn](https://linkedin.com/in/shubhamkjha-datascience)
- 🐙 [GitHub](https://github.com/shubhamkjha-datascience)
- 🚀 [Live Job Agent](https://job--agent.streamlit.app/)

---

<div align="center">

### Find less noise. Find more relevant jobs.

**Evidence > Assumptions**  
**Fresh data > stale listings**  
**Employer source > copied aggregator**  
**Quality applications > blind automation**

</div>
