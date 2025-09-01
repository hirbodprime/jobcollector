from typing import Sequence
import re, html
from asgiref.sync import sync_to_async
from django.db.models import QuerySet
from core.models import Post
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue

# ----------------- Text utilities -----------------

STOPWORDS = {
    "a","an","and","are","as","at","be","been","being","but","by","can","for","from",
    "has","have","having","he","her","him","his","how","i","if","in","into","is","it",
    "its","of","on","or","our","out","over","per","so","such","than","that","the",
    "their","them","then","there","these","they","this","those","to","up","we","what",
    "when","where","which","who","will","with","you","your","yours","about","across",
    "all","also","any","apply","ability","able","including","include","includes",
    "role","position","job","company","team","work","working","remote","fully","hybrid",
    "experience","experienced","responsible","responsibilities","requirements",
    "preferred","preferred","preferred","preferred"
}

SKILL_HINTS = {
    "python","django","fastapi","flask","sql","postgres","mysql","sqlite","mongodb",
    "redis","kafka","airflow","spark","hadoop","aws","gcp","azure","kubernetes","docker",
    "terraform","ansible","linux","golang","go","rust","java","kotlin","scala","swift",
    "javascript","typescript","react","vue","angular","node","nextjs","nuxt","svelte",
    "devops","ml","ai","nlp","cv","pytorch","tensorflow","sklearn","pandas","numpy",
    "etl","bi","analytics","product","design","figma","ui","ux","qa","selenium",
    "cybersecurity","blockchain","solidity","web3","defi","data","backend","frontend",
    "fullstack"
}

def _repair_mojibake(s: str) -> str:
    """Attempt to repair common UTF-8 <- latin1 mojibake."""
    if not s:
        return ""
    if "Ã" in s or "â" in s or "ð" in s:
        try:
            fixed = s.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
            if fixed:
                s = fixed
        except Exception:
            pass
    repl = {
        "â": "'", "â": "–", "â": "—", "â¦": "…",
        "â": "“", "â": "”",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s

def clean_text(s: str | None) -> str:
    """Strip HTML, repair mojibake, normalize whitespace."""
    s = _repair_mojibake(s or "")
    s = html.unescape(s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p\s*>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()

def clip(s: str, n: int) -> str:
    return (s[: n - 1] + "…") if len(s) > n else s

def extract_hashtags(text: str, extra: list[str] | None = None) -> list[str]:
    """
    Build hashtags from text + provided tags, filtered by stopwords & length.
    """
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+\-_.]{2,20}\b", (text or "").lower())
    keep = []
    seen = set()
    for w in words:
        if w in STOPWORDS:
            continue
        if w in seen:
            continue
        seen.add(w)
        keep.append(w)

    # Prioritize skills; then fill with general keywords
    prioritized = [w for w in keep if w in SKILL_HINTS]
    rest = [w for w in keep if w not in SKILL_HINTS]

    tags = [f"#{w}" for w in (prioritized + rest)][:12]

    if extra:
        tags += [("#" + t.strip().lstrip("#").replace(" ", "")) for t in extra if t]

    # include a few defaults
    tags += ["#remote", "#job", "#wfh"]
    # dedupe preserve order
    out, seen = [], set()
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= 18:
            break
    return out

# ----------------- Formatting -----------------

def _plausible_salary(period: str, value: float) -> bool:
    if value is None:
        return False
    period = (period or "").lower()
    if period == "hourly":   return 5 <= value <= 500
    if period == "daily":    return 50 <= value <= 5000
    if period == "monthly":  return 500 <= value <= 100_000
    if period == "yearly":   return 8_000 <= value <= 1_500_000
    return False

def _format_salary_line(p: dict) -> str | None:
    """
    Show salary only if it's sane. If period is missing, guess conservatively:
    <= 300 -> hourly, >= 5000 -> yearly, otherwise hide.
    """
    cur = (p.get("currency") or "").upper()
    mn = p.get("salary_min")
    mx = p.get("salary_max")
    per = (p.get("period") or "").lower()

    if mn is None and mx is None:
        return None

    hi = mx if mx is not None else mn
    lo = mn if mn is not None else mx

    # Guess period if missing
    guessed = False
    if not per:
        if hi is not None and hi <= 300:
            per, guessed = "hourly", True
        elif hi is not None and hi >= 5000:
            per, guessed = "yearly", True
        else:
            # No strong signal -> don't show salary
            return None

    if not _plausible_salary(per, hi or 0):
        return None

    if lo is not None and hi is not None and lo != hi:
        rng = f"{float(lo):.0f}–{float(hi):.0f}"
    else:
        rng = f"{float(lo or hi):.0f}"

    cur_prefix = f"{cur} " if cur else ""
    return f"💰 Salary: {cur_prefix}{rng}/{per}"

def format_post(p: dict) -> str:
    """
    English-only, clean text. Expects keys:
      id, title, description, link, category, source_name,
      company, location, salary_min, salary_max, currency, period, tags
    """
    header = {
        "JOB": "💼 New Remote Job",
        "PROJECT": "🚀 New Project",
        "COMPETITION": "🏆 New Competition",
    }.get(p.get("category"), "📢 Opportunity")

    title = clean_text(p.get("title"))
    desc = clean_text(p.get("description"))
    link = (p.get("link") or "").strip()
    source_name = clean_text(p.get("source_name"))
    company = clean_text(p.get("company"))
    location = clean_text(p.get("location"))

    # Hashtags
    raw_tags = p.get("tags") or []
    hashtags = " ".join(extract_hashtags(f"{title} {desc}", raw_tags))

    lines = [header, "─────────────────"]
    if source_name:
        lines.append(f"🌐 Source: {source_name}")
    if company and len(company) > 1:
        lines.append(f"🏢 Company: {company}")
    if location and len(location) > 1 and location.lower() != "remote":
        lines.append(f"📍 Location: {location}")
    if title:
        lines.append(f"📌 Title: {title}")
    if desc:
        lines.append(f"📝 Description: {clip(desc, 1000)}")

    salary_line = _format_salary_line(p)
    if salary_line:
        lines.append(salary_line)

    if link:
        lines.append(f"🔗 Link: {link}")

    lines.append("")
    lines.append(hashtags)
    return "\n".join(lines)

# ----------------- DB (async-safe) -----------------

@sync_to_async
def fetch_unposted(limit: int = 1) -> list[dict]:
    qs: QuerySet[Post] = (
        Post.objects
        .select_related("source")
        .filter(posted_to_channel=False)
        .order_by("created_at")[:limit]
    )
    out: list[dict] = []
    for obj in qs:
        out.append({
            "id": obj.id,
            "title": obj.title,
            "description": obj.description or "",
            "link": obj.link,
            "category": obj.category,
            "source_name": obj.source.name if obj.source_id else "",
            "company": obj.company or "",
            "location": obj.location or "",
            "salary_min": obj.salary_min,
            "salary_max": obj.salary_max,
            "currency": obj.currency or "",
            "period": obj.period or "",
            "tags": obj.tags or [],
        })
    return out

@sync_to_async
def mark_posted(ids: list[int]) -> None:
    Post.objects.filter(id__in=ids).update(posted_to_channel=True)

# ----------------- Bot jobs & handlers -----------------

async def post_new_items_job(context: ContextTypes.DEFAULT_TYPE):
    """Runs every N seconds. Posts at most ONE item to throttle the channel."""
    channel = context.bot_data.get("target_channel")
    if not channel:
        return

    items = await fetch_unposted(limit=1)
    if not items:
        return

    p = items[0]
    try:
        await context.bot.send_message(
            chat_id=channel,
            text=format_post(p),
            disable_web_page_preview=True,
        )
        await mark_posted([p["id"]])
        print(f"✅ Posted: {p['title']}")
    except Exception as e:
        print(f"⚠️ Failed to post: {e}")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")


def build_application(bot_token: str, target_channel: str, post_interval_seconds: int = 10):
    # ⬇️ Disable the Updater to avoid PTB 20.8 + Python 3.13 issue
    app = (
        Application.builder()
        .token(bot_token)
        .job_queue(JobQueue())
        .updater(None)          # <<< important
        .build()
    )

    # You can keep the /ping handler, but without Updater/polling it won't receive updates.
    # app.add_handler(CommandHandler("ping", ping))

    if app.job_queue:
        app.job_queue.run_repeating(
            post_new_items_job,
            interval=post_interval_seconds,
            first=0,
        )

    app.bot_data["target_channel"] = target_channel
    app.bot_data["post_interval"] = post_interval_seconds
    return app
