"""Session store adapters.

Each adapter knows how to discover and read one coding agent's local
session store. Adapters are defensive on purpose: vendor formats change, so
parsers sniff known shapes and degrade to a generic line-based read instead
of failing. Store locations can be overridden with environment variables so
the tool works in CI and on unusual setups:

- ``SESSIONPORT_CLAUDE_HOME`` (default ``~/.claude/projects``)
- ``SESSIONPORT_CODEX_HOME`` (default ``~/.codex/sessions``)
- ``SESSIONPORT_GEMINI_HOME`` (default ``~/.gemini/sessions``)
- ``SESSIONPORT_OPENCODE_HOME`` (default varies by platform)
- ``SESSIONPORT_HERMES_DB`` (default first existing ``~/.hermes/*.db`` candidate)
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Protocol

from sessionport.models import Message, SessionRef

StoreError = RuntimeError

_JSONL_ROLE_KEYS = ("role", "role_name", "actor", "type")
_JSONL_TEXT_BLOCK_TYPES = (
    "text",
    "input_text",
    "output_text",
    "text_delta",
    "summary_text",
)


def _content_to_text(content: object) -> str:
    """Coerce a JSON ``content`` field (string or block list) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type", ""))
            if block_type in _JSONL_TEXT_BLOCK_TYPES and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif block_type == "tool_result":
                inner = block.get("content")
                parts.append(_content_to_text(inner))
        return "\n".join(parts)
    return ""


def _line_message(obj: dict) -> dict:
    """Extract the message dict from a JSONL line, unwrapping vendor wrappers."""
    payload = obj.get("payload")
    if not isinstance(payload, dict):
        payload = obj
    message = payload.get("message")
    if not isinstance(message, dict):
        message = payload
    return message


def _jsonl_line_role(obj: dict) -> str:
    """Map a JSONL line to a role: user, assistant, tool, or other."""
    message = _line_message(obj)
    content = message.get("content")
    if isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "tool_result" for block in content
    ):
        return "tool"
    for key in _JSONL_ROLE_KEYS:
        role = message.get(key)
        if isinstance(role, str):
            lowered = role.lower()
            if lowered in ("user", "assistant"):
                return lowered
            if "tool" in lowered:
                return "tool"
    return "other"


def _jsonl_line_text(obj: dict) -> str:
    message = _line_message(obj)
    return _content_to_text(message.get("content"))


def read_jsonl_messages(path: Path) -> list[Message]:
    """Parse a JSONL transcript into messages, sniffing vendor shapes."""
    messages: list[Message] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            role = _jsonl_line_role(obj)
            text = _jsonl_line_text(obj).strip()
            if not text:
                continue
            timestamp = None
            for key in ("timestamp", "created_at", "ts"):
                if isinstance(obj.get(key), str):
                    timestamp = obj[key]
                    break
            messages.append(Message(role=role, text=text, timestamp=timestamp))
    return messages


def first_user_text(messages: list[Message]) -> str:
    """The goal-ish text: the first substantive user message."""
    for message in messages:
        if message.role == "user" and message.text.strip():
            return message.text.strip()
    return "(untitled)"


class SessionStore(Protocol):
    name: str

    def list_sessions(self) -> list[SessionRef]: ...

    def load_transcript(self, session_id: str) -> list[Message]: ...


class JsonlStore:
    """Generic adapter for agents that store one JSONL file per session."""

    name: str

    def __init__(self, name: str, home: Path, recursive: bool = False) -> None:
        self.name = name
        self._home = home
        self._recursive = recursive

    def list_sessions(self) -> list[SessionRef]:
        pattern = "**/*.jsonl" if self._recursive else "*.jsonl"
        refs: list[SessionRef] = []
        if not self._home.is_dir():
            return refs
        for path in sorted(self._home.glob(pattern)):
            lines = 0
            first_text = ""
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    lines += 1
                    if not first_text:
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                first_text = _jsonl_line_text(obj).strip()
                        except json.JSONDecodeError:
                            continue
            if lines == 0:
                continue
            refs.append(
                SessionRef(
                    agent=self.name,
                    session_id=path.stem,
                    title=first_text[:120] or path.stem,
                    path=str(path),
                    message_count=lines,
                )
            )
        return refs

    def load_transcript(self, session_id: str) -> list[Message]:
        pattern = "**/*.jsonl" if self._recursive else "*.jsonl"
        for path in self._home.glob(pattern):
            if path.stem == session_id:
                return read_jsonl_messages(path)
        raise StoreError(f"{self.name}: no session {session_id!r} under {self._home}")


class ClaudeCodeStore(JsonlStore):
    def __init__(self) -> None:
        home = Path(os.environ.get("SESSIONPORT_CLAUDE_HOME", Path.home() / ".claude" / "projects"))
        super().__init__("claude-code", home)


class CodexStore(JsonlStore):
    def __init__(self) -> None:
        home = Path(os.environ.get("SESSIONPORT_CODEX_HOME", Path.home() / ".codex" / "sessions"))
        super().__init__("codex", home)


class CursorStore(JsonlStore):
    """Cursor agent sessions (JSONL under ~/.cursor/agent)."""

    def __init__(self) -> None:
        override = os.environ.get("SESSIONPORT_CURSOR_HOME")
        if override:
            home = Path(override)
        else:
            candidates = [Path.home() / ".cursor" / "agent", Path.home() / ".cursor"]
            home = next((p for p in candidates if p.is_dir()), candidates[0])
        super().__init__("cursor", home, recursive=True)


class WindsurfStore(JsonlStore):
    """Windsurf editor agent sessions (JSONL under the Windsurf data dir)."""

    def __init__(self) -> None:
        override = os.environ.get("SESSIONPORT_WINDSURF_HOME")
        if override:
            home = Path(override)
        else:
            candidates = [
                Path.home() / ".windsurf" / "sessions",
                Path.home() / ".codeium" / "windsurf" / "sessions",
                Path.home() / ".windsurf",
            ]
            home = next((p for p in candidates if p.is_dir()), candidates[0])
        super().__init__("windsurf", home, recursive=True)


class OpenClawStore(JsonlStore):
    """OpenClaw agent sessions (JSONL under ~/.openclaw)."""

    def __init__(self) -> None:
        override = os.environ.get("SESSIONPORT_OPENCLAW_HOME")
        if override:
            home = Path(override)
        else:
            candidates = [
                Path.home() / ".openclaw" / "sessions",
                Path.home() / ".openclaw",
            ]
            home = next((p for p in candidates if p.is_dir()), candidates[0])
        super().__init__("openclaw", home, recursive=True)


class ClineStore(JsonlStore):
    """Cline task history (JSONL under the Cline tasks dir)."""

    def __init__(self) -> None:
        override = os.environ.get("SESSIONPORT_CLINE_HOME")
        if override:
            home = Path(override)
        else:
            candidates = [
                Path.home() / ".config" / "cline" / "tasks",
                Path.home() / "Library" / "Application Support" / "Cline" / "tasks",
                Path.home() / ".config" / "cline",
            ]
            home = next((p for p in candidates if p.is_dir()), candidates[0])
        super().__init__("cline", home, recursive=True)


class GenericJsonlStore(JsonlStore):
    """Base for agents with JSONL session stores under ``~/.<name>``.

    Resolves the store home from a ``SESSIONPORT_<NAME>_HOME`` override first,
    then the first existing candidate path, then the first candidate.
    """

    def __init__(self, name: str, env_key: str, candidates: list[Path]) -> None:
        override = os.environ.get(env_key)
        home = (
            Path(override)
            if override
            else next((p for p in candidates if p.is_dir()), candidates[0])
        )
        super().__init__(name, home, recursive=True)


class GooseStore(GenericJsonlStore):
    """Goose (Block) sessions, JSONL under ~/.goose."""

    def __init__(self) -> None:
        super().__init__(
            "goose",
            "SESSIONPORT_GOOSE_HOME",
            [Path.home() / ".goose" / "sessions", Path.home() / ".goose"],
        )


class KiloStore(GenericJsonlStore):
    """Kilo (Cerebras) sessions, JSONL under ~/.kilo."""

    def __init__(self) -> None:
        super().__init__(
            "kilo",
            "SESSIONPORT_KILO_HOME",
            [Path.home() / ".kilo" / "sessions", Path.home() / ".kilo"],
        )


class JunieStore(GenericJsonlStore):
    """Junie (JetBrains) sessions, JSONL under ~/.junie."""

    def __init__(self) -> None:
        super().__init__(
            "junie",
            "SESSIONPORT_JUNIE_HOME",
            [Path.home() / ".junie" / "sessions", Path.home() / ".junie"],
        )


class GrokStore(GenericJsonlStore):
    """Grok Code (xAI) sessions, JSONL under ~/.grok."""

    def __init__(self) -> None:
        super().__init__(
            "grok",
            "SESSIONPORT_GROK_HOME",
            [Path.home() / ".grok" / "sessions", Path.home() / ".grok"],
        )


class CopilotStore(GenericJsonlStore):
    """GitHub Copilot CLI sessions, JSONL under ~/.copilot-cli."""

    def __init__(self) -> None:
        super().__init__(
            "copilot",
            "SESSIONPORT_COPILOT_HOME",
            [
                Path.home() / ".copilot-cli" / "sessions",
                Path.home() / ".copilot-cli",
            ],
        )


class VibeStore(GenericJsonlStore):
    """Mistral Vibe sessions, JSONL under ~/.vibe."""

    def __init__(self) -> None:
        super().__init__(
            "vibe",
            "SESSIONPORT_VIBE_HOME",
            [
                Path.home() / ".vibe" / "sessions",
                Path.home() / ".local" / "share" / "vibe" / "sessions",
                Path.home() / ".vibe",
            ],
        )


class AiderStore:
    """Aider session history (markdown files under ~/.aider.chat/history).

    Aider writes one markdown file per repo session: lines starting with
    ``####`` are user prompts, everything else in the block is the response.
    """

    name = "aider"

    def __init__(self) -> None:
        override = os.environ.get("SESSIONPORT_AIDER_HOME")
        self._home = Path(override or Path.home() / ".aider.chat" / "history")

    def list_sessions(self) -> list[SessionRef]:
        refs: list[SessionRef] = []
        if not self._home.is_dir():
            return refs
        for path in sorted(self._home.rglob("*.md")):
            messages = self._parse_file(path)
            if not messages:
                continue
            refs.append(
                SessionRef(
                    agent=self.name,
                    session_id=path.stem,
                    title=first_user_text(messages)[:120],
                    path=str(path),
                    message_count=len(messages),
                )
            )
        return refs

    def load_transcript(self, session_id: str) -> list[Message]:
        for path in self._home.rglob("*.md"):
            if path.stem == session_id:
                messages = self._parse_file(path)
                if messages:
                    return messages
        raise StoreError(f"aider: no session {session_id!r} under {self._home}")

    def _parse_file(self, path: Path) -> list[Message]:
        messages: list[Message] = []
        role: str | None = None
        buffer: list[str] = []

        def flush() -> None:
            nonlocal role, buffer
            text = "\n".join(buffer).strip()
            if text and role:
                messages.append(Message(role=role, text=text))
            role = None
            buffer = []

        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.rstrip("\n")
                if line.startswith("#### "):
                    flush()
                    role = "user"
                    buffer.append(line[5:])
                elif line.strip():
                    if role == "user":
                        flush()
                        role = "assistant"
                        buffer.append(line)
                    elif role is None:
                        role = "assistant"
                        buffer.append(line)
                    else:
                        buffer.append(line)
        flush()
        return messages


class GeminiStore:
    """Adapter for the Gemini CLI markdown transcript store."""

    name = "gemini"

    def __init__(self) -> None:
        self._home = Path(
            os.environ.get("SESSIONPORT_GEMINI_HOME", Path.home() / ".gemini" / "sessions")
        )

    def list_sessions(self) -> list[SessionRef]:
        refs: list[SessionRef] = []
        if not self._home.is_dir():
            return refs
        for path in sorted(self._home.glob("*.*")):
            if path.suffix.lower() not in (".txt", ".md"):
                continue
            messages = self._parse_file(path)
            title = first_user_text(messages) if messages else path.stem
            refs.append(
                SessionRef(
                    agent=self.name,
                    session_id=path.stem,
                    title=title[:120],
                    path=str(path),
                    message_count=len(messages),
                )
            )
        return refs

    def load_transcript(self, session_id: str) -> list[Message]:
        for suffix in (".txt", ".md"):
            path = self._home / f"{session_id}{suffix}"
            if path.is_file():
                return self._parse_file(path)
        raise StoreError(f"gemini: no session {session_id!r} under {self._home}")

    def _parse_file(self, path: Path) -> list[Message]:
        messages: list[Message] = []
        current: str | None = None
        buffer: list[str] = []
        role_map = {"user": "user", "model": "assistant", "tool": "tool", "system": "other"}

        def flush() -> None:
            nonlocal current, buffer
            if current is not None and buffer:
                text = "\n".join(buffer).strip()
                if text:
                    messages.append(Message(role=role_map.get(current, "other"), text=text))
            current = None
            buffer = []

        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                match = re.match(r"^#{1,3}\s+(\w+)", line.strip())
                if match and match.group(1).lower() in role_map:
                    flush()
                    current = match.group(1).lower()
                elif current is not None:
                    buffer.append(line)
        flush()
        return messages


class OpenCodeStore:
    """Adapter for OpenCode's JSON session storage."""

    name = "opencode"

    def __init__(self) -> None:
        home = os.environ.get("SESSIONPORT_OPENCODE_HOME")
        if not home:
            candidates = [
                Path.home() / ".local" / "share" / "opencode",
                Path.home() / "Library" / "Application Support" / "opencode",
            ]
            home = str(next((p for p in candidates if p.is_dir()), candidates[0]))
        self._home = Path(home)

    def list_sessions(self) -> list[SessionRef]:
        refs: list[SessionRef] = []
        if not self._home.is_dir():
            return refs
        for path in sorted(self._home.rglob("*.json")):
            messages = self._read_session_file(path)
            if not messages:
                continue
            session_id = path.stem
            refs.append(
                SessionRef(
                    agent=self.name,
                    session_id=session_id,
                    title=first_user_text(messages)[:120],
                    path=str(path),
                    message_count=len(messages),
                )
            )
        return refs

    def load_transcript(self, session_id: str) -> list[Message]:
        for path in self._home.rglob("*.json"):
            if path.stem == session_id:
                messages = self._read_session_file(path)
                if messages:
                    return messages
        raise StoreError(f"opencode: no session {session_id!r} under {self._home}")

    def _read_session_file(self, path: Path) -> list[Message]:
        try:
            obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            return []
        if not isinstance(obj, dict):
            return []
        return self._json_messages(obj)

    def _json_messages(self, obj: dict) -> list[Message]:
        messages: list[Message] = []
        parts = obj.get("parts")
        if isinstance(parts, list):
            for part in parts:
                if not isinstance(part, dict):
                    continue
                part_type = str(part.get("type", ""))
                if part_type == "text" and isinstance(part.get("text"), str):
                    messages.append(Message(role="assistant", text=part["text"]))
                elif part_type == "user":
                    content = part.get("content")
                    if isinstance(content, list):
                        text = _content_to_text(content)
                        if text:
                            messages.append(Message(role="user", text=text))
        raw = obj.get("messages")
        if isinstance(raw, list) and not messages:
            for item in raw:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role", "")).lower()
                text = _content_to_text(item.get("content"))
                if text.strip():
                    mapped = role if role in ("user", "assistant", "tool") else "other"
                    messages.append(Message(role=mapped, text=text))
        return messages


class HermesStore:
    """Adapter for Hermes session databases.

    Hermes stores sessions in SQLite; the exact schema varies by version, so
    this adapter introspects tables and maps columns by name. Point
    ``SESSIONPORT_HERMES_DB`` at the database when it is not auto-discovered.
    """

    name = "hermes"

    def __init__(self) -> None:
        override = os.environ.get("SESSIONPORT_HERMES_DB")
        if override:
            self._db = Path(override)
        else:
            candidates = sorted(Path.home().glob(".hermes/*.db"))
            fallback = Path.home() / ".hermes" / "sessions.db"
            existing = (p for p in candidates if p.stat().st_size > 0)
            self._db = next(existing, candidates[0] if candidates else fallback)

    def list_sessions(self) -> list[SessionRef]:
        refs: list[SessionRef] = []
        if not self._db.is_file():
            return refs
        with sqlite3.connect(f"file:{self._db}?mode=ro", uri=True) as conn:
            table = self._sessions_table(conn)
            if table is None:
                return refs
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            id_col = self._pick(cols, ("id", "session_id", "uuid"))
            title_col = self._pick(cols, ("title", "summary", "name"))
            if id_col is None:
                return refs
            title_sql = f", {title_col}" if title_col else ""
            rows = conn.execute(f"SELECT {id_col}{title_sql} FROM {table}").fetchall()
            for row in rows:
                session_id = str(row[0])
                title = str(row[1]) if title_col else session_id
                refs.append(
                    SessionRef(
                        agent=self.name,
                        session_id=session_id,
                        title=(title or session_id)[:120],
                        path=str(self._db),
                        message_count=0,
                    )
                )
        return refs

    def load_transcript(self, session_id: str) -> list[Message]:
        if not self._db.is_file():
            raise StoreError(f"hermes: session database not found at {self._db}")
        with sqlite3.connect(f"file:{self._db}?mode=ro", uri=True) as conn:
            table = self._messages_table(conn)
            if table is None:
                raise StoreError(f"hermes: no messages table in {self._db}")
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            sid_col = self._pick(cols, ("session_id", "session", "conversation_id"))
            role_col = self._pick(cols, ("role", "sender", "author"))
            text_col = self._pick(cols, ("content", "text", "body", "message"))
            if sid_col is None or text_col is None:
                raise StoreError(f"hermes: cannot map columns in {table}: {cols}")
            role_sql = f", {role_col}" if role_col else ""
            rows = conn.execute(
                f"SELECT {text_col}{role_sql} FROM {table} WHERE {sid_col} = ?", (session_id,)
            ).fetchall()
            messages: list[Message] = []
            for row in rows:
                text = str(row[0]).strip()
                if not text:
                    continue
                role = str(row[1]).lower() if role_col else "other"
                if role not in ("user", "assistant", "tool"):
                    role = "other"
                messages.append(Message(role=role, text=text))
        return messages

    @staticmethod
    def _tables(conn: sqlite3.Connection) -> list[str]:
        return [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]

    @staticmethod
    def _sessions_table(conn: sqlite3.Connection) -> str | None:
        tables = HermesStore._tables(conn)
        for name in ("sessions", "conversations", "threads"):
            if name in tables:
                return name
        return None

    @staticmethod
    def _messages_table(conn: sqlite3.Connection) -> str | None:
        tables = HermesStore._tables(conn)
        for name in ("messages", "message", "turns"):
            if name in tables:
                return name
        return None

    @staticmethod
    def _pick(cols: list[str], candidates: tuple[str, ...]) -> str | None:
        for candidate in candidates:
            if candidate in cols:
                return candidate
        return None


def stores() -> dict[str, SessionStore]:
    """All known adapters, keyed by adapter name."""
    return {
        "claude-code": ClaudeCodeStore(),
        "codex": CodexStore(),
        "cursor": CursorStore(),
        "aider": AiderStore(),
        "windsurf": WindsurfStore(),
        "openclaw": OpenClawStore(),
        "cline": ClineStore(),
        "goose": GooseStore(),
        "kilo": KiloStore(),
        "junie": JunieStore(),
        "grok": GrokStore(),
        "copilot": CopilotStore(),
        "vibe": VibeStore(),
        "gemini": GeminiStore(),
        "opencode": OpenCodeStore(),
        "hermes": HermesStore(),
    }


def resolve_session(
    ref: str, available: dict[str, SessionStore]
) -> tuple[SessionStore, SessionRef]:
    """Resolve ``agent:id`` (or a bare id searched across agents) to a session."""
    if ":" in ref:
        agent, session_id = ref.split(":", 1)
        store = available.get(agent)
        if store is None:
            raise StoreError(f"unknown agent {agent!r}; known: {', '.join(sorted(available))}")
        for session in store.list_sessions():
            if session.session_id == session_id or session.session_id.startswith(session_id):
                return store, session
        raise StoreError(f"{agent}: no session {session_id!r}")
    matches: list[tuple[SessionStore, SessionRef]] = []
    for store in available.values():
        for session in store.list_sessions():
            if session.session_id == ref or session.session_id.startswith(ref):
                matches.append((store, session))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        agents = ", ".join(f"{store.name}:{session.session_id}" for store, session in matches)
        raise StoreError(f"ambiguous id {ref!r}; use agent:id. matches: {agents}")
    raise StoreError(f"no session matching {ref!r} in any store")
