"""Copy one pipeline run's finished Shorts to the host for review.

    docker compose cp scripts/collect_run_review.py api:/tmp/crr.py
    docker compose exec -e PYTHONPATH=/app api python /tmp/crr.py <run_id>
"""
import json
import pathlib
import re
import shutil
import sys

from app import db, storage
from app.config import settings

ROOT = pathlib.Path(settings.storage_local_dir)
OUT_ROOT = pathlib.Path("/ssd-inbox/clipdesk-review")


def slug(text, fallback="recording"):
    text = re.sub(r"[^A-Za-z0-9]+", "-", (text or "").strip()).strip("-")
    return (text[:40] or fallback)


def main(run_id: str) -> None:
    src_name = ""
    timings = {}
    compute = ""
    notes = []
    with db.session() as conn:
        cur = conn.cursor()
        cur.execute(
            "select source_key, stage_timings, compute_path, notes from pipeline_runs where id = %s",
            (run_id,),
        )
        row = cur.fetchone()
        if row and row[0]:
            cur.execute(
                "select filename from studio_recordings where storage_key = %s", (row[0],)
            )
            found = cur.fetchone()
            src_name = found[0] if found else ""
        if row:
            timings, compute, notes = row[1] or {}, row[2] or "", row[3] or []
        cur.execute(
            "select id, start_seconds, end_seconds, cheap_score, vision_score, "
            "final_score, origin, status, clip_id from pipeline_candidates "
            "where run_id = %s order by final_score desc",
            (run_id,),
        )
        candidates = [
            dict(zip([d.name for d in cur.description], r)) for r in cur.fetchall()
        ]

    out = OUT_ROOT / slug(src_name or run_id)
    out.mkdir(parents=True, exist_ok=True)
    index = []
    n = 0
    for c in candidates:
        if not c["clip_id"]:
            continue
        key = f"projects/{run_id}/clips/{c['id']}/short.mp4"
        if not storage.exists(key):
            # Older runs stored only the serving copy.
            key = f"clips/{c['clip_id']}/short.mp4"
        if not storage.exists(key):
            continue
        n += 1
        dest = out / f"{n:02d}_{c['start_seconds']:.0f}-{c['end_seconds']:.0f}s.mp4"
        shutil.copyfile(ROOT / key, dest)
        index.append(
            {
                "file": dest.name,
                "window": [c["start_seconds"], c["end_seconds"]],
                "origin": c["origin"],
                "scores": [c["cheap_score"], c["vision_score"], c["final_score"]],
                "status": c["status"],
            }
        )

    meta = {
        "run_id": run_id,
        "source": src_name,
        "compute_path": compute,
        "stage_timings": timings,
        "notes": notes,
        "clips": index,
    }
    (out / "manifest.json").write_text(json.dumps(meta, indent=2))
    lines = [
        f"Source: {src_name}",
        f"Run: {run_id}",
        f"Compute: {compute}",
        f"Stage seconds: {json.dumps(timings)}",
        f"Notes: {notes}",
        "",
    ]
    lines += [
        f"{i['file']}  | {i['origin']} | scores cheap={i['scores'][0]:.2f} "
        f"vision={i['scores'][1] if i['scores'][1] is not None else '—'} "
        f"final={i['scores'][2]:.2f} | {i['window'][0]:.0f}-{i['window'][1]:.0f}s"
        for i in index
    ]
    (out / "manifest.txt").write_text("\n".join(lines) + "\n")
    print("copied", n, "clips to", out)


if __name__ == "__main__":
    main(sys.argv[1])
