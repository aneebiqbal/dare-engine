#!/usr/bin/env python3
"""Gamer-section screenshots on the real stack.

    .venv/bin/python scripts/capture_gamer.py [web-url] [out-dir]

Signs in with the development admin (which can see every clip), then captures
each gamer route at phone/desktop widths in dark and light. Missing artwork is
expected to fall back to the graphite plate, not a broken icon.
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3200"
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "screens" / "after" / "gamer"

MISSION = "m_61224900"
CLIP = "f314b715-eb29-4496-9847-8ada7e51b74c"

PAGES = [
    ("dashboard", "/"),
    ("today", "/today"),
    ("mission", f"/missions/{MISSION}"),
    ("live", "/live"),
    ("remote", "/remote"),
    ("clips", "/clips"),
    ("clip", f"/clips/{CLIP}"),
    ("export", f"/export/{CLIP}"),
    ("history", "/history"),
    ("results", "/results"),
    ("settings", "/settings"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size_name, width, height in [("phone", 390, 844), ("desktop", 1280, 900)]:
            for theme in ("dark", "light"):
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                page.goto(f"{BASE}/signin", wait_until="networkidle")
                page.click('[data-testid="signin-admin"]')
                for _ in range(40):
                    if any(c["name"] == "clipdesk_session" for c in context.cookies()):
                        break
                    page.wait_for_timeout(500)
                for name, path in PAGES:
                    target = OUT / f"{size_name}-{theme}-{name}.png"
                    if target.exists():
                        print(f"skip {target.name}")
                        continue
                    url = f"{BASE}{path}?theme={theme}"
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    try:
                        page.get_by_text("Skip tour", exact=True).first.click(timeout=1500)
                    except Exception:
                        pass
                    page.wait_for_timeout(4500)
                    page.screenshot(path=str(target), full_page=True)
                    print(target.name)
                context.close()
        browser.close()


if __name__ == "__main__":
    main()
