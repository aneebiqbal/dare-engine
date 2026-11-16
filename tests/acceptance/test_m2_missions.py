"""M2 acceptance: typed questions become valid cards, and a creator accepts one.

CI uses the recorded LLM provider (no key). The live Gemini run is manual.
"""
import json
import os
import pathlib
import subprocess
import urllib.request

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
API = os.environ.get("CLIPDESK_API_URL", "http://localhost:8000")
WEB = os.environ.get("CLIPDESK_WEB_URL", "http://localhost:3100")


@pytest.fixture(scope="module", autouse=True)
def clean_missions():
    """Make the acceptance run repeatable: start from an empty mission pool."""
    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "db", "psql",
            "-U", "clipdesk", "-d", "clipdesk", "-c",
            "TRUNCATE missions, assignments, daily_sets RESTART IDENTITY CASCADE;",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    yield

QUESTIONS = [
    "Can you outrun five stars on a bicycle?",
    "What happens if you jump off the tallest building in a car?",
    "Is it possible to steal a police car in free roam?",
    "Can you win a street race without using the brakes?",
    "What is the fastest car in the game?",
    "Can you survive a five-star wanted level on foot?",
    "Is it possible to swim across the whole map?",
    "Can you land a helicopter on a moving truck?",
    "What happens when you drive into the ocean?",
    "Can you finish a heist alone?",
]


def _post(path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, json.loads(resp.read())


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as resp:
        return json.loads(resp.read())


def test_ten_questions_produce_ten_valid_cards():
    status, body = _post("/admin/questions", {"questions": QUESTIONS})
    assert status == 200
    cards = body["cards"]
    assert len(cards) == 10

    schema = json.loads((ROOT / "contracts/mission-card.schema.json").read_text())
    for card in cards:
        jsonschema.validate(card, schema)


def test_pool_lists_the_candidates():
    pool = _get("/admin/pool")
    assert len(pool) >= 10
    assert all(entry["state"] == "candidate" for entry in pool)


def test_approve_moves_a_card_out_of_the_pool():
    pool = _get("/admin/pool")
    entry = pool[0]
    status, body = _post(f"/admin/pool/{entry['id']}/approve", {})
    assert status == 200
    assert entry["id"] not in {e["id"] for e in _get("/admin/pool")}


def test_playwright_accepts_one_mission():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(f"{WEB}/admin")
            page.fill('[data-testid="questions"]', "\n".join(QUESTIONS))
            page.click('[data-testid="write-cards"]')
            page.wait_for_selector('[data-testid="approve-button"]', timeout=30000)
            page.click('[data-testid="approve-button"]')
            page.wait_for_timeout(1000)

            page.goto(f"{WEB}/")
            page.wait_for_selector('[data-testid="accept-button"]', timeout=30000)
            page.click('[data-testid="accept-button"]')
            page.wait_for_selector('[data-testid="accepted"]', timeout=30000)
        finally:
            browser.close()
