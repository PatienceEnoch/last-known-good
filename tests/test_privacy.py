import json

from network_flight_recorder.privacy import redact_snapshot


def test_redaction_removes_sensitive_values_and_is_stable():
    snapshot = {
        "host": {"hostname": "private-laptop"},
        "network": {
            "dns_servers": ["192.168.1.1"],
            "interfaces": [{"addresses": [{"local": "192.168.1.20"}]}],
            "routes": [{"gateway": "192.168.1.1", "prefsrc": "192.168.1.20"}],
            "probes": [{"host": "1.1.1.1"}],
            "dns_probes": [
                {"name": "example.com", "addresses": ["93.184.216.34"], "error": None}
            ],
        },
    }
    first = redact_snapshot(snapshot, "test-key")
    second = redact_snapshot(snapshot, "test-key")
    rendered = json.dumps(first)

    assert first == second
    for sensitive in ("private-laptop", "192.168.1.1", "192.168.1.20", "1.1.1.1", "example.com"):
        assert sensitive not in rendered
    assert snapshot["host"]["hostname"] == "private-laptop"
