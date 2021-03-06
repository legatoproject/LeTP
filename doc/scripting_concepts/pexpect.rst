.. _pexpect_libraries:

###############
Pexpect library
###############

`Pexpect <https://pexpect.readthedocs.io/en/stable/>`_  is a pure Python module for spawning child applications;
controlling them; and responding to expected patterns in their output.It is used to open the ssh and serial links, and is also handy to control host processes instead of subprocess.
The pexpect library is natively integrated in LeTP an used for the communication link over ssh and the serial ports. But it is also possible to use it to send commands on host in the same manner of subprocess or os.popen.

.. note::

    When using pexpect to send commands on host\,
    do not use it with redirect, pipe, or wild cards (\>, \|, or \*).


Running a command
-------------------
.. code-block:: python

    # Run a command on host
    rsp = pexpect.run("/usr/local/apache/bin/apachectl start")

    # With the exit status
    rsp, exit = pexpect.run("ifconfig", withexitstatus=1)
    assert exit == 0, "the command failed"

Command interaction
--------------------

Here is an example with a FTP connection::

    # FTP connection
    import pexpect
    child = pexpect.spawn ('ftp ftp.openbsd.org')
    child.expect ('Name .*: ')
    child.sendline ('anonymous')
    child.expect ('Password:')
    child.sendline ('noah@example.com')
    child.expect ('ftp> ')
    child.sendline ('ls /pub/OpenBSD/')
    child.expect ('ftp> ')
    print child.before   # Print the result of the ls command.
    child.interact()     # Give control of the child to the user.

Or for entering a password::

    # Get exit status
    (command_output, exitstatus) = run('ls -l /bin', withexitstatus=1)
    # these commands
    from pexpect import *
    child = pexpect.spawn('scp foo user@example.com:.')
    child.expect('(?i)password')
    child.sendline(mypassword)
    # are equivalents to :
    pexpect.run('scp foo user@example.com:.', events={'(?i)password': mypassword})

Using quotes (\") in commands
-----------------------------

When using ", it is recommended to use raw strings (r"My string") and to use \\ before ": r"/bin/grep -q \"string 123\""::

    if legato.ssh_to_target(r" cat %s | /bin/grep -q \"string 123\"" % (testFilePath))!= 0:
        print("[PASSED] the atomicity of le_atomFile_OpenStream is guaranteed once the process acquires the file lock")
    else:
        assert 0, "\[FAILED\] the atomicity of le_atomFile_OpenStream isn't guaranteed once the process acquires the file lock"
    target.run_at_cmd

Regular expressions with pexpect
--------------------------------

The patterns in the expected pattern list are Python regular expressions. Escape all the special Python characters if needed. Typically replace "+" by "\\+" ("+WDSI: 1" by "\\+WDSI: 1")::

    # Run AT+WDSS=1,0 with 1s timeout. Wait for OK, ERROR or timeout
    target.run_at_cmd("at+wdss=1,0", 1)
    # Run at+wdss=1,1 with 20s timeout. Wait for \+WDSI: 6 first, and then \+WDSI: 23,1, or timeout
    target.run_at_cmd("at+wdss=1,1", 20, ["\+WDSI: 6", "\+WDSI: 23,1"])
    # Check that "\+WDSI: 3 is in the response
    rsp = target.run_at_cmd("at+wdsr=3", 10, ["\+WDSI: 18,100", "\+WDSI: 10"])
    assert "\+WDSI: 3" in rsp
    # By default, assert if timeout or ERROR. To not assert, used try/except or the parameter check=False
    rsp = target.run_at_cmd("AT+NOTHING\r\n", 1, check=False)
    if rsp is None:
    # Command returned error
    # Control the end of the command. By default, add \r at the end of command. Do nothing if \r is already present in the command string.
    # Here send \r\n
    target.run_at_cmd("AT\r\n", 1)

    # To completely control what you send and what you receive with the AT commands, you can use target.at.send and target.at.expect (same as target.slink2.send and target.slink2.expect)
    target.at.send("ATI\r")
    rsp = target.at.expect(["\r\nOK\r\n", "ERROR", pexpect.TIMEOUT],
                                    timeout)
    assert rsp is not 1, "Command error"
    assert rsp is 0, "Command timeout. Received:\n%s" % list(target.before)
    target.sendcontrol
    target.sendcontrol('x')            => send ctrl-x on target
    target.slink1.sendcontrol('x')     => send ctrl-c on target.slink1
    target.read

    Read data.
    target.read(size=-1)

