from django.core.management.base import BaseCommand, CommandParser
from core.models import Source, SourceType, Category

class Command(BaseCommand):
    help = "Add Telegram channel sources. Usage: python manage.py add_channels https://t.me/xxx @yyy ... [--category JOB|PROJECT]"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("channels", nargs="+", help="Channel URLs or @usernames")
        parser.add_argument("--category", default="JOB", choices=["JOB", "PROJECT", "COMPETITION"])

    def handle(self, *args, **opts):
        cat = opts["category"]
        created = 0
        for raw in opts["channels"]:
            raw = raw.strip()
            url = raw if raw.startswith("http") else f"https://t.me/{raw.lstrip('@')}"
            name = "@" + url.split("/")[-1]
            obj, was_created = Source.objects.update_or_create(
                name=name,
                defaults=dict(url=url, type=SourceType.TELEGRAM_CHANNEL, category=cat, parser="", is_active=True),
            )
            if was_created:
                created += 1
            self.stdout.write(self.style.SUCCESS(f"Ensured: {name} -> {url} [{cat}]"))
        self.stdout.write(self.style.SUCCESS(f"Done. New sources created: {created}"))
