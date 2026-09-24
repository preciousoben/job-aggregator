"""Fit-score a posting 0-100 against Precious's resume/profile.

Two modes:
  - Embedding mode (preferred): if VOYAGE_API_KEY is set, embed the resume
    once and each posting's title+description, score by cosine similarity.
    Cheap (Voyage's free tier is 200M tokens) and needs no per-posting
    reasoning call, which is the whole point of "thin judgment."
  - Fallback mode (no key configured yet, or the API call fails): a
    keyword/skill-overlap heuristic so the pipeline still runs end-to-end
    without blocking on Voyage account setup. Cruder, but consistent and
    free, and it's the actual mode this build is tested in today.

Swap in the real embedding call once PRECIOUS_RESUME.txt + VOYAGE_API_KEY
are both in place — see README for setup.
"""
import os
import re

_TITLE_KEYWORDS = {
    "data analyst": 25,
    "data engineer": 25,
    "analytics engineer": 25,
    "bi analyst": 20,
    "business intelligence analyst": 20,
}

# Pulled from her stored technical profile — keep this in sync with her
# resume; used by the fallback scorer only (embedding mode reads the resume
# text file directly instead).
_SKILL_KEYWORDS = [
    "sql", "python", "power bi", "dbt", "snowflake", "tableau", "pandas",
    "numpy", "etl", "elt", "bigquery", "looker", "postgresql", "mysql",
    "data modeling", "data pipeline", "airflow", "medallion", "git",
]


def _fallback_score(title: str, description: str) -> float:
    text = f"{title} {description}".lower()
    score = 0.0
    for phrase, weight in _TITLE_KEYWORDS.items():
        if phrase in title.lower():
            score += weight
            break  # only count the best title match once
    hits = sum(1 for kw in _SKILL_KEYWORDS if kw in text)
    # up to 60 points for skill overlap, scaled against a realistic hit count
    score += min(60.0, hits * (60.0 / 8))
    # small bonus if it's clearly remote-friendly language
    if re.search(r"\bremote\b", text):
        score += 10
    return round(min(100.0, score), 1)


def _embedding_score(title: str, description: str, resume_text: str, api_key: str) -> float | None:
    """Real embedding-similarity scorer. Not live-tested yet (needs a Voyage
    API key, which isn't configured in this build session) — implemented
    against Voyage's documented API shape, verify on first real run."""
    try:
        import requests
        import numpy as np

        resp = requests.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "input": [resume_text, f"{title}\n\n{description}"],
                "model": "voyage-4-lite",
                "input_type": "document",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        resume_vec = np.array(data[0]["embedding"])
        job_vec = np.array(data[1]["embedding"])
        cosine = float(
            np.dot(resume_vec, job_vec) / (np.linalg.norm(resume_vec) * np.linalg.norm(job_vec))
        )
        # cosine similarity is typically ~0.3-0.9 for resume/JD pairs in practice;
        # this rescale is a starting point — recalibrate against real score
        # spread once we have a batch of real results (see README).
        return round(max(0.0, min(100.0, (cosine - 0.3) / 0.6 * 100)), 1)
    except Exception as e:  # noqa: BLE001 — never let scoring take the whole run down
        print(f"  [warn] embedding scoring failed, falling back to keyword score: {e}")
        return None


def score(title: str, description: str, resume_text: str = "") -> float:
    api_key = os.environ.get("VOYAGE_API_KEY")
    if api_key and resume_text:
        result = _embedding_score(title, description, resume_text, api_key)
        if result is not None:
            return result
    return _fallback_score(title, description)
