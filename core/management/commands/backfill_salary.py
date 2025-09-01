from django.core.management.base import BaseCommand
from core.models import Post
from crawlers.base import parse_salary

class Command(BaseCommand):
    help = "Parse salary from existing posts' title/description/extras and fill fields if empty."

    def handle(self, *args, **opts):
        updated = 0
        for p in Post.objects.all().iterator():
            if p.salary_min is not None or p.salary_max is not None:
                continue
            blob = " ".join([
                p.title or "",
                p.description or "",
                str(p.extras or ""),
            ])
            mn, mx, cur, per = parse_salary(blob)
            if mn is not None or mx is not None or cur or per:
                p.salary_min = mn
                p.salary_max = mx
                p.currency = (cur or p.currency or "").upper()
                p.period = per or p.period
                p.save(update_fields=["salary_min","salary_max","currency","period"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} posts with parsed salary."))
