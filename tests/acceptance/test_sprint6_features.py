"""Sprint 6 Part D/B: resumable upload, trim re-render, export package, AI rows."""
import io
import json
import time
import urllib.request
import zipfile

import pytest

from helpers import (
    ROOT,
    create_user_with_invite,
    make_admin,
    seed_mission,
    sql,
    truncate,
    upload_recording,
)

STANDIN = ROOT / "tests/fixtures/standin_speech_45s.mp4"


@pytest.fixture(scope="module")
def seeded():
    truncate(
        "users", "invites", "sessions", "login_attempts", "password_resets",
        "missions", "assignments", "marks", "clips", "jobs", "streams", "attempts",
        "daily_sets", "ai_usage", "tour_progress", "user_settings",
    )
    admin = make_admin()
    mission = seed_mission(admin)
    creator = create_user_with_invite(admin, "features@example.com", name="Features")
    return creator, mission


def _wait_ready(client, clip_id, timeout=420):
    deadline = time.time() + timeout
    while time.time() < deadline:
        clip = client.get(f"/clips/{clip_id}")
        if clip["state"] == "ready":
            return clip
        time.sleep(4)
    pytest.skip("clip did not render in time")


def test_resumable_chunked_upload(seeded):
    creator, mission = seeded
    start = creator.post("/uploads/start", {})
    data = STANDIN.read_bytes()
    chunk = start["chunk_size"]
    for i in range(0, len(data), chunk):
        creator.call("PUT", f"/uploads/{start['upload_id']}/chunks/{i // chunk}", raw=data[i : i + chunk],
                     ctype="application/octet-stream")
    result = creator.post(
        f"/uploads/{start['upload_id']}/complete",
        {"marks": [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}],
         "filename": "recording.mp4"},
    )
    assert result["count"] == 1
    assert len(creator.get("/clips")["items"]) == 1


def test_export_package_contains_video_thumb_and_metadata(seeded):
    creator, mission = seeded
    uploaded = upload_recording(creator, [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}])
    clip = _wait_ready(creator, uploaded["clips"][0])
    creator.post(f"/clips/{clip['id']}/export", {
        "title": "My Short", "description": "A description", "tags": ["one", "two"],
    })
    with creator.opener.open(f"http://localhost:8000/clips/{clip['id']}/export", timeout=60) as resp:
        blob = resp.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = set(zf.namelist())
        assert {"short.mp4", "thumbnail.jpg", "metadata.json"} <= names
        meta = json.loads(zf.read("metadata.json"))
        assert meta["title"] == "My Short"
        assert meta["tags"] == ["one", "two"]


def test_trim_re_renders_with_the_transcript_cached(seeded):
    creator, mission = seeded
    uploaded = upload_recording(creator, [{"mission_id": mission, "start": 5, "end": 30, "result": "0:41"}])
    clip = _wait_ready(creator, uploaded["clips"][0])
    assert clip["transcript"] is not None
    creator.post(f"/clips/{clip['id']}/trim", {"start": 8, "end": 25})
    again = _wait_ready(creator, clip["id"])
    assert again["state"] == "ready"
    assert again["transcript"]
    job = sql(
        "SELECT payload FROM jobs WHERE payload->>'clip_id'='%s' AND payload->>'trim_start' IS NOT NULL LIMIT 1;"
        % clip["id"]
    ).strip()
    assert job and json.loads(job)["trim_start"] == 8.0


def test_ai_rows_are_logged(seeded):
    admin = make_admin()
    admin.post("/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    usage = admin.get("/admin/ai-usage")["items"]
    assert usage, "the mission writer call was not logged"
    assert all(u["provider"] for u in usage)
    assert all("latency_ms" in u for u in usage)
