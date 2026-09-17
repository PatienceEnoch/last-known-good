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


@dataclass(frozen=True)
class Diagnosis:
    likely_cause: str
    confidence: str
    rationale: str
    supporting_findings: tuple[str, ...]
    verification: str


def _default_route(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    routes = snapshot.get("network", {}).get("routes", [])
    return next((route for route in routes if route.get("dst") == "default"), None)


def _interfaces(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = snapshot.get("network", {}).get("interfaces", [])
    return {item.get("name", "unknown"): item for item in items}


def _address_set(interface: dict[str, Any]) -> set[tuple[Any, Any, Any]]:
    return {
        (address.get("family"), address.get("local"), address.get("prefixlen"))
        for address in interface.get("addresses", [])
    }


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
    elif not old_default and new_default:
        findings.append(
            Finding(
                "info",
                "routing",
                "Default route restored",
                (
                    "The previous snapshot had no default route; "
                    f"the current snapshot uses {new_default.get('gateway', 'an on-link route')} "
                    f"via {new_default.get('dev', 'unknown')}."
                ),
                "Verify external connectivity remains stable.",
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
    elif not old_dns and new_dns:
        findings.append(
            Finding(
                "info",
                "dns",
                "DNS configuration restored",
                f"Resolvers are available again: {', '.join(new_dns)}.",
                "Verify name resolution remains stable.",
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

    old_dns_probes = {
        item.get("name"): item for item in baseline.get("network", {}).get("dns_probes", [])
    }
    for probe in current.get("network", {}).get("dns_probes", []):
        old = old_dns_probes.get(probe.get("name"))
        if old and old.get("resolved") and not probe.get("resolved"):
            findings.append(
                Finding(
                    "critical",
                    "dns",
                    f"DNS lookup for {probe.get('name')} failed",
                    f"The name resolved in the baseline but now fails: {probe.get('error') or 'unknown error'}.",
                    "Test the configured resolver directly and compare IP reachability before changing DNS.",
                )
            )
        elif old and old.get("resolved") and probe.get("resolved"):
            old_time = old.get("response_time_ms")
            new_time = probe.get("response_time_ms")
            if (
                old_time is not None
                and new_time is not None
                and new_time >= max(old_time * 3, old_time + 100)
            ):
                findings.append(
                    Finding(
                        "medium",
                        "dns",
                        f"DNS lookup for {probe.get('name')} slowed",
                        f"Response time increased from {old_time:.2f} ms to {new_time:.2f} ms.",
                        "Check resolver health, network latency, and retry against an approved alternate resolver.",
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
        elif old.get("state") != "UP" and new.get("state") == "UP":
            findings.append(
                Finding(
                    "info",
                    "interface",
                    f"Interface {name} is back up",
                    (
                        f"State changed from {old.get('state', 'UNKNOWN')} "
                        "to UP."
                    ),
                    "Verify addressing, routing, and connectivity remain stable.",
                )
            )
        else:
            if old.get("mtu") and new.get("mtu") and old.get("mtu") != new.get("mtu"):
                findings.append(
                    Finding(
                        "medium",
                        "interface",
                        f"Interface {name} MTU changed",
                        f"MTU changed from {old.get('mtu')} to {new.get('mtu')}.",
                        "Confirm the MTU matches the connected network and test for fragmentation.",
                    )
                )
            old_addresses = _address_set(old)
            new_addresses = _address_set(new)
            if old_addresses != new_addresses:
                removed = sorted(old_addresses - new_addresses, key=str)
                added = sorted(new_addresses - old_addresses, key=str)
                findings.append(
                    Finding(
                        "high",
                        "addressing",
                        f"Interface {name} addressing changed",
                        f"Removed addresses: {removed or 'none'}; added addresses: {added or 'none'}.",
                        "Verify DHCP or static addressing, prefix length, and duplicate-address events.",
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
        elif old and not old.get("reachable") and probe.get("reachable"):
            findings.append(
                Finding(
                    "info",
                    "connectivity",
                    f"Probe to {probe.get('host')} recovered",
                    "The target was unreachable previously and is reachable again.",
                    "Continue monitoring to confirm connectivity remains stable.",
                )
            )
        elif old and old.get("reachable") and probe.get("reachable"):
            old_loss = old.get("packet_loss_percent")
            new_loss = probe.get("packet_loss_percent")
            if old_loss is not None and new_loss is not None and new_loss - old_loss >= 20:
                findings.append(
                    Finding(
                        "high",
                        "connectivity",
                        f"Packet loss to {probe.get('host')} increased",
                        f"Packet loss increased from {old_loss:.1f}% to {new_loss:.1f}%.",
                        "Check interface errors, Wi-Fi signal, cabling, congestion, and upstream loss.",
                    )
                )
            old_latency = old.get("average_latency_ms")
            new_latency = probe.get("average_latency_ms")
            if (
                old_latency is not None
                and new_latency is not None
                and new_latency >= max(old_latency * 2, old_latency + 25)
            ):
                findings.append(
                    Finding(
                        "medium",
                        "performance",
                        f"Latency to {probe.get('host')} increased",
                        f"Average latency increased from {old_latency:.1f} ms to {new_latency:.1f} ms.",
                        "Compare gateway and upstream latency, then check congestion and route changes.",
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

    for service in sorted(old_failed - new_failed):
        findings.append(
            Finding(
                "info",
                "service",
                f"Service recovered: {service}",
                "The service was failed previously and is no longer failed.",
                f"Verify `systemctl status {service}` remains healthy.",
            )
        )

    return findings


def findings_as_dicts(findings: list[Finding]) -> list[dict[str, str]]:
    return [asdict(finding) for finding in findings]


def diagnose(findings: list[Finding]) -> Diagnosis | None:
    """Correlate related symptoms into one explainable likely root cause."""
    titles = {finding.title for finding in findings}
    categories = {finding.category for finding in findings}
    interface_failures = sorted(
        title
        for title in titles
        if title.startswith("Interface ")
        and title.endswith(("disappeared", "is no longer up"))
    )
    route_failures = sorted(
        title for title in titles if title in {"Default route disappeared", "Default route changed"}
    )
    connectivity_failures = sorted(
        title for title in titles if title.startswith("Probe to ") and title.endswith(" failed")
    )
    dns_failures = sorted(
        title
        for title in titles
        if title == "DNS configuration is empty"
        or (title.startswith("DNS lookup for ") and title.endswith(" failed"))
    )

    if interface_failures and (route_failures or connectivity_failures):
        return Diagnosis(
            "Local interface or link failure",
            "high",
            "An interface failure occurred alongside loss of routing or external reachability.",
            tuple(interface_failures + route_failures + connectivity_failures),
            "Verify link state, cabling or Wi-Fi association, switch port status, and the interface driver.",
        )
    if route_failures and connectivity_failures:
        return Diagnosis(
            "Default gateway or routing failure",
            "high",
            "External reachability failed when the default route disappeared or changed.",
            tuple(route_failures + connectivity_failures),
            "Verify the default gateway, route table, and DHCP lease before testing upstream.",
        )
    if dns_failures and "connectivity" not in categories:
        return Diagnosis(
            "DNS resolution failure",
            "high",
            "Name resolution failed without evidence that direct IP reachability failed.",
            tuple(dns_failures),
            "Query the configured resolver directly, then verify resolver health and configuration.",
        )
    degradation = sorted(
        title
        for title in titles
        if title.startswith(("Packet loss to ", "Latency to "))
    )
    if len(degradation) >= 2:
        return Diagnosis(
            "Network path degradation or congestion",
            "medium",
            "Latency and packet loss worsened together while the destination remained reachable.",
            tuple(degradation),
            "Compare gateway and upstream probes, then inspect interface errors and utilization.",
        )
    return None


def diagnosis_as_dict(diagnosis: Diagnosis | None) -> dict[str, Any] | None:
    return asdict(diagnosis) if diagnosis else None


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
    diagnosis = diagnose(findings)
    if diagnosis:
        lines.extend(
            [
                "## Likely root cause",
                "",
                f"**{diagnosis.likely_cause}** — {diagnosis.confidence.upper()} confidence",
                "",
                diagnosis.rationale,
                "",
                "**Correlated evidence:**",
                "",
                *[f"- {title}" for title in diagnosis.supporting_findings],
                "",
                f"**Recommended verification:** {diagnosis.verification}",
                "",
                "---",
                "",
            ]
        )
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
