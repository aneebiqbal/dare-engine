"""One real pipeline run on the repo trailer, printing measured stage timings."""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "acceptance"))
from helpers import make_admin, sql  # noqa: E402

FIXTURE = ROOT / "fixtures" / "gameplay_4min.mp4"


def main():
    admin = make_admin()
    boundary = "----trailer-run"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"gameplay_4min.mp4\"\r\nContent-Type: video/mp4\r\n\r\n"
    ).encode() + FIXTURE.read_bytes() + (f"\r\n--{boundary}--\r\n").encode()
    res = admin.call(
        "POST", "/pipeline/upload", raw=body,
        ctype=f"multipart/form-data; boundary={boundary}",
    )
    run_id = res["run_id"]
    sql(f"UPDATE pipeline_runs SET top_n = 2 WHERE id = '{run_id}'")
    print("run", run_id, flush=True)
    deadline = time.time() + 1800
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
