"""Where results land. Two backends behind one interface:

  - CsvStore: local CSV file. No credentials needed — this is what runs
    today, in this build/test session, and is a safe default GitHub Actions
    fallback if the Sheets secrets aren't configured yet.
  - SheetsStore: real Google Sheet via a service account. This is the
    intended production backend — not live-tested yet (needs Precious's
    Google Cloud service account, see README) but built against the
    documented Sheets API v4 shape.

main.py picks SheetsStore automatically when GOOGLE_SERVICE_ACCOUNT_JSON and
SHEET_ID are both set in the environment, else falls back to CsvStore so the
pipeline never just fails outright for lack of credentials.
"""
import csv
import os
from pathlib import Path

FIELDNAMES = [
    "date_found", "title", "company", "location", "posted_date", "age_days",
    "fit_score", "eligible", "eligibility_note", "company_size", "source",
    "url", "status",
]


class CsvStore:
    def __init__(self, path: str = "data/postings.csv"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()

    def get_existing_urls(self) -> set:
        urls = set()
        with open(self.path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                urls.add(row.get("url", "").strip().rstrip("/").lower())
        return urls

    def append_rows(self, rows: list[dict]):
        if not rows:
            return
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            for row in rows:
                writer.writerow(row)

    def archive_stale(self, max_age_days: float = 7.0):
        """Move rows older than max_age_days AND still status=new into a
        sibling archive CSV, leave anything Precious has already touched
        (status != new) alone."""
        if not self.path.exists():
            return 0
        keep, archive = [], []
        with open(self.path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            try:
                age = float(row.get("age_days", "unknown"))
            except ValueError:
                age = None
            if row.get("status") == "new" and age is not None and age > max_age_days:
                archive.append(row)
            else:
                keep.append(row)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(keep)
        if archive:
            archive_path = self.path.with_name(self.path.stem + "_archive.csv")
            write_header = not archive_path.exists()
            with open(archive_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                if write_header:
                    writer.writeheader()
                writer.writerows(archive)
        return len(archive)


class SheetsStore:
    """Google Sheets backend. Requires:
      GOOGLE_SERVICE_ACCOUNT_JSON — path to the service account key file
      SHEET_ID                    — the target spreadsheet's ID (from its URL)
    Not live-tested in this build session (no credentials available here) —
    verify on first real GitHub Actions run.
    """

    def __init__(self, sheet_id: str, credentials_path: str, worksheet_name: str = "Postings"):
        from google.oauth2.service_account import Credentials
        import gspread

        creds = Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(creds)
        self.sheet = client.open_by_key(sheet_id)
        try:
            self.ws = self.sheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            self.ws = self.sheet.add_worksheet(worksheet_name, rows=1000, cols=len(FIELDNAMES))
            self.ws.append_row(FIELDNAMES)

    def get_existing_urls(self) -> set:
        url_col_idx = FIELDNAMES.index("url") + 1
        col_values = self.ws.col_values(url_col_idx)[1:]  # skip header
        return {v.strip().rstrip("/").lower() for v in col_values if v}

    def append_rows(self, rows: list[dict]):
        if not rows:
            return
        values = [[row.get(f, "") for f in FIELDNAMES] for row in rows]
        self.ws.append_rows(values, value_input_option="USER_ENTERED")

    def archive_stale(self, max_age_days: float = 7.0):
        # v1: not implemented for Sheets yet (needs row-index bookkeeping
        # against a live sheet) — CsvStore has the reference implementation.
        # Add once the pipeline is running for real; see README open items.
        return 0


def get_store():
    sheet_id = os.environ.get("SHEET_ID")
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sheet_id and creds_path and os.path.exists(creds_path):
        return SheetsStore(sheet_id, creds_path)
    print("  [info] SHEET_ID / GOOGLE_SERVICE_ACCOUNT_JSON not set — writing to data/postings.csv instead")
    return CsvStore()
