"""Ashby posting API — https://api.ashbyhq.com/posting-api/job-board/<slug>
No API key needed. Confirmed working 2026-09-24."""
from src.http import get_json
from src.models import Posting

BASE = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def fetch(slug: str) -> list[Posting]:
    data = get_json(BASE.format(slug=slug))
    if not data or "jobs" not in data:
        return []
    out = []
    for job in data["jobs"]:
        loc = job.get("location") or job.get("address", {}).get("postalAddress", {}).get("addressLocality") or "unknown"
        out.append(Posting(
            title=job.get("title", ""),
            company=data.get("organizationName") or slug,
            location=str(loc),
            url=job.get("jobUrl") or job.get("applyUrl", ""),
            source="Ashby",
            posted_date=job.get("publishedAt"),
            description=job.get("descriptionPlain") or job.get("description", "") or "",
        ))
    return out
