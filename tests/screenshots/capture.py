"""Headless screenshots of every page at phone and desktop widths, light and dark.

Writes into docs/screens/. Run with the stack up and NEXT_PUBLIC_API_MOCK=1 so
pages whose backend does not exist still render their filled state.
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/screens"
BASE = os.environ.get("CLIPDESK_WEB_URL", "http://localhost:3100")

PAGES = [
    ("welcome", "/welcome"),
    ("signin", "/signin"),
    ("today", "/"),
    ("admin", "/admin"),
    ("remote", "/remote"),
    ("clips", "/clips"),
    ("live", "/live"),
    ("results", "/results"),
    ("history", "/history"),
    ("settings", "/settings"),
    ("leaderboard", "/leaderboard"),
    ("mission", "/m/m_0214"),
    ("creator", "/creators/u_1"),
    ("terms", "/terms"),
    ("privacy", "/privacy"),
    ("styleguide", "/styleguide"),
]

SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size_name, width, height in SIZES:
            for theme in ("dark", "light"):
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                for name, path in PAGES:
                    url = f"{BASE}{path}?theme={theme}"
                    page.goto(url, wait_until="networkidle")
                    page.wait_for_timeout(400)
                    target = OUT / f"{size_name}-{theme}-{name}.png"
                    page.screenshot(path=str(target), full_page=True)
                    print(f"{target.relative_to(ROOT)}")
                context.close()
        browser.close()


if __name__ == "__main__":
    sys.exit(main())
