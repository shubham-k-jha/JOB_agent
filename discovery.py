"""Production-oriented job discovery layer.

Design goals:
- Free-first: public feeds and public employer ATS endpoints do not require API keys.
- Source honesty: every result carries a source and discovery mode.
- Freshness honesty: "today" / "24h" requires a parseable timestamp.
- Company-first: when a company ATS board can be detected, fetch the company's
  published board rather than relying on an aggregator snippet.
- Broad coverage: remote feeds + user-supplied portal registry + ATS adapters.
- No CAPTCHA/MFA bypassing, credential use, or fake job generation.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from html import unescape
import json
import os
import re
from urllib.parse import urlparse, parse_qs, unquote
from xml.etree import ElementTree as ET
import requests

TIMEOUT = 20
UA = "AI-Job-Agent/3.0 (+https://job--agent.streamlit.app/)"


def _get(url, params=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json,text/xml,application/xml,text/html"}
    if headers:
        h.update(headers)
    r = requests.get(url, params=params, timeout=TIMEOUT, headers=h)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    if "json" in ct:
        return r.json()
    return r.text


def _strip_html(text):
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text or "", flags=re.I)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def _dt(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            value /= 1000
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except Exception:
            return None
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
        try:
            d = datetime.strptime(s[:40], fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _norm(job, source, **kw):
    d = _dt(kw.get("posted"))
    return {
        "source": source,
        "discovery_mode": kw.get("discovery_mode", "direct_feed"),
        "company": kw.get("company") or "Unknown company",
        "title": kw.get("title") or "Untitled role",
        "url": kw.get("url") or "",
        "application_url": kw.get("application_url") or kw.get("url") or "",
        "location": kw.get("location") or "Not disclosed",
        "work_mode": kw.get("work_mode") or "Unclear",
        "salary": kw.get("salary") or "Not disclosed",
        "description": kw.get("description") or "",
        "posted_at": d.isoformat() if d else "",
        "source_job_id": str(job.get("id", kw.get("source_job_id", ""))),
        "first_party": bool(kw.get("first_party", False)),
        "company_website": kw.get("company_website") or "",
    }


def _terms(query):
    return [x.lower() for x in re.findall(r"[A-Za-z0-9+#.-]+", query or "") if len(x) > 1]


def _query_match(job, query):
    ts = _terms(query)
    if not ts:
        return True
    hay = " ".join(str(job.get(k, "")) for k in ("title", "description", "company", "location")).lower()
    return any(t in hay for t in ts)


# -------------------------- free public feeds --------------------------

def jobicy(query="", limit=200):
    data = _get("https://jobicy.com/api/v2/remote-jobs", {"count": min(limit, 200), **({"tag": query} if query else {})})
    out=[]
    for j in data.get("jobs", []):
        sal="Not disclosed"
        if j.get("salaryMin") or j.get("salaryMax"):
            sal=f"{j.get('salaryMin','')}–{j.get('salaryMax','')} {j.get('salaryCurrency','')} {j.get('salaryPeriod','')}".strip()
        out.append(_norm(j,"Jobicy",company=j.get("companyName"),title=j.get("jobTitle"),url=j.get("url"),
            description=_strip_html(j.get("jobDescription","")),location=j.get("jobGeo"),posted=j.get("pubDate"),salary=sal,work_mode="Remote"))
    return out


def remotive(query="", limit=100):
    p={"limit":min(limit,100)}
    if query:p["search"]=query
    data=_get("https://remotive.com/api/remote-jobs",p)
    return [_norm(j,"Remotive",company=j.get("company_name"),title=j.get("title"),url=j.get("url"),description=j.get("description"),
        location=j.get("candidate_required_location"),posted=j.get("publication_date"),salary=j.get("salary") or "Not disclosed",work_mode="Remote") for j in data.get("jobs",[])]


def remoteok(query="", limit=200):
    data=_get("https://remoteok.com/api",{"limit":min(limit,200)})
    out=[]
    for j in data if isinstance(data,list) else []:
        if not isinstance(j,dict) or not j.get("position"): continue
        hay=(j.get("position","")+" "+j.get("description","")+" "+" ".join(j.get("tags",[]) or [])).lower()
        if query and not any(t in hay for t in _terms(query)): continue
        out.append(_norm(j,"RemoteOK",company=j.get("company"),title=j.get("position"),url=j.get("url"),description=_strip_html(j.get("description","")),
            location=j.get("location") or "Worldwide",posted=j.get("date") or j.get("published_at"),salary=j.get("salary") or "Not disclosed",work_mode="Remote"))
    return out


def arbeitnow(query="", pages=3):
    out=[]
    for page in range(1,pages+1):
        data=_get("https://www.arbeitnow.com/api/job-board-api",{"page":page})
        jobs=data.get("data",[])
        if not jobs: break
        for j in jobs:
            hay=(j.get("title","")+" "+j.get("description","")+" "+" ".join(j.get("tags",[]) or [])).lower()
            if query and not any(t in hay for t in _terms(query)): continue
            out.append(_norm(j,"Arbeitnow",company=j.get("company_name"),title=j.get("title"),url=j.get("url"),description=_strip_html(j.get("description","")),
                location=j.get("location"),posted=j.get("created_at"),work_mode="Remote" if j.get("remote") else "On-site/Hybrid"))
    return out


def himalayas(query="", limit=100):
    data=_get("https://himalayas.app/jobs/api/search",{"q":query,"sort":"recent","page":1})
    jobs=data.get("jobs") or data.get("data") or []
    out=[]
    for j in jobs[:limit]:
        company=j.get("company")
        if isinstance(company,dict): company=company.get("name")
        out.append(_norm(j,"Himalayas",company=j.get("companyName") or company,title=j.get("title"),url=j.get("applicationLink") or j.get("url") or j.get("guid"),
            application_url=j.get("applicationLink") or j.get("url"),description=_strip_html(j.get("description") or j.get("descriptionHtml") or ""),
            location=j.get("location") or j.get("locationRestrictions") or ("Worldwide" if j.get("isWorldwide") else "Not disclosed"),
            posted=j.get("pubDate") or j.get("publishedAt") or j.get("publicationDate"),salary=j.get("salary") or j.get("salaryRange") or "Not disclosed",work_mode="Remote"))
    return out


def remote_landers(query="", limit=200):
    terms=_terms(query); out=[]; page=1; per_page=min(max(limit,50),100)
    while page<=20:
        data=_get("https://remotelanders.com/api/jobs",{"limit":per_page,"page":page})
        jobs=data.get("jobs",[])
        if not jobs: break
        for j in jobs:
            hay=" ".join([j.get("title",""),j.get("company",""),j.get("category","")," ".join(j.get("subtags",[]) or [])]).lower()
            if terms and not any(t in hay for t in terms): continue
            out.append(_norm(j,"Remote Landers — Employer ATS",company=j.get("company"),title=j.get("title"),url=j.get("url"),application_url=j.get("applyUrl") or j.get("url"),
                location=j.get("location"),posted=j.get("postedDate"),salary=j.get("salary"),work_mode="Remote",first_party=True,company_website=j.get("companyWebsite"),source_job_id=j.get("slug")))
        total=int(data.get("total") or 0)
        if page*per_page>=total: break
        page+=1
    return out


def remotejobs_org(query="",limit=50):
    data=_get("https://remotejobs.org/api/v1/jobs",{"q":query,"limit":min(limit,50),"offset":0})
    out=[]
    for j in data.get("data",[]):
        c=j.get("company") or {}
        out.append(_norm(j,"RemoteJobs.org",company=c.get("name"),title=j.get("title"),url=j.get("url"),application_url=j.get("apply_url") or j.get("url"),
            description=_strip_html(j.get("description","")),location=j.get("location"),posted=j.get("posted_at"),salary=j.get("salary_text") or "Not disclosed",work_mode="Remote",company_website=c.get("website")))
    return out


def nomado24(query="",limit=100):
    data=_get("https://api.nomado24.de/api/public/v1/jobs",{"q":query,"language":"en","per_page":min(limit,100),"page":1})
    out=[]
    for j in data.get("data",[]):
        sal="Not disclosed"
        if j.get("salaryMin") or j.get("salaryMax"): sal=f"{j.get('salaryMin','')}–{j.get('salaryMax','')} {j.get('currency','')}".strip()
        out.append(_norm(j,"Nomado24",company=j.get("companyName"),title=j.get("title"),url=j.get("url"),description=_strip_html(j.get("description","")),location=j.get("location"),posted=j.get("publishedAt"),salary=sal,work_mode=j.get("workArrangement") or ("Remote" if j.get("remote") else "Hybrid")))
    return out


def startup_jobs_rss(query="",limit=50):
    text=_get("https://startup.jobs/feeds/jobs",{"workplace":"remote"}); root=ET.fromstring(text); out=[]
    for item in root.findall(".//item")[:limit]:
        def t(name):
            n=item.find(name); return n.text.strip() if n is not None and n.text else ""
        title=t("title"); desc=_strip_html(t("description")); company=t("company") or "Unknown company"
        if query and not _query_match({"title":title,"description":desc,"company":company},query): continue
        out.append(_norm({"id":t("guid") or t("link")},"Startup Jobs",company=company,title=title,url=t("link"),description=desc,location="Remote",posted=t("pubDate"),work_mode="Remote"))
    return out


# -------------------------- public ATS adapters --------------------------

def _page_date(url):
    if not url:return None
    try:
        html=_get(url)
        for pat in [r'"datePosted"\s*:\s*"([^"}]+)"',r'itemprop=["\']datePosted["\'][^>]*content=["\']([^"\']+)',r'"publishedAt"\s*:\s*"([^"}]+)"']:
            m=re.search(pat,html,re.I)
            if m:return m.group(1)
    except Exception: pass
    return None


def greenhouse(company,limit=200):
    data=_get(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs",{"content":"true"}); out=[]
    for j in data.get("jobs",[])[:limit]:
        loc=(j.get("location") or {}).get("name","") if isinstance(j.get("location"),dict) else str(j.get("location") or "")
        url=j.get("absolute_url"); posted=_page_date(url)
        out.append(_norm(j,"Greenhouse — Company",company=company.replace("-"," ").title(),title=j.get("title"),url=url,description=_strip_html(j.get("content","")),location=loc,posted=posted,work_mode="Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def lever(company,limit=200):
    data=_get(f"https://api.lever.co/v0/postings/{company}",{"mode":"json"}); out=[]
    for j in data[:limit] if isinstance(data,list) else []:
        cats=j.get("categories",{}) or {}
        out.append(_norm(j,"Lever — Company",company=company.replace("-"," ").title(),title=j.get("text"),url=j.get("hostedUrl"),application_url=j.get("applyUrl") or j.get("hostedUrl"),description=_strip_html(j.get("descriptionPlain") or j.get("description","")),location=cats.get("location"),posted=j.get("createdAt") or j.get("updatedAt"),work_mode=cats.get("workplaceType") or "Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def ashby(company,limit=200):
    data=_get(f"https://api.ashbyhq.com/posting-api/job-board/{company}",{"includeCompensation":"true"}); out=[]
    for j in data.get("jobs",[])[:limit]:
        if j.get("isListed") is False: continue
        comp=j.get("compensation") or {}; sal=comp.get("scrapeableCompensationSalarySummary") or comp.get("compensationTierSummary") or "Not disclosed"
        out.append(_norm(j,"Ashby — Company",company=company.replace("-"," ").title(),title=j.get("title"),url=j.get("jobUrl"),application_url=j.get("applyUrl") or j.get("jobUrl"),description=_strip_html(j.get("descriptionHtml") or j.get("description","")),location=j.get("location") or "",posted=j.get("publishedAt") or j.get("createdAt") or j.get("updatedAt"),salary=sal,work_mode=j.get("workplaceType") or "Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def smartrecruiters(company,limit=200):
    out=[]; offset=0
    while offset<1000:
        data=_get(f"https://api.smartrecruiters.com/v1/companies/{company}/postings",{"limit":min(100,limit),"offset":offset})
        content=data.get("content",[])
        if not content:break
        for j in content:
            loc=j.get("location") or {}
            out.append(_norm(j,"SmartRecruiters — Company",company=company.replace("-"," ").title(),title=j.get("name"),url=j.get("ref"),description="",location=", ".join(x for x in [loc.get("city"),loc.get("region"),loc.get("country")] if x),posted=j.get("releasedDate"),work_mode="Unknown",first_party=True,discovery_mode="company_ats"))
        if len(content)<min(100,limit):break
        offset+=len(content)
    return out[:limit]


def workable(company,limit=200):
    data=_get(f"https://apply.workable.com/api/v1/widget/accounts/{company}")
    jobs=data.get("jobs",data if isinstance(data,list) else [])
    out=[]
    for j in jobs[:limit]:
        out.append(_norm(j,"Workable — Company",company=company.replace("-"," ").title(),title=j.get("title"),url=j.get("url") or j.get("shortlink"),application_url=j.get("url") or j.get("shortlink"),description=_strip_html(j.get("description","")),location=j.get("location") or j.get("city"),posted=j.get("created_at") or j.get("published_at"),work_mode=j.get("workplace_type") or "Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def recruitee(company,limit=200):
    data=_get(f"https://{company}.recruitee.com/api/offers/")
    jobs=data.get("offers",data if isinstance(data,list) else []); out=[]
    for j in jobs[:limit]:
        out.append(_norm(j,"Recruitee — Company",company=company.replace("-"," ").title(),title=j.get("title"),url=j.get("careers_url") or j.get("url"),description=_strip_html(j.get("description","")),location=j.get("location"),posted=j.get("published_at") or j.get("created_at"),work_mode=j.get("remote") and "Remote" or "Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def breezy(company,limit=200):
    data=_get(f"https://{company}.breezy.hr/json"); jobs=data if isinstance(data,list) else data.get("jobs",[]); out=[]
    for j in jobs[:limit]:
        out.append(_norm(j,"Breezy HR — Company",company=company.replace("-"," ").title(),title=j.get("name") or j.get("title"),url=j.get("url"),description=_strip_html(j.get("description","")),location=j.get("location"),posted=j.get("published_date") or j.get("created_at"),salary=j.get("salary") or "Not disclosed",work_mode=j.get("type") or "Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def bamboohr(company,limit=200):
    data=_get(f"https://{company}.bamboohr.com/careers/list")
    jobs=data.get("jobs",data if isinstance(data,list) else []); out=[]
    for j in jobs[:limit]:
        out.append(_norm(j,"BambooHR — Company",company=company.replace("-"," ").title(),title=j.get("jobOpeningName") or j.get("title"),url=j.get("jobOpeningShareUrl") or j.get("url"),description=_strip_html(j.get("description","")),location=j.get("location"),posted=j.get("datePosted") or j.get("createdAt"),work_mode="Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def personio(company,limit=200):
    text=_get(f"https://{company}.jobs.personio.com/xml"); root=ET.fromstring(text); out=[]
    for item in root.findall(".//position")[:limit]:
        def child(name):
            n=item.find(name); return n.text.strip() if n is not None and n.text else ""
        out.append(_norm({"id":child("id")},"Personio — Company",company=company.replace("-"," ").title(),title=child("name") or child("title"),url=child("url"),description=_strip_html(child("jobDescription")),location=child("office"),posted=child("createdAt") or child("datePosted"),work_mode="Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def teamtailor(company,limit=200):
    data=_get(f"https://{company}.teamtailor.com/jobs.json"); jobs=data.get("jobs",data if isinstance(data,list) else []); out=[]
    for j in jobs[:limit]:
        out.append(_norm(j,"Teamtailor — Company",company=company.replace("-"," ").title(),title=j.get("title"),url=j.get("url"),description=_strip_html(j.get("description","")),location=j.get("location"),posted=j.get("created_at") or j.get("published_at"),work_mode=j.get("remote_status") or "Unknown",first_party=True,discovery_mode="company_ats"))
    return out


def rippling(company,limit=200):
    data=_get(f"https://api.rippling.com/platform/api/ats/v1/board/{company}/jobs"); jobs=data.get("data",data.get("jobs",[])); out=[]
    for j in jobs[:limit]:
        out.append(_norm(j,"Rippling — Company",company=company.replace("-"," ").title(),title=j.get("title"),url=j.get("url") or j.get("job_url"),description=_strip_html(j.get("description","")),location=j.get("location"),posted=j.get("published_at") or j.get("created_at"),work_mode=j.get("workplace_type") or "Unknown",first_party=True,discovery_mode="company_ats"))
    return out

ATS_HOSTS = {
    "boards.greenhouse.io":"greenhouse", "job-boards.eu.greenhouse.io":"greenhouse",
    "jobs.lever.co":"lever", "jobs.ashbyhq.com":"ashby", "careers.smartrecruiters.com":"smartrecruiters",
    "apply.workable.com":"workable", "recruitee.com":"recruitee", "breezy.hr":"breezy",
    "bamboohr.com":"bamboohr", "jobs.personio.com":"personio", "teamtailor.com":"teamtailor",
    "rippling.com":"rippling",
}
ATS_FUNCS = {"greenhouse":greenhouse,"lever":lever,"ashby":ashby,"smartrecruiters":smartrecruiters,"workable":workable,
            "recruitee":recruitee,"breezy":breezy,"bamboohr":bamboohr,"personio":personio,"teamtailor":teamtailor,"rippling":rippling}


def _ats_from_url(url):
    host=urlparse(url).netloc.lower().split(":")[0]
    path=[unquote(x) for x in urlparse(url).path.strip("/").split("/") if x]
    for needle,kind in ATS_HOSTS.items():
        if needle in host:
            token=None
            if kind in {"greenhouse","lever","ashby","smartrecruiters","workable","teamtailor","rippling"}:
                token=path[0] if path else None
            elif kind in {"recruitee","breezy","bamboohr","personio"}:
                token=host.split(".")[0]
            if token:return kind,token
    return None,None


# -------------------------- web discovery --------------------------

def free_web_search(query,limit=30):
    """Best-effort no-key discovery using DuckDuckGo HTML.
    Search results are NOT treated as verified job postings and do not qualify for
    today/24h unless a timestamp is actually exposed in the result.
    """
    r=requests.get("https://html.duckduckgo.com/html/",params={"q":query,"kl":"wt-wt"},timeout=TIMEOUT,headers={"User-Agent":UA,"Accept":"text/html"}); r.raise_for_status()
    text=r.text; out=[]
    blocks=re.findall(r'<div[^>]+class="result[^"]*"[\s\S]*?</div>\s*</div>',text,flags=re.I)
    for block in blocks[:limit]:
        href=re.search(r'class="result__a"[^>]+href="([^"]+)"',block,re.I); title=re.search(r'class="result__a"[^>]*>([\s\S]*?)</a>',block,re.I); snippet=re.search(r'class="result__snippet"[^>]*>([\s\S]*?)</(?:a|div)>',block,re.I)
        if not href:continue
        link=unquote(href.group(1).replace("&amp;","&")); q=parse_qs(urlparse(link).query)
        if q.get("uddg"):link=q["uddg"][0]
        title_txt=_strip_html(title.group(1)) if title else ""; snippet_txt=_strip_html(snippet.group(1)) if snippet else ""
        posted=None; combined=f"{title_txt} {snippet_txt}"
        dm=re.search(r'\b(today|yesterday|\d+\s+(?:hour|hours|day|days)\s+ago)\b',combined,re.I)
        if dm:
            token=dm.group(1).lower(); now=datetime.now(timezone.utc)
            if token=="today":posted=now
            elif token=="yesterday":posted=now-timedelta(days=1)
            else:
                m=re.match(r'(\d+)\s+(hour|hours|day|days)',token); n=int(m.group(1)); posted=now-timedelta(hours=n if 'hour' in m.group(2) else n*24)
        out.append(_norm({"id":link},"Web Search",title=title_txt,url=link,description=snippet_txt,location="Worldwide / verify",work_mode="Unknown",posted=posted,source_job_id=link,discovery_mode="web_index"))
    return out


def search_engine(query,limit=30):
    key=os.getenv("SERPER_API_KEY")
    if key:
        r=requests.post("https://google.serper.dev/search",json={"q":query,"num":min(limit,100)},headers={"X-API-KEY":key,"Content-Type":"application/json","User-Agent":UA},timeout=TIMEOUT); r.raise_for_status(); data=r.json(); out=[]
        for x in data.get("organic",[]):
            out.append(_norm({"id":x.get("link")},"Web Search",title=x.get("title"),url=x.get("link"),description=x.get("snippet",""),location="Worldwide / verify",work_mode="Unknown",posted=x.get("date") or x.get("publishedDate") or x.get("datePosted"),source_job_id=x.get("link"),discovery_mode="web_index"))
        return out
    return free_web_search(query,limit)


def _load_registry():
    p=os.path.join(os.path.dirname(__file__),"data","source_registry.json")
    try:
        with open(p,encoding="utf-8") as f:return json.load(f)
    except Exception:return {"portals":[],"companies":[]}

_REG=_load_registry()
PUBLIC_WEB_SOURCES={name:domain for name,domain in _REG.get("portals",[])}
COMPANY_TARGETS={name:domain for name,domain in _REG.get("companies",[])}


def web_platform_search(platform,queries,limit=20,regions=None):
    domain=PUBLIC_WEB_SOURCES.get(platform)
    if not domain:return [],[f"Unknown web platform: {platform}"]
    regions=regions or ["Worldwide","United States","UK","Europe","Australia","Singapore","UAE"]
    jobs=[]; errors=[]
    for q in queries:
        region_text=" OR ".join(f'"{r}"' for r in regions[:8])
        search_q=f'site:{domain} ({q}) (remote OR "work from anywhere" OR worldwide OR {region_text})'
        try:
            hits=search_engine(search_q,limit)
            for h in hits:
                h["source"]=platform; h["first_party"]=False; h["verification"]="Web-index result — verify on source"; jobs.append(h)
        except Exception as exc:errors.append(f"{platform}/{q}: {exc}")
    return jobs,errors


def discover_company_boards(queries,limit=30,regions=None):
    """Discover company career pages from the user registry and expand detected ATS boards.

    If a company exposes a public ATS, the complete published board is fetched. If not,
    the company-domain search result is retained only as web discovery evidence.
    """
    jobs=[]; errors=[]
    for company,domain in COMPANY_TARGETS.items():
        for q in queries:
            try:
                search_q=f'site:{domain} (careers OR jobs OR "open positions") ({q})'
                hits=search_engine(search_q,min(limit,20))
                expanded=False
                for h in hits:
                    h["source"]=f"{company} — Careers"; h["company"]=company; h["first_party"]=True; h["verification"]="Company-domain result — verify posting"; jobs.append(h)
                    kind,token=_ats_from_url(h.get("url",""))
                    if kind and token:
                        try:
                            jobs.extend(ATS_FUNCS[kind](token,limit=200)); expanded=True
                        except Exception as exc:errors.append(f"{company} {kind}: {exc}")
                if not expanded:
                    # Search directly for ATS-hosted boards for the company.
                    ats_q=f'("{company}" OR {domain}) (site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:careers.smartrecruiters.com OR site:apply.workable.com OR site:teamtailor.com)'
                    for h in search_engine(ats_q,min(limit,10)):
                        kind,token=_ats_from_url(h.get("url",""))
                        if kind and token:
                            try: jobs.extend(ATS_FUNCS[kind](token,limit=200)); expanded=True
                            except Exception as exc:errors.append(f"{company} ATS expansion: {exc}")
            except Exception as exc:errors.append(f"{company}/{q}: {exc}")
    return jobs,errors


def is_fresh(job,mode="today"):
    d=_dt(job.get("posted_at"))
    if not d:return False
    now=datetime.now(timezone.utc)
    if mode=="24h":return d>=now-timedelta(hours=24)
    return d.date()==now.date()


def dedupe(jobs):
    seen={}; out=[]
    def key(j):
        url=(j.get("application_url") or j.get("url") or "").lower().split("?")[0].rstrip("/")
        if url:return re.sub(r"\W+","",url)
        return re.sub(r"\W+","",f"{j.get('company','')}|{j.get('title','')}|{j.get('location','')}".lower())
    for j in jobs:
        k=key(j)
        if not k:continue
        if k not in seen:seen[k]=j;out.append(j);continue
        # Prefer first-party ATS records over web snippets and records with timestamps/descriptions.
        old=seen[k]
        score=lambda x:(2 if x.get("first_party") else 0)+(1 if x.get("posted_at") else 0)+(1 if x.get("description") else 0)
        if score(j)>score(old):
            idx=out.index(old);out[idx]=j;seen[k]=j
    return out

FREE_DIRECT_SOURCES=["Jobicy","Remotive","RemoteOK","Arbeitnow","Himalayas","Remote Landers — Employer ATS","RemoteJobs.org","Nomado24","Startup Jobs RSS"]
DIRECT_FUNCS={"Jobicy":jobicy,"Remotive":remotive,"RemoteOK":remoteok,"Arbeitnow":arbeitnow,"Himalayas":himalayas,"Remote Landers — Employer ATS":remote_landers,"RemoteJobs.org":remotejobs_org,"Nomado24":nomado24,"Startup Jobs RSS":startup_jobs_rss}


def discover(queries,freshness="today",sources=None,limit_per_source=100,company_search=False,regions=None):
    sources=sources or FREE_DIRECT_SOURCES; jobs=[]; errors=[]
    # Direct feeds
    for q in queries:
        for source in sources:
            fn=DIRECT_FUNCS.get(source)
            if fn:
                try:jobs.extend(fn(q,limit_per_source))
                except Exception as exc:errors.append(f"{source} / {q}: {exc}")
    # Portal web discovery. These are not claimed to be official APIs.
    for source in [s for s in sources if s in PUBLIC_WEB_SOURCES]:
        try:
            wj,we=web_platform_search(source,queries,limit=min(limit_per_source,50),regions=regions);jobs.extend(wj);errors.extend(we)
        except Exception as exc:errors.append(f"{source}: {exc}")
    if company_search:
        cj,ce=discover_company_boards(queries,limit=min(limit_per_source,20),regions=regions);jobs.extend(cj);errors.extend(ce)
    jobs=dedupe(jobs)
    fresh=[j for j in jobs if is_fresh(j,freshness)]
    fresh.sort(key=lambda x:x.get("posted_at","") or "",reverse=True)
    return fresh,errors
