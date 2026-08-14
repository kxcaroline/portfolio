# Module 5 — the database layer

`db.py` is the only place in that project that knows how to reach Postgres.
Everything else — the loader, the query layer, the Flask app — imports from
it.

## What it shows

**One source of connection configuration.** `DATABASE_URL` wins when set,
which is the single knob tests and CI override; otherwise the string is
assembled from discrete `DB_*` parts so an existing local `.env` keeps
working. Either path forces UTF-8, because accented university names had been
loading as mojibake.

**A pool, created lazily.** `@lru_cache(maxsize=1)` makes `get_pool()` a
singleton without a module-level global, and because the pool is built on
first call rather than at import, importing this module never opens a
connection. That is what keeps the test suite fast and isolated — tests that
import the app do not need a database standing by.

**A cursor context manager with an explicit commit.** `cursor()` yields from
the pool; `cursor(commit=True)` is the deliberate opt-in for writes. Making a
write look different from a read at the call site is the point.

## What is not here

The project's SQL, its scrapers, its cleaning logic and its analysis
queries — the graded work. This file is the plumbing underneath it.

The assignment was about software assurance: parameterized queries, a
least-privilege database role, a dependency graph and a Snyk scan in CI.
`db.py` is where the connection half of that lives.
