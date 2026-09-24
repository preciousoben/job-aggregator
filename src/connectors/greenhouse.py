"""Greenhouse job board API — https://boards-api.greenhouse.io/v1/boards/<slug>/jobs
No API key needed. Confirmed working 2026-09-24 (tested against Stripe)."""
from src.http import get_json
from src.models import Posting

BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def fetch(slug: str) -> list[Posting]:
    # ?content=true pulls full descriptions in one call instead of one request per job
    data = get_json(BASE.format(slug=slug), params={"content": "true"})
    if not data or "jobs" not in data:
        return []
    out = []
    for job in data["jobs"]:
        out.append(Posting(
            title=job.get("title", ""),
            company=job.get("company_name") or slug,
            location=(job.get("location") or {}).get("name", "unknown"),
            url=job.get("absolute_url", ""),
            source="Greenhouse",
            posted_date=job.get("first_published") or job.get("updated_at"),
            description=job.get("content", "") or "",
        ))
    return out
