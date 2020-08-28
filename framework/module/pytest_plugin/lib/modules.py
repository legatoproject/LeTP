# pylint: skip-file
# Reenable pylint after error fixes.
"""@package targetModules module dependant functions.

Set of functions that must be implemented differently depending
on the module (eth, ecm, imei,...)
"""
import sys
import time
import imp
import re
import os
import ipaddress
import copy
import pexpect
import pexpect.fdpexpect
import pexpect.pxssh
import swilog
import com
import com_port_detector
from module_exceptions import SlinkException, TargetException


__copyright__ = "Copyright (C) Sierra Wireless Inc."


def get_swi_module_files():
    """Return a list of module types to look for specific module."""
    modules = set()
    sys_paths = sys.path
    for path in sys_paths:
        if not os.path.exists(path):
            continue
        tree = os.listdir(path)
        for i in tree:
            if i.startswith("modules_"):
                module_name = i.replace(".py", "")
                modules.add(module_name)
    return set(modules)


def get_swi_module(class_name):
    """Get module from one of the modules files."""
    for module_file in get_swi_module_files():
        try:
            __import__(module_file)
            return getattr(sys.modules[module_file], class_name)
        except Exception:
            pass
    raise TargetException("Target not found: %s" % class_name)


def define_target(request, read_config, inst_name="module"):
    """!inst_name is the name of the module top element in the xml."""
    generic_name = read_config.findtext("%s/generic_name" % inst_name)
    module_name = read_config.findtext("%s/name" % inst_name)

    class_name = generic_name.replace("-", "").upper()
    module_fn = get_swi_module(class_name)

    return module_fn.create(module_name, generic_name, request, read_config, inst_name)


class ModuleLink:
    """Manage link functionalities."""

    def __init__(self, module, name):
        """Initialize ModuleLink."""
        assert module
        assert name
        self.module = module
        self.__obj = None
        self.name = name
        self.info = None
        self.port_type = None
        self.aliases = []
        # To prevent static analysis error "Not Callable"
        # because it was an empty variable.
        self.init_cb = lambda x: None
        self.close_cb = lambda x: None
        self.list_attr = []

    @property
    def obj(self):
        """Get the link obj."""
        if not self.__obj:
            self.init()
        return self.__obj

    @obj.setter
    def obj(self, obj):
        """Set the link obj."""
        swilog.debug("[Link %s] = %s" % (self.name, obj))
        self.__obj = obj
        self.refresh_aliases()

    def init(self):
        """Provide a generic way to initialize a link."""
        swilog.debug("[Link %s] init" % self.name)
        if callable(self.init_cb):
            try:
                return self.init_cb(self)
            except Exception as e:
                swilog.debug(e)
                raise SlinkException(e)
        swilog.warning("No init function has been provided for link %s" % self.name)
        return None

    def close(self):
        """Provide a generic way to close a link."""
        swilog.debug("[Link %s] close" % self.name)
        if callable(self.close_cb):
            try:
                self.close_cb(self)
            except Exception as e:
                swilog.debug(e)

        if hasattr(self.obj, "close"):
            try:
                self.obj.close()
            except Exception as e:
                swilog.debug(e)

    def reinit(self):
        """Reinit the link based on the port_type."""
        swilog.warning("%s port may be gone!", self.port_type)
        swilog.info("Try to reconnect the %s port...", self.port_type)
        dev_tty = self.module.port_detector.get_com_port(self.port_type)
        self.info.update_name(dev_tty)
        self.close()
        self.init()
        self.update_alias()

    def update_alias(self):
        """Update the alias of the link obj."""
        aliases_cpy = copy.deepcopy(self.aliases)
        for alias in aliases_cpy:
            self.remove_alias(alias)
            self.add_alias(alias)

    def add_alias(self, alias):
        """Add alias to the link obj."""
        if alias not in self.aliases:
            self.aliases.append(alias)
        self.refresh_aliases()

    def remove_alias(self, alias):
        """Remove alias of the link obj."""
        self.aliases.remove(alias)
        delattr(self.module, alias)
        if alias == "target":
            for fn in self.list_attr:
                if hasattr(self.module, fn):
                    delattr(self.module, fn)

    def refresh_aliases(self):
        """Refresh alias of the link obj."""
        obj = self.obj
        for alias in self.aliases:
            setattr(self.module, alias, obj)
            if alias == "target" and obj:
                self._set_target_alias()

    def _set_target_alias(self):
        """Assign every methods from the link object to the module."""
        for fn in dir(self.__obj):
            if not hasattr(self.module, fn):
                # A method can be already implemented in the upper class.
                try:
                    setattr(self.module, fn, getattr(self.__obj, fn))

                    if fn not in self.list_attr:
                        self.list_attr.append(fn)
                except Exception as e:
                    swilog.debug(e)
                    swilog.warning("Warning: Impossible to set attribute")


class SwiModule:
    """Generic Sierra Wireless module class."""

    def __init__(self, target_name):
        self.slink1 = self.slink2 = self.ssh = self._ssh_port = None
        self.target = self._com_port_info = None

        self.target_at_cmd = {
            "CIMI": "AT+CIMI",
            "ICCID": "AT+ICCID",
            "CCID?": "AT+CCID?",
            "KSREP?": "AT+KSREP?",
            "KGSN=0": "AT+KGSN=0",
            "KGSN=3": "AT+KGSN=3",
        }
        self.pathed_slink_template = "%s/slink%d"
        self.slink_template = "slink%d"

        self._target_name = target_name
        self.module_name = target_name[0]
        self.generic_name = target_name[1]
        self.is_connected = False

        self._com_port_checklist = {}
        self.port_detector = com_port_detector.ComPortDetector(
            self.com_port_checklist, self.com_port_info
        )

        # Map of all module links.
        # Not an array as we want to store things such as 'ssh'
        self.links = {}
        # Create the 3 links:
        for idx in [1, 2, 3]:
            self.links[idx] = ModuleLink(self, idx)

        # By default, link 1 is the default link
        self.set_link_alias(1, "target")

    @classmethod
    def create(
        cls, module_name, generic_name, request, read_config, inst_name="module"
    ):
        """Create module with necessary parameters."""
        raise NotImplementedError

    @property
    def com_port_info(self):
        """Check for com port info."""
        if not self._com_port_info:
            self._com_port_info = com.ComPortInfo()

        return self._com_port_info

    @property
    def com_port_checklist(self):
        """Return the information to check different type of com port."""
        if not self._com_port_checklist:
            self._com_port_checklist[com.ComPortType.AT.name] = [
                ("ATI", self.__class__.__name__.upper().strip("X"))
            ]

        return self._com_port_checklist

    def set_link_alias(self, idx, name):
        """Set the link aliases."""
        self.remove_link_alias(name)
        self.links[idx].add_alias(name)

    def remove_link_alias(self, name):
        """Remove the link aliases."""
        for link in self.links.values():
            if name in link.aliases:
                link.remove_alias(name)

    def get_link(self, port_type):
        """Get link from port."""
        for link in self.links.values():
            if link.port_type == port_type:
                return link
        return None

    @property
    def link1(self):
        """Link for CLI command."""
        return self.links[1].obj

    @property
    def link2(self):
        """Link for AT command."""
        return self.links[2].obj

    @property
    def link3(self):
        """Link for alternative connection."""
        return self.links[3].obj

    def is_port_responsive(self, port_type=com.ComPortType.CLI.name):
        """Check if specified port can respond to the cmd."""
        checklist = self.com_port_checklist.get(port_type)
        if not checklist:
            return False

        if not self.get_link(port_type) or not self.get_link(port_type).obj:
            return False

        link = self.get_link(port_type).obj

        for cmd, rsp in checklist:
            link.send(cmd + "\r")

            if port_type is com.ComPortType.AT.name:
                link.expect(["OK", pexpect.TIMEOUT], 10)

                if rsp not in link.before:
                    return False
            else:
                idx = link.expect([rsp, pexpect.TIMEOUT], 10)

                if idx == 1:
                    return False

        return True

    def is_port_accessible(self, port_type=com.ComPortType.CLI.name):
        """Check if specified port is accessible."""
        link = self.get_link(port_type)
        if not link:
            return False

        link_obj = link.obj
        if not link_obj:
            return False

        if not hasattr(link_obj, "fd") or link_obj.fd == -1:
            return False

        if link_obj.closed:
            return False

        # if CLI was pre-defined with a valid fd but device name has been changed
        re_opened_port = com.SerialPort.open(link_obj.dev_tty)

        if not re_opened_port:
            return False

        try:
            re_opened_port.close()
        except Exception as e:
            swilog.debug(e)

        return self.is_port_responsive(port_type)

    def is_prompt_expected(self, expected_prompt):
        """Check if the CLI prompt is expected."""
        self.slink1.send("\r")

        if self.slink1.expect([expected_prompt, pexpect.TIMEOUT], 1) == 0:
            return True

        return False

    def teardown(self):
        """Tear down link."""
        for link in self.links.values():
            try:
                link.close()
            except Exception as e:
                swilog.debug(e)

    @property
    def before(self):
        """Target logs before the command send to the target."""
        return self.target.before

    @property
    def after(self):
        """Target logs after the command send to the target."""
        return self.target.after

    @property
    def target_name(self):
        """Get the target name."""
        return self.generic_name

    @property
    def ssh_port(self):
        """SSH port property."""
        if self._ssh_port:
            return self._ssh_port
        if hasattr(self.target, "ssh_port") and self.target.ssh_port:
            return self.target.ssh_port
        raise TargetException("No SSH port declared in the main target link")

    @property
    def ssh_opts(self):
        """SSH options for ssh connection."""
        if hasattr(self.ssh, "ssh_opts") and self.ssh.ssh_opts:
            return self.ssh.ssh_opts
        if hasattr(self.target, "ssh_opts") and self.target.ssh_opts:
            return self.target.ssh_opts
        raise TargetException("No defined ssh options")

    def read_module_name(self):
        """Return the module name, as read from the device."""
        rsp = self.run_at_cmd("ATI", 20)
        device = re.search(r"(.*)Model: (?P<model>\w+)", rsp).group("model")
        return device

    @property
    def imei(self):
        """Return the IMEI of the module."""
        raise NotImplementedError

    def get_imei(self):
        """Return the IMEI of the module.

        (deprecated, use target.imei instead).

        @ingroup targetGroup
        """
        return self.imei

    @property
    def fsn(self):
        """Return the Serial Number of the module."""
        raise NotImplementedError

    @property
    def match(self):
        """Get target regex match."""
        return self.target.match

    @property
    def sim_iccid(self):
        """Return the SIM ICCID."""
        if self.sim_ready():
            rsp = self.run_at_cmd(self.target_at_cmd["CCID?"], 10)
            return re.search(r"\+CCID:\s*(?P<iccid>[0-9]+)", rsp).group("iccid")

        return None

    @property
    def sim_imsi(self):
        """Return the SIM IMSI."""
        if self.sim_ready():
            rsp = self.run_at_cmd(self.target_at_cmd["CIMI"], 10)
            return re.search(r"(?P<imsi>[0-9]+)", rsp).group("imsi")

        return None

    def configure_eth(self, addr=""):
        """Configure ethernet for using ssh.

        Args:
            addr: ip address that should be used
        @ingroup targetGroup
        """
        assert 0, "Not implemented yet"

    def configure_ecm(self, addr=""):
        """Configure the USB ECM link for using ssh.

        Args:
            addr: ip address that should be used
        @ingroup targetGroup
        """
        assert 0, "Not implemented yet"

    def get_legato_partition(self):
        assert 0, "Not implemented yet"

    def get_data_partition(self):
        assert 0, "Not implemented yet"

    def wait_for_itf(self, itf, timeout=20):
        assert 0, "Not implemented yet"

    def get_ip_addr(self, itf):
        assert 0, "Not implemented yet"

    def sim_status(self, timeout=5):
        """Get SIM status."""
        if not self.links[1].info.is_used():
            # bypass checking sim status
            return "0"
        else:
            rsp = self.run_at_cmd(self.target_at_cmd["KSREP?"], timeout)
            return re.search(r"\+KSREP:\s*[0|1]{1},(?P<status_id>\d{1})", rsp).group(
                "status_id"
            )

    def sim_absent(self):
        """Check if SIM is absent."""
        return self.sim_status() == "2"

    def sim_ready(self):
        """Check if SIM is ready."""
        return self.sim_status() == "0"

    def get_info(self):
        """Get software/hardware info.

        @ingroup targetGroup
        """
        self.run_at_cmd("ATI", 60)
        self.run_at_cmd("ATI8", 60)
        self.run_at_cmd("ATI9", 60)
        if self.sim_ready():
            self.run_at_cmd(self.target_at_cmd["CIMI"], 60)
            self.run_at_cmd(self.target_at_cmd["CCID?"], 60)

    def wait_for_device_up(self, timeout=180):
        """Check if device is up by testing all ports are responsive."""
        time_elapsed = time.time()
        end_time = time.time() + timeout

        while time_elapsed <= end_time:
            swilog.info("Wait for device is up...")
            if not self.is_port_accessible(com.ComPortType.AT.name):
                swilog.warning("checking at port")
                self.get_link(com.ComPortType.AT.name).reinit()
            elif self.links[1].info.is_used() and not self.is_port_accessible(
                com.ComPortType.CLI.name
            ):
                self.get_link(com.ComPortType.CLI.name).reinit()
            else:
                swilog.info("Device is up!")
                return 0

            time.sleep(1)
            time_elapsed = time.time()

        swilog.warning("Device may be at some bad state")
        return 1

    def wait_for_reboot(self, timeout=180):
        """Wait for the device to complete reboot."""
        if self.wait_for_device_up(timeout) == 1:
            return False

        return True

    def run_at_cmd(self, at_cmd, timeout=20, expect_rsp=None, check=True, eol="\r"):
        """Run a cmd in AT console."""
        return self.slink2.run_at_cmd(at_cmd, timeout, expect_rsp, check, eol)


def look_for_tty(root_dir, path, prefix):
    """Look for tty port."""
    for name in os.listdir(path):
        # Max depth of 3
        entry = os.path.join(path, name)
        depth = entry.replace(root_dir, "").count("/")
        if depth > 3:
            continue
        if name.startswith(prefix):
            return name
        if os.path.isdir(entry) or os.path.islink(entry):
            name = look_for_tty(root_dir, entry, prefix)
            if name:
                return name
    return None


def get_tty_device(usb_dev, prefix="ttyUSB"):
    """Get tty device."""
    root_dir = "/sys/bus/usb/devices/%s/" % usb_dev

    if not os.path.isdir(root_dir):
        return None

    return look_for_tty(root_dir, root_dir, prefix)


class SlinkInfo:
    """Generic slink info class for target link types."""

    def __init__(self, config, base_config, port_detector=None):
        self.config = config
        self.base_config = base_config
        self.port_detector = port_detector

    def __str__(self):
        """Get a string representation for this slink."""
        return "{}: speed={} port={} desc={} rtscts={}".format(
            self.name(), self.speed(), self.port(), self.desc(), self.rtscts()
        )

    def is_used(self):
        """Check if port is being used."""
        slink_d = self.config.find(self.base_config).get("used")
        return slink_d is not None and slink_d == "1"

    def name(self):
        """Get name of link."""
        return self.config.findtext(self.base_config + "/name")

    def is_ip(self):
        """Check if the device name is an IP.

        We need to clarify the usage of telnet IP which such IP
        shouldn't belong to slink LETP-309
        """
        try:
            ipaddress.ip_address(self.name())
        except ValueError:
            return False

        return True

    def speed(self):
        """Get the speed of the port from the base config."""
        return int(self.config.findtext(self.base_config + "/speed"))

    def port(self):
        """Get the port from the base config."""
        return self.config.findtext(self.base_config + "/port")

    def desc(self):
        """Get the description of the port from the base config."""
        return self.config.findtext(self.base_config + "/desc")

    def rtscts(self):
        """Get the RTSCTS from the base config."""
        return self.config.findtext(self.base_config + "/rtscts") == "1"

    def detect_ports(self):
        """Detect if slink port is available."""
        if "slink1" in self.base_config:
            return self.port_detector.get_com_port(com.ComPortType.CLI.name)
        elif "slink2" in self.base_config:
            return self.port_detector.get_com_port(com.ComPortType.AT.name)
        return None

    def device(self):
        """Create a device instance using ComPortDevice."""
        if self.name() is None:
            return None

        device_name = self.name()

        if device_name.startswith("usb:"):
            device_name = self.name().replace("usb:", "")
        elif device_name.startswith("COM"):
            return device_name

        com_port_device = com.ComPortDevice(device_name)

        if com_port_device.is_usb_interface():
            return com_port_device.get_dev_tty()
        elif com_port_device.is_usb_id():
            if self.port_detector:
                return self.detect_ports()
            else:
                usb_dev = get_tty_device(device_name)
                if not usb_dev:
                    swilog.warning(
                        "No device found for USB %s at the moment" % device_name
                    )
                    return None
                return "/dev/%s" % usb_dev
        elif com_port_device.is_dev_tty():
            return com_port_device.name
        else:
            swilog.warning("Unrecognized device name: %s" % device_name)

        return None

    def update_name(self, name):
        """Update the value of <name>."""
        tag = self.config.find(self.base_config + "/name")
        tag.text = name
