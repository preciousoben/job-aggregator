"""SmartRecruiters posting API — https://api.smartrecruiters.com/v1/companies/<slug>/postings
No API key needed. Documented (developers.smartrecruiters.com/docs/posting-api)
but NOT yet live-tested against a real company as of 2026-09-24 — verify
against a known slug before trusting this in production."""
from src.http import get_json
from src.models import Posting

BASE = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"


def fetch(slug: str) -> list[Posting]:
    data = get_json(BASE.format(slug=slug))
    if not data or "content" not in data:
        return []
    out = []
    for job in data["content"]:
        loc = job.get("location", {}) or {}
        location = ", ".join([p for p in [loc.get("city"), loc.get("country")] if p]) or "unknown"
        out.append(Posting(
            title=job.get("name", ""),
            company=(job.get("company") or {}).get("name") or slug,
            location=location,
            url=job.get("ref", ""),
            source="SmartRecruiters",
            posted_date=job.get("releasedDate") or job.get("createdOn"),
            description="",  # full description needs a second call per posting; add if we start using this source
        ))
    return out
