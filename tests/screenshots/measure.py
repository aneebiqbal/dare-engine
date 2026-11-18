"""Measure cold/warm navigation timings and API resource durations."""
import json
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CLIPDESK_WEB_URL", "http://localhost:3100")
PAGES = [
    ("dashboard", "/"), ("today", "/today"), ("live", "/live"), ("remote", "/remote"),
    ("clips", "/clips"), ("results", "/results"), ("history", "/history"),
    ("settings", "/settings"), ("help", "/help"), ("admin", "/admin"),
    ("admin-pool", "/admin/pool"), ("admin-studio", "/admin/studio"),
    ("admin-users", "/admin/users"), ("admin-jobs", "/admin/jobs"),
]

NAV = """() => {
  const n = performance.getEntriesByType('navigation')[0] || {};
  let lcp = 0;
  try { for (const e of performance.getEntriesByType('largest-contentful-paint')) lcp = e.startTime; } catch (e) {}
  const api = performance.getEntriesByType('resource')
    .filter(r => r.name.includes('/api/'))
    .map(r => ({ path: r.name.split('/api/')[1]?.split('?')[0], ms: Math.round(r.duration) }))
    .sort((a, b) => b.ms - a.ms);
  return { ttfb: Math.round(n.responseStart - n.startTime), dcl: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd), lcp: Math.round(lcp), api };
}"""


def main():
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        csrf = context.request.get(f"{BASE}/api/auth/csrf").json()["csrf"]
        context.request.post(
            f"{BASE}/api/auth/dev/sign-in", data={"display_name": "Admin"},
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
        )
        page = context.new_page()
        for name, path in PAGES:
            page.goto(f"{BASE}{path}", wait_until="networkidle")
            cold = page.evaluate(NAV)
            page.reload(wait_until="networkidle")
            warm = page.evaluate(NAV)
            out[name] = {"path": path, "cold": cold, "warm": warm}
            print(f"{name:14s} cold ttfb {cold['ttfb']:5d} lcp {cold['lcp']:5d} | warm ttfb {warm['ttfb']:5d} lcp {warm['lcp']:5d} | api {cold['api'][:3]}")
        browser.close()
    pathlib.Path("/tmp/measure.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    sys.exit(main())
