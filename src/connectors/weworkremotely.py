"""We Work Remotely RSS feeds — no key needed.
Their category taxonomy leans engineering, so instead of relying on a
"data" category (which may not exist/be complete) we pull the broad
programming + a couple of likely categories and filter by title keyword."""
import feedparser
from src.models import Posting

FEEDS = [
    "https://weworkremotely.com/categories/remote-data-jobs.rss",
    "https://weworkremotely.com/categories/remote-analytics-jobs.rss",
    "https://weworkremotely.com/remote-jobs.rss",  # all-categories firehose, filtered below
]
_KEYWORDS = ("data analyst", "data engineer", "analytics engineer", "bi analyst", "business intelligence")


def fetch() -> list[Posting]:
    out = []
    seen_links = set()
    for feed_url in FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            title = entry.get("title", "")
            if not any(k in title.lower() for k in _KEYWORDS):
                continue
            link = entry.get("link", "")
            if link in seen_links:
                continue
            seen_links.add(link)
            # WWR titles are usually "Company: Job Title"
            company, _, job_title = title.partition(":")
            out.append(Posting(
                title=job_title.strip() or title,
                company=company.strip(),
                location=entry.get("region", "unknown"),
                url=link,
                source="We Work Remotely",
                posted_date=_to_iso(entry.get("published")),
                description=entry.get("summary", "") or "",
            ))
    return out


def _to_iso(rfc822_str):
    if not rfc822_str:
        return None
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(rfc822_str).isoformat()
    except (ValueError, TypeError):
        return None
