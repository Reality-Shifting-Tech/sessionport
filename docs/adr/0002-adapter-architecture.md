# ADR-0002: Adapter architecture for session stores

- Status: Accepted
- Date: 2026-08-05

## Context

Each agent CLI stores sessions differently: Claude Code uses JSONL under
`~/.claude/projects`, Codex uses JSONL under `~/.codex/sessions`, the Gemini
CLI uses markdown transcripts, OpenCode uses JSON files, and Hermes uses
SQLite. Vendor formats change without notice, and store locations vary by
platform and install method. A hard-coded parser per vendor would break
silently and constantly.

## Decision

Session access goes through a small `SessionStore` protocol
(`list_sessions`, `load_transcript`) with one adapter per agent. Adapters:

- parse defensively: they sniff known JSON shapes (Claude Code and Codex
  message wrappers, generic `role`/`content` lines, tool-result blocks) and
  degrade to a generic line-based read instead of failing;
- resolve store paths from environment overrides first
  (`SESSIONPORT_CLAUDE_HOME`, `SESSIONPORT_CODEX_HOME`, `SESSIONPORT_GEMINI_HOME`,
  `SESSIONPORT_OPENCODE_HOME`, `SESSIONPORT_HERMES_DB`), then platform defaults;
- for SQLite (Hermes), introspect tables and map columns by name rather than
  assuming a fixed schema.

Fixtures for every adapter live in `tests/fixtures/` so format drift is
caught by CI, not by users.

## Consequences

Easier: adding a new agent is one adapter file plus fixtures; broken vendor
formats surface as failing tests. Harder: adapters must be maintained as
vendors evolve, and "defensive" parsing can silently drop messages a stricter
parser would keep; accepted for v0.1.
