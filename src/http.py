"""Shared HTTP helper: consistent user-agent, timeout, retry-once-on-failure."""
import time
import requests

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "PreciousObenJobAggregator/1.0 (personal job search tool; contact epoharaoben18@gmail.com)"
})


def get_json(url: str, params: dict = None, timeout: int = 15, retries: int = 2):
    """GET a URL and parse JSON. Returns None (not an exception) on failure,
    so one bad source never takes down the whole run."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout)
            if resp.status_code == 404:
                return None  # company/board doesn't exist on this platform — not an error
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 — deliberately broad, this is a best-effort fetch
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    print(f"  [warn] failed to fetch {url}: {last_err}")
    return None


def get_text(url: str, timeout: int = 15, retries: int = 2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    print(f"  [warn] failed to fetch {url}: {last_err}")
    return None
