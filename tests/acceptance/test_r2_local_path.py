"""R2 / M3: a local recording plus three marks yields three real Shorts.

Uses the synthetic stand-in because `fixtures/stream_10min.mp4` is missing, so
this proves the path, not the output quality. M3 is not accepted.
"""
import http.cookiejar
import json
import pathlib
import subprocess
import time
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
API = "http://localhost:8000"
STANDIN = ROOT / "tests/fixtures/standin_speech_45s.mp4"


def _opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


@pytest.fixture(scope="module")
def session():
    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "db", "psql", "-U", "clipdesk", "-d", "clipdesk",
            "-c", "TRUNCATE clips, jobs, marks, assignments, streams, missions, daily_sets, sessions "
                 "RESTART IDENTITY CASCADE;",
        ],
        cwd=ROOT, check=True, capture_output=True,
    )
    opener = _opener()
    req = urllib.request.Request(
        f"{API}/auth/dev/sign-in",
        data=json.dumps({"display_name": "Clip Runner"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=30) as resp:
        json.loads(resp.read())
    return opener


def call(opener, method, path, body=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={"Content-Type": ctype} if data else {},
    )
    with opener.open(req, timeout=180) as resp:
        return json.loads(resp.read())


def test_marks_require_an_assignment(session):
    call(session, "POST", "/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    pool = call(session, "GET", "/admin/pool")
    mission_id = pool[0]["id"]
    call(session, "POST", f"/admin/pool/{mission_id}/approve", {})
    assignment = call(session, "POST", "/assignments", {"mission_id": mission_id})
    mark = call(session, "POST", "/marks", {
        "assignment_id": assignment["id"], "kind": "start", "stream_time": 12.5,
    })
    assert mark["stream_time"] == 12.5
    with pytest.raises(urllib.error.HTTPError) as exc:
        call(session, "POST", "/marks", {"assignment_id": assignment["id"], "kind": "pause"})
    assert exc.value.code == 422


def test_three_marks_yield_three_real_shorts(session):
    pool = call(session, "GET", "/admin/pool")
    if not pool:
        call(session, "POST", "/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
        pool = call(session, "GET", "/admin/pool")
    mission_id = pool[0]["id"]
    call(session, "POST", f"/admin/pool/{mission_id}/approve", {})

    boundary = "----clipdesk-r2"
    video = STANDIN.read_bytes()
    marks = json.dumps([
        {"mission_id": mission_id, "start": 5, "end": 20, "result": "0:41"},
        {"mission_id": mission_id, "start": 20, "end": 35, "result": "0:52"},
        {"mission_id": mission_id, "start": 10, "end": 25, "result": "pass"},
    ])
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"rec.mp4\"\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + video + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"marks\"\r\n\r\n{marks}\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    uploaded = call(session, "POST", "/uploads", raw=body, ctype=f"multipart/form-data; boundary={boundary}")
    assert uploaded["count"] == 3

    deadline = time.time() + 420
    clips = []
    while time.time() < deadline:
        clips = call(session, "GET", "/clips")
        if len(clips) >= 3 and all(c["state"] == "ready" for c in clips):
            break
        time.sleep(5)

    assert len(clips) >= 3, f"clips never finished: {[c['state'] for c in clips]}"
    assert all(c["state"] == "ready" for c in clips[:3])
    assert all(c["duration_seconds"] and c["duration_seconds"] < 60 for c in clips[:3])
    assert all(c["download_url"] for c in clips[:3])

    # The download is a real file.
    with session.open(f"{API}{clips[0]['download_url']}", timeout=60) as resp:
        data = resp.read()
    assert len(data) > 1000
