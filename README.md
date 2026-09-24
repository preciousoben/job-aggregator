# Job aggregator

Your own scheduled pipeline: polls job boards and small-startup ATS boards
directly, dedupes, filters for freshness (nothing older than 7 days) and
eligibility (same hard-blocker-only rule used in the manual pulls), scores
each posting's fit against your resume, and writes new rows to a Google
Sheet. Runs on GitHub Actions, not through Claude — that's the whole point,
it costs nothing per run beyond GitHub's free Actions minutes and a trivial
amount of embedding API usage.

## What's actually tested vs. not (read this first)

**This build session's sandbox blocks outbound network calls to arbitrary
external hosts from code** (only PyPI/npm/a short allowlist are open — this
is an org policy on the Claude Cowork cloud environment, not something to
work around). So every connector here is built against real, confirmed API
shapes (grabbed via Claude's WebFetch tool, which *is* allowed through) and
tested against saved fixtures of that real data (`tests/test_connectors.py`,
14/14 passing), but **none of it has been run live against the actual
internet yet.** GitHub Actions runners don't have this restriction, so the
first real scheduled run (or a manual `workflow_dispatch` run) is the actual
integration test. Do that run and skim its logs before trusting the sheet.

Confirmed solid (live-tested via WebFetch during research, matches the
fixtures exactly): Ashby, Workable, Greenhouse, Himalayas, Remotive,
RemoteOK, We Work Remotely RSS.

Built from documentation only, not yet live-tested against a real company:
Lever, SmartRecruiters, Recruitee. `config/companies.yaml` deliberately
leaves these three empty — add a slug once you've confirmed it against a
real company's board (or just let the first real run tell you; a 404 there
just means zero postings, not a crash).

Not yet built at all: the Wellfound/web3.career/startup.jobs scrapers (Tier
3 in the source list — no official API, confirmed scrapable by hand but
needs real HTML-parsing code, which is more fragile and was lower priority
than getting the clean-API sources working first). The YC and seedtable.io
discovery scripts (only topstartups.io is built). The Sheets-side stale-row
archival (CSV has it, Sheets doesn't yet — see `src/store.py`).

## Setup

### 1. Google Sheet + service account (for the Sheets backend)
Without this, the pipeline still runs and writes to `data/postings.csv`
instead — safe default, nothing breaks, you just don't get the live sheet.

1. Create a Google Sheet, note its ID from the URL
   (`docs.google.com/spreadsheets/d/<THIS PART>/edit`).
2. In Google Cloud Console: new project → enable the Google Sheets API →
   create a service account → create a JSON key for it → download it.
3. Share the Sheet with the service account's email (found in the JSON key,
   looks like `...@...iam.gserviceaccount.com`), Editor access.
4. In your GitHub repo: Settings → Secrets and variables → Actions, add:
   - `SHEET_ID` — the sheet ID from step 1
   - `GOOGLE_SERVICE_ACCOUNT_JSON` — the *entire contents* of the JSON key file

### 2. Voyage AI key (for real embedding-based fit scores)
Without this, scoring falls back to a keyword/skill-overlap heuristic —
cruder, but the pipeline still runs and every posting still gets a 0-100
score, just a less accurate one.

1. Sign up at voyageai.com (free tier: 200M tokens, plenty for this).
2. Add `VOYAGE_API_KEY` as a GitHub Actions secret.

### 3. Your real resume
Replace `data/resume.txt` with your actual resume text (plain text is
fine, doesn't need to be pretty). The placeholder in there now is a thin
stand-in built from your stored profile facts — real embedding scoring
needs the real thing.

### 4. Push this repo to GitHub
```
git init
git add -A
git commit -m "job aggregator v1"
git remote add origin <your repo URL>
git push -u origin main
```
The `poll.yml` workflow starts firing hourly automatically once secrets are
set. Trigger it manually first (Actions tab → Poll job sources →
Run workflow) and check the logs before trusting the schedule.

## Running locally (no GitHub needed, useful for iterating)
```
pip install -r requirements.txt
python -m src.main
```
Writes to `data/postings.csv` unless `SHEET_ID` / `GOOGLE_SERVICE_ACCOUNT_JSON`
are set as environment variables.

## Running the tests
```
python -m unittest tests.test_connectors -v
```
These run against saved fixtures, no network needed — safe to run anywhere,
including this sandbox.

## Design notes / why it's built this way
- **No LLM in the polling loop.** Every source fetch, the dedupe, the
  freshness filter, and the hard-blocker eligibility scan are plain code.
  Fit scoring uses embeddings (one cheap API call per new posting), not a
  reasoning pass — that's the "thin judgment" you asked for, and it's what
  actually saves the recurring cost of the old twice-daily agent pull.
- **7-day freshness is enforced twice**: at ingestion (a posting older than
  7 days never gets written in the first place) and on every run (any row
  still marked `status: new` that's aged past 7 days since gets moved to an
  archive — see `store.py`). A row you've already marked `applied` or
  anything other than `new` is left alone, so acting on something doesn't
  make it vanish out from under you.
- **Eligibility stays permissive by design**, same rule as the manual pulls:
  only excluded for an explicit "must hold local work authorization, no
  sponsorship" statement or a genuine onsite/hybrid requirement. Everything
  else — restrictive-sounding country lists, timezone requirements — passes
  through with a flag in `eligibility_note` so you keep full information
  instead of the pipeline guessing on your behalf.

## Open items (see job-aggregator-build.md in project memory for full history)
- Live-verify Lever and SmartRecruiters against real companies.
- Build the Tier 3 scrapers (Wellfound especially — it surfaces company size
  directly, which is valuable for your size targeting).
- Build the YC and seedtable.io discovery scripts alongside topstartups.io.
- Sheets-side stale-row archival.
- Recalibrate the embedding-score rescale in `scoring.py` once there's a
  real batch of scores to look at — the 0.3-0.9 cosine-similarity range
  assumed there is a starting guess, not measured.
- Phase two: the outreach/cold-email layer — needs a separate data problem
  solved first (finding a real contact per company), not scoped yet.
