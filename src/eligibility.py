"""Rule-based hard-blocker scan, mirrors the manual eligibility rule used in
the earlier Claude-agent pulls: only exclude for an EXPLICIT statement that
the candidate must already hold local work authorization with no sponsorship,
or a genuine on-site/hybrid requirement. Everything else — restrictive-
sounding or ambiguous postings, country-restricted "eligible locations" lists,
timezone requirements — passes through and gets flagged in the note instead
of excluded, so Precious keeps full information and makes the final call
herself on the gray-area ones.
"""
import re

# Only these two categories are grounds for exclusion. Kept narrow and
# conservative on purpose — false exclusions are worse than false includes,
# because an excluded posting never reaches the sheet at all.
#
# Real postings phrase "must hold local work authorization" and "no
# sponsorship" in separate sentences far more often than in one neat clause
# (see the Splice/Integra/WorkMoney/Dragos examples from the manual pulls),
# so this checks for co-occurrence of an AUTHORIZATION signal and a
# NO-SPONSORSHIP signal anywhere in the text, rather than one brittle
# single-sentence pattern.
_AUTHORIZATION_PATTERNS = [
    r"must (?:already )?(?:be authorized|hold authorization|have (?:valid )?(?:work )?authorization)",
    r"authorized to work in (?:the )?(?:us|u\.s\.|united states|uk|u\.k\.)",
    r"\b(?:us|u\.s\.|united states) (?:citizen|permanent resident)\b",
    r"\bmust (?:already )?reside in\b",
]
_NO_SPONSORSHIP_PATTERNS = [
    r"no (?:visa )?sponsorship",
    r"(?:without|does not offer|do not offer|will not sponsor|does not sponsor|do not sponsor|not eligible for) (?:visa )?sponsorship",
    r"sponsorship (?:is )?(?:not )?(?:available|offered|provided)\b.{0,15}\bnot\b",
]
_ONSITE_PATTERNS = [
    r"\b(?:on-?site|in-?office)\s+(?:role|position|requirement|only|required)\b",
    r"\b\d+\s*days?\s*(?:a|per)\s*week\s+in\s+(?:the\s+)?office\b",
    r"\bmust (?:work|be) on-?site\b",
    r"\bhybrid\b[^.]{0,40}\b\d+\s*days?\b[^.]{0,40}\boffice\b",
    r"\brelocation (?:to|required)\b[^.]{0,40}\bmandatory\b",
]

_AUTHORIZATION_RE = re.compile("|".join(_AUTHORIZATION_PATTERNS), re.IGNORECASE)
_NO_SPONSORSHIP_RE = re.compile("|".join(_NO_SPONSORSHIP_PATTERNS), re.IGNORECASE)
_ONSITE_RE = re.compile("|".join(_ONSITE_PATTERNS), re.IGNORECASE)

# Softer signals worth surfacing in the note without excluding — matches the
# pattern we used manually (SwissBorg, Hire Hangar, Crux, Homeward).
_SOFT_FLAG_PATTERNS = [
    r"\bLatAM[- ]based\b",
    r"\beligible (?:countries|locations)\b",
    r"\bmust reside in\b",
    r"\bresidency requirement\b",
]
_SOFT_FLAG_RE = re.compile("|".join(_SOFT_FLAG_PATTERNS), re.IGNORECASE)


def check(description: str) -> tuple[bool, str]:
    """Returns (eligible, note). eligible=False only for the two explicit
    hard-blocker categories; everything else is eligible=True with a note
    flagging anything ambiguous so Precious can judge it herself."""
    text = description or ""
    if _AUTHORIZATION_RE.search(text) and _NO_SPONSORSHIP_RE.search(text):
        return False, "excluded: explicit local work-authorization / no-sponsorship statement"
    if _ONSITE_RE.search(text):
        return False, "excluded: explicit on-site/hybrid requirement"
    if _SOFT_FLAG_RE.search(text):
        return True, "included but flagged: posting has a geographic/residency restriction that doesn't rise to the two hard-blocker types — check before applying"
    return True, "no hard blocker found"
