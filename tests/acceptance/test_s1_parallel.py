"""S1: a killed worker's jobs are recovered, with no duplicate clips."""
import subprocess
import time

from helpers import make_admin, seed_mission, sign_up, truncate, upload_recording


def test_killing_a_worker_mid_render_still_finishes_three_clips():
    truncate(
        "users", "invites", "sessions", "login_attempts", "password_resets",
        "missions", "assignments", "marks", "clips", "jobs", "streams", "attempts",
        "daily_sets", "ai_usage", "tour_progress", "user_settings",
    )
    admin = make_admin()
    mission = seed_mission(admin)
    opener = sign_up("s1-parallel@example.com", name="S1 Parallel")
    upload_recording(opener, [
        {"mission_id": mission, "start": 5 + i * 5, "end": 20 + i * 5, "result": f"0:{40 + i}"}
        for i in range(3)
    ])

    def states():
        return [c["state"] for c in opener.get("/clips")["items"]]

    deadline = time.time() + 300
    while time.time() < deadline and not any(s == "ready" for s in states()):
        time.sleep(3)

    # Kill the worker mid-render, then bring it back.
    subprocess.run(["docker", "kill", "clipdesk-worker-1"], capture_output=True)
    subprocess.run(["docker", "compose", "up", "-d", "worker"], capture_output=True)
    time.sleep(6)

    deadline = time.time() + 600
    while time.time() < deadline:
        clips = opener.get("/clips")["items"]
        if len(clips) >= 3 and all(c["state"] == "ready" for c in clips[:3]):
            break
        time.sleep(5)

    clips = opener.get("/clips")["items"]
    assert len(clips) == 3, f"expected exactly three clips, got {len(clips)}"
    assert all(c["state"] == "ready" for c in clips)
    assert len({c["id"] for c in clips}) == 3, "duplicate clips"
