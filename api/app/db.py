import os
from contextlib import closing

import psycopg

from .config import settings

SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")


def _connect():
    return psycopg.connect(settings.database_url)


def migrate() -> None:
    with open(SCHEMA) as fh:
        ddl = fh.read()
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def check() -> None:
    with closing(_connect()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
