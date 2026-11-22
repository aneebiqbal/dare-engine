"""The first-run wizard: four steps, progress persisted, verified server-side."""
import pytest

from helpers import make_admin, truncate


@pytest.fixture(scope="module")
def admin():
    truncate("setup_steps")
    return make_admin("wizard-admin@example.com", "wizard-password-123")


def test_a_fresh_admin_starts_at_the_first_step(admin):
    state = admin.get("/admin/wizard")
    assert [s["id"] for s in state["steps"]] == ["ssd", "obs", "models", "cloud"]
    assert state["ready"] is False
    assert state["next"] == "ssd"
    assert all(s["status"] == "pending" for s in state["steps"])


def test_progress_is_persisted_per_user(admin):
    admin.post("/admin/wizard/ssd", {"status": "done", "detail": "1 drive(s) connected"})
    state = admin.get("/admin/wizard")
    assert state["steps"][0]["status"] == "done"
    assert state["steps"][0]["detail"] == "1 drive(s) connected"
    assert state["next"] == "obs"


def test_a_failed_step_is_recorded(admin):
    admin.post("/admin/wizard/obs", {"status": "failed", "detail": "OBS is unreachable"})
    state = admin.get("/admin/wizard")
    assert state["steps"][1]["status"] == "failed"
    assert state["steps"][1]["detail"] == "OBS is unreachable"
    assert state["ready"] is False


def test_all_steps_done_is_ready(admin):
    for step in ("ssd", "obs", "models", "cloud"):
        admin.post(f"/admin/wizard/{step}", {"status": "done"})
    state = admin.get("/admin/wizard")
    assert state["ready"] is True
    assert state["next"] is None


def test_unknown_step_and_status_are_rejected(admin):
    with pytest.raises(Exception):
        admin.post("/admin/wizard/nope", {"status": "done"})
    with pytest.raises(Exception):
        admin.post("/admin/wizard/ssd", {"status": "maybe"})
