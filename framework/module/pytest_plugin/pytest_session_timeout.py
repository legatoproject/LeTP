"""!@package pytest_session_timeout Session timeout.

In CI, we may want to have a time limit for the session.

This module piggybacks the pytest-timeout plugin
which can set timeout for each test.

It reads the session timeout and count down the elapsed time
after every test and calculate the next test timeout.

How to config timeout?
Session Timeout:

CLI command line: --session-timeout provides a timeout limit for the whole session.

Test case timeout:

In summary, we can configure the timeout via
(The priority from the lowest to the highest.)
pytest.ini with timeout = 300,
environment variable PYTEST_TIMEOUT,
--timeout CLi option,
@pytest.mark.timeout(300) marker.

Refer to: https://pypi.org/project/pytest-timeout/
"""
import sys
import time
import pytest
import _pytest.config
import pytest_timeout


def pytest_addoption(parser):
    """Add pytest cmd line options."""
    parser.addoption(
        "--session-timeout",
        action="store",
        help="The timeout for the whole test session",
    )


@pytest.hookimpl
def pytest_configure(config: _pytest.config.Config) -> None:
    """Configure the plugin."""
    config.pluginmanager.register(SessionTimeoutPlugin(config), "SessionTimeoutPlugin")


class TestTimeout:
    """Timeout for each test.

    It piggybacks pytest_timeout plugin.
    """

    def __init__(self, item):
        self.item = item
        self.item_timeout = self._get_pytest_timeout()

    def _get_pytest_timeout(self):
        per_test_timeout_settings = pytest_timeout.get_params(self.item)
        return per_test_timeout_settings.timeout

    def set_pytest_timeout(self, session_timeout):
        """Set the pytest timeout's highest priority timeout via marker."""
        if self.item_timeout and self.item_timeout > session_timeout:
            self.item.add_marker(pytest.mark.timeout(session_timeout))


class SessionTimeoutPlugin:
    """Session Timeout implementation.

    Depending on session timeout and pytest-timeout plugins setttings.
    """

    def __init__(self, config):
        self.config = config
        self._tw = _pytest.config.create_terminal_writer(config, sys.stdout)
        self.configured_session_timeout = None
        self.elapsed = 0

    @property
    def _session_timeout(self):
        if self.configured_session_timeout:
            return self.configured_session_timeout - self.elapsed
        return None

    def _stop_session_if_needed(self, session):
        if self.elapsed > self.configured_session_timeout:
            session.shouldstop = (
                "Session time limit {:.4f} "
                "in seconds reached: {:.4f} elapsed".format(
                    self.elapsed, self.configured_session_timeout
                )
            )

    @pytest.hookimpl(trylast=True)
    def pytest_sessionstart(self, session):
        """Process session timeout."""
        session_timeout = session.config.getoption("--session-timeout")
        if session_timeout:
            self.configured_session_timeout = float(session_timeout)

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        """Wrap a session timeout around pytest-timeout plugin."""
        precise_start = None
        if self._session_timeout:
            msg = "\nsession timeout in {:.4f}s".format(self._session_timeout)
            self._tw.write(msg, flush=True, yellow=True)
            test_timeout = TestTimeout(item)
            test_timeout.set_pytest_timeout(self._session_timeout)
            precise_start = time.perf_counter()

        yield

        if self._session_timeout:
            precise_end = time.perf_counter()
            duration = precise_end - precise_start
            self.elapsed += duration
            self._stop_session_if_needed(item.session)
