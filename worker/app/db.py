from contextlib import closing, contextmanager

import psycopg

from .config import settings


def _connect():
    return psycopg.connect(settings.database_url)


@contextmanager
def session():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def check() -> None:
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
