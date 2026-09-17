"""Incident grouping and CloudWatch incident summaries."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .event_recorder import NetworkEvent

LOG_GROUP = "/network-flight-recorder/incidents"
LOG_STREAM = "incident-summaries"

SEVERITY_RANK = {
    "unknown": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass(frozen=True, slots=True)
class Incident:
    """A group of related network events close together in time."""

    started_at: datetime
    ended_at: datetime
    severity: str
    categories: tuple[str, ...]
    events: tuple[NetworkEvent, ...]


def _incident_from_events(events: list[NetworkEvent]) -> Incident:
    """Build one incident from a non-empty collection of events."""
    ordered = sorted(events, key=lambda event: event.timestamp)

    severity = max(
        (
            event.metadata.get("severity", "unknown")
            for event in ordered
        ),
        key=lambda value: SEVERITY_RANK.get(value, 0),
    )

    categories = tuple(
        sorted(
            {
                event.event_type
                for event in ordered
            }
        )
    )

    return Incident(
        started_at=ordered[0].timestamp,
        ended_at=ordered[-1].timestamp,
        severity=severity,
        categories=categories,
        events=tuple(ordered),
    )


def group_events_into_incidents(
    events: list[NetworkEvent],
    gap: timedelta = timedelta(minutes=5),
) -> list[Incident]:
    """Group events into incidents based on the gap between observations."""
    if not events:
        return []

    ordered = sorted(events, key=lambda event: event.timestamp)

    incidents: list[Incident] = []
    current_group = [ordered[0]]

    for event in ordered[1:]:
        previous = current_group[-1]

        if event.timestamp - previous.timestamp <= gap:
            current_group.append(event)
            continue

        incidents.append(
            _incident_from_events(current_group)
        )
        current_group = [event]

    incidents.append(
        _incident_from_events(current_group)
    )

    return incidents


def incidents_as_markdown(incidents: list[Incident]) -> str:
    """Render grouped incidents as a readable report."""
    lines = ["# Incidents", ""]

    if not incidents:
        lines.append("No incidents found.")
        return "\n".join(lines)

    for number, incident in enumerate(incidents, start=1):
        lines.extend(
            [
                f"## Incident {number}",
                "",
                (
                    "Started: "
                    f"{incident.started_at.astimezone(UTC).isoformat()}"
                ),
                (
                    "Ended: "
                    f"{incident.ended_at.astimezone(UTC).isoformat()}"
                ),
                f"Severity: {incident.severity}",
                f"Events: {len(incident.events)}",
                f"Categories: {', '.join(incident.categories)}",
                "",
            ]
        )

    return "\n".join(lines).rstrip()


def build_incident_summary(
    captured_at: str | None,
    findings: list[dict[str, Any]],
    diagnosis: dict[str, Any] | None,
) -> dict[str, Any]:
    severity_counts: dict[str, int] = {}

    for finding in findings:
        severity = finding.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    categories = sorted(
        {
            finding.get("category", "unknown")
            for finding in findings
        }
    )

    return {
        "captured_at": captured_at or "unknown",
        "likely_cause": diagnosis.get("likely_cause") if diagnosis else None,
        "confidence": diagnosis.get("confidence") if diagnosis else None,
        "finding_count": len(findings),
        "severity_counts": severity_counts,
        "categories": categories,
    }


def publish_incident_summary(
    summary: dict[str, Any],
    region: str = "us-east-1",
) -> None:
    log_event = [
        {
            "timestamp": int(time.time() * 1000),
            "message": json.dumps(summary, sort_keys=True),
        }
    ]

    result = subprocess.run(
        [
            "aws",
            "logs",
            "put-log-events",
            "--log-group-name",
            LOG_GROUP,
            "--log-stream-name",
            LOG_STREAM,
            "--log-events",
            json.dumps(log_event),
            "--region",
            region,
            "--no-cli-pager",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"CloudWatch incident publishing failed: {result.stderr.strip()}"
        )
