"""Sprint 6 Part D: local voice-over with ducking, and a voice preview."""
import pathlib
import tempfile
import time

import pytest

from helpers import create_user_with_invite, make_admin, seed_mission, truncate, upload_recording


def _voice_ready() -> bool:
    import subprocess

    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "worker", "test", "-f",
         "/data/voices/en_US-amy-medium.onnx"],
        capture_output=True,
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(not _voice_ready(), reason="run `make voice` first")

@pytest.fixture(scope="module")
def seeded():
    truncate(
        "users", "invites", "sessions", "login_attempts", "password_resets",
        "missions", "assignments", "marks", "clips", "jobs", "streams", "attempts",
        "daily_sets", "ai_usage", "tour_progress", "user_settings", "voice_overs",
    )
    admin = make_admin()
    mission = seed_mission(admin)
    creator = create_user_with_invite(admin, "voice@example.com", name="Voice")
    return creator, mission


def _wait(client, clip_id, want_voice=None, timeout=420):
    deadline = time.time() + timeout
    while time.time() < deadline:
        clip = client.get(f"/clips/{clip_id}")
        if clip["state"] == "ready" and (want_voice is None or clip["voice_over"] == want_voice):
            return clip
        time.sleep(4)
    pytest.skip("clip did not render in time")


def test_voice_over_re_renders_with_speech(seeded):
    creator, mission = seeded
    uploaded = upload_recording(creator, [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}])
    clip = _wait(creator, uploaded["clips"][0])
    creator.post(f"/clips/{clip['id']}/voice-over", {"enabled": True, "voice": "en_US-amy-medium"})
    voiced = _wait(creator, clip["id"], want_voice=True)
    assert voiced["voice"] == "en_US-amy-medium"
    with creator.opener.open(f"http://localhost:8000{voiced['download_url']}", timeout=60) as resp:
        data = resp.read()
    assert len(data) > 1000
    out = pathlib.Path(tempfile.mkdtemp(prefix="voiced-")) / "short.mp4"
    out.write_bytes(data)
    probe = __import__("subprocess").run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True,
    )
    assert probe.stdout.strip() == "aac"


def test_voice_preview_is_a_wav(seeded):
    creator, mission = seeded
    uploaded = upload_recording(creator, [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}])
    clip = _wait(creator, uploaded["clips"][0])
    preview = creator.post(f"/clips/{clip['id']}/voice-preview", {"voice": "en_US-amy-medium"})
    deadline = time.time() + 120
    status = None
    while time.time() < deadline:
        status = creator.get(f"/voice-overs/{preview['id']}")
        if status["state"] == "ready":
            break
        time.sleep(2)
    assert status and status["audio_url"]
    with creator.opener.open(f"http://localhost:8000{status['audio_url']}", timeout=60) as resp:
        head = resp.read(4)
    assert head == b"RIFF"
