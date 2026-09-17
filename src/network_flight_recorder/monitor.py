"""Monitoring helpers for recording network state transitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .analyzer import Finding, analyze
from .event_recorder import findings_to_events, save_event


def record_transition(
    baseline: dict[str, Any],
    current: dict[str, Any],
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
