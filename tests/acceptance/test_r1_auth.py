"""R1: development sign-in creates real users and sessions, and ownership holds."""
import http.cookiejar
import json
import pathlib
import subprocess
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
API = "http://localhost:8000"


def _opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def sign_in(name: str):
    opener = _opener()
    req = urllib.request.Request(
        f"{API}/auth/dev/sign-in",
        data=json.dumps({"display_name": name}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=30) as resp:
        return opener, json.loads(resp.read())


def call(opener, method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with opener.open(req, timeout=30) as resp:
        return json.loads(resp.read())


@pytest.fixture(scope="module")
def two_users():
    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "db", "psql", "-U", "clipdesk", "-d", "clipdesk",
            "-c", "TRUNCATE sessions, assignments, marks, missions, daily_sets CASCADE; "
                 "DELETE FROM users WHERE google_subject LIKE 'dev:%';",
        ],
        cwd=ROOT, check=True, capture_output=True,
    )
    alice, _ = sign_in("Alice")
    bob, _ = sign_in("Bob")
    return alice, bob


def test_real_users_and_sessions(two_users):
    alice, bob = two_users
    assert call(alice, "GET", "/me")["user"]["display_name"] == "Alice"
    assert call(bob, "GET", "/me")["user"]["display_name"] == "Bob"


def test_users_only_see_their_own_accepted_missions(two_users):
    alice, bob = two_users
    call(alice, "POST", "/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    pool = call(alice, "GET", "/admin/pool")
    mission_id = pool[0]["id"]
    call(alice, "POST", f"/admin/pool/{mission_id}/approve", {})

    call(alice, "POST", "/assignments", {"mission_id": mission_id})
    assert mission_id in call(alice, "GET", "/today")["accepted"]
    assert mission_id not in call(bob, "GET", "/today")["accepted"]


def test_anonymous_requests_are_refused():
    with pytest.raises(urllib.error.HTTPError) as exc:
        call(_opener(), "GET", "/today")
    assert exc.value.code == 401


def test_production_refuses_dev_auth():
    proc = subprocess.run(
        ["docker", "compose", "run", "--rm", "-e", "DEV_AUTH_ENABLED=true", "-e", "APP_ENV=production", "api"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode != 0
    assert "DEV_AUTH_ENABLED" in (proc.stdout + proc.stderr)
