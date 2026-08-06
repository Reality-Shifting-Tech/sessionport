"""The sess-brief/v1 format: render and parse.

A brief is a markdown document with YAML-flavored frontmatter (flat keys only,
kept dependency-free) followed by labeled sections. It is human-readable,
diffable, and machine-parseable by design: the whole point is that a human can
read exactly what an agent will resume with.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sess.models import Brief

FORMAT = "sess-brief/v1"
_SECTION_ORDER = (
    ("goal", "Goal"),
    ("decisions", "Decisions"),
    ("files", "State: files"),
    ("urls", "State: references"),
    ("code", "Code"),
    ("next_actions", "Open threads / next actions"),
    ("constraints", "Constraints"),
    ("key_facts", "Key facts"),
)
_LIST_FIELDS = ("decisions", "files", "urls", "code", "next_actions", "constraints", "key_facts")


def _frontmatter(brief: Brief) -> str:
    lines = [
        f"format: {FORMAT}",
        f"source-agent: {brief.source_agent}",
        f"session: {brief.session}",
        f"exported: {brief.exported}",
        f"messages: {brief.messages}",
        f"estimated_tokens: {brief.estimated_tokens}",
    ]
    return "---\n" + "\n".join(lines) + "\n---"


def render(brief: Brief) -> str:
    """Render a Brief to the canonical sess-brief/v1 markdown."""
    parts = [_frontmatter(brief), "", f"# Session brief ({brief.source_agent})", ""]
    for field_name, heading in _SECTION_ORDER:
        if field_name == "goal":
            parts.append(f"## {heading}")
            parts.append("")
            parts.append("<!-- no explicit goal captured -->" if not brief.goal else brief.goal)
            parts.append("")
            continue
        items = getattr(brief, field_name)
        if items:
            parts.append(f"## {heading}")
            parts.append("")
            parts.extend(f"- {item}" for item in items)
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _parse_frontmatter(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
    return meta


def parse(text: str) -> Brief:
    """Parse a sess-brief/v1 document back into a Brief."""
    meta = _parse_frontmatter(text)
    source_agent = meta.get("source-agent", "unknown")
    session = meta.get("session", "unknown")
    exported = meta.get("exported", "")
    try:
        messages = int(meta.get("messages", "0"))
    except ValueError:
        messages = 0
    try:
        estimated_tokens = int(meta.get("estimated_tokens", "0"))
    except ValueError:
        estimated_tokens = 0

    sections: dict[str, list[str]] = {name: [] for name, _ in _SECTION_ORDER}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            current = next((name for name, head in _SECTION_ORDER if head == heading), None)
            continue
        if current is None:
            continue
        if line.startswith("- "):
            sections[current].append(line[2:].strip())
        elif (
            current == "goal"
            and line.strip()
            and not sections["goal"]
            and not line.startswith("<!--")
        ):
            sections["goal"].append(line.strip())

    goal = sections["goal"][0] if sections["goal"] else ""
    kwargs: dict[str, list[str]] = {name: sections[name] for name in _LIST_FIELDS}
    return Brief(
        source_agent=source_agent,
        session=session,
        exported=exported,
        messages=messages,
        estimated_tokens=estimated_tokens,
        goal=goal,
        **kwargs,
    )


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
