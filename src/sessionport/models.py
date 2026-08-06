"""Core data models for sessionport."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Message:
    """One message in an agent session transcript."""

    role: str
    text: str
    timestamp: str | None = None


@dataclass
class SessionRef:
    """A session as discovered in an agent's local session store."""

    agent: str
    session_id: str
    title: str
    path: str
    message_count: int
    updated_at: str | None = None


@dataclass
class Brief:
    """The canonical portable session brief (sessionport-brief/v1)."""

    source_agent: str
    session: str
    exported: str
    messages: int
    estimated_tokens: int
    goal: str = ""
    decisions: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    key_facts: list[str] = field(default_factory=list)
