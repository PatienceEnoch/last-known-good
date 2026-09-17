import json
from pathlib import Path

from network_flight_recorder.event_recorder import load_events
from network_flight_recorder.monitor import record_transition, watch_network

FIXTURES = Path("tests/fixtures")


def test_record_transition_analyzes_and_records_events(tmp_path) -> None:
    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    current = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )

    event_log = tmp_path / "events.jsonl"

    findings = record_transition(
        baseline,
        current,
        event_log,
    )

    events = load_events(event_log)

    assert len(findings) == 5
    assert len(events) == 5

    assert {
        event.event_type
        for event in events
    } == {
        "routing",
        "dns",
        "interface",
        "connectivity",
        "service",
    }


def test_watch_network_collects_and_records_transitions(tmp_path) -> None:
    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    current = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )

    snapshots = iter([baseline, current])
    sleeps = []

    def fake_collector(probe_hosts, dns_names):
        return next(snapshots)

    def fake_sleep(seconds):
        sleeps.append(seconds)

    event_log = tmp_path / "events.jsonl"

    completed = watch_network(
        interval_seconds=10,
        event_log=event_log,
        cycles=1,
        collector=fake_collector,
        sleeper=fake_sleep,
    )

    events = load_events(event_log)

    assert completed == 1
    assert sleeps == [10]
    assert len(events) == 5


def test_watch_network_reports_each_cycle(tmp_path) -> None:
    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    current = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )

    snapshots = iter([baseline, current])
    reports = []

    def fake_collector(probe_hosts, dns_names):
        return next(snapshots)

    def fake_sleep(seconds):
        pass

    def reporter(cycle, finding_count):
        reports.append((cycle, finding_count))

    watch_network(
        interval_seconds=1,
        event_log=tmp_path / "events.jsonl",
        cycles=1,
        collector=fake_collector,
        sleeper=fake_sleep,
        reporter=reporter,
    )

    assert reports == [(1, 5)]
