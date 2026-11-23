"""Automated accessibility checks with axe-core on every page.

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

CREATOR_PAGES = [
    ("welcome", "/welcome"),
    ("dashboard", "/"),
    ("today", "/today"),
    ("mission", "/missions/m_0214"),
    ("remote", "/remote"),
    ("clips", "/clips"),
    ("clip", "/clips/c_0001"),
    ("clip-rendering", "/clips/c_0002"),
    ("export", "/export/c_0001"),
    ("live", "/live"),
    ("results", "/results"),
    ("history", "/history"),
    ("settings", "/settings"),
    ("help", "/help"),
    ("leaderboard", "/leaderboard"),
    ("public-mission", "/m/m_0214"),
    ("styleguide", "/styleguide"),
    ("terms", "/terms"),
    ("privacy", "/privacy"),
]

ADMIN_PAGES = [
    ("admin", "/admin"),
    ("admin-games", "/admin/games"),
    ("admin-game", "/admin/games/g_1"),
    ("admin-pool", "/admin/pool"),
    ("admin-projects", "/admin/projects"),
    ("admin-studio", "/admin/studio"),
    ("admin-users", "/admin/users"),
    ("admin-invites", "/admin/invites"),
    ("admin-jobs", "/admin/jobs"),
    ("admin-ai", "/admin/ai"),
    ("admin-models", "/admin/models"),
    ("admin-wizard", "/admin/wizard"),
    ("admin-calendar", "/admin/calendar"),
    ("admin-long-form", "/admin/long-form"),
    ("admin-audit", "/admin/audit"),
    ("admin-templates", "/admin/templates"),
    ("admin-setup", "/admin/setup"),
]

SIZES = [("phone", 390, 844), ("desktop", 1280, 900)]


def main() -> int:
    report = {}
    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for size_name, width, height in SIZES:
            for theme in ("dark", "light"):
                for role, pages in (("creator", CREATOR_PAGES), ("admin", ADMIN_PAGES)):
                    context = browser.new_context(viewport={"width": width, "height": height})
                    name = "Admin" if role == "admin" else "Axe"
                    csrf = ""
                    for attempt in range(4):
                        try:
                            csrf = context.request.get(f"{BASE}/api/auth/csrf", timeout=20000).json()["csrf"]
                            break
                        except Exception:
                            if attempt == 3:
                                raise
                            context.request.get(f"{BASE}/api/health", timeout=20000)
                    context.request.post(
                        f"{BASE}/api/auth/dev/sign-in",
                        data={"display_name": name},
                        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
                    )
                    page = context.new_page()
                    page.set_default_timeout(20000)
                    for page_name, path in pages:
                        key = f"{size_name}-{theme}-{page_name}"
                        try:
                            page.goto(f"{BASE}{path}?theme={theme}", wait_until="domcontentloaded")
                            try:
                                page.wait_for_selector('[aria-busy="true"]', state="detached", timeout=8000)
                            except Exception:
                                pass
                            page.wait_for_timeout(600)
                            page.add_script_tag(path=str(AXE))
                            results = page.evaluate(
                                """() => axe.run(document, { resultTypes: ['violations'] })"""
                            )
                            violations = [
                                {"id": v["id"], "impact": v["impact"], "nodes": len(v["nodes"]), "help": v["help"]}
                                for v in results["violations"]
                                if v["impact"] in ("serious", "critical")
                            ]
                            report[key] = violations
                            if violations:
                                failed.append(f"{key}: {violations}")
                        except Exception as exc:
                            report[key] = [{"id": "harness-error", "impact": "serious", "nodes": 1, "help": str(exc)[:200]}]
                            failed.append(f"{key}: harness error {exc}")
                            try:
                                page.goto(f"{BASE}/signin?theme={theme}", wait_until="domcontentloaded")
                            except Exception:
                                pass
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
