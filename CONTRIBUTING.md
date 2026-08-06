# Contributing

Thanks for your interest in sessionport. This document is the contract between you
and the maintainers; please read it before opening a pull request.

## Development setup

Prerequisites: Python >= 3.11 and [uv](https://docs.astral.sh/uv).

```bash
uv sync --extra dev
```

Run the full gate before pushing:

```bash
make all   # lint + typecheck + test
```

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <imperative summary>
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `build`,
`perf`. Scope is a component name when useful, e.g.
`feat(adapters): add cursor adapter`. The changelog is maintained from these
messages, so write them for a reader, not for the diff.

## Pull requests

- One logical change per PR. Split refactors from features.
- Describe the _why_, not just the _what_; link issues and ADRs
  (`docs/adr/`).
- Keep the diff reviewable. If a PR needs more than ~400 changed lines of
  substance, it probably needs to be split.
- All CI checks must be green: lint, typecheck, tests.

## Quality gates

- **Zero-warning policy.** `make lint` runs ruff with the configured rule set
  (`E,F,I,UP,B,SIM`). A warning is a failed build, not a suggestion.
- **Types are non-negotiable.** `make typecheck` runs mypy over `src/` with
  `disallow_untyped_defs` and `warn_unused_ignores`. If you reach for an
  ignore or a cast, expect to justify it in review.
- **Tests.** New behavior ships with tests. Unit tests must not require live
  model endpoints or network access; inject fakes (the fidelity judge is
  injected, never called).

## Offline-by-default rule

The export path must stay free, fast, and private. Do not add network calls,
telemetry, or LLM dependencies to `sessionport export` or `sessionport import`. LLM
features belong behind `sessionport score`-style opt-in paths with env-gated keys.
PRs that break offline-by-default will be rejected.

## Adding an adapter

Each agent CLI stores sessions differently, so a new adapter is:

1. A `SessionStore` implementation in `src/sessionport/stores.py` (or its own module
   if it grows), resolving its path from a `SESSIONPORT_*` env override first.
2. A fixture transcript in `tests/fixtures/<agent>/` using the real vendor
   format (a sanitized sample, never a real session).
3. Tests in `tests/test_stores.py` covering list + load, plus an extraction
   test if the format surfaces new content shapes.
4. An entry in `stores()` and a line in the README supported-agents table.

## Code style

The bar is _edited, not generated_. Code should read as if a senior engineer
wrote it deliberately:

- No comments that narrate what the code plainly does. Comment the _why_, or
  nothing.
- No dead code, unused exports, or speculative abstractions. Build what the
  milestone requires.
- Consistent naming within a module; prefer the existing vocabulary over
  introducing synonyms.
- Reuse the existing error-handling convention (`StoreError` / `ScoreError`)
  rather than inventing a new one.

## Known environment pitfall

If `PYTHONPATH` points at another project's venv, imports and image scripts
can resolve the wrong packages. Run project commands with
`env -u PYTHONPATH` when in doubt.
