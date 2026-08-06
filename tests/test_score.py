"""Score tests: judge parsing and prompt building (fully offline)."""

from __future__ import annotations

import pytest

from sessionport.models import Message
from sessionport.score import (
    ScoreError,
    build_prompt,
    parse_judge_output,
    score_brief,
    transcript_text,
)


def test_build_prompt_contains_both_sources() -> None:
    prompt = build_prompt("TRANSCRIPT_BODY", "BRIEF_BODY")
    assert "=== TRANSCRIPT ===" in prompt
    assert "TRANSCRIPT_BODY" in prompt
    assert "BRIEF_BODY" in prompt
    assert "fidelity" in prompt


def test_transcript_text_marks_roles_and_caps() -> None:
    messages = [Message(role="user", text="hello"), Message(role="assistant", text="world")]
    text = transcript_text(messages, cap=10_000)
    assert "[user] hello" in text
    assert "[assistant] world" in text

    big = [Message(role="user", text="x" * 500) for _ in range(300)]
    capped = transcript_text(big, cap=1000)
    assert "[transcript truncated]" in capped


def test_parse_judge_output_valid() -> None:
    raw = (
        '{"fidelity": 0.93, "missed": ["lost decision about DB index"], "notes": "close, one gap"}'
    )
    score = parse_judge_output(raw)
    assert score.fidelity == pytest.approx(0.93)
    assert score.missed == ["lost decision about DB index"]
    assert score.notes == "close, one gap"


def test_parse_judge_output_string_fidelity_and_clamp() -> None:
    assert parse_judge_output('{"fidelity": "0.8", "missed": []}').fidelity == pytest.approx(0.8)
    assert parse_judge_output('{"fidelity": 2.5, "missed": []}').fidelity == pytest.approx(1.0)


def test_parse_judge_output_invalid() -> None:
    with pytest.raises(ScoreError):
        parse_judge_output("the brief is fine, no JSON here")


def test_score_brief_with_fake_judge() -> None:
    def fake_judge(prompt: str) -> str:
        assert "=== TRANSCRIPT ===" in prompt
        return '{"fidelity": 0.9, "missed": ["x"], "notes": "ok"}'

    score = score_brief("transcript", "brief", judge=fake_judge)
    assert score.fidelity == pytest.approx(0.9)
    assert score.missed == ["x"]
