"""M2 acceptance: typed questions become valid cards, and a creator accepts one.

CI uses the recorded LLM provider (no key). The live Gemini run is manual.
Signed in as a real development user (R1).
"""
import http.cookiejar
import json
import pathlib
import subprocess
import urllib.request

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
API = "http://localhost:8000"
WEB = "http://localhost:3100"

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


def _opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


@pytest.fixture(scope="module")
def session():
    """A real signed-in development user."""
    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "db", "psql", "-U", "clipdesk", "-d", "clipdesk",
            "-c", "TRUNCATE missions, assignments, daily_sets, sessions RESTART IDENTITY CASCADE;",
        ],
        cwd=ROOT, check=True, capture_output=True,
    )
    opener = _opener()
    req = urllib.request.Request(
        f"{API}/auth/dev/sign-in",
        data=json.dumps({"display_name": "Mission Editor"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=30) as resp:
        json.loads(resp.read())
    return opener


def _post(opener, path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=60) as resp:
        return resp.status, json.loads(resp.read())


def _get(opener, path: str) -> dict:
    with opener.open(f"{API}{path}", timeout=30) as resp:
        return json.loads(resp.read())


def test_ten_questions_produce_ten_valid_cards(session):
    status, body = _post(session, "/admin/questions", {"questions": QUESTIONS})
    assert status == 200
    assert len(body["cards"]) == 10
    schema = json.loads((ROOT / "contracts/mission-card.schema.json").read_text())
    for card in body["cards"]:
        jsonschema.validate(card, schema)


def test_pool_lists_the_candidates(session):
    pool = _get(session, "/admin/pool")
    assert len(pool) >= 10
    assert all(entry["state"] == "candidate" for entry in pool)


def test_approve_moves_a_card_out_of_the_pool(session):
    pool = _get(session, "/admin/pool")
    entry = pool[0]
    status, _ = _post(session, f"/admin/pool/{entry['id']}/approve", {})
    assert status == 200
    assert entry["id"] not in {e["id"] for e in _get(session, "/admin/pool")}


def test_playwright_accepts_one_mission():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(f"{WEB}/signin", wait_until="networkidle")
            page.click('[data-testid="signin-alice"]')
            page.wait_for_selector("text=Play today's mission", timeout=30000)

            page.goto(f"{WEB}/admin", wait_until="networkidle")
            page.fill('[data-testid="questions"]', "\n".join(QUESTIONS))
            page.click('[data-testid="write-cards"]')
            page.wait_for_selector('[data-testid="approve-button"]', timeout=30000)
            page.click('[data-testid="approve-button"]')
            page.wait_for_timeout(1000)

            page.goto(f"{WEB}/", wait_until="networkidle")
            page.wait_for_selector('[data-testid="accept-button"]', timeout=30000)
            page.click('[data-testid="accept-button"]')
            page.wait_for_selector('[data-testid="accepted"]', timeout=30000)
        finally:
            browser.close()
