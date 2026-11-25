"""Projects: the stage machine is derived from real artifacts, never stored."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from app.projects import STAGES, STAGE_PROGRESS, derive_stage  # noqa: E402


def test_a_bare_project_is_planned():
    assert derive_stage() == "planned"


def test_a_live_stream_is_recording():
    assert derive_stage(live=True) == "recording"


def test_an_attached_recording_is_imported():
    assert derive_stage(recording=True) == "imported"


def test_an_active_analysis_job_is_analyzing():
    assert derive_stage(recording=True, analyzing=True) == "analyzing"


def test_a_ready_clip_is_clips_ready():
    assert derive_stage(recording=True, analyzing=False, ready_clips=1, total_clips=1) == "clips_ready"


def test_all_clips_reviewed_is_reviewed():
    assert (
        derive_stage(recording=True, ready_clips=2, total_clips=2, reviewed_clips=2)
        == "reviewed"
    )


def test_a_partial_review_stays_clips_ready():
    assert (
        derive_stage(recording=True, ready_clips=2, total_clips=2, reviewed_clips=1)
        == "clips_ready"
    )


def test_an_export_wins_over_everything():
    assert (
        derive_stage(
            recording=True,
            ready_clips=2,
            total_clips=2,
            reviewed_clips=2,
            exported=True,
        )
        == "exported"
    )


def test_every_stage_has_a_progress_number():
    assert set(STAGE_PROGRESS) == set(STAGES)
    assert [STAGE_PROGRESS[s] for s in STAGES] == sorted(STAGE_PROGRESS[s] for s in STAGES)
