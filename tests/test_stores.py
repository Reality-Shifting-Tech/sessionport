"""Adapter tests: each agent store parses its fixture transcript."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sessionport.stores import (
    AiderStore,
    ClaudeCodeStore,
    ClineStore,
    CodexStore,
    CursorStore,
    GeminiStore,
    HermesStore,
    OpenClawStore,
    OpenCodeStore,
    StoreError,
    WindsurfStore,
    resolve_session,
    stores,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _env_homes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSIONPORT_CLAUDE_HOME", str(FIXTURES / "claude-code"))
    monkeypatch.setenv("SESSIONPORT_CODEX_HOME", str(FIXTURES / "codex"))
    monkeypatch.setenv("SESSIONPORT_GEMINI_HOME", str(FIXTURES / "gemini"))
    monkeypatch.setenv("SESSIONPORT_OPENCODE_HOME", str(FIXTURES / "opencode"))
    monkeypatch.setenv("SESSIONPORT_CURSOR_HOME", str(FIXTURES / "cursor"))
    monkeypatch.setenv("SESSIONPORT_AIDER_HOME", str(FIXTURES / "aider" / "history"))
    monkeypatch.setenv("SESSIONPORT_WINDSURF_HOME", str(FIXTURES / "windsurf" / "sessions"))
    monkeypatch.setenv("SESSIONPORT_OPENCLAW_HOME", str(FIXTURES / "openclaw" / "sessions"))
    monkeypatch.setenv("SESSIONPORT_CLINE_HOME", str(FIXTURES / "cline" / "tasks"))


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


def test_cursor_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = CursorStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "session-1"
    messages = store.load_transcript("session-1")
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].text == "Refactor the checkout flow"
    assert sessions[0].title.startswith("Refactor the checkout flow")


def test_aider_markdown_history(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = AiderStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "abc123"
    messages = store.load_transcript("abc123")
    assert [m.role for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[0].text == "Refactor the queue to use an outbox"
    assert "retries with backoff" in messages[3].text


def test_windsurf_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = WindsurfStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "s1"
    messages = store.load_transcript("s1")
    assert [m.role for m in messages] == ["user", "assistant"]


def test_openclaw_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = OpenClawStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "o1"
    messages = store.load_transcript("o1")
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[1].text.startswith("Decision: phased rollout")


def test_cline_jsonl(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    store = ClineStore()
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].session_id == "t1"
    messages = store.load_transcript("t1")
    assert [m.role for m in messages] == ["user", "assistant"]
    assert "typer" in messages[1].text


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
