"""Timestamped event recording for Network Flight Recorder."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .analyzer import Finding


@dataclass(frozen=True, slots=True)
class NetworkEvent:
    """A single timestamped event observed by the recorder."""

    event_type: str
    source: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

class EventRecorder:
    """Stores network events in the order they were recorded."""

    def __init__(self) -> None:
        self._events: list[NetworkEvent] = []

    def record(self, event: NetworkEvent) -> None:
        """Record a new network event."""
        self._events.append(event)

    def get_events(self) -> list[NetworkEvent]:
        """Return all recorded events in chronological order."""
        return sorted(self._events, key=lambda event: event.timestamp)


    def get_events_between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[NetworkEvent]:
        """Return events that occurred between two timestamps."""
        return [
            event
            for event in self.get_events()
            if start <= event.timestamp <= end
        ]


    def filter_events(
        self,
        *,
        source: str | None = None,
        event_type: str | None = None,
    ) -> list[NetworkEvent]:
        """Return events matching the requested source and event type."""
        events = self.get_events()

        if source is not None:
            events = [event for event in events if event.source == source]

        if event_type is not None:
            events = [
                event for event in events if event.event_type == event_type
            ]

        return events

    def query_events(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        source: str | None = None,
        event_type: str | None = None,
    ) -> list[NetworkEvent]:
        """Return events matching the requested incident criteria."""
        events = self.get_events()

        if start is not None:
            events = [event for event in events if event.timestamp >= start]

        if end is not None:
            events = [event for event in events if event.timestamp <= end]

        if source is not None:
            events = [event for event in events if event.source == source]

        if event_type is not None:
            events = [
                event for event in events if event.event_type == event_type
            ]

        return events


def events_as_timeline(events: list[NetworkEvent]) -> str:
    """Render recorded events as a chronological incident timeline."""
    if not events:
        return "No recorded events."

    lines = ["## Event timeline", ""]

    for event in sorted(events, key=lambda item: item.timestamp):
        timestamp = event.timestamp.astimezone(UTC).isoformat()

        lines.append(
            f"- `{timestamp}` **{event.source}** "
            f"[{event.event_type}] — {event.message}"
        )

    return "\n".join(lines)

def findings_to_events(
    findings: list[Finding],
    captured_at: str,
) -> list[NetworkEvent]:
    """Convert analyzer findings into timestamped network events."""
    timestamp = datetime.fromisoformat(captured_at)

    return [
        NetworkEvent(
            event_type=finding.category,
            source="analyzer",
            message=finding.title,
            timestamp=timestamp,
            metadata={
                "severity": finding.severity,
                "evidence": finding.evidence,
                "recommendation": finding.recommendation,
            },
        )
        for finding in findings
    ]
