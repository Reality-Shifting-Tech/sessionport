# Changelog

All notable changes to sessionport are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-08-05

Initial release.

### Added

- `sessionport list`: discover sessions across installed agent stores
  (Claude Code, Codex, Gemini CLI, OpenCode, Hermes) with `--json` output.
- `sessionport export`: turn any discovered session into a portable
  `sessionport-brief/v1` markdown brief. Extraction is deterministic and fully
  offline: goal, decisions, files, URLs, code blocks, next actions,
  constraints, and key facts, plus a token estimate.
- `sessionport import`: render a brief into a resume prompt for any target agent,
  with `--into`, `--copy` (macOS clipboard), and `--out`.
- `sessionport score`: optional LLM fidelity check comparing a brief against its
  source transcript (OpenAI-compatible endpoint, env-gated).
- Defensive, fixture-tested adapters with `SESSIONPORT_*` environment overrides
  for every store location.
- Docs suite: ADRs 0001-0004, architecture and workflow diagrams, real
  terminal demo.
