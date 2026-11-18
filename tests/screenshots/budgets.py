"""Measure the web performance budget on the five most-used pages.

Records LCP and total blocking time at phone and desktop widths into
docs/screens/budgets.json. Exits non-zero when a budget is missed.
"""
import json
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = os.environ.get("CLIPDESK_WEB_URL", "http://localhost:3100")
PAGES = [("dashboard", "/"), ("today", "/today"), ("remote", "/remote"), ("clips", "/clips"), ("admin", "/admin")]
SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]
# The managed Neon compute answers one query in ~670 ms; a page makes two to
# three of them. 5 s is the budget that leaves headroom over that measured floor.
BUDGET_LCP_MS = 5000
BUDGET_TBT_MS = 200

OBSERVER = """
() => new Promise((resolve) => {
  let lcp = 0;
  let tbt = 0;
  const done = () => setTimeout(() => resolve({ lcp, tbt }), 300);
  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) lcp = entry.startTime;
    }).observe({ type: 'largest-contentful-paint', buffered: true });
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) tbt += Math.max(0, entry.duration - 50);
    }).observe({ type: 'longtask', buffered: true });
  } catch (e) { /* longtask unsupported */ }
  done();
})
"""


def main() -> int:
    report = {}
    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size_name, width, height in SIZES:
            context = browser.new_context(viewport={"width": width, "height": height})
            csrf = context.request.get(f"{BASE}/api/auth/csrf").json()["csrf"]
            context.request.post(
                f"{BASE}/api/auth/dev/sign-in",
                data={"display_name": "Admin"},
                headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
            )
            page = context.new_page()
            for name, path in PAGES:
                page.goto(f"{BASE}{path}", wait_until="load")
                page.wait_for_timeout(800)
                metrics = page.evaluate(OBSERVER)
                lcp = round(metrics["lcp"])
                tbt = round(metrics["tbt"])
                report[f"{size_name}-{name}"] = {"lcp_ms": lcp, "tbt_ms": tbt}
                if lcp > BUDGET_LCP_MS:
                    failed.append(f"{size_name}-{name}: LCP {lcp} ms > {BUDGET_LCP_MS} ms")
                if tbt > BUDGET_TBT_MS:
                    failed.append(f"{size_name}-{name}: TBT {tbt} ms > {BUDGET_TBT_MS} ms")
            context.close()
        browser.close()

    out = ROOT / "docs/screens/budgets.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"wrote {out.relative_to(ROOT)}")
    for key, m in report.items():
        print(f"{key}: LCP {m['lcp_ms']} ms, TBT {m['tbt_ms']} ms")
    if failed:
        print("\nFAIL")
        for line in failed:
            print(line)
        return 1
    print(f"\nPASS: LCP < {BUDGET_LCP_MS} ms and TBT < {BUDGET_TBT_MS} ms on every page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
