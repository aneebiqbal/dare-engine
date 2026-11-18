"""Sprint 6 Part F: a new account sees the tour once, keyboard only, and can replay it."""
import pytest
from playwright.sync_api import sync_playwright

from helpers import create_user_with_invite, make_admin, truncate


@pytest.fixture(scope="module")
def fresh_user():
    truncate("users", "invites", "sessions", "tour_progress", "login_attempts", "password_resets")
    admin = make_admin()
    return create_user_with_invite(admin, "tour@example.com", name="Tour User")


def test_tour_runs_keyboard_only_and_can_be_replayed(fresh_user):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        try:
            page.goto("http://localhost:3100/signin", wait_until="networkidle")
            page.fill('[data-testid="email"]', "tour@example.com")
            page.fill('[data-testid="password"]', "creator-password-123")
            page.click('[data-testid="signin-submit"]')

            dialog = page.locator('[role="dialog"][aria-label="Your first mission"]')
            dialog.wait_for(timeout=30000)

            # Keyboard only: advance three steps, then skip with Escape.
            for _ in range(3):
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(200)
            page.keyboard.press("Escape")
            page.wait_for_timeout(1500)

            progress = fresh_user.get("/tours")
            creator = next(t for t in progress if t["tour_id"] == "creator")
            assert creator["skipped"] or creator["completed"]

            # Replay from Help.
            page.goto("http://localhost:3100/help", wait_until="networkidle")
            page.click('[data-testid="help-replay-tour"]')
            page.locator('[role="dialog"][aria-label="Your first mission"]').wait_for(timeout=15000)
            page.keyboard.press("Escape")
        finally:
            browser.close()
