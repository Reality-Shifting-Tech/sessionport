# Changelog

All notable changes to sess are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-08-05

Initial release.

### Added

- `sess list`: discover sessions across installed agent stores
  (Claude Code, Codex, Gemini CLI, OpenCode, Hermes) with `--json` output.
- `sess export`: turn any discovered session into a portable
  `sess-brief/v1` markdown brief. Extraction is deterministic and fully
  offline: goal, decisions, files, URLs, code blocks, next actions,
  constraints, and key facts, plus a token estimate.
- `sess import`: render a brief into a resume prompt for any target agent,
  with `--into`, `--copy` (macOS clipboard), and `--out`.
- `sess score`: optional LLM fidelity check comparing a brief against its
  source transcript (OpenAI-compatible endpoint, env-gated).
- Defensive, fixture-tested adapters with `RELAY_*` environment overrides
  for every store location.
- Docs suite: ADRs 0001-0004, architecture and workflow diagrams, real
  terminal demo.
