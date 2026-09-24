"""Entry point for the weekly discovery workflow: find new small-company
names (currently just topstartups.io — add ycombinator.py / seedtable.py
here following the same pattern once built), check each against every
Tier-1 ATS platform, and append any that resolve to config/companies.yaml.

NOT yet live-tested end to end (depends on src/discovery/topstartups.py,
which itself isn't live-tested — see that file's docstring). Run this
manually via workflow_dispatch and check the diff before trusting the
scheduled version.
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.discovery import topstartups

COMPANIES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config", "companies.yaml",
)


def run():
    with open(COMPANIES_PATH) as f:
        companies = yaml.safe_load(f)

    names = topstartups.discover_company_names()
    print(f"topstartups.io: {len(names)} candidate company names found")

    added = 0
    for name in names:
        slug = topstartups.slugify(name)
        results = topstartups.check_platforms(slug)
        for platform, found in results.items():
            if found and slug not in companies.get(platform, []):
                companies.setdefault(platform, []).append(slug)
                added += 1
                print(f"  + {platform}/{slug} ({name})")

    if added:
        with open(COMPANIES_PATH, "w") as f:
            yaml.safe_dump(companies, f, default_flow_style=False, sort_keys=False)
        print(f"\n{added} new company boards added to companies.yaml")
    else:
        print("\nno new company boards found this run")


if __name__ == "__main__":
    run()
