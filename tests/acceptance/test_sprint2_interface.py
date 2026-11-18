"""Sprint 2: the connected interface across both portals, on real data."""
import time
import urllib.error

import pytest
from playwright.sync_api import sync_playwright

from helpers import (
    dev_sign_in,
    make_admin,
    seed_mission,
    sign_up,
    sql,
    truncate,
    upload_recording,
)

WEB = "http://localhost:3100"
SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]
SUFFIX = int(time.time())


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        yield p.chromium.launch()


def _size(name):
    return next(s for s in SIZES if s[0] == name)


def _expect_error(client, method, path, **kwargs):
    try:
        client.call(method, path, **kwargs)
    except urllib.error.HTTPError as exc:
        return exc.code
    raise AssertionError(f"{method} {path} should have been refused")


# ---------------------------------------------------------------- Part C + D


def test_admin_invite_assign_and_gamer_loop():
    """Admin creates an invite, writes and approves a dare, assigns it; the
    gamer sees it, accepts it, records a session; the admin sees the job, the
    audit entries and the role boundary holds."""
    admin = make_admin()
    gamer = sign_up(f"gamer-{SUFFIX}@example.com", name="Gamer")
    truncate("missions", "assignments", "daily_sets", "ai_usage")

    # The admin writes one dare with the AI and approves it.
    written = admin.post("/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    assert written["count"] >= 1
    pool = admin.get("/admin/pool")["items"]
    assert pool, "the written dare should be in the pool"
    mission_id = pool[0]["id"]

    admin.post(f"/admin/pool/{mission_id}/approve", {})
    gamer_id = gamer.get("/me")["user"]["id"]
    assigned = admin.post(f"/admin/pool/{mission_id}/assign", {"user_id": gamer_id})
    assert assigned["state"] == "assigned"

    # It is on the gamer's Today.
    today = gamer.get("/today")
    today_ids = ({today["daily"]["id"]} if today["daily"] else set()) | {p["id"] for p in today["picks"]}
    assert mission_id in today_ids

    # The gamer accepts and records a real session.
    gamer.post("/assignments", {"mission_id": mission_id})
    uploaded = upload_recording(
        gamer, [{"mission_id": mission_id, "start": 5, "end": 20, "result": "0:41"}]
    )
    clip_id = uploaded["clips"][0]

    # The admin sees the render job and the audit trail.
    deadline = time.time() + 120
    kinds = set()
    while time.time() < deadline:
        kinds = {j["kind"] for j in admin.get("/admin/jobs?page_size=50")["items"]}
        if "render_clip" in kinds:
            break
        time.sleep(3)
    assert "render_clip" in kinds

    audit = admin.get("/admin/audit?page_size=100")["items"]
    actions = {a["action"] for a in audit}
    assert {"pool.approve", "pool.assign"} <= actions

    # Role boundary: the gamer cannot reach any admin route.
    assert _expect_error(gamer, "GET", "/admin/users") == 403
    assert _expect_error(gamer, "GET", "/admin/jobs") == 403

    # A clip with no gamer assignment never appears in the gamer's portal.
    admin_only = sql("INSERT INTO clips (state, title) VALUES ('ready', 'admin only') RETURNING id").strip()
    gamer_clips = {c["id"] for c in gamer.get("/clips")["items"]}
    assert admin_only not in gamer_clips
    assert clip_id in gamer_clips


# ---------------------------------------------------------------- four states


def _open_signed_in(browser, name, width=390, height=844):
    """Sign in through the real dev endpoint, so any display name works."""
    context = browser.new_context(viewport={"width": width, "height": height})
    csrf = context.request.get(f"{WEB}/api/auth/csrf").json()["csrf"]
    context.request.post(
        f"{WEB}/api/auth/dev/sign-in",
        data={"display_name": name},
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
    )
    page = context.new_page()
    page.goto(f"{WEB}/", wait_until="networkidle")
    page.wait_for_selector("text=Your day", timeout=30000)
    try:
        page.locator('[role="dialog"][aria-modal="true"]').first.wait_for(timeout=2000)
        page.keyboard.press("Escape")
    except Exception:
        pass
    return context, page


@pytest.mark.parametrize("size", ["phone", "desktop"])
def test_client_pages_error_state(browser, size):
    _, width, height = _size(size)
    context = browser.new_context(viewport={"width": width, "height": height})
    csrf = context.request.get(f"{WEB}/api/auth/csrf").json()["csrf"]
    context.request.post(
        f"{WEB}/api/auth/dev/sign-in",
        data={"display_name": "Admin"},
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
    )
    page = context.new_page()
    try:
        page.route("**/api/**", lambda route: route.abort())
        for path in ("/", "/results", "/admin"):
            page.goto(f"{WEB}{path}", wait_until="domcontentloaded")
            page.wait_for_selector('[role="alert"]', timeout=15000)
    finally:
        context.close()


@pytest.mark.parametrize("size", ["phone", "desktop"])
def test_loading_skeleton(browser, size):
    _, width, height = _size(size)
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    try:
        page.goto(f"{WEB}/signin", wait_until="networkidle")
        page.click('[data-testid="signin-alice"]')
        page.wait_for_selector("text=Your day", timeout=30000)

        def slow(route):
            time.sleep(1.5)
            route.continue_()

        page.route("**/api/results**", slow)
        page.goto(f"{WEB}/results", wait_until="domcontentloaded")
        page.wait_for_selector('[aria-busy="true"]', timeout=10000)
        page.wait_for_selector("text=Total views", timeout=20000)
    finally:
        context.close()


def test_empty_states(browser):
    admin = make_admin()
    sql("UPDATE missions SET status = 'rejected'")
    try:
        context, page = _open_signed_in(browser, f"Empty{SUFFIX}")
        try:
            page.goto(f"{WEB}/today", wait_until="networkidle")
            page.wait_for_selector("text=No dares today", timeout=15000)

            page.goto(f"{WEB}/history", wait_until="networkidle")
            page.wait_for_selector("text=No sessions yet", timeout=15000)

            page.goto(f"{WEB}/clips", wait_until="networkidle")
            page.wait_for_selector("text=Nothing here yet", timeout=15000)
        finally:
            context.close()
    finally:
        sql("UPDATE missions SET status = 'unverified' WHERE status = 'rejected'")


def _approve_two(admin):
    truncate("missions", "assignments", "daily_sets", "ai_usage")
    admin.post("/admin/questions", {"questions": [
        "Can you outrun five stars on a bicycle?",
        "Can you win a street race without using the brakes?",
    ]})
    items = admin.get("/admin/pool")["items"]
    for item in items:
        admin.post(f"/admin/pool/{item['id']}/approve", {})
    return [item["id"] for item in items]


@pytest.mark.parametrize("size", ["phone", "desktop"])
def test_creator_page_flows(browser, size):
    admin = make_admin()
    _approve_two(admin)
    _, width, height = _size(size)
    context, page = _open_signed_in(browser, "Flow", width, height)
    try:
        page.goto(f"{WEB}/today", wait_until="networkidle")
        page.click('[data-testid="accept-button"]')
        page.wait_for_selector('[data-testid="accepted"]', timeout=15000)
        page.click("text=Swap")
        page.wait_for_selector('[role="dialog"][aria-modal="true"]', timeout=15000)
        page.locator('[role="dialog"] button').first.click()
        page.wait_for_timeout(800)

        page.goto(f"{WEB}/live", wait_until="domcontentloaded")
        page.wait_for_selector("text=Stream key", timeout=15000)
        page.wait_for_selector("text=Before you go live", timeout=15000)
        assert page.evaluate("document.body.innerText.includes('••••••')")

        page.goto(f"{WEB}/remote", wait_until="networkidle")
        page.click('[data-testid="start"]')
        page.click('[data-testid="done"]')
        page.fill('[data-testid="result-input"]', "0:41")
        page.click('[data-testid="submit-result"]')
        page.wait_for_selector('[data-testid="next-dare"]', timeout=15000)

        page.goto(f"{WEB}/history", wait_until="networkidle")
        page.fill('[data-testid="history-search"]', "Can you")
        page.wait_for_selector("text=Can you", timeout=15000)
    finally:
        context.close()


def test_results_metric_entry(browser):
    admin = make_admin()
    mission = seed_mission(admin)
    creator = dev_sign_in("Metric")
    uploaded = upload_recording(
        creator, [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}]
    )
    clip_id = uploaded["clips"][0]
    deadline = time.time() + 300
    while time.time() < deadline:
        if creator.get(f"/clips/{clip_id}")["state"] == "ready":
            break
        time.sleep(4)
    context, page = _open_signed_in(browser, "Metric")
    try:
        page.goto(f"{WEB}/results", wait_until="networkidle")
        page.click("text=Add metrics")
        page.wait_for_selector('[role="dialog"][aria-modal="true"]', timeout=15000)
        page.fill('input[type="number"] >> nth=0', "1204")
        page.fill('input[type="number"] >> nth=1', "42")
        page.click("text=Save metrics")
        page.wait_for_selector("text=1,204", timeout=15000)
    finally:
        context.close()


def test_admin_assign_flow(browser):
    admin = make_admin()
    gamer = sign_up(f"assign-{SUFFIX}@example.com", name="Assignee")
    truncate("missions", "assignments", "daily_sets", "ai_usage")
    admin.post("/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    mission_id = admin.get("/admin/pool")["items"][0]["id"]
    admin.post(f"/admin/pool/{mission_id}/approve", {})
    gamer_id = gamer.get("/me")["user"]["id"]

    context, page = _open_signed_in(browser, "Admin")
    try:
        page.goto(f"{WEB}/admin/pool", wait_until="networkidle")
        page.click("text=Assign")
        page.wait_for_selector('[role="dialog"][aria-modal="true"]', timeout=15000)
        page.select_option("select", label="Assignee")
        page.click("text=Assign dare")
        page.wait_for_selector("text=Dare assigned", timeout=15000)

        page.goto(f"{WEB}/admin/jobs", wait_until="networkidle")
        assert page.locator("text=Stage").first.is_visible()
    finally:
        context.close()
    assert gamer_id


def test_styleguide_both_themes(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        for theme in ("light", "dark"):
            page.goto(f"{WEB}/styleguide?theme={theme}", wait_until="networkidle")
            page.wait_for_selector("text=Clipdesk design system", timeout=15000)
            assert page.evaluate("document.documentElement.classList.contains('dark')") == (theme == "dark")
            for text in ("Buttons", "Inputs", "Card", "Table", "States", "Stat tile", "Status"):
                assert page.locator(f"text={text}").first.is_visible()
    finally:
        context.close()
