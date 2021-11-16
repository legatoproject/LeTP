"""Host fixtures.

Fixtures for interacting with and executing commands on the host system
(i.e. the system where LeTP is running).
"""
__copyright__ = "Copyright (C) Sierra Wireless Inc."

from collections.abc import Callable
import subprocess

import pytest

from pytest_letp.lib import swilog


def _do_cmd(cmd: list):
    """Execute a command.

    :param cmd: List comprising the command to execute.
    :type cmd: list
    """
    try:
        swilog.debug(f"Host command: [{' '.join(cmd)}]")
        subprocess.run(
            cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as ex:
        swilog.error(
            f"Command [{' '.join(cmd)}] failed (code {ex.returncode}):\n"
            f"{ex.stdout.decode('utf-8')}"
        )
        raise ex


@pytest.fixture
def sudo() -> Callable:
    """Fixture to execute a command as a super user on the host system.

    :return: Closure to execute the provided command.
    :rtype: Callable
    """

    def _sudo(cmd: list):
        """Closure wrapping the subprocess invocation of the sudo command.

        :param cmd: List comprising the command to execute.
        :type cmd: list
        """
        _do_cmd(["sudo"] + cmd)

    return _sudo


@pytest.fixture
def command() -> Callable:
    """Fixture to execute a command on the host system.

    :return: Function to execute the provided command.
    :rtype: Callable
    """
    return _do_cmd
