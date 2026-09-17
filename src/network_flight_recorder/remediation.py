"""Generate approval-required remediation plans from network diagnoses."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from .analyzer import Diagnosis
from .guardrails import require_allowed_action


@dataclass(frozen=True)
class RemediationPlan:
    diagnosis: str
    confidence: str
    action_id: str
    proposed_action: str
    risk: str
    rationale: str
    verification: str
    approval_required: bool = True


_ACTIONS: dict[str, dict[str, str]] = {
    "Local interface or link failure": {
        "action_id": "restore_interface_connectivity",
        "proposed_action": (
            "Restore the affected interface or link after verifying the "
            "intended interface and connection."
        ),
        "risk": "medium",
    },
    "Default gateway or routing failure": {
        "action_id": "renew_network_configuration",
        "proposed_action": (
            "Renew network configuration for the affected interface and "
            "restore the expected default route."
        ),
        "risk": "medium",
    },
    "DNS resolution failure": {
        "action_id": "restore_name_resolution",
        "proposed_action": (
            "Restore the configured name-resolution service and verify the "
            "expected resolver configuration."
        ),
        "risk": "low",
    },
    "Network path degradation or congestion": {
        "action_id": "investigate_path_degradation",
        "proposed_action": (
            "Perform additional path and interface diagnostics before making "
            "a configuration change."
        ),
        "risk": "low",
    },
}


def generate_remediation_plan(
    diagnosis: Diagnosis | None,
) -> RemediationPlan | None:
    """Return an approval-required plan for a supported diagnosis."""
    if diagnosis is None:
        return None

    action = _ACTIONS.get(diagnosis.likely_cause)

    if action is None:
        return RemediationPlan(
            diagnosis=diagnosis.likely_cause,
            confidence=diagnosis.confidence,
            action_id="manual_review",
            proposed_action=(
                "Review the diagnosis and supporting evidence manually before "
                "making any network change."
            ),
            risk="unknown",
            rationale=diagnosis.rationale,
            verification=diagnosis.verification,
        )

    return RemediationPlan(
        diagnosis=diagnosis.likely_cause,
        confidence=diagnosis.confidence,
        action_id=action["action_id"],
        proposed_action=action["proposed_action"],
        risk=action["risk"],
        rationale=diagnosis.rationale,
        verification=diagnosis.verification,
    )


def remediation_plan_as_dict(
    plan: RemediationPlan | None,
) -> dict[str, Any] | None:
    return asdict(plan) if plan else None


def remediation_plan_as_markdown(
    plan: RemediationPlan | None,
) -> str:
    if plan is None:
        return "## Remediation Plan\n\nNo remediation plan available.\n"

    approval = "YES" if plan.approval_required else "NO"

    return (
        "## Remediation Plan\n\n"
        f"**Diagnosis:** {plan.diagnosis}\n\n"
        f"**Confidence:** {plan.confidence}\n\n"
        f"**Action ID:** `{plan.action_id}`\n\n"
        f"**Proposed action:** {plan.proposed_action}\n\n"
        f"**Risk:** {plan.risk}\n\n"
        f"**Approval required:** {approval}\n\n"
        f"**Rationale:** {plan.rationale}\n\n"
        f"**Verification:** {plan.verification}\n"
    )



def execute_remediation(
    plan: RemediationPlan,
    *,
    approved: bool,
    executor: Callable[[str], None],
) -> None:
    """Execute an allowlisted remediation only after explicit approval."""
    if not approved:
        raise PermissionError(
            "Remediation requires explicit approval"
        )

    require_allowed_action(plan.action_id)

    executor(plan.action_id)
