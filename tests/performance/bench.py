"""Measure wall-clock time for three clips from one upload.

Run with the stack up. Prints one CSV row so docs/performance.md can be built
from real measurements.

    WORKER_CONCURRENCY=1 python tests/performance/bench.py
"""
import http.cookiejar
import json
import os
import pathlib
import subprocess
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
API = "http://localhost:8000"
STANDIN = ROOT / "tests/fixtures/standin_speech_45s.mp4"


def _opener(name=None):
    name = name or f"Bench {os.environ.get('WORKER_CONCURRENCY', 'x')} {int(time.time())}"
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


def _ensure_mission(opener):
    pool = call(opener, "GET", "/admin/pool")
    if pool:
        mission_id = pool[0]["id"]
    else:
        mission_id = "m_bench"
        code = (
            "import json;from app import db;"
            "card=json.load(open('app/llm_recorded.json'))['cards'][0];card['id']='m_bench';"
            "conn=db.connect();cur=conn.cursor();"
            "cur.execute(\"INSERT INTO missions (id,card,status) VALUES ('m_bench',%s,'candidate') "
            "ON CONFLICT (id) DO UPDATE SET status='candidate', card=EXCLUDED.card\","
            "(json.dumps(card),));conn.commit()"
        )
        subprocess.run(
            ["docker", "compose", "exec", "-T", "api", "python", "-c", code],
            cwd=ROOT, check=True, capture_output=True,
        )
    call(opener, "POST", f"/admin/pool/{mission_id}/approve", {})
    return mission_id


def main() -> None:
    opener = _opener()
    mission_id = _ensure_mission(opener)

    boundary = "----bench"
    marks = json.dumps([
        {"mission_id": mission_id, "start": 5, "end": 20, "result": "0:41"},
        {"mission_id": mission_id, "start": 20, "end": 35, "result": "0:52"},
        {"mission_id": mission_id, "start": 10, "end": 25, "result": "pass"},
    ])
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"rec.mp4\"\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + STANDIN.read_bytes() + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"marks\"\r\n\r\n{marks}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    before = len(call(opener, "GET", "/clips"))
    call(opener, "POST", "/uploads", raw=body, ctype=f"multipart/form-data; boundary={boundary}")

    started = time.time()
    deadline = started + 600
    while time.time() < deadline:
        clips = call(opener, "GET", "/clips")
        fresh = clips[:3]
        if len(fresh) >= 3 and all(c["state"] == "ready" for c in fresh):
            break
        time.sleep(2)
    elapsed = time.time() - started
    concurrency = os.environ.get("WORKER_CONCURRENCY", "default")
    print(f"concurrency={concurrency} clips=3 wall_seconds={elapsed:.1f}")


if __name__ == "__main__":
    main()
