"""Extraction tests: deterministic heuristics over fixture transcripts."""

from __future__ import annotations

from pathlib import Path

import pytest

from sess.extract import estimate_tokens, extract
from sess.stores import ClaudeCodeStore, CodexStore, GeminiStore

FIXTURES = Path(__file__).parent / "fixtures"


def _store_messages(monkeypatch: pytest.MonkeyPatch, agent: str, session_id: str):
    if agent == "claude-code":
        monkeypatch.setenv("RELAY_CLAUDE_HOME", str(FIXTURES / "claude-code"))
        store = ClaudeCodeStore()
    elif agent == "codex":
        monkeypatch.setenv("RELAY_CODEX_HOME", str(FIXTURES / "codex"))
        store = CodexStore()
    else:
        monkeypatch.setenv("RELAY_GEMINI_HOME", str(FIXTURES / "gemini"))
        store = GeminiStore()
    return store.load_transcript(session_id)


def test_extract_claude_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = _store_messages(monkeypatch, "claude-code", "9f9f9f9f-1111-2222-3333-444444444444")
    result = extract(messages)

    assert result.goal.startswith("Fix the auth bug in login.py")
    assert any("httpOnly secure cookies" in decision for decision in result.decisions)
    assert "login.py" in result.files
    assert "tests/test_auth.py" in result.files
    assert "tests/test_session.py" in result.files
    assert any("example.com" in url for url in result.urls)
    assert result.code == ["```python x 1"]
    assert any("integration tests" in action for action in result.next_actions)
    assert any("never store tokens" in constraint for constraint in result.constraints)


def test_extract_codex_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = _store_messages(monkeypatch, "codex", "session-xyz")
    result = extract(messages)
    assert result.goal == "Add a health endpoint to the API"
    assert any("lightweight route in app.py" in decision for decision in result.decisions)
    assert "app.py" in result.files
    assert "Dockerfile" in result.files
    assert any("must not expose internals" in constraint for constraint in result.constraints)
    assert any("healthcheck" in action for action in result.next_actions)


def test_extract_gemini_key_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = _store_messages(monkeypatch, "gemini", "session-abc")
    result = extract(messages)
    assert any("never write to stdout" in fact for fact in result.key_facts)
    assert any("markdown-it" in decision for decision in result.decisions)


def test_estimate_tokens_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = _store_messages(monkeypatch, "claude-code", "9f9f9f9f-1111-2222-3333-444444444444")
    assert estimate_tokens(messages) > 0
