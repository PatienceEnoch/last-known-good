"""Monitoring helpers for recording network state transitions."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .analyzer import Finding, analyze
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


def watch_network(
    *,
    interval_seconds: float,
    event_log: Path,
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

    completed = 0

    while cycles is None or completed < cycles:
        sleeper(interval_seconds)

        current = collector(
            probe_hosts,
            dns_names,
        )

        findings = record_transition(
            previous,
            current,
            event_log,
        )

        completed += 1

        if reporter is not None:
            reporter(
                completed,
                len(findings),
            )

        previous = current

    return completed
