from pathlib import Path

from network_flight_recorder.cli import main


def test_watch_command_starts_monitoring(monkeypatch, tmp_path, capsys) -> None:
    calls = []

    def fake_watch_network(**kwargs):
        calls.append(kwargs)
        return 2

    monkeypatch.setattr(
        "network_flight_recorder.cli.watch_network",
        fake_watch_network,
    )

    event_log = tmp_path / "events.jsonl"

    result = main(
        [
            "watch",
            "--interval",
            "15",
            "--cycles",
            "2",
            "--probe",
            "1.1.1.1",
            "--dns",
            "example.com",
            "--log",
            str(event_log),
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert len(calls) == 1

    assert calls[0] == {
        "interval_seconds": 15.0,
        "event_log": Path(event_log),
        "probe_hosts": ["1.1.1.1"],
        "dns_names": ["example.com"],
        "cycles": 2,
    }

    assert "Watch completed: 2 cycle(s)" in output
