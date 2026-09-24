"""Workable widget API — https://apply.workable.com/api/v1/widget/accounts/<slug>
No API key needed. Confirmed working 2026-09-24."""
from src.http import get_json
from src.models import Posting

BASE = "https://apply.workable.com/api/v1/widget/accounts/{slug}"


def fetch(slug: str) -> list[Posting]:
    data = get_json(BASE.format(slug=slug))
    if not data or "jobs" not in data:
        return []
    out = []
    for job in data["jobs"]:
        city = job.get("city") or ""
        country = job.get("country") or ""
        location = ", ".join([p for p in [city, country] if p]) or ("Remote" if job.get("remote") else "unknown")
        out.append(Posting(
            title=job.get("title", ""),
            company=data.get("name") or slug,
            location=location,
            url=job.get("url") or job.get("shortlink", ""),
            source="Workable",
            posted_date=job.get("published_on") or job.get("created_at"),
            description=job.get("description", "") or "",
        ))
    return out
