# ADR-0003: Fidelity scoring is an optional LLM layer

- Status: Accepted
- Date: 2026-08-05

## Context

A brief is only useful if it preserves what the session actually knew. Pure
heuristic extraction (ADR-0001) is deterministic but cannot judge semantic
loss. An LLM judge can, but calling a model on the export path makes the core
tool dependent on network, keys, and cost, and makes the test suite flaky.

## Decision

Fidelity scoring (`sessionport score`) is opt-in and never on the export path:

- it requires `SESSIONPORT_JUDGE_API_KEY` (plus optional
  `SESSIONPORT_JUDGE_ENDPOINT` / `SESSIONPORT_JUDGE_MODEL`) and calls any
  OpenAI-compatible chat endpoint;
- the judge receives the rendered transcript (truncated at 120k characters)
  and the brief, and returns a JSON object: fidelity score, a list of missed
  facts, and a note;
- tests inject a fake judge; the suite runs fully offline.

## Consequences

Easier: the default path stays free, fast, and private; tests never touch the
network. Harder: heuristic extraction can miss semantic nuance the judge would
catch, so `sessionport score` is the honest answer to "did the brief lose anything".
Follow-up: a local judge via Ollama for fully offline scoring.
