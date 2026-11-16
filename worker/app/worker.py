import time
import traceback

from . import jobs


def run_once(worker_id: str) -> bool:
    row = jobs.claim(worker_id)
    if row is None:
        return False
    job_id, kind, payload = row
    handler = jobs.HANDLERS.get(kind)
    if handler is None:
        print(f"no handler for job {job_id} kind={kind}")
        jobs.finish(job_id, "failed")
        return True
    try:
        handler(payload)
        jobs.finish(job_id, "done")
    except Exception:
        traceback.print_exc()
        jobs.finish(job_id, "failed")
    return True


def loop(worker_id: str, interval: float = 1.0) -> None:
    while True:
        try:
            run_once(worker_id)
        except Exception:
            traceback.print_exc()
        time.sleep(interval)
