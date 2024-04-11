"""Controller for external equipment."""
import os
import sys
import time

import pexpect
import pexpect.fdpexpect

from pytest_letp.lib import com
from pytest_letp.lib import swilog
from pytest_letp.lib import com_port_detector


__copyright__ = "Copyright (C) Sierra Wireless Inc."

available_ctrl = {}


def register(name, ctrl_class):
    """Register controller classes."""
    available_ctrl[name] = ctrl_class


def get_ctrl():
    """Get available controllers."""
    return available_ctrl


class controller:  # noqa: N801
    """Controller base class."""

    def __init__(self, config):
        self.config = config
        self.ip = config.findtext("network/ip")
        # SSH, telnet, ...
        self.ip_protocol = config.findtext("network/protocol")
        self.com_port = config.findtext("com/port")
        self.com_baudrate = config.findtext("com/speed")
        if self.com_baudrate is not None:
            self.com_baudrate = int(self.com_baudrate)
        # If the controller controls multiple instances (i.e relays from 0 to 8)
        self.port_nb = config.findtext("port_nb")
        if self.port_nb != "":
            self.port_nb = int(self.port_nb)
        self.username = config.findtext("username")
        self.password = config.findtext("password")
        self.inverted = int(config.findtext("inverted"))
        self.ssh = None
        self.telnet = None
        self.serial = None
        self.ip_port = config.findtext("network/port")
        self._com_port_checklist = {}
        self._com_port_info = None
        if self.ip is not None and self.ip_protocol.upper() == "SSH":
            self.ssh = com.pxsshext(  # pylint:disable=no-member
                "controller",
                self.ip,
                self.ip_port,
                fd_uart=None,
                logfile=sys.stdout,
                options={
                    "StrictHostKeyChecking": "no",
                    "UserKnownHostsFile": "/dev/null",
                    "ServerAliveInterval": "5",
                    "ServerAliveCountMax": "1",
                },
            )
        elif self.ip is not None and self.ip_protocol.upper() == "TELNET":
            swilog.debug(f"telnet {self.ip} {self.ip_port}")
            self.telnet = pexpect.spawn(
                f"telnet {self.ip} {self.ip_port}", logfile=sys.stdout
            )
        if self.autoconfig:
            port_detector = com_port_detector.ComPortDetector(
                self.com_port_checklist, self.com_port_info
            )
            self.com_port = port_detector.get_com_port(com.ComPortType.RELAY.name)
        if self.com_port is not None and self.com_port != "":
            self.serial = com.target_serial_at.open(self.com_port, self.com_baudrate)

    @property
    def autoconfig(self):
        """Port is set for autoconfiguration."""
        com_config = self.config.find("com")
        if not com_config:
            return False
        autoconf = com_config.get("autoconf")
        return autoconf is not None and autoconf == "1"

    @property
    def com_port_info(self):
        """Check for com port info."""
        if not self._com_port_info:
            self._com_port_info = com.ComPortInfo()
        return self._com_port_info

    @property
    def com_port_checklist(self):
        """Return the information to check different type of com port."""
        return self._com_port_checklist


class power_supply(controller):  # noqa: N801
    """Power supply base class."""

    def reset(self):  # noqa
        """Reset power supply."""
        assert 0, "Not implemented"

    def set_levels(self, voltage, current):  # noqa
        """Set power supply levels."""
        assert 0, "Not implemented"

    def off(self, nb=-1):  # noqa
        """Set power supply off."""
        assert 0, "Not implemented"

    def on(self, nb=-1):  # noqa
        """Set power supply on."""
        assert 0, "Not implemented"

    def state(self, nb=-1):  # noqa
        """Read power supply state."""
        assert 0, "Not implemented"

    def cycle(self, nb=-1, delay=2):
        """Cycle power supply."""
        self.off(nb)
        time.sleep(delay)
        self.on(nb)


class RelayPort:
    """Relay port class."""

    def __init__(self, config, io):
        self.io = io
        assert self.io is not None, "No serial or telnet ports opened"
        self.inverted = config.get("inverted") == "1"
        if config.get("debounce") is not None:
            self.debounce = int(config.get("debounce"))
        else:
            self.debounce = 0
        self.port_nb = int(config.text)
        self.object = "relay"
        self.on_cmd = "on"
        self.off_cmd = "off"
        self.read_cmd = "read"

    def __on(self):
        """Set port on."""
        swilog.debug(f"numato {self.object} {self.port_nb} on")
        self.io.send(f"{self.object} {self.on_cmd} {self.port_nb}\r")
        self.io.expect(">", 5)
        time.sleep(self.debounce / 1000)
        swilog.debug(self.io.before)
        swilog.debug(self.io.after)

    def __off(self):
        """Set port off."""
        swilog.debug(f"numato {self.object} {self.port_nb} off")
        self.io.send(f"{self.object} {self.off_cmd} {self.port_nb}\r")
        self.io.expect(">", 5)
        time.sleep(self.debounce / 1000)
        swilog.debug(self.io.before)
        swilog.debug(self.io.after)

    def on(self):  # noqa: D402
        """Set port on (if inverted relay off else relay on)."""
        if self.inverted:
            self.__off()
        else:
            self.__on()

    def off(self):  # noqa: D402
        """Set port off (if inverted relay on else relay off)."""
        if self.inverted:
            self.__on()
        else:
            self.__off()

    def state(self):
        """Read port state."""
        com.clear_buffer(self.io)
        self.io.send(f"{self.object} {self.read_cmd} {self.port_nb}\r")
        self.io.expect(">", 5)
        expected_on_state = "on" if not self.inverted else "off"
        return "on" if expected_on_state in self.io.before else "off"

    def cycle(self, delay=2):
        """Cycle port."""
        self.off()
        time.sleep(delay)
        self.on()

    def set_debounce(self, debounce):
        """Set debounce, debounce unit is ms."""
        self.debounce = debounce

    def get_debounce(self):
        """Get debounce, debounce unit is ms."""
        return self.debounce


class GPIOPort(RelayPort):
    """Relay GPIO port class."""

    def __init__(self, config, io):
        super().__init__(config, io)
        self.object = "gpio"
        self.on_cmd = "set"
        self.off_cmd = "clear"

    def state(self):
        """Cannot get state of gpio."""
        assert 0, "Not implemented"


class numato(power_supply):  # noqa: N801
    """Numato relay class."""

    def __init__(self, config):
        swilog.debug("Init the numato relay")
        super().__init__(config)
        self.io = self.serial if self.serial is not None else self.telnet
        assert self.io is not None, "No serial or telnet ports opened"
        self.io.send("\r")
        self.__map_ports(config)

    @property
    def com_port_checklist(self):
        """Return the information to check different type of com port."""
        cmd = "relay read 0"
        if os.name == "posix":
            cmd = f"\r\n{cmd}"
        super().com_port_checklist[com.ComPortType.RELAY.name] = [
            (cmd, r"relay read 0\n\r(on|off)\n\r>")
        ]
        return super().com_port_checklist

    @property
    def com_port_info(self):
        """Initialize com port description."""
        if not self._com_port_info:
            self._com_port_info = com.ComPortInfo()
        self._com_port_info.add_port(
            com.ComPortType.RELAY.name, ["Numato", "USB Serial Device"]
        )
        return self._com_port_info

    @staticmethod
    def __get_ports(config):
        """Get list of ports from config."""
        ports = config.find("ports")
        if ports:
            return ports
        return []

    def __map_ports(self, config):
        """Map ports from config to class attributes."""
        for port in self.__get_ports(config):
            setattr(self, port.tag, RelayPort(port, self.io))
        gpio_config = config.find("gpio")
        if gpio_config and gpio_config.get("used") == "1":
            for port in self.__get_ports(gpio_config):
                setattr(self, port.tag, GPIOPort(port, self.io))

    def reset(self):
        """Reset relay."""
        swilog.debug("Reset the numato relay")
        self.io.send("reset\r")
        self.io.expect(">", 5)
        swilog.debug(self.io.before)
        swilog.debug(self.io.after)

    def __on(self, nb=-1):
        """Set relay on."""
        if nb == -1:
            nb = self.port_nb
        swilog.debug(f"numato relay {nb} on")
        self.io.send(f"relay on {nb}\r")
        self.io.expect(">", 5)
        swilog.debug(self.io.before)
        swilog.debug(self.io.after)

    def __off(self, nb=-1):
        """Set relay off."""
        if nb == -1:
            nb = self.port_nb
        swilog.debug(f"numato relay {nb} off")
        self.io.send(f"relay off {nb}\r")
        self.io.expect(">", 5)
        swilog.debug(self.io.before)
        swilog.debug(self.io.after)

    def on(self, nb=-1):  # noqa: D402
        """Set port on (if inverted relay off else relay on)."""
        if self.inverted:
            self.__off(nb)
        else:
            self.__on(nb)

    def off(self, nb=-1):  # noqa: D402
        """Set port off (if inverted relay on else relay off)."""
        if self.inverted:
            self.__on(nb)
        else:
            self.__off(nb)

    def state(self, nb=-1):  # noqa: D402
        """Read port state."""
        com.clear_buffer(self.io)
        if nb == -1:
            nb = self.port_nb
        self.io.send(f"relay read {nb}\r")
        self.io.expect(">", 5)
        expected_on_state = "on" if not self.inverted else "off"
        return "on" if expected_on_state in self.io.before else "off"
