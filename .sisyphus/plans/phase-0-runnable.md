# Plan: make Phase 0 actually run (+ repo hygiene)

Branch: `fix/phase-0-runnable` (branched from `main`, which is currently checked out)
Discovery brief: `.sisyphus/discovery/phase-0-runnable.md`

## Objective
Phase 0 is reported complete but nothing in it executes: Alembic dies on a wrong settings
attribute, the seed script dies on a non-context-manager, and two imports resolve only inside
PyCharm. Fix all four defects, then clean the two repo-hygiene problems found alongside them.

## Out of scope
Starting or re-pointing Postgres/Ollama; writing tests; any router, verification, or
feedback-loop work (Phase 1+ per `docs/local_multi_modal_router_plan.md`).

---

## Task 1 — Alembic reads a settings field that does not exist
**Complexity**: simple
**Placement**: subagent
**File**: `migrations/env.py:14`
Change `settings.database_url` to `settings.db_url`. Do not add an alias to `Settings`.
**Acceptance**: `uv run python -c "import migrations.env"` is not a valid check (Alembic
context required); instead confirm by grep that no `database_url` reference remains anywhere,
and that `mypy` reports no attribute error on that line.

## Task 2 — `session_scope()` is not a context manager
**Complexity**: standard
**File**: `src/db.py`
Decorate `session_scope` with `@contextlib.contextmanager` (import `contextmanager` from
`contextlib`). **Keep** the `-> Iterator[Session]` annotation — that is what `contextmanager`
expects; changing it to `Session` is wrong and will fail mypy.
**Acceptance**: `with session_scope() as db:` type-checks; `mypy` clean on `src/db.py`.

## Task 3 — Two src-root-relative imports
**Complexity**: simple
**Files**: `src/clients/embedding.py:4`, `seeds/seed_reference_library.py:5`
`from config import settings` → `from src.config import settings`.
`from clients.embedding import get_embedding` → `from src.clients.embedding import get_embedding`.
**Acceptance**: `uv run python -c "import src.clients.embedding"` succeeds; both mypy
`import-not-found` errors gone.

## Task 4 — Missing return annotation
**Complexity**: simple
**File**: `seeds/seed_reference_library.py:44`
`def seed_database():` → `def seed_database() -> None:`
**Acceptance**: mypy `no-untyped-def` error gone.

## Task 5 — Ignore bytecode and virtualenv; untrack committed bytecode
**Complexity**: simple
**Files**: `.gitignore` (+ `git rm -r --cached`)
Add `__pycache__/`, `*.pyc`, `.venv/`, `.jbeval/`. Then untrack the 8 already-committed
`.pyc` files with `git rm -r --cached` (never plain `git rm` — the local files must survive):
`migrations/__pycache__/`, `migrations/versions/__pycache__/`, `src/__pycache__/`,
`src/models/__pycache__/`.
**Acceptance**: `git ls-files | grep -E '__pycache__|\.pyc$'` is empty; the `.pyc` files still
exist on disk; `git check-ignore -q src/__pycache__` succeeds.

## Task 6 — `.env.example`
**Complexity**: simple
**File**: `.env.example` (new, tracked)
Four keys with the documented local-dev values: `DB_URL`,
`DB_ECHO_SQL=false`, `OLLAMA_BASE_URL=http://localhost:11434`,
`EMBEDDING_MODEL=qwen3-embedding:0.6b`. Add a header comment noting pgvector is required and
that the migration creates the extension. No real secrets — these are localhost dev defaults.
**Acceptance**: file is tracked; every key in `src/config.py` appears in it.

## Task 7 — Repo-wide format pass
**Complexity**: simple
**Placement**: inline (orchestrator runs the tool; no authored code)
`uv run ruff check --fix .` then `uv run ruff format .` across all 10 files.
**Must run after Tasks 1–4** so their edits are formatted in the same pass rather than
fighting it.
**Acceptance**: `uv run ruff check .` and `uv run ruff format --check .` both clean.

---

## Execution strategy
- **Wave 1 (parallel)**: Agent A = Tasks 1–4 (`archimedes-standard`); Agent B = Tasks 5–6
  (`archimedes-simple`). Disjoint file sets, so no collision.
- **Wave 2 (sequential)**: Task 7, after Wave 1 lands.
- Tasks 1–4 are grouped into one agent because they touch overlapping files and total ~6
  edited lines; seven separate dispatches would each need the full brief inlined and would
  collide on `seeds/seed_reference_library.py`.

## Verification — static only
Local services are down (see brief). `alembic upgrade head` and the seed script **cannot be
run**. Gates available: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
plus direct import resolution checks. End-to-end behaviour will be unproven, and must be
reported as unproven.
