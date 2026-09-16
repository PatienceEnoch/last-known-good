from datetime import UTC, datetime, timedelta

from network_flight_recorder.event_recorder import EventRecorder, NetworkEvent


def test_record_event() -> None:
    recorder = EventRecorder()

    event = NetworkEvent(
        event_type="connectivity_failure",
        source="web-server-01",
        message="Health check failed",
    )

    recorder.record(event)

    assert recorder.get_events() == [event]


def test_events_are_returned_in_chronological_order() -> None:
    recorder = EventRecorder()

    later = NetworkEvent(
        event_type="recovery",
        source="web-server-01",
        message="Health check recovered",
        timestamp=datetime.now(UTC),
    )

    earlier = NetworkEvent(
        event_type="connectivity_failure",
        source="web-server-01",
        message="Health check failed",
        timestamp=later.timestamp - timedelta(minutes=5),
    )

    recorder.record(later)
    recorder.record(earlier)

    assert recorder.get_events() == [earlier, later]
