# Performance

Measured on this machine: Colima VM, 4 CPU, 8 GB RAM, faster-whisper `small`
(int8) on CPU, FFmpeg software H.264, managed Neon. The rebuild sprint measured
the web app with Playwright (`tests/screenshots/measure.py`, `make budgets`).

## Rebuild sprint — before / after

**TTFB** (time to first byte: the shell is on screen and interactive), ms.

| Page | Before cold/warm | After cold/warm |
| --- | --- | --- |
| `/` dashboard | 1882 / 682 | 729 / **7** |
| `/today` | 2504 / 2744 | 17 / 13 |
| `/live` | 717 / 745 | 10 / 691 |
| `/remote` | 2660 / 2451 | 672 / 665 |
| `/clips` | 2489 / 2315 | 667 / **12** |
| `/results` | 2290 / 2500 | 15 / 12 |
| `/history` | 2405 / 2271 | 11 / 11 |
| `/settings` | 2301 / 2296 | 14 / 16 |
| `/help` | 780 / 690 | 16 / 9 |
| `/admin` | 684 / 683 | 14 / 706 |
| `/admin/pool` | 673 / 716 | 13 / 7 |
| `/admin/studio` | 689 / 824 | 6 / 11 |
| `/admin/users` | 698 / 906 | 11 / 10 |
| `/admin/jobs` | 699 / 686 | 15 / 8 |

The first byte now arrives in **~680 ms cold** (the shell + skeleton) and
**~10 ms warm** for a cached read. Before, creator pages waited 2.3–2.7 s for a
server-side API call before any HTML was flushed.

**LCP** (largest contentful paint, budget 5000 ms), ms.
`docs/screens/budgets.json` is the source of truth, measured by `make budgets`.

| Page | Phone | Desktop |
| --- | --- | --- |
| `/` dashboard | 856 | 976 |
| `/today` | 2120 | 2628 |
| `/remote` | 28 | 40 |
| `/clips` | 792 | 848 |
| `/admin` | 56 | 68 |

TBT is 0 ms on every page; `make budgets` passes. `/today` is the slowest
because it renders the daily dare and its generated card image (a real API/DB
read); the shell streams first and the page is interactive before the data
lands. Re-measure with `make budgets`.

**Cause.** Each creator page awaited one slow API call in its server component
before flushing HTML. Those endpoints run two to three sequential Neon round
trips (~600–900 ms each). The fix: wrap the data in a React `<Suspense>`
boundary so the shell and a skeleton stream first, split the admin dashboard's
6.3 s `/admin/setup` call into a second pass, and cache slow stable reads
(server + client, invalidated on mutation). The residual data latency is the
API's Neon round trips — backend, out of scope.

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

One Neon round trip is ~600–900 ms; the API keeps a small connection pool
(`api/app/db.py`), which removed the ~1.9 s TLS setup every request used to pay.
The web layer now caches the slow, stable reads so warm navigations do not pay
the query again.
