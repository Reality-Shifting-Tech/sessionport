# AGENTS.md

Guidance for AI agents working in this repository. Human-facing contribution
rules live in [CONTRIBUTING.md](CONTRIBUTING.md); this file is the operational
quick-reference. Where the two overlap, CONTRIBUTING wins.

## What this is

sess is an MIT-licensed CLI that carries AI agent sessions between agent
CLIs. It discovers sessions in each agent's local store (Claude Code, Codex,
Gemini CLI, OpenCode, Hermes), exports them to a portable `sess-brief/v1`
markdown brief, and imports a brief as a resume prompt into any target agent.
Export is deterministic and fully offline; `sess score` is an opt-in LLM
fidelity check.

## Toolchain

- Python >= 3.11 (3.12 also supported and tested in CI).
- `uv` for environment and dependency management.
- Unit tests must not call external model endpoints, hit the network, or
  touch real session stores — inject fakes (the fidelity judge is injected).

## Commands

Run from the repo root unless noted.

```bash
uv sync --extra dev

make lint        # ruff check . (zero-warning policy)
make typecheck   # mypy src
make test        # pytest (testpaths: tests)
make format      # ruff format + ruff check --fix
make images      # regenerate docs/images via docs/make_images.py
```

Full pre-push gate: `make all` (lint + typecheck + test).

## Layout

```
src/sess/            Core package
  __main__.py        CLI entry (sess)
  cli.py             argparse commands: list / export / import / score
  models.py          Message, SessionRef, Brief dataclasses
  stores.py          SessionStore adapters (one per agent) + resolve_session
  extract.py         Offline deterministic extraction heuristics
  brief.py           sess-brief/v1 render + parse (round-trip tested)
  score.py           Opt-in LLM fidelity judge (env-gated, injected in tests)
docs/
  adr/               Architecture decision records (0000 template + 0001-0004)
  images/            README assets: architecture.png, workflow.png,
                     terminal-demo.gif, agents/*.png (official logos)
  make_images.py     Deterministic PIL image generator (make images)
tests/
  fixtures/          Sanitized vendor-format transcripts, one dir per agent
  test_*.py          Adapter, extraction, brief, score, and CLI tests
```

## Conventions (enforced in review/CI)

- Conventional Commits: `<type>(<scope>): <imperative summary>`; types
  `feat|fix|chore|docs|refactor|test|ci|build|perf`.
- Ruff clean with zero warnings (select `E,F,I,UP,B,SIM`, line length 100).
- mypy clean over `src/` (`disallow_untyped_defs`, `warn_unused_ignores`).
- New behavior ships with tests. Tests must run fully offline.
- Style bar is "edited, not generated": no narrating comments, no dead code,
  no speculative abstractions, reuse existing vocabulary.
- Offline-by-default is a hard requirement: `export` and `import` never call
  the network. LLM features are opt-in behind env-gated keys (`RELAY_JUDGE_*`).
- Adapters resolve paths from `RELAY_*` env overrides before platform
  defaults, and every adapter has a fixture + tests.

## Working agreement for agents

- Never commit or push unless explicitly asked.
- API keys are read from the environment only. Never write a secret into a
  file that could be committed, and never log transcript bodies or keys.
- `sess score` spends tokens/credits when pointed at a live endpoint; do not
  run it casually.
- When adding a new agent adapter: implement the store, add a sanitized
  fixture, add tests, register it in `stores()`, update the README, and add
  an ADR note if it introduces a new format shape.

## Known environment pitfall

If `PYTHONPATH` points at another project's venv (e.g. a shared Hermes
install), `python` can import the wrong site-packages. Use
`env -u PYTHONPATH .venv/bin/python ...` for scripts that touch PIL or the
package itself.
