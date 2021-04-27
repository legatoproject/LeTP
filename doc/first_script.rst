########################
Creating test scripts
########################

To create a new test, knowing the concept of conftest.py and fixtures are prerequisites.
`Official documentation <https://docs.pytest.org/en/stable/fixture.html>`_

Testing is mainly performed by running specific commands on the target device, and then comparing the
received responses with the expected responses. This allows a thorough test coverage.

Communication to the device (ssh and serial links) are opened with pexpect. This allows the
test to run commands on the device and also compare the responses to the expected responses
using regex patterns. You can see examples for different connections on this page.

Below are some fundamental functionality that's helpful for basic test creation.
More information can be found in ``pytest_letp`` documentation.

Running Commands
================

Device connections
------------------
There are three main connections to test the target device. These are:
    1. CLI (Serial link 1)
    2. AT (Serial link 2)
    3. SSH (Secure Shell connection)

CLI
^^^
To send commands to the CLI port on the target device, ``target.slink1.run()`` or
``target.uart_cli.run()`` can both be used interchangeably. For example::

    swilog.step("Run 'time' cmd on slink1(CLI)")
    target.slink1.run("time\r\n")  # target.uart_cli.run("time\r\n") is also OK.

To test the response for a command, two other functions can be used. Note that
instead of "slink1", using "uart_cli" is also accepted. ::

    swilog.step("Run 'uname' cmd on slink1(CLI)")
    target.uart_cli.sendline("uname")
    target.uart_cli.expect("Linux", 5)  # Expects "Linux" to be returned for the previous command.

Since ``target.run()`` stores the response in a variable,
a good way to check the response is to use assertions with these variables. ::

    expected = "Linux"
    response = target.uart_cli.run("uname", 1)
    assert response == expected, "Expected response wasn't received!"

SSH
^^^
All the functions used with the CLI port can be used with SSH connection as well.
An important thing to keep in mind is that by default SSH is recognized as the main
communication link.

Calling ``target.expect`` is the same as calling ``target.ssh.expect``.
This is why the connection type needs to be specified for non-SSH connections. ::

    target.run(...) # Uses the SSH connection
    target.slink1.run(...) # Uses the CLI connection
    arget.slink2.run(...) # Uses the AT connection.

AT
^^
Many commands can be used on the AT port (slink2) as well. HOwever some commands and
their behaviour differ slightly.
To send a command, ``target.run_at_cmd`` is used. ::

    target.run_at_cmd("AT")

If not specified, ``run_at_cmd`` function expects "OK" as the response to the command.
This can be specified like this. ::

    target.run_at_cmd("AT+CPIN?", 1, [r"\+CPIN: READY\r", "OK\r"])

Above command runs ``AT+CPIN?``, and expects two responses; ``+CPIN: READY`` followed by
``OK``. For illustration:

.. image:: img/at+cpin.png

``target.run_at_cmd()`` function actually uses two low level functions: send + expect. ::

    target.send("AT+CPIN?")
    # Expect will find patterns in a list and return
    # the index of the pattern it has found
    response = target.expect([r"\+CPIN: READY\r", "OK\r"], 10)
    # If response == 0, +CPIN: READY was returned.
    # If response == 1, OK was returned.

To have more control over the returned responses, ``target.expect_in_order()`` can be used. ::

    # Send ATI9, wait for first Revision, then IMEI, then FSN then OK in order
    target.send("ATI9\r\n")
    response = target.expect_in_order(["Revision", "IMEI", "FSN", "OK"], 10)

Just like CLI, ``target.slink2.run()`` is equivalent to ``target.run_at_cmd()``

Other Target Functions
======================
Functions below can be used to control the target device as well as get information from it.

- :py:func:`target.reboot <lib.ssh_linux.target_ssh_qct.reboot>`

- :py:func:`target.wait_for_reboot <lib.ssh_linux.target_ssh_qct.wait_for_reboot>`

- :py:func:`target.wait_for_device_up <lib.ssh_linux.target_ssh_qct.wait_for_device_up>`

- :py:func:`target.wait_for_device_down <lib.ssh_linux.target_ssh_qct.wait_for_device_down>`

- :py:func:`target.imei <lib.modules_linux.ModuleLinux.imei>`

- :py:func:`target.fsn <lib.modules_linux.ModuleLinux.fsn>`

- :py:func:`target.get_ip_addr <lib.modules_linux.ModuleLinux.get_ip_addr>`

- :py:func:`target.get_info <lib.modules_linux.ModuleLinux.get_info>`

- :py:func:`target.sim_iccid <lib.modules_linux.ModuleLinux.sim_iccid>`

- :py:func:`target.sim_imsi <lib.modules_linux.ModuleLinux.sim_imsi>`

- :py:func:`target.is_sim_absent <lib.modules_linux.ModuleLinux.is_sim_absent>`















