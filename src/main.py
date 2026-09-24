"""Orchestrator: fetch every source, dedupe, filter freshness + eligibility,
score, write new rows. Runs on a schedule via GitHub Actions (see
.github/workflows/poll.yml) — no LLM agent in this loop, just code.
"""
import os
import sys
import time
import traceback
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.connectors import (
    ashby, workable, greenhouse, lever, smartrecruiters, recruitee,
    himalayas, remotive, remoteok, weworkremotely,
)
from src.models import Posting
from src.eligibility import check as check_eligibility
from src.scoring import score as score_posting
from src.store import get_store

MAX_AGE_DAYS = 7.0
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")


def _load_yaml(name):
    with open(os.path.join(CONFIG_DIR, name)) as f:
        return yaml.safe_load(f)


def _safe(name, fn, *args, **kwargs):
    """Never let one bad source take the whole run down."""
    try:
        result = fn(*args, **kwargs)
        print(f"  {name}: {len(result)} postings")
        return result
    except Exception:
        print(f"  [error] {name} failed:")
        traceback.print_exc()
        return []


def fetch_all() -> list[Posting]:
    companies = _load_yaml("companies.yaml")
    terms = _load_yaml("search_terms.yaml")["titles"]

    postings: list[Posting] = []

    print("Tier 1 — ATS platforms:")
    for slug in companies.get("ashby", []):
        postings += _safe(f"Ashby/{slug}", ashby.fetch, slug)
        time.sleep(0.3)
    for slug in companies.get("workable", []):
        postings += _safe(f"Workable/{slug}", workable.fetch, slug)
        time.sleep(0.3)
    for slug in companies.get("greenhouse", []):
        postings += _safe(f"Greenhouse/{slug}", greenhouse.fetch, slug)
        time.sleep(0.3)
    for slug in companies.get("lever", []):
        postings += _safe(f"Lever/{slug}", lever.fetch, slug)
        time.sleep(0.3)
    for slug in companies.get("smartrecruiters", []):
        postings += _safe(f"SmartRecruiters/{slug}", smartrecruiters.fetch, slug)
        time.sleep(0.3)
    for slug in companies.get("recruitee", []):
        postings += _safe(f"Recruitee/{slug}", recruitee.fetch, slug)
        time.sleep(0.3)

    print("Tier 2 — aggregator APIs:")
    for term in terms:
        postings += _safe(f"Himalayas/{term}", himalayas.fetch, term)
        postings += _safe(f"Remotive/{term}", remotive.fetch, term)
    postings += _safe("RemoteOK", remoteok.fetch)
    postings += _safe("We Work Remotely", weworkremotely.fetch)

    title_keywords = ("data analyst", "data engineer", "analytics engineer", "bi analyst", "business intelligence")
    postings = [p for p in postings if p.title and p.url]
    filtered = [p for p in postings if any(k in p.title.lower() for k in title_keywords)]
    print(f"\n{len(postings)} postings with a title/url -> {len(filtered)} after filtering to target roles")
    return filtered


def _load_resume_text() -> str:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "resume.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


def run():
    print(f"=== Job aggregator run — {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} ===")
    store = get_store()
    existing_urls = store.get_existing_urls()
    print(f"{len(existing_urls)} postings already in the sheet/CSV")

    all_postings = fetch_all()
    print(f"\n{len(all_postings)} raw postings fetched across all sources")

    resume_text = _load_resume_text()
    new_rows = []
    skipped_dupe = skipped_stale = skipped_ineligible = 0

    for p in all_postings:
        if p.dedupe_key() in existing_urls:
            skipped_dupe += 1
            continue
        age = p.age_days()
        if age is not None and age > MAX_AGE_DAYS:
            skipped_stale += 1
            continue
        eligible, note = check_eligibility(p.description)
        if not eligible:
            skipped_ineligible += 1
            continue
        fit = score_posting(p.title, p.description, resume_text)
        new_rows.append(p.to_row(fit, eligible, note))
        existing_urls.add(p.dedupe_key())  # guard against dupes within this same run

    store.append_rows(new_rows)
    archived = store.archive_stale(MAX_AGE_DAYS)

    print(f"\n{len(new_rows)} new postings written")
    print(f"skipped: {skipped_dupe} duplicate, {skipped_stale} stale (>{MAX_AGE_DAYS}d), {skipped_ineligible} hard-blocked")
    print(f"{archived} previously-new rows archived for aging past {MAX_AGE_DAYS}d")
    return new_rows


if __name__ == "__main__":
    run()