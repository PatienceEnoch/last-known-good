"""Command-line interface for Network Flight Recorder."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .analyzer import (
    analyze,
    diagnose,
    diagnosis_as_dict,
    findings_as_dicts,
    findings_as_markdown,
)
from .cloudwatch import publish_snapshot_metrics
from .collector import collect_snapshot
from .incidents import build_incident_summary, publish_incident_summary
from .privacy import redact_snapshot
from .retention import apply_prune, prune_candidates


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nfr",
        description="Capture and explain Linux network state changes.",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    snapshot = commands.add_parser(
        "snapshot",
        help="Capture local network state",
    )

    snapshot.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    snapshot.add_argument(
        "--probe",
        action="append",
        default=[],
        help="Optional host to ping; repeat as needed",
    )

    snapshot.add_argument(
        "--dns",
        action="append",
        default=[],
        help="Optional name to resolve; repeat as needed",
    )

    snapshot.add_argument(
        "--redact",
        action="store_true",
        help="Pseudonymize sensitive fields before writing",
    )

    snapshot.add_argument(
        "--cloudwatch",
        action="store_true",
        help="Publish privacy-preserving health metrics to AWS CloudWatch",
    )

    compare = commands.add_parser(
        "compare",
        help="Compare baseline and current snapshots",
    )

    compare.add_argument(
        "baseline",
        type=Path,
    )

    compare.add_argument(
        "current",
        type=Path,
    )

    compare.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )

    compare.add_argument(
        "--output",
        type=Path,
    )

    compare.add_argument(
        "--cloudwatch",
        action="store_true",
        help="Publish a privacy-preserving incident summary to CloudWatch Logs",
    )

    prune = commands.add_parser(
        "prune",
        help="Plan or apply snapshot retention",
    )

    prune.add_argument(
        "--directory",
        type=Path,
        default=Path("snapshots"),
    )

    prune.add_argument(
        "--keep",
        type=int,
        default=100,
    )

    prune.add_argument(
        "--max-age-days",
        type=int,
        default=30,
    )

    prune.add_argument(
        "--apply",
        action="store_true",
        help="Delete planned files",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "snapshot":
        snapshot = collect_snapshot(
            args.probe,
            args.dns,
        )

        if args.redact:
            key = os.environ.get("NFR_REDACTION_KEY", "")

            if not key:
                raise SystemExit(
                    "Set NFR_REDACTION_KEY before using --redact"
                )

            snapshot = redact_snapshot(
                snapshot,
                key,
            )

        _write(
            args.output,
            json.dumps(snapshot, indent=2) + "\n",
        )

        if args.cloudwatch:
            publish_snapshot_metrics(snapshot)
            print("CloudWatch metrics published")

        print(f"Snapshot written to {args.output}")
        return 0

    if args.command == "prune":
        candidates = prune_candidates(
            args.directory,
            args.keep,
            args.max_age_days,
        )

        for path in candidates:
            print(path)

        if not args.apply:
            print(
                f"Dry run: {len(candidates)} file(s) would be removed; "
                "add --apply to delete"
            )
            return 0

        removed = apply_prune(candidates)

        print(
            f"Removed {removed} snapshot file(s)"
        )

        return 0

    baseline = _load(args.baseline)
    current = _load(args.current)

    findings = analyze(
        baseline,
        current,
    )

    diagnosis = diagnose(findings)

    if args.cloudwatch:
        findings_dicts = findings_as_dicts(findings)

        summary = build_incident_summary(
            current.get("captured_at"),
            findings_dicts,
            diagnosis_as_dict(diagnosis),
        )

        publish_incident_summary(summary)

        print("CloudWatch incident summary published")

    if args.format == "json":
        report = (
            json.dumps(
                {
                    "diagnosis": diagnosis_as_dict(diagnosis),
                    "findings": findings_as_dicts(
                        findings
                    ),
                },
                indent=2,
            )
            + "\n"
        )

    else:
        report = findings_as_markdown(
            baseline,
            current,
            findings,
        )

    if args.output:
        _write(
            args.output,
            report,
        )

        print(
            f"Report written to {args.output}"
        )

    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
