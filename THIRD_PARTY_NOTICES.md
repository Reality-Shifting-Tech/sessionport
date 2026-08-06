# Third-Party Notices

sessionport reads session stores produced by the following agent CLIs. sessionport is not
affiliated with, and does not endorse, any of them. Their names, logos, and
session formats remain the property of their respective owners.

| Product | Owner | Format read | Official logo source |
|---|---|---|---|
| Claude Code | Anthropic | JSONL transcripts under `~/.claude/projects` | github.com/anthropics |
| Codex | OpenAI | JSONL sessions under `~/.codex/sessions` | github.com/openai |
| OpenCode | SST | JSON session files | github.com/sst |
| Gemini CLI | Google | Markdown transcripts | github.com/google-gemini |
| Hermes | Nous Research | SQLite session databases | github.com/NousResearch |

## Logos

The logo images in `docs/images/agents/` are the official organization
avatars of the respective owners, downloaded from GitHub for documentation
purposes. Each remains the property of its owner and is used here solely to
identify the compatible agent CLI.

## Dependencies

sessionport is MIT licensed. Its runtime dependencies are:

- httpx (BSD-3-Clause)

Development-only: pytest (MIT), ruff (MIT), mypy (MIT), pillow (HPND).

## Session formats

The brief format `sessionport-brief/v1` is original to this project. Parsers for
vendor session formats were written from observed file shapes; they are
defensive by design and may not capture every vendor field.
