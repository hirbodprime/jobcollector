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
# -------------------------------
# IRANIAN JOB BOARDS (take ALL jobs; no remote filter)
# -------------------------------

def scrape_jobinja() -> list[dict]:
    html = fetch("https://jobinja.ir/jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://jobinja.ir", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent(["article", "li", "div"])
        comp = (card.select_one(".c-jobList__meta-item--company, [class*='company']") or {}).get_text(" ", strip=True) if card else ""
        loc  = (card.select_one(".c-jobList__meta-item--location, [class*='location']") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": comp,
            "location": loc or "",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {comp} {loc} {meta}"))
    return normalize_items(out)

def scrape_jobvision() -> list[dict]:
    html = fetch("https://jobvision.ir/jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://jobvision.ir", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent(["article","li","div"])
        comp = (card.select_one("[class*='company'], .company") or {}).get_text(" ", strip=True) if card else ""
        loc  = (card.select_one("[class*='location'], .location") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": comp,
            "location": loc or "",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {comp} {loc} {meta}"))
    return normalize_items(out)

def scrape_irantalent() -> list[dict]:
    html = fetch("https://www.irantalent.com/jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href*='/job/'], a[href*='/jobs/']"):
        link = urljoin("https://www.irantalent.com", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent(["article","li","div"])
        comp = (card.select_one("[class*='company'], .company") or {}).get_text(" ", strip=True) if card else ""
        loc  = (card.select_one("[class*='location'], .location") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li,small") if card else []))
        if not title or not link:
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": comp,
            "location": loc or "",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {comp} {loc} {meta}"))
    return normalize_items(out)

def scrape_karboom() -> list[dict]:
    html = fetch("https://karboom.io/jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://karboom.io", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent(["article","li","div"])
        comp = (card.select_one("[class*='company'], .company") or {}).get_text(" ", strip=True) if card else ""
        loc  = (card.select_one("[class*='location'], .location") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": comp,
            "location": loc or "",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {comp} {loc} {meta}"))
    return normalize_items(out)

def scrape_e_estekhdam() -> list[dict]:
    html = fetch("https://www.e-estekhdam.com/")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/jobs/'], a[href^='/search/'], a[href^='/k']"):
        link = urljoin("https://www.e-estekhdam.com", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        if not title or not link:
            continue
        card = a.find_parent(["article","li","div"])
        comp = (card.select_one("[class*='company'], .company") or {}).get_text(" ", strip=True) if card else ""
        loc  = (card.select_one("[class*='location'], .location") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li,small") if card else []))
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": comp,
            "location": loc or "",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {comp} {loc} {meta}"))
    return normalize_items(out)

def scrape_quera_jobs() -> list[dict]:
    html = fetch("https://quera.org/jobs")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/job/'], a[href^='/jobs/']"):
        link = urljoin("https://quera.org", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent(["article","li","div"])
        comp = (card.select_one("[class*='company'], .company") or {}).get_text(" ", strip=True) if card else ""
        loc  = (card.select_one("[class*='location'], .location") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li,small") if card else []))
        if not title or not link:
            continue
        item = {
            "title": title,
            "description": _clip(meta),
            "link": link,
            "category": "JOB",
            "company": comp,
            "location": loc or "",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {comp} {loc} {meta}"))
    return normalize_items(out)

# -------------------------------
# IRANIAN FREELANCE / PROJECT BOARDS (take ALL projects)
# -------------------------------

def scrape_ponisha() -> list[dict]:
    # public search list is SSR
    html = fetch("https://ponisha.ir/search/projects")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/project/']"):
        link = urljoin("https://ponisha.ir", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent(["article","li","div"])
        budget = (card.select_one("[class*='budget'], .budget") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li,small") if card else []))
        if not title or not link:
            continue
        item = {
            "title": title,
            "description": _clip(f"{budget} {meta}"),
            "link": link,
            "category": "PROJECT",
            "company": "",
            "location": "Online",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {budget} {meta}"))
    return normalize_items(out)

def scrape_parscoders() -> list[dict]:
    html = fetch("https://parscoders.com/project/list/")
    s = soupify(html)
    out: list[dict] = []
    for a in s.select("a[href^='/project/']"):
        link = urljoin("https://parscoders.com", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent(["article","li","div","tr"])
        budget = (card.select_one("[class*='budget'], .budget, .price") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li,td,small") if card else []))
        if not title or not link:
            continue
        item = {
            "title": title,
            "description": _clip(f"{budget} {meta}"),
            "link": link,
            "category": "PROJECT",
            "company": "",
            "location": "Online",
            "extras": {},
        }
        out.append(_with_salary_fields(item, f"{title} {budget} {meta}"))
    return normalize_items(out)
def scrape_himalayas() -> list[dict]:
    html = fetch("https://himalayas.app/jobs")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://himalayas.app", a.get("href", ""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("article") or a.find_parent("div")
        company = (card.select_one("[data-testid*='company'], .text-gray-500, .text-slate-500") or {}).get_text(" ", strip=True) if card else ""
        loc = "Remote"
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link: 
            continue
        if not is_remote_text(f"{title} {meta} remote anywhere"):
            continue
        item = {
            "title": title, "description": _clip(meta), "link": link, "category": "JOB",
            "company": company, "location": loc, "extras": {}
        }
        out.append(_with_salary_fields(item, f"{title} {company} {meta}"))
    return normalize_items(out)

def scrape_remote_io() -> list[dict]:
    html = fetch("https://remote.io/remote-jobs")
    s = soupify(html)
    out = []
    for card in s.select("a.job-card"):
        link = urljoin("https://remote.io", card.get("href",""))
        title = (card.select_one(".job-title") or {}).get_text(strip=True)
        company = (card.select_one(".company") or {}).get_text(strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select(".job-tags, .meta, .location"))
        if not title or not link: 
            continue
        if not is_remote_text(f"{title} {meta}"):
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, f"{title} {company} {meta}"))
    return normalize_items(out)

def scrape_skipthedrive() -> list[dict]:
    html = fetch("https://skipthedrive.com/remote-jobs/")
    s = soupify(html)
    out = []
    for row in s.select("table.jobs-table tbody tr"):
        a = row.select_one("a")
        if not a: 
            continue
        link = a.get("href","")
        title = a.get_text(" ", strip=True)
        company = (row.select_one("td.company") or {}).get_text(" ", strip=True)
        loc = (row.select_one("td.location") or {}).get_text(" ", strip=True) or "Remote"
        meta = " ".join(x.get_text(" ", strip=True) for x in row.select("td"))
        if not is_remote_text(f"{title} {meta} remote"): 
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": loc, "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_jobicy() -> list[dict]:
    html = fetch("https://jobicy.com/remote-jobs")
    s = soupify(html)
    out = []
    for card in s.select("a.job-card"):
        link = card.get("href","")
        title = (card.select_one(".job-title") or {}).get_text(strip=True)
        company = (card.select_one(".company") or {}).get_text(strip=True)
        loc = (card.select_one(".job-location") or {}).get_text(strip=True) or "Remote"
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select(".job-meta, .job-tags"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta}"):
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": loc, "extras": {}}
        out.append(_with_salary_fields(item, f"{title} {company} {meta}"))
    return normalize_items(out)

def scrape_remotees() -> list[dict]:
    html = fetch("https://remotees.com/remote-jobs")
    s = soupify(html)
    out = []
    for row in s.select("table.jobs-table tr"):
        a = row.select_one("a[href^='/remote-jobs/']")
        if not a: 
            continue
        link = urljoin("https://remotees.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        company = (row.select_one("td.company") or {}).get_text(" ", strip=True)
        meta = " ".join(x.get_text(' ', strip=True) for x in row.select("td"))
        if not is_remote_text(f"{title} {meta}"): 
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_remotely_jobs() -> list[dict]:
    html = fetch("https://remotely.jobs/")
    s = soupify(html)
    out = []
    for card in s.select("a[href^='/remote/']"):
        link = urljoin("https://remotely.jobs", card.get("href",""))
        title = (card.select_one("h3, .job-title") or {}).get_text(strip=True)
        company = (card.select_one(".company") or {}).get_text(strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select("span,div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta}"): 
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_weremoto() -> list[dict]:
    html = fetch("https://weremoto.com/remote-jobs")
    s = soupify(html)
    out = []
    for card in s.select("a[href^='/remote-jobs/']"):
        link = urljoin("https://weremoto.com", card.get("href",""))
        title = (card.select_one(".job-card__title, h3") or {}).get_text(strip=True)
        company = (card.select_one(".job-card__company") or {}).get_text(strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select(".job-card__meta, .job-card__tags, span, div"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta}"):
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_remote_tech_jobs() -> list[dict]:
    html = fetch("https://remotetechjobs.com/")
    s = soupify(html)
    out = []
    for job in s.select("a.job"):
        link = urljoin("https://remotetechjobs.com", job.get("href",""))
        title = (job.select_one(".title") or {}).get_text(strip=True)
        company = (job.select_one(".company") or {}).get_text(strip=True)
        loc = (job.select_one(".location") or {}).get_text(strip=True) or "Remote"
        meta = " ".join(x.get_text(" ", strip=True) for x in job.select(".tags, .meta"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta}"):
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": loc, "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_powertofly() -> list[dict]:
    html = fetch("https://powertofly.com/jobs?location=Remote")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://powertofly.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("article") or a.find_parent("div")
        company = (card.select_one("[class*='company'], .company") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta}"):
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_freshremote() -> list[dict]:
    html = fetch("https://freshremote.work/")
    s = soupify(html)
    out = []
    for card in s.select("a.card, a[href^='/remote-jobs/']"):
        link = urljoin("https://freshremote.work", card.get("href",""))
        title = (card.select_one("h2, h3, .title") or {}).get_text(strip=True)
        company = (card.select_one(".company") or {}).get_text(strip=True)
        tags = " ".join(x.get_text(" ", strip=True) for x in card.select(".tags, .tag, .meta"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {tags}"):
            continue
        item = {"title": title, "description": _clip(tags), "link": link, "category": "JOB",
                "company": company, "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, tags))
    return normalize_items(out)

def scrape_authentic_jobs() -> list[dict]:
    html = fetch("https://www.authenticjobs.com/?location=remote")
    s = soupify(html)
    out = []
    for card in s.select("a[href*='/job/']"):
        link = card.get("href","")
        title = (card.select_one("h3, .job-title") or {}).get_text(strip=True)
        company = (card.select_one(".company") or {}).get_text(strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in card.select("span,div,li"))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta}"):
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_nofluffjobs() -> list[dict]:
    html = fetch("https://nofluffjobs.com/remote")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/job/']"):
        link = urljoin("https://nofluffjobs.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("article") or a.find_parent("div")
        company = (card.select_one("[data-testid*='company'], .posting-company") or {}).get_text(" ", strip=True) if card else ""
        loc = "Remote"
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta}"):
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": loc, "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_the_hub() -> list[dict]:
    html = fetch("https://thehub.io/jobs?location=remote")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://thehub.io", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("article") or a.find_parent("div")
        company = (card.select_one("[class*='company'], .job-company") or {}).get_text(" ", strip=True) if card else ""
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        if not is_remote_text(f"{title} {meta}"):
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "JOB",
                "company": company, "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)
def scrape_freelancer_com() -> list[dict]:
    html = fetch("https://www.freelancer.com/jobs/")
    s = soupify(html)
    out = []
    for a in s.select("a.JobSearchCard-primary-heading-link"):
        link = urljoin("https://www.freelancer.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("div", class_="JobSearchCard-item")
        desc = (card.select_one(".JobSearchCard-primary-description") or {}).get_text(" ", strip=True) if card else ""
        budget = (card.select_one(".JobSearchCard-secondary-price") or {}).get_text(" ", strip=True) if card else ""
        meta = f"{budget} {desc}"
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_peopleperhour() -> list[dict]:
    html = fetch("https://www.peopleperhour.com/freelance-jobs")
    s = soupify(html)
    out = []
    for a in s.select("a[href*='/job/']"):
        link = urljoin("https://www.peopleperhour.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent(["article","li","div"])
        budget = (card.select_one(".budget, [class*='budget']") or {}).get_text(" ", strip=True) if card else ""
        desc = " ".join(x.get_text(" ", strip=True) for x in (card.select("p, span, div") if card else []))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(f"{budget} {desc}"), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, f"{budget} {desc}"))
    return normalize_items(out)

def scrape_guru() -> list[dict]:
    html = fetch("https://www.guru.com/work/")
    s = soupify(html)
    out = []
    for a in s.select("a[href*='/work/detail/']"):
        link = urljoin("https://www.guru.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("div")
        budget = (card.select_one(".prj-bid-amt, .price, .budget") or {}).get_text(" ", strip=True) if card else ""
        desc = " ".join(x.get_text(" ", strip=True) for x in (card.select("p, span, div") if card else []))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(f"{budget} {desc}"), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, f"{budget} {desc}"))
    return normalize_items(out)

def scrape_contra() -> list[dict]:
    html = fetch("https://contra.com/jobs")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://contra.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("article") or a.find_parent("div")
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_braintrust() -> list[dict]:
    html = fetch("https://www.usebraintrust.com/jobs")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://www.usebraintrust.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("article") or a.find_parent("div")
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_gunio() -> list[dict]:
    html = fetch("https://gun.io/jobs")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://gun.io", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("article") or a.find_parent("div")
        meta = " ".join(x.get_text(" ", strip=True) for x in (card.select("span,div,li") if card else []))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_flexiple() -> list[dict]:
    html = fetch("https://flexiple.com/freelance-jobs/")
    s = soupify(html)
    out = []
    for a in s.select("a[href*='/freelance-jobs/']"):
        link = urljoin("https://flexiple.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        desc = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div,li"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(desc), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, desc))
    return normalize_items(out)

def scrape_topcoder() -> list[dict]:
    html = fetch("https://www.topcoder.com/challenges")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/challenges/']"):
        link = urljoin("https://www.topcoder.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        desc = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div,li"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(desc), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, desc))
    return normalize_items(out)

def scrape_dribbble_jobs() -> list[dict]:
    html = fetch("https://dribbble.com/jobs?location=remote")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://dribbble.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("li") or a.find_parent("div") or s).select("span,div,li"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_behance_jobs() -> list[dict]:
    html = fetch("https://www.behance.net/joblist?location=remote")
    s = soupify(html)
    out = []
    for a in s.select("a[href*='/job/']"):
        link = urljoin("https://www.behance.net", a.get("href",""))
        title = a.get_text(" ", strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("li") or a.find_parent("div") or s).select("span,div,li"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Remote", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_twine() -> list[dict]:
    html = fetch("https://www.twine.net/jobs")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/jobs/']"):
        link = urljoin("https://www.twine.net", a.get("href",""))
        title = a.get_text(" ", strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div,li"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_workana() -> list[dict]:
    html = fetch("https://www.workana.com/en/jobs")
    s = soupify(html)
    out = []
    for a in s.select("a[href*='/job/'], a[href*='/project/']"):
        link = urljoin("https://www.workana.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div,li"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_freelancermap() -> list[dict]:
    html = fetch("https://www.freelancermap.com/it-projects")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/project/']"):
        link = urljoin("https://www.freelancermap.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        meta = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div,li"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(meta), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, meta))
    return normalize_items(out)

def scrape_truelancer() -> list[dict]:
    html = fetch("https://www.truelancer.com/freelance-jobs")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/project/details/']"):
        link = urljoin("https://www.truelancer.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        card = a.find_parent("div")
        budget = (card.select_one(".budget, .amount") or {}).get_text(" ", strip=True) if card else ""
        desc = " ".join(x.get_text(" ", strip=True) for x in (card.select("p, span, div") if card else []))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(f"{budget} {desc}"), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(_with_salary_fields(item, f"{budget} {desc}"))
    return normalize_items(out)
def scrape_taikai() -> list[dict]:
    html = fetch("https://taikai.network/hackathons")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/hackathons/']"):
        link = urljoin("https://taikai.network", a.get("href",""))
        title = a.get_text(" ", strip=True)
        info = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div,li"))
        item = {"title": title, "description": _clip(info), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(item)
    return normalize_items(out)

def scrape_mlh() -> list[dict]:
    html = fetch("https://mlh.io/seasons")
    s = soupify(html)
    out = []
    for a in s.select("a[href*='/seasons/']"):
        link = urljoin("https://mlh.io", a.get("href",""))
        title = a.get_text(" ", strip=True)
        info = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div,li"))
        item = {"title": title, "description": _clip(info), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(item)
    return normalize_items(out)

def scrape_itch_io_jams() -> list[dict]:
    html = fetch("https://itch.io/jams")
    s = soupify(html)
    out = []
    for a in s.select("a.jam_title, a[href^='/jam/']"):
        link = urljoin("https://itch.io", a.get("href",""))
        title = a.get_text(" ", strip=True)
        info = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("div") or s).select("span,div,li"))
        item = {"title": title, "description": _clip(info), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(item)
    return normalize_items(out)

def scrape_codalab() -> list[dict]:
    html = fetch("https://codalab.lisn.upsaclay.fr/competitions/")
    s = soupify(html)
    out = []
    for a in s.select("a[href*='/competitions/']"):
        link = urljoin("https://codalab.lisn.upsaclay.fr", a.get("href",""))
        title = a.get_text(" ", strip=True)
        info = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("tr") or a.find_parent("div") or s).select("td, span, div"))
        item = {"title": title, "description": _clip(info), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(item)
    return normalize_items(out)

def scrape_product_hunt() -> list[dict]:
    # Project discovery (not strictly jobs) – still valuable for new projects/opportunities
    html = fetch("https://www.producthunt.com/posts")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/posts/']"):
        link = urljoin("https://www.producthunt.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        info = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(info), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(item)
    return normalize_items(out)
def scrape_kaggle() -> list[dict]:
    html = fetch("https://www.kaggle.com/competitions")
    s = soupify(html)
    out = []
    for a in s.select("a[href^='/competitions/']"):
        link = urljoin("https://www.kaggle.com", a.get("href",""))
        title = a.get_text(" ", strip=True)
        row = a.find_parent("div")
        info = " ".join(x.get_text(" ", strip=True) for x in (row.select("span,div") if row else []))
        item = {"title": title, "description": _clip(info), "link": link, "category": "COMPETITION",
                "company": "", "location": "Online", "extras": {}}
        out.append(item)
    return normalize_items(out)

def scrape_gitcoin() -> list[dict]:
    # Gitcoin explorer is mostly dynamic; fetch will often return limited SSR.
    html = fetch("https://gitcoin.co/grants/explorer")
    s = soupify(html)
    out = []
    for a in s.select("a[href*='/grants/']"):
        link = urljoin("https://gitcoin.co", a.get("href",""))
        title = a.get_text(" ", strip=True)
        info = " ".join(x.get_text(" ", strip=True) for x in (a.find_parent("article") or a.find_parent("div") or s).select("span,div,li"))
        if not title or not link:
            continue
        item = {"title": title, "description": _clip(info), "link": link, "category": "PROJECT",
                "company": "", "location": "Online", "extras": {}}
        out.append(item)
    return normalize_items(out)

# Sites that are mostly marketing/auth-only; return [] safely (parser exists, no crash)
def scrape_upwork() -> list[dict]: return []
def scrape_fiverr() -> list[dict]: return []
def scrape_toptal() -> list[dict]: return []
def scrape_lemons() -> list[dict]: return []
def scrape_malt() -> list[dict]: return []
def scrape_99designs() -> list[dict]: return []

def scrape_kaggle_placeholder() -> List[Dict]:
    return []

def scrape_gitcoin_placeholder() -> List[Dict]:
    return []
