"""Himalayas official public API — no key needed.
https://himalayas.app/jobs/api/search?q=<term>&page=<n>
Confirmed via docs 2026-09-24."""
from src.http import get_json
from src.models import Posting

SEARCH_URL = "https://himalayas.app/jobs/api/search"


def fetch(query: str, max_pages: int = 3) -> list[Posting]:
    out = []
    for page in range(1, max_pages + 1):
        data = get_json(SEARCH_URL, params={"q": query, "page": page})
        if not data:
            break
        jobs = data.get("jobs") or data.get("data") or []
        if not jobs:
            break
        for job in jobs:
            loc_restrictions = job.get("locationRestrictions") or []
            location = ", ".join(loc_restrictions) if loc_restrictions else "Worldwide"
            out.append(Posting(
                title=job.get("title", ""),
                company=job.get("companyName", ""),
                location=location,
                url=job.get("applicationLink", ""),
                source="Himalayas",
                posted_date=job.get("pubDate"),
                description=job.get("excerpt", "") or "",
            ))
        if len(jobs) < 20:  # last page (max page size is 20 per the docs)
            break
    return out
