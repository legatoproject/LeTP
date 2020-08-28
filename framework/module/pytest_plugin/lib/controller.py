# pylint: skip-file
# Reenable pylint after error fixes.
"""!@package controller The controller for external equipments."""
import sys
import time

import pexpect
import pexpect.fdpexpect
import pexpect.pxssh

import com
import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."

available_ctrl = {}


def register(name, ctrl_class):
    available_ctrl[name] = ctrl_class


def get_ctrl():
    return available_ctrl


class controller(object):
    def __init__(self, config):
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

        if self.ip is not None and self.ip_protocol.upper() == "SSH":
            self.ssh = com.pxsshext(
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
            swilog.debug("telnet %s %s" % (self.ip, self.ip_port))
            self.telnet = pexpect.spawn(
                "telnet %s %s" % (self.ip, self.ip_port), logfile=sys.stdout
            )
        if self.com_port is not None and self.com_port != "":
            self.serial = com.target_serial_at.open(self.com_port, self.com_baudrate)


class power_supply(controller):
    def __init__(self, config):
        super(power_supply, self).__init__(config)

    def reset(self):
        assert 0, "Not implemented"

    def set_levels(self, voltage, current):
        assert 0, "Not implemented"

    def off(self, nb=-1):
        """If nb == -1, the default port should be self.port_nb."""
        assert 0, "Not implemented"

    def on(self, nb=-1):
        """If nb == -1, the default port should be self.port_nb."""
        assert 0, "Not implemented"

    def state(self, nb=-1):
        """If nb == -1, the default port should be self.port_nb Return "on" or
        "off" depending on the state of the port."""
        assert 0, "Not implemented"

    def cycle(self, nb=-1, delay=2):
        self.off(nb)
        time.sleep(delay)
        self.on(nb)
