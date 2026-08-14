"""Shared PostgreSQL connection helper.

Single source of connection configuration (read from .env / environment), used
by load_data.py, query_data.py, and the Flask app. Exposes:

    get_conninfo()        -> libpq connection string (for one-off scripts)
    cursor(commit=False)  -> context manager yielding a pooled cursor (for the app)

The web app uses a connection pool so it never pays the TCP + auth handshake on
every request. One-off scripts (load_data) open a dedicated connection instead.

Connection encoding is forced to UTF-8 so accented program/university names
(e.g. "San Jose State University") load and render correctly.
"""

from __future__ import annotations

import atexit
import getpass
import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

# load .env from this module's directory, independent of the current working dir
load_dotenv(Path(__file__).resolve().parent / ".env")


def get_conninfo() -> str:
    """Return a libpq connection string from the environment.

    Prefers DATABASE_URL (a full ``postgresql://...`` URL) — the single knob
    tests and CI override. Falls back to assembling the string from
    discrete DB_* parts for local development, preserving backward compatibility
    with existing .env files. UTF-8 is enforced either way so accented program /
    university names load correctly.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        if "client_encoding" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}client_encoding=UTF8"
        return url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "gradcafe")
    user = os.getenv("DB_USER", getpass.getuser())
    password = os.getenv("DB_PASSWORD", "")

    parts = [
        f"host={host}",
        f"port={port}",
        f"dbname={name}",
        f"user={user}",
        "client_encoding=UTF8",
    ]
    if password:
        parts.append(f"password={password}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Connection pool (lazy) — used by the Flask app and query layer
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_pool() -> ConnectionPool:
    """Return a lazily-initialized connection pool (reused across requests).

    ``lru_cache`` memoizes the first result, so every caller shares a single
    pool — a singleton without a module-level global. The pool is created on
    first call (not at import time), so importing this module never opens a
    database connection, which keeps tests fast and isolated.
    """
    pool = ConnectionPool(conninfo=get_conninfo(), min_size=1, max_size=10, open=True)
    atexit.register(pool.close)  # clean shutdown (avoids thread-join-at-exit warning)
    return pool


@contextmanager
def cursor(commit: bool = False):
    """Yield a cursor from a pooled connection.

    Usage:
        with cursor() as cur:                 # read
            cur.execute("SELECT ...")
        with cursor(commit=True) as cur:      # write
            cur.execute("INSERT ...")
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
