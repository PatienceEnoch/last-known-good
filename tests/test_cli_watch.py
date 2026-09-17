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

    call = calls[0]

    assert call["interval_seconds"] == 15.0
    assert call["event_log"] == Path(event_log)
    assert call["probe_hosts"] == ["1.1.1.1"]
    assert call["dns_names"] == ["example.com"]
    assert call["cycles"] == 2
    assert callable(call["reporter"])

    assert "Watch completed: 2 cycle(s)" in output


def test_watch_command_reports_cycle_status(monkeypatch, tmp_path, capsys) -> None:
    def fake_watch_network(**kwargs):
        reporter = kwargs["reporter"]

        reporter(1, 0)
        reporter(2, 3)

        return 2

    monkeypatch.setattr(
        "network_flight_recorder.cli.watch_network",
        fake_watch_network,
    )

    result = main(
        [
            "watch",
            "--cycles",
            "2",
            "--log",
            str(tmp_path / "events.jsonl"),
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "Cycle 1: no changes" in output
    assert "Cycle 2: 3 finding(s) recorded" in output
    assert "Watch completed: 2 cycle(s)" in output


def test_watch_command_stops_cleanly_on_keyboard_interrupt(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    def fake_watch_network(**kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "network_flight_recorder.cli.watch_network",
        fake_watch_network,
    )

    result = main(
        [
            "watch",
            "--log",
            str(tmp_path / "events.jsonl"),
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "Watch stopped." in output


def test_watch_rejects_nonpositive_interval(tmp_path) -> None:
    try:
        main(
            [
                "watch",
                "--interval",
                "0",
                "--log",
                str(tmp_path / "events.jsonl"),
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("Expected invalid interval to exit")


def test_watch_rejects_nonpositive_cycles(tmp_path) -> None:
    try:
        main(
            [
                "watch",
                "--cycles",
                "0",
                "--log",
                str(tmp_path / "events.jsonl"),
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("Expected invalid cycles to exit")


def test_watch_command_passes_snapshot_directory(
    monkeypatch,
    tmp_path,
) -> None:
    calls = []

    def fake_watch_network(**kwargs):
        calls.append(kwargs)
        return 1

    monkeypatch.setattr(
        "network_flight_recorder.cli.watch_network",
        fake_watch_network,
    )

    snapshot_dir = tmp_path / "snapshots"

    result = main(
        [
            "watch",
            "--cycles",
            "1",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )

    assert result == 0
    assert calls[0]["snapshot_dir"] == snapshot_dir
