import json

from network_flight_recorder.cloudwatch import (
    publish_snapshot_metrics,
    snapshot_metrics,
)


def test_snapshot_metrics_counts_reachability_failures():
    snapshot = {
        "network": {
            "probes": [
                {"reachable": True},
                {"reachable": False},
                {"reachable": False},
            ]
        }
    }

    metrics = snapshot_metrics(snapshot)

    assert metrics == [
        {
            "MetricName": "SnapshotSuccess",
            "Value": 1,
            "Unit": "Count",
        },
        {
            "MetricName": "ReachabilityFailure",
            "Value": 2,
            "Unit": "Count",
        },
    ]


def test_publish_snapshot_metrics_calls_aws(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    monkeypatch.setattr(
        "network_flight_recorder.cloudwatch.subprocess.run",
        fake_run,
    )

    snapshot = {
        "network": {
            "probes": [
                {"reachable": True},
            ]
        }
    }

    publish_snapshot_metrics(snapshot)

    assert len(calls) == 1

    command, kwargs = calls[0]

    assert command[0:3] == [
        "aws",
        "cloudwatch",
        "put-metric-data",
    ]

    assert "--namespace" in command
    assert command[command.index("--namespace") + 1] == "NetworkFlightRecorder"

    metric_data_position = command.index("--metric-data") + 1
    metric_data = json.loads(command[metric_data_position])

    metric_names = {
        metric["MetricName"]
        for metric in metric_data
    }

    assert metric_names == {
        "SnapshotSuccess",
        "ReachabilityFailure",
    }

    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False
    assert kwargs["timeout"] == 15
