"""sessionport command line interface.

Commands:

- ``sessionport list``       discover sessions across installed agent stores
- ``sessionport export``     turn a session into a portable sessionport-brief/v1 file
- ``sessionport import``     turn a brief into a resume prompt for any agent
- ``sessionport score``      LLM fidelity check: what did the brief lose?
- ``sessionport version``    print version
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from sessionport import __version__, tools
from sessionport.brief import FORMAT, now_iso, render
from sessionport.brief import parse as parse_brief
from sessionport.extract import estimate_tokens, extract
from sessionport.models import Brief, SessionRef
from sessionport.score import Score, ScoreError, score_brief, transcript_text
from sessionport.stores import SessionStore, StoreError, resolve_session, stores

_BOOT_PROMPT_TEMPLATE = """Resume from a sessionport brief.

The sections below are ground truth from an earlier session with {agent}
(session {session}). Continue the work: do not re-litigate settled decisions,
do not re-read files you already inspected, and do not re-run commands whose
outcomes are recorded here. If you need a fact that is missing, say so and ask.

---

{brief}
"""


def _print_error(message: str) -> None:
    print(f"sessionport: error: {message}", file=sys.stderr)


def _json_out(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _session_to_dict(session: SessionRef) -> dict[str, object]:
    return {
        "agent": session.agent,
        "session_id": session.session_id,
        "title": session.title,
        "path": session.path,
        "message_count": session.message_count,
        "updated_at": session.updated_at,
    }


def _build_brief(store: SessionStore, session: SessionRef) -> Brief:
    messages = store.load_transcript(session.session_id)
    if not messages:
        raise StoreError(f"{store.name}: session {session.session_id!r} has no readable messages")
    extracted = extract(messages)
    return Brief(
        source_agent=store.name,
        session=session.session_id,
        exported=now_iso(),
        messages=len(messages),
        estimated_tokens=estimate_tokens(messages),
        goal=extracted.goal,
        decisions=extracted.decisions,
        files=extracted.files,
        urls=extracted.urls,
        code=extracted.code,
        next_actions=extracted.next_actions,
        constraints=extracted.constraints,
        key_facts=extracted.key_facts,
    )


def _copy_text(text: str) -> bool:
    """Copy text to the system clipboard (pbcopy on macOS, clip on Windows)."""
    for command in ("pbcopy", "clip"):
        exe = shutil.which(command)
        if exe:
            subprocess.run([exe], input=text.encode("utf-8"), check=True)
            return True
    return False


def cmd_list(args: argparse.Namespace) -> int:
    all_stores = stores()
    if args.agent:
        store = all_stores.get(args.agent)
        if store is None:
            _print_error(f"unknown agent {args.agent!r}; known: {', '.join(sorted(all_stores))}")
            return 1
        selected = {args.agent: store}
    else:
        selected = all_stores

    refs: list[SessionRef] = []
    for store in selected.values():
        try:
            refs.extend(store.list_sessions())
        except StoreError as exc:
            _print_error(str(exc))

    if args.json:
        _json_out([_session_to_dict(ref) for ref in refs])
        return 0
    if not refs:
        print("no sessions found")
        return 0
    for ref in refs:
        print(f"{ref.agent:12s} {ref.session_id[:20]:20s} {ref.message_count:6d} msgs  {ref.title}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    if args.all:
        return _export_all(args)
    if not args.session:
        _print_error("export needs a session reference (agent:id) or --all")
        return 1
    try:
        store, session = resolve_session(args.session, stores())
        brief = _build_brief(store, session)
    except StoreError as exc:
        _print_error(str(exc))
        return 1

    brief_text = render(brief)

    if args.json:
        _json_out(
            {
                "format": FORMAT,
                "brief": brief_text,
                "messages": brief.messages,
                "estimated_tokens": brief.estimated_tokens,
            }
        )
        return 0

    default_name = f"brief-{store.name}-{session.session_id[:12]}.md"
    out_path = Path(args.out) if args.out else Path(default_name)
    out_path.write_text(brief_text, encoding="utf-8")
    print(f"wrote {out_path} ({brief.messages} messages, ~{brief.estimated_tokens} tokens)")
    return 0


def _export_all(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_stores = stores()
    if args.agent:
        store = all_stores.get(args.agent)
        if store is None:
            _print_error(f"unknown agent {args.agent!r}; known: {', '.join(sorted(all_stores))}")
            return 1
        selected = {args.agent: store}
    else:
        selected = all_stores

    written = 0
    failed = 0
    for store in selected.values():
        for session in store.list_sessions():
            try:
                brief = _build_brief(store, session)
            except StoreError as exc:
                _print_error(str(exc))
                failed += 1
                continue
            name = f"brief-{store.name}-{session.session_id[:12]}.md"
            (out_dir / name).write_text(render(brief), encoding="utf-8")
            written += 1
    print(f"exported {written} briefs to {out_dir}" + (f", {failed} failed" if failed else ""))
    return 1 if failed and not written else 0


def cmd_import(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        _print_error(f"brief file not found: {path}")
        return 1
    brief = parse_brief(path.read_text(encoding="utf-8"))
    target = args.into or brief.source_agent
    prompt = _BOOT_PROMPT_TEMPLATE.format(
        agent=target,
        session=brief.session,
        brief=path.read_text(encoding="utf-8"),
    )

    if args.copy:
        if not _copy_text(prompt):
            _print_error("--copy needs pbcopy (macOS) or clip (Windows); use --out instead")
            return 1
        print(f"resume prompt for {target} copied to clipboard")
        return 0
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(prompt, encoding="utf-8")
        print(f"wrote resume prompt to {out_path}")
        return 0
    print(prompt)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        _print_error(f"brief file not found: {path}")
        return 1
    brief_text = path.read_text(encoding="utf-8")
    try:
        store, session = resolve_session(args.source, stores())
        messages = store.load_transcript(session.session_id)
    except StoreError as exc:
        _print_error(str(exc))
        return 1
    if not messages:
        _print_error(f"{store.name}: session {session.session_id!r} has no readable messages")
        return 1

    try:
        score: Score = score_brief(
            transcript_text(messages),
            brief_text,
            endpoint=args.endpoint,
            model=args.model,
        )
    except (StoreError, ScoreError) as exc:
        _print_error(str(exc))
        return 1

    if args.json:
        _json_out({"fidelity": score.fidelity, "missed": score.missed, "notes": score.notes})
        return 0
    print(f"fidelity: {score.fidelity:.2f}")
    if score.missed:
        print("missed:")
        for item in score.missed:
            print(f"  - {item}")
    if score.notes:
        print(f"notes: {score.notes}")
    return 0


def cmd_version(_: argparse.Namespace) -> int:
    print(f"sessionport {__version__} (brief format {FORMAT})")
    return 0


def cmd_mcp(_: argparse.Namespace) -> int:
    from sessionport.mcp_server import run_server

    try:
        run_server()
    except ImportError:
        _print_error("MCP server needs the optional dependency: pip install 'sessionport[mcp]'")
        return 1
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    try:
        hits = tools.search(stores(), args.query, agent=args.agent, limit=args.limit)
    except StoreError as exc:
        _print_error(str(exc))
        return 1
    if args.json:
        _json_out(hits)
        return 0
    if not hits:
        print("no matches")
        return 0
    for hit in hits:
        line = (
            f"{hit['agent']:12s} {hit['session_id'][:20]:20s} "
            f"#{hit['message']:4d}  {hit['snippet']}"
        )
        print(line)
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    old_path, new_path = Path(args.old), Path(args.new)
    if not old_path.is_file() or not new_path.is_file():
        _print_error("both files must exist")
        return 1
    result = tools.diff_briefs(
        old_path.read_text(encoding="utf-8"), new_path.read_text(encoding="utf-8")
    )
    if args.json:
        _json_out(result)
        return 0
    header = f"{result['old']['agent']} → {result['new']['agent']}"
    if result["goal_changed"]:
        header += "  (goal changed)"
    print(header)
    for section, changes in result["sections"].items():
        for label, items in (("+", changes["added"]), ("-", changes["removed"])):
            for item in items:
                print(f"{label} [{section}] {item}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    result = tools.stats(stores(), agent=args.agent)
    if args.json:
        _json_out(result)
        return 0
    for name, counts in sorted(result["per_agent"].items()):
        print(
            f"{name:12s} {counts['sessions']:5d} sessions  "
            f"{counts['messages']:7d} msgs  ~{counts['tokens']:8d} tokens"
        )
    totals = result["totals"]
    print(
        f"{'total':12s} {totals['sessions']:5d} sessions  "
        f"{totals['messages']:7d} msgs  ~{totals['tokens']:8d} tokens"
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    result = tools.doctor(stores())
    if args.json:
        _json_out(result)
        return 0
    for entry in result["stores"]:
        status = f"{entry['sessions']} sessions" if entry["found"] else "not found"
        print(f"{entry['agent']:12s} {status}")
    judge = result["judge"]
    judge_status = (
        "configured" if judge["configured"] else "not configured (SESSIONPORT_JUDGE_API_KEY)"
    )
    print(f"{'judge':12s} {judge_status} ({judge['endpoint']}, {judge['model']})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sessionport", description="Portable agent sessions: carry context between agent CLIs."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="discover sessions across agent stores")
    list_p.add_argument("--agent", help="only this agent (claude-code, codex, gemini, ...)")
    list_p.add_argument("--json", action="store_true", help="machine-readable output")
    list_p.set_defaults(func=cmd_list)

    export_p = sub.add_parser("export", help="export a session (or --all) to sessionport briefs")
    export_p.add_argument(
        "session", nargs="?", help="session reference, agent:id (e.g. claude-code:abc123)"
    )
    export_p.add_argument("--all", action="store_true", help="export every discovered session")
    export_p.add_argument("--agent", help="with --all: only this agent")
    export_p.add_argument("--out", help="output path (default brief-<agent>-<id>.md)")
    export_p.add_argument(
        "--out-dir", default="briefs", help="output directory for --all (default briefs)"
    )
    export_p.add_argument("--json", action="store_true", help="print brief as JSON, no file")
    export_p.set_defaults(func=cmd_export)

    import_p = sub.add_parser("import", help="build a resume prompt from a brief")
    import_p.add_argument("file", help="sessionport brief file")
    import_p.add_argument("--into", help="target agent name (default: brief's source agent)")
    import_p.add_argument("--copy", action="store_true", help="copy prompt to clipboard")
    import_p.add_argument("--out", help="write the prompt to a file")
    import_p.set_defaults(func=cmd_import)

    score_p = sub.add_parser("score", help="LLM fidelity check: what did the brief lose?")
    score_p.add_argument("file", help="sessionport brief file")
    score_p.add_argument("--source", required=True, help="source session reference, agent:id")
    score_p.add_argument("--endpoint", help="judge endpoint override (default: env or OpenAI)")
    score_p.add_argument("--model", help="judge model override (default: env or gpt-4o-mini)")
    score_p.add_argument("--json", action="store_true", help="machine-readable output")
    score_p.set_defaults(func=cmd_score)

    mcp_p = sub.add_parser("mcp", help="run the MCP stdio server (needs sessionport[mcp])")
    mcp_p.set_defaults(func=cmd_mcp)

    search_p = sub.add_parser("search", help="search every transcript for text")
    search_p.add_argument("query", help="text to search for (case-insensitive)")
    search_p.add_argument("--agent", help="only this agent")
    search_p.add_argument("--limit", type=int, default=50, help="max hits (default 50)")
    search_p.add_argument("--json", action="store_true", help="machine-readable output")
    search_p.set_defaults(func=cmd_search)

    diff_p = sub.add_parser("diff", help="compare two briefs section by section")
    diff_p.add_argument("old", help="old brief file")
    diff_p.add_argument("new", help="new brief file")
    diff_p.add_argument("--json", action="store_true", help="machine-readable output")
    diff_p.set_defaults(func=cmd_diff)

    stats_p = sub.add_parser("stats", help="session/message/token counts per agent")
    stats_p.add_argument("--agent", help="only this agent")
    stats_p.add_argument("--json", action="store_true", help="machine-readable output")
    stats_p.set_defaults(func=cmd_stats)

    doctor_p = sub.add_parser("doctor", help="which stores were found, judge config")
    doctor_p.add_argument("--json", action="store_true", help="machine-readable output")
    doctor_p.set_defaults(func=cmd_doctor)

    version_p = sub.add_parser("version", help="print version")
    version_p.set_defaults(func=cmd_version)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
