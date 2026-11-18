import os
from contextlib import closing, contextmanager

import psycopg
from psycopg_pool import ConnectionPool

from .config import settings

MIGRATIONS = os.path.join(os.path.dirname(__file__), "migrations")

# Each request used to open a fresh TLS connection to Neon (~2 s), which
# dominated every page's LCP. The pool also detects connections the server has
# closed, which a naive reuse would turn into a 500.
_pool = ConnectionPool(
    settings.database_url,
    min_size=1,
    max_size=8,
    timeout=30,
    max_idle=60,
    max_lifetime=300,
    kwargs={"autocommit": False},
)


def connect(direct: bool = False):
    """Pooled by default; `direct=True` uses DATABASE_URL_DIRECT.

    Neon's pooled endpoint is PgBouncer in transaction mode, which breaks
    migrations and the worker's row locks. Those two use the direct URL.
    """
    return psycopg.connect(settings.direct_url if direct else settings.database_url)


@contextmanager
def session(direct: bool = False):
    if direct:
        conn = psycopg.connect(settings.direct_url)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
        return
    with _pool.connection() as conn:
        yield conn


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
