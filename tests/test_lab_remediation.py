import json
from pathlib import Path

from network_flight_recorder.lab_remediation import (
    build_lab_remediation_command,
)

FIXTURES = Path("tests/fixtures")


def test_build_routing_recovery_command_from_baseline() -> None:
    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )

    command = build_lab_remediation_command(
        "renew_network_configuration",
        baseline,
    )

    assert command == [
        "ip",
        "route",
        "replace",
        "default",
        "via",
        "10.10.10.1",
        "dev",
        "eth0",
    ]


def test_execute_lab_remediation_runs_exact_command() -> None:
    from network_flight_recorder.lab_remediation import (
        execute_lab_remediation,
    )

    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )

    calls = []

    def fake_runner(command, *, check):
        calls.append(
            {
                "command": command,
                "check": check,
            }
        )

    execute_lab_remediation(
        "renew_network_configuration",
        baseline,
        runner=fake_runner,
    )

    assert calls == [
        {
            "command": [
                "ip",
                "route",
                "replace",
                "default",
                "via",
                "10.10.10.1",
                "dev",
                "eth0",
            ],
            "check": True,
        }
    ]


def test_verify_lab_remediation_detects_restored_network() -> None:
    from network_flight_recorder.lab_remediation import (
        verify_lab_remediation,
    )

    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    healthy = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    broken = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )

    assert (
        verify_lab_remediation(
            "renew_network_configuration",
            baseline,
            healthy,
        )
        is True
    )

    assert (
        verify_lab_remediation(
            "renew_network_configuration",
            baseline,
            broken,
        )
        is False
    )


def test_build_remediation_report_includes_before_and_after_state() -> None:
    from network_flight_recorder.lab_remediation import (
        build_remediation_report,
    )

    baseline = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )
    failed = json.loads(
        (FIXTURES / "broken.json").read_text(encoding="utf-8")
    )
    recovered = json.loads(
        (FIXTURES / "healthy.json").read_text(encoding="utf-8")
    )

    report = build_remediation_report(
        action_id="renew_network_configuration",
        baseline=baseline,
        before=failed,
        after=recovered,
        verified=True,
    )

    assert "# Remediation Report" in report
    assert "renew_network_configuration" in report
    assert "Verification: PASSED" in report
    assert "Before remediation" in report
    assert "After remediation" in report
    assert "Default route: missing" in report
    assert "Default route: 10.10.10.1 via eth0" in report


def test_failed_verification_triggers_rollback() -> None:
    from network_flight_recorder.lab_remediation import (
        remediate_with_rollback,
    )

    calls = []

    def fake_remediate():
        calls.append("remediate")

    def fake_verify():
        calls.append("verify")
        return False

    def fake_rollback():
        calls.append("rollback")

    result = remediate_with_rollback(
        remediate=fake_remediate,
        verify=fake_verify,
        rollback=fake_rollback,
    )

    assert result is False
    assert calls == [
        "remediate",
        "verify",
        "rollback",
    ]



def test_successful_verification_skips_rollback() -> None:
    from network_flight_recorder.lab_remediation import (
        remediate_with_rollback,
    )

    calls = []

    def fake_remediate():
        calls.append("remediate")

    def fake_verify():
        calls.append("verify")
        return True

    def fake_rollback():
        calls.append("rollback")

    result = remediate_with_rollback(
        remediate=fake_remediate,
        verify=fake_verify,
        rollback=fake_rollback,
    )

    assert result is True
    assert calls == [
        "remediate",
        "verify",
    ]
