"""The end-to-end product journey on real data, one screenshot per step.

Run with the stack up, NEXT_PUBLIC_API_MOCK=0, DEV_AUTH_ENABLED=true and
NEXT_PUBLIC_DEV_AUTH=1. It seeds a real game, sourced ideas, an assignment, a
rendered clip with commentary, a calendar entry, a long-form build and metrics,
then walks the UI as an admin and a creator, saving docs/screens/flow/<step>.png
and asserting every step has a real "Up next" link.
"""
from __future__ import annotations

import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "acceptance"))
sys.path.insert(0, str(ROOT / "tests"))

from helpers import WEB, dev_sign_in, make_admin, upload_recording  # noqa: E402

OUT = ROOT / "docs" / "screens" / "flow"
FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"


def seed() -> dict:
    admin = make_admin()
    slug = f"flow-{int(time.time())}"
    game = admin.post("/admin/games", {"slug": slug, "name": "Flow Game"})
    game_id = game["id"]
    admin.post(f"/admin/games/{game_id}/research", {})
    profile = admin.get(f"/admin/games/{game_id}")
    mission_id = profile["candidates"][0]["id"]
    admin.post(f"/admin/pool/{mission_id}/approve", {})

    creator = dev_sign_in("flow-creator")
    creator_id = creator.get("/me")["user"]["id"]
    admin.post(f"/admin/pool/{mission_id}/assign", {"user_id": creator_id})

    uploaded = upload_recording(
        creator, [{"mission_id": mission_id, "start": 5, "end": 20, "result": "0:41"}]
    )
    clip_id = uploaded["clips"][0]
    deadline = time.time() + 420
    while time.time() < deadline:
        if creator.get(f"/clips/{clip_id}")["state"] == "ready":
            break
        time.sleep(5)
    creator.patch(f"/clips/{clip_id}", {"commentary": "I cut the corner and the wanted level spiked."})
    creator.post(f"/clips/{clip_id}/approve", {})

    day = time.strftime("%Y-%m-%d")
    admin.post("/admin/calendar", {"clip_id": clip_id, "scheduled_for": day, "platform": "youtube"})
    long_form = admin.post(
        "/admin/long-form",
        {"title": "Flow session", "clip_ids": [clip_id], "intro": "Flow", "outro": "Clipdesk"},
    )
    creator.post(
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
        links = page.locator('[data-testid="next-step"]')
        assert links.count() >= 1, f"{path} has no Up next affordance"
        href = links.first.get_attribute("href") or ""
        assert href.startswith("/"), f"{path} next step is not a real route: {href!r}"
        if expect:
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
                ("04-studio", "/admin/studio", None),
                ("05-calendar", "/admin/calendar", "/admin/long-form"),
                ("06-long-form", "/admin/long-form", None),
            ],
        )
        admin_ctx.close()

        creator_ctx, user = sign_in(browser, "Alice")
        walk(
            user,
            [
                ("07-today", "/today", "/live"),
                ("08-go-live", "/live", "/remote"),
                ("09-remote", "/remote", "/clips"),
                ("10-review", f"/clips/{data['clip_id']}", "/admin/calendar"),
                ("11-results", "/results", "/today"),
            ],
        )
        creator_ctx.close()
        browser.close()
    print("flow complete:", data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
