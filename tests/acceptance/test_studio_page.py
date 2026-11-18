"""Part C: the studio screen drives a recording to finished clips with no
timestamp entry, and the compute-path indicator reflects the real run."""
import pathlib

from playwright.sync_api import sync_playwright

from helpers import ROOT, make_admin, seed_mission, truncate

FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"
WEB = "http://localhost:3100"


def test_studio_find_moments_and_generate():
    truncate(
        "clips", "jobs", "studio_candidates", "studio_recordings",
        "attempts", "marks", "assignments", "streams",
    )
    admin = make_admin()
    seed_mission(admin)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            page.goto(f"{WEB}/signin", wait_until="networkidle")
            page.click('[data-testid="signin-admin"]')
            page.wait_for_selector("text=Your day", timeout=30000)

            page.goto(f"{WEB}/admin/studio", wait_until="domcontentloaded")
            page.wait_for_selector('[data-testid="studio-file"]', timeout=30000)
            page.set_input_files('[data-testid="studio-file"]', str(FIXTURE))
            page.click('[data-testid="studio-upload"]')
            page.wait_for_selector('[data-testid="studio-find"]:not([disabled])', timeout=30000)

            page.click('[data-testid="studio-find"]')
            page.wait_for_selector('[data-testid="studio-candidate-0"]', timeout=180000)

            compute = page.text_content('[data-testid="studio-compute"]') or ""
            assert "whisper" in compute

            page.click('[data-testid="studio-accept-top"]')
            page.click('[data-testid="studio-generate"]')
            page.wait_for_selector('[data-testid="studio-clip-0"]', timeout=240000)
        finally:
            browser.close()
