import re
from typing import List, Dict
from urllib.parse import urlparse
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from .base import is_remote_text

def username_from_url(url: str) -> str:
    if not url: return ""
    u = urlparse(url)
    if u.netloc.endswith("t.me"):
        return u.path.strip("/").split("/")[:1][0]
    if url.startswith("@"):
        return url[1:]
    return url.strip("/")

async def fetch_new_from_channel(client: TelegramClient, channel_username: str, limit: int = 50) -> List[Dict]:
    out: List[Dict] = []
    try:
        async for m in client.iter_messages(channel_username, limit=limit):
            text = (m.message or "").strip()
            if not text: continue
            if not is_remote_text(text):
                continue
            link = f"https://t.me/{channel_username}/{m.id}"
            title = text.splitlines()[0][:120]
            out.append({
                "title": title,
                "description": text[:2000],
                "link": link,
                "category": "JOB",
            })
    except FloodWaitError as e:
        # Back off automatically via scheduler loop
        pass
    return out

async def build_telethon_client(api_id: int, api_hash: str, string_session: str | None = None) -> TelegramClient:
    
    if string_session:
        client = TelegramClient(StringSession(string_session), api_id, api_hash)
    else:
        client = TelegramClient("telethon.session", api_id, api_hash)
    await client.start()  # first run: prompts for phone/OTP in console
    return client
