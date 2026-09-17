import json
from pathlib import Path

from network_flight_recorder.event_recorder import load_events
from network_flight_recorder.monitor import record_transition

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
