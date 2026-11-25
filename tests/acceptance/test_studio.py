"""Parts A/C/E: upload, auto-detect, generate, and read back a real clip."""
import json
import pathlib
import subprocess
import time

import pytest

from helpers import ROOT, make_admin, seed_mission, truncate

FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"


@pytest.fixture(scope="module")
def admin():
    truncate(
        "clips", "jobs", "studio_candidates", "studio_recordings",
        "attempts", "marks", "assignments", "streams",
    )
    return make_admin()


@pytest.fixture(scope="module")
def mission(admin):
    return seed_mission(admin)


def _upload(admin, filename: str = "standin.mp4") -> dict:
    boundary = "----studio-test"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{filename}"\r\nContent-Type: video/mp4\r\n\r\n'
    ).encode() + FIXTURE.read_bytes() + (f"\r\n--{boundary}--\r\n").encode()
    return admin.call(
        "POST", "/studio/upload", raw=body,
        ctype=f"multipart/form-data; boundary={boundary}",
    )


def _detect(admin, recording_id: str) -> dict:
    admin.post("/studio/detect", {"recording_id": recording_id, "top_n": 3})
    for _ in range(90):
        time.sleep(2)
        detail = admin.get(f"/studio/recordings/{recording_id}")
        if detail["candidates"] and detail["compute"]["whisper_device"]:
            return detail
    pytest.fail("detection never finished")


def test_upload_reports_specs(admin):
    res = _upload(admin)
    assert res["duration_seconds"] > 0
    assert res["width"] == 1920 and res["height"] == 1080


def test_detect_returns_ranked_candidates_with_reasons(admin):
    detail = _detect(admin, _upload(admin)["recording_id"])
    assert detail["compute"]["whisper_device"] in ("cpu", "cuda", "mlx")
    assert detail["candidates"]
    for candidate in detail["candidates"]:
        assert candidate["start"] < candidate["end"]
        assert candidate["score"] > 0
        assert candidate["reasons"]


def test_generate_renders_a_real_clip_with_the_grammar(admin, mission):
    detail = _detect(admin, _upload(admin)["recording_id"])
    candidate = detail["candidates"][0]
    gen = admin.post("/studio/generate", {
        "recording_id": detail["recording"]["id"],
        "mission_id": mission,
        "windows": [{
            "candidate_id": candidate["id"],
            "start": candidate["start"],
            "end": candidate["end"],
            "template_id": "cold_open",
        }],
    })
    clip_id = gen["clips"][0]
    clip = {}
    for _ in range(90):
        time.sleep(3)
        clip = admin.get(f"/clips/{clip_id}")
        if clip["state"] in ("ready", "failed"):
            break
    assert clip["state"] == "ready", clip
    assert clip["duration_seconds"] < 60

    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "cat",
         f"/data/storage/clips/{clip_id}/metadata.json"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    meta = json.loads(out)
    assert meta["template"] == "cold_open"
    assert meta["beats"][-1]["kind"] == "payoff"
    assert meta["beats"][-1]["length"] >= max(b["length"] for b in meta["beats"])
