"""Target fixtures.

Use the pytest_target pytest plugin to communicate with targets.
"""
import pytest

from pytest_letp.lib import com
from pytest_letp.lib import modules

__copyright__ = "Copyright (C) Sierra Wireless Inc."


# This fixture is used it to communicate with the target, to get
# informations (target_ip, ...) or to do actions specific to the target.
# @{
@pytest.fixture(scope="function")
def target(request, read_config):
    """Fixture to communicate with the target.

    .. note::
        Configuration done in target.xml

    :param request: request fixture
    :param read_config: xml configuration

    :returns:: instance of the created module

    The target fixture is the way to communicate with the target.

    .. image:: /../doc/img/target_aggregation.png

    It gathers all the communication links to the target
    which are ssh and serial links to the Linux console or
    to AT commands. They can be configured in config/target.xml in target.xml are:

    The 3 main default links are:
        - target.ssh. If it is the main link by default. \
            Access to the Linux console by ssh.
        - target.slink1. Serial link 1 Access to the Linux console \
        by the serial port (UART). Another way to call it is configured in \
        config/target.xml ("module/slink1/desc"). By default it is "uart_cli". \
        So target.slink1.run is equivalent to target.uart_cli.run. \
        - target.slink2. Serial link 2 Access to the AT commands (UART, tty ACM...) \
        Another way to call it is configured in config/target.xml \
        ("module/slink2/desc"). By default it is "at". So target.slink2.run \
        is equivalent to target.at.run_at_command.

    They can be configured in config/target.xml.

    2 other ssh links can be added dynamically from fixtures during a test:

        - target.ssh2. This link is activated if the ssh2 fixture is used.
        - target.logread. This link is activated if the logread fixture is used.


    Functions

    .. note::
        If not specified, all these functions can be applied to all
        the communication links (ssh/slink1/slink2):
        For example, it is possible to call target.expect which is by default
        the same as calling target.ssh.expect.
        But it is possible to expect some data on the other links:
        target.slink1.expect or target.slink2.expect

    Functions to send/receive data

    .. note::
        Most of the functions are based on the pexpect library.
        See `the Pexpect documentation <https://pexpect.readthedocs.io/en/stable/>`_

    - :py:func:`target.run <lib.ssh_linux.target_ssh_qct.run>` : \
        Send a command and wait for the prompt

    - :py:func:`target.run_at_cmd <lib.com.target_at.run_at_cmd>` : \
        Send an AT command and wait for "OK" by default.

    - target.send: Send raw data

    - target.sendline: Send raw data + new line

    - target.read: Read data

    - :py:func:`target.run <lib.ssh_linux.target_ssh_qct.expect>` : \
        Wait for one or more patterns. \
         Use target.before, target.after or target.match to get the found data \
        (see below target.expect examples).

    - :py:func:`target.expect_exact <lib.com.ttyspawn.expect_exact>`

    - target.expect_list

    - :py:func:`target.expect_in_order <lib.com.ttyspawn.expect_in_order>`

    - :py:func:`target.sendcontrol <lib.com.ttyspawn.sendcontrol>`

    - :py:func:`target.prompt <lib.com.ttyspawn.prompt>`

    Functions related to the reboot

    - :py:func:`target.reboot <lib.ssh_linux.target_ssh_qct.reboot>`

    - :py:func:`target.wait_for_reboot <lib.ssh_linux.target_ssh_qct.wait_for_reboot>`

    - :py:func:`target.wait_for_device_up \
                <lib.ssh_linux.target_ssh_qct.wait_for_device_up>`

    - :py:func:`target.wait_for_device_down \
        <lib.ssh_linux.target_ssh_qct.wait_for_device_down>`

    - :py:func:`target.reinit <lib.ssh_linux.target_ssh_qct.reinit>`

    - :py:func:`target.login <lib.ssh_linux.target_ssh_qct.login>`

    .. warning::
        Always use the reboot functions of LeTP
        instead of sending the "reboot" command.
        Indeed, the reboot function can use
        the serial link to prepare the target (iptables,
        get IP address...) to communicate with ssh.

    Functions related to board configuration (firewall, ...)

    - :py:func:`target.configure_eth <lib.modules_linux.ModuleLinux.configure_eth>`

    - :py:func:`target.configure_ecm <lib.modules_linux.ModuleLinux.configure_ecm>`

    - :py:func:`target.open_port <lib.modules_linux.ModuleLinux.open_port>`

    Functions to get info from the device

    - :py:func:`target.imei <lib.modules_linux.ModuleLinux.imei>`

    - :py:func:`target.fsn <lib.modules_linux.ModuleLinux.fsn>`

    - :py:func:`target.get_ip_addr <lib.modules_linux.ModuleLinux.get_ip_addr>`

    - :py:func:`target.get_info <lib.modules_linux.ModuleLinux.get_info>`

    - :py:func:`target.sim_iccid <lib.modules_linux.ModuleLinux.sim_iccid>`

    - :py:func:`target.sim_imsi <lib.modules_linux.ModuleLinux.sim_imsi>`

    - :py:func:`target.is_sim_absent <lib.modules_linux.ModuleLinux.is_sim_absent>`

    - :py:func:`target.is_sim_absent <lib.modules_linux.ModuleLinux.is_sim_absent>`
    """
    app = modules.define_target(request, read_config, "module")
    yield app
    app.teardown()


@pytest.fixture(scope="function")
def target2(request, read_config):
    """Fixture to communicate with a second target.

    .. note::
        Configuration done in target2.xml

    :param request: request fixture
    :param read_config: xml configuration

    :returns: instance of the created module

    To control a second target. It is exactly the same as the
    pytest_target.target  Set the second target value parameters
    in the file config/target2.xml.
    It has the same interface as the target object.

    .. code-block:: python

        def test_two_targets(target, target2):
            # simple test that sends external commands to 2 targets
            # Fill target.xml for the first target and target2.xml for the second
            swilog.step("Get legato version on first target")
            target.run("ls")
            target.run("legato version")

            swilog.step("Get legato version on second target")
            target2.run("ls")
            target2.run("legato version")

            swilog.step("Reboot the targets")
            target2.reboot()
            target.reboot()
    """
    app = modules.define_target(request, read_config, "target2")
    yield app
    app.teardown()


@pytest.fixture(scope="function")
def target_at(request, read_config):
    """Fixture to communicate with AT commands on a UART.

    .. note::
        Configuration done in target.xml

    :param request: request fixture
    :param read_config: xml configuration

    :returns: instance of the created module
    """
    slink1_name = read_config.findtext("module/slink1/name")
    if slink1_name == "":
        request.raiseerror("Slink1 not set")
    slink1_d = read_config.get("SLINK1_DEV_NAME")
    if slink1_d is None or slink1_d["value"] == "":
        request.raiseerror("Target not set")
    slink1 = slink1_d["value"]
    baudrate1 = read_config.findtext("module/slink1/speed")
    slink1 = com.target_serial_at(
        dev_tty=slink1_name, baudrate=int(baudrate1), target_name="AT", target_ip=None
    )
    return slink1


# @}
