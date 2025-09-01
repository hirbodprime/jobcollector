# core/management/commands/scrape_once.py
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Source, SourceType
import importlib
from crawlers.persist import persist_items

class Command(BaseCommand):
    help = "Run one or more website scrapers once and persist results."

    def add_arguments(self, parser):
        parser.add_argument("--name", action="append", help="Source name (can repeat). If omitted, runs all WEBSITE sources with a parser.")
        parser.add_argument("--limit", type=int, default=5, help="Print sample of first N items.")
        parser.add_argument("--dry", action="store_true", help="Don't persist, only print counts/samples.")

    def handle(self, *args, **opts):
        names = opts.get("name") or []
        limit = opts["limit"]
        dry = opts["dry"]

        if names:
            sources = list(Source.objects.filter(name__in=names, type=SourceType.WEBSITE))
            if not sources:
                raise CommandError(f"No sources found for names: {names}")
        else:
            sources = list(Source.objects.filter(type=SourceType.WEBSITE).exclude(parser=""))

        mod = importlib.import_module("crawlers.websites")
        total_saved = 0

        for s in sources:
            fn = getattr(mod, s.parser, None)
            if not fn:
                self.stdout.write(self.style.WARNING(f"SKIP {s.name}: parser '{s.parser}' not found"))
                continue
            self.stdout.write(self.style.NOTICE(f"Running {s.name} -> {s.parser}"))
            try:
                items = fn()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"ERROR in {s.name}: {e}"))
                continue

            self.stdout.write(f"  scraped: {len(items)} items")
            for x in items[:limit]:
                self.stdout.write(f"    - {x.get('title','?')[:80]} | {x.get('link','')[:120]}")

            if dry:
                continue

            try:
                with transaction.atomic():
                    saved = persist_items(s, items)
                total_saved += saved
                self.stdout.write(self.style.SUCCESS(f"  saved new: {saved}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  persist error: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Total new saved: {total_saved}"))
