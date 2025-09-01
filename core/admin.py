# core/admin.py
from django.contrib import admin
from .models import Source, Post

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "category", "is_active", "last_crawled", "parser")
    list_filter = ("type", "category", "is_active")
    search_fields = ("name", "url", "parser")

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "location", "currency", "salary_min", "salary_max",
                    "source", "category", "posted_to_channel", "created_at")
    list_filter = ("category", "posted_to_channel", "source", "currency", "period")
    search_fields = ("title", "description", "link", "company", "location", "raw_text")
    readonly_fields = ("created_at",)
