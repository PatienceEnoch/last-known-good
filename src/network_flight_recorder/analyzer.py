"""Compare network snapshots and produce explainable findings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Finding:
    severity: str
    category: str
    title: str
    evidence: str
    recommendation: str


def _default_route(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    routes = snapshot.get("network", {}).get("routes", [])
    return next((route for route in routes if route.get("dst") == "default"), None)


def _interfaces(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = snapshot.get("network", {}).get("interfaces", [])
    return {item.get("name", "unknown"): item for item in items}


def analyze(baseline: dict[str, Any], current: dict[str, Any]) -> list[Finding]:
    """Identify high-signal changes between a known-good and current snapshot."""
    findings: list[Finding] = []
    old_default = _default_route(baseline)
    new_default = _default_route(current)

    if old_default and not new_default:
        findings.append(
            Finding(
                "critical",
                "routing",
                "Default route disappeared",
                f"Baseline used {old_default.get('gateway', 'an on-link route')} via "
                f"{old_default.get('dev', 'unknown')}; the current snapshot has no default route.",
                "Restore the expected gateway or renew the interface's DHCP lease, then retest connectivity.",
            )
        )
    elif old_default and new_default and (
        old_default.get("gateway"), old_default.get("dev")
    ) != (new_default.get("gateway"), new_default.get("dev")):
        findings.append(
            Finding(
                "high",
                "routing",
                "Default route changed",
                f"Gateway/interface changed from {old_default.get('gateway')} via "
                f"{old_default.get('dev')} to {new_default.get('gateway')} via {new_default.get('dev')}.",
                "Confirm that the new gateway and interface are authorized and expected.",
            )
        )

    old_dns = baseline.get("network", {}).get("dns_servers", [])
    new_dns = current.get("network", {}).get("dns_servers", [])
    if old_dns and not new_dns:
        findings.append(
            Finding(
                "critical",
                "dns",
                "DNS configuration is empty",
                f"Baseline resolvers were {', '.join(old_dns)}; no current resolver was found.",
                "Restore an approved resolver and test name resolution separately from IP connectivity.",
            )
        )
    elif old_dns != new_dns:
        findings.append(
            Finding(
                "medium",
                "dns",
                "DNS resolver changed",
                f"Resolvers changed from {old_dns or 'none'} to {new_dns or 'none'}.",
                "Verify the resolver source, DHCP settings, and whether the change was authorized.",
            )
        )

    old_interfaces = _interfaces(baseline)
    new_interfaces = _interfaces(current)
    for name, old in old_interfaces.items():
        new = new_interfaces.get(name)
        if new is None:
            findings.append(
                Finding(
                    "high",
                    "interface",
                    f"Interface {name} disappeared",
                    "The interface existed in the baseline but is absent from the current snapshot.",
                    "Check hardware, virtualization settings, drivers, and interface naming changes.",
                )
            )
        elif old.get("state") == "UP" and new.get("state") != "UP":
            findings.append(
                Finding(
                    "high",
                    "interface",
                    f"Interface {name} is no longer up",
                    f"State changed from UP to {new.get('state', 'UNKNOWN')}.",
                    "Check link state, switch port status, cabling, and the interface configuration.",
                )
            )

    old_probes = {
        item.get("host"): item for item in baseline.get("network", {}).get("probes", [])
    }
    for probe in current.get("network", {}).get("probes", []):
        old = old_probes.get(probe.get("host"))
        if old and old.get("reachable") and not probe.get("reachable"):
            findings.append(
                Finding(
                    "high",
                    "connectivity",
                    f"Probe to {probe.get('host')} failed",
                    "The target was reachable in the baseline and is unreachable now.",
                    "Test the local gateway, routing, DNS, and upstream connectivity in that order.",
                )
            )

    old_failed = set(baseline.get("system", {}).get("failed_services", []))
    new_failed = set(current.get("system", {}).get("failed_services", []))
    for service in sorted(new_failed - old_failed):
        findings.append(
            Finding(
                "medium",
                "service",
                f"Service failure detected: {service}",
                "The service is failed now but was not failed in the baseline.",
                f"Inspect `systemctl status {service}` and `journalctl -u {service}` before restarting it.",
            )
        )

    return findings


def findings_as_dicts(findings: list[Finding]) -> list[dict[str, str]]:
    return [asdict(finding) for finding in findings]


def findings_as_markdown(
    baseline: dict[str, Any], current: dict[str, Any], findings: list[Finding]
) -> str:
    lines = [
        "# Network Incident Report",
        "",
        f"- Baseline captured: {baseline.get('captured_at', 'unknown')}",
        f"- Current captured: {current.get('captured_at', 'unknown')}",
        f"- Findings: {len(findings)}",
        "",
    ]
    if not findings:
        lines.extend(["## Result", "", "No high-signal network changes were detected.", ""])
        return "\n".join(lines)

    for index, finding in enumerate(findings, start=1):
        lines.extend(
            [
                f"## {index}. [{finding.severity.upper()}] {finding.title}",
                "",
                f"**Category:** {finding.category}",
                "",
                f"**Evidence:** {finding.evidence}",
                "",
                f"**Recommended verification:** {finding.recommendation}",
                "",
            ]
        )
    return "\n".join(lines)

