"""The stub for letp unit tests."""
import pytest
import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


@pytest.fixture
def teardown_errors():
    """Force a teardown error."""
    yield True
    assert 0, "Error in teardown"


def test_command_by_filename():
    """This is just an empty function.

    Used for checking if this function got called or not.
    """
    swilog.info("Inside test_command_by_filename function")


@pytest.mark.usefixtures("teardown_errors")
def test_setup_teardown_failures():
    """Test failures in setup and teardown.

    Used for checking if this function got called or not.
    """
    swilog.step("Inside test_setup_teardown_failures function")
    assert 0, "Failure in testing phase."


@pytest.mark.xfail(reason="XFAIL result sample")
def test_json_report_xfail():
    """Test json report for xfail."""
    swilog.info("test_json_report_stub was called.")
    assert 0, "xfail error message."


@pytest.mark.xfail(reason="XPASS result sample")
def test_json_report_xpass():
    """Test json report for xpass."""
    swilog.info("test_json_report_stub was xpassed.")


def test_json_report_fail():
    """Test json report for fail."""
    swilog.info("test_json_report_stub fails.")
    assert 0, "error message."


def test_json_report_skip():
    """Test json report for skip."""
    pytest.skip("purposed skipped")
