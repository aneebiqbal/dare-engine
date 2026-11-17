"""R2 / M3: a local recording plus three marks yields three real Shorts.

Uses the synthetic stand-in because `fixtures/stream_10min.mp4` is missing, so
this proves the path, not the output quality. M3 is not accepted.
"""
import time
import urllib.error

import pytest

from helpers import make_admin, sign_up, truncate, upload_recording


@pytest.fixture(scope="module")
def seeded():
    truncate(
        "users", "invites", "sessions", "login_attempts", "password_resets",
        "missions", "assignments", "marks", "clips", "jobs", "streams", "attempts",
        "daily_sets", "ai_usage", "tour_progress", "user_settings",
    )
    admin = make_admin()
    admin.post("/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    mission_id = admin.get("/admin/pool")["items"][0]["id"]
    admin.post(f"/admin/pool/{mission_id}/approve", {})
    creator = sign_up("clip-runner@example.com", name="Clip Runner")
    return creator, mission_id


def test_marks_require_an_assignment(seeded):
    creator, mission_id = seeded
    assignment = creator.post("/assignments", {"mission_id": mission_id})
    mark = creator.post("/marks", {
        "assignment_id": assignment["id"], "kind": "start", "stream_time": 12.5,
    })
    assert mark["stream_time"] == 12.5
    with pytest.raises(urllib.error.HTTPError) as exc:
        creator.post("/marks", {"assignment_id": assignment["id"], "kind": "pause"})
    assert exc.value.code == 422


def test_three_marks_yield_three_real_shorts(seeded):
    creator, mission_id = seeded
    uploaded = upload_recording(creator, [
        {"mission_id": mission_id, "start": 5, "end": 20, "result": "0:41"},
        {"mission_id": mission_id, "start": 20, "end": 35, "result": "0:52"},
        {"mission_id": mission_id, "start": 10, "end": 25, "result": "pass"},
    ])
    assert uploaded["count"] == 3

    deadline = time.time() + 420
    clips = []
    while time.time() < deadline:
        clips = creator.get("/clips")["items"]
        if len(clips) >= 3 and all(c["state"] == "ready" for c in clips):
            break
        time.sleep(5)

    assert len(clips) >= 3, f"clips never finished: {[c['state'] for c in clips]}"
    assert all(c["state"] == "ready" for c in clips[:3])
    assert all(c["duration_seconds"] and c["duration_seconds"] < 60 for c in clips[:3])
    assert all(c["download_url"] for c in clips[:3])

    with creator.opener.open(f"http://localhost:8000{clips[0]['download_url']}", timeout=60) as resp:
        data = resp.read()
    assert len(data) > 1000
