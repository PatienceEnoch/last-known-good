"""Build tightly scoped remediation commands for the isolated Docker lab."""

from __future__ import annotations

import subprocess
from typing import Any

Snapshot = dict[str, Any]


def _default_route(snapshot: Snapshot) -> dict[str, Any] | None:
    """Return the default route from a captured snapshot."""
    routes = snapshot.get("network", {}).get("routes", [])

    return next(
        (
            route
            for route in routes
            if route.get("dst") == "default"
        ),
        None,
    )


def build_lab_remediation_command(
    action_id: str,
    baseline: Snapshot,
) -> list[str]:
    """Build an exact lab remediation command from known-good evidence."""
    if action_id != "renew_network_configuration":
        raise ValueError(
            f"Unsupported lab remediation action: {action_id}"
        )

    route = _default_route(baseline)

    if route is None:
        raise ValueError(
            "Known-good snapshot has no default route"
        )

    gateway = route.get("gateway")
    interface = route.get("dev")

    if not gateway or not interface:
        raise ValueError(
            "Known-good default route is missing gateway or interface"
        )

    return [
        "ip",
        "route",
        "replace",
        "default",
        "via",
        str(gateway),
        "dev",
        str(interface),
    ]



def execute_lab_remediation(
    action_id: str,
    baseline: Snapshot,
    *,
    runner: Any = subprocess.run,
) -> None:
    """Execute a tightly scoped remediation command inside the lab."""
    command = build_lab_remediation_command(
        action_id,
        baseline,
    )

    runner(
        command,
        check=True,
    )



def verify_lab_remediation(
    action_id: str,
    baseline: Snapshot,
    current: Snapshot,
) -> bool:
    """Verify that the intended lab remediation restored expected state."""
    if action_id != "renew_network_configuration":
        raise ValueError(
            f"Unsupported lab remediation action: {action_id}"
        )

    expected_route = _default_route(baseline)
    current_route = _default_route(current)

    if expected_route is None or current_route is None:
        return False

    return (
        current_route.get("gateway")
        == expected_route.get("gateway")
        and current_route.get("dev")
        == expected_route.get("dev")
    )



def _describe_default_route(snapshot: Snapshot) -> str:
    """Return a readable description of the snapshot's default route."""
    route = _default_route(snapshot)

    if route is None:
        return "missing"

    gateway = route.get("gateway", "unknown")
    interface = route.get("dev", "unknown")

    return f"{gateway} via {interface}"


def build_remediation_report(
    *,
    action_id: str,
    baseline: Snapshot,
    before: Snapshot,
    after: Snapshot,
    verified: bool,
) -> str:
    """Build a Markdown before-and-after remediation report."""
    verification = "PASSED" if verified else "FAILED"

    return "\n".join(
        [
            "# Remediation Report",
            "",
            f"- Action: `{action_id}`",
            f"- Verification: {verification}",
            "",
            "## Before remediation",
            "",
            f"- Default route: {_describe_default_route(before)}",
            "",
            "## Known-good state",
            "",
            f"- Default route: {_describe_default_route(baseline)}",
            "",
            "## After remediation",
            "",
            f"- Default route: {_describe_default_route(after)}",
            "",
        ]
    )
