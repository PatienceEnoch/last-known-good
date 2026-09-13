"""Command-line interface for Network Flight Recorder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyzer import analyze, findings_as_dicts, findings_as_markdown
from .collector import collect_snapshot


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nfr", description="Capture and explain Linux network state changes."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    snapshot = commands.add_parser("snapshot", help="Capture local network state")
    snapshot.add_argument("--output", type=Path, required=True)
    snapshot.add_argument(
        "--probe", action="append", default=[], help="Optional host to ping; repeat as needed"
    )

    compare = commands.add_parser("compare", help="Compare baseline and current snapshots")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("current", type=Path)
    compare.add_argument("--format", choices=("markdown", "json"), default="markdown")
    compare.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "snapshot":
        snapshot = collect_snapshot(args.probe)
        _write(args.output, json.dumps(snapshot, indent=2) + "\n")
        print(f"Snapshot written to {args.output}")
        return 0

    baseline = _load(args.baseline)
    current = _load(args.current)
    findings = analyze(baseline, current)
    if args.format == "json":
        report = json.dumps({"findings": findings_as_dicts(findings)}, indent=2) + "\n"
    else:
        report = findings_as_markdown(baseline, current, findings)
    if args.output:
        _write(args.output, report)
        print(f"Report written to {args.output}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

