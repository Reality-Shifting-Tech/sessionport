"""Fleet tooling: search, diff, stats, and doctor over session stores.

All of these run fully offline over the same ``SessionStore`` adapters the
CLI uses. Search streams transcripts message by message, diff compares briefs
section by section, stats aggregates counts, and doctor reports which agent
stores were found and whether the optional judge is configured.
"""

from __future__ import annotations

import os
from typing import Any

from sessionport.brief import parse as parse_brief
from sessionport.extract import estimate_tokens
from sessionport.stores import SessionStore


def search(
    available: dict[str, SessionStore],
    query: str,
    agent: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Case-insensitive substring search across transcripts."""
    needle = query.lower()
    selected = {agent: available[agent]} if agent else available
    hits: list[dict[str, Any]] = []
    for store in selected.values():
        for session in store.list_sessions():
            messages = store.load_transcript(session.session_id)
            for index, message in enumerate(messages):
                lowered = message.text.lower()
                if needle in lowered:
                    position = lowered.find(needle)
                    start = max(0, position - 60)
                    snippet = message.text[start : start + 160]
                    hits.append(
                        {
                            "agent": store.name,
                            "session_id": session.session_id,
                            "message": index + 1,
                            "role": message.role,
                            "snippet": snippet,
                        }
                    )
                    if len(hits) >= limit:
                        return hits
    return hits


def _section_diff(old: list[str], new: list[str]) -> dict[str, list[str]]:
    old_set = set(old)
    new_set = set(new)
    return {
        "added": [item for item in new if item not in old_set],
        "removed": [item for item in old if item not in new_set],
    }


def diff_briefs(old_text: str, new_text: str) -> dict[str, Any]:
    """Compare two briefs section by section (no LLM)."""
    old = parse_brief(old_text)
    new = parse_brief(new_text)
    sections: dict[str, Any] = {}
    for field in (
        "decisions",
        "files",
        "urls",
        "code",
        "next_actions",
        "constraints",
        "key_facts",
    ):
        sections[field] = _section_diff(getattr(old, field), getattr(new, field))
    return {
        "old": {"agent": old.source_agent, "session": old.session},
        "new": {"agent": new.source_agent, "session": new.session},
        "goal_changed": old.goal != new.goal,
        "sections": sections,
    }


def stats(available: dict[str, SessionStore], agent: str | None = None) -> dict[str, Any]:
    """Per-agent and total session/message/token counts."""
    selected = {agent: available[agent]} if agent else available
    per_agent: dict[str, dict[str, int]] = {}
    totals = {"sessions": 0, "messages": 0, "tokens": 0}
    for store in selected.values():
        sessions = store.list_sessions()
        messages = 0
        tokens = 0
        for session in sessions:
            transcript = store.load_transcript(session.session_id)
            messages += len(transcript)
            tokens += estimate_tokens(transcript)
        per_agent[store.name] = {"sessions": len(sessions), "messages": messages, "tokens": tokens}
        totals["sessions"] += len(sessions)
        totals["messages"] += messages
        totals["tokens"] += tokens
    return {"per_agent": per_agent, "totals": totals}


def doctor(available: dict[str, SessionStore]) -> dict[str, Any]:
    """Report which stores were found and whether the judge is configured."""
    found: list[dict[str, Any]] = []
    for name, store in available.items():
        try:
            sessions = store.list_sessions()
            found.append({"agent": name, "found": bool(sessions), "sessions": len(sessions)})
        except Exception as exc:  # noqa: BLE001 - doctor reports, never crashes
            found.append({"agent": name, "found": False, "error": str(exc)[:120]})
    judge = {
        "configured": bool(os.environ.get("SESSIONPORT_JUDGE_API_KEY")),
        "endpoint": os.environ.get(
            "SESSIONPORT_JUDGE_ENDPOINT", "https://api.openai.com/v1/chat/completions"
        ),
        "model": os.environ.get("SESSIONPORT_JUDGE_MODEL", "gpt-4o-mini"),
    }
    return {"stores": found, "judge": judge}
