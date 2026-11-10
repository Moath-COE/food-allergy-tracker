# Hassas — PRD (v0.4)

**Status:** Draft — nothing built yet · **Owner:** Moaz · **Last updated:** 2026-11-10
**Context:** [IDEA.md](IDEA.md) (vision & rationale) · [ROADMAP.md](ROADMAP.md) (build phases & tasks)

This document defines **what must be true for each part to count as done**. For _why_, see IDEA.md. For _in what order_, see ROADMAP.md.

---

## 1. Goal & success

**Goal:** A user onboards and logs meals and reactions in Telegram (English or Arabic), Hassas researches and verifies the ingredients in the background, and a Pattern Summary page ranks the hidden trigger above everyday staples. A synthetic benchmark shows Hassas beats naive counting. The core is channel-agnostic so WhatsApp can be added later as a premium channel without changing it.

**Success metrics**

| Metric                            | Target                                                                                                                       |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Benchmark: true trigger ranked #1 | Hassas top-1 accuracy ≥ 20 percentage points above naive counting, on N = 300 synthetic users (report both, e.g. "X% vs Y%") |
| Log → acknowledgment latency      | < 3 s (p90)                                                                                                                  |
| Severe-symptom test set           | 100% routed to emergency referral                                                                                            |
| Analysis determinism              | Same log + same seed → identical output                                                                                      |
| Channel independence              | Full conversation test suite passes against both the Telegram adapter and a WhatsApp-constraints fake adapter (CH-9)         |

---

## 2. Scope

**Priorities**

- **Must** — the thin end-to-end slice + safety (ROADMAP Part A).
- **Should** — full Version 1 features (IDEA §9). Build after all Musts work (ROADMAP Part B).
- **Later** — not in this build.

**Channel decision**

- **Telegram is the primary channel** — free Bot API, no 24-hour messaging window, no per-message fees, no business verification; good for development and an open beta.
- **WhatsApp comes later as a premium channel.** WhatsApp charges per message and limits messages Hassas sends on its own, so it fits a paid tier.
- **Design rule:** the core (conversation logic, agents, analysis, summary) speaks in channel-neutral terms and must work within the _stricter_ of the two channels' limits. Telegram-only features are progressive enhancements: the product must stay fully usable without them. See §4 CH.

**Model decision**

- All LLM agents (conversation, research, verification) and voice transcription run on **Meta's models via the Meta Model API** (existing credits). Which Meta model per agent is still open (§8).

**Out of scope (this build)**

- Building the WhatsApp adapter (designed for via CH-\*, built later as premium)
- Other channels (Messenger, SMS, own app)
- Restaurant-side features (voice dish cards, QR menus)
- Photo or barcode logging
- Cross-reaction detection (IDEA §6) — Later
- Accounts/auth beyond the chat identity (CH-7 keeps the door open for linking channels)
- Knowledge graph (verified dishes live in an ordinary database)
- Any diagnosis, dietary advice, or nutrition features (permanently out — see IDEA §5)

---

## 3. Core flows

- **O. Onboard:** first contact → greeting in Hassas's voice → language + timezone → consent (not a diagnosis; health data stored) → optional known/suspected triggers → short "how to log" example. No health data stored before consent.
- **A. Log a meal:** user message → instant ack → background research + verification → ingredients stored → (if needed) one follow-up question.
- **B. Report a reaction:** user message → calm reply → symptom + timing captured → stored.
- **C. Severe symptom:** user message → humor off → emergency-care referral **before** anything else.
- **D. Log a cofactor** _(Should — CHAT-5)_: exercise / alcohol / painkiller / illness → stored with time.
- **E. Get the summary:** user asks → link to Pattern Summary page. _(Should: a "summary ready" nudge when the minimum-evidence threshold is first reached.)_
- **F. Late or out-of-order info:** user adds a forgotten detail to an earlier meal, or logs a past meal/reaction after later entries → matched to the right meal (or placed at its real time) → only the changed parts researched → analysis rerun on the full history.
- **N. Nudge (proactive):** Hassas has something to say without being asked (pending follow-up, logging reminder, summary ready) → channel policy decides whether to send now, hold until the user's next message, or drop.

---

## 4. Requirements

Acceptance checks should become automated tests where possible (`tests/` named by ID, e.g. `test_LOG_2`).

### CH — channel layer

| ID    | Requirement                                                                                                                                                                                                                                    | Pri    | Acceptance check                                                                      |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------- |
| CH-1  | Core never imports a channel SDK. Each channel is an adapter that converts platform updates to a neutral `InboundMessage` (text, voice, choice reply, command intent) and neutral `OutboundMessage`s back to platform calls                    | Must   | Lint/import check: no `telegram`/`whatsapp` imports outside `channels/`               |
| CH-2  | Outbound messages are semantic: `Text`, `Choice` (question + options), `SummaryLink`, `Nudge`. Adapters decide the rendering (inline keyboard, reply buttons, list…)                                                                           | Must   | Core code builds no platform-specific payloads                                        |
| CH-3  | `Choice` respects the strictest limits: ≤ 3 options, option label ≤ 20 chars, and a typed reply is always accepted as an answer                                                                                                                | Must   | Validator rejects longer choices; typing the option text works the same as tapping it |
| CH-4  | Message editing is optional. Core may request "update the earlier ack"; adapters without edit support send a new short message instead                                                                                                         | Should | Same flow passes with edit enabled and disabled                                       |
| CH-5  | Proactive messages go through a per-channel policy (Telegram: send any time, rate-limited; WhatsApp: only inside the 24 h window or via an approved template, otherwise hold). Core must work if a nudge is held until the user's next message | Must   | With "no proactive" policy, pending follow-ups are delivered on the next user message |
| CH-6  | Every command also works as natural language in both languages ("/summary" = "send my summary" = "ابعت الملخص"; same for delete, language)                                                                                                     | Must   | Each command has EN + AR phrase tests                                                 |
| CH-7  | Identity: internal `user_id`; channel accounts live in a separate `ChannelIdentity` table (channel, hashed external id). One user may later link several channels                                                                              | Must   | Schema has no channel-specific column on User                                         |
| CH-8  | Outbound text uses a small neutral markup (bold, italic, line breaks, links) rendered per channel; max 4,000 chars per message                                                                                                                 | Must   | Renderer tests for Telegram HTML and WhatsApp markup                                  |
| CH-9  | Shared conversation test suite runs against a fake adapter configured with WhatsApp constraints (no edit, ≤ 3 buttons, no proactive outside window, no commands menu)                                                                          | Must   | Suite passes in CI                                                                    |
| CH-10 | Telegram adapter: Bot API webhook, inline keyboards for `Choice`, commands menu (/start, /summary, /language, /delete). Message editing is added with CH-4                                                                                     | Must   | Manual check + adapter tests                                                          |
| CH-11 | Voice notes arrive as an audio file reference regardless of channel; transcription happens in the core                                                                                                                                         | Should | Telegram voice note goes through the same path as CHAT-8                              |

### ONB — onboarding

| ID    | Requirement                                                                                                                                                | Pri    | Acceptance check                                         |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------------------------------------------------------- |
| ONB-1 | Onboarding is a chat conversation built from `Text` + `Choice` steps (works on any channel); language, timezone, consent required; known triggers optional | Must   | Runs end to end on the WhatsApp-constraints fake adapter |
| ONB-2 | No meal, reaction or cofactor is stored before consent; logs sent earlier are held and stored after consent, or discarded if declined                      | Must   | Log before consent → not in DB until consent given       |
| ONB-3 | Timezone inferred from language/phone hints where possible and confirmed with one `Choice`; user can change it later                                       | Should | Change via "I moved to Cairo" updates timezone           |
| ONB-4 | Richer onboarding form (Telegram Mini App now, WhatsApp Flow later) is optional and fills the same onboarding record                                       | Later  | Both paths produce identical stored profile              |

### CHAT — conversation & logging

| ID      | Requirement                                                                                                                              | Pri    | Acceptance check                                                                                                  |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| CHAT-1  | Receive and reply to text messages through the channel layer (Telegram first)                                                            | Must   | Message to the bot gets a reply                                                                                   |
| CHAT-2  | Extract meals from English text: dish(es), place (if any), time                                                                          | Must   | "Had a cheeseburger and fries from Joe's, then a latte" → 3 items, place = Joe's on burger/fries, time ≈ now      |
| CHAT-3  | Extract meals from Arabic (any dialect) and mixed text                                                                                   | Must   | Fixed set of ≥ 20 EN/AR/mixed phrases; ≥ 90% parsed correctly                                                     |
| CHAT-4  | Extract reactions: symptom(s), onset time, rough severity                                                                                | Must   | "Got hives about 2 hours after lunch" → symptom = hives, onset = lunch + 2h                                       |
| CHAT-5  | Extract cofactors: exercise, alcohol, painkillers, illness — including backfilled past cofactors (as CHAT-14)                            | Should | Each type recognized in EN and AR test phrases                                                                    |
| CHAT-6  | Handle relative/past times ("yesterday dinner", "الصبح")                                                                                 | Must   | Timestamp resolved relative to message time in user's timezone                                                    |
| CHAT-7  | Acknowledge every log instantly; research runs async                                                                                     | Must   | Ack < 3 s even when research takes 30 s+                                                                          |
| CHAT-8  | Voice notes transcribed and handled like text (EN + AR)                                                                                  | Should | Same parse result as the equivalent typed message on ≥ 10 test notes                                              |
| CHAT-9  | Persona: brief (1–2 lines), matches user language and tone                                                                               | Must   | Spot-check: replies ≤ 2 lines, same language as user                                                              |
| CHAT-10 | Ask at most one follow-up at a time, only when it changes the analysis                                                                   | Should | Follow-up comes from ANA-8 output, never generic                                                                  |
| CHAT-11 | Draft "ask the restaurant" message for an uncertain ingredient                                                                           | Should | Message names dish + ingredient, is short, in the user's language                                                 |
| CHAT-12 | Users can correct a log ("actually it was chicken, not beef")                                                                            | Should | Stored entry updated, analysis rerun                                                                              |
| CHAT-13 | Add forgotten details to an earlier meal (a side, sauce, drink, place) after later logs. Simple version first: most recent matching meal | Should | Log lunch, then dinner, then "oh, lunch also had garlic sauce" → sauce added to lunch, not dinner                 |
| CHAT-14 | Backfill: log a meal or reaction that happened before already-logged entries (cofactor backfill comes with CHAT-5)                       | Must   | "Forgot to say, I had a Snickers yesterday at 4pm" → stored at yesterday 16:00, ordered correctly in the timeline |
| CHAT-15 | Resolve which earlier meal a late detail belongs to; ask one short question if ambiguous                                                 | Should | Two meals at the same place today → Hassas asks "lunch or dinner?" instead of guessing                            |
| CHAT-16 | Gentle logging reminders at user-chosen times, sent as `Nudge` through CH-5 policy; user can turn them off                               | Should | Reminder off → none sent; on WhatsApp-constraints adapter → held, not sent                                        |

### RES — ingredient research

| ID    | Requirement                                                                     | Pri    | Acceptance check                                                                |
| ----- | ------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------- |
| RES-1 | For each dish, search the web and return a structured ingredient list           | Must   | Output validates against schema (ingredient, source URL, source type)           |
| RES-2 | Follow source priority: official restaurant/brand → product databases → recipes | Must   | When an official allergen page exists, it appears as a source                   |
| RES-3 | Look for likely hidden components (dressings, sauces, oils, buns)               | Must   | Caesar salad → anchovy appears; pesto → pine nuts appears                       |
| RES-4 | Use ≥ 3 independent sources when no official source exists                      | Should | Source count logged per dish                                                    |
| RES-5 | Reuse verified dishes per place instead of re-searching                         | Should | Second log of same dish + place makes no search call                            |
| RES-6 | When a meal is amended, research only the new or changed dishes                 | Should | Adding a sauce to a verified meal triggers one research job, for the sauce only |

### VER — verification

| ID    | Requirement                                                               | Pri    | Acceptance check                                        |
| ----- | ------------------------------------------------------------------------- | ------ | ------------------------------------------------------- |
| VER-1 | Separate agent (own prompt, no shared context) checks research output     | Must   | Verifier receives only dish + research output + sources |
| VER-2 | Assign confidence per ingredient: confirmed / likely / possible           | Must   | Every stored ingredient has exactly one level           |
| VER-3 | Every ingredient keeps at least one source citation (or "user confirmed") | Must   | No stored ingredient without a source                   |
| VER-4 | Flag conflicts between sources instead of picking silently                | Should | Conflicting test dish → `conflict` flag set             |
| VER-5 | User/restaurant confirmation upgrades or removes an ingredient            | Should | "Yes, it had peanut sauce" → peanut = confirmed         |

### ANA — analysis engine (deterministic code, no LLM)

| ID     | Requirement                                                                                                                                                                                                                                                                | Pri    | Acceptance check                                                           |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------- |
| ANA-1  | Case vs. control comparison: exposure in a hard 0–8 h lookback window before each reaction vs. matched symptom-free control windows of the same length                                                                                                                     | Must   | Beats naive counting on benchmark (BEN-3)                                  |
| ANA-2  | Confidence-weighted exposure (confirmed ≈ 1.0, likely ≈ 0.7, possible ≈ 0.3; configurable)                                                                                                                                                                                 | Must   | Weights read from config, not hardcoded                                    |
| ANA-3  | Delay-weighted 0–8 h lookback, replacing ANA-1's hard cutoff                                                                                                                                                                                                               | Should | Benchmark accuracy on delayed-trigger users improves vs. ANA-1 alone       |
| ANA-4  | Bayesian shrinkage toward "no pattern"                                                                                                                                                                                                                                     | Should | 2 coincidences never produce a Strong pattern (unit test)                  |
| ANA-5  | Monte Carlo over uncertain ingredients → score range                                                                                                                                                                                                                       | Should | Each score has a [low, high] range; fixed seed reproduces it               |
| ANA-6  | Cofactor comparison for top patterns                                                                                                                                                                                                                                       | Should | Cofactor-dependent synthetic users flagged as such                         |
| ANA-7  | Pattern statuses (Collecting / Emerging / Strong / Can't be assessed / Unlikely) with minimum-evidence threshold. All thresholds and status rules (incl. the "present in nearly every / almost no window" cut-offs) live in config; starting values set in ROADMAP Phase 2 | Must   | Below threshold → only "Collecting" shown; each status has a unit test     |
| ANA-8  | Pick the single unconfirmed ingredient that would change the ranking most                                                                                                                                                                                                  | Should | Returns ingredient + meal; drives CHAT-10                                  |
| ANA-9  | Deterministic: same input + seed → same output                                                                                                                                                                                                                             | Must   | Run twice, diff is empty                                                   |
| ANA-10 | Use event time (when it happened), never arrival order; any insert, edit or late detail triggers a rerun over the full history                                                                                                                                             | Must   | Same events entered in shuffled order → identical output to in-order entry |
| ANA-11 | Reaction severity is stored and shown in the summary, but not used in scoring in Version 1 (every reaction counts equally)                                                                                                                                                 | Must   | Changing severities leaves scores unchanged                                |

### SUM — Pattern Summary page

| ID    | Requirement                                                                                                                                                         | Pri    | Acceptance check                                                                                                    |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------- |
| SUM-1 | Standalone web page (works in any browser) reached by a signed, expiring link sent in chat. Shown in the user's language, with full right-to-left layout for Arabic | Must   | Link works on mobile; not listable/guessable; expired link refused; Arabic user gets an RTL Arabic page             |
| SUM-2 | Ranked ingredient table: score, status (+ range when ANA-5 exists)                                                                                                  | Must   | Matches analysis output exactly                                                                                     |
| SUM-3 | Boundary statement always visible                                                                                                                                   | Must   | Text present (in the page language): "Patterns in your own log, for discussion with a clinician — not a diagnosis." |
| SUM-4 | Reaction timeline with shaded lookback windows                                                                                                                      | Should | Visual check                                                                                                        |
| SUM-5 | Evidence trail for top patterns: meals, confidence, sources                                                                                                         | Should | Each top ingredient links to its meals + citations                                                                  |
| SUM-6 | Uncertainty highlights: patterns depending on unconfirmed ingredients                                                                                               | Should | Shown when any top pattern is fragile                                                                               |
| SUM-7 | Same page opens as a Telegram Mini App (auth via Telegram init data instead of the link token); no feature exists only inside the Mini App                          | Should | Page content identical in browser and Mini App                                                                      |
| SUM-8 | Fallback: PDF sent in chat                                                                                                                                          | Later  | Only if the page is unavailable                                                                                     |

### SAF — safety

| ID    | Requirement                                                                                                                           | Pri  | Acceptance check                                                      |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------- |
| SAF-1 | Detect severe symptoms (throat swelling, breathing trouble, fainting, etc.) in EN + AR                                                | Must | Fixed test set (~20 phrases incl. dialects) → 100% detected           |
| SAF-2 | Severe symptoms → emergency referral first, no humor, before any logging                                                              | Must | Reply's first line is the referral; no emoji/jokes                    |
| SAF-3 | Never diagnose ("you're allergic to X")                                                                                               | Must | Adversarial test set ("am I allergic to nuts?") → no diagnostic claim |
| SAF-4 | Never give dietary instructions ("avoid X", diets, calories)                                                                          | Must | Adversarial test set → redirects to clinician                         |
| SAF-5 | No patterns shown before the minimum-evidence threshold                                                                               | Must | Same as ANA-7                                                         |
| SAF-6 | Health data encrypted at rest; secrets out of the repo                                                                                | Must | DB encryption on; `.env` git-ignored; no tokens in code               |
| SAF-7 | User can delete all their data ("delete my data" / /delete)                                                                           | Must | All rows for that user and their channel identities removed           |
| SAF-8 | Stay a narrow food-and-reaction tool; off-topic requests get a short redirect (keeps WhatsApp's AI-provider policy satisfiable later) | Must | Off-topic test set → brief redirect, no general answers               |

### BEN — benchmark

| ID    | Requirement                                                                                                                  | Pri    | Acceptance check                                                |
| ----- | ---------------------------------------------------------------------------------------------------------------------------- | ------ | --------------------------------------------------------------- |
| BEN-1 | Simulator generates N synthetic users (default 300): hidden trigger (often inside a dish), 0–8 h delays, staples, noisy logs | Must   | Configurable N, seedable                                        |
| BEN-2 | Simulator includes cofactor-dependent and delayed-trigger users                                                              | Should | Separate accuracy reported per user type                        |
| BEN-3 | Compare Hassas engine vs. naive counting: top-1 and top-3 accuracy                                                           | Must   | Single command outputs table + chart; top-1 meets the §1 target |
| BEN-4 | Benchmark runs on the analysis engine directly (no LLM calls)                                                                | Must   | Runs offline in minutes                                         |

---

## 5. Key entities

Shared vocabulary for agents, database and engine.

- **User** — internal id, language, timezone, consent (given at, version), reminder settings, plan (free / premium)
- **ChannelIdentity** — user, channel (telegram / whatsapp), hashed external id, linked at
- **Meal** — user, event time (when eaten), logged time (when told), place (optional), list of Dishes, raw message(s), edit history
- **Dish** — name, place (optional), list of Ingredients, verified flag, added-late flag
- **Ingredient** — name, confidence (confirmed / likely / possible), sources[], conflict flag
- **Reaction** — user, onset time, symptoms, severity (stored, not scored — ANA-11), raw message
- **Cofactor** — user, type (exercise / alcohol / painkiller / illness), time
- **PendingNudge** — user, kind (follow-up / reminder / summary-ready), payload, created at, delivered at
- **Window** — case (before a reaction) or control (matched symptom-free), start/end
- **PatternResult** — ingredient, score, range, status, evidence (meal ids)

---

## 6. Tech stack

- **Language & API:** Python, FastAPI, managed with uv
- **Database:** PostgreSQL (verified dishes in ordinary tables)
- **Background jobs:** Procrastinate (Postgres-based task queue)
- **Agents:** Meta's models via the Meta Model API; no agent framework
- **Channels:** Telegram Bot API now; WhatsApp Cloud API later

---

## 7. Non-functional

- **Latency:** ack < 3 s; background research + verification per dish < 15 min (soft limit; timeouts are logged, not fatal).
- **Models:** all LLM agents and voice transcription run on Meta's models via the Meta Model API (§2).
- **Determinism:** analysis engine is pure code, seeded randomness only.
- **Cost:** log LLM + search calls per meal; track Meta API credit use; track messaging cost per active user per channel (Telegram ≈ 0; WhatsApp priced per message) to size the premium tier.
- **Languages:** English, Arabic (all dialects), mixed — in input, replies and the summary page.
- **Privacy:** minimal data stored; raw messages kept only as needed for corrections; channel ids stored hashed.
- **Observability:** each log has a trace id across channel → conversation → research → verification → analysis.

---

## 8. Open questions

- Which Meta model for each agent (conversation, research, verification)? _(ROADMAP Phases 3–4)_
- Which Meta model for voice transcription? _(Phase 8)_
- Starting values for the minimum-evidence threshold and status rules? _(Phase 2)_
- Control-window matching rule: same time of day only, or also day of week? _(Phase 2)_
- Which search API for the research agent? _(Phase 4)_
- Hosting: home lab + Cloudflare Tunnel, or a cloud host? _(Phase 1 for development, Phase 10 for production)_
- Summary page links: expiry time? _(Phase 5)_
- WhatsApp premium: price point vs. per-active-user message cost; which reminder templates to get approved. _(Phase 11)_
