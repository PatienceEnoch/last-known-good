import json
from pathlib import Path

from network_flight_recorder.analyzer import analyze, diagnose, findings_as_markdown

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


def test_detects_address_mtu_latency_and_packet_loss_changes():
    baseline = load("healthy.json")
    current = json.loads(json.dumps(baseline))
    baseline_interface = baseline["network"]["interfaces"][0]
    current_interface = current["network"]["interfaces"][0]
    baseline_interface["mtu"] = 1500
    current_interface["mtu"] = 1400
    current_interface["addresses"] = [
        {"family": "inet", "local": "192.0.2.25", "prefixlen": 24}
    ]
    baseline_probe = baseline["network"]["probes"][0]
    current_probe = current["network"]["probes"][0]
    baseline_probe["packet_loss_percent"] = 0.0
    current_probe["packet_loss_percent"] = 33.0
    baseline_probe["average_latency_ms"] = 10.0
    current_probe["average_latency_ms"] = 50.0

    titles = {finding.title for finding in analyze(baseline, current)}
    assert "Interface eth0 MTU changed" in titles
    assert "Interface eth0 addressing changed" in titles
    assert "Packet loss to 1.1.1.1 increased" in titles
    assert "Latency to 1.1.1.1 increased" in titles


def test_detects_dns_failure_and_slow_response():
    baseline = load("healthy.json")
    baseline["network"]["dns_probes"] = [
        {
            "name": "example.com",
            "resolved": True,
            "response_time_ms": 20.0,
            "addresses": ["192.0.2.10"],
            "error": None,
        },
        {
            "name": "example.net",
            "resolved": True,
            "response_time_ms": 25.0,
            "addresses": ["192.0.2.20"],
            "error": None,
        },
    ]
    current = json.loads(json.dumps(baseline))
    current["network"]["dns_probes"][0].update(
        {"resolved": False, "response_time_ms": 15.0, "addresses": [], "error": "name not known"}
    )
    current["network"]["dns_probes"][1]["response_time_ms"] = 150.0

    titles = {finding.title for finding in analyze(baseline, current)}
    assert "DNS lookup for example.com failed" in titles
    assert "DNS lookup for example.net slowed" in titles


def test_correlates_interface_failure_as_likely_root_cause():
    diagnosis = diagnose(analyze(load("healthy.json"), load("broken.json")))
    assert diagnosis is not None
    assert diagnosis.likely_cause == "Local interface or link failure"
    assert diagnosis.confidence == "high"
    assert "Interface eth0 is no longer up" in diagnosis.supporting_findings
    assert "Default route disappeared" in diagnosis.supporting_findings


def test_correlates_dns_failure_when_ip_connectivity_remains_healthy():
    baseline = load("healthy.json")
    current = json.loads(json.dumps(baseline))
    baseline["network"]["dns_probes"] = [
        {"name": "example.com", "resolved": True, "response_time_ms": 10.0}
    ]
    current["network"]["dns_probes"] = [
        {"name": "example.com", "resolved": False, "response_time_ms": 10.0, "error": "failed"}
    ]
    diagnosis = diagnose(analyze(baseline, current))
    assert diagnosis is not None
    assert diagnosis.likely_cause == "DNS resolution failure"


def test_report_places_correlated_diagnosis_before_individual_findings():
    baseline = load("healthy.json")
    current = load("broken.json")
    report = findings_as_markdown(baseline, current, analyze(baseline, current))
    assert "## Likely root cause" in report
    assert report.index("## Likely root cause") < report.index("## 1.")


def test_detects_network_recovery() -> None:
    findings = analyze(
        load("broken.json"),
        load("healthy.json"),
    )

    titles = {finding.title for finding in findings}

    assert "Default route restored" in titles
    assert "DNS configuration restored" in titles
    assert "Interface eth0 is back up" in titles
    assert "Probe to 1.1.1.1 recovered" in titles
    assert "Service recovered: systemd-networkd.service" in titles

    recovery_findings = [
        finding
        for finding in findings
        if finding.title in titles
    ]

    assert all(
        finding.severity == "info"
        for finding in recovery_findings
    )
