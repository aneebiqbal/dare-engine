#!/usr/bin/env python3
"""Backfill missing game cover art from RAWG.

    .venv/bin/python scripts/backfill_game_art.py

Only rows with a NULL/empty art_url are touched. A game with no RAWG match is
left alone and reported, never given a placeholder.
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "shared"))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("llm_shared", ROOT / "shared" / "llm.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sys.modules["llm_shared"] = _mod

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app import db  # noqa: E402
from app.keys import resolve  # noqa: E402


def rawg_search(query: str, key: str) -> dict | None:
    url = "https://api.rawg.io/api/games?" + urllib.parse.urlencode(
        {"key": key, "search": query, "page_size": 5}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "clipdesk-research/0.1"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def main() -> int:
    key = resolve("rawg")
    if not key:
        print("no RAWG key configured")
        return 2
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, slug, name FROM games WHERE art_url IS NULL OR art_url = ''")
            missing = cur.fetchall()
            for gid, slug, name in missing:
                try:
                    data = rawg_search(name, key)
                except Exception as exc:
                    print(f"{name}: RAWG unreachable ({type(exc).__name__})")
                    continue
                results = (data or {}).get("results") or []
                match = next((g for g in results if g.get("slug") == slug), results[0] if results else None)
                if not match or not match.get("background_image"):
                    print(f"{name}: no RAWG match, left empty")
                    continue
                cur.execute(
                    "UPDATE games SET art_url = %s, external_id = COALESCE(external_id, %s), "
                    "genre = COALESCE(genre, %s), release_date = COALESCE(release_date, %s) "
                    "WHERE id = %s",
                    (
                        match["background_image"],
                        str(match["id"]) if match.get("id") is not None else None,
                        (match.get("genres") or [{}])[0].get("name"),
                        match.get("released"),
                        gid,
                    ),
                )
                print(f"{name}: {match['background_image']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
