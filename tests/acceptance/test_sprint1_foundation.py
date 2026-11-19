"""Sprint 1 foundation: security (F3) and retention (F2)."""
import pathlib
import subprocess
import time
import urllib.error

from helpers import (
    ROOT,
    make_admin,
    seed_mission,
    sign_up,
    sql,
    storage_keys,
    upload_recording,
)

STANDIN = ROOT / "tests/fixtures/standin_speech_45s.mp4"
SUFFIX = int(time.time())


def _email(name: str) -> str:
    return f"{name}-{SUFFIX}@example.com"
API = "http://localhost:8000"


def _wait_ready(client, clip_id, timeout=420):
    deadline = time.time() + timeout
    while time.time() < deadline:
        clip = client.get(f"/clips/{clip_id}")
        if clip["state"] == "ready":
            return clip
        time.sleep(4)
    raise AssertionError("clip did not render in time")


# --------------------------------------------------------------------- F3


def test_upload_chunk_endpoints_require_a_session():
    from helpers import Client

    anon = Client()
    # GET needs no CSRF; the mutation paths get a CSRF cookie first, then must
    # still be refused because there is no session.
    for method, path, kwargs in [
        ("POST", "/uploads/start", {"body": {}}),
        ("GET", "/uploads/anything", {}),
        ("PUT", "/uploads/anything/chunks/0", {"raw": b"x", "ctype": "application/octet-stream"}),
    ]:
        try:
            anon.call(method, path, **kwargs)
            raise AssertionError(f"{method} {path} should be refused")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401, (method, path, exc.code)


def test_a_stolen_database_session_value_does_not_work():
    client = sign_up(_email("stolen-session"))
    client.get("/me")
    stored = sql("SELECT token FROM sessions LIMIT 1").strip()
    assert stored
    req = urllib.request.Request(
        f"{API}/me", headers={"Cookie": f"clipdesk_session={stored}"}
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        raise AssertionError("a database session value must not be usable as a cookie")
    except urllib.error.HTTPError as exc:
        assert exc.code == 401


def test_per_ip_rate_limit_blocks_after_many_failures():
    from helpers import Client

    client = Client()
    try:
        client.post("/auth/sign-in", {"email": "ip-limit@example.com", "password": "wrong-password-123"})
    except urllib.error.HTTPError:
        pass
    ip = sql(
        "SELECT ip FROM login_attempts WHERE email='ip-limit@example.com' "
        "ORDER BY created_at DESC LIMIT 1"
    ).strip()
    assert ip
    sql("DELETE FROM login_attempts")
    sql(
        "INSERT INTO login_attempts (email, ip, ok) "
        f"SELECT 'x' || g || '@example.com', '{ip}', false FROM generate_series(1, 50) AS g"
    )
    try:
        client.post("/auth/sign-in", {"email": _email("ip-limit"), "password": "wrong-password-123"})
        raise AssertionError("the IP should be rate limited")
    except urllib.error.HTTPError as exc:
        assert exc.code == 429
    finally:
        sql("DELETE FROM login_attempts")


def test_demoting_an_admin_revokes_access_immediately():
    admin = make_admin()
    creator = sign_up(_email("demote-me"))
    user_id = creator.get("/me")["user"]["id"]
    admin.patch(f"/admin/users/{user_id}", {"role": "admin"})
    assert creator.get("/admin/users")["items"] is not None
    admin.patch(f"/admin/users/{user_id}", {"role": "creator"})
    try:
        creator.get("/admin/users")
        raise AssertionError("a demoted admin must lose access immediately")
    except urllib.error.HTTPError as exc:
        assert exc.code == 401


# --------------------------------------------------------------------- F2


def test_upload_staging_is_deleted_after_assembly():
    admin = make_admin()
    mission = seed_mission(admin)
    creator = sign_up(_email("staging"))
    start = creator.post("/uploads/start", {})
    creator.call(
        "PUT",
        f"/uploads/{start['upload_id']}/chunks/0",
        raw=STANDIN.read_bytes(),
        ctype="application/octet-stream",
    )
    creator.post(
        f"/uploads/{start['upload_id']}/complete",
        {"marks": [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}],
         "filename": "recording.mp4"},
    )
    probe = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "sh", "-c",
         f"test ! -e /tmp/clipdesk-uploads/{start['upload_id']}"],
        cwd=ROOT, capture_output=True,
    )
    assert probe.returncode == 0, "upload staging should be gone after assembly"


def test_a_recording_past_retention_is_removed_but_the_clip_remains():
    admin = make_admin()
    mission = seed_mission(admin)
    creator = sign_up(_email("retention"))
    uploaded = upload_recording(
        creator, [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}]
    )
    clip = _wait_ready(creator, uploaded["clips"][0])
    key = sql(f"SELECT recording_key FROM clips WHERE id='{clip['id']}'").strip()
    assert key
    sql(f"UPDATE clips SET created_at = now() - interval '8 days' WHERE id='{clip['id']}'")
    result = admin.post("/admin/cleanup", {})
    assert result["recordings"] >= 1
    assert key not in storage_keys()
    assert sql(f"SELECT count(*) FROM clips WHERE id='{clip['id']}'").strip() == "1"


def test_deleting_an_account_removes_voice_over_previews():
    admin = make_admin()
    mission = seed_mission(admin)
    creator = sign_up(_email("preview-del"))
    uploaded = upload_recording(
        creator, [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}]
    )
    clip_id = uploaded["clips"][0]
    key = f"voice-overs/test-{clip_id}/preview.wav"
    subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-c",
         "from worker_app import storage; import pathlib;"
         f"p=pathlib.Path('/tmp/preview.wav');p.write_text('x');storage.put_file('{key}','/tmp/preview.wav')"],
        cwd=ROOT, check=True, capture_output=True,
    )
    sql(
        "INSERT INTO voice_overs (clip_id, voice, text, audio_key, state) "
        f"VALUES ('{clip_id}', 'v', 't', '{key}', 'ready')"
    )
    assert key in storage_keys()
    creator.delete("/account")
    assert key not in storage_keys()
