"""!AT-test samples.

Set of tests showing how to use the AT commands interface

@package sampleAT
"""
# To use target.at.expect
import pexpect

# Log module
import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


# ======================================================================
# Test functions
# ======================================================================
def test_AT_commands_simple_command(target):
    """Send AT commands. Check for simple intermediate responses.

    Args:
        target: fixture to communicate with the target
    """
    # Print a message
    swilog.info("This is my test")
    # Send AT command. Expect OK. Timeout of 1s
    target.run_at_cmd("AT", 1)

    # Send AT+CPIN? command. Expect  +CPIN: READY, then OK
    target.run_at_cmd("AT+CPIN?", 1, [r"\+CPIN: READY\r", "OK\r"])

    # Send AT+CPIN=530 command. Expect ERROR
    rsp = target.run_at_cmd("AT+CPIN=530", 1, ["ERROR"])
    # print the content of the received data
    swilog.info("Receive %s" % rsp)


def test_AT_commands_expect(target):
    """Send a command and expect/search for regexp patterns.

    Args:
        target: fixture to communicate with the target
    """
    # target.run_at_cmd uses low level functions: send + expect.
    # They can be used to control what to send and what to receive.
    # Send ATI9, wait for IMEI SV
    rsp = target.send("/usr/bin/microcom /dev/ttyAT\r\n")
    target.send("ATI9\r")
    # expect will find patterns in a list and return
    # which pattern it has found
    rsp = target.expect([pexpect.TIMEOUT, "IMEI SV: "], 10)
    if rsp == 0:
        # Found the first pattern (pexpect.TIMEOUT)
        swilog.error("Timeout")
    elif rsp == 1:
        # Found the second element: "IMEI SV: "
        # Now get the IMEI SV
        rsp = target.expect([pexpect.TIMEOUT, r"\d+\r"], 10)
        # target.at.before is the content of the received data
        # target.at.after is the content of the regexp
        swilog.info("IMEI SV is %s" % target.after.strip())
        # get the end of the command
        rsp = target.expect(["OK"], 10)
    target.sendcontrol("x")


def test_AT_commands_expect_in_order(target):
    """Wait for a list of regexp patterns in the order of the list.

    Args:
        target: fixture to communicate with the target
    """
    # Expect some patterns in a list (in order of the list)
    # Send ATI9, wait for first Revision, then IMEI, then FSN then OK
    rsp = target.send("/usr/bin/microcom /dev/ttyAT\r\n")
    target.send("ATI9\r\n")
    rsp = target.expect_in_order(["Revision", "IMEI", "FSN", "OK"], 10)
    swilog.info("Receive: %s" % rsp)
    target.sendcontrol("x")


def L_MY_TEST_0001(target):
    """Test AT port of the target.

    target is an object received by the test function to communicate
    with the target.
    """
    # Print a message
    swilog.info("This is my test")
    # Send AT command. Expect OK. Timeout of 1s
    target.run_at_cmd("AT", 1)

    # Send AT+CPIN? command. Expect  +CPIN: READY, then OK
    target.run_at_cmd("AT+CPIN?", 1, [r"\+CPIN: READY\r", "OK\r"])

    # Send AT+CPIN=530 command. Expect ERROR
    rsp = target.run_at_cmd("AT+CPIN=530", 1, ["ERROR"])
    # print the content of the received data
    swilog.info("Receive %s" % rsp)

    # target.run_at_cmd uses low level functions: send + expect.
    # They can be used to control
    # what to send and what to receive.
    # Send ATI9, wait for IMEI-SV
    rsp = target.send("/usr/bin/microcom /dev/ttyAT \r\n")
    target.send("ATI9\r\n")
    # expect will find patterns in a list and return which pattern it has found
    rsp = target.expect([pexpect.TIMEOUT, r"IMEI.SV: "], 10)
    if rsp == 0:
        # Found the first pattern (pexpect.TIMEOUT)
        swilog.error("Timeout")
    elif rsp == 1:
        # Found the second element: "IMEI-SV: "
        # Now get the IMEI-SV
        target.expect([pexpect.TIMEOUT, r"\d+\r"], 10)
        # target.at.before is the content of the received data before the found regexp
        # target.at.after is the content of the regexp
        swilog.info("IMEI SV is %s" % target.after.strip())
        # get the end of the command
        target.expect(["OK"], 10)

    # Expect some patterns in a list (in order of the list)
    # Send ATI9, wait for first atSwi, then UBOOT, then Apps and then OK
    target.send("ATI9\r")
    rsp = target.expect_in_order([r"IMEI.SV", "OK"], 10)
    swilog.info("Receive: %s" % rsp)
    target.sendcontrol("x")
    target.run("cm info")
