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


def test_watch_network_preserves_snapshot_history(tmp_path) -> None:
    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    current = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )

    snapshots = iter([baseline, current])

    def fake_collector(probe_hosts, dns_names):
        return next(snapshots)

    def fake_sleep(seconds):
        pass

    snapshot_dir = tmp_path / "snapshots"

    watch_network(
        interval_seconds=1,
        event_log=tmp_path / "events.jsonl",
        snapshot_dir=snapshot_dir,
        cycles=1,
        collector=fake_collector,
        sleeper=fake_sleep,
    )

    files = sorted(snapshot_dir.glob("*.json"))

    assert [path.name for path in files] == [
        "0000-baseline.json",
        "0001.json",
    ]

    assert json.loads(
        files[0].read_text(encoding="utf-8")
    ) == baseline

    assert json.loads(
        files[1].read_text(encoding="utf-8")
    ) == current


def test_watch_network_limits_snapshot_history(tmp_path) -> None:
    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )

    snapshots = iter(
        [
            baseline,
            json.loads(json.dumps(baseline)),
            json.loads(json.dumps(baseline)),
            json.loads(json.dumps(baseline)),
        ]
    )

    def fake_collector(probe_hosts, dns_names):
        return next(snapshots)

    def fake_sleep(seconds):
        pass

    snapshot_dir = tmp_path / "snapshots"

    watch_network(
        interval_seconds=1,
        event_log=tmp_path / "events.jsonl",
        snapshot_dir=snapshot_dir,
        snapshot_limit=3,
        cycles=3,
        collector=fake_collector,
        sleeper=fake_sleep,
    )

    files = sorted(snapshot_dir.glob("*.json"))

    assert [path.name for path in files] == [
        "0001.json",
        "0002.json",
        "0003.json",
    ]


def test_watch_network_preserves_incident_evidence(tmp_path) -> None:
    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    current = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )

    snapshots = iter([baseline, current])

    def fake_collector(probe_hosts, dns_names):
        return next(snapshots)

    def fake_sleep(seconds):
        pass

    snapshot_dir = tmp_path / "snapshots"

    watch_network(
        interval_seconds=1,
        event_log=tmp_path / "events.jsonl",
        snapshot_dir=snapshot_dir,
        snapshot_limit=1,
        cycles=1,
        collector=fake_collector,
        sleeper=fake_sleep,
    )

    incident_dir = snapshot_dir / "incidents" / "cycle-0001"

    before = incident_dir / "before.json"
    after = incident_dir / "after.json"

    assert before.exists()
    assert after.exists()

    assert json.loads(
        before.read_text(encoding="utf-8")
    ) == baseline

    assert json.loads(
        after.read_text(encoding="utf-8")
    ) == current


def test_watch_network_writes_incident_report(tmp_path) -> None:
    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    current = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )

    snapshots = iter([baseline, current])

    def fake_collector(probe_hosts, dns_names):
        return next(snapshots)

    def fake_sleep(seconds):
        pass

    snapshot_dir = tmp_path / "snapshots"

    watch_network(
        interval_seconds=1,
        event_log=tmp_path / "events.jsonl",
        snapshot_dir=snapshot_dir,
        cycles=1,
        collector=fake_collector,
        sleeper=fake_sleep,
    )

    report = (
        snapshot_dir
        / "incidents"
        / "cycle-0001"
        / "report.md"
    )

    assert report.exists()

    content = report.read_text(encoding="utf-8")

    assert "# Network Incident Report" in content
    assert "Default route disappeared" in content
    assert "Probe to 1.1.1.1 failed" in content


def test_watch_network_links_recovery_to_open_incident(tmp_path) -> None:
    healthy = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    broken = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )
    recovered = json.loads(json.dumps(healthy))
    recovered["captured_at"] = "2026-09-13T12:10:00+00:00"

    snapshots = iter(
        [
            healthy,
            broken,
            recovered,
        ]
    )

    def fake_collector(probe_hosts, dns_names):
        return next(snapshots)

    def fake_sleep(seconds):
        pass

    snapshot_dir = tmp_path / "snapshots"

    watch_network(
        interval_seconds=1,
        event_log=tmp_path / "events.jsonl",
        snapshot_dir=snapshot_dir,
        cycles=2,
        collector=fake_collector,
        sleeper=fake_sleep,
    )

    incidents_dir = snapshot_dir / "incidents"

    incident_dirs = sorted(
        path
        for path in incidents_dir.iterdir()
        if path.is_dir()
    )

    assert [path.name for path in incident_dirs] == [
        "cycle-0001",
    ]

    incident_dir = incident_dirs[0]

    recovery = incident_dir / "recovery.json"
    recovery_report = incident_dir / "recovery.md"

    assert recovery.exists()
    assert recovery_report.exists()

    assert json.loads(
        recovery.read_text(encoding="utf-8")
    ) == recovered

    report = recovery_report.read_text(encoding="utf-8")

    assert "Default route restored" in report
    assert "Probe to 1.1.1.1 recovered" in report
