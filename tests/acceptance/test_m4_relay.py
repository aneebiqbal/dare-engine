"""M4: push a stream over RTMP, mark Start and Done mid-stream, get a Short.

Uses the synthetic stand-in because `fixtures/stream_10min.mp4` is missing, so
the relay path is proven, not the clip quality. M4 is not accepted.
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


def call(opener, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with opener.open(req, timeout=60) as resp:
        return json.loads(resp.read())


def _seed_candidate():
    code = (
        "import json;from app import db;"
        "card=json.load(open('app/llm_recorded.json'))['cards'][0];card['id']='m_m4';"
        "conn=db.connect();cur=conn.cursor();"
        "cur.execute(\"INSERT INTO missions (id,card,status) VALUES ('m_m4',%s,'candidate') "
        "ON CONFLICT (id) DO UPDATE SET status='candidate', card=EXCLUDED.card\","
        "(json.dumps(card),));conn.commit()"
    )
    subprocess.run(["docker", "compose", "exec", "-T", "api", "python", "-c", code],
                   cwd=ROOT, check=True, capture_output=True)


def test_stream_produces_a_short_before_it_ends():
    _seed_candidate()
    opener = _opener(f"M4 {int(time.time())}")
    mission_id = call(opener, "GET", "/admin/pool")[0]["id"]
    call(opener, "POST", f"/admin/pool/{mission_id}/approve", {})

    stream = call(opener, "POST", "/streams", {"title": "m4"})
    push = subprocess.Popen(
        [
            "ffmpeg", "-re", "-stream_loop", "3", "-i", str(STANDIN),
            "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
            "-f", "flv", stream["rtmp_url"],
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        # The Live page polls this endpoint.
        connected = False
        for _ in range(20):
            time.sleep(1)
            status = call(opener, "GET", f"/streams/{stream['id']}/status")
            if status.get("connected"):
                connected = True
                break
        assert connected, "relay never reported the stream as connected"

        assignment = call(opener, "POST", "/assignments", {"mission_id": mission_id})
        time.sleep(3)
        call(opener, "POST", "/marks", {
            "assignment_id": assignment["id"], "kind": "start", "stream_time": 8,
        })
        time.sleep(8)
        done_at = time.time()
        call(opener, "POST", "/marks", {
            "assignment_id": assignment["id"], "kind": "done",
            "stream_time": 16, "result": "0:41",
        })

        deadline = time.time() + 300
        clips = []
        while time.time() < deadline:
            clips = call(opener, "GET", "/clips")
            if clips and clips[0]["state"] == "ready":
                break
            time.sleep(3)

        assert clips and clips[0]["state"] == "ready", f"clip never rendered: {clips[:1]}"
        seconds = time.time() - done_at
        print(f"Done -> finished file: {seconds:.1f}s")
        assert seconds < 180, f"took too long: {seconds:.1f}s"
        assert clips[0]["duration_seconds"] and clips[0]["duration_seconds"] < 60
    finally:
        push.terminate()
