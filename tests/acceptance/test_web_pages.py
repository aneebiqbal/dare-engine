"""Web app acceptance: W1-W6 page flows plus the W7 end-to-end journey.

Runs against the mock-enabled web app (NEXT_PUBLIC_API_MOCK=1) for pages whose
backend is blocked by Gate 0, and against the real API where it exists. The pages
that are mocked are listed in PROGRESS.md.
"""
import os
import pathlib

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
WEB = os.environ.get("CLIPDESK_WEB_URL", "http://localhost:3100")

SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        yield p.chromium.launch()


def page_for(browser, size):
    name, width, height = size
    context = browser.new_context(viewport={"width": width, "height": height})
    return context, context.new_page()


PUBLIC = [
    ("welcome", "/welcome", "The Short is written"),
    ("signin", "/signin", "Sign in with Google"),
    ("mission", "/m/m_0214", "5 STARS."),
    ("leaderboard", "/leaderboard", "Daily Mission board"),
    ("creator", "/creators/u_1", "Creator u_1"),
    ("terms", "/terms", "Terms of service"),
    ("privacy", "/privacy", "Privacy policy"),
]


@pytest.mark.parametrize("size", [s[0] for s in SIZES], ids=["phone", "desktop"])
def test_w1_public_pages(browser, size):
    context, page = page_for(browser, SIZES[0] if size == "phone" else SIZES[1])
    try:
        for name, path, text in PUBLIC:
            page.goto(f"{WEB}{path}", wait_until="networkidle")
            page.wait_for_selector(f"text={text}", timeout=15000)
    finally:
        context.close()


@pytest.mark.parametrize("size", [s[0] for s in SIZES], ids=["phone", "desktop"])
def test_w2_today_and_go_live(browser, size):
    context, page = page_for(browser, SIZES[0] if size == "phone" else SIZES[1])
    try:
        page.goto(f"{WEB}/", wait_until="networkidle")
        page.wait_for_selector("text=Play today's mission", timeout=15000)
        page.click("text=Accept")
        page.wait_for_selector("text=accepted", timeout=15000)

        page.goto(f"{WEB}/live", wait_until="networkidle")
        page.wait_for_selector("text=Your stream address", timeout=15000)
        # The key is masked in the rendered UI, never shown in full.
        assert "dev-key-please-change" not in page.inner_text("body")
        page.click("text=Reveal")
        page.wait_for_selector("text=dev-key-please-change", timeout=15000)
    finally:
        context.close()


@pytest.mark.parametrize("size", [s[0] for s in SIZES], ids=["phone", "desktop"])
def test_w3_remote_start_done_and_offline_queue(browser, size):
    context, page = page_for(browser, SIZES[0] if size == "phone" else SIZES[1])
    try:
        page.goto(f"{WEB}/remote", wait_until="networkidle")
        page.click('[data-testid="start"]')
        page.wait_for_selector('[data-testid="done"]', timeout=15000)
        page.click('[data-testid="done"]')
        page.fill('[data-testid="result-input"]', "0:41")
        page.click('[data-testid="submit-result"]')
        page.wait_for_selector("text=Mission logged", timeout=15000)

        # Offline taps are queued with their original timestamp, then flushed.
        page.reload(wait_until="networkidle")
        page.wait_for_selector('[data-testid="start"]', timeout=15000)
        context.set_offline(True)
        page.wait_for_selector("text=Offline", timeout=15000)
        page.click('[data-testid="start"]')
        page.wait_for_selector('[data-testid="pending"]', timeout=15000)
        context.set_offline(False)
        page.wait_for_selector("text=Live", timeout=15000)
        page.wait_for_selector('[data-testid="pending"]', state="detached", timeout=15000)
    finally:
        context.close()


def test_w3_clip_review(browser):
    context, page = page_for(browser, SIZES[0])
    try:
        page.goto(f"{WEB}/clips/c_0001", wait_until="networkidle")
        page.fill("input", "A better title")
        page.click("text=Save")
        page.wait_for_selector("text=Title saved", timeout=15000)
        page.click("text=Approve")
        page.wait_for_selector("text=Clip approved", timeout=15000)
    finally:
        context.close()


def test_w4_after_stream_pages(browser):
    context, page = page_for(browser, SIZES[0])
    try:
        for path, text in [
            ("/clips", "Your Shorts"),
            ("/results", "Views and retention"),
            ("/history", "Mission history"),
        ]:
            page.goto(f"{WEB}{path}", wait_until="networkidle")
            page.wait_for_selector(f"text={text}", timeout=15000)
    finally:
        context.close()


def test_w5_settings(browser):
    context, page = page_for(browser, SIZES[0])
    try:
        page.goto(f"{WEB}/settings", wait_until="networkidle")
        page.wait_for_selector("text=Account settings", timeout=15000)
        page.wait_for_selector("text=Clips used", timeout=15000)
        page.click("text=Export my data")
        page.wait_for_selector("text=Export queued", timeout=15000)
    finally:
        context.close()


def test_w6_admin_pool_and_tabs(browser):
    context, page = page_for(browser, SIZES[0])
    try:
        page.goto(f"{WEB}/admin", wait_until="networkidle")
        page.fill('[data-testid="questions"]', "Can you outrun five stars on a bicycle?")
        page.click('[data-testid="write-cards"]')
        page.wait_for_selector('[data-testid="approve-button"]', timeout=15000)
        for tab in ["Templates", "Users", "Jobs", "Health"]:
            page.click(f'[role="tab"]:has-text("{tab}")')
            page.wait_for_timeout(200)
    finally:
        context.close()


def test_w7_journey(browser):
    """Sign-in → accept → Start/Done → review → leaderboard."""
    context, page = page_for(browser, SIZES[0])
    try:
        page.goto(f"{WEB}/signin", wait_until="networkidle")
        page.click("text=Continue as dev creator")
        page.wait_for_selector("text=Play today's mission", timeout=15000)

        page.click("text=Accept")
        page.wait_for_selector("text=accepted", timeout=15000)

        page.goto(f"{WEB}/remote", wait_until="networkidle")
        page.click('[data-testid="start"]')
        page.click('[data-testid="done"]')
        page.fill('[data-testid="result-input"]', "0:41")
        page.click('[data-testid="submit-result"]')
        page.wait_for_selector("text=Mission logged", timeout=15000)

        page.goto(f"{WEB}/clips/c_0001", wait_until="networkidle")
        page.click("text=Approve")
        page.wait_for_selector("text=Clip approved", timeout=15000)

        page.goto(f"{WEB}/leaderboard", wait_until="networkidle")
        page.wait_for_selector("text=#1", timeout=15000)
    finally:
        context.close()
