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

## Web budgets (to be measured in D3)

| Page | Budget |
| --- | --- |
| `/` Today | LCP < 2.0 s, INP < 200 ms |
| `/remote` | LCP < 1.5 s, INP < 100 ms |
| `/clips` | LCP < 2.0 s |
| `/admin` | LCP < 2.0 s |
| `/welcome` | LCP < 2.0 s |

Not yet measured. D3 records the real numbers here.
