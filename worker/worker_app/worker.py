"""Job loop: a small pool sized from the CPU count, with stale-job recovery."""
from __future__ import annotations

import os
import threading
import time
import traceback

from . import db, jobs

CONCURRENCY = max(1, int(os.environ.get("WORKER_CONCURRENCY", os.cpu_count() or 2)))
STALE_SECONDS = int(os.environ.get("WORKER_STALE_SECONDS", 600))


def run_once(worker_id: str) -> bool:
    row = jobs.claim(worker_id)
    if row is None:
        return False
    job_id, kind, payload = row
    payload = {**payload, "_job_id": str(job_id)}
    handler = jobs.HANDLERS.get(kind)
    if handler is None:
        print(f"no handler for job {job_id} kind={kind}")
        jobs.finish(job_id, "failed")
        return True
    try:
        handler(payload)
        jobs.finish(job_id, "done")
    except Exception as exc:
        traceback.print_exc()
        jobs.fail(job_id, f"{type(exc).__name__}: {exc}")
    return True


def _run(worker_id: str, interval: float) -> None:
    while True:
        try:
            run_once(worker_id)
        except Exception:
            traceback.print_exc()
        time.sleep(interval)


def _reaper() -> None:
    """A crashed worker's job returns to the queue after the stale timeout."""
    while True:
        time.sleep(30)
        try:
            with db.session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE jobs SET state = 'queued', locked_by = NULL "
                        "WHERE state = 'running' AND updated_at < now() - make_interval(secs => %s)",
                        (STALE_SECONDS,),
                    )
        except Exception:
            traceback.print_exc()


def loop(worker_id: str, interval: float = 1.0) -> None:
    threading.Thread(target=_reaper, daemon=True).start()
    threads = [
        threading.Thread(target=_run, args=(f"{worker_id}-{i}", interval), daemon=True)
        for i in range(CONCURRENCY)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
