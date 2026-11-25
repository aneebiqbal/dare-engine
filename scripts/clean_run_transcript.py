"""Strip wrong-script words from a finished run's transcript and rescore it.

    docker compose cp scripts/clean_run_transcript.py worker:/tmp/crt.py
    docker compose exec -e PYTHONPATH=/app worker python /tmp/crt.py <run_id>
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worker"))

from clip import pipeline  # noqa: E402


def main(run_id: str) -> None:
    run = pipeline._get_run(run_id)
    if run is None:
        raise SystemExit("no such run")
    language = run.get("language") or "en"
    words = [
        pipeline.Word(float(w["start"]), float(w["end"]), str(w["text"]))
        for w in (run.get("transcript") or [])
    ]
    kept = pipeline._clean_words(words, language)
    dropped = len(words) - len(kept)
    timings = dict(run.get("stage_timings") or {})
    for stage in ("detect", "signals", "score", "cut", "render"):
        timings.pop(stage, None)
    pipeline._update_run(
        run_id,
        {
            "transcript": json.dumps(
                [{"start": w.start, "end": w.end, "text": w.text} for w in kept]
            ),
            "stage_timings": json.dumps(timings),
            "state": "queued",
            "stage": "regions",
            "progress": 22,
            "error": None,
            "action": "Queued to rescore with a cleaned transcript",
        },
    )
    from worker_app import db, jobs

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM pipeline_candidates WHERE run_id = %s", (run_id,)
            )
    jobs.enqueue(
        "run_pipeline",
        json.dumps({"run_id": run_id, "project_id": str(run["project_id"])}),
    )
    print(f"cleaned {dropped} word(s); {len(kept)} remain; queued")


if __name__ == "__main__":
    main(sys.argv[1])
