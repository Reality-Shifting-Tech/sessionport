"""Deterministic brief extraction from a transcript.

Extraction is heuristic and runs fully offline: no model calls, no network.
It picks out the durable parts of a session (goal, decisions, files, URLs,
code, next actions, constraints) and drops the chatter. The optional LLM
fidelity scorer (``sess.score``) is a separate, opt-in layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sess.models import Message

_FILE_RE = re.compile(
    r"(?<![\w])([\w./~-]+\.(?:py|ts|tsx|js|jsx|go|rs|md|json|yaml|yml|toml|sh|sql|css|html|swift|kt|java|rb|php|vue|svelte|ipynb|lock)(?::\d+)?|"
    r"Dockerfile|Makefile|Procfile|LICENSE)"
)
_URL_RE = re.compile(r"https?://[^\s\)\]\}<>\"']+")
_DECISION_RE = re.compile(
    r"^\s*(?:decision:?|decided(?::| to)?|we'?ll go with|we will (?:use|go with)|"
    r"going with|"
    r"we chose|let'?s (?:use|go with|stick with)|stick with|won'?t use|rejected|abandoned|"
    r"dropped|settled on|using )",
    re.IGNORECASE,
)
_NEXT_RE = re.compile(
    r"(?:^|\.\s+)(?:[-*]\s*\[[ x]\]\s+|next(?: steps?)?:?|todo:?|todos?:?)\s+",
    re.IGNORECASE,
)
_CONSTRAINT_RE = re.compile(
    r"\b(must not|can'?t|cannot|don'?t|dont|never|requires?|important:?|"
    r"note:?|warning|critical|blocked|avoid)\b",
    re.IGNORECASE,
)
_KEYFACT_RE = re.compile(r"^\s*(?:key fact:?|remember:?|fact:?|ground truth:?)", re.IGNORECASE)


@dataclass
class Extracted:
    """The durable content pulled out of a transcript."""

    goal: str = ""
    decisions: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    key_facts: list[str] = field(default_factory=list)


def _dedupe(items: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
        if len(out) >= limit:
            break
    return out


def _collapse(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def extract(messages: list[Message]) -> Extracted:
    """Extract the durable parts of a session transcript (offline)."""
    result = Extracted()

    user_texts = [message.text for message in messages if message.role == "user"]
    assistant_texts = [message.text for message in messages if message.role == "assistant"]
    tool_texts = [message.text for message in messages if message.role == "tool"]

    if user_texts:
        result.goal = _collapse(user_texts[0], 280)

    decisions: list[str] = []
    files: list[str] = []
    urls: list[str] = []
    next_actions: list[str] = []
    constraints: list[str] = []
    key_facts: list[str] = []
    code_langs: dict[str, int] = {}

    for text in user_texts + assistant_texts + tool_texts:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if _DECISION_RE.match(stripped):
                decisions.append(_collapse(stripped, 200))
            if _NEXT_RE.search(stripped):
                next_actions.append(_collapse(stripped, 200))
            if _KEYFACT_RE.match(stripped):
                key_facts.append(_collapse(stripped, 200))
            if (
                _CONSTRAINT_RE.search(stripped)
                and not _NEXT_RE.search(stripped)
                and not _KEYFACT_RE.match(stripped)
            ):
                constraints.append(_collapse(stripped, 200))
            for match in _FILE_RE.finditer(stripped):
                files.append(match.group(1))
            for match in _URL_RE.finditer(stripped):
                urls.append(match.group(0).rstrip(".,;:"))
        for match in re.finditer(r"```([\w+-]*)", text):
            lang = match.group(1)
            if not lang:
                continue  # closing fence
            code_langs[lang] = code_langs.get(lang, 0) + 1

    result.decisions = _dedupe(decisions, 12)
    result.files = _dedupe(files, 25)
    result.urls = _dedupe(urls, 15)
    result.next_actions = _dedupe(next_actions, 12)
    result.constraints = _dedupe(constraints, 12)
    result.key_facts = _dedupe(key_facts, 12)
    result.code = [f"```{lang} x {count}" for lang, count in sorted(code_langs.items())]
    return result


def estimate_tokens(messages: list[Message]) -> int:
    """Rough token estimate: ~4 characters per token."""
    return sum(len(message.text) for message in messages) // 4
