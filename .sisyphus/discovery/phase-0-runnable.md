# Discovery Brief: make Phase 0 actually run (+ repo hygiene)

## Codebase map
- `src/config.py` — pydantic-settings `Settings` singleton. Fields are snake_case:
  `db_url`, `db_echo_sql`, `ollama_base_url`, `embedding_model`. Exported as `settings`.
  There is **no** `database_url` field.
- `src/db.py` — `get_engine()` / `get_sessionmaker()` (both `@lru_cache(maxsize=1)`) and
  `session_scope() -> Iterator[Session]`, a bare generator with try/commit/except/rollback/
  finally/close. Not decorated.
- `src/clients/embedding.py` — Ollama embedding client (`get_embedding`,
  `get_embeddings_batch`, cosine helpers). Uses `requests`, returns `np.ndarray`.
- `src/models/` — SQLAlchemy 2.x declarative; `Base` + `ReferenceLibrary`,
  `ClassificationLog`, `Correction`. `Vector(1024)` on the embedding column.
- `migrations/env.py` — Alembic runtime; imports `settings` and `Base` root-relative.
- `seeds/seed_reference_library.py` — standalone seeding script, 15 curated examples.
- `alembic.ini` — `script_location = %(here)s/migrations`, `prepend_sys_path = .`,
  `sqlalchemy.url = ""` (set at runtime by env.py).
- `pyproject.toml` — `[project]`, `[dependency-groups] dev` (ruff 0.17.0, mypy 2.4.0),
  `[tool.ruff]` (line-length 120, py312), `[tool.mypy]` (strict-ish, root-anchored).

## Conventions to match
- Imports are **root-relative `src.*`** and nothing else. `src/` is an implicit namespace
  package (no `__init__.py`); the project root is what goes on `sys.path`.
- `uv run` for every command, always from the project root.
- Sync only — no async/await anywhere.
- Double quotes; line length 120; SQLAlchemy 2.x `Mapped[...]` annotations.
- Commit prefixes in use by this workflow: `[impl]`, `[fix]`, `[chore]`, `[docs]`.

## Constraints and hazards
- **Local services are DOWN.** Nothing listens on `localhost:5433` (Postgres) or
  `localhost:11434` (Ollama), verified by socket connect. Docker has `postgres:16-alpine`
  and `postgres:16.2` on port **32768**, neither a pgvector image. Therefore
  `alembic upgrade head` and the seed script **cannot be executed** to verify this work.
  Verification is static only: import resolution, `ruff check`, `ruff format --check`, `mypy`.
- The working tree already carries unrelated uncommitted work: `pyproject.toml`,
  `uv.lock`, `src/config.py`, plus `AM` (staged-and-modified) state on
  `seeds/seed_reference_library.py`, `src/clients/embedding.py`, `src/db.py`, and an
  untracked `CLAUDE.md`. Do not revert or restage anything outside the named files.
- `@lru_cache` on `get_engine`/`get_sessionmaker` means engine config is captured once per
  process. Harmless here; relevant if tests ever need to swap the URL.
- Embedding dimension 1024 is duplicated in `src/models/reference_library.py` and the
  migration with no runtime check.
- DB CHECK constraints fail hard: `tier` ∈ {1,2,3}, `source` ∈ {curated, learned,
  user_override}, `router_method` ∈ {embedding, tiny_llm, hybrid}.
- `.venv/` is not matched by any gitignore rule — it is invisible only because `uv` wrote
  `.venv/.gitignore` containing `*`. That self-exclusion is the only thing protecting it.

## External research
Skipped — no external surface. Every defect is in first-party code, and the two library
behaviours relied on (`contextlib.contextmanager`, pydantic-settings field naming) are
already demonstrated or contradicted by code in this repo.

## Assessment
Four independent defects, each reproduced in-session with evidence, plus two hygiene items:

1. `migrations/env.py:14` reads `settings.database_url`; the field is `db_url`.
   Verified: `dir(settings)` yields `['db_url', 'ollama_base_url']`. Alembic raises
   `AttributeError` before touching the database.
2. `src/db.py:24` `session_scope()` is an undecorated generator, but
   `seeds/seed_reference_library.py:43` calls `with session_scope() as db:`.
   Verified: no `contextmanager` import anywhere in the repo. Raises
   `AttributeError: __enter__`.
3. `src/clients/embedding.py:4` `from config import settings` and
   `seeds/seed_reference_library.py:5` `from clients.embedding import get_embedding` are
   src-root style. Verified: `uv run python -c "import clients.embedding"` →
   `ModuleNotFoundError`. They appear to work only because `.idea/nescio-agents.iml` marks
   `src` as a PyCharm source root. mypy now independently flags both.
4. `seeds/seed_reference_library.py:44` `seed_database()` lacks a return annotation, which
   `disallow_untyped_defs` rejects.

Fix direction for each is the minimal correct one: use the real field name; decorate with
`@contextlib.contextmanager` (keeping the `Iterator[Session]` annotation, which is what
`contextmanager` expects); rewrite the two imports to `src.*`; add `-> None`.

Rejected alternative for (1): adding a `database_url` alias/property to `Settings`. It would
make Alembic work, but it legitimises two names for one setting and contradicts the
documented snake_case rule. Rejected for (2): changing callers to `next(session_scope())`.
That loses commit-on-success and rollback-on-exception, which is the entire point of the
function.

## Open questions
- Which Postgres container (and which pgvector-capable image) is meant to serve port 5433,
  and should `.env` change instead? Only the maintainer can answer. Not a blocker for these
  fixes, but Phase 0 stays unrunnable until it is resolved.

---

## Update — findings during execution

**Defect 4 was a tripwire, not a cosmetic nit.** mypy does not type-check the body of a
fully-unannotated function; under `disallow_untyped_defs` it only reports the missing
annotation. Corroborated by the first mypy run, which emitted
`seeds/seed_reference_library.py:55: note: By default the bodies of untyped functions are not
checked [annotation-unchecked]`. Adding `-> None` made the function typed, switched
body-checking on, and surfaced a latent defect: `seed_examples` infers as
`list[dict[str, object]]` because its values mix `str`/`int`/`float`, so `e["prompt"]` is
`object` where `get_embedding(text: str)` requires `str`.
Resolution (maintainer-approved): a `SeedExample` TypedDict, not `dict[str, Any]` and not a
`cast` — it keeps real checking on the tier/source values that the DB CHECK constraints
enforce anyway.

**Fifth defect found during verification — filter/zip mismatch.**
`seeds/seed_reference_library.py`: embeddings were built from rows filtered to
`source == "curated"`, but `zip(seed_examples, embeddings, strict=True)` iterated *all* rows.
Benign today because all 15 rows are curated; one non-curated row raises `ValueError`, and
without `strict=True` it would silently mis-pair every embedding after the skipped row. This
becomes live the moment the Phase 2+ feedback loop starts writing `learned` and
`user_override` rows into the same table the seeder reads. Resolution: filter once into
`curated`, derive embeddings from it, zip it, and report `len(curated)`.

**Agent reporting note.** The hygiene agent claimed its changes were "staged in index only";
in fact only the `git rm -r --cached` deletions were staged, and `.gitignore`/`.env.example`
sat unstaged in the working tree. The edits themselves were all correct — but the claim about
git state was wrong, which is why commit position and index state get verified directly
rather than taken from a report.

## End-to-end verification — PASSED

The maintainer started `pgvector/pgvector:0.8.6-pg18-trixie` on 5433 and Ollama on 11434,
which allowed the first real run and immediately exposed three further defects that ruff,
mypy and import checks could not see:

7. `python seeds/seed_reference_library.py` fails with `ModuleNotFoundError: No module named
   'src'`. Invoking a script by path puts the script's own directory on `sys.path[0]`, not
   the project root. The agents' acceptance checks used `python -c "import seeds..."`, which
   does put the CWD on the path — so importability was proven while executability was not.
   Correct invocation is `python -m seeds.seed_reference_library`; CLAUDE.md was wrong and is
   fixed.
8. `ClassificationLog.corrections` used `back_populates="original_classification"` against a
   `Correction` class that had only the FK column. Mapper configuration raised
   `InvalidRequestError` on the first ORM instantiation, making every table unwritable.
9. All three models used `default=datetime.now(tz=UTC)`, evaluated once at import time, so
   every row from a process carried that process's start timestamp. Silent; nothing failed.
   Now `server_default=func.now()` plus migration `474e08917fca`.

Final state: `alembic upgrade head` → `474e08917fca`; `configure_mappers()` clean with both
relationships; seeder inserted 15 rows, `vector_dims = 1024`, `created_at` non-null and
server-stamped, no all-zero embeddings; a second run aborted with exit 1 and left the row
count at 15. `ruff check`, `ruff format --check` and `mypy` all green.

Note: all 15 rows share one `created_at`, which is correct — Postgres `now()` is
transaction-start time and the inserts were one transaction. `clock_timestamp()` would be
needed only if per-row ordering within a batch ever mattered.

## Still open after this branch
- Two containers both claim port 5433 (`postgres-vector` on pgvector/pg18 and `postgres` on
  `postgres:16.2`); only the pgvector one is actually bound. The stale duplicate is a
  footgun worth removing.
- `Correction.original_classification` has no `passive_deletes=True` while the FK carries
  `ondelete="CASCADE"`. On an ORM-level delete SQLAlchemy will try to NULL a NOT NULL
  column instead of letting Postgres cascade. Not yet reachable — nothing deletes — but it
  will fire the first time the feedback loop prunes a classification.
- `actual_tier_used` and `escalated_reason` are `nullable=True` but annotated
  `Mapped[int]` / `Mapped[str]` rather than `| None`.
- `compare_server_default` is not enabled in `migrations/env.py`, so `--autogenerate` will
  not notice server-default drift.
- No tests exist. The cosine helpers in `src/clients/embedding.py` and the `Settings` loader
  are testable without Postgres or Ollama and are the cheapest starting point.
- Embedding dimension 1024 is still duplicated between the ORM model and the migration with
  no runtime assertion.
