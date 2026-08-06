"""MCP server for sessionport (v0.2).

Exposes the CLI's core loop over MCP stdio: list sessions, export a brief,
and render an import prompt. The tool handlers are plain functions over the
library so they are testable offline; the MCP transport is an optional
dependency (``sessionport[mcp]``) and is only imported at run time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sessionport.brief import render
from sessionport.extract import estimate_tokens, extract
from sessionport.models import Brief
from sessionport.stores import StoreError, resolve_session, stores


def _brief_for(session_ref: str) -> Brief:
    store, session = resolve_session(session_ref, stores())
    messages = store.load_transcript(session.session_id)
    if not messages:
        raise StoreError(f"{store.name}: session {session.session_id!r} has no readable messages")
    extracted = extract(messages)
    return Brief(
        source_agent=store.name,
        session=session.session_id,
        exported="",
        messages=len(messages),
        estimated_tokens=estimate_tokens(messages),
        goal=extracted.goal,
        decisions=extracted.decisions,
        files=extracted.files,
        urls=extracted.urls,
        code=extracted.code,
        next_actions=extracted.next_actions,
        constraints=extracted.constraints,
        key_facts=extracted.key_facts,
    )


def tool_list_sessions(agent: str | None = None) -> list[dict[str, Any]]:
    """Discover sessions across installed agent stores."""
    all_stores = stores()
    if agent is not None:
        store = all_stores.get(agent)
        if store is None:
            raise StoreError(f"unknown agent {agent!r}; known: {', '.join(sorted(all_stores))}")
        selected = {agent: store}
    else:
        selected = all_stores
    out: list[dict[str, Any]] = []
    for store in selected.values():
        for session in store.list_sessions():
            out.append(
                {
                    "agent": store.name,
                    "session_id": session.session_id,
                    "title": session.title,
                    "message_count": session.message_count,
                }
            )
    return out


def tool_export_brief(session: str) -> str:
    """Export a session to a portable brief and return the markdown."""
    return render(_brief_for(session))


def tool_import_prompt(brief_file: str, into: str | None = None) -> str:
    """Render a brief file as a resume prompt for a target agent."""
    path = Path(brief_file)
    if not path.is_file():
        raise StoreError(f"brief file not found: {path}")
    from sessionport.brief import parse as parse_brief

    brief = parse_brief(path.read_text(encoding="utf-8"))
    target = into or brief.source_agent
    return (
        "Resume from a sessionport brief.\n\n"
        "The sections below are ground truth from an earlier session with "
        f"{target} (session {brief.session}). Continue the work: do not "
        "re-litigate settled decisions, do not re-read files you already "
        "inspected, and do not re-run commands whose outcomes are recorded "
        "here. If you need a fact that is missing, say so and ask.\n\n"
        "---\n\n"
        f"{path.read_text(encoding='utf-8')}"
    )


def build_server() -> Any:
    """Build the FastMCP server (requires the optional ``mcp`` dependency)."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("sessionport")
    server.tool()(tool_list_sessions)
    server.tool()(tool_export_brief)
    server.tool()(tool_import_prompt)
    return server


def run_server() -> None:
    """Run the stdio MCP server."""
    build_server().run()
