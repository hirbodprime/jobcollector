# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import time
import random
import json
from typing import List, Dict, Tuple, Optional, Callable, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# --- Optional Cloudflare client (pip install cloudscraper)
try:
    import cloudscraper  # type: ignore
except Exception:
    cloudscraper = None

# =========================================================
# Remote text detector (EN + FA)
# =========================================================
REMOTE_PATTERNS = re.compile(
    r"(?:\b(?:remote|anywhere|work[\s-]?from[\s-]?home|wfh|online|virtual)\b|"
    r"ریموت|دورکاری|کار\s*از\s*راه\s*دور)",
    re.I | re.U,
)

def is_remote_text(text: str) -> bool:
    return bool(REMOTE_PATTERNS.search(text or ""))

# =========================================================
# HTTP fetch (robust)
# =========================================================

# Tunables via env (with safe defaults)
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "25"))
SCRAPER_RETRIES = int(os.getenv("SCRAPER_RETRIES", "3"))
SCRAPER_SLEEP_BASE = float(os.getenv("SCRAPER_SLEEP_BASE", "1.0"))
SCRAPER_MIN_LEN = int(os.getenv("SCRAPER_MIN_LEN", "200"))
SCRAPER_DEBUG = os.getenv("SCRAPER_DEBUG", "0") == "1"

# Rotating desktop UA pool
_UA_POOL = [
    # Recent Chrome on Windows/Mac/Linux
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.6; rv:121.0) Gecko/20100101 Firefox/121.0",
]

DEFAULT_HEADERS = {
    "User-Agent": random.choice(_UA_POOL),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
}

RETRY_STATUS = {401, 403, 404, 408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
BLOCKPAGE_RE = re.compile(
    r"(just a moment|cloudflare|cf-[-\w]*-ray|attention required|access denied|"
    r"request rejected|verify you are a human|bot detection)",
    re.I,
)

def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS.copy())
    # Honor HTTP(S)_PROXY, NO_PROXY, REQUESTS_CA_BUNDLE from env automatically (requests does this)
    return s

def _maybe_cloudflare():
    if os.getenv("DISABLE_CLOUDSCRAPER") == "1":
        return None
    return cloudscraper.create_scraper() if cloudscraper else None

def _looks_like_blockpage(text: str) -> bool:
    if not text or len(text) < 64:
        return True  # suspiciously tiny
    return bool(BLOCKPAGE_RE.search(text))

def _origin_referer(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/"

def fetch(
    url: str,
    *,
    timeout: int | None = None,
    retries: int | None = None,
    sleep_base: float | None = None,
    headers: dict | None = None,
    allow_blockpage: bool = False,
) -> str:
    """
    Fetch text with retries, exponential backoff + jitter, rotating UA, and
    optional Cloudflare bypass. Raises RuntimeError only after exhausting retries.

    Env toggles:
      SCRAPER_TIMEOUT, SCRAPER_RETRIES, SCRAPER_SLEEP_BASE, SCRAPER_MIN_LEN, SCRAPER_DEBUG
      DISABLE_CLOUDSCRAPER=1  -> disables cloudscraper fallback
    """
    t_out = timeout or SCRAPER_TIMEOUT
    n_try = retries or SCRAPER_RETRIES
    s_base = sleep_base or SCRAPER_SLEEP_BASE

    sess = _new_session()
    cf = _maybe_cloudflare()

    # Merge headers and set dynamic Referer + randomized UA each call
    hdrs = DEFAULT_HEADERS.copy()
    hdrs["User-Agent"] = random.choice(_UA_POOL)
    hdrs["Referer"] = _origin_referer(url)
    if headers:
        hdrs.update(headers)
    sess.headers.update(hdrs)

    last_status, last_err, last_text = None, None, ""

    for i in range(max(1, n_try)):
        # Change UA each attempt to reduce sticky blocking
        sess.headers["User-Agent"] = random.choice(_UA_POOL)
        if SCRAPER_DEBUG:
            print(f"[fetch] try={i+1}/{n_try} GET {url}")

        try:
            r = sess.get(url, timeout=t_out, allow_redirects=True)
            last_status = r.status_code
            last_text = r.text or ""

            if r.status_code == 200 and len(last_text) >= SCRAPER_MIN_LEN:
                if allow_blockpage or not _looks_like_blockpage(last_text):
                    return last_text

            # Fallbacks for protected sites or API responses
            if (r.status_code in RETRY_STATUS or len(last_text) < SCRAPER_MIN_LEN or _looks_like_blockpage(last_text)):
                # If JSON API, sometimes setting explicit Accept helps
                if "application/json" in (r.headers.get("Content-Type", "").lower()):
                    pass  # already JSONy
                else:
                    # Try with explicit JSON Accept
                    try:
                        r2 = sess.get(url, timeout=t_out, headers={**hdrs, "Accept": "application/json,*/*;q=0.8"})
                        last_status = r2.status_code
                        last_text = r2.text or last_text
                        if r2.status_code == 200 and len(last_text) >= SCRAPER_MIN_LEN and not _looks_like_blockpage(last_text):
                            return last_text
                    except Exception as _e2:
                        last_err = _e2

                # Cloudflare / WAF fallback
                if cf is not None:
                    try:
                        r3 = cf.get(url, timeout=t_out, headers=hdrs, allow_redirects=True)
                        last_status = r3.status_code
                        last_text = r3.text or last_text
                        if r3.status_code == 200 and len(last_text) >= SCRAPER_MIN_LEN:
                            if allow_blockpage or not _looks_like_blockpage(last_text):
                                return last_text
                    except Exception as _e3:
                        last_err = _e3

        except Exception as e:
            last_err = e

        # backoff + jitter
        time.sleep(s_base * (2 ** i) + random.random() * 0.75)

    raise RuntimeError(f"fetch({url}) failed: status={last_status} err={last_err}")

def fetch_json(url: str, **kw) -> Any:
    txt = fetch(url, headers={"Accept": "application/json, */*;q=0.8"}, **kw)
    try:
        return json.loads(txt)
    except Exception:
        # Some APIs wrap JSON in HTML; attempt to strip tags crudely
        clean = BeautifulSoup(txt, "lxml").get_text(" ", strip=True)
        return json.loads(clean)

def soupify(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "lxml")

def parse_rss(xml_text: str) -> list[dict]:
    soup = BeautifulSoup(xml_text or "", "xml")
    items: list[dict] = []
    entries = soup.find_all("item") or soup.find_all("entry") or []
    for e in entries:
        def _find(*names):
            for n in names:
                tag = e.find(n)
                if tag:
                    return tag
            return None

        ttag = _find("title")
        title = ttag.get_text(strip=True) if ttag else ""

        link = ""
        ltag = _find("link")
        if ltag:
            if ltag.has_attr("href"):  # Atom
                link = ltag["href"]
            else:  # RSS
                link = ltag.get_text(strip=True)
        if not link:
            gtag = _find("guid")
            link = gtag.get_text(strip=True) if gtag else ""

        dtag = _find("description", "content", "summary")
        description = dtag.get_text(" ", strip=True) if dtag else ""

        ptag = _find("pubDate", "updated", "published")
        published = ptag.get_text(strip=True) if ptag else ""

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "description": description,
                "published": published
            })
    return items

# =========================================================
# Safe text helpers used by scrapers
# =========================================================

def txt(node, sep: str = " ", strip: bool = True) -> str:
    try:
        return node.get_text(sep=sep, strip=strip)
    except Exception:
        return ""

def attr(node, name: str, default: str = "") -> str:
    try:
        v = node.get(name)
        return v if isinstance(v, str) else default
    except Exception:
        return default

def abs_url(base: str, href: str) -> str:
    return urljoin(base, href or "")

# Non-crashing wrapper for scrapers (use as decorator @no_fail)
def no_fail(fn: Callable[..., list[dict]]) -> Callable[..., list[dict]]:
    def wrapper(*a, **kw) -> list[dict]:
        try:
            return fn(*a, **kw) or []
        except Exception as e:
            print(f"[scraper:{fn.__name__}] swallowed error: {e}")
            return []
    return wrapper

# =========================================================
# Salary parsing (robust)
# =========================================================

AMOUNT_TOKEN = r"\d+(?:[.,]\d{3})*(?:[.,]\d+)?\s*[kKmM]?"
CURRENCY_TOKEN = r"(?:USD|EUR|GBP|CAD|AUD|CHF|JPY|SEK|NOK|DKK|INR|₮|₽|\$|€|£)"
PERIOD_TOKEN = r"(?:per\s+(?:year|month|hour|day)|/year|/month|/hour|yr|year|annum|mo|month|hr|hour|day)"

SALARY_RE = re.compile(
    rf"(?P<cur1>{CURRENCY_TOKEN})?\s*(?P<min>{AMOUNT_TOKEN})"
    rf"(?:\s*[-–]\s*(?P<cur2>{CURRENCY_TOKEN})?\s*(?P<max>{AMOUNT_TOKEN}))?"
    rf"\s*(?P<per>{PERIOD_TOKEN})?",
    re.I,
)

CURRENCY_MAP = {"$": "USD", "€": "EUR", "£": "GBP"}

def _amount_to_number(tok: str | None) -> Optional[float]:
    if not tok:
        return None
    t = tok.replace(",", "").strip().lower()
    mult = 1.0
    if t.endswith("k"):
        mult, t = 1_000.0, t[:-1]
    elif t.endswith("m"):
        mult, t = 1_000_000.0, t[:-1]
    try:
        return float(t) * mult
    except ValueError:
        return None

def _period_to_enum(per: str) -> str:
    s = (per or "").lower()
    if any(k in s for k in ["yr", "year", "annum", "/year"]):  return "YEARLY"
    if any(k in s for k in ["mo", "month", "/month"]):         return "MONTHLY"
    if any(k in s for k in ["hr", "hour", "/hour"]):           return "HOURLY"
    if "day" in s:                                             return "DAILY"
    return ""

def parse_salary(text: str) -> Tuple[Optional[float], Optional[float], str, str]:
    """
    Return (min, max, currency, period) parsed from free text.
    Currency may be blank; period is YEARLY/MONTHLY/HOURLY/DAILY or ''.
    """
    if not text:
        return None, None, "", ""
    m = SALARY_RE.search(text)
    if not m:
        return None, None, "", ""
    cur = (m.group("cur1") or m.group("cur2") or "").upper()
    cur = CURRENCY_MAP.get(cur, cur)
    mn = _amount_to_number(m.group("min"))
    mx = _amount_to_number(m.group("max"))
    per = _period_to_enum(m.group("per") or "")
    return mn, mx, cur, per

# =========================================================
# Normalization for DB insert
# =========================================================

def normalize_items(items: List[Dict]) -> List[Dict]:
    """
    Ensure required keys exist and backfill salary by parsing free text.
    We keep extra keys like company/location/tags/extras/raw_text if provided.
    """
    normalized: List[Dict] = []
    for it in items or []:
        title = (it.get("title") or "").strip()
        link = (it.get("link") or "").strip()
        if not title or not link:
            continue

        desc = (it.get("description") or "").strip()
        mn = it.get("salary_min")
        mx = it.get("salary_max")
        cur = (it.get("currency") or "").upper()
        period = it.get("period") or ""

        # If no structured salary provided, parse from text/extras
        if mn is None and mx is None:
            pmn, pmx, pcur, pper = parse_salary(
                " ".join([title, desc, str(it.get("extras") or "")])
            )
            mn = mn or pmn
            mx = mx or pmx
            cur = cur or pcur
            period = period or pper

        normalized.append({
            "title": title,
            "description": desc,
            "link": link,
            "category": it.get("category", "JOB"),
            "company": (it.get("company") or "").strip(),
            "location": (it.get("location") or "").strip(),
            "salary_min": mn,
            "salary_max": mx,
            "currency": cur,
            "period": period,
            "tags": it.get("tags") or [],
            "extras": it.get("extras") or {},
            "raw_text": it.get("raw_text") or "",
        })
    return normalized
