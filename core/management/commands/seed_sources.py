# core/management/commands/seed_sources.py
from django.core.management.base import BaseCommand
from core.models import Source, SourceType, Category

SOURCES = [
    # Existing
    {"name": "RemoteOK", "url": "https://remoteok.com", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remoteok"},
    {"name": "Remotive", "url": "https://remotive.com", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remotive"},
    {"name": "We Work Remotely", "url": "https://weworkremotely.com", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_wwr"},
    {"name": "Remote.co", "url": "https://remote.co", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remote_co"},
    {"name": "JustRemote", "url": "https://justremote.co", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_justremote"},
    {"name": "Wellfound (AngelList)", "url": "https://wellfound.com", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_wellfound"},

    # NEW job sources
    {"name": "Working Nomads", "url": "https://www.workingnomads.com/jobs", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_working_nomads"},
    {"name": "NoDesk", "url": "https://nodesk.co/remote-jobs/", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_nodesk"},
    {"name": "Jobspresso", "url": "https://jobspresso.co/remote-work/", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_jobspresso"},
    {"name": "Arc.dev", "url": "https://arc.dev/remote-jobs", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_arc"},

    # Existing projects
    {"name": "Devpost", "url": "https://devpost.com", "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_devpost"},

    # NEW project/hackathon sources
    {"name": "HackerEarth Challenges", "url": "https://www.hackerearth.com/challenges/", "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_hackerearth"},
    {"name": "Devfolio Hackathons", "url": "https://devfolio.co/hackathons", "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_devfolio"},

    # Telegram channels you already had (examples)
    {"name": "@remotejobs", "url": "https://t.me/remotejobs", "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@weworkremotely", "url": "https://t.me/weworkremotely", "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@remoteworkers", "url": "https://t.me/remoteworkers", "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
]

class Command(BaseCommand):
    help = "Seed default sources"

    def handle(self, *args, **options):
        created = 0
        for s in SOURCES:
            obj, was_created = Source.objects.update_or_create(
                name=s["name"],
                defaults={
                    "url": s["url"],
                    "type": s["type"],
                    "category": s["category"],
                    "parser": s.get("parser", ""),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded/ensured {len(SOURCES)} sources (new: {created})."))
