"""Fleet tooling tests: search, diff, stats, doctor (fully offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sessionport import tools
from sessionport.stores import stores

FIXTURES = Path(__file__).parent / "fixtures"


def _env_homes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSIONPORT_CLAUDE_HOME", str(FIXTURES / "claude-code"))
    monkeypatch.setenv("SESSIONPORT_CODEX_HOME", str(FIXTURES / "codex"))
    monkeypatch.setenv("SESSIONPORT_CURSOR_HOME", str(FIXTURES / "cursor"))


def test_search_finds_match(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    hits = tools.search(stores(), "auth bug")
    assert any(hit["agent"] == "claude-code" for hit in hits)
    assert any("session cookie" in hit["snippet"] for hit in hits)


def test_search_agent_filter_and_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    hits = tools.search(stores(), "the", agent="codex", limit=1)
    assert len(hits) <= 1
    assert all(hit["agent"] == "codex" for hit in hits)


def test_search_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    assert tools.search(stores(), "zzz-no-such-string") == []


def test_diff_briefs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sessionport.brief import render
    from sessionport.models import Brief

    def brief(decision: str, extra: list[str] | None = None) -> str:
        return render(
            Brief(
                source_agent="codex",
                session="s1",
                exported="2026-08-01T00:00:00Z",
                messages=2,
                estimated_tokens=50,
                goal="Add a health endpoint",
                decisions=[decision],
                files=extra or ["app.py"],
            )
        )

    old_text = brief("Decision: use a lightweight route")
    new_text = brief("Decision: use a lightweight route", extra=["app.py", "Dockerfile"])
    result = tools.diff_briefs(old_text, new_text)
    assert result["new"]["agent"] == "codex"
    assert result["sections"]["files"]["added"] == ["Dockerfile"]
    assert result["sections"]["files"]["removed"] == []
    assert result["sections"]["decisions"]["added"] == []
    assert result["goal_changed"] is False


def test_stats_totals(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    result = tools.stats(stores())
    assert result["totals"]["sessions"] >= 3
    assert result["totals"]["messages"] > 0
    assert result["per_agent"]["claude-code"]["sessions"] == 1
    assert result["per_agent"]["claude-code"]["messages"] == 4


def test_doctor_reports_stores_and_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    _env_homes(monkeypatch)
    monkeypatch.delenv("SESSIONPORT_JUDGE_API_KEY", raising=False)
    result = tools.doctor(stores())
    agents = {entry["agent"]: entry for entry in result["stores"]}
    assert agents["claude-code"]["found"] is True
    assert agents["claude-code"]["sessions"] == 1
    assert result["judge"]["configured"] is False
