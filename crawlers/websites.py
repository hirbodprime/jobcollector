# crawlers/websites.py
from typing import List, Dict
import json
from urllib.parse import urljoin
from .base import fetch, soupify, is_remote_text, normalize_items, parse_salary

# ---- Jobs ----

def scrape_remoteok() -> List[Dict]:
    data = json.loads(fetch("https://remoteok.com/api"))
    out = []
    for job in data[1:]:
        url = job.get("url") or ""
        title = job.get("position") or ""
        company = job.get("company") or ""
        if not url or not title:
            continue
        if not is_remote_text(" ".join([title, company, "remote"])):
            continue

        # Try to capture any salary-like text the API provides
        salary_text = job.get("salary") or job.get("compensation") or ""
        mn, mx, cur, per = parse_salary(" ".join([
            salary_text,
            job.get("description") or "",
            title, company
        ]))

        out.append({
            "title": title,
            "description": job.get("description") or ", ".join(job.get("tags", [])),
            "link": url,
            "category": "JOB",
            "company": company,
            "location": job.get("location") or "",
            "salary_min": mn,
            "salary_max": mx,
            "currency": cur,
            "period": per,
            "tags": job.get("tags") or [],
            "extras": job,
        })
    return normalize_items(out)

def scrape_remotive() -> List[Dict]:
    data = json.loads(fetch("https://remotive.com/api/remote-jobs"))
    jobs = data.get("jobs", [])
    out = []
    for j in jobs:
        title = j.get("title", "")
        company = j.get("company_name", "")
        if not is_remote_text(" ".join([title, company, j.get("candidate_required_location",""), "remote"])):
            continue

        # Remotive sometimes exposes salary_* fields
        mn = j.get("salary_min")
        mx = j.get("salary_max")
        cur = (j.get("salary_currency") or "").upper()
        per = (j.get("salary_type") or "").upper()
        if mn is None and mx is None:
            pmn, pmx, pcur, pper = parse_salary(" ".join([
                j.get("salary","") or "",
                j.get("description") or "",
                title, company
            ]))
            mn, mx = mn or pmn, mx or pmx
            cur, per = cur or pcur, per or pper

        out.append({
            "title": title,
            "description": j.get("description") or j.get("category",""),
            "link": j.get("url",""),
            "category": "JOB",
            "company": company,
            "location": j.get("candidate_required_location",""),
            "salary_min": mn,
            "salary_max": mx,
            "currency": cur,
            "period": per,
            "tags": [j.get("job_type",""), j.get("category","")] + (j.get("tags") or []),
            "extras": j,
        })
    return normalize_items(out)

def scrape_wwr() -> List[Dict]:
    html = fetch("https://weworkremotely.com/remote-jobs")
    s = soupify(html)
    out = []
    for li in s.select("section.jobs li.feature"):
        a = li.select_one("a")
        if not a or not a.get("href"): 
            continue
        link = urljoin("https://weworkremotely.com", a.get("href"))
        company = (li.select_one("span.company") or {}).get_text(strip=True)
        title = (li.select_one("span.title") or {}).get_text(strip=True)
        region = (li.select_one("span.region") or {}).get_text(strip=True)
        if not is_remote_text(" ".join([company or "", title or "", "remote"])):
            continue
        out.append({
            "title": title,
            "description": region,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": region,
            "tags": [t.get_text(strip=True) for t in li.select("span.feature")],
            "extras": {"region": region},
        })
    return normalize_items(out)

def scrape_remote_co() -> List[Dict]:
    html = fetch("https://remote.co/remote-jobs/")
    s = soupify(html)
    out = []
    for card in s.select("div.card"):
        a = card.select_one("a.card-title")
        if not a: continue
        title = a.get_text(strip=True)
        link = a.get("href")
        company = (card.select_one(".card-company") or {}).get_text(strip=True)
        loc = (card.select_one(".card-location") or {}).get_text(strip=True)
        if not is_remote_text(title + " remote"):
            continue
        out.append({
            "title": title,
            "description": loc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc,
            "extras": {},
        })
    return normalize_items(out)

def scrape_justremote() -> List[Dict]:
    html = fetch("https://justremote.co/remote-jobs")
    s = soupify(html)
    out = []
    for job in s.select("a.job-card"):
        title = (job.select_one(".job-title") or {}).get_text(strip=True)
        company = (job.select_one(".company") or {}).get_text(strip=True)
        link = urljoin("https://justremote.co", job.get("href",""))
        loc = (job.select_one(".job-location") or {}).get_text(strip=True)
        tags = [t.get_text(strip=True) for t in job.select(".job-tag")]
        if not is_remote_text(title + " remote"):
            continue
        out.append({
            "title": title,
            "description": " ".join(tags) or loc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc,
            "tags": tags,
            "extras": {},
        })
    return normalize_items(out)

def scrape_wellfound() -> List[Dict]:
    html = fetch("https://wellfound.com/role/software-engineer?remote=true")
    s = soupify(html)
    out = []
    for card in s.select("[data-test='job-listing-card'] a[href*='/jobs/']"):
        title = card.get_text(strip=True)
        link = urljoin("https://wellfound.com", card.get("href",""))
        out.append({
            "title": title,
            "description": "Wellfound listing (remote)",
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        })
    return normalize_items(out)

# ---- Projects / Competitions ----

def scrape_devpost() -> List[Dict]:
    html = fetch("https://devpost.com/hackathons?sort_by=deadline&status=upcoming&open_to=all")
    s = soupify(html)
    out = []
    for card in s.select(".hackathon-tile"):
        a = card.select_one("a.hackathon-tile-title")
        if not a: continue
        title = a.get_text(strip=True)
        link = urljoin("https://devpost.com", a.get("href",""))
        info = (card.select_one(".takeaways") or {}).get_text(" ", strip=True)
        if not is_remote_text(title + " " + info + " online virtual global remote anywhere"):
            continue
        out.append({
            "title": title,
            "description": info,
            "link": link,
            "category": "PROJECT",
            "company": "",
            "location": "Online",
            "tags": [],
            "extras": {"takeaways": info},
        })
    return normalize_items(out)

def scrape_kaggle_placeholder() -> List[Dict]:
    return []

def scrape_gitcoin_placeholder() -> List[Dict]:
    return []



# =========================================================
# Extra Remote JOB Sources
# =========================================================

def scrape_working_nomads() -> list[dict]:
    """
    Working Nomads - https://www.workingnomads.com/jobs
    HTML lists. We'll scrape title, company, location, link and infer remote.
    """
    html = fetch("https://www.workingnomads.com/jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        # Card contains multiple spans: role/company/location
        title = (a.select_one("h3") or a.select_one("span")) or None
        title = title.get_text(strip=True) if title else ""
        link = urljoin("https://www.workingnomads.com", a.get("href", "").strip())
        meta = " ".join(x.get_text(" ", strip=True) for x in a.select("span,div"))
        company = ""
        location = ""
        # crude split attempt (site markup changes often)
        parts = [p.strip() for p in meta.split("·") if p.strip()]
        if parts:
            company = parts[0]
            if len(parts) > 1:
                location = parts[1]
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        out.append({
            "title": title,
            "description": meta,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": location or "Remote",
            "extras": {"meta": meta},
        })
    return normalize_items(out)

def scrape_nodesk() -> list[dict]:
    """
    NoDesk - https://nodesk.co/remote-jobs/
    """
    html = fetch("https://nodesk.co/remote-jobs/")
    s = soupify(html)
    out: list[dict] = []
    for card in s.select("article a.job-card"):
        title = (card.select_one(".job-card__title") or {}).get_text(strip=True)
        company = (card.select_one(".job-card__company") or {}).get_text(strip=True)
        loc = (card.select_one(".job-card__location") or {}).get_text(strip=True)
        link = urljoin("https://nodesk.co", card.get("href", ""))
        desc = " ".join(x.get_text(" ", strip=True) for x in card.select(".job-card__meta, .job-card__tags"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {desc} remote"):
            continue
        out.append({
            "title": title,
            "description": desc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": [t.get_text(strip=True) for t in card.select(".job-card__tags .tag")],
            "extras": {},
        })
    return normalize_items(out)

def scrape_jobspresso() -> list[dict]:
    """
    Jobspresso - https://jobspresso.co/remote-work/
    """
    html = fetch("https://jobspresso.co/remote-work/")
    s = soupify(html)
    out: list[dict] = []
    for job in s.select("li.job_listing"):
        a = job.select_one("a.job_listing-clickbox")
        if not a:
            continue
        link = a.get("href", "").strip()
        title = (job.select_one("h3") or {}).get_text(strip=True)
        company = (job.select_one(".company strong") or {}).get_text(strip=True)
        loc = (job.select_one(".location") or {}).get_text(strip=True)
        tags = [t.get_text(strip=True) for t in job.select(".job-types li")]
        desc = " ".join([loc] + tags)
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {desc} remote"):
            continue
        out.append({
            "title": title,
            "description": desc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": tags,
            "extras": {},
        })
    return normalize_items(out)

def scrape_arc() -> list[dict]:
    """
    Arc.dev - https://arc.dev/remote-jobs
    """
    html = fetch("https://arc.dev/remote-jobs")
    s = soupify(html)
    out: list[dict] = []
    for card in s.select("a[href^='/remote-jobs/']"):
        link = urljoin("https://arc.dev", card.get("href", "").strip())
        title = (card.select_one("[data-testid='job-card-title']") or card.select_one("h3") or {}).get_text(strip=True)
        company = (card.select_one("[data-testid='job-card-company']") or {}).get_text(strip=True)
        loc = (card.select_one("[data-testid='job-card-location']") or {}).get_text(strip=True)
        desc = " ".join(x.get_text(" ", strip=True) for x in card.select("[data-testid*='job-card']"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {desc} remote anywhere"):
            continue
        out.append({
            "title": title,
            "description": desc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "extras": {},
        })
    return normalize_items(out)

# =========================================================
# Projects / Hackathons
# =========================================================

def scrape_hackerearth() -> list[dict]:
    """
    HackerEarth Challenges - https://www.hackerearth.com/challenges/
    We'll include hackathons/hiring challenges that indicate online/remote.
    """
    html = fetch("https://www.hackerearth.com/challenges/")
    s = soupify(html)
    out: list[dict] = []
    for card in s.select("div.challenge-card-modern"):
        a = card.select_one("a.challenge-card-link")
        if not a:
            continue
        link = urljoin("https://www.hackerearth.com", a.get("href", "").strip())
        title = (card.select_one(".challenge-list-title") or {}).get_text(strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select(".challenge-card-wrapper, .event-info"))
        # consider online/virtual keywords
        if not is_remote_text(f"{title} {meta} online virtual remote anywhere"):
            continue
        out.append({
            "title": title,
            "description": meta,
            "link": link,
            "category": "PROJECT",
            "company": "",
            "location": "Online",
            "extras": {},
        })
    return normalize_items(out)

def scrape_devfolio() -> list[dict]:
    """
    Devfolio Hackathons - https://devfolio.co/hackathons
    """
    html = fetch("https://devfolio.co/hackathons")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/hackathons/']"):
        link = urljoin("https://devfolio.co", a.get("href", "").strip())
        title = a.get_text(strip=True)
        info = " ".join(x.get_text(" ", strip=True) for x in a.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {info} online virtual remote"):
            continue
        out.append({
            "title": title,
            "description": info,
            "link": link,
            "category": "PROJECT",
            "company": "",
            "location": "Online",
            "extras": {},
        })
    return normalize_items(out)