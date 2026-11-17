"""Automated accessibility checks with axe-core on the main pages.

Runs at phone and desktop widths and writes docs/screens/a11y.json. Exits non-zero
on any serious or critical violation.
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
AXE = pathlib.Path(__file__).parent / "lib" / "axe.min.js"
BASE = __import__("os").environ.get("CLIPDESK_WEB_URL", "http://localhost:3100")

PAGES = [("welcome", "/welcome"), ("today", "/"), ("remote", "/remote"), ("clips", "/clips"), ("styleguide", "/styleguide")]
SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]


def main() -> int:
    report = {}
    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size_name, width, height in SIZES:
            context = browser.new_context(viewport={"width": width, "height": height})
            # Sign in so the protected pages render their filled state.
            context.request.post(
                f"{BASE}/api/auth/dev/sign-in",
                data={"display_name": "Axe"},
                headers={"Content-Type": "application/json"},
            )
            page = context.new_page()
            for name, path in PAGES:
                page.goto(f"{BASE}{path}?theme=dark", wait_until="networkidle")
                page.add_script_tag(path=str(AXE))
                results = page.evaluate(
                    """() => axe.run(document, { resultTypes: ['violations'] })"""
                )
                violations = [
                    {"id": v["id"], "impact": v["impact"], "nodes": len(v["nodes"]), "help": v["help"]}
                    for v in results["violations"]
                    if v["impact"] in ("serious", "critical")
                ]
                report[f"{size_name}-{name}"] = violations
                if violations:
                    failed.append(f"{size_name}-{name}: {violations}")
            context.close()
        browser.close()

    out = ROOT / "docs/screens/a11y.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"wrote {out.relative_to(ROOT)}")
    for key, violations in report.items():
        print(f"{key}: {len(violations)} serious/critical")
    if failed:
        print("\nFAIL")
        for line in failed:
            print(line)
        return 1
    print("\nPASS: no serious or critical violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
