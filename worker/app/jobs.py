"""Postgres-backed job queue. Row locking replaces Redis/Celery."""
from contextlib import closing

import psycopg

from .config import settings

HANDLERS: dict[str, callable] = {}


def register(kind: str):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn

    return deco


def _connect():
    return psycopg.connect(settings.database_url)


def enqueue(kind: str, payload: dict) -> None:
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (kind, payload) VALUES (%s, %s)",
                (kind, payload),
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
