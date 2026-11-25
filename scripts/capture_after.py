#!/usr/bin/env python3
"""Fresh 'after' screenshots against a locally running stack.

Signs in with the QA admin, then captures the pages this session changed at
phone/desktop widths in dark and light.

    .venv/bin/python scripts/capture_after.py [web-url] [out-dir]

Needs the local API on 8001 (STORAGE_LOCAL_DIR set) and `next dev` on 3200.
"""
from __future__ import annotations

import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3200"
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "screens" / "after" / "2026-11-24"
EMAIL = "qa-admin@example.com"
PASSWORD = "clipdesk-qa-1234"

PAGES = [
    ("landing", "/landing"),
    ("welcome", "/welcome"),
    ("dashboard", "/"),
    ("today", "/today"),
    ("admin", "/admin"),
    ("admin-games", "/admin/games"),
    ("admin-projects", "/admin/projects"),
    ("admin-studio", "/admin/studio"),
    ("admin-calendar", "/admin/calendar"),
    ("admin-pool", "/admin/pool"),
    ("clips", "/clips"),
    ("results", "/results"),
    ("history", "/history"),
    ("settings", "/settings"),
]


def db_ids() -> tuple[str | None, str | None]:
    try:
        sys.path.insert(0, str(ROOT / "api"))
        sys.path.insert(0, str(ROOT / "shared"))
        import importlib.util

        spec = importlib.util.spec_from_file_location("llm_shared", ROOT / "shared" / "llm.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["llm_shared"] = mod
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        from app import db

        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM games WHERE enabled = true ORDER BY created_at LIMIT 1")
                game = cur.fetchone()
                cur.execute("SELECT id FROM clips ORDER BY created_at DESC LIMIT 1")
                clip = cur.fetchone()
        return (str(game[0]) if game else None, str(clip[0]) if clip else None)
    except Exception:
        return (None, None)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    game_id, clip_id = db_ids()
    pages = list(PAGES)
    if game_id:
        pages.append(("admin-game", f"/admin/games/{game_id}"))
    if clip_id:
        pages.extend([("clip", f"/clips/{clip_id}"), ("export", f"/export/{clip_id}")])
    def sign_in(context, page):
        page.goto(f"{BASE}/signin", wait_until="networkidle")
        page.fill('[data-testid="email"]', EMAIL)
        page.fill('[data-testid="password"]', PASSWORD)
        page.wait_for_timeout(400)
        page.wait_for_selector('[data-testid="signin-submit"]:not([disabled])', timeout=15000)
        page.click('[data-testid="signin-submit"]')
        for _ in range(40):
            if any(c["name"] == "clipdesk_session" for c in context.cookies()):
                return True
            page.wait_for_timeout(500)
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size_name, width, height in [("phone", 390, 844), ("desktop", 1280, 900)]:
            for theme in ("dark", "light"):
                # One session per viewport/theme: signing in per page trips the
                # auth rate limit and captures fall back to the sign-in screen.
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                if not sign_in(context, page):
                    print("sign-in failed; aborting this pass")
                    context.close()
                    continue
                for name, path in pages:
                    target = OUT / f"{size_name}-{theme}-{name}.png"
                    if target.exists():
                        print(f"skip {target.name}")
                        continue
                    url = f"{BASE}{path}?theme={theme}"
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    if "/signin" in page.url:
                        # A lost session mid-run: re-authenticate once, then retry.
                        if sign_in(context, page):
                            page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    # First-visit tour overlays are dismissed so the page itself is captured.
                    try:
                        page.get_by_text("Skip tour", exact=True).first.click(timeout=1500)
                    except Exception:
                        pass
                    page.wait_for_timeout(6000 if name == "admin" else 5000)
                    if name == "admin":
                        # The overview batches many reads and can take ~10-20 s
                        # against a cold Neon pool; give the real state time.
                        page.wait_for_timeout(18000)
                    page.screenshot(path=str(target), full_page=True)
                    print(target.name)
                context.close()
        browser.close()


if __name__ == "__main__":
    main()
