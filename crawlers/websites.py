# crawlers/websites.py
from typing import List, Dict
import json
from urllib.parse import urljoin
from .base import fetch, soupify, is_remote_text, normalize_items, parse_salary

# ----------------------------
# Helpers
# ----------------------------
def _clip(s: str, n: int = 500) -> str:
    s = (s or "").strip()
    return (s[: n - 1] + "…") if len(s) > n else s

def _with_salary_fields(item: Dict, text: str) -> Dict:
    mn, mx, cur, per = parse_salary(text or "")
    if mn is not None: item["salary_min"] = mn
    if mx is not None: item["salary_max"] = mx
    if cur: item["currency"] = cur
    if per: item["period"] = per
    return item

# =========================================================
# Core Remote JOB Sources (you already had)
# =========================================================

def scrape_remoteok() -> List[Dict]:
    data = json.loads(fetch("https://remoteok.com/api"))
    out = []
    for job in data[1:]:
        url = job.get("url") or ""
        title = job.get("position") or ""
        company = job.get("company") or ""
        if not url or not title:
            continue
        if not is_remote_text(" ".join([title, company, "remote"])):  # keep remote-only
            continue

        salary_text = job.get("salary") or job.get("compensation") or ""
        item = {
            "title": title,
            "description": job.get("description") or ", ".join(job.get("tags", [])),
            "link": url,
            "category": "JOB",
            "company": company,
            "location": job.get("location") or "Remote",
            "tags": job.get("tags") or [],
            "extras": job,
        }
        text_for_salary = " ".join([
            salary_text,
            job.get("description") or "",
            title, company
        ])
        out.append(_with_salary_fields(item, text_for_salary))
    return normalize_items(out)

def scrape_remotive() -> List[Dict]:
    data = json.loads(fetch("https://remotive.com/api/remote-jobs"))
    jobs = data.get("jobs", [])
    out = []
    for j in jobs:
        title = j.get("title", "")
        company = j.get("company_name", "")
        loc = j.get("candidate_required_location", "")
        if not is_remote_text(" ".join([title, company, loc, "remote"])):
            continue

        mn = j.get("salary_min")
        mx = j.get("salary_max")
        cur = (j.get("salary_currency") or "").upper()
        per = (j.get("salary_type") or "").upper()

        item = {
            "title": title,
            "description": j.get("description") or j.get("category",""),
            "link": j.get("url",""),
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": [j.get("job_type",""), j.get("category","")] + (j.get("tags") or []),
            "extras": j,
        }
        if mn is None and mx is None:
            text_for_salary = " ".join([j.get("salary","") or "", j.get("description") or "", title, company])
            item = _with_salary_fields(item, text_for_salary)
        else:
            if mn is not None: item["salary_min"] = mn
            if mx is not None: item["salary_max"] = mx
            if cur: item["currency"] = cur
            if per: item["period"] = per
        out.append(item)
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
        if not is_remote_text(f"{company} {title} remote"):
            continue
        item = {
            "title": title,
            "description": region,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": region or "Remote",
            "tags": [t.get_text(strip=True) for t in li.select("span.feature")],
            "extras": {"region": region},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {region}"))
    return normalize_items(out)

def scrape_remote_co() -> List[Dict]:
    html = fetch("https://remote.co/remote-jobs/")
    s = soupify(html)
    out = []
    for card in s.select("div.card"):
        a = card.select_one("a.card-title")
        if not a:
            continue
        title = a.get_text(strip=True)
        link = a.get("href")
        company = (card.select_one(".card-company") or {}).get_text(strip=True)
        loc = (card.select_one(".card-location") or {}).get_text(strip=True)
        if not is_remote_text(f"{title} remote"):
            continue
        item = {
            "title": title,
            "description": loc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {loc}"))
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
        if not is_remote_text(f"{title} remote"):
            continue
        item = {
            "title": title,
            "description": " ".join(tags) or loc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": tags,
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {loc} {' '.join(tags)}"))
    return normalize_items(out)

def scrape_wellfound() -> List[Dict]:
    html = fetch("https://wellfound.com/role/software-engineer?remote=true")
    s = soupify(html)
    out = []
    for card in s.select("[data-test='job-listing-card'] a[href*='/jobs/']"):
        title = card.get_text(strip=True)
        link = urljoin("https://wellfound.com", card.get("href",""))
        item = {
            "title": title,
            "description": "Wellfound listing (remote)",
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, title))
    return normalize_items(out)

# =========================================================
# Extra Remote JOB Sources (new)
# =========================================================

def scrape_himalayas() -> list[dict]:
    html = fetch("https://himalayas.app/jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        title = (a.get_text(" ", strip=True) or "")
        link = urljoin("https://himalayas.app", a.get("href", ""))
        card = a.parent
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote anywhere"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "tags": [],
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_jobicy() -> list[dict]:
    html = fetch("https://jobicy.com/remote-jobs")
    s = soupify(html)
    out: list[dict] = []
    for li in s.select("li[class*='jl'] a[href*='/jobs/']"):
        link = li.get("href", "").strip()
        title = li.get_text(" ", strip=True)
        row = li.find_parent("li")
        company = (row.select_one(".company") or {}).get_text(strip=True) if row else ""
        loc = (row.select_one(".region") or {}).get_text(strip=True) if row else ""
        desc = " ".join(x.get_text(" ", strip=True) for x in (row.select(".desc, .job-tags") if row else []))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {loc} {desc} remote anywhere wfh"):
            continue
        item = {
            "title": title,
            "description": _clip(f"{company} {loc} {desc}"),
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": [],
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {loc} {desc}"))
    return normalize_items(out)

def scrape_skipthedrive() -> list[dict]:
    html = fetch("https://skipthedrive.com/remote-jobs/")
    s = soupify(html)
    out: list[dict] = []
    for row in s.select("div.jobs-listing a.job-link"):
        link = row.get("href", "").strip()
        title = (row.select_one(".job-title") or {}).get_text(strip=True) or row.get_text(strip=True)
        meta = row.find_parent("div", class_="job") or row
        company = (meta.select_one(".company") or {}).get_text(strip=True)
        loc = (meta.select_one(".location") or {}).get_text(strip=True)
        desc = " ".join(x.get_text(" ", strip=True) for x in meta.select(".desc, .tags"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {desc} remote anywhere"):
            continue
        item = {
            "title": title,
            "description": _clip(f"{company} {loc} {desc}"),
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": [],
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {loc} {desc}"))
    return normalize_items(out)

def scrape_remotees() -> list[dict]:
    html = fetch("https://remotees.com/remote-jobs")
    s = soupify(html)
    out: list[dict] = []
    for art in s.select("article a[href^='/remote-']"):
        link = urljoin("https://remotees.com", art.get("href", "").strip())
        title = art.get_text(" ", strip=True)
        wrap = art.find_parent("article")
        company = (wrap.select_one(".company") or {}).get_text(strip=True) if wrap else ""
        loc = (wrap.select_one(".location") or {}).get_text(strip=True) if wrap else ""
        desc = " ".join(x.get_text(" ", strip=True) for x in (wrap.select(".tags, .desc") if wrap else []))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {desc} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(f"{company} {loc} {desc}"),
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": [],
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {loc} {desc}"))
    return normalize_items(out)

def scrape_powertofly() -> list[dict]:
    html = fetch("https://powertofly.com/jobs?location=Remote")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://powertofly.com", a.get("href", "").strip())
        title = a.get_text(" ", strip=True)
        card = a.find_parent()
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "tags": [],
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_freshremote() -> list[dict]:
    html = fetch("https://freshremote.work/")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://freshremote.work", a.get("href", "").strip())
        title = a.get_text(" ", strip=True)
        card = a.find_parent()
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "tags": [],
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_remote_io() -> list[dict]:
    """remote.io/remote-jobs (best-effort; site may be JS-heavy)"""
    html = fetch("https://remote.io/remote-jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href*='/remote-jobs/']"):
        title = a.get_text(" ", strip=True)
        link = urljoin("https://remote.io", a.get("href",""))
        meta = " ".join(x.get_text(" ", strip=True) for x in a.parent.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_remotely_jobs() -> list[dict]:
    """remotely.jobs (best-effort)"""
    html = fetch("https://remotely.jobs/")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/remote-'], a[href*='/jobs/']"):
        title = a.get_text(" ", strip=True)
        link = urljoin("https://remotely.jobs", a.get("href",""))
        meta = " ".join(x.get_text(" ", strip=True) for x in a.parent.select("span,div,small"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_weremoto() -> list[dict]:
    html = fetch("https://weremoto.com/remote-jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/remote-jobs/']"):
        title = a.get_text(" ", strip=True)
        link = urljoin("https://weremoto.com", a.get("href",""))
        meta = " ".join(x.get_text(" ", strip=True) for x in a.parent.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_remote_tech_jobs() -> list[dict]:
    html = fetch("https://remotetechjobs.com/")
    s = soupify(html)
    out: list[dict] = []
    for card in s.select("a[href^='/remote-'], a[href^='/job/']"):
        title = card.get_text(" ", strip=True)
        link = urljoin("https://remotetechjobs.com", card.get("href",""))
        meta = " ".join(x.get_text(" ", strip=True) for x in card.parent.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_authentic_jobs() -> list[dict]:
    html = fetch("https://www.authenticjobs.com/?location=remote")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        title = a.get_text(" ", strip=True)
        link = urljoin("https://www.authenticjobs.com", a.get("href",""))
        meta = " ".join(x.get_text(' ', strip=True) for x in a.parent.select("span,div,small"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_nofluffjobs() -> list[dict]:
    """NoFluffJobs remote board (often JS-heavy; may return [])"""
    html = fetch("https://nofluffjobs.com/remote")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/pl/job/'], a[href^='/job/']"):
        title = a.get_text(" ", strip=True)
        link = urljoin("https://nofluffjobs.com", a.get("href",""))
        meta = " ".join(x.get_text(' ', strip=True) for x in a.parent.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

def scrape_the_hub() -> list[dict]:
    html = fetch("https://thehub.io/jobs?location=remote")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        title = a.get_text(" ", strip=True)
        link = urljoin("https://thehub.io", a.get("href",""))
        meta = " ".join(x.get_text(' ', strip=True) for x in a.parent.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": "",
            "location": "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {meta}"))
    return normalize_items(out)

# =========================================================
# Your existing extra sources
# =========================================================

def scrape_working_nomads() -> list[dict]:
    html = fetch("https://www.workingnomads.com/jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        title = (a.select_one("h3") or a.select_one("span"))
        title = title.get_text(strip=True) if title else ""
        link = urljoin("https://www.workingnomads.com", a.get("href", "").strip())
        meta = " ".join(x.get_text(" ", strip=True) for x in a.select("span,div"))
        company = ""
        location = ""
        parts = [p.strip() for p in meta.split("·") if p.strip()]
        if parts:
            company = parts[0]
            if len(parts) > 1:
                location = parts[1]
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta} remote"):
            continue
        item = {
            "title": title,
            "description": meta,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": location or "Remote",
            "extras": {"meta": meta},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {location}"))
    return normalize_items(out)

def scrape_nodesk() -> list[dict]:
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
        item = {
            "title": title,
            "description": desc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": [t.get_text(strip=True) for t in card.select(".job-card__tags .tag")],
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {loc} {desc}"))
    return normalize_items(out)

def scrape_jobspresso() -> list[dict]:
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
        item = {
            "title": title,
            "description": desc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "tags": tags,
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {loc} {' '.join(tags)}"))
    return normalize_items(out)

def scrape_arc() -> list[dict]:
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
        item = {
            "title": title,
            "description": desc,
            "link": link,
            "category": "JOB",
            "company": company,
            "location": loc or "Remote",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {company} {loc} {desc}"))
    return normalize_items(out)

# =========================================================
# Projects / Hackathons
# =========================================================

def scrape_devpost() -> List[Dict]:
    html = fetch("https://devpost.com/hackathons?sort_by=deadline&status=upcoming&open_to=all")
    s = soupify(html)
    out = []
    for card in s.select(".hackathon-tile"):
        a = card.select_one("a.hackathon-tile-title")
        if not a: 
            continue
        title = a.get_text(strip=True)
        link = urljoin("https://devpost.com", a.get("href",""))
        info = (card.select_one(".takeaways") or {}).get_text(" ", strip=True)
        if not is_remote_text(f"{title} {info} online virtual global remote anywhere"):
            continue
        item = {
            "title": title,
            "description": info,
            "link": link,
            "category": "PROJECT",
            "company": "",
            "location": "Online",
            "tags": [],
            "extras": {"takeaways": info},
        }
        out.append(_with_salary_fields(item, f"{title} {info}"))
    return normalize_items(out)

def scrape_hackerearth() -> list[dict]:
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
        if not is_remote_text(f"{title} {meta} online virtual remote anywhere"):
            continue
        item = {
            "title": title,
            "description": meta,
            "link": link,
            "category": "PROJECT",
            "company": "",
            "location": "Online",
            "extras": {},
        }
        out.append(item)
    return normalize_items(out)

def scrape_devfolio() -> list[dict]:
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
        item = {
            "title": title,
            "description": info,
            "link": link,
            "category": "PROJECT",
            "company": "",
            "location": "Online",
            "extras": {},
        }
        out.append(item)
    return normalize_items(out)

def scrape_kaggle_placeholder() -> List[Dict]:
    return []

def scrape_gitcoin_placeholder() -> List[Dict]:
    return []
