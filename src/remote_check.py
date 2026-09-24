"""Positive remote-signal check.

Added 2026-09-24 after a GoCardless "Data Engineer" posting (Riga, Latvia —
silent on remote vs. onsite, no explicit onsite blocker phrase like "on-site
role" or "hybrid, 3 days/week") slipped through the hard-blocker-only
eligibility rule in eligibility.py and turned out to actually be an
in-person role. Precious asked to only include postings with an actual
positive signal of being remote from here on — "no explicit onsite
statement" is no longer good enough on its own to pass a posting through.

This is deliberately a SEPARATE check from eligibility.py, not a change to
it — eligibility.py's hard-blocker-only rule (only exclude for explicit
no-sponsorship or explicit onsite/hybrid language) is still the right rule
for THAT question (visa/work-authorization and explicit onsite mandates).
This is a different question: does the posting affirmatively say it's
remote at all.
"""
import re

# Sources where being remote is inherent to the board itself — every
# posting on these is remote by definition (that's the board's whole
# premise), so no text check is needed or meaningful.
_REMOTE_NATIVE_SOURCES = {"RemoteOK", "Remotive", "We Work Remotely", "Himalayas"}

_REMOTE_SIGNAL_RE = re.compile(
    r"\bremote\b|\bwork[\s-]from[\s-]home\b|\bwfh\b|\bdistributed team\b|"
    r"\bworldwide\b|\banywhere\b|\bfully remote\b|\bremote-first\b|\bremote-friendly\b",
    re.IGNORECASE,
)


def is_remote(posting) -> bool:
    """True if this posting affirmatively signals remote work, either
    because its source board is remote-only by nature, or because its
    location or description text actually says so. False (i.e. "not
    confirmed remote") is now the default for silence, not True."""
    if posting.source in _REMOTE_NATIVE_SOURCES:
        return True
    if _REMOTE_SIGNAL_RE.search(posting.location or ""):
        return True
    if _REMOTE_SIGNAL_RE.search(posting.description or ""):
        return True
    return False