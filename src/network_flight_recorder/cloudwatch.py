"""Publish privacy-preserving Network Flight Recorder metrics to CloudWatch."""

from __future__ import annotations

import json
import subprocess
from typing import Any

NAMESPACE = "NetworkFlightRecorder"


def snapshot_metrics(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    probes = snapshot.get("network", {}).get("probes", [])

    reachability_failures = sum(
        1 for probe in probes if not probe.get("reachable", False)
    )

    return [
        {
            "MetricName": "SnapshotSuccess",
            "Value": 1,
            "Unit": "Count",
        },
        {
            "MetricName": "ReachabilityFailure",
            "Value": reachability_failures,
            "Unit": "Count",
        },
    ]


def publish_snapshot_metrics(
    snapshot: dict[str, Any],
    region: str = "us-east-1",
) -> None:
    metric_data = snapshot_metrics(snapshot)

    result = subprocess.run(
        [
            "aws",
            "cloudwatch",
            "put-metric-data",
            "--namespace",
            NAMESPACE,
            "--metric-data",
            json.dumps(metric_data),
            "--region",
            region,
            "--no-cli-pager",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"CloudWatch metric publishing failed: {result.stderr.strip()}"
        )
