# pylint: skip-file
# Reenable pylint after error fixes.
"""!@package com Communication links (ssh + serial link)."""
import os
import sys
import time
import stat
import termios
import socket
import struct
import fcntl
import re
from enum import Enum
import colorama
import swilog
import pexpect
import pexpect.fdpexpect
import pexpect.pxssh
from com_exceptions import ComException

__copyright__ = "Copyright (C) Sierra Wireless Inc."


PROMPT_swi_qct = "root@.+:.+#"
LOGIN_swi_qct = "[^ ]+ login:"

# Some constant for termios
TIOCMGET = getattr(termios, "TIOCMGET", 0x5415)
TIOCMBIS = getattr(termios, "TIOCMBIS", 0x5416)
TIOCMBIC = getattr(termios, "TIOCMBIC", 0x5417)
TIOCM_CAR = getattr(termios, "TIOCM_CAR", 0x040)
TIOCM_RNG = getattr(termios, "TIOCM_RNG", 0x080)
TIOCM_CD = getattr(termios, "TIOCM_CD", TIOCM_CAR)
TIOCM_RI = getattr(termios, "TIOCM_RI", TIOCM_RNG)
TIOCM_DTR = getattr(termios, "TIOCM_DTR", 0x002)
TIOCM_RTS = getattr(termios, "TIOCM_RTS", 0x004)
TIOCM_CTS = getattr(termios, "TIOCM_CTS", 0x020)
TIOCM_DSR = getattr(termios, "TIOCM_DSR", 0x100)
TIOCM_zero_str = struct.pack("I", 0)
TIOCM_DTR_str = struct.pack("L", TIOCM_DTR)


# Size of the pexpect maxread
PEXPECT_MAXREAD = 2000

# Terminal size to avoid \n after 80 characters
TTY_SIZE = 500


class ComPortType(Enum):
    """Different types of port."""

    CLI = 1
    AT = 2


class ComPort:
    """Store com port information."""

    def __init__(
        self,
        name=ComPortType.CLI.name,
        desc="Sierra Wireless WP7603",
        baudrate=115200,
        usb_interface=None,
    ):
        """Initialize the com port information."""
        self.name = name
        self.desc = desc
        self.baudrate = baudrate
        self.usb_interface = usb_interface

    def update_usb_interface(self, usb_interface):
        """Update the usb interface of the ComPort."""
        if usb_interface and re.match(
            r"[0-9]+-[0-9]+(\.[0-9]+)*:[0-9]+(\.[0-9]+)?", usb_interface
        ):
            self.usb_interface = usb_interface
        else:
            swilog.warning("%s is an invalid usb interface" % usb_interface)


class ComPortInfo:
    """Store static com port information mapping."""

    def __init__(self):
        """Initialize the com port mapping dictionary."""
        self.port_info_mapping = {}

    def __getitem__(self, name):
        """Implement evaluation of self.port_info_mapping[key]."""
        return self.port_info_mapping.get(name)

    def add_port(self, name, desc, baudrate=115200):
        """Add description in the com port mapping dictionary."""
        self.port_info_mapping[name] = ComPort(name, desc, baudrate)

    def remove_port(self, name):
        """Remove description in the com port mapping dictionary."""
        if name in self.port_info_mapping:
            del self.port_info_mapping[name]


class ComPortDevice:
    """Provide the information about the com port device."""

    def __init__(self, name):
        """Initialize ComPortDevice."""
        self.name = name
        self.dev_tty_regx = r"(?P<dev_tty>/dev/tty[A-Z]+[0-9]+)"
        self.tty_regx = r"(?P<tty>tty[A-Z]+[0-9]+)"
        self.usb_interface_regx = (
            r"(?P<usb_interface>[0-9]+-[0-9]+(\.[0-9]+)*:[0-9]+(\.[0-9]+)*)"
        )
        self.usb_id_regx = r"(?P<usb_id>[0-9]+-[0-9]+(\.[0-9]+)*)"

    @property
    def name(self):
        """Return the device name."""
        return self._name

    @name.setter
    def name(self, name):
        """Set the device name."""
        if name and os.path.exists(name):
            name = os.path.realpath(name)

        self._name = name

    def is_dev_tty(self):
        """Check if the name follows /dev/ttyxx device format."""
        if self.name:
            if os.path.exists(self.name) and re.search(self.dev_tty_regx, self.name):
                return True

        return False

    def is_tty(self):
        """Check if the name follows ttyxx device format."""
        if self.name and re.search(self.tty_regx, self.name):
            return True

        return False

    def is_usb_interface(self):
        """Check if the name follows usb interface format."""
        if self.name and re.match(self.usb_interface_regx, self.name):
            return True

        return False

    def is_usb_id(self):
        """Check if the name follows usb id format."""
        if self.name and re.match(self.usb_id_regx, self.name):
            return True

        return False

    def get_dev_tty(self):
        """Get the corresponding /dev/ttyUSBxx based on the usb interface."""
        if not self.name:
            return None

        if self.is_dev_tty():
            return self.name
        elif self.is_usb_interface():
            if self.wait_for_usb_dev():
                for _, dirs, _ in os.walk(self.get_device_path()):
                    for item in dirs:
                        self.name = item
                        if self.is_tty():
                            return "/dev/%s" % item

        return None

    def get_usb_interface(self):
        """Get the corresponding usb interface based on the "/dev/ttyUSBxx"."""
        if not self.name:
            return None

        if self.is_usb_interface():
            return self.name
        elif self.is_dev_tty():
            if self.wait_for_usb_dev():
                tty = re.search(self.tty_regx, self.name).group("tty")
                dir_name = "/sys/class/tty/%s" % tty
                rsp = os.path.realpath(dir_name)
                match_obj = re.search(self.usb_interface_regx, rsp)

                if match_obj:
                    return match_obj.group("usb_interface")

        return None

    def get_device_path(self):
        """Return the system file path of the device."""
        if self.is_usb_id():
            return "/sys/bus/usb/devices/{}".format(self.name)
        elif self.is_usb_interface():
            usb_id = re.search(self.usb_id_regx, self.name).group("usb_id")
            return "/sys/bus/usb/devices/{}/{}".format(usb_id, self.name)
        elif self.is_dev_tty():
            return self.name

        return None

    def wait_for_usb_dev(self, timeout=300):
        """Wait for usb device to show up in sys fs."""
        time_elapsed = time.time()
        end_time = time.time() + timeout

        if not self.name:
            return False

        while time_elapsed <= end_time:
            swilog.info("Waiting for USB device {} to be up...".format(self.name))
            dev_path = self.get_device_path()

            if not dev_path:
                swilog.warning("Don't know how to check if {} is up".format(self.name))
                return True

            if os.path.exists(dev_path):
                swilog.info("USB device {} is present!".format(self.name))
                return True

            time.sleep(1)
            time_elapsed = time.time()

        return False


def clear_buffer(target):
    """Clear target buffer."""
    while not target.expect([r".+", pexpect.TIMEOUT], timeout=0.001):
        target.match.group(0)


def run_at_cmd_and_check(
    target, at_cmd, timeout=20, expect_rsp=None, check=True, eol="\r"
):
    r"""Run and check AT commands.

    - If no expected responses, it waits for OK or ERROR.
      ERROR or TIMEOUT cause an assertion.
    - If the list of responses is not void, then it waits for each pattern
      in the order declared in the list.
      TIMEOUT is raised if not all the patterns are found.

    Args:
    target: target fixture
    at_cmd: AT command. Add \r if \r not in the command.
             Use target.send to send command without \r.
    timeout: timeout in seconds
    expect_rsp: List of expected pattern to catch.
                 ex. [r"\+WDSI: 1", r"\+WDSI: 6"] or
                     ["ERROR"] if the command must failed.
    check: If True, AssertionError if command error or timeout.
            If True and command error or timeout, return None
    eol: Specify the end of lince character.
          Default \r but in le_at_GetTextAsync the \r is not valid and it must be \x1a

    return: all the data saved during this command

    Raises:
        AssertionError (only if check is True)
    @ingroup targetGroup
    """
    # Clear target buffer before running command.
    clear_buffer(target)
    raw_cmd = at_cmd.replace("\r", "").replace("\n", "")
    at_cmd = at_cmd + eol if eol not in at_cmd else at_cmd
    swilog.debug("Send %s" % list(at_cmd))
    target.send(at_cmd)
    try:
        if not expect_rsp:
            regex_ok = r"(?P<rsp>.*OK)"
            regex_error = r"(?P<rsp>.*ERROR)"
            # Regex to search for the command + rsp + OK.
            # This is to avoid matching to previous command responses in the buffer.
            # Linux targets do not have the command echoed in AT port, this is for rtos.
            regex_ok_with_cmd = r"({}\s){}".format(re.escape(raw_cmd), regex_ok)

            rsp = target.expect(
                [
                    regex_ok_with_cmd,
                    regex_ok,
                    regex_error,
                    pexpect.TIMEOUT,
                    pexpect.EOF,
                ],
                timeout=timeout,
            )
            assert rsp != 2, "Command %s error" % raw_cmd
            assert rsp != 3, "Command %s timeout. Received:\n%s" % (
                raw_cmd,
                list(target.before),
            )
            assert rsp in (0, 1, 4), "No answer from command %s. Received:\n%s" % (
                raw_cmd,
                list(target.before),
            )
            return target.match.group("rsp")
        else:
            buf = ""
            for expect_pattern in expect_rsp:
                rsp = target.expect([pexpect.TIMEOUT, expect_pattern], timeout=timeout)
                if rsp == 0:
                    swilog.debug(
                        "Did not received %s. Received: \n%s"
                        % (expect_pattern, list(target.before))
                    )
                    assert 0, "timeout from command %s" % raw_cmd
                buf += target.before
                if isinstance(target.after, str):
                    buf += target.after
            return buf
    except Exception as e:
        if check:
            raise ComException(
                "{} didn't return after {} is sent".format(expect_rsp, at_cmd)
            )
        if getattr(target, "before"):
            swilog.debug("Received:\n%s" % list(target.before))
        return None


def setup_linux_login(target):
    """Handle login nagger for linux."""
    status = target.expect([pexpect.TIMEOUT, target.PROMPT, "Do nothing"], timeout=1)
    if status == 0:
        target.sendline("")
        status = target.expect(
            [pexpect.TIMEOUT, target.PROMPT, "Do nothing", "Setup password"], timeout=1
        )
    if status == 0:
        # Just in case it is in Microcom
        target.sendcontrol("x")
        # Just in case it is in an application
        target.sendcontrol("c")
        # Just in case it is rebooting, wait a little
        time.sleep(10)
    if status == 2:
        # Login nagger detected, disabling
        target.sendline("3")
        target.expect("Would you like a reminder next time you log in")
        target.sendline("n")
        target.expect("OK")
        target.prompt()
    elif status == 3:
        # Login nagger detected, disabling
        target.sendline("2")
        # Setting an empty root password
        target.expect("New password:")
        target.sendline("")
        target.expect("Warning: weak password")
        target.sendline("")
        target.expect("Re-enter new password")
        target.sendline("")
        target.expect("Disable console access")
        target.sendline("n")
        target.prompt()
        # Remove the root password
        target.sendline("sed -i 's/^root:[^:]*/root:/gi' /etc/shadow")
        target.prompt()

    return status != 0


class TTYLog:
    """Log interface that sends logs to stdout and swilog."""

    def __init__(self, direction=None, wait_for_newline=False):
        self.buf = ""
        self.direction = direction
        self.wait_for_newline = wait_for_newline

    def write(self, s):
        """Write to stdout."""
        out = s
        if self.direction == "OUT":
            out = "%s%s%s" % (colorama.Fore.CYAN, s, colorama.Style.RESET_ALL)
        sys.stdout.write(out)
        self.buf += s.replace("\r", "")

    def flush(self):
        """Flush log."""
        sys.stdout.flush()
        if self.wait_for_newline and "\n" not in self.buf:
            return
        lines = self.buf.split("\n")
        for i in range(len(lines) - 1):
            self._log_line(lines[i])
        self.buf = lines[len(lines) - 1]

    def _log_line(self, line):
        if self.direction:
            line = "[%s] %s" % (self.direction, line)
        swilog.trace(line)


class ttyspawn(pexpect.fdpexpect.fdspawn):
    """Wrap fdPExpect to hold reference to file object."""

    def __init__(self, fd=None, **kwargs):
        # Hold a reference so file object is not garbage collected
        self.fd = fd
        encoding = "utf-8" if sys.version_info[0] == 3 else None
        super(ttyspawn, self).__init__(
            fd,
            maxread=PEXPECT_MAXREAD,
            encoding=encoding,
            codec_errors="replace",
            **kwargs
        )
        self.config_logging()

    def config_logging(self):
        """Fdspawn will use those logfiles."""
        self.logfile_read = TTYLog("IN", False)
        self.logfile_send = TTYLog("OUT", True)

    # Ubuntu 14.04 does not have __enter__ and __exit__ in pexpect, so define
    # them here.
    def __enter__(self):
        try:
            return super(ttyspawn, self).__enter__()
        except AttributeError:
            return self

    def __exit__(self, etype, evalue, tb):
        try:
            super(ttyspawn, self).__exit__(etype, evalue, tb)
        except AttributeError:
            pass

    def prompt(self, timeout=-1):
        """Read the console prompt.

        Args:
            timeout: timeout in second

        Returns:
            True if the shell prompt was matched, False if the timeout was
                 reached.
        @ingroup targetGroup
        """
        i = self.expect([self.PROMPT, pexpect.TIMEOUT], timeout=timeout)
        return i == 0

    def sendcontrol(self, char):
        r"""Send control is not available with fdspawn, only with pxssh.

        Take it from ptyprocess.
        Helper method that wraps send() with mnemonic access for
        sending control character to the child (such as Ctrl-C or Ctrl-D).
        For example, to send Ctrl-G (ASCII 7, bell, '\a')::

            child.sendcontrol('g')

        See also, sendintr() and sendeof().

        Args:
            char: character to associate with control

        @ingroup targetGroup
        """
        char = char.lower()
        a = ord(char)
        if 97 <= a <= 122:
            a = a - ord("a") + 1
            return self.send(chr(a))
        d = {
            "@": 0,
            "`": 0,
            "[": 27,
            "{": 27,
            "\\": 28,
            "|": 28,
            "]": 29,
            "}": 29,
            "^": 30,
            "~": 30,
            "_": 31,
            "?": 127,
        }
        if char not in d:
            return 0
        return self.send(chr(d[char]))

    def expect(self, *args, **kwargs):
        """Intermediate function to expect.

        Avoid too much backtraces.
        """
        try:
            return super(ttyspawn, self).expect(*args, **kwargs)
        except Exception as e:
            raise ComException(e)

    def expect_exact(self, *args, **kwargs):
        """Intermediate function to expect_exact.

        Avoid too much backtraces.
        """
        try:
            return super(ttyspawn, self).expect_exact(*args, **kwargs)
        except Exception as e:
            raise ComException(e)

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

    def close(self):
        """Close the fd."""
        try:
            os.close(self.fd)
            super().close()
        except OSError as e:
            swilog.debug(e)


class SerialPort:
    """Class providing serial port configuration."""

    # Available baud rates.
    BAUD = {
        9600: termios.B9600,
        19200: termios.B19200,
        38400: termios.B38400,
        57600: termios.B57600,
        115200: termios.B115200,
        230400: termios.B230400,
        460800: termios.B460800,
        # Linux baudrates bits missing in termios module included below
        500000: 0x1005,
        576000: 0x1006,
        921600: 0x1007,
        1000000: 0x1008,
        1152000: 0x1009,
        1500000: 0x100A,
        2000000: 0x100B,
        2500000: 0x100C,
        3000000: 0x100D,
        3500000: 0x100E,
        4000000: 0x100F,
    }

    # TTY attribute fields.
    IFLAG = 0
    OFLAG = 1
    CFLAG = 2
    LFLAG = 3
    ISPEED = 4
    OSPEED = 5
    CC = 6

    @staticmethod
    def open(device, baudrate=None, rtscts=False):
        """Open a serial port.

        @param  device      Device name.
        @param  baudrate    Initial baud rate to set.  Defaults to port's default.

        @return Port instance, or None if device not found.
        """
        port = None
        device_stat = None

        if not device:
            return None

        try:
            device_stat = os.stat(device)
        except OSError:
            pass

        if device_stat and stat.S_ISCHR(device_stat.st_mode):
            port = SerialPort(device, baudrate, rtscts)
        return port

    def __init__(self, device, baudrate, rtscts=False):
        """Instantiate serial port wrapper.

        @param  device      Device name.
        @param  baudrate    Initial baud rate to set.
                            Defaults to port's default if None.
        """
        self._device = device
        self._baudrate = None
        swilog.debug("Init of %s" % str(self._device))
        device_stat = None
        try:
            device_stat = os.stat(device)
        except OSError:
            pass
        if self._device and stat.S_ISCHR(device_stat.st_mode):
            self.fd = os.open(self._device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        else:
            assert 0, "%s not a valid port" % self._device
        self._tty_attr = termios.tcgetattr(self.fd)
        self._tty_attr[self.IFLAG] = termios.IGNBRK
        self._tty_attr[self.OFLAG] = 0
        self._tty_attr[self.LFLAG] = 0
        self._tty_attr[self.CC] = [0] * 32
        if not baudrate:
            self._tty_attr[self.CFLAG] = termios.CS8 | (
                self._tty_attr[self.CFLAG] & termios.CBAUD
            )
        else:
            self._tty_attr[self.CFLAG] = termios.CS8 | self.BAUD[baudrate]
            self._tty_attr[self.ISPEED] = self._tty_attr[self.OSPEED] = self.BAUD[
                baudrate
            ]
        # Enable receiver, ignore modem control lines
        self._tty_attr[self.CFLAG] |= termios.CREAD | termios.CLOCAL
        # Flow control
        if rtscts:
            swilog.debug("Hardware flow control is activated")
            self._tty_attr[self.CFLAG] |= termios.CRTSCTS
        else:
            self._tty_attr[self.CFLAG] &= ~termios.CRTSCTS
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self._tty_attr)
        self._tty_attr = termios.tcgetattr(self.fd)

        if not baudrate:
            baud_value = self._tty_attr[self.CFLAG] & termios.CBAUD
            for b, v in self.BAUD.items():
                if v == baud_value:
                    baudrate = b
                    break
        self._baudrate = baudrate
        assert self._baudrate in self.BAUD

    def flush(self):
        """Flush serial port input and output buffers."""
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def close(self):
        """Close the opened fd."""
        if hasattr(self, "fd"):
            try:
                os.close(self.fd)
            except Exception as e:
                swilog.debug(e)

    @property
    def baudrate(self):
        """Get current baud rate.

        @return Current baud rate.
        """
        return self._baudrate

    @baudrate.setter
    def baudrate(self, baudrate):
        """Change the baud rate.

        @param  baudrate    New baud rate to set.
        """
        self._baudrate = baudrate
        swilog.debug("Set baudrate of %s to %d" % (self._device, baudrate))
        # Get tty attributes
        (iflag, oflag, cflag, lflag, _, _, cc) = termios.tcgetattr(self.fd)

        # Modify tty attributes
        cflag &= ~(termios.CBAUD | termios.CBAUDEX)
        cflag |= self.BAUD[baudrate]
        ispeed = self.BAUD[baudrate]
        ospeed = self.BAUD[baudrate]

        # Set tty attributes
        termios.tcsetattr(
            self.fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
        )
        self.flush()
        time.sleep(0.1)

    def __repr__(self):
        """Get printable representation of port.

        @return Port string representation.
        """
        return "SerialPort<{0} @ {1} | {2}>".format(
            self._device, self.baudrate, self.fd
        )


class CommandFailedException(Exception):
    """Command failed exception."""


class target_qct:
    """Wrap fdPExpect to hold reference to file object."""

    def __init__(self, dev_tty=None, baudrate=115200, **kwargs):
        self.PROMPT = PROMPT_swi_qct
        self.LOGIN = LOGIN_swi_qct
        self.dev_tty = dev_tty

        swilog.debug("Serial init %s %s" % (dev_tty, baudrate))
        self.target = self

    def prompt(self, timeout=-1, retry=2):
        """Check for target_qct prompt."""
        i = self.expect([self.PROMPT, pexpect.TIMEOUT], timeout=timeout)
        if i == 1:
            if retry > 0:
                # Try to send a new line to see if we get a prompt, in case
                # of spurious messages that might have polluted the previous prompt.
                self.sendline("\n")
                return self.prompt(timeout=2, retry=(retry - 1))
            else:
                return False
        return True

    def _read_exit_code(self, timeout, retry=2):
        self.sendline('echo "\n$?"')
        self.expect(["\n\d+\r\n", pexpect.TIMEOUT], timeout)
        if self.after == pexpect.TIMEOUT:
            _exit = 1
            exit_s = "Timeout"
            return (_exit, exit_s)
        # Search for "\n0" exactly
        _exit = 0 if "\n0" in self.after else 1
        exit_s = self.after.replace("\n", "").replace("\r", "")
        if _exit != 0 and not re.match(r"^\d+", exit_s) and (retry > 0):
            return self._read_exit_code(timeout, retry=(retry - 1))
        return (_exit, exit_s)

    def run_main(
        self, cmd, timeout=-1, local_echo=True, withexitstatus=False, check=True
    ):
        """Run a command. Check the command and assert by default.

        :cmd: command to execute
        :timeout: timeout of the command in second
        :local_echo: read the echo of the command before
        :withexitstatus: return the exit status with the response in a tuple (exit, rsp)
        :check: If False do not assert if the command exit status is not 0
        :return: stdout/stderr of the command or a tuple (exit, stdout/stderr of the command) if withexitstatus is set
        """
        clear_buffer(self)
        self.sendline(cmd)
        rsp = ""
        if local_echo:
            # Try to read the command first
            try:
                # Read local echo
                self.expect(cmd, 0.5)
            except Exception:
                swilog.debug("No local echo received %s: %s" % (cmd, list(self.before)))
                # The command is not exactly received as expected.
                # Add the data to the future self.expect()
                rsp += self.before
        if not self.prompt(timeout=timeout):
            raise ComException("Unable to get prompt after %ss" % timeout)
        rsp += self.before

        # Get the command exit code
        if withexitstatus or check:
            exit_code, exit_s = self._read_exit_code(timeout)
            if withexitstatus:
                return (exit_code, rsp)
            if check and exit_code != 0:
                msg = "Command '%s' failed with exit code '%s'" % (cmd, exit_s)
                raise CommandFailedException(msg)
        return rsp.strip("\r\n")

    def run(self, cmd, timeout=-1, local_echo=True, withexitstatus=False, check=True):
        """Intermediate function to run.

        Avoid too much backtraces.
        """
        try:
            return self.run_main(cmd, timeout, local_echo, withexitstatus, check)
        except Exception as e:
            raise ComException(e)

    def login(self, attempts=10):
        """Login to target cli."""
        for _ in range(attempts):
            swilog.info("send root")
            self.sendline("root")
            if setup_linux_login(target=self):
                break
        for _ in range(attempts):
            if self.run("stty columns %d" % TTY_SIZE, withexitstatus=1)[0] == 0:
                return
        assert False, "Impossible to send command stty to target"

    def reboot(self, timeout=60, login=True):
        self.sendline("reboot")
        self.wait_for_reboot(timeout, login)

    def wait_for_reboot(self, timeout=60, login=True):
        assert self.wait_for_device_down(timeout=timeout) == 0
        assert self.wait_for_device_up(timeout=timeout) == 0, "No login after reboot"
        if login:
            self.login()

    def reinit(self):
        """Reinit target connection."""
        self.login()

    def wait_for_device_up(self, timeout):
        """Wait for promp or login."""
        clear_buffer(self)
        swilog.debug("wait for up")
        self.sendline("")
        status = self.expect([pexpect.TIMEOUT, self.LOGIN, self.PROMPT], timeout)
        return 0 if status == 1 or status == 2 else 1

    def wait_for_device_down(self, timeout):
        """Wait for device down.

        Keep sending line until prompt is not found.
        """
        clear_buffer(self)
        swilog.debug("wait for down")
        sleep_time = 2
        for _ in range(0, timeout, sleep_time):
            self.sendline("")
            status = self.expect([pexpect.TIMEOUT, self.LOGIN, self.PROMPT], sleep_time)
            if status == 0:
                return 0
            time.sleep(sleep_time)
        return 1

    def wait_for_device(self, down, timeout=60):
        if down:
            self.wait_for_device_down(timeout)
        else:
            self.wait_for_device_up(timeout)


class target_serial_qct(target_qct, ttyspawn):
    """Wrap fdPExpect to hold reference to file object."""

    @staticmethod
    def open(dev_tty=None, baudrate=115200, rtscts=False, **kwargs):
        """Open a serial port."""
        return target_serial_qct(dev_tty, baudrate, rtscts, **kwargs)

    def __init__(self, dev_tty=None, baudrate=115200, rtscts=False, **kwargs):
        self.tty = SerialPort.open(dev_tty, baudrate, rtscts=rtscts)
        if not self.tty:
            swilog.warning(
                "Unable to open tty %s baudrate[%d] rtscts[%s]"
                % (dev_tty, baudrate, rtscts)
            )
            return
        ttyspawn.__init__(self, fd=self.tty.fd, **kwargs)
        target_qct.__init__(self, dev_tty=dev_tty, baudrate=baudrate, **kwargs)


class target_telnet_qct(target_qct):
    def __init__(self, telnet_ip=None, telnet_port=None, **kwargs):
        self.PROMPT = PROMPT_swi_qct
        self.LOGIN = LOGIN_swi_qct
        self.target_ip = telnet_ip
        self.telnet_ip = telnet_ip
        self.telnet_port = telnet_port
        super(target_telnet_qct, self).__init__(**kwargs)
        encoding = "utf-8" if sys.version_info[0] == 3 else None
        self.telnet = pexpect.spawn(
            "telnet %s %s" % (self.telnet_ip, self.telnet_port),
            encoding=encoding,
            codec_errors="replace",
        )
        self.telnet.logfile_read = TTYLog("IN", False)
        self.telnet.logfile_send = TTYLog("OUT", True)
        self.expect = self.telnet.expect
        self.send = self.telnet.send
        self.sendline = self.telnet.sendline
        self.linesep = self.telnet.linesep
        self.sendcontrol = self.telnet.sendcontrol

    @property
    def before(self):
        """Wrap telnet.before."""
        return self.telnet.before

    @property
    def after(self):
        """Wrap telnet.after."""
        return self.telnet.after

    @property
    def match(self):
        """Wrap telnet.match."""
        return self.telnet.match

    def close(self):
        """Wrap telnet.close."""
        self.telnet.close()

    def __del__(self):
        """Close port."""
        self.telnet.close()


class target_at:
    """class to send AT commands.

    @ingroup target_serial_at
    """

    def __init__(self, dev_tty=None, baudrate=115200):
        self.PROMPT = ["OK", "ERROR"]
        self.LOGIN = ""

    def prompt(self, timeout=-1):
        """Check for target_at prompt."""
        return self.expect(self.PROMPT + [pexpect.TIMEOUT], timeout)

    def run(self, cmd, timeout=-1):
        """Run command on target_at."""
        self.send(cmd + "\r")
        self.expect(self.PROMPT, timeout)
        return self.before + self.after

    def login(self):
        """Login to target_at."""

    def reboot(self, timeout=60, power_supply=None, cmd="AT+CFUN=1,1\r"):
        """Reboot target via target_at."""
        if not power_supply:
            self.send(cmd)
            assert self.prompt(timeout) == 0
        else:
            power_supply.cycle()

    def run_at_cmd(self, at_cmd, timeout=20, expect_rsp=None, check=True, eol="\r"):
        """Run an AT command on the target.

        It waits for "OK" by default.
        """
        try:
            rsp = run_at_cmd_and_check(self, at_cmd, timeout, expect_rsp, check, eol)
        except Exception as e:
            # Try/except to limit the backtrace
            raise ComException(e)
        return rsp


class target_serial_at(target_at, ttyspawn):
    """
    @defgroup target_serial_at Serial AT management

    class to manage an uart to send AT commands, based on pexpect
    """

    @staticmethod
    def open(dev_tty=None, baudrate=115200, rtscts=False, **kwargs):
        """Open a serial port."""
        return target_serial_at(dev_tty, baudrate, rtscts, **kwargs)

    def __init__(self, dev_tty=None, baudrate=115200, rtscts=False, **kwargs):
        self.dev_tty = dev_tty
        self.rtscts = rtscts
        self.save_kwargs = kwargs
        self.tty = SerialPort.open(dev_tty, baudrate, rtscts=rtscts)

        if self.tty:
            ttyspawn.__init__(self, fd=self.tty.fd, **kwargs)
            target_at.__init__(self, dev_tty, baudrate)
        else:
            swilog.warning("AT port %s is inaccessible at the moment" % dev_tty)

    @property
    def baudrate(self):
        """Get current baud rate of the serial interface.

        Returns:
            Current baud rate.

        Examples:
            >>> swilog.info("The actual baudrate is %s" % target.at.baudrate)
            'The actual baudrate is 115200'

        @ingroup targetGroup
        """
        return self.tty.baudrate

    @baudrate.setter
    def baudrate(self, baudrate):
        """Change the baud rate of the serial interface.

        Args:
            baudrate: New baud rate to set.

        Examples:
            >>> target.at.baudrate = 115200

        @ingroup targetGroup
        """
        self.tty.baudrate = baudrate

    def reinit(self, baudrate=None):
        """Reinit target connection."""
        bd = baudrate if baudrate else self.baudrate
        self.tty = SerialPort.open(self.dev_tty, bd, rtscts=self.rtscts)
        if not self.tty:
            raise ComException(
                "Unable to open tty %s baudrate[%d] rtscts[%s]"
                % (self.dev_tty, bd, self.rtscts)
            )
        ttyspawn.__init__(self, fd=self.tty.fd, **self.save_kwargs)
        target_at.__init__(self, self.dev_tty, bd)

    def set_dtr(self, state):
        """Set terminal status line: Data Terminal Ready.

        @ingroup targetGroup
        """
        if state:
            fcntl.ioctl(self.fd, TIOCMBIS, TIOCM_DTR_str)
        else:
            fcntl.ioctl(self.fd, TIOCMBIC, TIOCM_DTR_str)

    @property
    def cts(self):
        """Read terminal status line: Clear To Send.

        @ingroup targetGroup
        """
        s = fcntl.ioctl(self.tty.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack("I", s)[0] & TIOCM_CTS != 0

    @property
    def dsr(self):
        """Read terminal status line: Data Set Ready.

        @ingroup targetGroup
        """
        s = fcntl.ioctl(self.tty.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack("I", s)[0] & TIOCM_DSR != 0

    @property
    def ri(self):
        """Read terminal status line: Ring Indicator.

        @ingroup targetGroup
        """
        s = fcntl.ioctl(self.tty.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack("I", s)[0] & TIOCM_RI != 0

    @property
    def cd(self):
        """Read terminal status line: Carrier Detect.

        @ingroup targetGroup
        """
        s = fcntl.ioctl(self.tty.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack("I", s)[0] & TIOCM_CD != 0


class target_telnet_at(target_at):
    """Wrap fdPExpect to hold reference to file object.

    AT port.
    """

    def __init__(self, telnet_ip=None, telnet_port=None, **kwargs):
        self.telnet_ip = telnet_ip
        self.telnet_port = telnet_port
        super(target_telnet_at, self).__init__(**kwargs)
        encoding = "utf-8" if sys.version_info[0] == 3 else None
        self.telnet = pexpect.spawn(
            "telnet %s %s" % (self.telnet_ip, self.telnet_port),
            encoding=encoding,
            codec_errors="replace",
        )
        self.telnet.logfile_read = TTYLog("IN", False)
        self.telnet.logfile_send = TTYLog("OUT", True)
        self.expect = self.telnet.expect
        self.send = self.telnet.send
        self.sendline = self.telnet.sendline
        self.linesep = self.telnet.linesep

    @property
    def before(self):
        """Wrap telnet.before."""
        return self.telnet.before

    @property
    def after(self):
        """Wrap telnet.after."""
        return self.telnet.after

    @property
    def match(self):
        """Wrap telnet.match."""
        return self.telnet.match

    def close(self):
        """Wrap telnet.close."""
        self.telnet.close()

    def __del__(self):
        """Close port."""
        self.telnet.close()


class target_ssh_qct(pexpect.pxssh.pxssh):
    """class to connect with ssh based on pexpect.

    @defgroup target_ssh SSH management
    """

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
        self.PROMPT = PROMPT_swi_qct
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
        """Login to the embedded Linux console.

        @ingroup targetGroup
        """
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
            if not setup_linux_login(self):
                raise ComException("Unable to login")
        exit_code = 1
        count = 0
        while exit_code != 0:
            exit_code, rsp = self.run("stty columns %d" % TTY_SIZE, withexitstatus=1)
            count += 1
            assert count != 5, "Impossible to send command stty to target"

    def expect(self, *args, **kwargs):
        """Expect function from the pexpect library.

        Avoid too much backtraces.

        @ingroup targetGroup

        Send a command and expect some patterns (reg exp)
        with target.expect (list of regexp to wait),
        target.expect_exact (list of exact patterns to wait) or
        target.expect_in_order (wait patterns in the order of the list).
        If the expected pattern is found,
        target.before are the data before the pattern.
        target.after is the found pattern.

        ~~~~~~~~~~~~~{.py}
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
        ~~~~~~~~~~~~~
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

        :cmd: command to execute
        :timeout: timeout of the command in second
        :local_echo: read the echo of the command before
        :withexitstatus: return the exit status with the response in a tuple (exit, rsp)
        :check: If False do not assert if the command exit status is not 0
        :return: stdout/stderr of the command or a tuple
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
        """Run a command, check the exit status by default and returns the
        response.

        @param cmd: command to execute
        @param timeout: timeout of the command in second
        @param local_echo: read the echo of the command before
        @param withexitstatus: return the exit status with the
        @param response in a tuple (exit, rsp)
        @param check: If False do not assert if the command exit status is not 0

        @Returns stdout/stderr of the command or a tuple (exit, stdout/stderr of
            the command) if withexitstatus is set

        @ingroup targetGroup

        ~~~~~~~~~~~~~{.py}
        # Test if "PASSED" is in the logs
        rsp = target.run("/sbin/logread")
        assert "PASSED" in rsp, "test returned [FAILED]"
        # Check that the exit status of the command is not 0. Use withexitstatus.
        exit, rsp = target.run(" [ -e %s ]" % (testFilePath), withexitstatus=True)
        assert exit != 0, "[FAILED] file is created after the write operation"
        ~~~~~~~~~~~~~
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
        @ingroup targetGroup
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
        """Wait for ssh connection to be up.

        @ingroup targetGroup
        """
        swilog.debug("wait for up (over ssh)")
        return self.wait_for_device(down=False, timeout=timeout)

    def wait_for_device_down(self, timeout):
        """Wait for ssh connection to be down.

        @ingroup targetGroup
        """
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
        @ingroup targetGroup
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
        @ingroup targetGroup
        """
        assert self.wait_for_device_down(timeout) == 0, "No shutdown of the target"
        assert self.wait_for_device_up(timeout) == 0, "Device was not started"
        self.reinit()

    def reinit(self):
        """Link reconnection (for example after a reboot).

        @ingroup targetGroup
        """
        if self.reinit_in_progress:
            raise ComException("A reinit is already in progress")
        self.reinit_in_progress = True
        swilog.debug("Reinit the ssh connection with %s" % (self.target_ip))
        self.pid = None
        swilog.debug("%s %s" % (self.target_ip, self.ssh_port))
        self.__init__(
            self.target_ip,
            self.ssh_port,
            self.config_target,
            *self.save_args,
            **self.save_kwargs
        )
        self.PROMPT = PROMPT_swi_qct
        time.sleep(2)
        self.login()
        self.reinit_in_progress = False

    def check_communication(self, timeout=1):
        """Check that is possible to connect with the communication link.

        Args:
            timeout: timeout in second
        @ingroup targetGroup
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

        @ingroup targetGroup
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
