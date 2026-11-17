from contextlib import closing, contextmanager

import psycopg

from .config import settings


def connect(direct: bool = True):
    # The worker takes row locks, so it always uses the direct connection.
    return psycopg.connect(settings.direct_url if direct else settings.database_url)


@contextmanager
def session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def check() -> None:
    with closing(connect(False)) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
