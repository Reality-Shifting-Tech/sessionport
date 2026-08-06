"""MCP server tests: tool handlers run offline against fixture stores."""

from __future__ import annotations

from pathlib import Path

import pytest

from sessionport import mcp_server
from sessionport.stores import StoreError

FIXTURES = Path(__file__).parent / "fixtures"


def _env_homes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSIONPORT_CLAUDE_HOME", str(FIXTURES / "claude-code"))
    monkeypatch.setenv("SESSIONPORT_CODEX_HOME", str(FIXTURES / "codex"))


def test_tool_list_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    sessions = mcp_server.tool_list_sessions(agent="claude-code")
    assert len(sessions) == 1
    assert sessions[0]["agent"] == "claude-code"
    assert sessions[0]["message_count"] == 4


def test_tool_list_sessions_unknown_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    with pytest.raises(StoreError, match="unknown agent"):
        mcp_server.tool_list_sessions(agent="bogus")


def test_tool_export_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    brief = mcp_server.tool_export_brief("claude-code:9f9f9f9f")
    assert brief.startswith("---\nformat: sessionport-brief/v1")
    assert "## Decisions" in brief
    assert "login.py" in brief


def test_tool_import_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _env_homes(monkeypatch)
    brief = mcp_server.tool_export_brief("claude-code:9f9f9f9f")
    brief_file = tmp_path / "brief.md"
    brief_file.write_text(brief, encoding="utf-8")
    prompt = mcp_server.tool_import_prompt(str(brief_file), into="codex")
    assert "Resume from a sessionport brief" in prompt
    assert "codex" in prompt
    assert "## Decisions" in prompt
