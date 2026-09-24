"""Fixture-based tests. This sandbox's network policy blocks raw outbound
calls to arbitrary external hosts from code (only PyPI/npm/etc. are
allowlisted) — confirmed 2026-09-24, see README "Known limitation of this
build session". So these tests monkeypatch src.http to serve saved fixture
JSON (captured from real API shapes confirmed via WebFetch earlier the same
day) instead of hitting the network, which proves the *parsing* logic is
correct. The connectors themselves still need a live run (e.g. the first
real GitHub Actions run) to confirm the live endpoints behave exactly like
the fixtures — see README "First real run checklist".
"""
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _load(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


class TestATSConnectors(unittest.TestCase):
    def test_ashby(self):
        from src.connectors import ashby
        with patch("src.connectors.ashby.get_json", return_value=_load("ashby.json")):
            postings = ashby.fetch("zefir")
        self.assertEqual(len(postings), 1)
        p = postings[0]
        self.assertEqual(p.title, "Founding Analytics Engineer")
        self.assertEqual(p.company, "Zefir")
        self.assertEqual(p.source, "Ashby")
        self.assertIn("2026-08-07", p.posted_date)
        self.assertGreater(p.age_days(), 40)  # sanity: this fixture is deliberately stale

    def test_workable(self):
        from src.connectors import workable
        with patch("src.connectors.workable.get_json", return_value=_load("workable.json")):
            postings = workable.fetch("ruby-labs")
        self.assertEqual(len(postings), 1)
        p = postings[0]
        self.assertEqual(p.title, "Data Analytics Engineer")
        self.assertEqual(p.company, "Ruby Labs")
        self.assertEqual(p.location, "Remote")

    def test_greenhouse(self):
        from src.connectors import greenhouse
        with patch("src.connectors.greenhouse.get_json", return_value=_load("greenhouse.json")):
            postings = greenhouse.fetch("splice")
        self.assertEqual(len(postings), 1)
        p = postings[0]
        self.assertEqual(p.title, "Staff Data Analyst")
        self.assertEqual(p.location, "Remote US")

    def test_himalayas(self):
        from src.connectors import himalayas
        # only one page of fixture data — fetch() should stop after the
        # short page instead of looping forever
        with patch("src.connectors.himalayas.get_json", return_value=_load("himalayas.json")):
            postings = himalayas.fetch("data analyst")
        self.assertEqual(len(postings), 1)
        self.assertEqual(postings[0].company, "SwissBorg")

    def test_remotive(self):
        from src.connectors import remotive
        with patch("src.connectors.remotive.get_json", return_value=_load("remotive.json")):
            postings = remotive.fetch("analytics engineer")
        self.assertEqual(len(postings), 1)
        self.assertEqual(postings[0].company, "Homeward")

    def test_remoteok_filters_non_data_roles(self):
        from src.connectors import remoteok
        with patch("src.connectors.remoteok.get_json", return_value=_load("remoteok.json")):
            postings = remoteok.fetch()
        # fixture has 2 real jobs + 1 legal blob; only the data-engineer one should survive the title filter
        self.assertEqual(len(postings), 1)
        self.assertEqual(postings[0].company, "Alpaca")

    def test_weworkremotely_rss(self):
        from src.connectors import weworkremotely
        import feedparser
        fixture_path = os.path.join(FIXTURES, "weworkremotely.rss")
        with open(fixture_path) as f:
            rss_text = f.read()
        parsed_once = feedparser.parse(rss_text)
        with patch("src.connectors.weworkremotely.feedparser.parse", return_value=parsed_once):
            postings = weworkremotely.fetch()
        # 3 identical feed URLs in FEEDS all return the same parsed fixture;
        # dedupe-by-link inside fetch() should collapse them to 1 unique posting
        self.assertEqual(len(postings), 1)
        self.assertEqual(postings[0].company, "Welltech")
        self.assertEqual(postings[0].title, "Senior Data Engineer (Redshift)")


class TestEligibility(unittest.TestCase):
    def test_excludes_explicit_no_sponsorship(self):
        from src.eligibility import check
        eligible, note = check("Must be authorized to work in the US. No sponsorship offered.")
        self.assertFalse(eligible)

    def test_excludes_explicit_onsite(self):
        from src.eligibility import check
        eligible, note = check("This is an on-site role, 4 days a week in the office required.")
        self.assertFalse(eligible)

    def test_includes_ambiguous_timezone_requirement(self):
        from src.eligibility import check
        eligible, note = check("Must overlap with CET business hours. Fully remote.")
        self.assertTrue(eligible)

    def test_includes_but_flags_country_restriction(self):
        from src.eligibility import check
        eligible, note = check("Eligible countries: France, Germany, Spain. LatAM-based preferred.")
        self.assertTrue(eligible)
        self.assertIn("flagged", note)


class TestScoring(unittest.TestCase):
    def test_fallback_score_rewards_title_and_skill_match(self):
        from src.scoring import score
        strong = score("Senior Data Analyst", "SQL, Python, dbt, Snowflake, Power BI, fully remote")
        weak = score("Marketing Manager", "social media and brand campaigns")
        self.assertGreater(strong, weak)
        self.assertLessEqual(strong, 100)


class TestFullPipeline(unittest.TestCase):
    """Runs src.main.run() end to end against all fixtures at once, into a
    throwaway CSV, to prove dedupe/freshness/eligibility/scoring/store all
    wire together correctly."""

    def test_full_run_against_fixtures(self):
        import shutil
        import tempfile

        tmpdir = tempfile.mkdtemp()
        csv_path = os.path.join(tmpdir, "postings.csv")

        patches = [
            patch("src.connectors.ashby.get_json", return_value=_load("ashby.json")),
            patch("src.connectors.workable.get_json", return_value=_load("workable.json")),
            patch("src.connectors.greenhouse.get_json", return_value=_load("greenhouse.json")),
            patch("src.connectors.lever.get_json", return_value=None),
            patch("src.connectors.smartrecruiters.get_json", return_value=None),
            patch("src.connectors.recruitee.get_json", return_value=None),
            patch("src.connectors.himalayas.get_json", return_value=_load("himalayas.json")),
            patch("src.connectors.remotive.get_json", return_value=_load("remotive.json")),
            patch("src.connectors.remoteok.get_json", return_value=_load("remoteok.json")),
        ]
        for p in patches:
            p.start()
        try:
            import src.main as main_mod
            with patch("src.main.get_store", return_value=__import__("src.store", fromlist=["CsvStore"]).CsvStore(csv_path)):
                with patch("src.connectors.weworkremotely.fetch", return_value=[]):
                    rows = main_mod.run()
        finally:
            for p in patches:
                p.stop()
            shutil.rmtree(tmpdir, ignore_errors=True)

        # Zefir (posted Aug 7) and Ruby Labs (posted Aug 20) are both >7 days
        # old as of this fixture's "today" and should be dropped by the
        # freshness filter — same treatment, proving the 7-day cutoff is
        # applied consistently regardless of source.
        titles = {r["title"] for r in rows}
        self.assertNotIn("Founding Analytics Engineer", titles)  # Zefir — too old
        self.assertNotIn("Data Analytics Engineer", titles)  # Ruby Labs — too old
        self.assertIn("Analytics Engineer", titles)  # Homeward — fresh + soft-flagged, not excluded
        self.assertIn("Junior Data Analyst", titles)  # SwissBorg — fresh + soft-flagged, not excluded
        self.assertNotIn("Staff Data Analyst", titles)  # Splice — explicit no-sponsorship language, hard-excluded

    def test_greenhouse_no_sponsorship_fixture_is_excluded(self):
        """Sanity check the Splice fixture (explicit no-sponsorship language)
        actually gets excluded by eligibility, isolated from the full-run test
        above so a failure here is unambiguous."""
        from src.connectors import greenhouse
        from src.eligibility import check
        with patch("src.connectors.greenhouse.get_json", return_value=_load("greenhouse.json")):
            postings = greenhouse.fetch("splice")
        eligible, note = check(postings[0].description)
        self.assertFalse(eligible)


if __name__ == "__main__":
    unittest.main(verbosity=2)
