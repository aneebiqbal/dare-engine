"""Part 3: one acceptance test that walks the entire product.

Managed database (Neon), mock off, no shortcut beyond local sign-in. The
recording is the stand-in; the clip-quality verdict is the one step that needs
the user's real gameplay (see PROGRESS.md).
"""
import time
import urllib.error
import zipfile
from io import BytesIO

import pytest

from helpers import make_admin, sign_up, truncate, upload_recording

SUFFIX = int(time.time())


def _wait_ready(client, clip_id, timeout=420):
    deadline = time.time() + timeout
    while time.time() < deadline:
        clip = client.get(f"/clips/{clip_id}")
        if clip["state"] == "ready":
            return clip
        if clip["state"] == "failed":
            raise AssertionError(f"clip failed: {clip.get('error')}")
        time.sleep(4)
    raise AssertionError("clip did not render in time")


def test_full_product_flow():
    # 1. admin, invite, creator signs up.
    admin = make_admin()
    creator = sign_up(f"full-{SUFFIX}@example.com", name="Full Flow")
    truncate("missions", "assignments", "attempts", "daily_sets", "ai_usage")

    # 2. admin writes a dare with the AI and approves it.
    written = admin.post("/admin/questions", {"questions": ["Can you outrun five stars on a bicycle?"]})
    assert written["count"] >= 1
    mission_id = admin.get("/admin/pool")["items"][0]["id"]
    admin.post(f"/admin/pool/{mission_id}/approve", {})
    admin.post(f"/admin/pool/{mission_id}/assign", {"user_id": creator.get("/me")["user"]["id"]})

    # 3. the creator sees it on Today and accepts it.
    today = creator.get("/today")
    ids = ({today["daily"]["id"]} if today["daily"] else set()) | {p["id"] for p in today["picks"]}
    assert mission_id in ids, "the approved dare must reach the creator's Today"
    creator.post("/assignments", {"mission_id": mission_id})

    # 4. the creator uploads a recording and marks a moment; the clip renders.
    uploaded = upload_recording(
        creator, [{"mission_id": mission_id, "start": 5, "end": 20, "result": "0:41"}]
    )
    clip_id = uploaded["clips"][0]
    _wait_ready(creator, clip_id)

    # 5. review: the creator approves the finished clip.
    assert creator.post(f"/clips/{clip_id}/approve", {})["state"] == "approved"

    # 6. export the package and read the zip.
    assert creator.post(f"/clips/{clip_id}/export", {"title": "Full flow"})["state"] == "ready"
    with creator.opener.open(f"http://localhost:8000/clips/{clip_id}/export", timeout=120) as resp:
        package = zipfile.ZipFile(BytesIO(resp.read()))
    assert set(package.namelist()) >= {"short.mp4", "metadata.json"}

    # 7. manual metrics feed the results page.
    creator.post("/metrics", {"clip_id": clip_id, "views": 1204, "avg_view_percentage": 42})
    results = creator.get("/results")
    assert any(c["clip_id"] == clip_id and c["views"] == 1204 for c in results["clips"])

    # 8. the public leaderboard carries the real attempt.
    board = creator.get(f"/missions/{mission_id}/leaderboard")
    assert board["total"] >= 1

    # 9. the role boundary holds: a creator never reaches an admin route.
    with pytest.raises(urllib.error.HTTPError) as exc:
        creator.get("/admin/users")
    assert exc.value.code == 403
