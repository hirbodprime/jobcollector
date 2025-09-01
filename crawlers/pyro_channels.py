# crawlers/pyro_channels.py
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from urllib.parse import urlparse

from pyrogram import Client
from pyrogram.types import Message

from core.models import Source, SourceType
from asgiref.sync import sync_to_async
from .base import normalize_items

REMOTE_LINK_FMT = "https://t.me/{username}/{msg_id}"

# ----------------- DB helpers -----------------

@sync_to_async
def _get_active_channel_sources() -> List[Source]:
    return list(
        Source.objects.filter(is_active=True, type=SourceType.TELEGRAM_CHANNEL)
        .only("id", "name", "url", "category")
    )

# ----------------- Pyrogram client -----------------

async def build_pyro_client(
    api_id: int,
    api_hash: str,
    session_string: Optional[str] = None,
    proxy: Optional[dict] = None,
) -> Client:
    """
    Start a Pyrogram user client (v2 API).
    - If session_string is provided, it's used (best for headless servers).
    - Otherwise it will create/use a local session file named 'pyrogram'.
    """
    app = Client(
        name="pyrogram",
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,  # <-- v2 way
        proxy=proxy,
        workdir=".",  # keep session locally if file-based
    )
    await app.start()
    return app

# ----------------- Utilities -----------------

def _username_from_url(url: str) -> Optional[str]:
    if not url:
        return None
    u = url.strip()
    if u.startswith("@"):
        return u[1:]
    if "t.me" in u:
        p = urlparse(u)
        parts = [x for x in p.path.split("/") if x]
        return parts[0] if parts else None
    return u

def _msg_to_item(msg: Message, source_category: str, username: Optional[str]) -> Optional[Dict]:
    """
    Convert a Telegram message into our normalized item dict.
    We ingest all text/caption messages (no keyword filter).
    """
    # Skip service/system messages
    if getattr(msg, "service", False):
        return None

    text = (getattr(msg, "text", None) or getattr(msg, "caption", None) or "").strip()
    if not text:
        return None

    # Title = first non-empty line, clipped
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    title = first_line[:160] if first_line else "Opportunity"

    link = f"https://t.me/{username}/{msg.id}" if username else ""

    return {
        "title": title,
        "description": text,
        "link": link or (f"tg://resolve?domain={username}&post={msg.id}" if username else ""),
        "category": source_category,
        "company": "",
        "location": "Remote",
        "tags": [],
        "extras": {
            "chat_id": msg.chat.id if msg.chat else None,
            "message_id": msg.id,
            "date": msg.date.isoformat() if msg.date else None,
            "views": getattr(msg, "views", None),
        },
        "raw_text": text,
    }

# ----------------- Crawl & loop -----------------

async def crawl_one_channel(app: Client, source: Source, since_days: int = 7, max_msgs: int = 300) -> int:
    """
    Fetch messages from the past `since_days` days (default 7) and save them.
    No keyword filtering — we take any message that has text/caption.
    """
    username = _username_from_url(source.url)
    if not username:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

    new_items: List[Dict] = []

    async for msg in app.get_chat_history(username, limit=max_msgs):
        # Stop at older content
        msg_dt = msg.date
        if msg_dt and msg_dt.tzinfo is None:
            msg_dt = msg_dt.replace(tzinfo=timezone.utc)
        if msg_dt and msg_dt < cutoff:
            break

        item = _msg_to_item(msg, source.category, username)
        if item:
            new_items.append(item)

    if not new_items:
        return 0

    norm = normalize_items(new_items)

    # Save via scheduler's async saver (de-dupes by (source, link))
    from .scheduler import save_items  # local import to avoid cycles
    saved = await save_items(source, norm)
    return saved

async def telegram_channels_loop(interval_seconds: int, app: Client):
    """
    Background loop: poll all active channel sources every N seconds,
    ingest past-week content + any new posts.
    Tunables:
      CHANNEL_LOOKBACK_DAYS (default 7)
      CHANNEL_FETCH_LIMIT  (default 300)
    """
    while True:
        try:
            lookback_days = int(os.getenv("CHANNEL_LOOKBACK_DAYS", "7"))
            fetch_limit = int(os.getenv("CHANNEL_FETCH_LIMIT", "300"))

            sources = await _get_active_channel_sources()
            for src in sources:
                try:
                    saved = await crawl_one_channel(app, src, since_days=lookback_days, max_msgs=fetch_limit)
                    if saved:
                        print(f"[PYRO] {src.name}: saved {saved} items")
                except Exception as e:
                    print(f"[PYRO] Error crawling {src.name}: {e}")
        except Exception as e:
            print(f"[PYRO] Loop error: {e}")

        await asyncio.sleep(interval_seconds)
