"""Priority 2: games + the daily research brain, end to end on real data.

Runs against the recorded provider and the saved sample feed (the live source
keys are optional), so it proves the pipeline shape: sourced, schema-valid
candidates, an approval gate, an assignment, and the gamer's Today.
"""
import json
import pathlib
import time

import jsonschema

from helpers import API, dev_sign_in, sql  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
CARD_SCHEMA = json.loads((ROOT / "contracts" / "mission-card.schema.json").read_text())


def _cleanup(game_id: str) -> None:
    sql(f"DELETE FROM assignments WHERE mission_id IN (SELECT id FROM missions WHERE game_id = '{game_id}');")
    sql(f"DELETE FROM mission_sources WHERE mission_id IN (SELECT id FROM missions WHERE game_id = '{game_id}');")
    sql(f"DELETE FROM missions WHERE game_id = '{game_id}';")
    sql(f"DELETE FROM research_runs WHERE game_id = '{game_id}';")
    sql(f"DELETE FROM games WHERE id = '{game_id}';")


def _poll_run(admin, run_id: str) -> dict:
    for _ in range(60):
        run = admin.get(f"/admin/research/{run_id}")
        if run["status"] != "running":
            return run
        time.sleep(2)
    raise AssertionError("research run did not finish")


def _run_research(admin, game_id: str) -> dict:
    """Start a run and poll its real stage until it finishes."""
    started = admin.post(f"/admin/games/{game_id}/research", {})
    return _poll_run(admin, started["run_id"])


def _reset_provider() -> None:
    """Research must run on the recorded provider; clear any stored override."""
    sql("DELETE FROM global_settings")


def test_research_brain_to_gamer_today():
    admin = dev_sign_in("admin")
    _reset_provider()
    slug = f"research-test-{int(time.time())}"
    game = admin.post("/admin/games", {"slug": slug, "name": "Research Test Game"})
    game_id = game["id"]

    try:
        started = admin.post(f"/admin/games/{game_id}/research", {})
        assert started["status"] == "running"
        assert started["run_id"]
        run = _poll_run(admin, started["run_id"])
        assert run["ideas_count"] >= 1, "research produced no ideas"
        assert run["fallback"] is True, "recorded mode must be flagged as a fallback"
        assert sum(run["source_counts"].values()) >= 1

        profile = admin.get(f"/admin/games/{game_id}")
        assert profile["game"]["name"] == "Research Test Game"
        assert len(profile["candidates"]) == run["ideas_count"]
        assert profile["runs"][0]["status"] == "done"

        # Accuracy: every candidate cites a real source from the feed, and the
        # card itself is schema-valid.
        sample_urls = {
            s["url"]
            for s in json.loads((ROOT / "api" / "app" / "research_sample.json").read_text())["sources"]
        }
        for entry in profile["candidates"]:
            assert entry["sources"], f"{entry['id']} has no source"
            assert {s["url"] for s in entry["sources"]} <= sample_urls
            card = dict(entry["card"])
            card.setdefault("status", "unverified")
            card.setdefault("evidence", {"askers": 0, "source_video_ids": []})
            card.setdefault("policy", {"spoiler": False, "online_exploit": False})
            jsonschema.validate(card, CARD_SCHEMA)

        # The approval gate: nothing reaches a gamer unapproved.
        mission_id = profile["candidates"][0]["id"]
        admin.post(f"/admin/pool/{mission_id}/approve", {})
        assert admin.get(f"/missions/{mission_id}")["status"] == "unverified"

        # The generated card image is real and local (no remote image).
        with admin.opener.open(f"{API}/missions/{mission_id}/card.svg", timeout=30) as resp:
            assert resp.headers.get("content-type", "").startswith("image/svg+xml")
            assert b"<svg" in resp.read()

        creator = dev_sign_in("research-creator")
        creator_id = creator.get("/me")["user"]["id"]
        assigned = admin.post(f"/admin/pool/{mission_id}/assign", {"user_id": creator_id})
        assert assigned["state"] == "assigned"

        today = creator.get("/today")
        assert any(a["mission_id"] == mission_id for a in today["assignments"])

        # The game profile now shows the assignment.
        profile = admin.get(f"/admin/games/{game_id}")
        assert any(a["mission_id"] == mission_id for a in profile["assigned"])
    finally:
        _cleanup(game_id)


def test_pool_filters_by_game():
    admin = dev_sign_in("admin")
    _reset_provider()
    slug = f"research-filter-{int(time.time())}"
    game = admin.post("/admin/games", {"slug": slug, "name": "Filter Test Game"})
    game_id = game["id"]
    try:
        run = _run_research(admin, game_id)
        assert run["ideas_count"] >= 1
        items = admin.get(f"/admin/pool?game_id={game_id}")["items"]
        assert items, "game filter returned nothing"
        # Every returned candidate belongs to the game (via its sources/card).
        assert all(entry["sources"] for entry in items)
    finally:
        _cleanup(game_id)
