"""R6 proof: deleting an account removes every row and every stored file."""
import time

from helpers import (
    create_user_with_invite,
    make_admin,
    seed_mission,
    sql,
    storage_keys,
    truncate,
    upload_recording,
)


def test_deleting_an_account_removes_rows_and_files():
    truncate(
        "missions", "assignments", "marks", "clips", "jobs", "streams", "attempts",
        "daily_sets", "ai_usage", "tour_progress", "user_settings",
    )
    admin = make_admin()
    mission = seed_mission(admin)
    name = f"Delete Me {int(time.time())}"
    opener = create_user_with_invite(admin, f"delete-{int(time.time())}@example.com", name=name)
    user_id = opener.get("/me")["user"]["id"]

    upload_recording(opener, [{"mission_id": mission, "start": 5, "end": 20, "result": "0:41"}])

    before = storage_keys()
    assert any(k.startswith(f"recordings/{user_id}/") for k in before), "recording not stored"

    counts = sql(
        "SELECT (SELECT count(*) FROM users WHERE id='%s'), "
        "(SELECT count(*) FROM assignments WHERE user_id='%s'), "
        "(SELECT count(*) FROM sessions WHERE user_id='%s'), "
        "(SELECT count(*) FROM streams WHERE user_id='%s');" % (user_id, user_id, user_id, user_id)
    ).strip()
    users, assignments, sessions, streams = (int(x) for x in counts.split(","))
    assert users == assignments == sessions == streams == 1

    assert opener.delete("/account")["ok"] is True

    after = sql(
        "SELECT (SELECT count(*) FROM users WHERE id='%s'), "
        "(SELECT count(*) FROM assignments WHERE user_id='%s'), "
        "(SELECT count(*) FROM sessions WHERE user_id='%s'), "
        "(SELECT count(*) FROM streams WHERE user_id='%s'), "
        "(SELECT count(*) FROM clips WHERE assignment_id IN "
        "  (SELECT id FROM assignments WHERE user_id='%s'));" % (user_id, user_id, user_id, user_id, user_id)
    ).strip()
    assert all(int(x) == 0 for x in after.split(",")), f"rows left behind: {after}"

    keys_after = storage_keys()
    assert not any(k.startswith(f"recordings/{user_id}/") for k in keys_after), "files left behind"
