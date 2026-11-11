# 5. Enforce package layout and import-linter dependency rules

Date: 2026-11-11
Status: Accepted

## Context

Hassas keeps a channel-neutral core (CH-1), a pure analysis engine (ANA-9, BEN-4) and a benchmark that runs without a database or an LLM. All three depend on rules about which package may import which (ARCHITECTURE.md §4). Coding agents write most of the code, one short task at a time, and a rule that is only written down gets broken by an innocent-looking import. The first break is cheap to fix; the hundredth is a refactor.

We need the rules to fail CI, and to keep working as modules are added.

Alternatives considered:

- **No enforcement, review only.** Nothing to build, but the owner would have to spot every import in every PR. A forbidden import is a one-line change in a large diff.
- **A custom pytest check.** Walk the code with `ast` and assert on imports. No new dependency, but we would write and maintain our own graph, wildcard and indirect-import logic, and its error messages. import-linter already does this and reports the full import chain.
- **Separate installable packages per layer** (`hassas-domain`, `hassas-analysis`...). The package manager would enforce the boundaries. It adds a workspace, several builds and version pins to a one-owner project, and still cannot express "only `main` may import `channels`".
- **import-linter** (chosen). Contracts live in `pyproject.toml`, run in about a second, and print the offending chain.

## Decision

We will use **import-linter**, run as `uv run lint-imports` after mypy in CI, with the contracts in `pyproject.toml` under `[tool.importlinter]`. The root packages are `hassas` and `benchmark` (the benchmark sits at the repo root, outside `src/`). External packages are included in the graph so that channel SDKs can be forbidden by name even though none is installed.

The contracts, one per rule in ARCHITECTURE.md §4:

1. `hassas.domain` imports nothing else from `hassas`.
2. `hassas.analysis` imports only `hassas.domain`.
3. CH-1: nothing in `hassas` imports `hassas.channels`, except `hassas.main`, the only module that wires the app together.
4. CH-1: no `telegram`, `aiogram`, `telebot`, `whatsapp` or `pywa` import outside `hassas.channels`.
5. `hassas.channels` imports only `messaging`, `domain`, `config`, `logging` and the top-level `hassas.conversation` package, not its submodules.
6. `conversation`, `agents`, `jobs` and `summary` reach the database only through `hassas.db.repositories`.
7. Nothing imports `hassas.main`. Without this, contract 3's exception would let any module reach `channels` through `main`.
8. `hassas.agents` never imports `hassas.conversation` or `hassas.channels`.
9. `benchmark` imports only `hassas.analysis` and `hassas.domain` from `hassas`.

Choices that go with them:

- **`hassas.main` is the composition root.** Core code that needs to send a message uses a sender protocol defined in `messaging/`; `main` passes in the concrete adapter. `jobs` never import `channels`.
- **Allow-lists, not deny-lists.** Contracts 1, 2, 5 and 9 forbid `hassas.*` (or `hassas`) and list the allowed imports in `ignore_imports`. A new top-level module is then forbidden by default and needs a deliberate edit to be allowed. Contract 3 uses `hassas.*` as its source for the same reason.
- **Indirect imports** are allowed in contracts 5 and 6 (`channels -> conversation -> conversation.x`, `conversation -> db.repositories -> db.models` are the intended paths) and checked everywhere else.
- **`AnalysisConfig` lives in `analysis/config.py`** with a pure `AnalysisConfig.from_toml(text: str)`. Callers (`hassas/config.py` for the app, the benchmark CLI) read `config/analysis.toml` themselves. That keeps `analysis/` free of I/O and lets `benchmark` stay inside its import rule.
- **Layout:** every package in the ARCHITECTURE.md §4 module map exists, empty apart from `__init__.py` or `.gitkeep`. Modules with logic (`hassas.logging`, `analysis/config.py`, `db/models.py`) come with the tasks that need them.
- **Tests:** every contract has a test that copies the tree to a temp directory, adds one violating module and expects that contract to break, and a test that the allowed imports stay clean (`tests/unit/test_import_contracts.py`).

## Consequences

- A forbidden import fails CI with the exact import chain, instead of relying on the reviewer.
- The allow-lists in `ignore_imports` are written by hand. Allowing a new import (say `channels` using a new `hassas.errors` module) means editing the contract, and the edit shows up in the PR as a deliberate change. That is the point, but it is friction.
- Contract 2, 5 and 9 allow-lists name `domain`, `messaging`, `config` and `logging` by path. Renaming one of those packages means editing the contracts too.
- The SDK contract lists SDK names. A channel SDK not on the list (a new library) is not caught until it is added.
- Contract 6 allows only `hassas.db.repositories` and everything under it. `db.mappers` (the database-to-`AnalysisInput` mapping) is therefore not importable from core code; it has to be reached through a repository method. If that proves awkward, change the contract in a new ADR.
- A direct `import hassas.db` or `from hassas.db import x` in core code is also an error, even though `hassas/db/__init__.py` holds no logic.
- `hassas.logging` and `hassas.db.models` / `session` do not exist yet. Their entries cost nothing today and apply as soon as the modules appear. The allow-lists set `unmatched_ignore_imports_alerting = "none"` so that such entries are accepted, which also means a stale entry is never reported.
- Plain `import hassas` (the root `__init__`) is not covered by the `hassas.*` forms in contracts 1 and 2, only by contract 9. The root `__init__` is empty and should stay so.
- The contract tests start about seventy `lint-imports` subprocesses, run eight at a time, and add about eight seconds to the test run.
- import-linter is one more dev dependency, pinned in `uv.lock`.
