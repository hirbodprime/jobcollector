from django.core.management.base import BaseCommand
from core.models import Source, Category, SourceType

WEBSITE_SOURCES = [
    # Jobs
    ("RemoteOK", "https://remoteok.com/", "scrape_remoteok", Category.JOB),
    ("Remotive", "https://remotive.com/remote-jobs", "scrape_remotive", Category.JOB),
    ("We Work Remotely", "https://weworkremotely.com/remote-jobs", "scrape_wwr", Category.JOB),
    ("Remote.co", "https://remote.co/remote-jobs/", "scrape_remote_co", Category.JOB),
    ("JustRemote", "https://justremote.co/remote-jobs", "scrape_justremote", Category.JOB),
    ("Wellfound (AngelList)", "https://wellfound.com/jobs", "scrape_wellfound", Category.JOB),

    # Projects/Competitions
    ("Devpost", "https://devpost.com/hackathons", "scrape_devpost", Category.PROJECT),
    # Placeholders to extend (Kaggle/Gitcoin can require JS/API work)
    ("Kaggle", "https://www.kaggle.com/competitions", "scrape_kaggle_placeholder", Category.COMPETITION),
    ("Gitcoin", "https://www.gitcoin.co/", "scrape_gitcoin_placeholder", Category.PROJECT),
]

TELEGRAM_CHANNELS = [
    ("@remotejobs", "https://t.me/remotejobs", Category.JOB),
    ("@weworkremotely", "https://t.me/weworkremotely", Category.JOB),
    ("@remoteworkers", "https://t.me/remoteworkers", Category.JOB),
]

class Command(BaseCommand):
    help = "Seed default sources"

    def handle(self, *args, **opts):
        created = 0
        for name, url, parser, cat in WEBSITE_SOURCES:
            Source.objects.get_or_create(
                name=name,
                defaults=dict(url=url, parser=parser, type=SourceType.WEBSITE, category=cat, is_active=True)
            )
            created += 1
        for name, url, cat in TELEGRAM_CHANNELS:
            Source.objects.get_or_create(
                name=name,
                defaults=dict(url=url, parser="", type=SourceType.TELEGRAM_CHANNEL, category=cat, is_active=True)
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded/ensured {created} sources."))
