# pylint: skip-file
"""SSH communictaion link for linux environment."""
import sys
import re
import time
import socket
import pexpect.pxssh
from pytest_letp.lib import swilog
from pytest_letp.lib.com import (
    TTYLog,
    setup_linux_login,
    CommandFailedException,
    QctAttr,
)
from pytest_letp.lib.com_exceptions import ComException


__copyright__ = "Copyright (C) Sierra Wireless Inc."

# Size of the pexpect maxread
PEXPECT_MAXREAD = 2000


class target_ssh_qct(pexpect.pxssh.pxssh):
    """Class to connect with ssh based on pexpect."""

    def __init__(self, target_ip, ssh_port, config_target, *args, **kwargs):
        self.target_ip = target_ip
        self.ssh_port = int(ssh_port)
        self.config_target = config_target

        ssh_opts_dict = kwargs.get("options", {})
        self.ssh_opts = ""
        for option in ssh_opts_dict:
            ssh_opt = "-o %s=%s " % (option, ssh_opts_dict[option])
            self.ssh_opts += ssh_opt
        self.ssh_opts = self.ssh_opts.strip()

        self.save_args = args
        self.save_kwargs = kwargs
        encoding = "utf-8" if sys.version_info[0] == 3 else None
        super(target_ssh_qct, self).__init__(
            *args,
            maxread=PEXPECT_MAXREAD,
            encoding=encoding,
            codec_errors="replace",
            **kwargs
        )
        self.logfile_read = TTYLog("IN", False)
        self.logfile_send = TTYLog("OUT", True)
        self.PROMPT = QctAttr().prompt
        self.target = self
        self.reinit_in_progress = False

    def prompt(self, timeout=-1):
        """Check for target_ssh_qct prompt."""
        i = self.expect([self.PROMPT, pexpect.TIMEOUT], timeout=timeout)
        if i == 1:
            # Try to send a new line to see if we get a prompt, in case
            # of spurious messages that might have polluted the previous prompt.
            self.sendline("\r\n\r\n\r\n")
            i = self.expect([self.PROMPT, pexpect.TIMEOUT], timeout=0.5)
            if i == 1:
                return False
        return True

    def login(self, timeout=90):
        """Login to the embedded Linux console."""
        delay = 10
        count = int(timeout / delay)
        while self.check_communication() != 0:
            count -= 1
            if count <= 0:
                swilog.error("No communication with the target after %ds.", timeout)
                break
            swilog.warning(
                "No communication with the target. Trying again in %ds.", delay
            )
            time.sleep(delay)
        try:
            super(target_ssh_qct, self).login(
                self.target_ip, "root", auto_prompt_reset=False, port=self.ssh_port
            )
            setup_linux_login(self)
        except Exception as inst:
            swilog.debug(inst)
            if not setup_linux_login(self):
                raise ComException("Unable to login")
        exit_code = 1
        count = 0
        while exit_code != 0:
            exit_code, rsp = self.run(
                "stty columns {}".format(QctAttr().tty_size), withexitstatus=1
            )
            count += 1
            assert count != 5, "Impossible to send command stty to target"

    def expect(self, *args, **kwargs):
        r"""Expect function from the pexpect library.

        Avoid too much backtraces.

        Send a command and expect some patterns (reg exp)
        with target.expect (list of regexp to wait),
        target.expect_exact (list of exact patterns to wait) or
        target.expect_in_order (wait patterns in the order of the list).
        If the expected pattern is found,
        target.before are the data before the pattern.
        target.after is the found pattern.

        .. code-block:: python

            # Timeout of 60s
            APP_TIMEOUT = 60

            # Start the application
            target.send("app start %s\r" % APP_NAME)

            # Wait for "Failures: \d+" or timeout
            id = target.expect([pexpect.TIMEOUT, "Failures: \d+"], APP_TIMEOUT)

            # if id == 0, it is a timeout
            # if id == 1, "Failures: \d+" was found
            assert id == 1, "Timeout received!"
            # Check there is 0 failure in the response
            assert "Failures: 0" in target.after, "Some tests failed!"

            target.sendline("ls \/")
            # Wait for "data", then "bin", "boot", and at the end "var"
            rsp = target.expect_in_order(["data", "bin", "boot", "var"], 10)

        """
        try:
            return super(target_ssh_qct, self).expect(*args, **kwargs)
        except (EOFError, pexpect.EOF):
            swilog.warning("EOF received")
            timeout = 60
            assert self.wait_for_device_up(timeout) == 0, "Device was not started"
            self.reinit()
            # Retry, not protected this time
            return super(target_ssh_qct, self).expect(*args, **kwargs)
        except Exception as e:
            swilog.warning(e)

            if self.closed:
                raise ComException("Connection to the device is lost")

    def _read_exit_code(self, timeout, retry=2):
        """Read exit code."""
        self.sendline('echo "\n$?"')
        self.expect([r"\n\d+\r\n", pexpect.TIMEOUT], timeout)

        if self.after == pexpect.TIMEOUT:
            exit_code = 1
            exit_s = "Timeout"
            return (exit_code, exit_s)
        # Search for "\n0" exactly
        exit_code = 0 if "\n0" in self.after else 1
        exit_s = self.after.replace("\n", "").replace("\r", "")
        if exit_code != 0 and not re.match(r"^\d+", exit_s) and (retry > 0):
            return self._read_exit_code(timeout, retry=(retry - 1))
        return (exit_code, exit_s)

    def run_main(
        self, cmd, timeout=-1, local_echo=True, withexitstatus=False, check=True
    ):
        """Run a command. Check the command and assert by default.

        :param cmd: command to execute
        :param timeout: timeout of the command in second
        :param local_echo: read the echo of the command before
        :param withexitstatus: return the exit status with the response
                               in a tuple (exit, rsp)
        :param check: If False do not assert if the command exit status is not 0

        :returns: stdout/stderr of the command or a tuple
                 (exit, stdout/stderr of the command) if withexitstatus is set
        """
        # Sometimes, when using send, sendline or expect, there is stuff in the buffer
        # Flush it. Cleaning self.buffer does not seem to work. So expect characters.
        while not self.expect([r".+", pexpect.TIMEOUT], timeout=0.1):
            if not self.match:
                break
            self.match.group(0)

        self.sendline(cmd)
        rsp = ""

        if local_echo:
            # Try to read the command first
            try:
                # Read local echo
                self.expect("\n", 5)
            except Exception:
                swilog.debug("No local echo received %s: %s" % (cmd, list(self.before)))
                # The command is not exactly received as expected.
                # Add the data to the future self.expect()
                rsp += self.before
        try:
            if not self.prompt(timeout=timeout):
                raise ComException("Unable to get ssh prompt")
            rsp += self.before

            if withexitstatus or check:
                exit_code, exit_s = self._read_exit_code(timeout)
                if withexitstatus:
                    return (exit_code, rsp)
                if check and exit_code != 0:
                    msg = "Command '%s' failed with exit code '%s'" % (cmd, exit_s)
                    raise CommandFailedException(msg)
            return rsp.strip("\r\n")
        except Exception as inst:
            # Reboot command will stop communication
            if "reboot" not in cmd:
                if self.check_communication() != 0:
                    # Great chance that a reboot occured. reinit the ssh communication
                    swilog.error(
                        "communication error!!!. Was there an unexpected reboot?"
                    )
                    time.sleep(30)
                    self.reinit()
                    assert 0, (
                        "communication error!!!. Was there an unexpected reboot? %s"
                        % (inst)
                    )
                else:
                    raise ComException(
                        "Communication to the device is lost after reboot"
                    )

    def run(self, cmd, timeout=-1, local_echo=True, withexitstatus=False, check=True):
        r"""Run a command, check the exit status by default.

        and returns the response.

        :param cmd: command to execute
        :param timeout: timeout of the command in second
        :param local_echo: read the echo of the command before
        :param withexitstatus: return the exit status with the
        :param response: in a tuple (exit, rsp)
        :param check: If False do not assert if the command exit status is not 0

        :returns: stdout/stderr of the command or a tuple (exit, stdout/stderr of
                  the command) if withexitstatus is set


        .. code-block:: python

            # Test if "PASSED" is in the logs
            rsp = target.run("/sbin/logread")
            assert "PASSED" in rsp, "test returned [FAILED]"
            # Check that the exit status of the command is not 0. Use withexitstatus.
            exit, rsp = target.run(" [ -e %s ]" % (testFilePath), withexitstatus=True)
            assert exit != 0, "[FAILED] file is created after the write operation"

        """
        try:
            return self.run_main(cmd, timeout, local_echo, withexitstatus, check)
        except (EOFError, pexpect.EOF):
            swilog.warning("EOF received")
            assert self.wait_for_device_up(timeout) == 0, "Device was not started"
            self.reinit()
            # Retry, not protected this time
            return self.run_main(cmd, timeout, local_echo, withexitstatus, check)
        except Exception as e:
            swilog.warning(e)
            raise ComException("Unable to send the cmd {} through ssh link".format(cmd))

    def reboot(self, timeout=60, power_supply=None):
        """Reboot the device.

        Args:
            timeout: in second
            power_supply: power supply instance. Reboot with an external power supply
        """
        if not power_supply:
            # Don't know why the following commented line does not work....
            # self.sendline("/sbin/reboot -f")
            self.run("/sbin/reboot -f", 1, check=False)
            # os.system("ssh root@%s \"/sbin/reboot\"")
        self.close()
        if power_supply:
            power_supply.cycle()
        self.wait_for_reboot(timeout)

    def wait_for_device_up(self, timeout):
        """Wait for ssh connection to be up."""
        swilog.debug("wait for up (over ssh)")
        return self.wait_for_device(down=False, timeout=timeout)

    def wait_for_device_down(self, timeout):
        """Wait for ssh connection to be down."""
        swilog.debug("wait for down (over ssh)")
        return self.wait_for_device(down=True, timeout=timeout)

    def wait_for_device(self, down, timeout=60):
        """Wait for the device to be down or up.

        Args:
            down: True if the module is expected to shutdown,
               False if the module must start
            timeout: in second

        Returns:
            0 if timeout not reached
        """
        count = timeout
        expected_com = 1 if down else 0
        while self.check_communication(timeout=1) != expected_com and count != 0:
            # Sleep should be done only if expected_com == 1:
            # But seen that sometimes the socket does not wait 1 s (LETEST-1619)
            time.sleep(1)
            count -= 1
        return 1 if count == 0 else 0

    def wait_for_reboot(self, timeout=60):
        """Wait for a reboot of the target (by ssh).

        Args:
            timeout: timeout in seconds
        """
        assert self.wait_for_device_down(timeout) == 0, "No shutdown of the target"
        assert self.wait_for_device_up(timeout) == 0, "Device was not started"
        self.reinit()

    def reinit(self):
        """Link reconnection (for example after a reboot)."""
        if self.reinit_in_progress:
            raise ComException("A reinit is already in progress")
        self.reinit_in_progress = True
        swilog.debug("Reinit the ssh connection with %s" % (self.target_ip))
        swilog.debug("%s %s" % (self.target_ip, self.ssh_port))
        self.pid = None
        self.__init__(
            self.target_ip,
            self.ssh_port,
            self.config_target,
            *self.save_args,
            **self.save_kwargs
        )
        self.PROMPT = QctAttr().prompt
        time.sleep(2)
        self.login()
        self.reinit_in_progress = False

    def check_communication(self, timeout=1):
        """Check that is possible to connect with the communication link.

        Args:
            timeout: timeout in second
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        rsp = 1
        try:
            sock.connect((self.target_ip, self.ssh_port))
            data = sock.recv(64)
            sock.close()
            if not data or len(data) == 0:
                rsp = 1
            else:
                swilog.debug("Connected to %s %d" % (self.target_ip, self.ssh_port))
                rsp = 0
        except Exception:
            rsp = 1
        if rsp == 1:
            swilog.debug(
                "Impossible to connect to %s %d" % (self.target_ip, self.ssh_port)
            )
        return rsp

    def expect_in_order(self, expected_list, timeout=5):
        """Wait for patterns in a list in the order of the list.

        Assert if one pattern is not found.

        Args:
            expected_list: list of patterns to find.
            timeout: timeout to give at expect for every pattern

        Returns:
            Received data

        Raises:
            Assertion
        """
        data = ""
        for pattern in expected_list:
            i = self.expect([pexpect.TIMEOUT, pattern], timeout)
            assert i != 0, "Did not received %s. Received: \n%s" % (
                pattern,
                list(self.before),
            )
            data += self.before
            data += self.after
        return data
