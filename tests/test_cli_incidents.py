from datetime import UTC, datetime, timedelta

from network_flight_recorder.cli import main
from network_flight_recorder.event_recorder import NetworkEvent, save_event


def test_incidents_groups_related_events(tmp_path, capsys) -> None:
    path = tmp_path / "events.jsonl"
    base_time = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)

    save_event(
        path,
        NetworkEvent(
            event_type="interface",
            source="analyzer",
            message="Interface went down",
            timestamp=base_time,
            metadata={"severity": "high"},
        ),
    )

    save_event(
        path,
        NetworkEvent(
            event_type="routing",
            source="analyzer",
            message="Default route disappeared",
            timestamp=base_time + timedelta(minutes=2),
            metadata={"severity": "critical"},
        ),
    )

    save_event(
        path,
        NetworkEvent(
            event_type="dns",
            source="analyzer",
            message="DNS failed later",
            timestamp=base_time + timedelta(minutes=20),
            metadata={"severity": "medium"},
        ),
    )

    result = main(
        [
            "incidents",
            "--log",
            str(path),
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "# Incidents" in output
    assert "Incident 1" in output
    assert "Incident 2" in output
    assert "Severity: critical" in output
    assert "Severity: medium" in output
    assert "Events: 2" in output
    assert "Events: 1" in output
    assert "interface" in output
    assert "routing" in output
    assert "dns" in output
