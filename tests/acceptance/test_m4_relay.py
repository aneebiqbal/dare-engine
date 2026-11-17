"""M4: push a stream over RTMP, mark Start and Done mid-stream, get a Short.

Uses the synthetic stand-in because `fixtures/stream_10min.mp4` is missing, so
the relay path is proven, not the clip quality. M4 is not accepted.
"""
import subprocess
import time

from helpers import ROOT, make_admin, seed_mission, sign_up, truncate

STANDIN = ROOT / "tests/fixtures/standin_speech_45s.mp4"


def test_stream_produces_a_short_before_it_ends():
    truncate(
        "users", "invites", "sessions", "login_attempts", "password_resets",
        "missions", "assignments", "marks", "clips", "jobs", "streams", "attempts",
        "stream_segments", "daily_sets", "ai_usage", "tour_progress", "user_settings",
    )
    admin = make_admin()
    mission = seed_mission(admin)
    opener = sign_up("m4-relay@example.com", name="M4 Relay")

    stream = opener.post("/streams", {"title": "m4"})
    push = subprocess.Popen(
        [
            "ffmpeg", "-re", "-stream_loop", "3", "-i", str(STANDIN),
            "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
            "-f", "flv", stream["rtmp_url"],
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        connected = False
        for _ in range(20):
            time.sleep(1)
            status = opener.get(f"/streams/{stream['id']}/status")
            if status.get("connected"):
                connected = True
                break
        assert connected, "relay never reported the stream as connected"

        assignment = opener.post("/assignments", {"mission_id": mission})
        time.sleep(3)
        opener.post("/marks", {
            "assignment_id": assignment["id"], "kind": "start", "stream_time": 8,
        })
        time.sleep(8)
        done_at = time.time()
        opener.post("/marks", {
            "assignment_id": assignment["id"], "kind": "done",
            "stream_time": 16, "result": "0:41",
        })

        deadline = time.time() + 300
        clips = []
        while time.time() < deadline:
            clips = opener.get("/clips")["items"]
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
