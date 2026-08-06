"""Optional LLM fidelity scoring for briefs.

The scorer answers one question: what did the original session know that the
brief lost? It is opt-in (needs ``RELAY_JUDGE_API_KEY``), runs against any
OpenAI-compatible chat endpoint, and is never on the export path. Tests inject
a fake judge so the suite runs fully offline.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from sess.models import Message

Judge = Callable[[str], str]

_TRANSCRIPT_CAP = 120_000
_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


@dataclass
class Score:
    """Fidelity of a brief relative to its source transcript."""

    fidelity: float
    missed: list[str] = field(default_factory=list)
    notes: str = ""


class ScoreError(RuntimeError):
    pass


def transcript_text(messages: list[Message], cap: int = _TRANSCRIPT_CAP) -> str:
    """Render a transcript for the judge, oldest first, truncated."""
    parts: list[str] = []
    used = 0
    for message in messages:
        block = f"[{message.role}] {message.text}"
        if used + len(block) > cap:
            parts.append("[transcript truncated]")
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def build_prompt(transcript: str, brief_text: str) -> str:
    return (
        "You measure how well a session brief preserves an agent session transcript.\n"
        "Compare the transcript and the brief. The brief may compress freely, but it must "
        "not lose: the goal, settled decisions, files touched, URLs referenced, constraints, "
        "and any facts the agent would need to resume work without re-discovering them.\n"
        'Reply with ONLY a JSON object: {"fidelity": 0.0-1.0, "missed": ["fact lost 1", ...], '  # noqa: E501
        '"notes": "one sentence"}\n\n'
        f"=== TRANSCRIPT ===\n{transcript}\n\n=== BRIEF ===\n{brief_text}"
    )


def parse_judge_output(raw: str) -> Score:
    """Parse the judge's JSON reply leniently."""
    match = _JSON_BLOCK_RE.search(raw)
    if not match:
        raise ScoreError(f"judge returned no JSON: {raw[:200]!r}")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ScoreError(f"judge returned invalid JSON: {exc}") from exc
    try:
        fidelity = float(payload.get("fidelity", 0.0))
    except (TypeError, ValueError):
        fidelity = 0.0
    missed = payload.get("missed")
    if not isinstance(missed, list):
        missed = []
    notes = payload.get("notes")
    clamped = max(0.0, min(1.0, fidelity))
    return Score(fidelity=clamped, missed=[str(x) for x in missed], notes=str(notes or ""))


def http_judge() -> Judge:
    """Build the default judge: an OpenAI-compatible chat completion call."""
    endpoint = os.environ.get("RELAY_JUDGE_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    api_key = os.environ.get("RELAY_JUDGE_API_KEY", "")
    model = os.environ.get("RELAY_JUDGE_MODEL", "gpt-4o-mini")
    if not api_key:
        hint = (
            "RELAY_JUDGE_API_KEY is not set; set it (plus RELAY_JUDGE_ENDPOINT / RELAY_JUDGE_MODEL)"
        )
        raise ScoreError(f"{hint} to score")

    def judge(prompt: str) -> str:
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise fidelity auditor for agent session briefs.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])

    return judge


def score_brief(transcript: str, brief_text: str, judge: Judge | None = None) -> Score:
    """Score a brief against its source transcript using a judge."""
    judge_fn = judge or http_judge()
    prompt = build_prompt(transcript, brief_text)
    return parse_judge_output(judge_fn(prompt))
