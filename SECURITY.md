# Security Policy

## Reporting a vulnerability

Please do **not** open a public issue for security vulnerabilities.

Email security reports to **elias@realityshifting.tech**. Include:

- A description of the vulnerability and its impact
- Steps to reproduce or a proof of concept
- Affected versions or commits

We aim to acknowledge reports within 72 hours and to keep you informed as we
investigate and fix.

## Scope

sess reads local agent session transcripts (which can contain source code,
paths, tokens, and other sensitive context) and, only when you opt in, sends a
truncated transcript plus a brief to an LLM judge endpoint for fidelity
scoring. Issues involving transcript handling, the optional judge call
(endpoint, key handling, prompt injection through transcript content), and
store-path resolution are treated as high priority.

## Design posture

- The export path is fully offline: no network calls, no telemetry.
- Judge calls (`sess score`) only happen with `RELAY_JUDGE_API_KEY` set, go to
  the endpoint you configure, and truncate transcripts to 120k characters.
- Store locations resolve from explicit environment overrides before any
  platform default, so the tool can be pointed at copies instead of live
  stores.
- Secrets never belong in briefs by design; if you find a brief containing a
  credential, that is a bug. Report it.

## Supported versions

sess is pre-release. Only the latest commit on the default branch receives
security fixes until the first stable version is published.
