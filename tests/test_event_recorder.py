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

def test_get_events_between_returns_only_matching_events() -> None:
    recorder = EventRecorder()

    base_time = datetime.now(UTC)

    before = NetworkEvent(
        event_type="before_window",
        source="router-01",
        message="Before incident window",
        timestamp=base_time - timedelta(minutes=10),
    )

    inside = NetworkEvent(
        event_type="packet_loss",
        source="router-01",
        message="Packet loss detected",
        timestamp=base_time,
    )

    after = NetworkEvent(
        event_type="after_window",
        source="router-01",
        message="After incident window",
        timestamp=base_time + timedelta(minutes=10),
    )

    recorder.record(before)
    recorder.record(inside)
    recorder.record(after)

    events = recorder.get_events_between(
        base_time - timedelta(minutes=5),
        base_time + timedelta(minutes=5),
    )

    assert events == [inside]


def test_filter_events_by_source_and_type() -> None:
    recorder = EventRecorder()

    router_failure = NetworkEvent(
        event_type="connectivity_failure",
        source="router-01",
        message="Router lost connectivity",
    )

    router_recovery = NetworkEvent(
        event_type="recovery",
        source="router-01",
        message="Router connectivity restored",
    )

    server_failure = NetworkEvent(
        event_type="connectivity_failure",
        source="web-server-01",
        message="Server health check failed",
    )

    recorder.record(router_failure)
    recorder.record(router_recovery)
    recorder.record(server_failure)

    events = recorder.filter_events(
        source="router-01",
        event_type="connectivity_failure",
    )

    assert events == [router_failure]

def test_query_events_combines_filters() -> None:
    recorder = EventRecorder()

    base_time = datetime.now(UTC)

    matching = NetworkEvent(
        event_type="connectivity_failure",
        source="router-01",
        message="Router lost connectivity",
        timestamp=base_time,
    )

    wrong_source = NetworkEvent(
        event_type="connectivity_failure",
        source="router-02",
        message="Another router failed",
        timestamp=base_time,
    )

    wrong_type = NetworkEvent(
        event_type="recovery",
        source="router-01",
        message="Router recovered",
        timestamp=base_time,
    )

    outside_window = NetworkEvent(
        event_type="connectivity_failure",
        source="router-01",
        message="Older failure",
        timestamp=base_time - timedelta(minutes=20),
    )

    recorder.record(matching)
    recorder.record(wrong_source)
    recorder.record(wrong_type)
    recorder.record(outside_window)

    events = recorder.query_events(
        start=base_time - timedelta(minutes=5),
        end=base_time + timedelta(minutes=5),
        source="router-01",
        event_type="connectivity_failure",
    )

    assert events == [matching]
