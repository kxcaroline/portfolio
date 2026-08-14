# Module 6 — the container stack

`docker-compose.yml` is the whole four-service system: a Flask web app, a
background worker, RabbitMQ and Postgres.

## What it shows

**Healthchecks that mean something.** Services declare
`depends_on: condition: service_healthy` rather than plain `depends_on`, so
the web app waits until Postgres actually answers, not merely until its
container has started. The difference shows up as a flaky first request that
is otherwise very hard to reproduce.

**Least-privilege database roles.** The application connects as a role that
cannot create databases, create roles or replicate. CI asserts this — it
queries `pg_roles` and fails the build if any `gradcafe_*` role holds a
superuser-class attribute — because a privilege granted during debugging and
forgotten is exactly the kind of thing that survives to production.

**A queue between the request and the work.** The web app publishes to
RabbitMQ and returns a task id; the worker consumes and does the scraping and
loading. That is what lets a long pull run without a request hanging on it,
and what makes the worker independently restartable.

## On the credentials

The published copy replaces this project's local development passwords with
environment references — `${POSTGRES_PASSWORD}`, `${OWNER_PASSWORD}`,
`${RO_PASSWORD}`, `${RW_PASSWORD}`. In the private repository they are
literals, which is defensible for containers that only ever run on a laptop
and are recreated from scratch each time; it is not something to publish, and
reading a connection string with a password in it teaches the wrong habit
regardless of whether the password matters.

## What is not here

The application code, the scraper, the loader, the migrations and the test
suite. This is the orchestration around them.

The stack is exercised end to end in CI — built with `--build`, waited on
until every healthcheck passes, then driven through
`/pull-data` → `/tasks/<id>` → `done` — because Dockerfile and compose
mistakes are invisible to unit tests by construction.
