"""The end-to-end product journey on real data, one screenshot per step.

Run with the stack up, NEXT_PUBLIC_API_MOCK=0, DEV_AUTH_ENABLED=true and
NEXT_PUBLIC_DEV_AUTH=1. It seeds a real game, sourced ideas, an assignment, then
the admin runs the real studio (upload -> find moments -> generate), reviews the
clip with commentary, schedules it, builds a long-form video and records results.
A creator walks Today, Go Live and Remote. Every step is screenshotted to
docs/screens/flow/ and the real "Up next" links are asserted.
"""
from __future__ import annotations

import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "acceptance"))
sys.path.insert(0, str(ROOT / "tests"))

from helpers import WEB, dev_sign_in, truncate  # noqa: E402

OUT = ROOT / "docs" / "screens" / "flow"
FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"


def studio_upload(client, filename="session.mp4"):
    boundary = "----flow"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{filename}\"\r\nContent-Type: video/mp4\r\n\r\n"
    ).encode() + FIXTURE.read_bytes() + (f"\r\n--{boundary}--\r\n").encode()
    return client.call(
        "POST", "/studio/upload", raw=body, ctype=f"multipart/form-data; boundary={boundary}"
    )


def seed() -> dict:
    truncate(
        "missions", "assignments", "attempts", "daily_sets", "clips", "jobs",
        "studio_candidates", "studio_recordings", "calendar_entries", "long_forms",
        "posts", "metrics", "games", "mission_sources", "research_runs",
        "exports", "voice_overs", "streams", "marks",
    )
    admin = dev_sign_in("Admin")
    slug = f"flow-{int(time.time())}"
    game = admin.post("/admin/games", {"slug": slug, "name": "Flow Game"})
    game_id = game["id"]
    admin.post(f"/admin/games/{game_id}/research", {})
    profile = admin.get(f"/admin/games/{game_id}")
    mission_id = profile["candidates"][0]["id"]
    admin.post(f"/admin/pool/{mission_id}/approve", {})

    creator = dev_sign_in("Alice")
    creator_id = creator.get("/me")["user"]["id"]
    admin.post(f"/admin/pool/{mission_id}/assign", {"user_id": creator_id})

    # The admin runs the real studio: upload, find moments, generate.
    rec = studio_upload(admin)
    recording_id = rec["recording_id"]
    admin.post("/studio/detect", {"recording_id": recording_id, "top_n": 3})
    detail = {}
    for _ in range(150):
        detail = admin.get(f"/studio/recordings/{recording_id}")
        if detail["candidates"]:
            break
        time.sleep(2)
    candidate = detail["candidates"][0]
    gen = admin.post(
        "/studio/generate",
        {
            "recording_id": recording_id,
            "mission_id": mission_id,
            "windows": [
                {
                    "start": candidate["start"],
                    "end": candidate["end"],
                    "template_id": "cold_open",
                    "candidate_id": candidate["id"],
                }
            ],
        },
    )
    clip_id = gen["clips"][0]
    for _ in range(150):
        if admin.get(f"/clips/{clip_id}")["state"] == "ready":
            break
        time.sleep(2)

    admin.patch(f"/clips/{clip_id}", {"commentary": "I cut the corner and the wanted level spiked."})
    admin.post(f"/clips/{clip_id}/approve", {})
    day = time.strftime("%Y-%m-%d")
    admin.post("/admin/calendar", {"clip_id": clip_id, "scheduled_for": day, "platform": "youtube"})
    long_form = admin.post(
        "/admin/long-form",
        {"title": "Flow session", "clip_ids": [clip_id], "intro": "Flow", "outro": "Clipdesk"},
    )
    admin.post(
        "/metrics",
        {
            "clip_id": clip_id,
            "views": 1200,
            "avg_view_percentage": 42,
            "swiped": 300,
            "saves": 12,
            "shares": 8,
        },
    )
    return {
        "game_id": game_id,
        "mission_id": mission_id,
        "recording_id": recording_id,
        "clip_id": clip_id,
        "long_form_id": long_form["id"],
    }


def shoot(page, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    print(f"docs/screens/flow/{name}.png")


def sign_in(browser, name: str):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto(f"{WEB}/signin", wait_until="networkidle")
    page.click(f'[data-testid="signin-{name.lower()}"]')
    page.wait_for_selector("text=Your day", timeout=30000)
    return context, page


def walk(page, steps) -> None:
    for name, path, expect in steps:
        page.goto(f"{WEB}{path}", wait_until="networkidle")
        page.wait_for_timeout(600)
        shoot(page, name)
        if expect is None:
            continue
        links = page.locator('[data-testid="next-step"]')
        assert links.count() >= 1, f"{path} has no Up next affordance"
        href = links.first.get_attribute("href") or ""
        assert href.startswith("/"), f"{path} next step is not a real route: {href!r}"
        if expect != "*":
            assert expect in href, f"{path} next step {href!r} does not lead to {expect!r}"
        print(f"  up next -> {href}")


def main() -> int:
    data = seed()
    with sync_playwright() as p:
        browser = p.chromium.launch()

        admin_ctx, admin = sign_in(browser, "Admin")
        walk(
            admin,
            [
                ("01-game-setup", "/admin/games", "/admin/games/"),
                ("02-daily-ideas", f"/admin/games/{data['game_id']}", "/admin/pool"),
                ("03-approve-assign", "/admin/pool", None),
                ("04-studio", "/admin/studio", "*"),
                ("05-review", f"/clips/{data['clip_id']}", "/admin/calendar"),
                ("06-calendar", "/admin/calendar", "/admin/long-form"),
                ("07-long-form", "/admin/long-form", None),
                ("08-results", "/results", "/today"),
            ],
        )
        admin_ctx.close()

        creator_ctx, user = sign_in(browser, "Alice")
        # Today: accept the assigned dare, then the next step is Go Live.
        user.goto(f"{WEB}/today", wait_until="networkidle")
        user.wait_for_timeout(500)
        accept = user.locator('[data-testid="accept-button"]')
        if accept.count():
            accept.first.click()
            user.wait_for_timeout(800)
        shoot(user, "09-today")
        links = user.locator('[data-testid="next-step"]')
        assert links.count() >= 1 and "/live" in (links.first.get_attribute("href") or ""), (
            "Today did not lead to Go Live"
        )
        print("  up next ->", links.first.get_attribute("href"))

        walk(user, [("10-go-live", "/live", "/remote")])

        # Remote: really tap Start and Done, then the next step is Clips.
        user.goto(f"{WEB}/remote", wait_until="networkidle")
        user.wait_for_timeout(500)
        user.click('[data-testid="start"]')
        user.wait_for_selector('[data-testid="done"]', timeout=15000)
        user.click('[data-testid="done"]')
        user.fill('[data-testid="result-input"]', "0:41")
        user.click('[data-testid="submit-result"]')
        user.wait_for_selector('[data-testid="done-state"]', timeout=15000)
        shoot(user, "11-remote")
        links = user.locator('[data-testid="next-step"]')
        assert links.count() >= 1 and "/clips" in (links.first.get_attribute("href") or ""), (
            "Remote did not lead to Clips"
        )
        print("  up next ->", links.first.get_attribute("href"))
        creator_ctx.close()
        browser.close()
    print("flow complete:", data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
