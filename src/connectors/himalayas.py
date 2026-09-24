"""Himalayas official public API — no key needed.
https://himalayas.app/jobs/api/search?q=<term>&page=<n>
Confirmed via docs 2026-09-24. NOTE: despite the docs saying pubDate is
always an ISO 8601 string, real responses have been observed returning a
raw Unix epoch integer instead (confirmed 2026-09-24 from live sheet data)
— _normalize_date handles both."""
from datetime import datetime, timezone
from src.http import get_json
from src.models import Posting

SEARCH_URL = "https://himalayas.app/jobs/api/search"


def _normalize_date(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            return None
    return value


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
                posted_date=_normalize_date(job.get("pubDate")),
                description=job.get("excerpt", "") or "",
            ))
        if len(jobs) < 20:
            break
    return out