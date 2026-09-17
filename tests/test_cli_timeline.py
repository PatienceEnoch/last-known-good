from datetime import UTC, datetime, timedelta

from network_flight_recorder.cli import main
from network_flight_recorder.event_recorder import NetworkEvent, save_event


def test_timeline_filters_by_event_type(tmp_path, capsys) -> None:
    path = tmp_path / "events.jsonl"

    save_event(
        path,
        NetworkEvent(
            event_type="dns",
            source="analyzer",
            message="DNS configuration is empty",
            timestamp=datetime(2026, 9, 13, 12, 5, tzinfo=UTC),
        ),
    )

    save_event(
        path,
        NetworkEvent(
            event_type="routing",
            source="analyzer",
            message="Default route disappeared",
            timestamp=datetime(2026, 9, 13, 12, 6, tzinfo=UTC),
        ),
    )

    result = main(
        [
            "timeline",
            "--log",
            str(path),
            "--type",
            "dns",
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "DNS configuration is empty" in output
    assert "Default route disappeared" not in output


def test_timeline_filters_by_source(tmp_path, capsys) -> None:
    path = tmp_path / "events.jsonl"

    save_event(
        path,
        NetworkEvent(
            event_type="dns",
            source="analyzer",
            message="DNS configuration is empty",
            timestamp=datetime(2026, 9, 13, 12, 5, tzinfo=UTC),
        ),
    )

    save_event(
        path,
        NetworkEvent(
            event_type="connectivity",
            source="probe",
            message="Gateway probe failed",
            timestamp=datetime(2026, 9, 13, 12, 6, tzinfo=UTC),
        ),
    )

    result = main(
        [
            "timeline",
            "--log",
            str(path),
            "--source",
            "probe",
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "Gateway probe failed" in output
    assert "DNS configuration is empty" not in output


def test_timeline_filters_by_since(tmp_path, capsys) -> None:
    path = tmp_path / "events.jsonl"
    now = datetime.now(UTC)

    save_event(
        path,
        NetworkEvent(
            event_type="dns",
            source="analyzer",
            message="Recent DNS failure",
            timestamp=now - timedelta(minutes=30),
        ),
    )

    save_event(
        path,
        NetworkEvent(
            event_type="routing",
            source="analyzer",
            message="Old routing failure",
            timestamp=now - timedelta(hours=2),
        ),
    )

    result = main(
        [
            "timeline",
            "--log",
            str(path),
            "--since",
            "1h",
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "Recent DNS failure" in output
    assert "Old routing failure" not in output
