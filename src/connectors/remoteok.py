"""RemoteOK public API — no key needed. https://remoteok.com/api
Confirmed working 2026-09-24. ToS note: requires a backlink to RemoteOK
if republished publicly — fine for a private tracking sheet."""
from src.http import get_json
from src.models import Posting

URL = "https://remoteok.com/api"
_KEYWORDS = ("data analyst", "data engineer", "analytics engineer", "bi analyst", "business intelligence")


def fetch() -> list[Posting]:
    data = get_json(URL)
    if not data or not isinstance(data, list):
        return []
    out = []
    for job in data:
        if not isinstance(job, dict) or "position" not in job:
            continue  # first element is a legal/metadata blob, not a job
        title = job.get("position", "")
        if not any(k in title.lower() for k in _KEYWORDS):
            continue
        out.append(Posting(
            title=title,
            company=job.get("company", ""),
            location=job.get("location", "unknown"),
            url=job.get("url") or job.get("apply_url", ""),
            source="RemoteOK",
            posted_date=job.get("date"),
            description=job.get("description", "") or "",
        ))
    return out
