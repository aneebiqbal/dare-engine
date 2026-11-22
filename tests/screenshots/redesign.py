"""Before/after screenshots for the redesign.

Signs in with the real dev identity provider (DEV_AUTH_ENABLED=true), walks every
page at phone and desktop widths in dark and light, and writes full-page PNGs.

    .venv/bin/python tests/screenshots/redesign.py --label before
    .venv/bin/python tests/screenshots/redesign.py --label after

Writes into docs/screens/<label>/. Real data only: no NEXT_PUBLIC_API_MOCK.
"""
import argparse
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = os.environ.get("CLIPDESK_WEB_URL", "http://localhost:3100")

CLIP_ID = "cc2b6f87-891e-4dc0-a9ee-841461b38204"
GAME_ID = "42946eac-2464-44d1-8e0d-703ad08a1a7f"
CREATOR_ID = "3c20cd89-8ba1-447c-8888-d9845f789049"

PAGES = [
    ("welcome", "/welcome"),
    ("signin", "/signin"),
    ("signup", "/signup"),
    ("dashboard", "/"),
    ("today", "/today"),
    ("mission", "/missions/m_0001"),
    ("live", "/live"),
    ("remote", "/remote"),
    ("clips", "/clips"),
    ("clip", f"/clips/{CLIP_ID}"),
    ("export", f"/export/{CLIP_ID}"),
    ("history", "/history"),
    ("results", "/results"),
    ("settings", "/settings"),
    ("help", "/help"),
    ("leaderboard", "/leaderboard"),
    ("public-mission", "/m/m_0001"),
    ("creator", f"/creators/{CREATOR_ID}"),
    ("admin", "/admin"),
    ("admin-games", "/admin/games"),
    ("admin-game", f"/admin/games/{GAME_ID}"),
    ("admin-pool", "/admin/pool"),
    ("admin-studio", "/admin/studio"),
    ("admin-projects", "/admin/projects"),
    ("admin-calendar", "/admin/calendar"),
    ("admin-long-form", "/admin/long-form"),
    ("admin-models", "/admin/models"),
    ("admin-wizard", "/admin/wizard"),
    ("admin-setup", "/admin/setup"),
    ("admin-users", "/admin/users"),
    ("admin-invites", "/admin/invites"),
    ("admin-jobs", "/admin/jobs"),
    ("admin-ai", "/admin/ai"),
    ("admin-audit", "/admin/audit"),
    ("admin-templates", "/admin/templates"),
    ("styleguide", "/styleguide"),
]

SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]


def capture(browser, out: pathlib.Path, theme: str) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    csrf = context.request.get(f"{BASE}/api/auth/csrf").json()["csrf"]
    context.request.post(
        f"{BASE}/api/auth/dev/sign-in",
        data={"display_name": "Admin"},
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
    )
    page = context.new_page()
    for size_name, width, height in SIZES:
        page.set_viewport_size({"width": width, "height": height})
        for name, path in PAGES:
            page.goto(f"{BASE}{path}?theme={theme}", wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            target = out / f"{size_name}-{theme}-{name}.png"
            page.screenshot(path=str(target), full_page=True)
            print(target.relative_to(ROOT))
    context.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="before")
    args = ap.parse_args()
    out = ROOT / "docs" / "screens" / args.label
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in ("dark", "light"):
            capture(browser, out, theme)
        browser.close()
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
