#!/usr/bin/env python3
"""Prove the research brain reads a live source.

Runs one real research run against the configured game and prints what actually
happened: how many sources came from which live kind, whether the sample feed
was used, whether the AI provider was live, and how long it took.

    .venv/bin/python scripts/prove_research_live.py [game-slug]

Exit code 0 when at least one live source was fetched. A recorded AI provider is
reported honestly (`ai_fallback: true`) — it needs key credit to write ideas.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "shared"))

# The images copy shared/llm.py to /app/llm_shared.py; load it the same way.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("llm_shared", ROOT / "shared" / "llm.py")
_llm_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_llm_shared)
sys.modules["llm_shared"] = _llm_shared

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app import db, research  # noqa: E402


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else ""
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, slug, name FROM games WHERE enabled = true "
                "AND (%s = '' OR slug = %s) ORDER BY created_at LIMIT 1",
                (slug, slug),
            )
            row = cur.fetchone()
    if row is None:
        print(json.dumps({"error": f"no enabled game matches {slug!r}"}))
        return 2
    game_id, game_slug, name = str(row[0]), row[1], row[2]
    print(f"game: {name} ({game_slug})")
    started = research.start_research(game_id)
    run_id = started["run_id"]
    print(f"run: {run_id}")
    deadline = time.time() + 900
    last = None
    while time.time() < deadline:
        run = research.get_run(run_id)
        if run is None:
            print("run vanished")
            return 2
        if run["stage"] != last:
            print(f"  stage {run['stage']}: {run['detail']}")
            last = run["stage"]
        if run["status"] in ("done", "failed"):
            break
        time.sleep(2)
    print(json.dumps(run, indent=2))
    live_sources = sum((run.get("source_counts") or {}).values())
    return 0 if live_sources and not run.get("source_fallback") else 1


if __name__ == "__main__":
    raise SystemExit(main())
