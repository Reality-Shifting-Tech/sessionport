# ADR-0001: Portable brief format (sess-brief/v1)

- Status: Accepted
- Date: 2026-08-05

## Context

sess exists to move agent context between different agent CLIs whose native
session stores are incompatible JSONL/JSON/SQLite formats. To make sessions
portable we need one canonical artifact, and that artifact must be durable:
readable by humans, diffable in git, parseable by machines, and stable across
tool versions. A binary or vendor-specific format fails on every count.

## Decision

The portable artifact is a markdown document with flat YAML-flavored
frontmatter (format id `sess-brief/v1`, source agent, session id, export
timestamp, message count, token estimate) followed by labeled sections:
Goal, Decisions, State (files and references), Code, Open threads / next
actions, Constraints, and Key facts.

- Frontmatter is parsed with a dependency-free flat parser; no YAML library.
- Extraction is deterministic and offline (see ADR-0003 for the optional LLM
  layer).
- The format is versioned in the frontmatter (`format: sess-brief/v1`) so
  future revisions can be migrated explicitly.

## Consequences

Easier: humans can read exactly what an agent will resume with; briefs are
git-diffable; any agent CLI can consume the same artifact. Harder: flat
frontmatter cannot express nested metadata, which we accept at v1. Follow-up:
a schema version migration path when v2 arrives.
