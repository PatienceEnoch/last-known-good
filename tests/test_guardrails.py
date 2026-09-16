import pytest

from network_flight_recorder.guardrails import (
    ALLOWED_ACTION_IDS,
    is_action_allowed,
    require_allowed_action,
)


def test_known_remediation_actions_are_allowlisted():
    assert "restore_interface_connectivity" in ALLOWED_ACTION_IDS
    assert "renew_network_configuration" in ALLOWED_ACTION_IDS
    assert "restore_name_resolution" in ALLOWED_ACTION_IDS
    assert "investigate_path_degradation" in ALLOWED_ACTION_IDS


def test_unknown_action_is_blocked():
    assert is_action_allowed("run_arbitrary_command") is False

    with pytest.raises(PermissionError):
        require_allowed_action("run_arbitrary_command")


def test_manual_review_is_not_executable():
    assert is_action_allowed("manual_review") is False

    with pytest.raises(PermissionError):
        require_allowed_action("manual_review")
