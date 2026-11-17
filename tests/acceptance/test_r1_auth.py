"""Sprint 6 Part A: real accounts, roles, invites, lockout, reset and CSRF."""
import http.cookiejar
import json
import pathlib
import subprocess
import urllib.error
import urllib.request

import pytest

from helpers import API, ROOT, Client, dev_sign_in, make_admin, make_invite, sign_up, sql, truncate


@pytest.fixture(autouse=True)
def clean_state():
    truncate(
        "users", "invites", "login_attempts", "password_resets", "missions", "jobs",
        "sessions", "assignments", "marks", "clips", "streams", "attempts",
        "ai_usage", "audit_log", "tour_progress", "user_settings", "voice_overs",
        "exports", "posts", "metrics", "daily_sets",
    )
    yield


def _anonymous() -> Client:
    return Client()


def test_creator_cannot_reach_admin_routes():
    creator = sign_up("creator@example.com")
    with pytest.raises(urllib.error.HTTPError) as exc:
        creator.get("/admin/users")
    assert exc.value.code == 403
    with pytest.raises(urllib.error.HTTPError) as exc:
        creator.post("/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    assert exc.value.code == 403


def test_admin_can_reach_admin_routes():
    admin = make_admin()
    assert len(admin.get("/admin/users")["items"]) >= 1
    # Regression: /admin/jobs used to fail with tuple + list.
    assert "items" in admin.get("/admin/jobs")


def test_sign_up_requires_an_invite_by_default():
    client = Client()
    with pytest.raises(urllib.error.HTTPError) as exc:
        client.post("/auth/sign-up", {
            "email": "nobody@example.com", "password": "password-123", "display_name": "Nobody",
        })
    assert exc.value.code == 403


def test_invite_is_single_use():
    admin = make_admin()
    code = make_invite(admin, "once@example.com")
    first = Client()
    first.post("/auth/sign-up", {
        "email": "once@example.com", "password": "password-123", "display_name": "Once", "invite_code": code,
    })
    second = Client()
    with pytest.raises(urllib.error.HTTPError) as exc:
        second.post("/auth/sign-up", {
            "email": "twice@example.com", "password": "password-123", "display_name": "Twice", "invite_code": code,
        })
    assert exc.value.code == 403


def test_state_changing_route_requires_csrf():
    client = Client()
    # No CSRF cookie fetched: the token is missing.
    req = urllib.request.Request(
        f"{API}/auth/sign-in",
        data=json.dumps({"email": "x@example.com", "password": "password-123"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        client.opener.open(req, timeout=30)
    assert exc.value.code == 403


def test_locked_account_stays_locked():
    admin = make_admin()
    code = make_invite(admin, "locked@example.com")
    client = Client()
    client.post("/auth/sign-up", {
        "email": "locked@example.com", "password": "password-123", "display_name": "Locked", "invite_code": code,
    })
    for _ in range(10):
        with pytest.raises(urllib.error.HTTPError):
            client.post("/auth/sign-in", {"email": "locked@example.com", "password": "wrong-password-123"})
    # Even the correct password is refused while locked.
    with pytest.raises(urllib.error.HTTPError) as exc:
        client.post("/auth/sign-in", {"email": "locked@example.com", "password": "password-123"})
    assert exc.value.code == 423
    row = sql("SELECT locked_until IS NOT NULL FROM users WHERE email='locked@example.com'")
    assert row.strip() == "t"


def test_password_reset_link_works_once():
    admin = make_admin()
    creator = sign_up("reset@example.com")
    user_id = creator.get("/me")["user"]["id"]
    url = admin.post(f"/admin/users/{user_id}/reset-link", {})["url"]
    token = url.split("token=")[1]
    client = Client()
    client.post("/auth/reset-password", {"token": token, "new_password": "new-password-123"})
    # The link is one-time.
    with pytest.raises(urllib.error.HTTPError) as exc:
        client.post("/auth/reset-password", {"token": token, "new_password": "other-password-123"})
    assert exc.value.code == 400
    # The new password signs in.
    signed = Client()
    signed.post("/auth/sign-in", {"email": "reset@example.com", "password": "new-password-123"})
    assert signed.get("/me")["user"]["email"] == "reset@example.com"


def test_sign_out_everywhere_ends_other_sessions():
    client = sign_out = sign_up("everywhere@example.com")
    other = Client()
    other.post("/auth/sign-in", {"email": "everywhere@example.com", "password": "creator-password-123"})
    assert other.get("/me")["user"]["email"] == "everywhere@example.com"
    client.post("/auth/sign-out-all", {})
    with pytest.raises(urllib.error.HTTPError) as exc:
        other.get("/me")
    assert exc.value.code == 401


def test_dev_sign_in_is_off_by_default():
    # The compose default sets DEV_AUTH_ENABLED=false; the test run sets it true.
    # Prove the guard independently of the flag by checking the production guard.
    proc = subprocess.run(
        ["docker", "compose", "run", "--rm", "-e", "DEV_AUTH_ENABLED=true", "-e", "APP_ENV=production", "api"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode != 0
    assert "DEV_AUTH_ENABLED" in (proc.stdout + proc.stderr)


def test_anonymous_pages_are_refused():
    client = _anonymous()
    for path in ["/today", "/clips", "/history", "/settings", "/results"]:
        with pytest.raises(urllib.error.HTTPError) as exc:
            client.get(path)
        assert exc.value.code == 401, path
