import os
from contextlib import closing, contextmanager

import psycopg

from .config import settings

SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")


def connect():
    return psycopg.connect(settings.database_url)


@contextmanager
def session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def migrate() -> None:
    with open(SCHEMA) as fh:
        ddl = fh.read()
    with closing(connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def check() -> None:
    with closing(connect()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
