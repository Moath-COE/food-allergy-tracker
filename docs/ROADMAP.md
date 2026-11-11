# Hassas — Roadmap

**Last updated:** 2026-11-11
**Context:** [PRD.md](PRD.md) (what counts as done, requirement IDs) · [ARCHITECTURE.md](ARCHITECTURE.md) (how) · [IDEA.md](IDEA.md) (why)

This is the **plan**: the order of work, as one numbered line of small phases. Status lives in GitHub (see "Tracking").

---

## How it works

- **Task** = one branch = one PR, sized for one agent session. It names the requirement IDs it covers; their acceptance checks become ID-named tests (AGENTS.md).
- **Phase** = one outcome the owner can try: in Telegram, in the local fake chat, or with the benchmark command. 2–5 tasks. **You can test** is the exit check.
- **Part A** (phases 1–15) builds every Must requirement as a thin end-to-end slice, in order. **Part B** (phases 16+) adds the Should requirements; its order is set after internal testing.
- Global rules, not repeated per phase: CI green on every PR; the schema grows with the phases (each adds only the tables it uses, as an Alembic migration); each ADR lands in the PR that first uses the decision; any change to `analysis/` or `config/analysis.toml` from phase 13 on includes before/after benchmark numbers and is kept only if the benchmark doesn't get worse.
- Never trade away: safety (SAF-\*), determinism (ANA-9, ANA-10), the benchmark.

**Tracking**

- Each phase is a GitHub milestone named `N. Phase name`.
- When a phase starts, each task becomes an issue titled `[N.M] Task`, in that milestone. Issues are the status; this file has no checkboxes.
- Branch names keep the AGENTS.md format (`feat/ch-3-choice-validator`), not the task number.
- When the plan changes (a task added, split or moved), update this file in the same PR or a small `docs` PR.

---

## Part A — Thin end-to-end slice (Must)

### 1. Repo ready

**You can test:** a PR shows green CI (format, lint, types, import rules, tests with Postgres).
**Covers:** setup (ARCHITECTURE §2, §9)

- 1.1 Tooling: ruff, mypy strict, pytest config with the `llm` marker, pre-commit with a gitleaks secret scan, first test; ADR 0001 (record decisions as ADRs)
- 1.2 GitHub Actions running ARCHITECTURE §9 in order, plus a gitleaks job
- 1.3 Package layout and import-linter contracts for ARCHITECTURE §4, incl. CH-1; adds `lint-imports` to CI; ADR 0005
- 1.4 Docker Compose Postgres 18, `Settings` with unprefixed env vars + `.env.example`, structlog with a trace-id contextvar, a `SELECT 1` integration test; adds the Postgres service to CI; ADR 0006

**Notes:** tooling first, then CI, so every later task merges against green checks. Each later task extends the CI workflow with the check it introduces. The scaffold still disagrees with the docs: `Settings` uses the `APP_` prefix (§7 says no prefix); 1.4 fixes it.

### 2. Neutral core + fake chat

**You can test:** a local CLI chat echoes your messages, running under WhatsApp limits (no edit, ≤ 3 options, no proactive sends, no commands menu).
**Covers:** CH-2, CH-3, CH-8, CH-9

- 2.1 `InboundMessage` / `OutboundMessage` (`Text`, `Choice`, `SummaryLink`, `Nudge`) and the `Choice` validator (CH-2, CH-3)
- 2.2 Neutral markup with Telegram HTML and WhatsApp renderers, 4,000-char limit (CH-8)
- 2.3 `ChannelCapabilities`, WhatsApp-constraints fake adapter, CLI chat (CH-9)
- 2.4 Shared conversation suite, parametrized over adapters, in CI (CH-9)

**Notes:** the fake adapter comes before Telegram: if a flow works under WhatsApp limits, Telegram is the easy case.

### 3. Telegram echo

**You can test:** message the bot through the dev tunnel and get a reply; add it to a group and it posts a notice and leaves.
**Needs:** 2 · **Covers:** CH-1, CH-10 (webhook, sending), CH-12, CHAT-1

- 3.1 Telegram adapter: webhook with secret-token check, httpx Bot API client, `Text` sending, added to the conversation suite with respx; ADR 0003 (CH-1, CH-10, CHAT-1)
- 3.2 Group chats: one short notice, leave, nothing stored (CH-12)

**Notes:** trap: Telegram concepts (`chat_id`, `callback_data`) leaking out of `channels/`. The import-linter contract should catch it.

### 4. Onboarding

**You can test:** a new user onboards (language, timezone, consent incl. 18+, optional known triggers) in Telegram and in the fake chat, and the profile is stored.
**Needs:** 3 · **Covers:** CH-7, CH-10 (keyboards, commands menu), ONB-1

- 4.1 `User` + `ChannelIdentity` tables, keyed hashing of external ids, first migration; ADR 0002 (CH-7)
- 4.2 Onboarding as an explicit state machine of `Text` + `Choice` steps, typed replies matched to option text (ONB-1, CH-3)
- 4.3 Telegram inline keyboards for `Choice`; commands menu (/start, /summary, /language, /delete) (CH-10)

**Notes:** onboarding is code, not the LLM. Natural-language replies come with phase 9.

### 5. Consent + safety gate

**You can test:** a log sent before consent gets "finish setup first", and "send it again" after consent; bumping `CONSENT_VERSION` asks again before anything else; "I can't breathe" gets the emergency warning first, in its language, even from a brand-new user.
**Needs:** 4 · **Covers:** ONB-2, ONB-5, SAF-1, SAF-2 (keyword half), SAF-9

- 5.1 Consent gate and versioning: nothing parsed or stored before consent (ONB-2, ONB-5); ADR: no pre-consent holding
- 5.2 Severe-symptom fixture set (~20 EN/AR phrases incl. dialects) and the keyword pre-check as the first pipeline step (SAF-1, SAF-2)
- 5.3 Banned-words test over fixed reply strings, EN + AR (SAF-9)

**Notes:** the safety gate runs on every message, before the consent gate, and never depends only on the LLM. Fixture sets are the spec: write them before the code.

### 6. Log a meal (English)

**You can test:** "had a burger and fries at Joe's for dinner yesterday" → an ack that says what was understood, in 1–2 lines; the meal is stored with event time and precision, in the right timeline position.
**Needs:** 5 · **Covers:** CHAT-2, CHAT-6, CHAT-9, CHAT-14, SAF-1/SAF-2 (LLM half)

- 6.1 `LLMClient` (OpenAI SDK, Responses API, strict JSON schema, one retry) + `FakeLLMClient`; ADR 0004; ADR: Muse model for the conversation agent
- 6.2 `Meal` / `Dish` tables and repositories
- 6.3 Combined safety + extraction call; persona ack (CHAT-2, CHAT-9, SAF-1/2)
- 6.4 Time resolution with precision (exact / approximate / part of day) and backfill (CHAT-6, CHAT-14)

**Notes:** the LLM extracts "yesterday dinner"; code turns it into a timestamp in the user's timezone with an injected clock. Either safety signal (keyword or LLM) triggers the warning.

### 7. Never wait

**You can test:** with a slow LLM (fake or real), the ack still arrives in < 3 s, and the result follows as a second message; with a "no proactive" policy, it arrives on your next message instead.
**Needs:** 6 · **Covers:** CHAT-7, CH-5

- 7.1 Procrastinate app, worker command, trace id passed into jobs; job arguments carry ids only
- 7.2 ~2 s timeout on the sync call → generic ack → background processing (CHAT-7); ADR: sync ack path
- 7.3 Proactive-message policy + `PendingNudge`; held messages delivered on the next user message (CH-5)

### 8. Reactions + Arabic

**You can test:** "got hives about 2 hours after lunch" is stored with symptom, category, onset and severity; Arabic, dialect and mixed logs work like English ones.
**Needs:** 7 · **Covers:** CHAT-3, CHAT-4

- 8.1 `Reaction` table and reaction extraction (CHAT-4)
- 8.2 EN/AR/mixed phrase set (≥ 20) as an `llm` eval, ≥ 90% (CHAT-3)

### 9. Stays on topic

**You can test:** "send my summary" and "ابعت الملخص" act like /summary; "am I allergic to nuts?" gets no diagnosis; "what should I avoid?" gets no dietary advice; off-topic questions get a short redirect.
**Needs:** 8 · **Covers:** CH-6, SAF-3, SAF-4, SAF-8

- 9.1 Commands as natural language, EN + AR (CH-6)
- 9.2 Adversarial fixture sets and prompt fixes until they pass (SAF-3, SAF-4, SAF-8)

### 10. Ingredient research

**You can test:** log "Caesar salad" (or "my mom's molokhia") → a researched ingredient list with source URLs and types is stored a little later.
**Needs:** 7 · **Covers:** RES-1, RES-2, RES-3, RES-7

- 10.1 `SearchClient` on the Meta built-in `web_search`; ADR: web search; ADR: Muse model for research
- 10.2 Research job: structured output, source priority, hidden components, home-cooked dishes as recipes (RES-1, RES-2, RES-3, RES-7)
- 10.3 Research time per dish logged against the 15-min soft limit

**Notes:** tests use recorded search responses, never live calls.

### 11. Verified ingredients

**You can test:** Caesar salad → anchovy (likely or confirmed) under a canonical key, with sources; "parmesan" and "جبنة" resolve to the same key; "it had garlic" → garlic confirmed.
**Needs:** 10 · **Covers:** VER-1, VER-2, VER-3, VER-6, VER-7

- 11.1 `config/allergen_groups.toml` (16 groups, EN + AR), seed `config/ingredients.toml`, `ingredient_keys` table; ADR: ingredient vocabulary + allergen groups (VER-6, VER-7)
- 11.2 Verification job: separate prompt and call, input is only dish + research output + sources; one confidence level and ≥ 1 source per ingredient (VER-1, VER-2, VER-3); ADR: Muse model for verification
- 11.3 Key resolution: exact alias → agent maps to an existing key → provisional key; user-listed ingredients stored as confirmed (VER-6, RES-7)

**Notes:** enforce VER-1 in the function signature, and make an ingredient without a source impossible at the DB level.

### 12. Benchmark baseline

**You can test:** `uv run python -m benchmark` prints naive-counting top-1 / top-3 accuracy on 300 synthetic users, with a chart.
**Covers:** BEN-1, BEN-3 (naive side), BEN-4

- 12.1 `AnalysisInput` / `AnalysisResult` types and `config/analysis.toml` loader
- 12.2 Seedable simulator: hidden triggers (often inside dishes), 0–8 h delays, staples, noisy logs, unlogged days, imprecise times, production key and group structure (BEN-1)
- 12.3 Naive counting + frequency-normalized variant; benchmark CLI with table + chart (BEN-3, BEN-4)

**Notes:** only `analysis/`, `benchmark/` and `config/`. No DB, no LLM, no FastAPI. This phase can start any time after phase 1 if there's a reason to.

### 13. Engine beats naive

**You can test:** the benchmark prints "naive X% vs Hassas Y%" with Y ≥ X + 20 on top-1 (PRD §1).
**Needs:** 12 · **Covers:** ANA-1, ANA-2, ANA-7, ANA-9, ANA-10, ANA-11, ANA-12, ANA-13, ANA-14, ANA-15, ANA-16, SAF-5

- 13.1 Event-time sorting, episodes (ANA-13), active days (ANA-1), midpoints for imprecise times (ANA-15)
- 13.2 Case vs. control scoring with a hard 0–8 h window and confidence weights, at ingredient and allergen-group level (ANA-1, ANA-2, ANA-12); ADR: control-window matching rule
- 13.3 Statuses and the minimum-evidence threshold, one unit test per status (ANA-7, SAF-5); ADR: thresholds and status rules
- 13.4 Hypothesis property tests for ANA-9, ANA-10, ANA-11, ANA-14, ANA-16; small benchmark in CI

### 14. Summary page

**You can test:** send "summary" in Telegram → a link → a page in your language (RTL for Arabic) with ranked ingredient and allergen-group tables, statuses, "generated on" and the boundary statement; "cancel my summary links" kills old links.
**Needs:** 11, 13 · **Covers:** SUM-1, SUM-2, SUM-3, ANA-10 (rerun on change)

- 14.1 Analysis-rerun job: any new or changed meal, ingredient or reaction → full-history rerun → stored `AnalysisResult` (ANA-10)
- 14.2 Signed, expiring (30 days), revocable links via the per-user link secret; ADR: summary links (SUM-1)
- 14.3 Jinja page from the stored result: tables, boundary statement, EN + AR with RTL, banned-words test on templates (SUM-1, SUM-2, SUM-3, SAF-9)

**Notes:** the page renders the stored `AnalysisResult`; it never runs analysis inside a request.

### 15. Ready to test

**You can test:** "delete my data" removes everything; logs show one trace id from webhook to analysis, and LLM + search cost per meal.
**Needs:** 14 · **Covers:** SAF-6, SAF-7, PRD §7 (observability, cost)

- 15.1 Delete my data / /delete, cascade + no-rows-left test (SAF-7)
- 15.2 Encryption at rest + secrets audit; ADR: encryption at rest (SAF-6)
- 15.3 Trace id end to end; per-call and per-meal LLM + search cost logging
- 15.4 Audit: every Must acceptance check has a passing ID-named test

### → Internal testing

The owner (and anyone they invite) uses Hassas for real. Problems become fix tasks; once they're done, Part B starts, in an order chosen from what testing showed.

---

## Part B — Full Version 1 (Should)

Order is set after internal testing; tasks are written when a phase is picked. Each needs Part A.

| #   | Phase                        | Covers                                                    |
| --- | ---------------------------- | --------------------------------------------------------- |
| 16  | Smarter scoring              | ANA-3, ANA-4                                              |
| 17  | Score ranges                 | ANA-5, ranges on the summary (SUM-2)                      |
| 18  | Cofactors                    | CHAT-5, ANA-6, BEN-2                                      |
| 19  | Corrections + late details   | CHAT-12, CHAT-13, CHAT-15                                 |
| 20  | Smart follow-ups             | ANA-8, CHAT-10, CHAT-11                                   |
| 21  | Research reuse + conflicts   | RES-4, RES-5, RES-6, VER-4, VER-5                         |
| 22  | Voice notes                  | CHAT-8, CH-11                                             |
| 23  | Reminders + nudges           | CHAT-16, summary-ready nudge (PRD §3 flow E), CH-4        |
| 24  | Timezone changes             | ONB-3                                                     |
| 25  | Full summary                 | SUM-4, SUM-5, SUM-6, SUM-9, SUM-10                        |
| 26  | Mini App                     | SUM-7                                                     |

**Notes for when they're picked**

- **16, 17:** one scoring step per PR, benchmark before/after each. Monte Carlo takes a `numpy.random.Generator(seed)` passed in, never global state.
- **20:** needs 16–17 for a meaningful "most informative" choice; CHAT-10 follow-ups come only from ANA-8.
- **21:** a verified-dish cache keyed by normalized (dish, place) in `db/`; research jobs check it first.
- **19:** corrections and late details reuse the phase 14 full-rerun path.
- **22:** the adapter passes an `audio_ref`; download, WAV conversion (ffmpeg, ADR) and transcription happen in the core.
- **26:** the same route with Telegram init-data auth (validated in `channels/telegram/`), not a separate frontend.

---

## Later

- WhatsApp adapter (must pass the conversation suite without changing the core; if the core has to change, that's a bug), account linking across channels (CH-7)
- Cross-reaction detection (IDEA §6)
- Richer onboarding form: Telegram Mini App, WhatsApp Flow (ONB-4)
- PDF summary in chat as a fallback (SUM-8)
- Per-category scoring (ANA-14), benchmark-gated
- Photo and barcode logging
- Restaurant side: voice dish cards, QR menus
- Knowledge graph from the verified-dish database
- More channels (Messenger, SMS, own app)

**Deferred decisions** (privacy and compliance, retention, terms, pricing, public launch, production hosting): PRD §8.

**Permanently out:** diagnosis, dietary advice, nutrition features (IDEA §5).

---

## Demo script (for showcases and the portfolio)

1. Voice note in chat → Hassas logs the meal and asks one smart follow-up.
2. Hassas sends the Pattern Summary link.
3. Ranked ingredients: everyday staples ruled out; the hidden trigger ranked top.
4. Evidence trail: which dishes contained it, and the sources behind it.
5. Benchmark chart: Hassas vs. naive counting.
6. Safety switch: a severe-symptom message → humor off, emergency warning.

**Pitch line:** _"حساس means both 'sensitive' and 'sensor.' Hassas is sensitive to every detail, so you don't have to be."_
