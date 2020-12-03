"""Collection of pytest fixtures for tests."""
import os
import traceback
import pytest
from pytest_letp.lib import swilog
from pytest_letp.lib import modules

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def pytest_addoption(parser):
    """Add options to pytest."""
    parser.addoption("--path", action="append", help="xml xpath")
    parser.addoption(
        "--expected_value", action="append", help="expected value of the xml xpath"
    )


@pytest.fixture(scope="function")
def target(request, read_config):
    """Assert target is in desired state before running testcase."""
    swilog.step("####### Check initial target state #######")

    target = None

    try:
        swilog.debug("Construct an on-target obj")
        target = modules.define_target(request, read_config)
    except:
        traceback.print_exc()
        raise

    # Eventually retry, unprotected this time
    if not target:
        target = modules.define_target(request, read_config)

    swilog.step("####### End: Check initial target state #######")
    yield target
    target.teardown()


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown():
    """Check the session setup and teardown.

    Do the pre-validation and cleanup.
    """
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config")
    assert os.path.exists(os.readlink(config_path)), "No config path at {}".format(
        config_path
    )
    yield
