"""Test multiple target connectivity."""
import pytest
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def test_one_target(target):
    """Test sending external commands to one target.

    Fill target.xml first.
    """
    swilog.step("Get legato version on first target")
    target.run("ls")
    target.run("legato version")


@pytest.mark.config("$LETP_TESTS/config/target2.xml")
def test_two_targets(target, target2):
    """Test sending external commands to 2 targets.

    Fill target.xml for the first target and target2.xml for the second.
    """
    swilog.step("Get legato version on first target")
    target.run("ls")
    target.run("legato version")

    swilog.step("Get legato version on second target")
    target2.run("ls")
    target2.run("legato version")

    swilog.step("Reboot the targets")
    target2.reboot()
    target.reboot()
