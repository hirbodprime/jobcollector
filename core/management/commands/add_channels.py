# core/management/commands/add_channels.py
from django.core.management.base import BaseCommand
from core.models import Source, SourceType

class Command(BaseCommand):
    help = "Add one or more Telegram channels or websites into the sources table."

    def add_arguments(self, parser):
        parser.add_argument(
            "urls",
            nargs="+",
            help="One or more channel usernames (e.g. @remotejobs) or full URLs.",
        )
        parser.add_argument(
            "--type",
            choices=["channel", "website"],
            default="channel",
            help="Source type (default: channel).",
        )
        parser.add_argument(
            "--category",
            choices=["JOB", "PROJECT", "COMPETITION"],
            default="JOB",
            help="Category for the source (default: JOB).",
        )

    def handle(self, *args, **options):
        stype = SourceType.TELEGRAM_CHANNEL if options["type"] == "channel" else SourceType.WEBSITE
        added = 0
        for url in options["urls"]:
            src, created = Source.objects.get_or_create(
                url=url.strip(),
                defaults={
                    "name": url.strip(),
                    "type": stype,
                    "category": options["category"],
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Added: {src.url}"))
                added += 1
            else:
                self.stdout.write(self.style.WARNING(f"Already exists: {src.url}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Done. {added} new source(s) added."))
