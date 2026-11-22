"""Projects: one recording is one project, and the stage follows real artifacts."""
import pathlib
import time

import pytest

from helpers import ROOT, make_admin, seed_mission, truncate

FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"


@pytest.fixture(scope="module")
def admin():
    truncate(
        "clips", "jobs", "studio_candidates", "studio_recordings", "projects",
        "attempts", "marks", "assignments", "streams",
    )
    return make_admin()


@pytest.fixture(scope="module")
def mission(admin):
    return seed_mission(admin)


def _upload(admin, filename: str = "standin.mp4") -> dict:
    boundary = "----projects-test"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{filename}"\r\nContent-Type: video/mp4\r\n\r\n'
    ).encode() + FIXTURE.read_bytes() + (f"\r\n--{boundary}--\r\n").encode()
    return admin.call(
        "POST", "/studio/upload", raw=body,
        ctype=f"multipart/form-data; boundary={boundary}",
    )


def _project(admin, project_id: str) -> dict:
    return admin.get(f"/projects/{project_id}")


def _wait_for(admin, project_id: str, predicate, tries=90, delay=2):
    for _ in range(tries):
        state = _project(admin, project_id)
        if predicate(state):
            return state
        time.sleep(delay)
    pytest.fail(f"project {project_id} never reached the expected state")


def test_a_new_project_is_planned(admin):
    state = admin.post("/projects", {"name": "Friday stream"})
    assert state["stage"] == "planned"
    assert state["progress"] == 0
    assert state["clips"] == {"ready": 0, "total": 0, "reviewed": 0}


def test_uploading_a_recording_starts_a_project(admin):
    res = _upload(admin)
    items = admin.get("/projects")["items"]
    mine = [p for p in items if p["recording_id"] == res["recording_id"]]
    assert len(mine) == 1
    assert mine[0]["stage"] == "imported"


def test_attach_moves_a_project_to_imported(admin):
    project = admin.post("/projects", {"name": "Attach me"})
    res = _upload(admin)
    state = admin.post(f"/projects/{project['id']}/attach", {"recording_id": res["recording_id"]})
    assert state["recording_id"] == res["recording_id"]
    assert state["stage"] == "imported"


def test_queue_runs_analysis_and_counts_candidates(admin):
    res = _upload(admin)
    items = admin.get("/projects")["items"]
    project = next(p for p in items if p["recording_id"] == res["recording_id"])
    admin.post(f"/projects/{project['id']}/queue", {})
    state = _wait_for(
        admin,
        project["id"],
        lambda s: s["candidates"] > 0 and "candidates" in (s["stage_note"] or ""),
    )
    assert state["candidates"] > 0


def test_two_projects_run_one_after_the_other(admin):
    """The single-project lane is FIFO: the first queued project is processed first."""
    first = admin.post("/projects", {"name": "First"})
    second = admin.post("/projects", {"name": "Second"})
    admin.post(f"/projects/{first['id']}/queue", {})
    admin.post(f"/projects/{second['id']}/queue", {})

    claimed = {}
    for _ in range(60):
        time.sleep(2)
        a = _project(admin, first["id"])
        b = _project(admin, second["id"])
        if not a["queued"]:
            claimed["first"] = a
        if not b["queued"]:
            claimed["second"] = b
        if len(claimed) == 2:
            break
    assert len(claimed) == 2, claimed
    # The first project finished before the second was claimed.
    assert claimed["first"]["updated_at"] <= claimed["second"]["updated_at"]


def test_stage_follows_real_clips_review_and_export(admin, mission):
    res = _upload(admin)
    items = admin.get("/projects")["items"]
    project = next(p for p in items if p["recording_id"] == res["recording_id"])
    admin.post("/studio/detect", {"recording_id": res["recording_id"], "top_n": 3})
    detail = None
    for _ in range(90):
        time.sleep(2)
        detail = admin.get(f"/studio/recordings/{res['recording_id']}")
        if detail["candidates"]:
            break
    assert detail and detail["candidates"]
    candidate = detail["candidates"][0]
    gen = admin.post("/studio/generate", {
        "recording_id": res["recording_id"],
        "mission_id": mission,
        "windows": [{
            "candidate_id": candidate["id"],
            "start": candidate["start"],
            "end": candidate["end"],
            "template_id": "cold_open",
        }],
    })
    clip_id = gen["clips"][0]
    for _ in range(90):
        time.sleep(3)
        clip = admin.get(f"/clips/{clip_id}")
        if clip["state"] in ("ready", "failed"):
            break
    assert clip["state"] == "ready", clip

    assert _wait_for(admin, project["id"], lambda s: s["stage"] == "clips_ready")["clips"]["ready"] == 1

    admin.post(f"/clips/{clip_id}/approve", {})
    assert _wait_for(admin, project["id"], lambda s: s["stage"] == "reviewed")

    admin.post(f"/clips/{clip_id}/export", {"title": "My clip"})
    assert _wait_for(admin, project["id"], lambda s: s["stage"] == "exported")
