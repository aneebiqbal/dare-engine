"""R4 / M7: real Daily Mission attempts rank correctly on the public page."""
import http.cookiejar
import json
import pathlib
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


def _upload(opener, mission_id, result):
    boundary = "----r4"
    marks = json.dumps([{"mission_id": mission_id, "start": 5, "end": 20, "result": result}])
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"rec.mp4\"\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + STANDIN.read_bytes() + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"marks\"\r\n\r\n{marks}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    return call(opener, "POST", "/uploads", raw=body, ctype=f"multipart/form-data; boundary={boundary}")


@pytest.fixture(scope="module")
def mission():
    opener = _opener("Editor")
    call(opener, "POST", "/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    pool = call(opener, "GET", "/admin/pool")
    mission_id = pool[0]["id"]
    call(opener, "POST", f"/admin/pool/{mission_id}/approve", {})
    return mission_id


def test_two_users_rank_on_the_public_page(mission):
    _upload(_opener("R4 Alice"), mission, "41")
    _upload(_opener("R4 Bob"), mission, "52")

    deadline = time.time() + 300
    rows = []
    while time.time() < deadline:
        rows = call(_opener("R4 Alice"), "GET", f"/missions/{mission}/leaderboard")
        if len(rows) >= 2:
            break
        time.sleep(5)

    assert [r["rank"] for r in rows[:2]] == [1, 2]
    assert rows[0]["result_value"] == 41.0
    assert rows[1]["result_value"] == 52.0

    page = call(_opener("R4 Alice"), "GET", f"/m/{mission}")
    assert page["attempts"][0]["rank"] == 1
    assert page["card"]["id"] == mission
