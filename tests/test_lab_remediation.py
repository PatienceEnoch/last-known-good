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
