"""@package LinuxVersions.

Set of functions that retrieve the linux platform's versions using
either legato command line or AT command from the module
"""
import re
from pytest_letp.lib import com
from pytest_letp.lib.versions import TargetVersions


class LinuxVersions(TargetVersions):
    """Provide the subclass of TargetVersions for Linux platform."""

    def __init__(self):
        """Initialize linux versions.

        Set regex patterns:
        - full: regex to match full version line.
        - parsed: regex to match image tag version.
        """
        super().__init__()
        self.linux_cmd = {
            com.ComPortType.CLI: "cat /etc/legato/version",
            com.ComPortType.AT: "ATI8",
        }
        self.modem_cmd = {com.ComPortType.CLI: "cm info", com.ComPortType.AT: "ATI9"}

    def get(self, full=True, target=None):
        """Get version object dictionary."""
        return {
            "legato": self.get_legato_version(full=full, target=target),
            "linux": self.get_linux_version(full=full, target=target),
            "firmware": self.get_modem_version(full=full, target=target),
        }

    def get_version(self, cmd, pattern, console, full=True, target=None):
        """Override get_version to login prior to check."""
        if console == com.ComPortType.CLI:
            target.login()
        return super().get_version(cmd, pattern, console, full, target)

    def get_linux_version(self, console=com.ComPortType.CLI, full=True, target=None):
        """Return the linux version.

        e.g. SWI9X07H_00.02.21.00 / LXSWI2.5-13.0
        """
        return self.get_version(
            cmd=self.linux_cmd,
            pattern=target.linux_pattern,
            console=console,
            full=full,
            target=target,
        )

    def parse_linux(self, version, target):
        """Return parsed linux version."""
        match_obj = re.search(target.modem_pattern["parsed"], version)
        return self._match_version(match_obj)
