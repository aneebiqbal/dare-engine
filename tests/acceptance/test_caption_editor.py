"""Part 4: edit caption text/timing on a rendered clip without re-transcribing."""
import time

import pytest

from helpers import ROOT, make_admin, seed_mission, truncate

FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"


@pytest.fixture(scope="module")
def admin():
    truncate(
        "clips", "jobs", "studio_candidates", "studio_recordings", "projects",
        "attempts", "marks", "assignments", "streams",
    )
    return make_admin()


@pytest.fixture(scope="module")
def clip(admin):
    mission = seed_mission(admin)
    boundary = "----caption-test"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="standin.mp4"\r\nContent-Type: video/mp4\r\n\r\n'
    ).encode() + FIXTURE.read_bytes() + (f"\r\n--{boundary}--\r\n").encode()
    rec = admin.call(
        "POST", "/studio/upload", raw=body,
        ctype=f"multipart/form-data; boundary={boundary}",
    )
    admin.post("/studio/detect", {"recording_id": rec["recording_id"], "top_n": 3})
    detail = None
    for _ in range(90):
        time.sleep(2)
        detail = admin.get(f"/studio/recordings/{rec['recording_id']}")
        if detail["candidates"]:
            break
    assert detail and detail["candidates"]
    candidate = detail["candidates"][0]
    gen = admin.post("/studio/generate", {
        "recording_id": rec["recording_id"],
        "mission_id": mission,
        "windows": [{
            "candidate_id": candidate["id"],
            "start": candidate["start"],
            "end": candidate["end"],
            "template_id": "cold_open",
        }],
    })
    clip_id = gen["clips"][0]
    for _ in range(90):
        time.sleep(3)
        row = admin.get(f"/clips/{clip_id}")
        if row["state"] in ("ready", "failed"):
            break
    assert row["state"] == "ready", row
    return clip_id


def test_captions_come_from_the_transcript(admin, clip):
    res = admin.get(f"/clips/{clip}/captions")
    assert res["source"] == "transcript"
    assert res["captions"]
    assert all(c["start"] < c["end"] for c in res["captions"])


def test_editing_captions_stores_an_override_and_rerenders(admin, clip):
    before = admin.get(f"/clips/{clip}")
    transcript_words = len(before["transcript"] or [])
    override = [
        {"start": 0.0, "end": 1.5, "text": "EDITED OPEN"},
        {"start": 1.5, "end": 3.0, "text": "SECOND LINE"},
    ]
    admin.patch(f"/clips/{clip}", {"captions": override})
    row = {}
    for _ in range(90):
        time.sleep(3)
        row = admin.get(f"/clips/{clip}")
        if row["state"] in ("ready", "failed"):
            break
    assert row["state"] == "ready", row
    res = admin.get(f"/clips/{clip}/captions")
    assert res["source"] == "override"
    assert res["captions"] == override
    # The transcript is untouched: the edit never re-transcribed.
    assert len(row["transcript"] or []) == transcript_words


def test_bad_captions_are_rejected(admin, clip):
    with pytest.raises(Exception):
        admin.patch(f"/clips/{clip}", {"captions": [{"start": 3, "end": 1, "text": "bad"}]})


def test_engine_activity_is_logged(admin, clip):
    items = admin.get("/admin/engine-events?limit=100")["items"]
    kinds = {i["kind"] for i in items}
    assert "job_start" in kinds
    assert "job_done" in kinds
    assert "cleanup" in kinds
    assert any(i["detail"] and "render_clip" in i["detail"] for i in items)
