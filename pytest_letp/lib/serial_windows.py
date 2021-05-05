# pylint: skip-file
"""Serial communication for Windows.

Reference the implementation from pexpect.fdpexpect.fdspawn.
"""

__copyright__ = "Copyright (C) Sierra Wireless Inc."

import serial
from pexpect.spawnbase import SpawnBase
from pytest_letp.lib.com_exceptions import ComException

__all__ = ["SerialSpawn"]


class SerialSpawn(SpawnBase):
    """Provide serial communication interraction."""

    def __init__(
        self,
        serial_com,
        args=None,
        timeout=30,
        maxread=2000,
        searchwindowsize=None,
        logfile=None,
        encoding=None,
        codec_errors="strict",
    ):

        if not isinstance(serial_com, serial.serialwin32.Serial):
            raise ComException("Passed-in invalid serial object")

        if not serial_com.isOpen():
            raise ComException("Serial port can not be opened")

        self.serial_com = serial_com
        self.args = None
        self.command = None
        SpawnBase.__init__(
            self,
            timeout,
            maxread,
            searchwindowsize,
            logfile,
            encoding=encoding,
            codec_errors=codec_errors,
        )
        self.own_fd = False
        self.closed = False
        self.name = "<serial port {}>".format(serial_com.port)

    def close(self):
        """Close the serial port.

        Calling this method a second time does nothing.
        """
        if not self.serial_com.isOpen():
            return

        self.flush()
        self.serial_com.close()
        self.closed = True

    def isalive(self):
        """Check if the serial port is still opened."""
        return self.serial_com.isOpen()

    def read_nonblocking(self, size=1, timeout=None):
        """Read from the serail port in non-blocking mode."""
        s = self.serial_com.read(size)
        s = self._decoder.decode(s, final=False)
        self._log(s, "read")
        return s

    def send(self, s):
        """Write to serial, return number of bytes written."""
        s = self._coerce_send_string(s)
        self._log(s, "send")

        b = self._encoder.encode(s, final=False)
        return self.serial_com.write(b)

    def sendline(self, s):
        """Send a string following by a newline."""
        s = self._coerce_send_string(s)
        return self.send(s + self.linesep)

    def write(self, s):
        """Write to serial, return None."""
        self.send(s)

    def writelines(self, sequence):
        """Call self.write() for each item in sequence."""
        for s in sequence:
            self.write(s)
