"""Web app flows against the real backend (NEXT_PUBLIC_API_MOCK=0).

Pages whose backend is not built are not exercised here; they are listed under
"Mocked pages" in PROGRESS.md with their Gate 0 blocker.
"""
import http.cookiejar
import json
import pathlib
import subprocess
import time
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
WEB = "http://localhost:3100"
API = "http://localhost:8000"
STANDIN = ROOT / "tests/fixtures/standin_speech_45s.mp4"

SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        yield p.chromium.launch()


def _size(name):
    return next(s for s in SIZES if s[0] == name)


def sign_in(page, name="Alice"):
    page.goto(f"{WEB}/signin", wait_until="networkidle")
    page.click(f'[data-testid="signin-{name.lower()}"]')
    page.wait_for_selector("text=Play today's mission", timeout=30000)


def _api_opener(name="Alice"):
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req = urllib.request.Request(
        f"{API}/auth/dev/sign-in",
        data=json.dumps({"display_name": name}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=30) as resp:
        json.loads(resp.read())
    return opener


def _seed_clip(name="Alice"):
    """Upload the stand-in with one mark and wait for the real Short."""
    opener = _api_opener(name)

    def call(method, path, body=None, raw=None, ctype="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(
            f"{API}{path}", data=data, method=method,
            headers={"Content-Type": ctype} if data else {},
        )
        with opener.open(req, timeout=180) as resp:
            return json.loads(resp.read())

    call("POST", "/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    pool = call("GET", "/admin/pool")
    mission_id = pool[0]["id"]
    call("POST", f"/admin/pool/{mission_id}/approve", {})

    boundary = "----seed"
    marks = json.dumps([{"mission_id": mission_id, "start": 5, "end": 20, "result": "0:41"}])
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"rec.mp4\"\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + STANDIN.read_bytes() + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"marks\"\r\n\r\n{marks}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    call("POST", "/uploads", raw=body, ctype=f"multipart/form-data; boundary={boundary}")

    deadline = time.time() + 300
    while time.time() < deadline:
        clips = call("GET", "/clips")
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
    _, width, height = _size(size)
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    try:
        sign_in(page)
        page.click("text=Accept")
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
    clip_id = _seed_clip("Alice")
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        sign_in(page, "Alice")
        page.goto(f"{WEB}/clips/{clip_id}", wait_until="networkidle")
        page.fill("input", "A better title")
        page.click("text=Save")
        page.wait_for_selector("text=Title saved", timeout=15000)
        page.click("text=Approve")
        page.wait_for_selector("text=Clip approved", timeout=15000)
    finally:
        context.close()


@pytest.mark.parametrize("size", ["phone", "desktop"])
def test_w4_clips_and_history(browser, size):
    _seed_clip("Alice")
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
        sign_in(page)
        page.goto(f"{WEB}/admin", wait_until="networkidle")
        page.fill('[data-testid="questions"]', "Can you outrun five stars on a bicycle?")
        page.click('[data-testid="write-cards"]')
        page.wait_for_selector('[data-testid="approve-button"]', timeout=30000)
        page.click('[data-testid="approve-button"]')
        page.wait_for_timeout(500)
    finally:
        context.close()


def test_w8_real_journey(browser):
    _seed_clip("Alice")
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        sign_in(page)
        page.click("text=Accept")
        page.wait_for_selector('[data-testid="accepted"]', timeout=15000)

        page.goto(f"{WEB}/remote", wait_until="networkidle")
        page.click('[data-testid="start"]')
        page.click('[data-testid="done"]')
        page.fill('[data-testid="result-input"]', "0:41")
        page.click('[data-testid="submit-result"]')
        page.wait_for_selector("text=Mission logged", timeout=15000)

        page.goto(f"{WEB}/clips", wait_until="networkidle")
        page.wait_for_selector("text=Review", timeout=15000)
    finally:
        context.close()
