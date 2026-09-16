from network_flight_recorder.analyzer import Diagnosis
from network_flight_recorder.remediation import (
    generate_remediation_plan,
    remediation_plan_as_dict,
)


def test_generate_routing_remediation_requires_approval():
    diagnosis = Diagnosis(
        likely_cause="Default gateway or routing failure",
        confidence="high",
        rationale=(
            "External reachability failed when the default route disappeared."
        ),
        supporting_findings=(
            "Default route disappeared",
            "Probe to 1.1.1.1 failed",
        ),
        verification=(
            "Verify the default gateway, route table, and DHCP lease."
        ),
    )

    plan = generate_remediation_plan(diagnosis)

    assert plan is not None
    assert plan.action_id == "renew_network_configuration"
    assert plan.risk == "medium"
    assert plan.approval_required is True
    assert plan.diagnosis == "Default gateway or routing failure"


def test_unknown_diagnosis_falls_back_to_manual_review():
    diagnosis = Diagnosis(
        likely_cause="Unexpected network condition",
        confidence="low",
        rationale="The available evidence does not match a known pattern.",
        supporting_findings=("Unknown condition",),
        verification="Inspect the network manually.",
    )

    plan = generate_remediation_plan(diagnosis)

    assert plan is not None
    assert plan.action_id == "manual_review"
    assert plan.risk == "unknown"
    assert plan.approval_required is True


def test_no_diagnosis_returns_no_plan():
    assert generate_remediation_plan(None) is None


def test_remediation_plan_serializes_to_dict():
    diagnosis = Diagnosis(
        likely_cause="DNS resolution failure",
        confidence="high",
        rationale="DNS failed while direct connectivity remained available.",
        supporting_findings=("DNS lookup failed",),
        verification="Query the configured resolver directly.",
    )

    plan = generate_remediation_plan(diagnosis)
    result = remediation_plan_as_dict(plan)

    assert result is not None
    assert result["action_id"] == "restore_name_resolution"
    assert result["approval_required"] is True

def test_remediation_plan_markdown_requires_approval():
    from network_flight_recorder.remediation import (
        remediation_plan_as_markdown,
    )

    diagnosis = Diagnosis(
        likely_cause="DNS resolution failure",
        confidence="high",
        rationale="DNS failed while connectivity remained available.",
        supporting_findings=("DNS lookup failed",),
        verification="Query the resolver directly.",
    )

    plan = generate_remediation_plan(diagnosis)
    report = remediation_plan_as_markdown(plan)

    assert "## Remediation Plan" in report
    assert "restore_name_resolution" in report
    assert "Approval required:** YES" in report

def test_cli_compare_includes_remediation_plan(capsys):
    from network_flight_recorder.cli import main

    result = main(
        [
            "compare",
            "tests/fixtures/healthy.json",
            "tests/fixtures/broken.json",
            "--remediation-plan",
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "## Remediation Plan" in output
    assert "restore_interface_connectivity" in output
    assert "Approval required:** YES" in output
