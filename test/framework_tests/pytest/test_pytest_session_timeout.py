"""Test the session timeout plugin."""
import pytest
from testlib import run_python_with_command


def test_valid_timeout_config_without_timeout(testdir_stub):
    """Test timeout config."""
    result = testdir_stub.runpytest(
        "-p", "pytest_session_timeout", "--session-timeout=10"
    )
    result.assert_outcomes(passed=1)


def test_valid_session_timeout(default_command):
    """Make session timeout valid and verify INTERRUPTED."""
    default_command += "--session-timeout=0.00001"
    try:
        run_python_with_command(default_command)
        assert 0, "Should not hit here. Should timeout"
    except SystemExit as err:
        assert err.code == pytest.ExitCode.INTERRUPTED
