"""Brief format tests: render, parse, round trip."""

from __future__ import annotations

from sessionport.brief import FORMAT, parse, render
from sessionport.models import Brief


def _sample() -> Brief:
    return Brief(
        source_agent="codex",
        session="session-xyz",
        exported="2026-08-01T12:00:00Z",
        messages=3,
        estimated_tokens=120,
        goal="Add a health endpoint to the API",
        decisions=["Decision: use a lightweight route in app.py"],
        files=["app.py", "Dockerfile"],
        urls=["https://example.com/api"],
        code=["```python x 1"],
        next_actions=["Next: wire it into the Dockerfile healthcheck"],
        constraints=["must not expose internals"],
        key_facts=["Remember: keep it stateless"],
    )


def test_render_contains_sections() -> None:
    text = render(_sample())
    assert text.startswith("---\nformat: sessionport-brief/v1")
    assert "## Goal" in text
    assert "## Decisions" in text
    assert "## State: files" in text
    assert "## Open threads / next actions" in text
    assert "must not expose internals" in text


def test_parse_round_trip() -> None:
    original = _sample()
    parsed = parse(render(original))
    assert parsed.source_agent == original.source_agent
    assert parsed.session == original.session
    assert parsed.exported == original.exported
    assert parsed.messages == original.messages
    assert parsed.estimated_tokens == original.estimated_tokens
    assert parsed.goal == original.goal
    assert parsed.decisions == original.decisions
    assert parsed.files == original.files
    assert parsed.urls == original.urls
    assert parsed.code == original.code
    assert parsed.next_actions == original.next_actions
    assert parsed.constraints == original.constraints
    assert parsed.key_facts == original.key_facts


def test_parse_empty_sections() -> None:
    brief = Brief(
        source_agent="hermes",
        session="h1",
        exported="2026-08-01T00:00:00Z",
        messages=1,
        estimated_tokens=10,
    )
    text = render(brief)
    assert "## Decisions" not in text
    parsed = parse(text)
    assert parsed.decisions == []
    assert parsed.goal == ""


def test_format_constant() -> None:
    assert FORMAT == "sessionport-brief/v1"
