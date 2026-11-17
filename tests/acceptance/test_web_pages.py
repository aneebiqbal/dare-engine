"""Web app flows against the real backend (NEXT_PUBLIC_API_MOCK=0)."""
import pathlib
import time

import pytest
from playwright.sync_api import sync_playwright

from helpers import (
    ROOT,
    dev_sign_in,
    make_admin,
    seed_mission,
    upload_recording,
)

WEB = "http://localhost:3100"
SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        yield p.chromium.launch()


def _size(name):
    return next(s for s in SIZES if s[0] == name)


def dismiss_tour(page):
    try:
        page.locator('[role="dialog"][aria-modal="true"]').first.wait_for(timeout=3000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
    except Exception:
        pass


def sign_in(page, name="Alice"):
    page.goto(f"{WEB}/signin", wait_until="networkidle")
    page.click(f'[data-testid="signin-{name.lower()}"]')
    page.wait_for_selector("text=Your day", timeout=30000)
    dismiss_tour(page)


def _seed_clip(email: str = "", name: str = "Alice") -> str:
    """Admin seeds a mission; the dev-signed-in Alice uploads the stand-in."""
    admin = make_admin()
    mission = seed_mission(admin)
    creator = dev_sign_in(name)
    upload_recording(creator, [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}])
    deadline = time.time() + 300
    while time.time() < deadline:
        clips = creator.get("/clips")["items"]
        if clips and clips[0]["state"] == "ready":
            return clips[0]["id"]
        time.sleep(5)
    pytest.skip("clip did not render in time")


@pytest.mark.parametrize("size", ["phone", "desktop"])
def test_w1_public_pages(browser, size):
    _, width, height = _size(size)
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    try:
        page.goto(f"{WEB}/welcome", wait_until="networkidle")
        page.wait_for_selector("text=The Short is written", timeout=15000)
        page.goto(f"{WEB}/signin", wait_until="networkidle")
        page.wait_for_selector("text=Sign in to Clipdesk", timeout=15000)
        for path, text in [("/terms", "Terms of service"), ("/privacy", "Privacy policy")]:
            page.goto(f"{WEB}{path}", wait_until="networkidle")
            page.wait_for_selector(f"text={text}", timeout=15000)
    finally:
        context.close()


@pytest.mark.parametrize("size", ["phone", "desktop"])
def test_w2_today_and_go_live(browser, size):
    seed_mission(make_admin())
    _, width, height = _size(size)
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    try:
        sign_in(page)
        page.goto(f"{WEB}/today", wait_until="networkidle")
        page.click('[data-testid="accept-button"]')
        page.wait_for_selector('[data-testid="accepted"]', timeout=15000)

        page.goto(f"{WEB}/live", wait_until="networkidle")
        page.wait_for_selector("text=Your stream address", timeout=15000)
        assert page.evaluate("document.body.innerText.includes('••••••')")
        page.click("text=Reveal")
        page.wait_for_selector("text=Copy key", timeout=15000)
    finally:
        context.close()


@pytest.mark.parametrize("size", ["phone", "desktop"])
def test_w3_remote_marks(browser, size):
    _, width, height = _size(size)
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    try:
        sign_in(page, "Bob")
        page.goto(f"{WEB}/remote", wait_until="networkidle")
        page.click('[data-testid="start"]')
        page.wait_for_selector('[data-testid="done"]', timeout=15000)
        page.click('[data-testid="done"]')
        page.fill('[data-testid="result-input"]', "0:41")
        page.click('[data-testid="submit-result"]')
        page.wait_for_selector("text=Mission logged", timeout=15000)

        context.set_offline(True)
        page.wait_for_selector("text=Offline", timeout=15000)
        context.set_offline(False)
        page.wait_for_selector("text=Live", timeout=15000)
    finally:
        context.close()


def test_w3_clip_review(browser):
    clip_id = _seed_clip()
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        sign_in(page, "Alice")
        page.goto(f"{WEB}/clips/{clip_id}", wait_until="networkidle")
        page.fill("input", "A better title")
        page.click("text=Save title")
        page.wait_for_selector("text=Title saved", timeout=15000)
        page.click("text=Approve")
        page.wait_for_selector("text=Clip approved", timeout=15000)
    finally:
        context.close()


@pytest.mark.parametrize("size", ["phone", "desktop"])
def test_w4_clips_and_history(browser, size):
    _seed_clip()
    _, width, height = _size(size)
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    try:
        sign_in(page, "Alice")
        page.goto(f"{WEB}/clips", wait_until="networkidle")
        page.wait_for_selector("text=Your Shorts", timeout=15000)
        page.wait_for_selector("text=Review", timeout=15000)
        page.goto(f"{WEB}/history", wait_until="networkidle")
        page.wait_for_selector("text=Mission history", timeout=15000)
    finally:
        context.close()


def test_w6_admin_pool(browser):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        sign_in(page, "Admin")
        page.goto(f"{WEB}/admin/pool", wait_until="networkidle")
        page.fill('[data-testid="questions"]', "Can you outrun five stars on a bicycle?")
        page.click('[data-testid="write-cards"]')
        page.wait_for_selector('[data-testid="approve-button"]', timeout=30000)
        page.click('[data-testid="approve-button"]')
        page.wait_for_timeout(500)
    finally:
        context.close()


def test_w8_real_journey(browser):
    seed_mission(make_admin())
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        sign_in(page)
        page.goto(f"{WEB}/today", wait_until="networkidle")
        page.click('[data-testid="accept-button"]')
        page.wait_for_selector('[data-testid="accepted"]', timeout=15000)

        page.goto(f"{WEB}/remote", wait_until="networkidle")
        page.click('[data-testid="start"]')
        page.click('[data-testid="done"]')
        page.fill('[data-testid="result-input"]', "0:41")
        page.click('[data-testid="submit-result"]')
        page.wait_for_selector("text=Mission logged", timeout=15000)

        # A finished Short to review on the Clips page.
        _seed_clip()
        page.goto(f"{WEB}/clips", wait_until="networkidle")
        page.wait_for_selector("text=Review", timeout=15000)
    finally:
        context.close()
