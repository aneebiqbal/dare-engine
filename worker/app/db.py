from contextlib import closing

import psycopg

from .config import settings


def _connect():
    return psycopg.connect(settings.database_url)


def check() -> None:
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
