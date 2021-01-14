"""com port detector library."""
import os
import time

import pexpect
import serial.tools.list_ports

from pytest_letp.lib import com
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class ComPortDetector:
    """Auto-detect CLI and AT com ports.

    Limitation: unable to reliably detect com ports if
    multiple modules of the same type are connected to the same
    host.
    """

    def __init__(self, com_port_checklist, com_port_info):
        """Provide functionality to scan/detect AT and CLI com ports."""
        self.tty_session = None
        self.serial_port = None
        self.com_port_checklist = com_port_checklist
        self.com_port_info = com_port_info

    def _get_com_port_device_lst(self, com_port_name=com.ComPortType.CLI.name):
        """Iterate over the list of com port. Find possible matches based on.

        com_port_name. The look up order should be usb-interface (e.g. 5-2:1.3)

        -> com port description.

        Returns:
            A list of possible usb com port device name.
        """
        possible_devices_lst = []
        most_likely_dev_tty = None
        com_port_info = self.com_port_info[com_port_name]
        if not com_port_info:
            raise Exception("No description for port %s" % com_port_name)

        usb_interface = com_port_info.usb_interface
        com_port_device = com.ComPortDevice(usb_interface)

        if com_port_device.is_usb_interface():
            # Look up usb-interface
            most_likely_dev_tty = com_port_device.get_dev_tty()
            swilog.info(
                "%s is likely the %s port" % (most_likely_dev_tty, com_port_name)
            )

            if most_likely_dev_tty:
                possible_devices_lst.append(most_likely_dev_tty)

                return possible_devices_lst

        com_port_desc = com_port_info.desc
        if not com_port_desc:
            swilog.warning(
                "Unable to find the description of the port %s", com_port_name
            )
            return possible_devices_lst

        # Look up port description
        for port_obj in serial.tools.list_ports.comports():
            device = port_obj.device
            device_description = port_obj.description

            if com_port_desc in device_description:
                possible_devices_lst.append(device)

        return possible_devices_lst

    def _is_resp_expected(self, cmd, expect_pattern):
        """Check if the resp returned by the cmd is expected."""
        self.tty_session.send(cmd + "\r")
        expect_idx = self.tty_session.expect([expect_pattern, pexpect.TIMEOUT], 1)

        if expect_idx == 0:
            return True

        return False

    def _get_baudrate(self, com_port_name):
        baudrate = self.com_port_info[com_port_name].baudrate
        default_baudrate = 115200

        if not baudrate:
            swilog.warning(
                "Undefined baudrate for %s, so the default baudrate %d would be used"
                % (com_port_name, default_baudrate)
            )
            return default_baudrate  # the most common baudrate for swi modules

        return baudrate

    def open(self, port, baudrate=115200):
        """Open the specified port."""
        try:
            self.serial_port = com.SerialPort.open(port, baudrate)
            self.tty_session = com.ttyspawn(self.serial_port.fd)
        except:
            swilog.warning("Unable to open %s" % port)
            return False

        return True

    def close(self):
        """Close self.serial_port."""
        try:
            os.close(self.serial_port.fd)
        except:
            pass

    def identify_port(self, com_port_name=com.ComPortType.CLI.name):
        """Identify the port based on com_port_name and com_port_checklist."""
        if (
            com_port_name is not com.ComPortType.CLI.name
            and com_port_name is not com.ComPortType.AT.name
        ):
            swilog.error("Unknown port type!")
            return False

        if not self.com_port_checklist:
            return False

        checklist = self.com_port_checklist.get(com_port_name)

        if not checklist:
            return False

        for cmd, rsp in checklist:
            if not self._is_resp_expected(cmd, rsp):
                return False

        return True

    def get_com_port(self, com_port_name=com.ComPortType.CLI.name):
        """Iterate over a list of possible devices.

        Returns:
             The port corresponds to com_port_name.
        """
        max_retry = 6
        max_wait_time = 15
        possible_devices_lst = self._get_com_port_device_lst(com_port_name)

        for i in range(max_retry):
            swilog.info(
                "%d iteration to scan through all possible %s ports"
                % ((i + 1), com_port_name)
            )

            if len(possible_devices_lst) == 0:
                possible_devices_lst = self._get_com_port_device_lst(com_port_name)

            for usb_device_path in possible_devices_lst:
                has_port_found = False
                swilog.info(
                    "Try to open %s and see if it is a %s port"
                    % (usb_device_path, com_port_name)
                )

                baudrate = self._get_baudrate(com_port_name)
                if self.open(usb_device_path, baudrate):
                    has_port_found = self.identify_port(com_port_name)
                self.close()

                if has_port_found:
                    swilog.info("%s is the %s port!" % (usb_device_path, com_port_name))
                    com_port_device = com.ComPortDevice(usb_device_path)
                    self.com_port_info[com_port_name].update_usb_interface(
                        com_port_device.get_usb_interface()
                    )
                    return usb_device_path

            swilog.info("Wait for %d seconds before the next retry..." % max_wait_time)
            time.sleep(max_wait_time)

        return None
