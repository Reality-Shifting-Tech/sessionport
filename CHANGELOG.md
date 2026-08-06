# Changelog

All notable changes to sessionport are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-08-06

### Added

- Five new adapters: Cursor, Aider, Windsurf, OpenClaw, Cline (ten agents
  total), each with a `SESSIONPORT_*` env override, sanitized fixture, and
  tests.
- MCP server (`sessionport mcp`): `list_sessions`, `export_brief`, and
  `import_prompt` tools over MCP stdio. Optional dependency
  (`sessionport[mcp]`). ADR-0005.
- `sessionport export --all [--agent NAME] [--out-dir DIR]`: export every
  discovered session in one command.
- `sessionport score --endpoint URL --model NAME`: per-call judge overrides
  (Ollama and any OpenAI-compatible endpoint work).
- Windows support: `clip.exe` clipboard fallback and platform-aware store
  path candidates.
- Docs: 10-agent architecture diagram with official logos.

## [0.1.0] - 2026-08-05

Initial release.

### Added

- `sessionport list`: discover sessions across installed agent stores
  (Claude Code, Codex, Gemini CLI, OpenCode, Hermes) with `--json` output.
- `sessionport export`: turn any discovered session into a portable
  `sessionport-brief/v1` markdown brief. Extraction is deterministic and
  fully offline: goal, decisions, files, URLs, code blocks, next actions,
  constraints, and key facts, plus a token estimate.
- `sessionport import`: render a brief into a resume prompt for any target
  agent, with `--into`, `--copy` (macOS clipboard), and `--out`.
- `sessionport score`: optional LLM fidelity check comparing a brief against
  its source transcript (OpenAI-compatible endpoint, env-gated).
- Defensive, fixture-tested adapters with `SESSIONPORT_*` environment
  overrides for every store location.
- Docs suite: ADRs 0001-0004, architecture and workflow diagrams, real
  terminal demo.
