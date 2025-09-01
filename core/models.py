# core/models.py
from django.db import models

class SourceType(models.TextChoices):
    WEBSITE = "WEBSITE", "Website"
    TELEGRAM_CHANNEL = "TELEGRAM_CHANNEL", "Telegram Channel"

class Category(models.TextChoices):
    JOB = "JOB", "Job"
    PROJECT = "PROJECT", "Project"
    COMPETITION = "COMPETITION", "Competition"

class Source(models.Model):
    name = models.CharField(max_length=200, unique=True)
    url = models.URLField(max_length=500, blank=True)
    type = models.CharField(max_length=20, choices=SourceType.choices, db_index=True)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    parser = models.CharField(max_length=100, blank=True, help_text="websites.py function name")
    is_active = models.BooleanField(default=True)
    last_crawled = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} [{self.type}/{self.category}]"

class Post(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    link = models.URLField(max_length=1000)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)

    # 🔥 New rich fields
    company = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=16, blank=True)  # e.g., USD, EUR
    period = models.CharField(max_length=16, blank=True)    # e.g., YEARLY, MONTHLY, HOURLY, PROJECT
    tags = models.JSONField(default=list, blank=True)       # list of strings
    extras = models.JSONField(default=dict, blank=True)     # raw source payload (keep everything)
    raw_text = models.TextField(blank=True)                 # original text snapshot, if available

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    posted_to_channel = models.BooleanField(default=False, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "link"], name="uniq_source_link")
        ]
        indexes = [
            models.Index(fields=["posted_to_channel", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.source.name})"
