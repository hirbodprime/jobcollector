# crawlers/base.py
import re
import requests
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
# crawlers/base.py
from __future__ import annotations
import os, time, random, json
from typing import Callable, Any
import requests
from bs4 import BeautifulSoup

# --- Optional Cloudflare client
try:
    import cloudscraper  # pip install cloudscraper
except Exception:
    cloudscraper = None
# -------------------- Remote filter --------------------

REMOTE_PATTERNS = re.compile(
    r"(?:\b(?:remote|anywhere|work[\s-]?from[\s-]?home|wfh|online|virtual)\b|"
    r"ریموت|دورکاری|کار\s*از\s*راه\s*دور)",
    re.I | re.U,
)

def is_remote_text(text: str) -> bool:
    return bool(REMOTE_PATTERNS.search(text or ""))



DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

def _session():
    # Optional proxy via env: HTTP_PROXY/HTTPS_PROXY
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS.copy())
    return s

def _maybe_cloudflare():
    if os.getenv("DISABLE_CLOUDSCRAPER") == "1":
        return None
    return cloudscraper.create_scraper() if cloudscraper else None

def _do_get(sess, url, timeout):
    return sess.get(url, timeout=timeout)

def fetch(url: str, *, timeout: int = 25, retries: int = 3, sleep_base: float = 1.0, headers: dict | None = None) -> str:
    """
    Robust HTML/text fetch with retries, exponential backoff, and optional Cloudflare bypass.
    Never returns empty string for a 200 response (basic sanity check).
    Raises RuntimeError only after exhausting retries.
    """
    hdrs = DEFAULT_HEADERS.copy()
    if headers:
        hdrs.update(headers)

    sess = _session()
    sess.headers.update(hdrs)

    cf = _maybe_cloudflare()

    last_status, last_err = None, None
    for i in range(retries):
        try:
            r = _do_get(sess, url, timeout)
            last_status = r.status_code
            if r.status_code == 200 and r.text and len(r.text) > 200:
                return r.text
            if r.status_code in (403, 429, 503) and cf is not None:
                r2 = cf.get(url, timeout=timeout, headers=hdrs)
                last_status = r2.status_code
                if r2.status_code == 200 and r2.text and len(r2.text) > 200:
                    return r2.text
        except Exception as e:
            last_err = e
        # backoff + jitter
        time.sleep(sleep_base * (2 ** i) + random.random())
    raise RuntimeError(f"fetch({url}) failed: status={last_status} err={last_err}")

def fetch_json(url: str, **kw) -> Any:
    txt = fetch(url, **kw)
    return json.loads(txt)

def soupify(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")

def parse_rss(xml_text: str) -> list[dict]:
    soup = BeautifulSoup(xml_text, "xml")
    items = []
    entries = soup.find_all("item") or soup.find_all("entry")
    for e in entries:
        def _find(*names):
            for n in names:
                tag = e.find(n)
                if tag:
                    return tag
            return None
        title = (_find("title").get_text(strip=True) if _find("title") else "")
        link = ""
        tag_link = _find("link")
        if tag_link:
            if tag_link.has_attr("href"):  # Atom
                link = tag_link["href"]
            else:  # RSS
                link = tag_link.get_text(strip=True)
        if not link and _find("guid"):
            link = _find("guid").get_text(strip=True)
        desc_tag = _find("description", "content", "summary")
        description = desc_tag.get_text(" ", strip=True) if desc_tag else ""
        pub = (_find("pubDate", "updated", "published").get_text(strip=True)
               if _find("pubDate", "updated", "published") else "")
        if title and link:
            items.append({"title": title, "link": link, "description": description, "published": pub})
    return items

# ---- Safe text helpers used by scrapers
def txt(node, sep=" ", strip=True) -> str:
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
    from urllib.parse import urljoin
    return urljoin(base, href or "")

# ---- Non-crashing wrapper for scrapers
def no_fail(fn: Callable[..., list[dict]]) -> Callable[..., list[dict]]:
    def wrapper(*a, **kw) -> list[dict]:
        try:
            return fn(*a, **kw) or []
        except Exception as e:
            print(f"[scraper:{fn.__name__}] swallowed error: {e}")
            return []
    return wrapper

def soupify(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")




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
