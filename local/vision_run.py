"""Run the sampled vision pass on one recording and print what it found.

    .venv/bin/python local/vision_run.py <recording.mp4> [out-dir]

The pass samples about one frame every five seconds, asks the host bridge's
vision model about each window, then unloads the model. It prints the ranked
suggestions with the model's reason and the frame it judged, plus the seconds the
pass added and whether the unload was verified.
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worker"))

# This script runs on the host, where the bridge is localhost. The worker
# container uses host.docker.internal (the default in clip.vision).
os.environ.setdefault("MODEL_BRIDGE_URL", "http://127.0.0.1:8798")

from clip.vision import suggest  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path("vision-out")
    out.mkdir(parents=True, exist_ok=True)
    suggestions, meta = suggest(path, top_n=5, tmp_root=str(out))
    payload = {
        "meta": meta,
        "suggestions": [
            {**s.as_dict(), "thumb": s.thumb_path} for s in suggestions
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
