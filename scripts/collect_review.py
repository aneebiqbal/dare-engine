"""Collect every generated Short into /ssd-inbox/clipdesk-review with a manifest."""
import json
import pathlib
import re
import shutil

from app import db, storage
from app.config import settings

ROOT = pathlib.Path(settings.storage_local_dir)
OUT = pathlib.Path("/ssd-inbox/clipdesk-review")
OUT.mkdir(parents=True, exist_ok=True)


def slug(text, fallback="recording"):
    text = re.sub(r"[^A-Za-z0-9]+", "-", (text or "").strip()).strip("-")
    return (text[:32] or fallback)


runs = {}
src_names = {}
clips = {}
cands = []
with db.session() as conn:
    cur = conn.cursor()
    cur.execute("select id, source_key, stage_timings, compute_path, notes from pipeline_runs")
    for r in cur.fetchall():
        runs[str(r[0])] = {"source_key": r[1], "timings": r[2], "compute": r[3], "notes": r[4]}
    cur.execute("select storage_key, filename from studio_recordings")
    for k, f in cur.fetchall():
        src_names[k] = f
    cur.execute("select id, duration_seconds, title from clips")
    for r in cur.fetchall():
        clips[str(r[0])] = {"duration": r[1], "title": r[2]}
    cur.execute(
        "select run_id, start_seconds, end_seconds, cheap_score, vision_score, "
        "final_score, origin, status, clip_id from pipeline_candidates"
    )
    cands = [dict(zip([d.name for d in cur.description], row)) for row in cur.fetchall()]


def run_source(rid):
    info = runs.get(rid) or {}
    return src_names.get(info.get("source_key"), "")


def duration_of_clip(clip_id):
    row = clips.get(str(clip_id)) if clip_id else None
    return row["duration"] if row and row["duration"] else 0.0


candidates_by_clip = {str(c["clip_id"]): c for c in cands if c["clip_id"]}
covered_clips = set()
manifest = []

# Canonical per-project finals first.
keys = storage.list_keys()
for key in keys:
    if not key.endswith("short.mp4"):
        continue
    parts = key.split("/")
    if parts[0] != "projects":
        continue
    rid, cand = parts[1], parts[3]
    src = run_source(rid)
    dur = duration_of_clip((candidates_by_clip.get(str(cand), {}) or {}).get("clip_id"))
    name = f"{slug(src)}__{rid[:8]}__{len(manifest) + 1:02d}_{dur:.1f}s.mp4"
    dest = OUT / name
    shutil.copyfile(ROOT / key, dest)
    covered_clips.add(str((candidates_by_clip.get(str(cand), {}) or {}).get("clip_id")))
    manifest.append({
        "file": name, "source": src, "run": rid, "candidate": str(cand),
        "window": [c["start_seconds"], c["end_seconds"]] if (c := candidates_by_clip.get(str(cand))) else None,
        "origin": c["origin"] if c else None, "scores": [c["cheap_score"], c["vision_score"], c["final_score"]] if c else None,
        "duration": dur, "compute": (runs.get(rid) or {}).get("compute"),
        "stage_timings": (runs.get(rid) or {}).get("timings"),
    })

# Older or manual clips that have no per-project copy.
for key in keys:
    if not key.endswith("short.mp4"):
        continue
    parts = key.split("/")
    if parts[0] != "clips":
        continue
    clip_id = parts[1]
    if clip_id in covered_clips:
        continue
    c = candidates_by_clip.get(clip_id)
    rid = str(c["run_id"]) if c else ""
    src = run_source(rid)
    dur = duration_of_clip(clip_id)
    name = f"{slug(src)}__{(rid or 'studio')[:8]}__{len(manifest) + 1:02d}_{dur:.1f}s.mp4"
    shutil.copyfile(ROOT / key, OUT / name)
    manifest.append({
        "file": name, "source": src, "run": rid, "candidate": "",
        "window": [c["start_seconds"], c["end_seconds"]] if c else None,
        "origin": c["origin"] if c else None,
        "scores": [c["cheap_score"], c["vision_score"], c["final_score"]] if c else None,
        "duration": dur, "compute": (runs.get(rid) or {}).get("compute"),
        "stage_timings": (runs.get(rid) or {}).get("timings"),
    })

(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
lines = ["Generated Shorts for review", ""]
for m in manifest:
    win = f"{m['window'][0]:.0f}-{m['window'][1]:.0f}s" if m["window"] else "-"
    lines.append(
        f"{m['file']}  | source={m['source'] or 'unknown'} | window={win} | "
        f"origin={m['origin'] or 'studio'} | {m['duration']:.1f}s | {m['compute']}"
    )
(OUT / "manifest.txt").write_text("\n".join(lines) + "\n")
print("copied", len(manifest))
