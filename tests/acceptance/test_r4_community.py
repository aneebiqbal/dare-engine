"""R4 / M7: real attempts rank correctly on the public page."""
import time

from helpers import create_user_with_invite, make_admin, seed_mission, truncate, upload_recording


def test_two_users_rank_on_the_public_page():
    truncate(
        "users", "invites", "sessions", "login_attempts", "password_resets",
        "missions", "assignments", "marks", "clips", "jobs", "streams", "attempts",
        "daily_sets", "ai_usage", "tour_progress", "user_settings",
    )
    admin = make_admin()
    mission = seed_mission(admin)
    alice = create_user_with_invite(admin, "r4-alice@example.com", name="R4 Alice")
    bob = create_user_with_invite(admin, "r4-bob@example.com", name="R4 Bob")

    upload_recording(alice, [{"mission_id": mission, "start": 5, "end": 20, "result": "41"}])
    upload_recording(bob, [{"mission_id": mission, "start": 5, "end": 20, "result": "52"}])

    deadline = time.time() + 300
    rows = []
    while time.time() < deadline:
        rows = alice.get(f"/missions/{mission}/leaderboard")["items"]
        if len(rows) >= 2:
            break
        time.sleep(5)

    assert [r["rank"] for r in rows[:2]] == [1, 2]
    assert rows[0]["result_value"] == 41.0
    assert rows[1]["result_value"] == 52.0

    page = alice.get(f"/m/{mission}")
    assert page["attempts"][0]["rank"] == 1
    assert page["card"]["id"] == mission
