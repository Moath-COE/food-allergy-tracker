# 1. Record architecture decisions

Date: 2026-11-11
Status: Accepted

## Context

Hassas is built by coding agents, one short task at a time, and the owner reviews every PR. An agent starts each session with no memory of earlier ones. A decision made in one PR (a library, a module boundary, a data rule) is easy to undo or contradict in the next unless the reason is written down where the next agent will find it.

ARCHITECTURE.md describes what is true now. It does not say why, and rewriting it to keep history would turn it into a changelog. We need a place for the reasoning that survives the decision itself.

Alternatives considered:

- **No records.** The reasoning lives in PR descriptions and chat. Cheapest now, but PR threads are not read when an agent plans a task, and the reasons are lost once the PR is squashed and the branch deleted.
- **Decisions only inside ARCHITECTURE.md.** One file to read, but it mixes "what is true" with "why it became true". Rejected alternatives and downsides pile up in a document that agents are meant to read quickly.
- **MADR (Markdown Any Decision Records).** Well supported by tooling, but its template has more sections (decision drivers, considered options with pros and cons, confirmation) than a one-person project with a short-lived codebase will keep filled in.
- **Michael Nygard's ADR format.** Title, Date, Status, Context, Decision, Consequences. About a page each, easy for an agent to write and review.

## Decision

We will record architecture decisions as ADRs in `docs/adr/`, using Michael Nygard's format.

- Files are named `NNNN-kebab-case-title.md`, numbered in order and never reused.
- An Accepted ADR changes only in its status line. A changed decision gets a new ADR that supersedes it.
- The agent writes the ADR in the same PR as the change it justifies, and updates the index in ARCHITECTURE.md §12.
- AGENTS.md lists when an ADR is required: a new library or service, a module boundary, a data or schema rule, a security choice, or a PRD §8 question being decided.

## Consequences

- Reasons and rejected alternatives stay next to the code, in the repo, where agents read them.
- ARCHITECTURE.md stays a description of the present; ADRs hold the history.
- Every qualifying PR carries extra writing, and the owner has one more file to review.
- The index in ARCHITECTURE.md §12 can drift from the directory. Reviewers have to check it.
- A short template invites thin Context sections. The "alternatives considered" rule in AGENTS.md is the guard, and it depends on review.
