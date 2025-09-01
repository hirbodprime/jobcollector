# crawlers/base.py
import re
import requests
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup

# -------------------- Remote filter --------------------

REMOTE_PATTERNS = re.compile(
    r"(?:\b(?:remote|anywhere|work[\s-]?from[\s-]?home|wfh|online|virtual)\b|"
    r"ریموت|دورکاری|کار\s*از\s*راه\s*دور)",
    re.I | re.U,
)

def is_remote_text(text: str) -> bool:
    return bool(REMOTE_PATTERNS.search(text or ""))

# -------------------- HTTP helpers --------------------

# crawlers/base.py (improve fetch)
import time
import random
import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

def fetch(url: str, *, timeout: int = 25, retries: int = 3, sleep_base: float = 1.0) -> str:
    last_status = None
    last_err = None
    for i in range(retries):
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            last_status = resp.status_code
            if resp.status_code == 200 and resp.text and len(resp.text) > 200:
                return resp.text
            # 403/429/backoff
        except Exception as e:
            last_err = e
        time.sleep(sleep_base * (2 ** i) + random.random())
    raise RuntimeError(f"fetch({url}) failed: status={last_status} err={last_err}")


import os
from bs4 import BeautifulSoup, FeatureNotFound

def soupify(html: str) -> BeautifulSoup:
    """
    Use lxml if installed; otherwise fall back to Python's built-in html.parser.
    You can force a parser via .env: BS_PARSER=html.parser or lxml
    """
    preferred = (os.getenv("BS_PARSER") or "").strip()
    candidates = [preferred] if preferred else []
    candidates += ["lxml", "html.parser"]

    for parser in candidates:
        try:
            return BeautifulSoup(html, parser)
        except FeatureNotFound:
            continue
    # final fallback
    return BeautifulSoup(html, "html.parser")


# -------------------- Salary parsing (robust) --------------------

# Tokens (no duplicate named groups)
AMOUNT_TOKEN = r"\d+(?:[.,]\d{3})*(?:[.,]\d+)?\s*[kKmM]?"
CURRENCY_TOKEN = r"(?:USD|EUR|GBP|CAD|AUD|CHF|JPY|\$|€|£)"
PERIOD_TOKEN = r"(?:per\s+(?:year|month|hour|day)|/year|/month|/hour|yr|year|annum|mo|month|hr|hour|day)"

# Example matches: "$80–120k", "€50/hour", "65k per year", "USD 120000 yr"
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

# -------------------- Normalization --------------------

def normalize_items(items: List[Dict]) -> List[Dict]:
    """
    Ensure required keys exist and backfill salary by parsing free text.
    We keep extra keys like company/location/tags/extras/raw_text if provided.
    """
    normalized: List[Dict] = []
    for it in items:
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
