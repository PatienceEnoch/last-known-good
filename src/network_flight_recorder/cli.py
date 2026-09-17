"""Command-line interface for Network Flight Recorder."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import UTC, datetime, timedelta
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
from .event_recorder import (
    NetworkEvent,
    events_as_timeline,
    findings_to_events,
    load_events,
    save_event,
)
from .incidents import (
    build_incident_summary,
    group_events_into_incidents,
    incidents_as_markdown,
    publish_incident_summary,
)
from .privacy import redact_snapshot
from .remediation import (
    generate_remediation_plan,
    remediation_plan_as_dict,
    remediation_plan_as_markdown,
)
from .retention import apply_prune, prune_candidates


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _parse_since(value: str) -> timedelta:
    """Parse a duration such as 30m, 1h, or 2d."""
    if len(value) < 2:
        raise argparse.ArgumentTypeError(
            "Duration must look like 30m, 1h, or 2d"
        )

    unit = value[-1].lower()
    amount_text = value[:-1]

    try:
        amount = int(amount_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Duration must look like 30m, 1h, or 2d"
        ) from exc

    if amount < 0:
        raise argparse.ArgumentTypeError(
            "Duration must be zero or greater"
        )

    if unit == "m":
        return timedelta(minutes=amount)

    if unit == "h":
        return timedelta(hours=amount)

    if unit == "d":
        return timedelta(days=amount)

    raise argparse.ArgumentTypeError(
        "Duration unit must be m, h, or d"
    )


def _filter_events(
    events: list[NetworkEvent],
    *,
    event_type: str | None = None,
    source: str | None = None,
    since: timedelta | None = None,
) -> list[NetworkEvent]:
    """Return events matching the requested CLI filters."""
    filtered = events

    if event_type:
        filtered = [
            event
            for event in filtered
            if event.event_type == event_type
        ]

    if source:
        filtered = [
            event
            for event in filtered
            if event.source == source
        ]

    if since:
        cutoff = datetime.now(UTC) - since

        filtered = [
            event
            for event in filtered
            if event.timestamp >= cutoff
        ]

    return filtered


def _event_summary_as_markdown(events: list[NetworkEvent]) -> str:
    """Render a concise summary of recorded network events."""
    lines = ["# Event Summary", ""]

    lines.append(f"Total events: {len(events)}")

    if not events:
        return "\n".join(lines)

    ordered = sorted(events, key=lambda event: event.timestamp)

    lines.append(
        f"First observed: {ordered[0].timestamp.astimezone(UTC).isoformat()}"
    )
    lines.append(
        f"Last observed: {ordered[-1].timestamp.astimezone(UTC).isoformat()}"
    )

    severity_counts = Counter(
        event.metadata.get("severity", "unknown")
        for event in events
    )

    category_counts = Counter(
        event.event_type
        for event in events
    )

    lines.extend(["", "## Severity"])

    for severity, count in sorted(severity_counts.items()):
        lines.append(f"- {severity}: {count}")

    lines.extend(["", "## Categories"])

    for category, count in sorted(category_counts.items()):
        lines.append(f"- {category}: {count}")

    return "\n".join(lines)


def _add_event_filter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--type",
        dest="event_type",
        help="Show only events of this type",
    )

    parser.add_argument(
        "--source",
        help="Show only events from this source",
    )

    parser.add_argument(
        "--since",
        type=_parse_since,
        metavar="DURATION",
        help="Show events from a recent duration such as 30m, 1h, or 2d",
    )


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

    compare.add_argument(
        "--remediation-plan",
        action="store_true",
        help="Generate an approval-required remediation plan",
    )

    timeline = commands.add_parser(
        "timeline",
        help="Show recorded network events in chronological order",
    )

    timeline.add_argument(
        "--log",
        type=Path,
        default=Path("events/events.jsonl"),
        help="Path to the JSONL event log",
    )

    _add_event_filter_arguments(timeline)

    timeline.add_argument(
        "--output",
        type=Path,
        help="Optional file to write the timeline to",
    )

    summary = commands.add_parser(
        "summary",
        help="Summarize recorded network events",
    )

    summary.add_argument(
        "--log",
        type=Path,
        default=Path("events/events.jsonl"),
        help="Path to the JSONL event log",
    )

    _add_event_filter_arguments(summary)

    summary.add_argument(
        "--output",
        type=Path,
        help="Optional file to write the summary to",
    )

    incidents = commands.add_parser(
        "incidents",
        help="Group related network events into incidents",
    )

    incidents.add_argument(
        "--log",
        type=Path,
        default=Path("events/events.jsonl"),
        help="Path to the JSONL event log",
    )

    _add_event_filter_arguments(incidents)

    incidents.add_argument(
        "--output",
        type=Path,
        help="Optional file to write the incident report to",
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

    if args.command == "timeline":
        events = _filter_events(
            load_events(args.log),
            event_type=args.event_type,
            source=args.source,
            since=args.since,
        )

        report = events_as_timeline(events)

        if args.output:
            _write(
                args.output,
                report + "\n",
            )
            print(f"Timeline written to {args.output}")
        else:
            print(report)

        return 0

    if args.command == "summary":
        events = _filter_events(
            load_events(args.log),
            event_type=args.event_type,
            source=args.source,
            since=args.since,
        )

        report = _event_summary_as_markdown(events)

        if args.output:
            _write(
                args.output,
                report + "\n",
            )
            print(f"Summary written to {args.output}")
        else:
            print(report)

        return 0

    if args.command == "incidents":
        events = _filter_events(
            load_events(args.log),
            event_type=args.event_type,
            source=args.source,
            since=args.since,
        )

        incidents = group_events_into_incidents(events)
        report = incidents_as_markdown(incidents)

        if args.output:
            _write(
                args.output,
                report + "\n",
            )
            print(f"Incident report written to {args.output}")
        else:
            print(report)

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

    events = findings_to_events(
        findings,
        current["captured_at"],
    )

    for event in events:
        save_event(
            Path("events/events.jsonl"),
            event,
        )

    diagnosis = diagnose(findings)

    remediation_plan = None

    if args.remediation_plan:
        remediation_plan = generate_remediation_plan(
            diagnosis
        )

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
        payload = {
            "diagnosis": diagnosis_as_dict(diagnosis),
            "findings": findings_as_dicts(findings),
        }

        if args.remediation_plan:
            payload["remediation_plan"] = remediation_plan_as_dict(
                remediation_plan
            )

        report = (
            json.dumps(
                payload,
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

        if args.remediation_plan:
            report += "\n" + remediation_plan_as_markdown(
                remediation_plan
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
