"""Thin client for the WOCAT database API (https://wocat.net/api/database/redoc/)."""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv

BASE_URL = "https://wocat.net/api/database"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Where the corpus lives. Defaults to <repo>/data; point WOCAT_DATA_DIR at an existing
# copy (e.g. ../wocat/data) to reuse a download instead of fetching it again.
DATA_DIR = Path(os.environ.get("WOCAT_DATA_DIR") or PROJECT_ROOT / "data").resolve()
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


def get_token() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    token = os.environ.get("WOCAT_TOKEN")
    if not token:
        raise RuntimeError(
            "WOCAT_TOKEN is not set. Copy .env.example to .env and paste your token."
        )
    return token


class WocatClient:
    """Session-based client. All endpoints are GET-only and token-authenticated."""

    def __init__(self, token: str | None = None, timeout: int = 60):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {token or get_token()}",
                "Accept": "application/json",
            }
        )

    def get(self, path: str, **params: Any) -> Any:
        resp = self.session.get(f"{BASE_URL}/{path.strip('/')}/", params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # -- list endpoints (lightweight summaries, one request each) --------------
    def technologies(self) -> list[dict]:
        return self.get("technologies")

    def approaches(self) -> list[dict]:
        return self.get("approaches")

    def countries(self) -> list[dict]:
        return self.get("countries")

    # -- detail endpoint (the full ~190-field questionnaire) -------------------
    def technology(self, tech_id: int) -> dict:
        return self.get(f"technologies/{tech_id}")


def fetch_technology_details(
    ids: Iterable[int],
    client: WocatClient | None = None,
    cache_dir: Path = RAW_DIR / "technologies",
    workers: int = 6,
    refresh: bool = False,
    progress: bool = True,
) -> list[dict]:
    """Fetch full technology records, caching one JSON file per id.

    Re-runs are free: cached ids are read from disk unless ``refresh=True``. The client
    (and therefore the token) is only created on the first cache miss, so a fully cached
    corpus can be rebuilt with no token and no network.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    ids = list(ids)
    lazy: list[WocatClient] = [client] if client else []
    lock = threading.Lock()

    def online() -> WocatClient:
        with lock:
            if not lazy:
                lazy.append(WocatClient())
            return lazy[0]

    def load_one(tech_id: int) -> dict | None:
        path = cache_dir / f"{tech_id}.json"
        if path.exists() and not refresh:
            return json.loads(path.read_text())
        try:
            record = online().technology(tech_id)
        except requests.HTTPError as exc:  # skip withdrawn / restricted entries
            print(f"  ! {tech_id}: {exc}")
            return None
        path.write_text(json.dumps(record, ensure_ascii=False))
        return record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(load_one, ids))

    ok = [r for r in results if r is not None]
    if progress:
        print(f"  fetched/loaded {len(ok)}/{len(ids)} technology records")
    return ok
