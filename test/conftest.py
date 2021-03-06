"""Collection of pytest fixtures for tests."""

import os
from pathlib import Path
import pytest

__copyright__ = "Copyright (C) Sierra Wireless Inc."

pytest_plugins = ["pytester", "pytest_letp"]

INTERNAL_TEST_PATH = os.path.expandvars("$LETP_INTERNAL_PATH")

CURRENT_PATH = Path(os.path.dirname(__file__))
LETP_STUBS = os.path.join(CURRENT_PATH, "framework_tests", "letp")


@pytest.fixture(scope="session")
def letp_cmd():
    """Get letp command path."""
    return os.path.join(CURRENT_PATH.parent, "letp")


@pytest.fixture(scope="session")
def default_command(letp_cmd):
    """Have a default command."""
    return (
        "{} run ".format(letp_cmd)
        + "scenario/command/test_config_stub.py::test_config_value "
    )


@pytest.fixture(scope="session", autouse=True)
def init_letp(letp_cmd):
    """Init LETP_TEST path for the tests."""
    store_letp_test_path = None
    if "LETP_TESTS" in os.environ:
        store_letp_test_path = os.environ["LETP_TESTS"]
    os.environ["LETP_TESTS"] = LETP_STUBS
    os.chdir(os.environ["LETP_TESTS"])
    assert os.path.exists(letp_cmd), "letp was not found!!!"
    print(
        "\n#####################LETP Tests Repo:{}######################\n".format(
            LETP_STUBS
        )
    )
    yield
    if store_letp_test_path:
        os.environ["LETP_TESTS"] = store_letp_test_path
    print("### Restore LETP_TESTS to {} ###".format(store_letp_test_path))


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart():
    """Dynamically load internal tests stub folder.

    Clean up the symlinks after the test.
    """
    if os.path.exists(INTERNAL_TEST_PATH):
        internal_tests_dir = os.path.join(INTERNAL_TEST_PATH, "test")
        internal_tests_stub_name = "internal_stub"
        src_letp_test_stub = os.path.join(internal_tests_dir, internal_tests_stub_name)
        dst_letp_test_stub = os.path.join(LETP_STUBS, internal_tests_stub_name)
        if not os.path.islink(dst_letp_test_stub):
            os.symlink(src_letp_test_stub, dst_letp_test_stub)


@pytest.fixture
def log_file_option(request):
    """Add the function name as the log file name."""
    return "--log-file log/{}.txt".format(request.node.name)


@pytest.fixture
def testdir_stub(testdir):
    """Define a stub file in testdir."""
    testdir.makepyfile(
        """
    import pytest

    def test_stub():
        assert "Hello World!"
    """
    )
    return testdir
