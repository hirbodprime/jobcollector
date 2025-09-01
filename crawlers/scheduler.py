import asyncio
from datetime import datetime, timezone
from typing import Callable, Dict, List
from asgiref.sync import sync_to_async
from django.db import IntegrityError
from core.models import Source, Post, SourceType
from . import websites
from .telegram_channels import fetch_new_from_channel, username_from_url
# crawlers/scheduler.py (only the save_items function needs updating)

Scraper = Callable[[], List[dict]]

SCRAPERS: Dict[str, Scraper] = {
    # jobs
    "scrape_remoteok": websites.scrape_remoteok,
    "scrape_remotive": websites.scrape_remotive,
    "scrape_wwr": websites.scrape_wwr,
    "scrape_remote_co": websites.scrape_remote_co,
    "scrape_justremote": websites.scrape_justremote,
    "scrape_wellfound": websites.scrape_wellfound,
    # projects/competitions
    "scrape_devpost": websites.scrape_devpost,
    "scrape_kaggle_placeholder": websites.scrape_kaggle_placeholder,
    "scrape_gitcoin_placeholder": websites.scrape_gitcoin_placeholder,
}

@sync_to_async
def list_active_sources() -> List[Source]:
    return list(Source.objects.filter(is_active=True))



@sync_to_async
def save_items(source: Source, items: list[dict]) -> int:
    saved = 0
    for it in items:
        try:
            Post.objects.get_or_create(
                source=source,
                link=it["link"],
                defaults=dict(
                    title=it["title"],
                    description=it.get("description",""),
                    category=source.category,
                    company=it.get("company",""),
                    location=it.get("location",""),
                    salary_min=it.get("salary_min"),
                    salary_max=it.get("salary_max"),
                    currency=it.get("currency",""),
                    period=it.get("period",""),
                    tags=it.get("tags") or [],
                    extras=it.get("extras") or {},
                    raw_text=it.get("raw_text",""),
                )
            )
            saved += 1
        except IntegrityError:
            pass
    Source.objects.filter(pk=source.pk).update(last_crawled=datetime.now(timezone.utc))
    return saved


# crawlers/scheduler.py (excerpt)
async def websites_loop(interval_seconds: int = 60):
    import asyncio, importlib
    from datetime import datetime
    from core.models import Source, SourceType
    from crawlers.persist import persist_items

    def get_scraper(name):
        try:
            m = importlib.import_module("crawlers.websites")
            return getattr(m, name, None)
        except Exception:
            return None

    while True:
        sources = list(Source.objects.filter(type=SourceType.WEBSITE, is_active=True))
        for src in sources:
            if not src.parser:
                # print(f"[{src.name}] no parser")
                continue
            fn = get_scraper(src.parser)
            if not fn:
                print(f"[{src.name}] parser not found: {src.parser}")
                continue

            try:
                items = await asyncio.to_thread(fn)
                saved = await asyncio.to_thread(persist_items, src, items)
                print(f"[{datetime.utcnow():%H:%M:%S}] {src.name}: scraped {len(items)}, new {saved}")
            except Exception as e:
                print(f"[{src.name}] ERROR: {e}")

        await asyncio.sleep(interval_seconds)

async def telegram_channels_loop(interval: int, telethon_client):
    while True:
        sources = await list_active_sources()
        for src in [s for s in sources if s.type == SourceType.TELEGRAM_CHANNEL]:
            username = username_from_url(src.url or src.name)
            try:
                items = await fetch_new_from_channel(telethon_client, username)
                added = await save_items(src, items)
            except Exception:
                pass
        await asyncio.sleep(interval)
