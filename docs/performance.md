# Performance

Measured on this machine: Colima VM, 4 CPU, 8 GB RAM, faster-whisper `small`
(int8) on CPU, FFmpeg software H.264. The fixture is the synthetic stand-in, so
these numbers measure the pipeline, not clip quality.

## Three clips from one upload

| Concurrency | Wall time | Notes |
| --- | --- | --- |
| 1 (serial) | 188.7 s | one render at a time |
| 4 (pool) | 119.8 s | 1.6× faster; the VM has 4 CPUs and transcription is CPU-bound |
| 4 (pool, warm) | 70.9 s | earlier run with the model already cached and less contention |

The pool is sized from the CPU count and configurable with
`WORKER_CONCURRENCY`. A crashed worker's jobs return to the queue on restart
(`running` → `queued`) and after `WORKER_STALE_SECONDS` (default 600).

Re-measure with:

```sh
docker compose up -d --build worker
WORKER_CONCURRENCY=1 python tests/performance/bench.py
WORKER_CONCURRENCY=4 python tests/performance/bench.py
```

## Web budgets

Measured with `make budgets` (`tests/screenshots/budgets.py`) on the five
most-used pages at 390 px and 1280 px. Budget: **LCP < 5000 ms** and **total
blocking time < 200 ms**. The numbers are written to `docs/screens/budgets.json`.

The budget is set from a measured floor, not a target: one query to the managed
Neon compute takes **~670 ms** round trip (a persistent connection, no
connection setup), and each page makes two to three of them. The API also keeps
a small client-side connection pool (`api/app/db.py`), which removed the ~1.9 s
TLS setup that every request used to pay.

| Page | Phone LCP | Desktop LCP | Budget |
| --- | --- | --- | --- |
| `/` dashboard | 924 ms | 692 ms | pass |
| `/today` | 2808 ms | 2472 ms | pass |
| `/remote` | 2484 ms | 2448 ms | pass |
| `/clips` | 2276 ms | 2176 ms | pass |
| `/admin` | 776 ms | 664 ms | pass |

Measured results: `docs/screens/budgets.json` (rebuilt by `make budgets`).
