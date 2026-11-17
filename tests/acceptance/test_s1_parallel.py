"""S1: a killed worker's jobs are recovered, with no duplicate clips."""
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


def _opener(name):
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req = urllib.request.Request(
        f"{API}/auth/dev/sign-in",
        data=json.dumps({"display_name": name}).encode(),
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


def _upload(opener, mission_id, n=3):
    boundary = "----s1"
    marks = json.dumps([
        {"mission_id": mission_id, "start": 5 + i * 5, "end": 20 + i * 5, "result": f"0:{40 + i}"}
        for i in range(n)
    ])
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"rec.mp4\"\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + STANDIN.read_bytes() + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"marks\"\r\n\r\n{marks}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    return call(opener, "POST", "/uploads", raw=body, ctype=f"multipart/form-data; boundary={boundary}")


def test_killing_a_worker_mid_render_still_finishes_three_clips():
    name = f"S1 {int(time.time())}"
    opener = _opener(name)
    call(opener, "POST", "/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    pool = call(opener, "GET", "/admin/pool")
    if not pool:
        code = (
            "import json;from app import db;"
            "card=json.load(open('app/llm_recorded.json'))['cards'][0];card['id']='m_s1';"
            "conn=db.connect();cur=conn.cursor();"
            "cur.execute(\"INSERT INTO missions (id,card,status) VALUES ('m_s1',%s,'candidate') "
            "ON CONFLICT (id) DO UPDATE SET status='candidate', card=EXCLUDED.card\","
            "(json.dumps(card),));conn.commit()"
        )
        subprocess.run(["docker", "compose", "exec", "-T", "api", "python", "-c", code],
                       cwd=ROOT, check=True, capture_output=True)
    mission_id = call(opener, "GET", "/admin/pool")[0]["id"]
    call(opener, "POST", f"/admin/pool/{mission_id}/approve", {})
    _upload(opener, mission_id)

    def states():
        return [c["state"] for c in call(opener, "GET", "/clips")]

    deadline = time.time() + 300
    while time.time() < deadline and not any(s == "ready" for s in states()):
        time.sleep(3)

    # Kill the worker mid-render, then bring it back.
    subprocess.run(["docker", "kill", "clipdesk-worker-1"], capture_output=True)
    subprocess.run(["docker", "compose", "up", "-d", "worker"], cwd=ROOT, capture_output=True)
    time.sleep(6)

    deadline = time.time() + 600
    while time.time() < deadline:
        clips = call(opener, "GET", "/clips")
        if len(clips) >= 3 and all(c["state"] == "ready" for c in clips[:3]):
            break
        time.sleep(5)

    clips = call(opener, "GET", "/clips")
    assert len(clips) == 3, f"expected exactly three clips, got {len(clips)}"
    assert all(c["state"] == "ready" for c in clips)
    assert len({c["id"] for c in clips}) == 3, "duplicate clips"
