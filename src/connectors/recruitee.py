"""Recruitee public offers API — https://<slug>.recruitee.com/api/offers/
No API key needed. Common ATS for EU-based startups. Not yet live-tested
as of 2026-09-24 — verify against a known slug before trusting in production."""
from src.http import get_json
from src.models import Posting

BASE = "https://{slug}.recruitee.com/api/offers/"


def fetch(slug: str) -> list[Posting]:
    data = get_json(BASE.format(slug=slug))
    if not data or "offers" not in data:
        return []
    out = []
    for job in data["offers"]:
        out.append(Posting(
            title=job.get("title", ""),
            company=slug,
            location=job.get("location", "unknown"),
            url=job.get("careers_url", ""),
            source="Recruitee",
            posted_date=job.get("created_at") or job.get("published_at"),
            description=job.get("description", "") or "",
        ))
    return out
