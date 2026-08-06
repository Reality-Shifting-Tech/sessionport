"""Adapter tests: each agent store parses its fixture transcript."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sessionport.stores import (
    ClaudeCodeStore,
    CodexStore,
    GeminiStore,
    HermesStore,
    OpenCodeStore,
    StoreError,
    resolve_session,
    stores,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _env_homes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSIONPORT_CLAUDE_HOME", str(FIXTURES / "claude-code"))
    monkeypatch.setenv("SESSIONPORT_CODEX_HOME", str(FIXTURES / "codex"))
    monkeypatch.setenv("SESSIONPORT_GEMINI_HOME", str(FIXTURES / "gemini"))
    monkeypatch.setenv("SESSIONPORT_OPENCODE_HOME", str(FIXTURES / "opencode"))


def test_claude_code_list_and_load(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = ClaudeCodeStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    session = sessions[0]
    assert session.session_id == "9f9f9f9f-1111-2222-3333-444444444444"
    assert session.message_count == 4
    assert session.title.startswith("Fix the auth bug")

    messages = store.load_transcript(session.session_id)
    assert [m.role for m in messages] == ["user", "assistant", "tool", "assistant"]
    assert "test_refresh PASSED" in messages[2].text
    assert messages[0].timestamp == "2026-08-01T10:00:00Z"


def test_codex_list_and_load(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = CodexStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "session-xyz"
    messages = store.load_transcript("session-xyz")
    assert [m.role for m in messages] == ["user", "assistant", "user"]
    assert "health endpoint" in messages[0].text


def test_gemini_markdown_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = GeminiStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "session-abc"
    messages = store.load_transcript("session-abc")
    assert [m.role for m in messages] == ["user", "assistant", "user"]
    assert messages[1].text.startswith("Decision: use markdown-it")


def test_opencode_json_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = OpenCodeStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "abc"
    messages = store.load_transcript("abc")
    assert [m.role for m in messages] == ["assistant", "user"]
    assert messages[1].text == "Refactor the queue to use an outbox"


def test_hermes_sqlite(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    db_path = tmp_path / "sessions.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT, created_at TEXT)")
    conn.execute(
        "CREATE TABLE messages ("
        "id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, created_at TEXT)"
    )
    conn.execute("INSERT INTO sessions (id, title) VALUES ('h1', 'fix onboarding flow')")
    conn.execute(
        "INSERT INTO messages (session_id, role, content) "
        "VALUES ('h1', 'user', 'fix onboarding flow')"
    )
    conn.execute(
        "INSERT INTO messages (session_id, role, content) "
        "VALUES ('h1', 'assistant', 'Decision: use resend for emails.')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setenv("SESSIONPORT_HERMES_DB", str(db_path))

    store = HermesStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "h1"
    messages = store.load_transcript("h1")
    assert [m.role for m in messages] == ["user", "assistant"]


def test_resolve_session_exact_and_fuzzy(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    available = stores()
    store, session = resolve_session("claude-code:9f9f9f9f", available)
    assert store.name == "claude-code"
    assert session.session_id == "9f9f9f9f-1111-2222-3333-444444444444"

    store, session = resolve_session("session-xyz", available)
    assert store.name == "codex"


def test_resolve_session_unknown_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    with pytest.raises(StoreError, match="unknown agent"):
        resolve_session("bogus:anything", stores())


def test_resolve_session_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    with pytest.raises(StoreError, match="no session"):
        resolve_session("claude-code:does-not-exist", stores())
