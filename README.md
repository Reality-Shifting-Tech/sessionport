<p align="center">
  <img src="assets/logo.png" alt="sess" width="120">
</p>

<h1 align="center">sess</h1>

<p align="center">
  <b>Carry your AI agent sessions between CLIs.</b><br>
  Export any session to one portable, human-readable brief. Resume it in any other agent.
</p>

<p align="center">
  <a href="https://github.com/Reality-Shifting-Tech/sess/actions"><img alt="CI" src="https://github.com/Reality-Shifting-Tech/sess/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/sess/"><img alt="PyPI" src="https://img.shields.io/pypi/v/sess"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/Reality-Shifting-Tech/sess"></a>
</p>

<p align="center">
  <img src="docs/images/terminal-demo.gif" alt="sess in action" width="720">
</p>

---

## Why

You work in Claude Code today and OpenCode tomorrow. Codex for the weekend, Gemini for the big refactor. Every agent has its own session store, its own format, and zero memory of the others. Switch agents and your context dies: the decisions, the constraints, the files you already read, the next steps you agreed on.

sess is the missing layer. It reads any agent's local session store, distills the durable parts into one markdown brief, and hands that brief to any other agent as a resume prompt.

- **Offline by default.** Export never calls the network. Your sessions stay on your machine.
- **Open format.** A brief is markdown with plain frontmatter: read it, diff it, commit it.
- **One command.** `sess export` out of one agent, `sess import` into the next.

## Supported agents

| | Agent | Store |
|---|---|---|
| <img src="docs/images/agents/claude-code.png" width="24"> | **Claude Code** | JSONL transcripts (`~/.claude/projects`) |
| <img src="docs/images/agents/codex.png" width="24"> | **Codex** | JSONL sessions (`~/.codex/sessions`) |
| <img src="docs/images/agents/opencode.png" width="24"> | **OpenCode** | JSON session files |
| <img src="docs/images/agents/gemini.png" width="24"> | **Gemini CLI** | Markdown transcripts |
| <img src="docs/images/agents/hermes.png" width="24"> | **Hermes** | SQLite session databases |

Every store location can be overridden with a `RELAY_*` environment variable
for CI and unusual setups (`RELAY_CLAUDE_HOME`, `RELAY_CODEX_HOME`,
`RELAY_GEMINI_HOME`, `RELAY_OPENCODE_HOME`, `RELAY_HERMES_DB`).

## Install

```bash
pip install sess
# or
uv tool install sess
```

Requires Python >= 3.11. macOS and Linux.

## Quickstart

```bash
# see every session, from every agent, in one place
sess list

# turn a session into a portable brief
sess export claude-code:9f9f9f9f

# hand the brief to another agent as a resume prompt
sess import brief-claude-code-9f9f9f9f.md --into codex --copy

# did the brief lose anything? (optional, needs an LLM key)
sess score brief-claude-code-9f9f9f9f.md --source claude-code:9f9f9f9f
```

That's the whole loop: export, carry, import, resume.

## How it works

<p align="center">
  <img src="docs/images/architecture.png" alt="sess architecture" width="860">
</p>

1. **Discover.** `sess list` walks each agent's local session store.
2. **Extract.** `sess export` reads the transcript and pulls out the durable
   parts: goal, decisions, files touched, URLs, code blocks, next actions,
   constraints, key facts. Deterministic heuristics, no LLM, no network.
3. **Carry.** The result is one `sess-brief/v1` markdown file.
4. **Resume.** `sess import` wraps the brief in a resume prompt for any
   target agent. Paste it, or `--copy` it, and the new agent continues the
   work without re-litigating settled decisions.

## The brief format

`sess-brief/v1` is markdown with flat YAML-flavored frontmatter. Example:

```markdown
---
format: sess-brief/v1
source-agent: claude-code
session: 9f9f9f9f-1111-2222-3333-444444444444
exported: 2026-08-06T00:41:29Z
messages: 4
estimated_tokens: 121
---

# Session brief (claude-code)

## Goal

Fix the auth bug in login.py: the session cookie is not being set on refresh

## Decisions

- Decision: switch to httpOnly secure cookies. We'll go with SameSite=Lax...

## State: files

- login.py
- tests/test_session.py

## Constraints

- Constraint: never store tokens in localStorage.
```

Human-readable, git-diffable, machine-parseable. The format is versioned in
the frontmatter so future revisions migrate explicitly.

## Fidelity scoring

A brief is only useful if it kept what mattered. `sess score` compares a
brief against its source transcript with an LLM judge and reports:

- **fidelity**: 0.0-1.0, how much of the session's durable knowledge survived
- **missed**: the specific facts the brief lost
- **notes**: one-sentence verdict

Opt-in and env-gated, against any OpenAI-compatible endpoint:

```bash
export RELAY_JUDGE_API_KEY=sk-...
export RELAY_JUDGE_ENDPOINT=https://api.openai.com/v1/chat/completions  # default
export RELAY_JUDGE_MODEL=gpt-4o-mini                                     # default
sess score brief.md --source claude-code:9f9f9f9f
```

The judge never runs on the export path, and transcripts are truncated to
120k characters.

## CLI reference

```
sess list [--agent NAME] [--json]
sess export SESSION [--out FILE] [--json]
sess import FILE [--into AGENT] [--copy] [--out FILE]
sess score FILE --source AGENT:SESSION [--json]
sess version
```

`SESSION` is `agent:id` (e.g. `claude-code:9f9f9f9f`), or a bare id that is
searched across all stores.

## Development

```bash
uv sync --extra dev
make all          # lint + typecheck + test (the full gate)
make images       # regenerate docs/images
```

30 tests, zero-warning lint, strict mypy. See [AGENTS.md](AGENTS.md) for the
operational reference and [CONTRIBUTING.md](CONTRIBUTING.md) for the
contribution contract.

## Roadmap

- MCP server (v0.2): the same library behind an agent-native surface
- More adapters: Cursor, Aider, Warp, Windsurf
- Local judge via Ollama for fully offline scoring
- Windows parity

## License

MIT. See [LICENSE](LICENSE). Third-party attributions in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
