# Hassas — Roadmap

**Last updated:** 2026-11-10
**How to use this:** no dates. Work through phases one at a time, whenever there's time. Each phase has a goal, a task list, and a "done when" check. Requirement IDs refer to [PRD.md](PRD.md); the _why_ is in [IDEA.md](IDEA.md).

**Order**

- **Phases 1–5 build the thin end-to-end slice** (all Must requirements). Do them in order; Phase 2 needs no chat or LLM, so it can also run alongside Phase 1.
- **Phases 6–9 add the full Version 1 features** (Should requirements), in any order. Dependencies are noted.
- **Phase 10 (open beta)** needs at least Phases 6 and 9. **Phase 11 (WhatsApp)** comes last.

**Working rules**

- Every phase ends with something that runs, and all tests pass.
- Acceptance checks become automated tests named by ID (`test_LOG_2`).
- Add statistical sophistication one step at a time, and check each step against the benchmark: keep it only if the benchmark doesn't get worse.
- Never trade away: safety (SAF-1–8), determinism (ANA-9, ANA-10), the benchmark.
- All agents use Meta's models via the Meta Model API (PRD §2).
- Small sessions are fine: each task is meant to fit in one or two sittings.

---

## Part A — Thin end-to-end slice (Must)

### Phase 1 — Foundations: project, channel layer, Telegram

**Goal:** a Telegram bot on a channel-neutral core that onboards a user.

- [ ] Project setup per PRD §6: repo, Python/FastAPI/Postgres with uv, CI, `.env` git-ignored
- [ ] Database schema for the PRD §5 entities (User, ChannelIdentity, Meal, Dish, Ingredient, Reaction, Cofactor, PendingNudge, Window, PatternResult)
- [ ] Neutral `InboundMessage` / `OutboundMessage` types: `Text`, `Choice`, `SummaryLink`, `Nudge` (CH-1, CH-2)
- [ ] All channel code in `channels/`; import lint check (CH-1)
- [ ] `Choice` validator: ≤ 3 options, labels ≤ 20 chars, typed replies accepted (CH-3)
- [ ] Neutral markup renderer for Telegram HTML and WhatsApp markup; 4,000-char limit (CH-8)
- [ ] `ChannelIdentity` with hashed external ids; no channel columns on User (CH-7)
- [ ] Proactive-message policy + `PendingNudge`; held nudges delivered on the next user message (CH-5)
- [ ] Telegram adapter: webhook, inline keyboards, commands menu — no message editing yet (CH-10, CHAT-1)
- [ ] WhatsApp-constraints fake adapter + shared conversation test suite in CI (CH-9)
- [ ] Onboarding conversation: language, timezone, consent, optional known triggers (ONB-1)
- [ ] Nothing stored before consent; early logs held or discarded (ONB-2)
- [ ] Choose development hosting: home lab + Cloudflare Tunnel or a cloud host (PRD §8)

**Done when:** a new user onboards in Telegram, and the same onboarding passes on the WhatsApp-constraints fake adapter.

### Phase 2 — Analysis engine + benchmark

**Goal:** the headline result — Hassas beats naive counting — with no chat or LLM involved.

- [ ] Decide starting values: minimum-evidence threshold, status rules, control-window matching rule (PRD §8)
- [ ] Case vs. control comparison with a hard 0–8 h lookback and matched symptom-free windows (ANA-1)
- [ ] Confidence-weighted exposure, weights from config (ANA-2)
- [ ] Pattern statuses + minimum-evidence threshold, all rules in config, one unit test per status (ANA-7, SAF-5)
- [ ] Severity stored but not scored (ANA-11)
- [ ] Deterministic, seeded output (ANA-9)
- [ ] Event-time ordering; full rerun on any insert or edit; shuffled-order test (ANA-10)
- [ ] Simulator: seedable synthetic users (default N = 300) with hidden triggers, 0–8 h delays, staples, noisy logs (BEN-1)
- [ ] Benchmark command: Hassas vs. naive counting, top-1 and top-3, table + chart (BEN-3, BEN-4)

**Done when:** one command prints "naive X% vs Hassas Y%" on 300 users, with Hassas top-1 ≥ 20 points above naive (PRD §1).

### Phase 3 — Conversation agent + safety

**Goal:** Hassas understands meals, reactions and times in English and Arabic, and handles severe symptoms safely.

- [ ] Choose the Meta model for the conversation agent (PRD §8)
- [ ] Background job queue with Procrastinate (needed for CHAT-7; research jobs plug into it in Phase 4)
- [ ] Extract meals from English text: dishes, place, time (CHAT-2)
- [ ] Extract meals from Arabic (any dialect) and mixed text; ≥ 20-phrase test set, ≥ 90% (CHAT-3)
- [ ] Extract reactions: symptoms, onset, severity (CHAT-4)
- [ ] Relative and past times in the user's timezone (CHAT-6)
- [ ] Backfill past meals and reactions in the right order (CHAT-14)
- [ ] Instant ack (< 3 s) with work queued in the background (CHAT-7)
- [ ] Persona: 1–2 lines, user's language and tone (CHAT-9)
- [ ] Commands also work as natural language in EN + AR (CH-6)
- [ ] Severe-symptom detection, ~20 EN/AR phrases incl. dialects, 100%; referral first, no humor (SAF-1, SAF-2)
- [ ] Adversarial test sets: no diagnosis, no dietary advice, off-topic redirect (SAF-3, SAF-4, SAF-8)

**Done when:** the EN/AR phrase set parses at ≥ 90%, and the severe-symptom set is 100%.

### Phase 4 — Research + verification agents

**Goal:** each logged dish becomes a sourced, confidence-rated ingredient list, in the background.

- [ ] Choose the search API and the Meta models for research and verification (PRD §8)
- [ ] Research agent as a background job: structured ingredient list with sources (RES-1)
- [ ] Source priority: official → product databases → recipes (RES-2)
- [ ] Look for hidden components: dressings, sauces, oils, buns (RES-3)
- [ ] Separate verification agent with no shared context (VER-1)
- [ ] One confidence level per ingredient: confirmed / likely / possible (VER-2)
- [ ] Every ingredient keeps a source or "user confirmed" (VER-3)
- [ ] Log research time per dish against the 15-min soft limit

**Done when:** Caesar salad → anchovy (likely or confirmed) with sources, stored in the database.

### Phase 5 — End to end + basic Pattern Summary

**Goal:** the full thin slice: a chat log goes all the way to a summary link.

- [ ] Wire it up: log → research → verification → analysis rerun → summary
- [ ] Summary page behind a signed, expiring link; decide expiry time (SUM-1)
- [ ] Page in the user's language, full RTL layout for Arabic (SUM-1)
- [ ] Ranked ingredient table matching the analysis output (SUM-2)
- [ ] Boundary statement always visible, in the page language (SUM-3)
- [ ] Delete all my data: "delete my data" / /delete (SAF-7)
- [ ] Encryption at rest; secrets audit (SAF-6)
- [ ] Trace id across channel → conversation → research → verification → analysis (PRD §7)
- [ ] Log LLM + search calls per meal; track Meta API credit use (PRD §7)

**Done when:** a meal logged in Telegram leads to a summary link with a correct ranked table, and every Must acceptance check is an automated test that passes.

---

## Part B — Full Version 1 (Should)

### Phase 6 — Smarter analysis

**Goal:** the full scoring from IDEA §2. Add one step at a time, benchmark after each.

- [ ] Delay-weighted 0–8 h lookback, replacing the hard cutoff (ANA-3)
- [ ] Bayesian shrinkage toward "no pattern" (ANA-4)
- [ ] Monte Carlo over uncertain ingredients → seeded score ranges (ANA-5)
- [ ] Cofactor comparison for top patterns (ANA-6) — _needs cofactor data: CHAT-5 (Phase 8) for real users; the simulator covers it for the benchmark_
- [ ] "Most informative next question" selection (ANA-8)
- [ ] Simulator: cofactor-dependent and delayed-trigger users; accuracy per user type (BEN-2)

**Done when:** each step has a recorded benchmark result, and the final engine beats the Phase 2 result.
**Unlocks:** CHAT-10 (Phase 8) needs ANA-8; score ranges on the summary (Phase 9) need ANA-5.

### Phase 7 — Stronger research and verification

**Goal:** better ingredient data with less repeated work.

- [ ] ≥ 3 independent sources when there's no official one; log source count (RES-4)
- [ ] Reuse verified dishes per place (RES-5)
- [ ] Research only new or changed dishes when a meal is amended (RES-6)
- [ ] Flag conflicts between sources (VER-4)
- [ ] User or restaurant confirmation upgrades or removes an ingredient (VER-5)

**Done when:** a second log of the same dish + place makes no search call, and conflicting sources are flagged.

### Phase 8 — Richer logging and conversation

**Goal:** logging that feels effortless, including voice and corrections.

- [ ] Choose the Meta model for voice transcription (PRD §8)
- [ ] Voice notes, EN + AR, transcribed in the core (CHAT-8, CH-11)
- [ ] Cofactor logging, incl. backfilled cofactors: exercise, alcohol, painkillers, illness (CHAT-5)
- [ ] Corrections: "actually it was chicken" (CHAT-12)
- [ ] Add forgotten details to an earlier meal (CHAT-13)
- [ ] Ask which meal when a late detail is ambiguous (CHAT-15)
- [ ] One targeted follow-up at a time, driven by ANA-8 (CHAT-10) — _needs Phase 6_
- [ ] "Ask the restaurant" message drafts (CHAT-11)
- [ ] Optional logging reminders through the nudge policy (CHAT-16)
- [ ] "Summary ready" nudge when the evidence threshold is first reached (PRD §3 flow E)
- [ ] Message editing for acks, with a fallback (CH-4)
- [ ] Timezone inference + "I moved to Cairo" (ONB-3)

**Done when:** ≥ 10 voice notes parse the same as typed text, and the correction and late-detail tests pass.

### Phase 9 — Full Pattern Summary page

**Goal:** the complete summary a user can take to a doctor.

- [ ] Reaction timeline with shaded lookback windows, showing severity (SUM-4, ANA-11)
- [ ] Evidence trail: meals, confidence, sources for top patterns (SUM-5)
- [ ] Uncertainty highlights for fragile patterns (SUM-6)
- [ ] Score ranges in the ranked table (SUM-2 + ANA-5) — _needs Phase 6_
- [ ] Same page as a Telegram Mini App (SUM-7)
- [ ] Mobile and print check, in both languages (doctors may get it printed)

**Done when:** the page shows all IDEA §2 summary sections and looks identical in a browser and the Mini App.

---

## Part C — Launch and grow

### Phase 10 — Open beta

**Goal:** real people using Hassas on Telegram. _Needs Phases 6 and 9 at minimum._

- [ ] Production hosting, backups and monitoring
- [ ] Privacy notice and data-handling page; consent text reviewed
- [ ] Rate limits and per-user cost caps
- [ ] In-chat feedback and a simple way to report problems
- [ ] Invite a small group of testers (Arabic dialects + English)
- [ ] Track usage: logs per user per week, drop-off after onboarding
- [ ] Write up results for the bilingual blog series on moaz-coe.com

**Done when:** a group of testers has used Hassas for 2+ weeks and the feedback is written down.

### Phase 11 — WhatsApp as a premium channel

**Goal:** add WhatsApp without changing the core.

- [ ] Build the WhatsApp adapter against the existing conversation suite
- [ ] Get reminder / summary-ready templates approved
- [ ] Account linking: one user, Telegram + WhatsApp (CH-7)
- [ ] Track message cost per active user; set the premium price (PRD §8)
- [ ] Free/premium plan on User; payment

**Done when:** the full conversation suite passes on the real WhatsApp adapter and a user can link both channels.

**Setup notes**

- Cloud API test number: free, no business verification, up to 5 verified recipients.
- Temporary token expires every 24 h → use a System User permanent token.
- Needs a public HTTPS webhook → Cloudflare Tunnel from the home lab (or ngrok).
- Since 1 Oct 2026, Meta bills service messages.

---

## Later / ideas

Not planned yet; pick up when the phases above are done.

- Cross-reaction detection (IDEA §6): flag ingredients related to a top pattern (e.g. other tree nuts)
- Restaurant side: restaurants describe dishes by voice → ingredient & allergen cards + QR menu; Hassas uses verified restaurant cards instead of searching
- Richer onboarding form: Telegram Mini App, WhatsApp Flow (ONB-4)
- PDF summary sent in chat as a fallback (SUM-8)
- Photo and barcode logging
- Knowledge graph grown from the verified-dish database
- More channels (Messenger, SMS, own app)

**Permanently out:** diagnosis, dietary advice, nutrition features (IDEA §5).

---

## Demo script (for showcases and the portfolio)

1. Voice note in chat → Hassas logs the meal and asks one smart follow-up.
2. Hassas sends the Pattern Summary link.
3. Ranked ingredients: everyday staples ruled out; the hidden trigger ranked top.
4. Evidence trail: which dishes contained it, and the sources behind it.
5. Benchmark chart: Hassas vs. naive counting.
6. Safety switch: a severe-symptom message → humor off, emergency referral.

**Pitch line:** _"حساس means both 'sensitive' and 'sensor.' Hassas is sensitive to every detail, so you don't have to be."_
