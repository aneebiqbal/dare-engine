"""The automatic pipeline through the real API: upload, watch it finish, resume."""
import pathlib
import time

import pytest

from helpers import ROOT, make_admin, sql, truncate

FIXTURE = ROOT / "tests" / "fixtures" / "standin_speech_45s.mp4"


@pytest.fixture(scope="module")
def admin():
    truncate(
        "pipeline_candidates", "pipeline_runs", "clips", "jobs",
        "studio_candidates", "studio_recordings", "projects", "exports",
        "attempts", "marks", "assignments", "streams",
    )
    return make_admin()


def _upload(admin, filename="standin.mp4"):
    boundary = "----pipeline-test"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{filename}\"\r\nContent-Type: video/mp4\r\n\r\n"
    ).encode() + FIXTURE.read_bytes() + (f"\r\n--{boundary}--\r\n").encode()
    return admin.call(
        "POST", "/pipeline/upload", raw=body,
        ctype=f"multipart/form-data; boundary={boundary}",
    )


def _wait_for(admin, run_id, predicate, tries=120, delay=3):
    for _ in range(tries):
        state = admin.get(f"/pipeline/{run_id}")
        if predicate(state):
            return state
        time.sleep(delay)
    pytest.fail(f"pipeline {run_id} never reached the expected state")


def test_upload_starts_a_run_and_finishes_with_shorts(admin):
    res = _upload(admin)
    run_id = res["run_id"]
    # Keep the acceptance run short: three clips.
    sql(f"UPDATE pipeline_runs SET top_n = 3 WHERE id = '{run_id}'")

    state = _wait_for(
        admin, run_id,
        lambda s: s["run"]["state"] in ("done", "failed", "paused"),
    )
    run = state["run"]
    assert run["state"] == "done", run
    assert run["progress"] == 100
    assert run["stage"] == "done"
    assert run["stage_timings"].keys() >= {
        "ingest", "scan", "rank", "vision", "cut", "transcribe", "render",
    }
    assert state["candidates"], "the cheap scan produced no candidates"
    assert len(state["clips"]) == 3, state["clips"]
    assert all(c["state"] == "ready" for c in state["clips"])
    assert run["compute_path"]
    assert run["finished_at"]
    # Media lives on the SSD under the project folder; the model is gone.
    from helpers import storage_keys

    keys = storage_keys()
    assert any(k.startswith(f"projects/{run_id}/") for k in keys), keys
    assert run["memory"], "the idle memory readout was not recorded"
    assert run["model_loaded"] == ""


def test_project_shows_the_live_pipeline_state(admin):
    res = _upload(admin)
    run_id = res["run_id"]
    sql(f"UPDATE pipeline_runs SET top_n = 2 WHERE id = '{run_id}'")
    items = admin.get("/projects")["items"]
    mine = [p for p in items if p["id"] == res["project_id"]]
    assert mine and mine[0]["pipeline"]["run_id"] == run_id
    _wait_for(admin, run_id, lambda s: s["run"]["state"] == "done")


def test_timestamps_are_added_without_removing_ai_suggestions(admin):
    res = _upload(admin)
    run_id = res["run_id"]
    sql(f"UPDATE pipeline_runs SET top_n = 2 WHERE id = '{run_id}'")
    out = admin.post(f"/pipeline/{run_id}/timestamps", {
        "timestamps": [{"start": 1, "end": 8}, {"start": 9999, "end": 10005}],
    })
    assert out["added"] == 1
    assert any("outside the video" in n for n in out["ignored"])
    state = _wait_for(admin, run_id, lambda s: s["run"]["state"] == "done")
    origins = {c["origin"] for c in state["candidates"]}
    assert "user" in origins
    assert "ai" in origins


def test_resume_requeues_a_paused_run(admin):
    res = _upload(admin)
    run_id = res["run_id"]
    sql(f"UPDATE pipeline_runs SET state = 'paused', top_n = 1 WHERE id = '{run_id}'")
    out = admin.post(f"/pipeline/{run_id}/resume", {})
    assert out["state"] == "queued"
    state = _wait_for(admin, run_id, lambda s: s["run"]["state"] == "done")
    assert state["run"]["stage_timings"].keys() >= {"ingest", "scan", "render"}
