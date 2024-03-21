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
            raise Exception(f"No description for port {com_port_name}")

        usb_interface = com_port_info.usb_interface
        com_port_device = com.ComPortDevice(usb_interface)

        if com_port_device.is_usb_interface():
            # Look up usb-interface
            most_likely_dev_tty = com_port_device.get_dev_tty()
            swilog.info(f"{most_likely_dev_tty} is likely the {com_port_name} port")

            if most_likely_dev_tty:
                possible_devices_lst.append(most_likely_dev_tty)

                return possible_devices_lst

        com_port_desc_list = com_port_info.desc

        # Check if the list has valid parameters
        if com_port_desc_list is None or len(com_port_desc_list) < 1:
            swilog.warning(
                "Unable to find the description list of the port %s", com_port_name
            )
            return possible_devices_lst
        elif not isinstance(com_port_desc_list, list):
            raise Exception(f"Unknown description list type for port {com_port_name}")

        # Try and find the device description from com port list
        for port_obj in serial.tools.list_ports.comports():
            device = port_obj.device
            device_description = port_obj.description

            # Iterate through the com_port_desc_list
            for com_port_desc in com_port_desc_list:
                if com_port_desc is None or type(com_port_desc) is not type(
                    device_description
                ):
                    swilog.warning(
                        "Unusual description present in port %s", com_port_name
                    )
                elif com_port_desc.lower() in device_description.lower():
                    possible_devices_lst.append(device)

        return possible_devices_lst

    def _is_resp_expected(self, cmd, expect_pattern):
        """Check if the resp returned by the cmd is expected."""
        self.tty_session.send(cmd + "\r")
        expect_idx = self.tty_session.expect([expect_pattern, pexpect.TIMEOUT], 2)

        if expect_idx == 0:
            return True
        else:
            self.tty_session.send(cmd + "\r")
            expect_idx = self.tty_session.expect([expect_pattern, pexpect.TIMEOUT], 2)
            if expect_idx == 0:
                return True

        return False

    def _get_baudrate(self, com_port_name):
        baudrate = self.com_port_info[com_port_name].baudrate
        default_baudrate = 115200

        if not baudrate:
            warning_message = (
                f"Undefined baudrate for {com_port_name}, "
                f"so the default baudrate {str(default_baudrate)} would be used"
            )
            swilog.warning(warning_message)
            return default_baudrate  # the most common baudrate for swi modules

        return baudrate

    def open(self, port, baudrate=115200):
        """Open the specified port."""
        try:
            self.serial_port = com.SerialPort.open(port, baudrate)
            self.tty_session = com.ttyspawn(self.serial_port.fd)
        except:
            swilog.warning(f"Unable to open {port}")
            return False

        return True

    def close(self):
        """Close self.serial_port."""
        try:
            if os.name == "nt":
                self.serial_port.close()
            else:
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
                f"{str(i + 1)} iteration to scan through all possible "
                f"{com_port_name} ports"
            )

            if len(possible_devices_lst) == 0:
                possible_devices_lst = self._get_com_port_device_lst(com_port_name)

            for usb_device_path in possible_devices_lst:
                has_port_found = False
                swilog.info(
                    f"Try to open {usb_device_path}"
                    f" and see if it is a {com_port_name} port"
                )

                baudrate = self._get_baudrate(com_port_name)
                if self.open(usb_device_path, baudrate):
                    has_port_found = self.identify_port(com_port_name)
                self.close()

                if has_port_found:
                    swilog.info(f"{usb_device_path} is the {com_port_name} port!")
                    com_port_device = com.ComPortDevice(usb_device_path)
                    self.com_port_info[com_port_name].update_usb_interface(
                        com_port_device.get_usb_interface()
                    )
                    return usb_device_path

            swilog.info(
                f"Wait for {str(max_wait_time)} seconds before the next retry..."
            )
            time.sleep(max_wait_time)

        return None
