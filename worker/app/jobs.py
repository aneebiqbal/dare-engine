"""Postgres-backed job queue. Row locking replaces Redis/Celery.

Jobs are idempotent (idempotency_key), retry with backoff and keep their error.
"""
from contextlib import closing

import psycopg

from .config import settings

HANDLERS: dict[str, callable] = {}
MAX_RETRIES = 5


def register(kind: str):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn

    return deco


def _connect():
    return psycopg.connect(settings.direct_url)


def enqueue(kind: str, payload: dict, idempotency_key: str | None = None) -> None:
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) VALUES (%s, %s, %s) "
                "ON CONFLICT (idempotency_key) DO NOTHING",
                (kind, payload, idempotency_key),
            )
        conn.commit()


def claim(worker_id: str):
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE jobs
                   SET state = 'running', locked_by = %s,
                       attempts = attempts + 1, updated_at = now()
                  WHERE id = (
                     SELECT id FROM jobs
                      WHERE state = 'queued' AND available_at <= now()
                      ORDER BY available_at, id
                      FOR UPDATE SKIP LOCKED
                      LIMIT 1
                  )
                RETURNING id, kind, payload
                """,
                (worker_id,),
            )
            row = cur.fetchone()
            conn.commit()
            return row


def finish(job_id, state: str) -> None:
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET state = %s, updated_at = now() WHERE id = %s",
                (state, job_id),
            )
        conn.commit()


def fail(job_id, error: str) -> None:
    """Requeue with exponential backoff, or mark failed after MAX_RETRIES."""
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT retry_count FROM jobs WHERE id = %s", (job_id,))
            row = cur.fetchone()
            retry_count = (row[0] if row else 0) or 0
            delay = min(300, 5 * (2 ** retry_count))
            state = "queued" if retry_count < MAX_RETRIES - 1 else "failed"
            cur.execute(
                "UPDATE jobs SET state = %s, error = %s, retry_count = %s, "
                "available_at = now() + make_interval(secs => %s), "
                "locked_by = NULL, updated_at = now() WHERE id = %s",
                (state, error[-2000:], retry_count + 1, delay, job_id),
            )
        conn.commit()
