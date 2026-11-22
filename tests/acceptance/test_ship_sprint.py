"""Ship sprint: client error reporting and the optional sampled vision pass."""
import pathlib
import time

import pytest

from helpers import ROOT, make_admin, truncate

FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"


def _upload(admin, filename: str = "standin.mp4") -> dict:
    boundary = "----ship-test"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{filename}"\r\nContent-Type: video/mp4\r\n\r\n'
    ).encode() + FIXTURE.read_bytes() + (f"\r\n--{boundary}--\r\n").encode()
    return admin.call(
        "POST", "/studio/upload", raw=body,
        ctype=f"multipart/form-data; boundary={boundary}",
    )


def test_client_error_reaches_the_admin_log():
    admin = make_admin()
    admin.post("/client-error", {"message": "boom from the test", "stack": "line 1", "path": "/test"})
    items = admin.get("/admin/errors")["items"]
    assert any(i["message"] == "boom from the test" and i["path"] == "/test" for i in items)


def test_vision_enqueue_runs_the_sampled_pass():
    truncate("clips", "jobs", "studio_candidates", "studio_recordings")
    admin = make_admin()
    recording_id = _upload(admin)["recording_id"]
    admin.post("/studio/vision", {"recording_id": recording_id, "top_n": 3})

    jobs = admin.get("/admin/jobs?page_size=50")["items"]
    assert any(j["kind"] == "suggest_clips" for j in jobs)

    # The pass samples frames and records how long it took, even when no vision
    # model is installed (it then suggests nothing and says so).
    for _ in range(60):
        detail = admin.get(f"/studio/recordings/{recording_id}")
        if detail["vision"]["seconds_added"] is not None:
            assert detail["vision"]["model"]
            return
        time.sleep(2)
    pytest.fail("the vision pass never finished")
