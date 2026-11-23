"""One real pipeline run on a video, printing measured stage timings.

    make pipeline-demo FILE=fixtures/gameplay_4min.mp4 TOP_N=2
"""
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "acceptance"))
from helpers import make_admin, sql  # noqa: E402

FIXTURE = pathlib.Path(os.environ.get("FILE") or (ROOT / "fixtures" / "gameplay_4min.mp4"))
TOP_N = int(os.environ.get("TOP_N", "2"))


def main():
    admin = make_admin()
    boundary = "----trailer-run"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{FIXTURE.name}\"\r\nContent-Type: video/mp4\r\n\r\n"
    ).encode() + FIXTURE.read_bytes() + (f"\r\n--{boundary}--\r\n").encode()
    res = admin.call(
        "POST", "/pipeline/upload", raw=body,
        ctype=f"multipart/form-data; boundary={boundary}",
    )
    run_id = res["run_id"]
    sql(f"UPDATE pipeline_runs SET top_n = {TOP_N} WHERE id = '{run_id}'")
    print("run", run_id, "file", FIXTURE, "top_n", TOP_N, flush=True)
    deadline = time.time() + int(os.environ.get("TIMEOUT", "3600"))
    while time.time() < deadline:
        state = admin.get(f"/pipeline/{run_id}")
        run = state["run"]
        print(run["state"], run["stage"], run["progress"], run["action"], flush=True)
        if run["state"] in ("done", "failed", "paused"):
            print("TIMINGS", json.dumps(run["stage_timings"], indent=1))
            print("RATES", json.dumps(run.get("rates"), indent=1))
            print("COMPUTE", run["compute_path"])
            print("NOTES", run["notes"])
            print("MEMORY", json.dumps(run["memory"]))
            print("CLIPS", len(state["clips"]), [c["duration_seconds"] for c in state["clips"]])
            return
        time.sleep(5)


if __name__ == "__main__":
    main()
