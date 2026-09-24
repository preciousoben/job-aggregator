"""Company discovery from topstartups.io — filterable by size/stage/industry,
each listing links to the company's real career page. No bulk API, so this
scrapes the filtered listing pages. Run weekly (see .github/workflows/
discover.yml), not on every hourly poll — this list changes slowly.

NOT yet live-tested from this build session (see README "Known limitation")
— the HTML parsing below is a best-effort structure based on what WebFetch
showed on 2026-09-24; topstartups.io's markup may not match exactly.
Confirm and adjust selectors on the first real run.

Output feeds into companies.yaml: for each company name found here, check it
against every Tier-1 ATS URL pattern (see check_platforms below) and append
any slug that resolves.
"""
from bs4 import BeautifulSoup
from src.http import get_text, get_json

LISTING_URL = "https://topstartups.io/"

# topstartups.io filter params observed 2026-09-24 — verify these still work
# before relying on them; the site may use client-side filtering that a
# plain fetch won't see, in which case this needs a headless-browser step
# instead (see README open items).
TARGET_SIZE_BANDS = ["1-10", "11-50"]


def discover_company_names(size_bands=None) -> list[str]:
    size_bands = size_bands or TARGET_SIZE_BANDS
    names = []
    for band in size_bands:
        html = get_text(LISTING_URL, )
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        # placeholder selector — topstartups.io's actual card markup needs
        # confirming on a real run; look for company name elements within
        # listing cards.
        for card in soup.select("[class*=company-card], [class*=startup-card]"):
            name_el = card.select_one("[class*=name], h3, h2")
            if name_el:
                names.append(name_el.get_text(strip=True))
    return sorted(set(names))


# Tier-1 ATS platforms this discovery step checks each company name/slug
# against. Slugs are usually a lowercased, hyphenated version of the company
# name, but not always — this is a best-effort guess, not a guarantee.
def slugify(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def check_platforms(slug: str) -> dict:
    """Returns {platform: bool} for whether a board exists at that slug on
    each Tier-1 ATS. Cheap — one GET per platform, 404s are expected and
    fine (see src/http.get_json, which treats 404 as 'not found', not a
    warning)."""
    from src.connectors import ashby, workable, greenhouse

    return {
        "ashby": bool(get_json(ashby.BASE.format(slug=slug))),
        "workable": bool(get_json(workable.BASE.format(slug=slug))),
        "greenhouse": bool(get_json(greenhouse.BASE.format(slug=slug))),
        # lever/smartrecruiters/recruitee: add once their connectors are
        # live-verified against a real company (see README open items)
    }
