"""CLI test samples.

Set of tests showing how to use the CLI commands interface
"""

# Log module
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


# ======================================================================
# Test functions
# ======================================================================
def test_CLI_connection(target):
    """Send CLI commands. Check for simple intermediate responses.

    Args:
        target: fixture to communicate with the target
    """
    # Print a message
    swilog.info("This is a CLI test")

    # Run command runs a command, checks the exit status and returns the response.
    # Run the command "cd", expect just a prompt as response
    target.uart_cli.run("cd")

    # Run the command "uname", return response "Linux", timeout set to 1
    rsp = target.uart_cli.run("uname", 1)
    assert rsp == "Linux", "Timeout received!"


def test_CLI_expect(target):
    """Send a CLI command and compare the output with the expected output.

    :param target: fixture to communicate with the target
    """
    # Expect command can be used to check the output of a previous command
    # and then compare it to an expected response.
    # Run the command "uname", expect the response "Linux", timeout set to 5 seconds
    # If expected response is not received within TIMEOUT, the test will fail.
    target.uart_cli.sendline("uname")
    target.uart_cli.expect("Linux", 5)


def test_CLI_expect_in_order(target):
    """Wait for a list of regexp patterns in the order of the list.

    :param target: fixture to communicate with the target
    """
    # Expect the response to match the order in the list.
    # Run "free", expect "Mem:" and "Swap:" in this order
    # Set timeout to 3 seconds
    target.uart_cli.sendline("free")
    target.uart_cli.expect_in_order(["Mem:", "Swap:"], 3)
    # assert rsp == 1, "Timeout received"

    # There can be gaps in the list
    target.uart_cli.sendline("ls /")
    # Wait for "data", then "bin", "boot", and at the end "var"
    target.uart_cli.expect_in_order(["bin", "boot", "data", "var"], 10)
