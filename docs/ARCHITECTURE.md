# Hassas — Architecture

**Status:** Target design — ROADMAP phase 1 in progress · **Last updated:** 2026-11-11
**Context:** [IDEA.md](IDEA.md) (why) · [PRD.md](PRD.md) (what) · [ROADMAP.md](ROADMAP.md) (order) · [adr/](adr/) (why each technical decision was made)

This document describes **how Hassas is built**: the stack, the module structure and the rules between modules. Per-phase notes live in ROADMAP.md. It describes the system as it should be _now_. When a decision changes it, update this file and record the decision as an ADR (see §12).

**For agents:** read this before writing code. If the code disagrees with this document, flag it and ask which is right. Don't introduce a library, module or pattern that isn't listed here without proposing an ADR first.

---

## 1. Principles

These come from the PRD and shape every choice below.

1. **Channel-neutral core** (CH-1). Platform code lives only in `channels/`. The core speaks neutral messages and designs for WhatsApp's stricter limits.
2. **Analysis is pure code** (ANA-9, ANA-10). No I/O, no LLM, no database in `analysis/`. Same input + seed gives the same output. Event time, never arrival order.
3. **Seams at every external service.** LLM, web search, Telegram and the clock sit behind small protocols, so tests use fakes and providers can be swapped.
4. **Safety before features** (SAF-1–9). The severe-symptom check runs before anything else in the conversation pipeline, on every message, including before onboarding and consent.
5. **Boring, well-documented tools.** Prefer the mainstream option with good docs over the clever one.
6. **No agent framework** (PRD §6). Agents are plain functions: prompt in, validated structured output out.

---

## 2. Stack

PRD §6 fixes the first four rows. The rest fill the gaps.

| Concern            | Choice                                                                     | Why                                                                                                                                  |
| ------------------ | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Language / tooling | Python 3.14, **uv** (deps, lockfile, scripts)                               | PRD §6. Check every new dependency ships 3.14 wheels.                                                                              |
| Web framework      | **FastAPI** (async)                                                         | PRD §6. Hosts the Telegram webhook, the summary page and health checks.                                                              |
| Database           | **PostgreSQL**                                                              | PRD §6. Also hosts the job queue, so there's one stateful service.                                                                  |
| Background jobs    | **Procrastinate**                                                           | PRD §6. Postgres-based queue; no Redis or broker to run.                                                                            |
| DB access          | **SQLAlchemy 2.0** (typed, async) + **Alembic** migrations                  | Mature, typed, well documented. DB models stay separate from API schemas and domain types (no SQLModel).                            |
| DB driver          | **psycopg 3**                                                               | Same driver Procrastinate uses.                                                                                                      |
| Validation         | **Pydantic v2**                                                             | API schemas, neutral messages, LLM output schemas, config.                                                                           |
| Config             | **pydantic-settings** (env / `.env`) + **`config/analysis.toml`**           | Two kinds of config: secrets & deployment vs. algorithm parameters (§7).                                                            |
| LLM client         | **`openai` Python SDK** (Responses API) against the **Meta Model API** (`https://api.meta.ai/v1`, Muse models), behind our own `LLMClient` protocol | Development provider (existing credits). The Llama API (`api.llama.com`) was retired in July 2026. The SDK gives retries, timeouts and typed responses; the protocol keeps tests and provider swaps cheap. Responses API everywhere because built-in web search is only available there. |
| Web search         | The Meta Model API's built-in `web_search` tool (Responses API), behind a `SearchClient` protocol | Same provider and credits; results come back with URL citations. Swappable later (Brave, Tavily, Serper). |
| Transcription      | The Meta Model API's transcription model (`muse-voice-transcribe-1.0`, `POST /v1/asr/transcribe`) | Not OpenAI-compatible (custom multipart) and WAV-only, so Telegram's OGG/Opus voice notes are converted with ffmpeg first. Built with CHAT-8; ffmpeg gets an ADR then. |
| Telegram           | **`httpx`** directly against the Bot API (webhook mode)                     | We need ~6 methods. A bot framework would bring its own routing and state, competing with the neutral core.                          |
| Analysis numerics  | **numpy**, seeded `numpy.random.Generator`                                  | Fast, deterministic. No pandas in the engine.                                                                                       |
| Benchmark output   | **matplotlib** (chart) + plain-text table                                   | BEN-3: one command, table + chart.                                                                                                   |
| Summary page       | **Jinja2** server-rendered HTML, minimal hand-written CSS                   | No JS framework. Works in any browser and later as a Telegram Mini App (SUM-7).                                                    |
| Signed links       | stdlib `hmac` (or `itsdangerous`) with an expiry timestamp                  | SUM-1.                                                                                                                              |
| Logging            | **structlog**, JSON output, trace id in a `contextvar`                     | PRD §7 observability.                                                                                                                |
| Testing            | **pytest**, pytest-asyncio, **hypothesis**, **respx** (mock httpx)          | Hypothesis suits ANA-9/ANA-10 property tests; respx fakes Telegram and search HTTP.                                                 |
| Lint / format      | **ruff** (`ruff check`, `ruff format`)                                      | One fast tool.                                                                                                                       |
| Type checking      | **mypy**                                                                     | Most widely documented. Strict (`strict = true`) across `src/` from the start, with the `pydantic.mypy` plugin.                       |
| Architecture lint  | **import-linter**                                                           | Turns the dependency rules in §4 (incl. CH-1) into a CI failure.                                                                    |
| Git hooks          | **pre-commit** (ruff, ruff-format, end-of-file, no large files, secret scan) | Catch issues before CI.                                                                                                             |
| CI                 | **GitHub Actions**                                                          | §9.                                                                                                                                  |
| Local services     | **Docker Compose** for Postgres only; the app runs with `uv run`            | Fast reloads; one container to manage.                                                                                              |
| Dev webhook        | A tunnel from the dev machine (`cloudflared` or ngrok)                     | Telegram needs public HTTPS. Hosting is a production-grade host chosen at first deploy (PRD §8).                                    |

---

## 3. System overview

```
Telegram ──webhook──▶ channels/telegram ──InboundMessage──▶ conversation/
                          ▲                                    │
                          │ OutboundMessage                    ├─ safety keyword pre-check (SAF-1/2) — always first, every message
                          │ (Text, Choice, SummaryLink, Nudge) ├─ onboarding / consent (ONB-1/2/5)
                          └────────────────────────────────────├─ one LLM call: safety class + extraction (~2 s timeout)
                                                               ├─ store via db/ repositories
                                                               └─ enqueue jobs ──▶ jobs/ (Procrastinate)
                                                                                    │
            research (LLM + search) ──▶ verification (LLM, no shared context) ──────┘
                                                │
                                   ingredients stored in db/
                                                │
                    analysis rerun: db/ → AnalysisInput → analysis/ (pure) → AnalysisResult → db/
                                                │
                       summary/ renders AnalysisResult ──▶ signed link ──▶ browser / Mini App
```

The webhook handler only parses, runs the conversation step, replies and enqueues. Anything slow (research, verification, analysis) is a job. This is how CHAT-7 (ack < 3 s) holds.

**The synchronous path (CHAT-7, SAF-1/2):**

1. Keyword/phrase pre-check for severe symptoms. A hit sends the seek-emergency-help warning immediately, with no LLM wait.
2. Consent gate. Before consent, nothing is parsed or stored (ONB-2); the reply asks the user to finish setup.
3. One combined LLM call returns both the safety classification and the extraction, with a ~2 s timeout. Either safety signal firing (step 1 or 3) triggers the warning.
4. In time: the ack can say what was understood ("Burger, fries, latte, got it 👀"). On timeout: a generic ack, and the message is processed in a background job; any follow-up arrives as a second message (inside WhatsApp's 24 h window, so CH-5 allows it).

---

## 4. Module map and dependency rules

Package name: **`hassas`**.

```
src/hassas/
  main.py              # app factory and wiring only (create_app, routers, lifespan)
  config.py            # Settings (env); also reads config/analysis.toml and builds AnalysisConfig
  health.py            # GET /health (liveness; later also DB readiness)
  logging.py           # structlog setup, trace-id contextvar
  domain/              # PRD §5 entities as plain types (dataclasses / Pydantic). Imports nothing from hassas.
  messaging/           # InboundMessage, OutboundMessage (Text, Choice, SummaryLink, Nudge),
                       #   Choice validator (CH-3), neutral markup (CH-8), ChannelCapabilities,
                       #   nudge policy interface (CH-5)
  conversation/        # the pipeline: safety gate, onboarding state machine, intent routing,
                       #   command phrases (CH-6), persona replies
  agents/
    llm.py             # LLMClient protocol + OpenAI-SDK implementation + FakeLLMClient
    search.py          # SearchClient protocol + implementations
    extraction.py      # meal / reaction / cofactor extraction (conversation agent)
    research.py        # research agent (RES-*)
    verification.py    # verification agent (VER-*)
    schemas.py         # Pydantic output schemas for every agent
    prompts/           # one versioned prompt file per agent (*.md)
  analysis/            # PURE. windows, exposure, scoring, statuses, AnalysisInput/AnalysisResult,
                       #   config.py (AnalysisConfig; pure AnalysisConfig.from_toml(text: str))
  summary/             # builds view models from AnalysisResult; templates/ (Jinja2); signed links
  db/
    models.py          # SQLAlchemy models
    repositories/      # one per aggregate (users, meals, reactions, nudges...)
    session.py
    mappers.py         # db models ⇄ domain types; db → AnalysisInput
  jobs/                # Procrastinate app + task definitions (thin: call agents/analysis)
  channels/            # the ONLY place with platform code
    telegram/          # webhook router, Bot API client (httpx), renderer, update models
    fake/              # WhatsApp-constraints fake adapter (CH-9) + CLI chat for local dev
benchmark/             # simulator (BEN-1/2), naive-counting baseline, CLI (BEN-3/4)
config/analysis.toml   # weights, thresholds, status rules, window lengths, active-day rule, episode gap, part-of-day ranges
config/allergen_groups.toml  # the fixed allergen groups (VER-7), EN + AR names
config/ingredients.toml      # seed vocabulary: canonical keys, EN + AR names, aliases, groups (VER-6)
migrations/            # Alembic (created by `alembic init migrations`, which needs the folder not to exist yet)
tests/
  unit/                # pure logic: analysis, messaging, validators, renderers
  integration/         # with real Postgres: repositories, jobs, webhook → DB
  conversation/        # shared suite, parametrized over adapters (CH-9)
  llm/                 # phrase-set evals against the real model (marker: llm)
  fixtures/            # phrase sets (EN/AR/mixed), severe-symptom set, adversarial sets
```

**Dependency rules** (enforced with import-linter contracts in `pyproject.toml`):

| Rule                                                                                     | Why                                                   |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `domain` imports nothing from `hassas`                                                   | Shared vocabulary; no cycles.                         |
| `analysis` imports only `domain` (and its own config types)                              | ANA-9/10 purity; benchmark calls it directly (BEN-4). |
| Nothing outside `channels/` imports `hassas.channels`, except `hassas.main`; no `telegram`/`whatsapp` SDK imports outside it | CH-1. `main` is the only place that wires the app together. |
| `channels` may import `messaging`, `domain`, `config`, `logging`, and the top-level `hassas.conversation` package only | Adapters translate, they don't decide. Never `db`, `agents`, `analysis`, `jobs`, `summary` or conversation submodules. |
| `conversation`, `agents`, `jobs`, `summary` reach the DB only through `db.repositories` | Keeps SQL in one place; easy fakes.                   |
| `agents` never import `conversation` or `channels`                                       | Research/verification run headless in jobs.           |
| `benchmark` imports `analysis` and `domain` only                                         | BEN-4: no LLM, no DB.                                 |
| Nothing imports `hassas.main`                                                            | It is the composition root; keeps the CH-1 exception from becoming a back door. |

Core code sends messages through a sender protocol defined in `messaging/`; `hassas.main` passes in the concrete adapter. `jobs` never import `channels`. Any `hassas.db` module except `repositories` is off limits to those four packages, so a database-to-`AnalysisInput` mapping is reached through a repository method. The contracts are in `pyproject.toml` (`[tool.importlinter]`) and run as `uv run lint-imports`; ADR 0005 explains their shape.

---

## 5. Key contracts

These are the interfaces most code depends on. Change them deliberately.

**Neutral messages** (`messaging/`)

- `InboundMessage`: `user_ref` (channel + external id), `kind` (text / voice / choice_reply / command), `text`, `choice_id`, `audio_ref`, `received_at`, `trace_id`.
- `OutboundMessage` = `Text | Choice | SummaryLink | Nudge`. `Choice` validates ≤ 3 options and labels ≤ 20 chars on construction (CH-3). Text uses the neutral markup (bold, italic, line break, link), ≤ 4,000 chars (CH-8).
- `ChannelCapabilities`: `can_edit`, `max_choice_options`, `has_commands_menu`, `proactive_policy`. The core reads capabilities; it never checks "is this Telegram".

**Adapter protocol** (`channels/`): `parse(raw) -> InboundMessage`, `send(user_ref, messages) -> None`, `capabilities`.

**LLM** (`agents/llm.py`)

```python
class LLMClient(Protocol):
    async def complete_json(
        self, *, model: str, system: str, user: str, schema: type[BaseModel], trace_id: str
    ) -> BaseModel: ...
```

- The implementation wraps `openai.AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)`.
- Uses the Responses API with strict JSON-schema output (`text.format`). Strict mode means output schemas avoid unions (`oneOf`/`allOf`) and recursion, set `additionalProperties: false`, and list every property as required (use nullable fields for optional values). Always validate with the Pydantic schema, and retry once on a validation error.
- Model names per agent come from settings, never hardcoded.
- Every call logs model, prompt version, token usage, latency and trace id (PRD §7 cost tracking).

**Analysis** (`analysis/`)

- `analyze(input: AnalysisInput, config: AnalysisConfig, seed: int) -> AnalysisResult`. A pure function.
- `AnalysisConfig` lives in `analysis/config.py` with a pure `AnalysisConfig.from_toml(text: str)`. Callers (`hassas/config.py` for the app, the benchmark CLI) read `config/analysis.toml` themselves, so `analysis/` does no I/O.
- `AnalysisInput`: the user's timezone, plus meals (event time + precision; dishes → canonical ingredient keys with confidence and allergen groups), reactions (onset + precision, severity, symptom category), and cofactors. All times are UTC-aware datetimes.
- The engine derives everything else itself: active days (ANA-1), episodes from nearby reactions (ANA-13), midpoints for imprecise times (ANA-15). Severity, symptom category and known triggers never reach scoring (ANA-11, ANA-14, ANA-16).
- `AnalysisResult`: `PatternResult`s at ingredient level and at allergen-group level (ANA-12) (key, score, range, status, evidence meal ids), plus the windows used, logging coverage (days logged, active days), the config hash and the seed. Storing the config hash makes any summary reproducible.
- The engine sorts by event time itself. It never trusts input order (ANA-10).

**Agents' output schemas** (`agents/schemas.py`): `ExtractedMeal`, `ExtractedReaction`, `ResearchResult` (ingredient, source URL, source type), `VerifiedIngredient` (canonical key or proposed new key with EN + AR names and groups, confidence, sources, conflict). These are validated at the boundary, so nothing untyped from an LLM reaches the DB.

---

## 6. Data

- **Migrations:** every schema change is an Alembic migration, reviewed in the PR. Never edit an applied migration.
- **Time:** store `timestamptz` in UTC. Store the user's timezone as an IANA name (`Africa/Cairo`). Convert at the edges with `zoneinfo`. Every event has both `event_time` (when it happened) and `logged_at` (when it was told).
- **Identity (CH-7):** `User` has no channel columns. `ChannelIdentity.external_id_hash` = HMAC-SHA256(secret key, `channel:external_id`). It's a keyed hash because Telegram ids are small sequential integers that a plain hash wouldn't protect.
- **Consent (ONB-2, ONB-5):** the conversation pipeline checks consent before parsing or storing anything. Pre-consent messages are not held anywhere: the user is asked to finish setup and, after consent, to send them again. `User` stores `consent_version` and `consent_given_at`; when the current version in settings is newer, the next message asks for consent again before anything else is stored.
- **Ingredient vocabulary (VER-6, VER-7):** `ingredient_keys` table (canonical key, EN + AR names, aliases, allergen groups, status `seed` / `provisional`), seeded from `config/ingredients.toml`. Resolution order: exact alias match (deterministic) → verification agent maps to an existing key → otherwise a provisional key from the agent's proposal. Provisional keys score like any other. Promoting or merging them is a later admin task.
- **Retention:** during development, data is kept as is. Retention, redaction and anonymization are deferred (PRD §8).
- **Deletion (SAF-7):** foreign keys from all user data to `User` use `ON DELETE CASCADE`, so deleting a user removes everything. A test asserts no rows remain.
- **Encryption at rest (SAF-6):** disk-level vs. column-level is decided in ROADMAP phase 15 → ADR.
- **Job arguments** carry ids and the trace id only, never raw message text or health details.

---

## 7. Configuration

| Kind                    | Where                                       | Examples                                                               |
| ----------------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| Secrets & deployment    | Environment / `.env` (git-ignored), read by `Settings` | `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `LLM_API_KEY`, `LLM_BASE_URL` (default `https://api.meta.ai/v1`), `ID_HASH_KEY`, `SUMMARY_LINK_KEY` |
| Model choice            | Environment                                  | `LLM_MODEL_CONVERSATION`, `LLM_MODEL_RESEARCH`, `LLM_MODEL_VERIFICATION`, `LLM_MODEL_TRANSCRIPTION` |
| Product settings        | Environment (with defaults in `Settings`)    | `CONSENT_VERSION`, `SUMMARY_LINK_TTL_DAYS` (30), sync LLM timeout (~2 s) |
| Algorithm parameters    | `config/analysis.toml` (committed, versioned) | confidence weights (ANA-2), window length, active-day minimum meals (ANA-1), episode merge gap (ANA-13), part-of-day ranges (ANA-15), thresholds and status rules (ANA-7), Monte Carlo runs |
| Vocabulary              | `config/allergen_groups.toml`, `config/ingredients.toml` (committed) | allergen groups (VER-7), seed ingredient keys (VER-6) |

- Environment variables have **no prefix** (`DATABASE_URL`, not `APP_DATABASE_URL`): Alembic, Procrastinate and hosts expect the plain names.
- `.env.example` lists every variable with a dummy value, and is updated in the same PR as `Settings`.
- `analysis.toml` changes count as code changes: run the benchmark and put the result in the PR.

---

## 8. Testing strategy

- **Naming:** tests that prove an acceptance check are named by requirement ID: `test_CH_3_choice_rejects_four_options`. One ID may have several tests.
- **Unit** (`tests/unit/`): pure logic, no network, no DB. Most of `analysis/`, `messaging/` and the renderers.
- **Property tests** (hypothesis): ANA-9 (run twice → equal), ANA-10 (shuffled events → equal result), ANA-11 / ANA-14 / ANA-16 (severities, symptom categories or known triggers changed → equal scores).
- **Integration** (`tests/integration/`): real Postgres (Compose locally, a service container in CI). Each test runs in a transaction that's rolled back. Covers repositories, migrations up/down, webhook → DB, jobs.
- **Conversation suite** (`tests/conversation/`): scripted dialogues parametrized over the Telegram adapter (HTTP mocked with respx) and the WhatsApp-constraints fake (CH-9). It uses `FakeLLMClient` with canned outputs, so it's deterministic and free.
- **LLM evals** (`tests/llm/`, `@pytest.mark.llm`): phrase sets against the real model. Covers CHAT-3 (≥ 90%), SAF-1 (100%), SAF-3/4/8 and Caesar → anchovy. Excluded from the default run because they cost credits and are not fully deterministic. Run them before merging changes to prompts or models, and on a schedule.
- **Benchmark** (`benchmark/`): not a test, but a gate. Any change to `analysis/` or `analysis.toml` includes before/after numbers in the PR.
- **Time and randomness:** inject a clock and a seed; never call `datetime.now()` or unseeded random inside logic.

---

## 9. Quality gates and CI

GitHub Actions on every PR and on `main`, fastest checks first:

1. `uv sync --locked`
2. `uv run ruff format --check .`
3. `uv run ruff check .`
4. `uv run mypy src`
5. `uv run lint-imports`
6. `uv run pytest -m "not llm"` (with a Postgres service)

A separate `secrets` job runs gitleaks over the full git history next to these checks.

A PR merges only when all of these and the `secrets` job are green (AGENTS.md git workflow). From ROADMAP phase 13, CI also runs a small benchmark (fewer users) to catch regressions quickly. The full N = 300 run is a local command.

**Commands** _(target — verify against `pyproject.toml` once they exist, then mirror in AGENTS.md)_

```bash
docker compose up -d db          # Postgres
uv run alembic upgrade head      # migrate
uv run fastapi dev               # API with reload
uv run procrastinate --app=hassas.jobs.app worker   # job worker
uv run pytest                    # tests (excl. llm by default via addopts)
uv run pytest -m llm             # LLM evals (costs credits)
uv run python -m benchmark       # BEN-3 table + chart
```

---

## 10. Observability and cost

- One **trace id** per inbound message, created in the adapter, stored in a `contextvar`, written to every log line, and passed into every job it enqueues (PRD §7).
- structlog JSON logs. Never log raw health text or external ids, only internal ids.
- Per LLM/search call: agent, model, prompt version, tokens, latency, cost estimate, trace id. Summed per meal (ROADMAP phase 15).
- Research time per dish is logged against the 15-min soft limit (ROADMAP phase 10).

---

## 11. Security

- Secrets only in the environment. `.env` is git-ignored, and pre-commit runs a secret scanner.
- Telegram webhook verifies `X-Telegram-Bot-Api-Secret-Token` on every request.
- Summary links are HMAC-signed with an expiry (30 days), are not guessable, and are refused after expiry (SUM-1). The signature includes a per-user link secret; rotating it ("cancel my summary links") revokes every earlier link.
- External ids are stored only as keyed hashes (§6).
- LLM output is untrusted input: validated by schema before use, never executed, never rendered without escaping (Jinja autoescape on).
- Dependencies pinned via `uv.lock`; Dependabot (or Renovate) for updates.

---

## 12. Decisions (ADRs)

Decisions are recorded as ADRs in [`docs/adr/`](adr/), using the Michael Nygard template in [`docs/adr/template.md`](adr/template.md). The rules are in AGENTS.md. This section only indexes them.

**Decided 2026-11-10, recorded in the ROADMAP task that first uses them** (phases 1–6):

| #    | Decision                                                      |
| ---- | ------------------------------------------------------------- |
| [0001](adr/0001-record-architecture-decisions.md) | Record architecture decisions (use Nygard ADRs)               |
| 0002 | SQLAlchemy 2.0 + Alembic with psycopg 3                       |
| 0003 | Plain httpx for the Telegram adapter                          |
| 0004 | OpenAI SDK (Responses API) against the Meta Model API, behind `LLMClient` |
| [0005](adr/0005-package-layout-and-import-rules.md) | Enforce package layout and import-linter dependency rules |
| 0006 | Two-tier config: env for secrets, `analysis.toml` for algorithm parameters |

**Decided 2026-11-11, to record with the change that uses them:** no pre-consent holding (ONB-2), ingredient vocabulary + allergen groups (VER-6, VER-7, ANA-12), sync ack path (CHAT-7), Meta built-in web search (behind `SearchClient`), summary links 30 days + revocable (SUM-1), transcription via Meta + ffmpeg (CHAT-8).

**Open → becomes an ADR when decided** (mirrors PRD §8): minimum-evidence threshold and status rules, control-window matching within active days, Muse model per agent, encryption at rest, production hosting.
