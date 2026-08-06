# ADR-0005: MCP server in v0.2

- Status: Accepted
- Date: 2026-08-06
- Supersedes: ADR-0004 (the deferral no longer applies)

## Context

ADR-0004 deferred an MCP server to keep v0.1 dependency-light. The library
(`SessionStore` adapters, extract, render) has since stabilized across ten
adapters, and MCP is now the default way agents talk to tools: Claude
Desktop, Cursor, OpenCode, and custom harnesses all speak MCP. The transport
is the missing surface, not the logic.

## Decision

Add `sessionport mcp`, a stdio MCP server exposing three tools over the
existing library:

- `list_sessions(agent)` — discover sessions
- `export_brief(session)` — render a portable brief
- `import_prompt(brief_file, into)` — build a resume prompt

The `mcp` package is an optional extra (`sessionport[mcp]`), imported only at
run time, so the core install stays light and the tool handlers remain plain
library functions tested offline without the transport.

## Consequences

Easier: any MCP client can now carry sessions without shelling out to a CLI.
Harder: two surfaces (CLI and MCP) to keep in sync; accepted because both are
thin wrappers over the same functions, and the tests pin the shared behavior.
