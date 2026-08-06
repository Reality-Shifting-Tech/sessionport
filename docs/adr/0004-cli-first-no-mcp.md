# ADR-0004: CLI and library first, no MCP server in v0.1

- Status: Accepted
- Date: 2026-08-05

## Context

sessionport competes in a fast-moving space where the distribution story matters as
much as the engine. An MCP server is a natural surface for agent-native use,
but shipping one in v0.1 adds a heavy dependency, a second protocol to test,
and coupling to a spec that is still evolving.

## Decision

v0.1 ships a single CLI (`sessionport list/export/import/score`) backed by a plain
Python library with a stable `SessionStore` protocol. The CLI output is
already machine-readable (`--json`), which covers scripted and agent use. An
MCP server is scheduled for v0.2 as a thin wrapper over the same library.

## Consequences

Easier: one install path, one test surface, dependency-light core, faster
v0.1. Harder: agents that speak MCP cannot call sessionport directly until v0.2;
accepted because `--json` + the library cover the same ground today.
