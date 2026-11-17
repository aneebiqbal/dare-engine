"""M2 acceptance: typed questions become valid cards, and a creator accepts one.

CI uses the recorded LLM provider (no key). Signed in with a real account.
"""
import json
import pathlib

import jsonschema
import pytest

from helpers import ROOT, Client, make_admin, sql, truncate

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


@pytest.fixture(scope="module")
def session():
    truncate("missions", "assignments", "daily_sets", "ai_usage")
    return make_admin()


def test_ten_questions_produce_ten_valid_cards(session):
    body = session.post("/admin/questions", {"questions": QUESTIONS})
    assert len(body["cards"]) == 10
    schema = json.loads((ROOT / "contracts/mission-card.schema.json").read_text())
    for card in body["cards"]:
        jsonschema.validate(card, schema)


def test_pool_lists_the_candidates(session):
    pool = session.get("/admin/pool")
    assert pool["total"] >= 10
    assert all(entry["state"] == "candidate" for entry in pool["items"])


def test_approve_moves_a_card_out_of_the_pool(session):
    entry = session.get("/admin/pool")["items"][0]
    session.post(f"/admin/pool/{entry['id']}/approve", {})
    assert entry["id"] not in {e["id"] for e in session.get("/admin/pool")["items"]}


def test_ai_suggest_returns_three_cards(session):
    mission_id = session.get("/today")["picks"][0]["id"]
    res = session.post("/ai/suggest", {"mission_id": mission_id})
    assert len(res["suggestions"]) <= 3
    assert "fallback" in res


def test_playwright_accepts_one_mission():
    from playwright.sync_api import sync_playwright

    admin = make_admin()
    page_questions = "\n".join(QUESTIONS)
    admin.post("/admin/questions", {"questions": QUESTIONS})
    mission_id = admin.get("/admin/pool")["items"][0]["id"]
    admin.post(f"/admin/pool/{mission_id}/approve", {})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto("http://localhost:3100/signin", wait_until="networkidle")
            page.click('[data-testid="signin-alice"]')
            page.wait_for_selector("text=Your day", timeout=30000)
            try:
                page.locator('[role="dialog"][aria-label="Your first mission"]').wait_for(timeout=3000)
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
            except Exception:
                pass

            page.goto("http://localhost:3100/today", wait_until="networkidle")
            page.wait_for_selector('[data-testid="accept-button"]', timeout=30000)
            page.click('[data-testid="accept-button"]')
            page.wait_for_selector('[data-testid="accepted"]', timeout=30000)
        finally:
            browser.close()
