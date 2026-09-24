"""Remotive official public API — no key needed.
https://remotive.com/api/remote-jobs?search=<term>
Confirmed via github.com/remotive-com/remote-jobs-api 2026-09-24.
ToS note: free-tier results are ~24h delayed and require attribution/backlink
to Remotive if republished publicly — fine for a private tracking sheet."""
from src.http import get_json
from src.models import Posting

URL = "https://remotive.com/api/remote-jobs"


def fetch(search: str) -> list[Posting]:
    data = get_json(URL, params={"search": search})
    if not data or "jobs" not in data:
        return []
    out = []
    for job in data["jobs"]:
        out.append(Posting(
            title=job.get("title", ""),
            company=job.get("company_name", ""),
            location=job.get("candidate_required_location", "unknown"),
            url=job.get("url", ""),
            source="Remotive",
            posted_date=job.get("publication_date"),
            description=job.get("description", "") or "",
        ))
    return out
