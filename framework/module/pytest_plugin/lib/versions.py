"""@package targetVersions.

Set of functions that retrieve the target's versions using
either legato command line or AT command from the module
"""
import re
import com
import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class TargetVersions:
    """Provide functionalities to retrieve different types of version.

    Such version can be retrieved by a CLI or AT cmd
    """

    def __init__(self):
        """Initialize target versions.

        Set regex patterns:
        - full: regex to match full version line.
        - parsed: regex to match image tag version.
        """
        self.legato_cmd = {
            com.ComPortType.CLI: "legato version",
            com.ComPortType.AT: "ATI8",
        }
        self.modem_cmd = {com.ComPortType.CLI: None, com.ComPortType.AT: "ATI"}

    def get(self, full=True, target=None):
        """Get version object dictionary."""
        return {
            "legato": self.get_legato_version(full=full, target=target),
            "firmware": self.get_modem_version(full=full, target=target),
        }

    @staticmethod
    def _match_version(match_obj):
        """Return matched version if matched."""
        version = match_obj.group("version").strip() if match_obj else None
        swilog.debug("version: {}".format(version))
        return version

    def parse_version_dict(self, version_dict, target=None):
        """Parse through version dictionary.

        Returns: version dictionary with full and parsed versions.
        """
        parsed_dict = {}
        for version_type, version in version_dict.items():
            parser = "parse_{}".format(version_type)
            parsed_dict[version_type] = getattr(self, parser)(version, target)
            parsed_dict[version_type + "_full"] = version
        return parsed_dict

    @staticmethod
    def get_version(cmd, pattern, console, full=True, target=None):
        """Return target version."""
        pattern = pattern["full"] if full else pattern["parsed"]
        cmd = cmd[console]

        if not cmd or not target:
            return None

        swilog.debug("command: {}".format(cmd))
        swilog.debug("console: {}".format(console))

        return target.get_version(cmd, pattern, console)

    def get_legato_version(self, console=com.ComPortType.CLI, full=True, target=None):
        """Return the legato version.

        e.g. 20.04.0
        """
        return self.get_version(
            cmd=self.legato_cmd,
            pattern=target.legato_pattern,
            console=console,
            full=full,
            target=target,
        )

    def parse_legato(self, version, target=None):
        """Return parsed legato version."""
        match_obj = re.search(target.legato_pattern["parsed"], version)
        return self._match_version(match_obj)

    def get_modem_version(self, target, console=com.ComPortType.AT, full=True):
        """Return the modem version.

        e.g. SWI9X07H_00.02.21.00
        """
        return self.get_version(
            cmd=self.modem_cmd,
            pattern=target.modem_pattern,
            console=console,
            full=full,
            target=target,
        )

    def parse_modem(self, version, target=None):
        """Return parsed modem version."""
        match_obj = re.search(target.modem_pattern["parsed"], version)
        return self._match_version(match_obj)

    def get_fw_image_pair(self, target=None):
        """Return the fw image pair: (current_fw, preferred_fw).

        current fw: the downloaded fw and it is currently running from
        the device(target) preferred fw: the downloaded fw in the device
        but it has not executed yet
        """
        current_fw_pattern = {
            "parsed": (
                r"current fw version:\s+"
                r"(?P<version>[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9])"
            )
        }

        preferred_fw_pattern = {
            "parsed": (
                r"preferred fw version:\s+"
                r"(?P<version>[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9])"
            )
        }

        cmd = {com.ComPortType.AT: "AT!IMPREF?"}

        return (
            self.get_version(
                cmd, current_fw_pattern, com.ComPortType.AT, False, target
            ),
            self.get_version(
                cmd, preferred_fw_pattern, com.ComPortType.AT, False, target
            ),
        )

    def is_fw_matched(self, target=None):
        """Return if the current fw is matched with the preferred fw."""
        current_fw, preferred_fw = self.get_fw_image_pair(target=target)

        return current_fw == preferred_fw
