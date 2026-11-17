import os
from contextlib import closing, contextmanager

import psycopg

from .config import settings

MIGRATIONS = os.path.join(os.path.dirname(__file__), "migrations")


def connect(direct: bool = False):
    """Pooled by default; `direct=True` uses DATABASE_URL_DIRECT.

    Neon's pooled endpoint is PgBouncer in transaction mode, which breaks
    migrations and the worker's row locks. Those two use the direct URL.
    """
    return psycopg.connect(settings.direct_url if direct else settings.database_url)


@contextmanager
def session(direct: bool = False):
    conn = connect(direct)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def migrate() -> None:
    """Apply numbered migration files once each, in order, on an empty or
    existing database. `direct=True` because DDL over PgBouncer is unsupported.
    """
    with closing(connect(direct=True)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            cur.execute("SELECT name FROM schema_migrations")
            applied = {r[0] for r in cur.fetchall()}
            for name in sorted(os.listdir(MIGRATIONS)):
                if not name.endswith(".sql") or name in applied:
                    continue
                with open(os.path.join(MIGRATIONS, name)) as fh:
                    cur.execute(fh.read())
                cur.execute(
                    "INSERT INTO schema_migrations (name) VALUES (%s)", (name,)
                )
        conn.commit()


def check() -> None:
    with closing(connect()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
