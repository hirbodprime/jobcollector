# crawlers/persist.py
from __future__ import annotations

from typing import Iterable, Dict, Any
from django.db import transaction
from django.utils.text import Truncator
from core.models import Post, Source

# Map incoming scraper keys -> Post model field names
# (only applied if those fields actually exist on your Post model)
KEY_MAP = {
    "title": "title",
    "description": "description",
    "link": "link",
    "category": "category",
    "company": "company",
    "location": "location",
    "salary_min": "salary_min",
    "salary_max": "salary_max",
    "currency": "currency",
    "period": "period",
    "tags": "tags",          # ArrayField or CharField (we'll coerce below)
    "extras": "extras",      # JSONField (optional)
}

def _model_fields(model) -> set[str]:
    return {f.name for f in model._meta.get_fields()}

POST_FIELDS = _model_fields(Post)

def _coerce(value: Any, field: str) -> Any:
    """Light coercion so we don't crash on schema differences."""
    if field == "tags":
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value.strip():
            # comma/space split best-effort
            if "," in value:
                return [t.strip() for t in value.split(",") if t.strip()]
            return value.split()
        return []
    return value

@transaction.atomic
def persist_items(source: Source, items: Iterable[Dict[str, Any]]) -> int:
    """
    Save a batch of scraped items for a given Source.
    - De-dupe by (source, link) primarily; if link missing, skip.
    - Update existing row if found; otherwise create new.
    - Leaves posted_to_channel as default (False) so bot can pick it up.
    Returns how many **new** rows were created.
    """
    created_count = 0

    for it in items:
        link = (it.get("link") or "").strip()
        title = (it.get("title") or "").strip()
        if not link or not title:
            continue  # must have both

        # Truncate long fields safely
        title = Truncator(title).chars(255)
        description = (it.get("description") or "")
        if isinstance(description, str):
            # keep DB friendly (adjust if your model allows more)
            description = description[:8000]

        # Build defaults only with fields that exist on Post
        defaults: Dict[str, Any] = {"title": title, "description": description}
        # if category missing from item, fallback to source.category
        defaults["category"] = it.get("category") or getattr(source, "category", None)

        for in_key, model_key in KEY_MAP.items():
            if model_key in ("title", "description", "category", "link"):
                # already handled or key field
                continue
            if model_key not in POST_FIELDS:
                continue
            if in_key in it:
                defaults[model_key] = _coerce(it[in_key], model_key)

        # Always associate the source
        defaults["source"] = source

        # Upsert by (source, link)
        obj, created = Post.objects.update_or_create(
            source=source,
            link=link,
            defaults=defaults,
        )
        if created:
            created_count += 1

    return created_count
