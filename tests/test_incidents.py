import json

from network_flight_recorder.incidents import (
    build_incident_summary,
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
