"""Monitoring helpers for recording network state transitions."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .analyzer import Finding, analyze, findings_as_markdown
from .collector import collect_snapshot
from .event_recorder import findings_to_events, save_event

Snapshot = dict[str, Any]
Collector = Callable[[list[str], list[str]], Snapshot]
Sleeper = Callable[[float], None]
Reporter = Callable[[int, int], None]


def record_transition(
    baseline: Snapshot,
    current: Snapshot,
    event_log: Path,
) -> list[Finding]:
    """Analyze one snapshot transition and record resulting events."""
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
            event_log,
            event,
        )

    return findings


def _enforce_snapshot_limit(
    snapshot_dir: Path,
    snapshot_limit: int | None,
) -> None:
    """Keep only the newest snapshot files when a limit is configured."""
    if snapshot_limit is None:
        return

    files = sorted(snapshot_dir.glob("*.json"))

    while len(files) > snapshot_limit:
        files[0].unlink()
        files.pop(0)



def watch_network(
    *,
    interval_seconds: float,
    event_log: Path,
    snapshot_dir: Path | None = None,
    snapshot_limit: int | None = None,
    probe_hosts: list[str] | None = None,
    dns_names: list[str] | None = None,
    cycles: int | None = None,
    collector: Collector = collect_snapshot,
    sleeper: Sleeper = time.sleep,
    reporter: Reporter | None = None,
) -> int:
    """Continuously capture network state and record detected transitions."""
    probe_hosts = probe_hosts or []
    dns_names = dns_names or []

    previous = collector(
        probe_hosts,
        dns_names,
    )

    if snapshot_dir is not None:
        snapshot_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        (
            snapshot_dir / "0000-baseline.json"
        ).write_text(
            json.dumps(
                previous,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        _enforce_snapshot_limit(
            snapshot_dir,
            snapshot_limit,
        )

    completed = 0
    open_incident_dir: Path | None = None

    while cycles is None or completed < cycles:
        sleeper(interval_seconds)

        current = collector(
            probe_hosts,
            dns_names,
        )

        if snapshot_dir is not None:
            (
                snapshot_dir / f"{completed + 1:04d}.json"
            ).write_text(
                json.dumps(
                    current,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            _enforce_snapshot_limit(
                snapshot_dir,
                snapshot_limit,
            )

        findings = record_transition(
            previous,
            current,
            event_log,
        )

        completed += 1

        if findings and snapshot_dir is not None:
            is_recovery = all(
                finding.severity == "info"
                for finding in findings
            )

            if is_recovery and open_incident_dir is not None:
                (
                    open_incident_dir / "recovery.json"
                ).write_text(
                    json.dumps(
                        current,
                        indent=2,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )

                (
                    open_incident_dir / "recovery.md"
                ).write_text(
                    findings_as_markdown(
                        previous,
                        current,
                        findings,
                    ),
                    encoding="utf-8",
                )

                open_incident_dir = None

            else:
                incident_dir = (
                    snapshot_dir
                    / "incidents"
                    / f"cycle-{completed:04d}"
                )

                incident_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                (incident_dir / "before.json").write_text(
                    json.dumps(
                        previous,
                        indent=2,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )

                (incident_dir / "after.json").write_text(
                    json.dumps(
                        current,
                        indent=2,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )

                (incident_dir / "report.md").write_text(
                    findings_as_markdown(
                        previous,
                        current,
                        findings,
                    ),
                    encoding="utf-8",
                )

                if not is_recovery:
                    open_incident_dir = incident_dir

        if reporter is not None:
            reporter(
                completed,
                len(findings),
            )

        previous = current

    return completed
