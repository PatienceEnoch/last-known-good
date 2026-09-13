import json
from pathlib import Path

from network_flight_recorder.analyzer import analyze, findings_as_markdown

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_detects_multiple_correlated_failures():
    findings = analyze(load("healthy.json"), load("broken.json"))
    titles = {finding.title for finding in findings}
    assert "Default route disappeared" in titles
    assert "DNS configuration is empty" in titles
    assert "Interface eth0 is no longer up" in titles
    assert "Probe to 1.1.1.1 failed" in titles
    assert "Service failure detected: systemd-networkd.service" in titles


def test_identical_snapshots_have_no_findings():
    healthy = load("healthy.json")
    assert analyze(healthy, healthy) == []


def test_markdown_report_contains_evidence_and_recommendation():
    baseline = load("healthy.json")
    current = load("broken.json")
    report = findings_as_markdown(baseline, current, analyze(baseline, current))
    assert "# Network Incident Report" in report
    assert "**Evidence:**" in report
    assert "**Recommended verification:**" in report

