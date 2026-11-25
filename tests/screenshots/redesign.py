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

def _ids():
    """Resolve real ids at runtime; tests truncate the tables between runs."""
    import psycopg

    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip())
    url = env.get("DATABASE_URL_DIRECT") or env.get("DATABASE_URL")
    import time

    out = [None, None, None, None]
    for attempt in range(6):
        try:
            with psycopg.connect(url) as conn:
                with conn.cursor() as cur:
                    out = []
                    for sql in (
                        "select id from clips order by created_at desc limit 1",
                        "select id from games order by created_at limit 1",
                        "select id from missions order by created_at limit 1",
                        "select id from users where role='creator' order by created_at limit 1",
                    ):
                        cur.execute(sql)
                        row = cur.fetchone()
                        out.append(str(row[0]) if row else None)
            if out[0]:
                return out
        except Exception:
            pass
        time.sleep(5)
    return out if "out" in locals() else [None, None, None, None]


CLIP_ID, GAME_ID, MISSION_ID, CREATOR_ID = _ids()
MISSION_ID = MISSION_ID or "m_0001"
CLIP_ID = CLIP_ID or "c_0001"

PAGES = [
    ("welcome", "/welcome"),
    ("signin", "/signin"),
    ("signup", "/signup"),
    ("dashboard", "/"),
    ("today", "/today"),
    ("mission", f"/missions/{MISSION_ID}"),
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
            for attempt in range(4):
                try:
                    page.goto(f"{BASE}{path}?theme={theme}", wait_until="domcontentloaded", timeout=30000)
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    page.wait_for_timeout(3000)
            # Wait for the async region to leave its skeleton; pages that poll
            # never reach networkidle, so this is the reliable "filled" signal.
            try:
                page.wait_for_selector('[aria-busy="true"]', state="detached", timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(1200)
            # A concurrent acceptance run can truncate sessions mid-pass.
            if "session expired" in page.content():
                try:
                    csrf = context.request.get(f"{BASE}/api/auth/csrf", timeout=20000).json()["csrf"]
                    context.request.post(
                        f"{BASE}/api/auth/dev/sign-in",
                        data={"display_name": "Admin"},
                        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
                    )
                    page.goto(f"{BASE}{path}?theme={theme}", wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1500)
                except Exception:
                    pass
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
