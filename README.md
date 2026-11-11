# Hassas (حساس)

> _The sensor for your sensitivities._

Hassas is a chat companion that helps people find the hidden food triggers behind their reactions. Users log meals and symptoms by text or voice note in Telegram (WhatsApp later), in English or Arabic. Hassas researches and verifies the ingredients in each dish, then looks for patterns in the user's own log. It produces a Pattern Summary page they can take to a doctor.

The name is Arabic and means both "sensitive" and "sensor".

**Status:** planning. Nothing is built yet. See [docs/ROADMAP.md](docs/ROADMAP.md) for progress.

## What it does

- Natural chat logging of meals, reactions and cofactors (exercise, alcohol, painkillers, illness).
- Background ingredient research, with an independent verification agent that assigns confidence levels and citations.
- Lag-aware pattern analysis (case-crossover design) that ranks recurring ingredients with scores, uncertainty ranges and statuses.
- A Pattern Summary web page, shareable with a clinician.
- A synthetic benchmark that compares the analysis against naive counting.

## What it never does

Hassas never diagnoses and never gives dietary advice. Severe symptoms get an immediate warning to seek emergency help. The summary is the user's own data, organized, for discussion with a clinician.

## Planned stack

Python, FastAPI and uv. PostgreSQL. Procrastinate for background jobs. Meta's models via the Meta Model API, with no agent framework. Telegram Bot API first, WhatsApp Cloud API later. See [docs/PRD.md](docs/PRD.md) §6.

## Docs

| File                                 | What it answers                                         |
| ------------------------------------ | ------------------------------------------------------- |
| [docs/IDEA.md](docs/IDEA.md)         | Why: the problem, the approach and the safety principles |
| [docs/PRD.md](docs/PRD.md)           | What: requirements by ID and their acceptance checks    |
| [docs/ROADMAP.md](docs/ROADMAP.md)   | In what order: build phases and tasks                   |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How: stack, modules, dependency rules       |

## Development

Setup and run instructions will be added here once the project skeleton exists (ROADMAP phase 1).

Work happens on short-lived branches, one per ROADMAP task, merged into `main` through pull requests. Branches are named `<type>/<req-id>-<short-description>` and commits follow Conventional Commits. See [AGENTS.md](AGENTS.md) for the full workflow.
