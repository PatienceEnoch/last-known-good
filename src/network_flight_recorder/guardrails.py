"""Safety guardrails for Network Flight Recorder remediation actions."""

from __future__ import annotations

ALLOWED_ACTION_IDS = frozenset(
    {
        "restore_interface_connectivity",
        "renew_network_configuration",
        "restore_name_resolution",
        "investigate_path_degradation",
    }
)


def is_action_allowed(action_id: str) -> bool:
    """Return True only when an action is explicitly allowlisted."""
    return action_id in ALLOWED_ACTION_IDS


def require_allowed_action(action_id: str) -> None:
    """Block any remediation action that is not explicitly allowlisted."""
    if not is_action_allowed(action_id):
        raise PermissionError(
            f"Remediation action is not allowlisted: {action_id}"
        )
