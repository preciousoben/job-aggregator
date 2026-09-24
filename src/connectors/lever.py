"""Lever postings API — https://api.lever.co/v0/postings/<slug>?mode=json
No API key needed. Documented (github.com/lever/postings-api) but NOT yet
live-tested against a real Lever-hosted company as of 2026-09-24 — verify
against a known slug before trusting this in production."""
from src.http import get_json
from src.models import Posting

BASE = "https://api.lever.co/v0/postings/{slug}"


def fetch(slug: str) -> list[Posting]:
    data = get_json(BASE.format(slug=slug), params={"mode": "json"})
    if not data or not isinstance(data, list):
        return []
    out = []
    for job in data:
        categories = job.get("categories", {}) or {}
        out.append(Posting(
            title=job.get("text", ""),
            company=slug,
            location=categories.get("location", "unknown"),
            url=job.get("hostedUrl", ""),
            source="Lever",
            posted_date=_epoch_to_iso(job.get("createdAt")),
            description=job.get("descriptionPlain") or job.get("description", "") or "",
        ))
    return out


def _epoch_to_iso(ms):
    if not ms:
        return None
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None
