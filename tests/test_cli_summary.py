from datetime import UTC, datetime, timedelta

from network_flight_recorder.cli import main
from network_flight_recorder.event_recorder import NetworkEvent, save_event


def test_summary_reports_event_log_statistics(tmp_path, capsys) -> None:
    path = tmp_path / "events.jsonl"
    base_time = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)

    save_event(
        path,
        NetworkEvent(
            event_type="dns",
            source="analyzer",
            message="DNS configuration is empty",
            timestamp=base_time,
            metadata={"severity": "critical"},
        ),
    )

    save_event(
        path,
        NetworkEvent(
            event_type="routing",
            source="analyzer",
            message="Default route disappeared",
            timestamp=base_time + timedelta(minutes=2),
            metadata={"severity": "high"},
        ),
    )

    save_event(
        path,
        NetworkEvent(
            event_type="connectivity",
            source="analyzer",
            message="Probe failed",
            timestamp=base_time + timedelta(minutes=5),
            metadata={"severity": "high"},
        ),
    )

    result = main(
        [
            "summary",
            "--log",
            str(path),
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "# Event Summary" in output
    assert "Total events: 3" in output
    assert "critical: 1" in output
    assert "high: 2" in output
    assert "dns: 1" in output
    assert "routing: 1" in output
    assert "connectivity: 1" in output
    assert "2026-09-17T12:00:00+00:00" in output
    assert "2026-09-17T12:05:00+00:00" in output
