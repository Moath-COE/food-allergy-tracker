# Hassas — Architecture

**Status:** Target design — Phase 1 not started · **Last updated:** 2026-11-10
**Context:** [IDEA.md](IDEA.md) (why) · [PRD.md](PRD.md) (what) · [ROADMAP.md](ROADMAP.md) (order) · [adr/](adr/) (why each technical decision was made)

This document describes **how Hassas is built**: the stack, the module structure, the rules between modules, and the technical approach for each ROADMAP phase. It describes the system as it should be _now_. When a decision changes it, update this file and record the decision as an ADR (see §12).

**For agents:** read this before suggesting code. If the code disagrees with this document, flag it and ask which is right. Don't introduce a library, module or pattern that isn't listed here without proposing an ADR first.

---

## 1. Principles

These come from the PRD and shape every choice below.

1. **Channel-neutral core** (CH-1). Platform code lives only in `channels/`. The core speaks neutral messages and designs for WhatsApp's stricter limits.
2. **Analysis is pure code** (ANA-9, ANA-10). No I/O, no LLM, no database in `analysis/`. Same input + seed gives the same output. Event time, never arrival order.
3. **Seams at every external service.** LLM, web search, Telegram and the clock sit behind small protocols, so tests use fakes and providers can be swapped.
4. **Safety before features** (SAF-1–8). The severe-symptom check runs before anything else in the conversation pipeline.
5. **Boring, well-documented tools.** This is a learning project: prefer the mainstream option with good docs over the clever one.
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
| LLM client         | **`openai` Python SDK** pointed at Meta's OpenAI-compatible endpoint, behind our own `LLMClient` protocol | Meta's Llama API exposes an OpenAI-compatible endpoint (`https://api.llama.com/compat/v1/` at time of writing — verify in Phase 3). The SDK gives retries, timeouts and typed responses; the protocol keeps tests and provider swaps cheap. |
| Web search         | TBD in Phase 4 (PRD §8), behind a `SearchClient` protocol                   | Candidates: Brave Search API, Tavily, Serper.                                                                                        |
| Telegram           | **`httpx`** directly against the Bot API (webhook mode)                     | We need ~6 methods. A bot framework would bring its own routing and state, competing with the neutral core.                          |
| Analysis numerics  | **numpy**, seeded `numpy.random.Generator`                                  | Fast, deterministic. No pandas in the engine.                                                                                       |
| Benchmark output   | **matplotlib** (chart) + plain-text table                                   | BEN-3: one command, table + chart.                                                                                                   |
| Summary page       | **Jinja2** server-rendered HTML, minimal hand-written CSS                   | No JS framework. Works in any browser and later as a Telegram Mini App (SUM-7).                                                    |
| Signed links       | stdlib `hmac` (or `itsdangerous`) with an expiry timestamp                  | SUM-1.                                                                                                                              |
| Logging            | **structlog**, JSON output, trace id in a `contextvar`                     | PRD §7 observability.                                                                                                                |
| Testing            | **pytest**, pytest-asyncio, **hypothesis**, **respx** (mock httpx)          | Hypothesis suits ANA-9/ANA-10 property tests; respx fakes Telegram and search HTTP.                                                 |
| Lint / format      | **ruff** (`ruff check`, `ruff format`)                                      | One fast tool.                                                                                                                       |
| Type checking      | **mypy**                                                                     | Most widely documented. Start lenient; tighten per module (`analysis/` and `domain/` strict first).                                 |
| Architecture lint  | **import-linter**                                                           | Turns the dependency rules in §4 (incl. CH-1) into a CI failure.                                                                    |
| Git hooks          | **pre-commit** (ruff, ruff-format, end-of-file, no large files, secret scan) | Catch issues before CI.                                                                                                             |
| CI                 | **GitHub Actions**                                                          | §9.                                                                                                                                  |
| Local services     | **Docker Compose** for Postgres only; the app runs with `uv run`            | Fast reloads; one container to manage.                                                                                              |
| Dev webhook        | **Cloudflare Tunnel** from the home lab (ngrok as fallback)                 | Telegram needs public HTTPS. Final hosting choice is a PRD §8 question.                                                             |

---

## 3. System overview

```
Telegram ──webhook──▶ channels/telegram ──InboundMessage──▶ conversation/
                          ▲                                    │
                          │ OutboundMessage                    ├─ safety gate (SAF-1/2) — always first
                          │ (Text, Choice, SummaryLink, Nudge) ├─ onboarding / consent (ONB-1/2)
                          └────────────────────────────────────├─ extract meal / reaction / cofactor (LLM)
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

---

## 4. Module map and dependency rules

Package name: **`hassas`** (renaming the current `food_allergy_tracker` package is part of the Phase 1 project-setup task).

```
src/hassas/
  main.py              # app factory and wiring only (create_app, routers, lifespan)
  config.py            # Settings (env) + AnalysisConfig loader (TOML)
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
  analysis/            # PURE. windows, exposure, scoring, statuses, AnalysisInput/AnalysisResult
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
config/analysis.toml   # weights, thresholds, status rules, window lengths
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
| Nothing outside `channels/` imports `hassas.channels`; no `telegram`/`whatsapp` SDK imports outside it | CH-1.                                         |
| `channels` may import `messaging`, `domain`, `conversation` (entry point only)          | Adapters translate, they don't decide.                |
| `conversation`, `agents`, `jobs`, `summary` reach the DB only through `db.repositories` | Keeps SQL in one place; easy fakes.                   |
| `agents` never import `conversation` or `channels`                                       | Research/verification run headless in jobs.           |
| `benchmark` imports `analysis` and `domain` only                                         | BEN-4: no LLM, no DB.                                 |

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
    async def complete_json(self, *, model: str, system: str, user: str,
                            schema: type[BaseModel], trace_id: str) -> BaseModel: ...
```

- The implementation wraps `openai.AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)`.
- Ask for structured output with a JSON schema when the endpoint supports it; otherwise use JSON mode. Always validate with the Pydantic schema, and retry once on a validation error.
- Model names per agent come from settings, never hardcoded.
- Every call logs model, prompt version, token usage, latency and trace id (PRD §7 cost tracking).

**Analysis** (`analysis/`)

- `analyze(input: AnalysisInput, config: AnalysisConfig, seed: int) -> AnalysisResult`. A pure function.
- `AnalysisInput`: the user's timezone, plus meals (event time; dishes → ingredients with confidence), reactions (onset, severity), and cofactors. All times are UTC-aware datetimes.
- `AnalysisResult`: a list of `PatternResult` (ingredient, score, range, status, evidence meal ids), plus the windows used, the config hash and the seed. Storing the config hash makes any summary reproducible.
- The engine sorts by event time itself. It never trusts input order (ANA-10).

**Agents' output schemas** (`agents/schemas.py`): `ExtractedMeal`, `ExtractedReaction`, `ResearchResult` (ingredient, source URL, source type), `VerifiedIngredient` (name, confidence, sources, conflict). These are validated at the boundary, so nothing untyped from an LLM reaches the DB.

---

## 6. Data

- **Migrations:** every schema change is an Alembic migration, reviewed in the PR. Never edit an applied migration.
- **Time:** store `timestamptz` in UTC. Store the user's timezone as an IANA name (`Africa/Cairo`). Convert at the edges with `zoneinfo`. Every event has both `event_time` (when it happened) and `logged_at` (when it was told).
- **Identity (CH-7):** `User` has no channel columns. `ChannelIdentity.external_id_hash` = HMAC-SHA256(secret key, `channel:external_id`). It's a keyed hash because Telegram ids are small sequential integers that a plain hash wouldn't protect.
- **Consent (ONB-2):** the conversation pipeline checks consent before any health write. How pre-consent logs are "held" (in memory vs. a short-lived buffer table) is a Phase 1 decision → ADR.
- **Deletion (SAF-7):** foreign keys from all user data to `User` use `ON DELETE CASCADE`, so deleting a user removes everything. A test asserts no rows remain.
- **Encryption at rest (SAF-6):** disk-level vs. column-level is decided in Phase 5 → ADR.
- **Job arguments** carry ids and the trace id only, never raw message text or health details.

---

## 7. Configuration

| Kind                    | Where                                       | Examples                                                               |
| ----------------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| Secrets & deployment    | Environment / `.env` (git-ignored), read by `Settings` | `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `LLM_API_KEY`, `LLM_BASE_URL`, `ID_HASH_KEY`, `SUMMARY_LINK_KEY` |
| Model choice            | Environment                                  | `LLM_MODEL_CONVERSATION`, `LLM_MODEL_RESEARCH`, `LLM_MODEL_VERIFICATION` |
| Algorithm parameters    | `config/analysis.toml` (committed, versioned) | confidence weights (ANA-2), window length, thresholds and status rules (ANA-7), Monte Carlo runs |

- `.env.example` lists every variable with a dummy value, and is updated in the same PR as `Settings`.
- `analysis.toml` changes count as code changes: run the benchmark and put the result in the PR.

---

## 8. Testing strategy

- **Naming:** tests that prove an acceptance check are named by requirement ID: `test_CH_3_choice_rejects_four_options`. One ID may have several tests.
- **Unit** (`tests/unit/`): pure logic, no network, no DB. Most of `analysis/`, `messaging/` and the renderers.
- **Property tests** (hypothesis): ANA-9 (run twice → equal), ANA-10 (shuffled events → equal result), ANA-11 (severities changed → equal scores).
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

A PR merges only when all of these are green (AGENTS.md git workflow). From Phase 2, CI also runs a small benchmark (fewer users) to catch regressions quickly. The full N = 300 run is a local command.

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
- Per LLM/search call: agent, model, prompt version, tokens, latency, cost estimate, trace id. Summed per meal (Phase 5 task).
- Research time per dish is logged against the 15-min soft limit (Phase 4).

---

## 11. Security

- Secrets only in the environment. `.env` is git-ignored, and pre-commit runs a secret scanner.
- Telegram webhook verifies `X-Telegram-Bot-Api-Secret-Token` on every request.
- Summary links are HMAC-signed with an expiry, are not guessable, and are refused after expiry (SUM-1).
- External ids are stored only as keyed hashes (§6).
- LLM output is untrusted input: validated by schema before use, never executed, never rendered without escaping (Jinja autoescape on).
- Dependencies pinned via `uv.lock`; Dependabot (or Renovate) for updates.

---

## 12. Decisions (ADRs)

Decisions are recorded as ADRs in [`docs/adr/`](adr/), using the Michael Nygard template in [`docs/adr/template.md`](adr/template.md). The rules are in AGENTS.md. This section only indexes them.

**To record now** (decided in the architecture discussion, 2026-11-10):

| #    | Decision                                                      |
| ---- | ------------------------------------------------------------- |
| 0001 | Record architecture decisions (use Nygard ADRs)               |
| 0002 | SQLAlchemy 2.0 + Alembic with psycopg 3                       |
| 0003 | Plain httpx for the Telegram adapter                          |
| 0004 | OpenAI SDK against Meta's compatible endpoint, behind `LLMClient` |
| 0005 | Package layout and import-linter dependency rules             |
| 0006 | Two-tier config: env for secrets, `analysis.toml` for algorithm parameters |

**Open → becomes an ADR when decided** (mirrors PRD §8): development hosting (Phase 1), pre-consent holding (Phase 1), minimum-evidence threshold and status rules (Phase 2), control-window matching (Phase 2), Meta model per agent (Phases 3–4), search API (Phase 4), summary link expiry (Phase 5), encryption at rest (Phase 5), transcription model (Phase 8), production hosting (Phase 10).

---

## 13. Phase playbook

How to approach each ROADMAP phase technically. The ROADMAP's "Done when" is the exit check; this lists the modules involved, the order inside the phase and the traps.

### Phase 1 — Foundations

- **Order:** project setup (rename to `hassas`, remove the `items` scaffold, ruff/mypy/import-linter/pre-commit, Compose Postgres, CI) → `domain/` + DB schema + first migration → `messaging/` types, Choice validator, markup renderers → identity hashing → nudge policy + `PendingNudge` → Telegram adapter → fake adapter + conversation suite → onboarding → consent gate.
- Set up CI first, so every later task merges against green checks.
- Build the fake adapter **before** finishing the Telegram one. If onboarding works under WhatsApp constraints first, Telegram is the easy case.
- Onboarding is an explicit state machine (state stored on `User`), not LLM-driven. In Phase 1, typed replies are matched against option text (CH-3); natural-language understanding comes in Phase 3.
- **Trap:** letting Telegram concepts (`chat_id`, `callback_data`) leak into `conversation/`. The import-linter contract should fail if they do.

### Phase 2 — Analysis engine + benchmark

- Entirely in `analysis/`, `benchmark/` and `config/analysis.toml`. No DB, no FastAPI.
- Write the **simulator and naive baseline first**, then the engine. You need something to measure against.
- Decide the PRD §8 thresholds and the control-window rule up front (ADRs), and put the values in `analysis.toml`.
- Hypothesis tests for ANA-9/10/11; one unit test per status (ANA-7).
- Every later change to the engine includes a benchmark result in the PR.

### Phase 3 — Conversation agent + safety

- Set up Procrastinate first (the ack/async split is what makes CHAT-7 work).
- `LLMClient` with the OpenAI SDK; check the Meta endpoint's support for JSON-schema output and record the model choice (ADR).
- The **safety gate** is the first step of the pipeline. It's a fast keyword/phrase pre-check plus an LLM classification, and either one firing triggers the referral. It never depends only on the LLM.
- Build the fixture phrase sets (EN / AR dialects / mixed, severe, adversarial) **before** writing prompts. They are the spec.
- Time resolution (CHAT-6) is deterministic code: the LLM extracts "yesterday dinner"; code turns it into a timestamp in the user's timezone with an injected clock.

### Phase 4 — Research + verification

- Both agents run as jobs. Verification gets **only** dish + research output + sources (VER-1), with a separate prompt and a separate call, no shared message history. Enforce this in the function signature.
- Choose and record the search API (ADR). Put it behind `SearchClient` and use respx-recorded responses in tests.
- Store source URL and type on every ingredient (VER-3). The DB constraint should make an ingredient without a source impossible.

### Phase 5 — End to end + basic summary

- Wire the jobs: verification done → enqueue analysis rerun (full history, ANA-10) → store `AnalysisResult`.
- The summary page is a FastAPI route + Jinja template. Render from the stored `AnalysisResult`, never by re-running analysis inside a request. `dir="rtl"` and translated strings for Arabic (SUM-1).
- Close the safety and ops items: delete (SAF-7), encryption (ADR), trace ids end to end, cost logging.
- Exit check: every Must acceptance check has an ID-named test.

### Phases 6–9 (Part B)

- **6:** one scoring step per PR, each with benchmark before/after; keep it only if the result doesn't get worse. Monte Carlo uses `numpy.random.Generator(seed)` passed in, never global state.
- **7:** a verified-dish cache keyed by normalized (dish, place) in `db/`; research jobs check it first (RES-5).
- **8:** voice arrives as an `audio_ref` from the adapter; download + transcription happen in the core (CH-11). Corrections and late details reuse the Phase 2 full-rerun path.
- **9:** the Mini App is the same route with a different auth (Telegram init-data validation in `channels/telegram/`), not a separate frontend.

### Phases 10–11

- **10:** production hosting ADR, backups, monitoring, rate limits. Semver tags start here.
- **11:** the WhatsApp adapter must pass the existing conversation suite **without changing the core**. If the core has to change, that's a bug in an earlier phase.
