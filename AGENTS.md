# Hassas (food-allergy-tracker)

Hassas is a chat companion that finds patterns between meals and food reactions in a user's own log. Coding agents implement it; the owner (Moaz) reviews every PR and does the final testing.

**Current goal:** a working product, tested internally by the owner and friends. Privacy compliance, data retention, pricing and public launch are deferred (PRD §8 Deferred). Keep designs and questions focused on getting the product working.

## How agents work here
- One task per branch and PR. Start by reading the requirement IDs the task covers (PRD §4) and the matching ARCHITECTURE.md sections.
- Each acceptance check becomes an automated test named by its requirement ID, e.g. `test_CH_3_choice_rejects_four_options`.
- Before opening the PR, run the CI checks locally (ARCHITECTURE.md §9) and get them green.
- The owner merges. Agents open PRs and leave `main` to the owner.
- `docs/ROADMAP.md` is being rewritten (2026-11-11). Until it is, the owner names the next task.

## Source of truth
- `docs/IDEA.md` (why), `docs/PRD.md` (what counts as done, requirement IDs), `docs/ROADMAP.md` (order of work), `docs/ARCHITECTURE.md` (how: stack, module structure, dependency rules) are loaded via `.opencode/opencode.json` and `CLAUDE.md`. If code disagrees with the docs, flag it and ask which one is right.
- Technical decisions are ADRs in `docs/adr/` (see "Architecture decisions"). ARCHITECTURE.md says what is true now; ADRs say why.
- Refer to requirements by ID (`CH-1`, `ANA-9`, `SAF-3`...).
- When a PRD §8 open question is decided, move it to "Resolved" in the PRD and record the ADR in the same PR.

## Non-negotiables
- Safety (`SAF-1`–`SAF-9`): Hassas never diagnoses and never gives dietary advice. A severe symptom gets a clear seek-emergency-help warning first, on every message, even before onboarding; Hassas never acts on the user's behalf. User-facing text says "pattern" and "reaction".
- The analysis engine is deterministic pure code, not an LLM (`ANA-9`, `ANA-10`). Same input + seed gives the same output. Event time, never arrival order.
- Only `channels/` imports channel SDKs (`CH-1`). Design for WhatsApp's stricter limits (≤ 3 choice options, labels ≤ 20 chars, no reliance on editing or proactive sends).
- Research and verification are separate LLM agents with no shared context (`VER-1`). No agent framework.
- Every scoring change is checked against the benchmark and kept only if the benchmark doesn't get worse.
- Secrets live in the environment; `.env` is git-ignored. Nothing from a user is parsed or stored before consent (`ONB-2`).

## Git workflow
- Default branch `main` (remote `origin` on GitHub), always deployable. All work goes through branches.
- GitHub Flow: one short-lived branch per task, opened as a PR into `main`, squash-merged, branch deleted after merge. Merge only when CI is green.
- Branch names: `<type>/<req-id>-<short-kebab-description>`, e.g. `feat/ch-1-neutral-messages`, `fix/ana-10-event-time-order`, `chore/project-setup`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.
- Commits: Conventional Commits, imperative, ≤ 72-char subject, e.g. `feat(channels): add neutral InboundMessage types (CH-1)`. Small, one logical change each. Scope is the top-level module (`channels`, `analysis`, `agents`, `summary`, `db`...).
- PR title follows the commit format (it becomes the squash commit). PR description: requirement IDs covered and how it was verified.
- Commit source, docs and config only; `.env`, secrets and generated artifacts stay out.
- Releases: semver tags `vMAJOR.MINOR.PATCH` on `main`, `v0.x` before a public release.

## Architecture decisions (ADRs)
- Format: Michael Nygard's template. Copy `docs/adr/template.md` (a filled-in example). Sections: title, Date, Status, Context, Decision, Consequences. About a page each.
- File name: `docs/adr/NNNN-kebab-case-title.md`, numbered in order, never reused. Heading: `# N. Title in imperative form`.
- Status: `Proposed` → `Accepted`, later `Deprecated` or `Superseded by [ADR-N](NNNN-....md)`. An Accepted ADR changes only in its status line; a changed decision gets a new ADR that supersedes it.
- Write one when a choice is hard to reverse or spans modules: a new library or service, a module boundary, a data/schema rule, a security choice, or a PRD §8 question being decided.
- The agent writes the ADR in the same PR as the change it justifies: Context names the alternatives considered, Consequences list the downsides. Update the index in ARCHITECTURE.md §12, and the relevant ARCHITECTURE.md section if the design changes.

## Stack & structure
Defined in `docs/ARCHITECTURE.md` (§2 stack, §4 module map and import rules). Python + FastAPI + uv, PostgreSQL, Procrastinate, Meta's Muse models via the Meta Model API (OpenAI SDK, Responses API, behind `LLMClient`), Telegram Bot API (WhatsApp later). A library or pattern outside ARCHITECTURE.md comes with an ADR. Once real config exists, list the verified commands here (uv, test, lint, CI order).

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues on `Moath-COE/food-allergy-tracker` (via `gh`). See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
