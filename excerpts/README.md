# Excerpts

One file each from a few coursework projects, chosen because the file shows
how something was built rather than what an assignment asked for.

The projects themselves stay private. They are JHU EP 605.256 assignments,
and publishing them would hand solutions to students currently taking the
course. What is here is the infrastructure around the graded work —
connection handling, container orchestration, joining two sources — which is
the part an employer would want to read and the part that gives nothing away.

Each folder holds the file plus a note on what it demonstrates and what was
deliberately left out.

| Folder | Project | Shows | Slice |
|---|---|---|---|
| [`module_05-database/`](module_05-database/) | Software assurance & secure SQL | Pooled Postgres connections, one source of configuration, a cursor context manager | 1 of 16 source files |
| [`module_06-containers/`](module_06-containers/) | Containerization & messaging | A four-service Compose stack with healthchecks, dependency ordering and least-privilege roles | 1 file of 65 |
| [`module_10-second-source/`](module_10-second-source/) | Immuno-oncology pipeline | Joining a second, independent source to test a claim the first cannot settle | 1 of 19 source files |

Each file is complete rather than trimmed. A file cut mid-way proves less
than a small one shown whole, and the slice is chosen so that showing it
whole costs nothing.

**Credentials.** The Compose file's local development passwords are replaced
here with environment references (`${OWNER_PASSWORD}` and so on). Nothing in
this folder holds a password, a token, or a key.

Two projects have their code public elsewhere rather than excerpted here:

- **Module 13** — the fine-tuned model's serving code is public on its
  [Hugging Face Space](https://huggingface.co/spaces/kxcaroline/will-you-get-in/tree/main),
  because deploying it required publishing `serialize.py`, `inference.py` and
  the app.
- **Module 4** — the Sphinx documentation is published on
  [Read the Docs](https://jhu-software-concepts-ckim179.readthedocs.io/).

For the reasoning behind each project, the case studies on
[caroline.kim/projects](https://caroline.kim/projects) carry the
problem, the approach and what went wrong.
