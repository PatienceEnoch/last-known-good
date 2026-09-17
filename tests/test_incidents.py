import json
from datetime import UTC, datetime, timedelta

from network_flight_recorder.event_recorder import NetworkEvent
from network_flight_recorder.incidents import (
    build_incident_summary,
    group_events_into_incidents,
    publish_incident_summary,
)


def test_build_incident_summary():
    findings = [
        {
            "severity": "critical",
            "category": "routing",
        },
        {
            "severity": "high",
            "category": "connectivity",
        },
        {
            "severity": "high",
            "category": "routing",
        },
    ]

    diagnosis = {
        "likely_cause": "Default gateway or routing failure",
        "confidence": "high",
    }

    summary = build_incident_summary(
        "2026-09-16T20:00:00+00:00",
        findings,
        diagnosis,
    )

    assert summary == {
        "captured_at": "2026-09-16T20:00:00+00:00",
        "likely_cause": "Default gateway or routing failure",
        "confidence": "high",
        "finding_count": 3,
        "severity_counts": {
            "critical": 1,
            "high": 2,
        },
        "categories": [
            "connectivity",
            "routing",
        ],
    }


def test_group_events_into_separate_incidents():
    base_time = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)

    events = [
        NetworkEvent(
            event_type="interface",
            source="analyzer",
            message="Interface went down",
            timestamp=base_time,
            metadata={"severity": "high"},
        ),
        NetworkEvent(
            event_type="routing",
            source="analyzer",
            message="Default route disappeared",
            timestamp=base_time + timedelta(minutes=1),
            metadata={"severity": "critical"},
        ),
        NetworkEvent(
            event_type="connectivity",
            source="analyzer",
            message="Probe failed",
            timestamp=base_time + timedelta(minutes=3),
            metadata={"severity": "high"},
        ),
        NetworkEvent(
            event_type="dns",
            source="analyzer",
            message="DNS failed later",
            timestamp=base_time + timedelta(minutes=20),
            metadata={"severity": "medium"},
        ),
    ]

    incidents = group_events_into_incidents(events)

    assert len(incidents) == 2

    first = incidents[0]

    assert first.started_at == base_time
    assert first.ended_at == base_time + timedelta(minutes=3)
    assert len(first.events) == 3
    assert first.severity == "critical"
    assert first.categories == (
        "connectivity",
        "interface",
        "routing",
    )

    second = incidents[1]

    assert second.started_at == base_time + timedelta(minutes=20)
    assert second.ended_at == base_time + timedelta(minutes=20)
    assert len(second.events) == 1
    assert second.severity == "medium"
    assert second.categories == ("dns",)


def test_publish_incident_summary_calls_aws(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    monkeypatch.setattr(
        "network_flight_recorder.incidents.subprocess.run",
        fake_run,
    )

    monkeypatch.setattr(
        "network_flight_recorder.incidents.time.time",
        lambda: 1000.0,
    )

    summary = {
        "captured_at": "2026-09-16T20:00:00+00:00",
        "likely_cause": "DNS resolution failure",
        "confidence": "high",
        "finding_count": 1,
        "severity_counts": {
            "high": 1,
        },
        "categories": [
            "dns",
        ],
    }

    publish_incident_summary(summary)

    assert len(calls) == 1

    command, kwargs = calls[0]

    assert command[0:3] == [
        "aws",
        "logs",
        "put-log-events",
    ]

    assert command[command.index("--log-group-name") + 1] == (
        "/network-flight-recorder/incidents"
    )

    assert command[command.index("--log-stream-name") + 1] == (
        "incident-summaries"
    )

    events = json.loads(
        command[command.index("--log-events") + 1]
    )

    assert events[0]["timestamp"] == 1000000

    message = json.loads(events[0]["message"])

    assert message == summary

    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False
    assert kwargs["timeout"] == 15
