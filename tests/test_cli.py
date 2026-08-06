"""CLI tests: list, export, import, score against fixture stores."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sessionport.brief import render
from sessionport.cli import main
from sessionport.models import Brief
from sessionport.score import Score

FIXTURES = Path(__file__).parent / "fixtures"


def _env_homes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSIONPORT_CLAUDE_HOME", str(FIXTURES / "claude-code"))
    monkeypatch.setenv("SESSIONPORT_CODEX_HOME", str(FIXTURES / "codex"))
    monkeypatch.setenv("SESSIONPORT_GEMINI_HOME", str(FIXTURES / "gemini"))
    monkeypatch.setenv("SESSIONPORT_OPENCODE_HOME", str(FIXTURES / "opencode"))


def _run(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as excinfo:
        main(argv)
    return int(excinfo.value.code or 0)


def test_version() -> None:
    assert _run(["version"]) == 0


def test_list_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _env_homes(monkeypatch)
    assert _run(["list", "--agent", "claude-code", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["agent"] == "claude-code"
    assert payload[0]["message_count"] == 4


def test_export_writes_brief(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _env_homes(monkeypatch)
    out = tmp_path / "brief.md"
    assert _run(["export", "claude-code:9f9f9f9f", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---\nformat: sessionport-brief/v1")
    assert "## Decisions" in text
    assert "login.py" in text


def test_export_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _env_homes(monkeypatch)
    assert _run(["export", "codex:session-xyz", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["format"] == "sessionport-brief/v1"
    assert "## Goal" in payload["brief"]
    assert payload["messages"] == 3


def test_export_missing_session(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _env_homes(monkeypatch)
    assert _run(["export", "claude-code:nope"]) == 1
    assert "error" in capsys.readouterr().err


def test_import_renders_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    brief = Brief(
        source_agent="codex",
        session="session-xyz",
        exported="2026-08-01T12:00:00Z",
        messages=3,
        estimated_tokens=120,
        goal="Add a health endpoint to the API",
    )
    brief_file = tmp_path / "brief.md"
    brief_file.write_text(render(brief), encoding="utf-8")
    assert _run(["import", str(brief_file), "--into", "opencode"]) == 0
    out = capsys.readouterr().out
    assert "Resume from a sessionport brief" in out
    assert "opencode" in out
    assert "session-xyz" in out


def test_import_out_file(tmp_path: Path) -> None:
    brief = Brief(
        source_agent="hermes",
        session="h1",
        exported="2026-08-01T12:00:00Z",
        messages=1,
        estimated_tokens=10,
        goal="fix onboarding flow",
    )
    brief_file = tmp_path / "brief.md"
    brief_file.write_text(render(brief), encoding="utf-8")
    out_file = tmp_path / "prompt.txt"
    assert _run(["import", str(brief_file), "--out", str(out_file)]) == 0
    assert "fix onboarding flow" in out_file.read_text(encoding="utf-8")


def test_score_with_fake_judge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _env_homes(monkeypatch)
    brief = Brief(
        source_agent="claude-code",
        session="9f9f9f9f-1111-2222-3333-444444444444",
        exported="2026-08-01T12:00:00Z",
        messages=4,
        estimated_tokens=100,
        goal="Fix the auth bug in login.py",
        decisions=["Decision: switch to httpOnly secure cookies"],
    )
    brief_file = tmp_path / "brief.md"
    brief_file.write_text(render(brief), encoding="utf-8")

    def fake_score(
        transcript: str,
        brief_text: str,
        endpoint: str | None = None,
        model: str | None = None,
    ) -> Score:
        assert "auth bug" in transcript
        assert endpoint == "https://judge.example/v1"
        assert model == "judge-lite"
        return Score(fidelity=0.88, missed=["one fact"], notes="ok")

    monkeypatch.setattr("sessionport.cli.score_brief", fake_score)
    assert (
        _run(
            [
                "score",
                str(brief_file),
                "--source",
                "claude-code:9f9f9f9f",
                "--endpoint",
                "https://judge.example/v1",
                "--model",
                "judge-lite",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["fidelity"] == 0.88
    assert payload["missed"] == ["one fact"]


def test_export_all(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _env_homes(monkeypatch)
    out_dir = tmp_path / "briefs"
    assert _run(["export", "--all", "--out-dir", str(out_dir)]) == 0
    files = sorted(p.name for p in out_dir.iterdir())
    assert any("claude-code" in name for name in files)
    assert any("codex" in name for name in files)
    assert "exported" in capsys.readouterr().out


def test_export_all_requires_target(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _env_homes(monkeypatch)
    assert _run(["export"]) == 1
    assert "error" in capsys.readouterr().err


def test_copy_text_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import sessionport.cli as cli

    calls: list[list[str]] = []

    def fake_run(cmd, input=b"", check=True) -> None:  # noqa: ANN001
        calls.append(list(cmd))

    monkeypatch.setattr(cli.shutil, "which", lambda name: "clip" if name == "clip" else None)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli._copy_text("hello")
    assert calls == [["clip"]]


def test_mcp_command_without_dep(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import importlib.util

    if importlib.util.find_spec("mcp") is not None:
        pytest.skip("mcp installed; would start the stdio server")
    assert _run(["mcp"]) == 1
    assert "sessionport[mcp]" in capsys.readouterr().err
