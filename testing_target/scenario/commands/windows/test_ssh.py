"""Provide sample testcases using SSH connection in Windows."""
from pytest_letp.lib import swilog


__copyright__ = "Copyright (C) Sierra Wireless Inc."


# ======================================================================
# Test functions
# ======================================================================
def test_simple_command_0001(target):
    """Send some basic commands over ssh using target.execute_command."""
    msg_err = "[FAILED] can't get expected value after sending command"
    # Print a message
    swilog.step("Begin of {}".format(test_simple_command_0001.__name__))

    # Send 'cm info' command. Expect IMEI in response. Timeout of 10s
    rsp = target.execute_command("/legato/systems/current/bin/cm info", 10, "IMEI")
    assert rsp, msg_err

    # Send 'legato version' command. Expect rc in response. Timeout of 10s
    rsp = target.execute_command(
        "/legato/systems/current/bin/legato version", 10, ".*rc.*"
    )
    assert rsp, msg_err

    # Send 'legato status' command.
    target.execute_command("/legato/systems/current/bin/legato status")


def test_simple_command_0002(target):
    """Send some basic commands over ssh using target.send, target.expect."""
    msg_err = "[FAILED] can't get expected value after sending command"
    # Print a message
    swilog.step("Begin of {}".format(test_simple_command_0002.__name__))

    # Send 'cm info' command. Expected is regexes. Timeout of 10
    target.send("cm info")
    assert target.expect(r".*Resets.*", timeout=10) == 0, msg_err

    # Send 'app status atService' command. Expected is regexes. Timeout of 10
    target.send("app status atService")
    assert target.expect([r".*stopped.*", r".*running.*"], timeout=10), msg_err
