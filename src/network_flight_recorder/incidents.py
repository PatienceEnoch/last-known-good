"""Publish privacy-preserving incident summaries to CloudWatch Logs."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any


LOG_GROUP = "/network-flight-recorder/incidents"
LOG_STREAM = "incident-summaries"


def build_incident_summary(
    captured_at: str | None,
    findings: list[dict[str, Any]],
    diagnosis: dict[str, Any] | None,
) -> dict[str, Any]:
    severity_counts: dict[str, int] = {}

    for finding in findings:
        severity = finding.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    categories = sorted(
        {
            finding.get("category", "unknown")
            for finding in findings
        }
    )

    return {
        "captured_at": captured_at or "unknown",
        "likely_cause": diagnosis.get("likely_cause") if diagnosis else None,
        "confidence": diagnosis.get("confidence") if diagnosis else None,
        "finding_count": len(findings),
        "severity_counts": severity_counts,
        "categories": categories,
    }


def publish_incident_summary(
    summary: dict[str, Any],
    region: str = "us-east-1",
) -> None:
    log_event = [
        {
            "timestamp": int(time.time() * 1000),
            "message": json.dumps(summary, sort_keys=True),
        }
    ]

    result = subprocess.run(
        [
            "aws",
            "logs",
            "put-log-events",
            "--log-group-name",
            LOG_GROUP,
            "--log-stream-name",
            LOG_STREAM,
            "--log-events",
            json.dumps(log_event),
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
            f"CloudWatch incident publishing failed: {result.stderr.strip()}"
        )
