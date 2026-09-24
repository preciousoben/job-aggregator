"""Shared data model for a normalized job posting, used by every connector."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Posting:
    title: str
    company: str
    location: str
    url: str                       # canonical link — used as the dedupe key
    source: str                    # e.g. "Ashby", "Himalayas", "Greenhouse"
    posted_date: Optional[str]     # ISO 8601 string, or None if unknown
    description: str = ""          # raw text/HTML, used for eligibility scan + scoring
    company_size: Optional[str] = None
    salary: Optional[str] = None

    def age_days(self) -> Optional[float]:
        """Days since posted_date, or None if we don't have a usable date."""
        if not self.posted_date:
            return None
        try:
            posted = str(self.posted_date)
            dt = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt).total_seconds() / 86400
        except (ValueError, TypeError, AttributeError):
            return None

    def dedupe_key(self) -> str:
        return self.url.strip().rstrip("/").lower()

    def to_row(self, score: float, eligible: bool, elig_note: str) -> dict:
        """Flatten to the row shape written into the Google Sheet / CSV."""
        return {
            "date_found": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "posted_date": self.posted_date or "unknown",
            "age_days": round(self.age_days(), 1) if self.age_days() is not None else "unknown",
            "fit_score": score,
            "eligible": "yes" if eligible else "no",
            "eligibility_note": elig_note,
            "company_size": self.company_size or "",
            "source": self.source,
            "url": self.url,
            "status": "new",
        }