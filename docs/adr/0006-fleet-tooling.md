# ADR-0006: Fleet tooling (search, diff, stats, doctor)

- Status: Accepted
- Date: 2026-08-06

## Context

sessionport grows beyond single-session carry: users run a fleet of agents,
and the obvious questions become "where did I talk about X", "what changed
between these two briefs", "how big is my fleet", and "is my install working".
Each of these is a thin, fully offline read over the same adapters, and
answering them by hand means grepping vendor formats directly.

## Decision

Add a `tools` module with four deterministic, offline operations, exposed as
CLI subcommands:

- `sessionport search QUERY` — case-insensitive substring search across every
  transcript, returning agent/session/message/snippet hits (`--agent`,
  `--limit`, `--json`).
- `sessionport diff OLD NEW` — section-by-section comparison of two briefs
  (decisions, files, URLs, code, next actions, constraints, key facts) with
  added/removed lists and a goal-change flag; no LLM.
- `sessionport stats [--agent]` — sessions, messages, and estimated tokens
  per agent plus totals.
- `sessionport doctor` — which stores were found, how many sessions each
  holds, and whether the optional judge is configured.

All four run offline and share the existing adapter error model.

## Consequences

Easier: fleet questions get one-command answers, all testable with the same
fixture stores. Harder: search loads full transcripts per session (fine for
local JSONL at this scale; a tokenized index is follow-up if fleets grow
past thousands of sessions).
