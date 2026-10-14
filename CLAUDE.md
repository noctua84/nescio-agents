# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A self-learning, tiered router for local LLM inference: it classifies an incoming prompt's
complexity, dispatches it to the cheapest Ollama model that can handle it, and learns from
escalations, user overrides, and latency signals.

`docs/local_multi_modal_router_plan.md` is the binding roadmap. Read it before implementing any
router, verification, or feedback-loop work, and do not jump ahead of the current phase.
The repo is at **Phase 0**: schema, config, db session, embedding client, and seed data exist.
The router itself does not.

## Prerequisites

Both must be running or seeding and every embedding call will block:

- **PostgreSQL in Docker on port 5433** with the pgvector extension available. The initial
  migration issues `CREATE EXTENSION IF NOT EXISTS vector`.
- **Ollama on the host at port 11434** with the embedding model pulled:
  `ollama pull qwen3-embedding:0.6b`

## Commands

Dependencies are managed with `uv` against `uv.lock`. Always run through `uv run` — never a bare
`python` — and always from the project root.

```bash
uv sync --frozen                                  # install from the lockfile
uv run alembic upgrade head                       # apply migrations
uv run alembic revision --autogenerate -m "msg"   # new migration from ORM changes
uv run python -m seeds.seed_reference_library     # seed the reference library

uv run ruff check --fix .                         # lint
uv run ruff format .                              # format (line length 120)
uv run mypy                                       # type check src/ and seeds/
```

Ruff and mypy are configured in `pyproject.toml`. There is **no test suite and no CI** yet, so do
not report a test gate as passing — say explicitly that none exists.

## Environment

`.env` is gitignored and there is **no `.env.example`**, so a fresh clone cannot run anything until
it is recreated. Required keys:

| Key | Purpose |
|---|---|
| `DB_URL` | Postgres connection string, e.g. `postgresql://postgres:postgres@localhost:5433/ai_router_db` |
| `DB_ECHO_SQL` | SQLAlchemy SQL logging; `false` normally |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `EMBEDDING_MODEL` | `qwen3-embedding:0.6b` |

Config is a pydantic-settings singleton: `from src.config import settings`. Attributes are
**snake_case** (`settings.db_url`, `settings.ollama_base_url`), not the uppercase env-var names.

## Imports

Always root-relative `src.*` — `from src.config import settings`, `from src.models import Base`.
`src/` is an implicit namespace package with no `__init__.py`, and `alembic.ini` sets
`prepend_sys_path = .`, so the project root is what must be on `sys.path`.

**Run scripts with `-m`, never by path.** `python seeds/seed_reference_library.py` fails with
`ModuleNotFoundError: No module named 'src'`, because invoking a script by path puts that
script's own directory on `sys.path[0]` instead of the project root. `python -m
seeds.seed_reference_library` puts the working directory on the path and resolves `src.*`.

Never write src-root-relative imports (`from config import settings`, `from clients.embedding
import ...`). `.idea/nescio-agents.iml` marks `src` as a source root, so PyCharm puts both the root
and `src/` on `sys.path` and those imports appear to work there while failing from any shell.
If you see one, it is a bug.

## Invariants

- **Embedding dimension is 1024**, duplicated in `src/models/reference_library.py` and the
  migration, with no runtime validation. Changing the embedding model means changing both and
  writing a migration.
- Database CHECK constraints fail hard, with no graceful handling. Validate before insert:
  `tier` ∈ {1, 2, 3}, `source` ∈ {`curated`, `learned`, `user_override`},
  `router_method` ∈ {`embedding`, `tiny_llm`, `hybrid`}.
- Deleting a `classification_logs` row cascades to its `corrections` rows.

## Conventions

- **Sync only.** There is no async/await anywhere; database sessions block. Keep it that way
  unless the roadmap says otherwise.
- SQLAlchemy 2.x declarative style with `Mapped[...]` annotations.
- Embeddings travel as `numpy.ndarray`; `pgvector.sqlalchemy.Vector` on the ORM side.
- New tests go under `tests/` and use pytest.
- Seeding aborts if any `curated` rows already exist. Re-seeding requires clearing them first.
