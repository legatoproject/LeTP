# pylint: disable=broad-except
# pylint: disable=no-member
# pylint: disable=too-many-statements
"""Module dependant functions.

Set of functions for Linux modules.
"""
import time
import re
import os
import pexpect
import pexpect.fdpexpect

from pytest_letp.lib import swilog
from pytest_letp.lib import com
from pytest_letp.lib import app

from pytest_letp.lib.versions_linux import LinuxVersions
from pytest_letp.lib.module_exceptions import SlinkException, TargetException
from pytest_letp.lib.modules import SwiModule, SlinkInfo, ModuleLink
from pytest_letp.pytest_test_config import TEST_CONFIG_KEY

if os.name == "posix":
    from pytest_letp.lib import ssh_linux
elif os.name == "nt":
    from pytest_letp.lib import ssh_windows
__copyright__ = "Copyright (C) Sierra Wireless Inc."


# =====================================================================================
# Linux Helper Functions
# =====================================================================================
def configure_ssh_env(read_config, inst_name):
    """Determine the ip address and the port of the target, set env variables.

    :return: a tuple: (target_ip, ssh_port)
    """
    # Determine the environment variable name by the target to define
    target_ip_env_name = "TARGET_IP"
    target_ssh_port_env_name = "TARGET_SSH_PORT"
    letp_ssh_port_env_name = "LETP_SSH_PORT"
    ssh_port_env_name = "SSH_PORT"
    if inst_name.startswith("target"):
        target_num = int(inst_name.replace("target", ""))
        target_ip_env_name = "TARGET%d_IP" % target_num
        target_ssh_port_env_name = "TARGET%d_SSH_PORT" % target_num
        letp_ssh_port_env_name += str(target_num)
        ssh_port_env_name += str(target_num)

    # Get ip and ssh port if they exist
    env_ip = os.getenv(target_ip_env_name)
    env_ssh_port = os.getenv(target_ssh_port_env_name)

    # The environment variables have more priority than the configuration files
    target_ip = (
        read_config.findtext("%s/ssh/ip_address" % inst_name)
        if env_ip is None
        else env_ip
    )
    ssh_port = int(
        read_config.findtext("%s/ssh/port" % inst_name)
        if env_ssh_port is None
        else env_ssh_port
    )

    if env_ip is None:
        # Create TARGET_IP for AVLib
        os.environ[target_ip_env_name] = target_ip

    # Set environment for LeTP
    os.environ["LETP_SSH_OPTS"] = (
        "-o ServerAliveInterval=5 -o ServerAliveCountMax=1 "
        "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    )
    os.environ[letp_ssh_port_env_name] = "%d" % ssh_port

    # Set environment for the Legato tools (instapp, ...)
    # ServerAliveCountMax and ServerAliveInterval are already set in the Legato tools
    os.environ[
        "SSH_EXTRA_OPTS"
    ] = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    os.environ[ssh_port_env_name] = "%d" % ssh_port
    return (target_ip, ssh_port)


# =====================================================================================
# Linux Generic Module
# =====================================================================================
class ModuleLinux(SwiModule):
    # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """Generic class for Linux based modules."""

    linux_pattern = {
        "full": r".*?(?P<version>(SWI.+\_|LXSWI.+\-).+$)",
        "parsed": (
            r".*?(?P<version>"
            r"(SWI.+\_|LXSWI.+\-)\d+\.\d+(\.\d+\.\d+)?(\.rc\d{1,2})?).*?"
        ),
    }

    def __init__(
        self,
        target_name,
        target_ip,
        ssh_add,
        ssh_port,
        config_target,
        inst_name, request
    ):
        super(ModuleLinux, self).__init__(target_name)

        self.ssh2 = self.ssh_logread = None
        self.ssh_cmd = {
            "network_if": "%s/ssh/network_if",
            "config_eth0": "ifconfig eth0 %s",
            "config_ecm0": "ifconfig ecm0 %s",
        }
        self._target_ip = target_ip
        self.config_target = config_target.getroot()
        self._ssh_add = ssh_add
        self._ssh_port = ssh_port
        self.inst_name = inst_name

        # Link 1 = Console
        self.links[1].port_type = com.ComPortType.CLI.name
        self.links[1].init_cb = self.init_cli_port
        # Link 2 = AT
        self.links[2].port_type = com.ComPortType.AT.name
        self.links[2].init_cb = self.init_at_port

        for idx in [1, 2]:
            self.links[idx].info = SlinkInfo(
                config_target, self.pathed_slink_template % (inst_name, idx)
            )
            self.links[idx].add_alias(self.links[idx].info.desc())
            self.links[idx].add_alias(self.slink_template % idx)

        if (
            ssh_add is not None
            and self.config_target.find("%s/ssh" % inst_name).get("used") == "1"
        ):
            # the second (ssh2) and third ssh (ssh_logread)
            # link will be added dynamically
            # if needed in the test by a fixture
            self.links["ssh"] = ModuleLink(self, "ssh")
            self.links["ssh"].init_cb = self.init_ssh_link
            self.links["ssh"].add_alias("ssh")
            ssh_desc = self.config_target.findtext("%s/ssh/desc" % inst_name)
            self.links["ssh"].add_alias(ssh_desc)

        assert (
            self.slink1 is not None or self.slink2 is not None or self.ssh is not None
        ), "target fixture needs at least one communication link!"

        ssh_main_link = self.config_target.find("%s/ssh" % inst_name).get("main_link")

        if self.ssh is not None and ssh_main_link == "1":
            self.set_link_alias("ssh", "target")

        try:

            if self.ssh is not None and self.slink1 is not None:
                # Change the default target to serial link
                self.set_link_alias(1, "target")
                network_if = self.config_target.findtext(
                    self.ssh_cmd["network_if"] % self.inst_name
                )
                if self.ssh.check_communication() != 0 or (
                    self.slink1.login()
                    and self.get_ip_addr(network_if) != self.ssh.target_ip
                ):
                    self.get_ip_addr(network_if)
                    self.configure_board_for_ssh(request)
                self.ssh.login()
                # Restore ssh as default link
                self.set_link_alias("ssh", "target")
                # For the long lines, change the terminal length. Unfortunately,
                # not available for serial link
                self.ssh.setwinsize(com.TTY_SIZE, 200)

            self.login()
            # Set the mac address if needed
            target_mac_add = self.config_target.findtext(
                "%s/target/mac_add" % self.inst_name
            )
            if target_mac_add is not None:
                self.set_mac(target_mac_add)
        except Exception as e:
            swilog.warning("Error during initialization: %s" % e)

    @classmethod
    def create(
        cls, module_name, generic_name, request, read_config, inst_name="module"
    ):
        """Create module with necessary parameters."""
        target_ip, ssh_port = configure_ssh_env(read_config, inst_name)
        ssh_add = None

        if read_config.find("%s/ssh" % inst_name).get("used") == "1":
            ssh_add = target_ip
            # Ssh is the default main test link
            main_link = "1"
            if (
                request.config.getoption("--use_uart")
                or read_config.find("%s/ssh" % inst_name).get("main_link") == "0"
            ):
                # Uart is the main link
                main_link = "0"
            read_config.find("%s/ssh" % inst_name).set("main_link", main_link)
        return cls(
            (module_name, generic_name),
            target_ip,
            ssh_add,
            ssh_port,
            read_config,
            inst_name,
            request,
        )

    def login(self):
        """Login to the target using the appropriate link."""
        if self.slink1:
            self.slink1.login()
        elif self.ssh:
            self.ssh.login()
        elif hasattr(self, "ssh2") and self.ssh2:
            self.ssh2.login()
        elif hasattr(self, "ssh_logread") and self.ssh_logread:
            self.ssh_logread.login()
        elif self.slink2:
            self.slink2.login()

    def init_ssh_link(self, link):
        """Create SSH link to the device."""
        link.obj = self.create_ssh_connection()

    @staticmethod
    def init_cli_port(link):
        """Cr(self, itfeate link to CLI port on device."""
        if not link.info.is_used():
            return

        if link.info.device():
            link.obj = com.target_serial_qct(
                dev_tty=link.info.device(),
                baudrate=link.info.speed(),
                rtscts=link.info.rtscts(),
            )
        else:
            link.obj = com.target_telnet_qct(
                telnet_ip=link.info.name(), telnet_port=link.info.port()
            )

    @staticmethod
    def init_at_port(link):
        """Create link to AT port on device."""
        if not link.info.is_used():
            return

        if link.info.device():
            link.obj = com.target_serial_at(
                dev_tty=link.info.device(),
                baudrate=link.info.speed(),
                rtscts=link.info.rtscts(),
            )
        else:
            link.obj = com.target_telnet_at(
                telnet_ip=link.info.name(), telnet_port=link.info.port()
            )

    def create_ssh_connection(self):
        """Start a SSH session between host and target."""
        ssh_client = None
        if os.name == "posix":
            ssh_client = ssh_linux.target_ssh_qct(
                self.target_ip,
                self._ssh_port,
                config_target=self.config_target,
                options={
                    "StrictHostKeyChecking": "no",
                    "UserKnownHostsFile": "/dev/null",
                    "ServerAliveInterval": "5",
                    "ServerAliveCountMax": "1",
                },
            )
        elif os.name == "nt":
            ssh_client = ssh_windows.TargetSSH(self.target_ip)
        return ssh_client

    def is_ssh_connection_accessible(self):
        """Return True if the ssh connection is accessible."""
        if not hasattr(self, "ssh") or not self.ssh:
            swilog.debug("ssh link wasn't created before")
            return False

        if self.ssh.closed:
            return False

        if self.ssh.check_communication() != 0:
            return False

        return self.ssh.prompt()

    @property
    def target_ip(self):
        """Get the target IP."""
        return self._target_ip

    @property
    def com_port_checklist(self):
        """Return the information to check different type of com port."""
        super().com_port_checklist[com.ComPortType.CLI.name] = [
            ("\r\n\r\n\r\n", r"root@.+:.+#|[^ ]+ login:")
        ]

        return super().com_port_checklist

    @property
    def linux_version(self):
        """Return the linux version in the module."""
        version_obj = LinuxVersions()
        return version_obj.get_linux_version(console=com.ComPortType.AT)

    def wait_for_device_up(self, timeout=0):
        """Wait for the device to be up."""
        if self.slink1:
            return self.slink1.wait_for_device_up(timeout)
        elif self.ssh:
            return self.ssh.wait_for_device_up(timeout)
        swilog.error("No link available.")
        raise SlinkException

    # pylint: disable=arguments-differ
    def wait_for_reboot(self, timeout=60, request=None):
        """Wait for a reboot of the target (by ssh)."""
        if self.slink1 is not None and self.ssh is not None:
            self.slink1.wait_for_reboot(timeout=timeout)
            if self.ssh.check_communication() != 0:
                self.configure_board_for_ssh(request)
        else:
            assert self.wait_for_device_down(timeout) == 0, "No shutdown of the target"
            assert self.wait_for_device_up(timeout) == 0, "Device was not started"

        if hasattr(self, "reinit"):
            self.reinit()
        if hasattr(self, "ssh2") and self.ssh2:
            self.ssh2.reinit()
        if hasattr(self, "ssh_logread") and self.ssh_logread:
            self.ssh_logread.reinit()
            self.ssh_logread.sendline("logread -f")

    def reboot(self, timeout=60, power_supply=None):
        """Reboot the target using a power supply or sending reboot command."""
        if power_supply is None:
            self.send("/sbin/reboot -f\n")
            time.sleep(2)
        for name in ["ssh", "ssh2", "ssh_logread"]:
            if not hasattr(self, name):
                continue
            link = getattr(self, name)
            if link is None:
                swilog.debug("Not closing {}, link is None".format(name))
                continue
            if link.closed:
                swilog.debug("Not closing {}, link {} is closed".format(name, link))
                continue
            link.close()
        if power_supply is not None:
            power_supply.cycle()
        self.wait_for_reboot(timeout)

    def wait_for_itf(self, itf, timeout=20):
        """Wait for the interface up in ifconfig.

        Args:
            itf:  interface of ifconfig (eth0, usb0, ...)
            timeout: in seconds
        """
        count = 0
        while count < timeout:
            try:
                self.target.run("/sbin/ifconfig %s " % itf)
                break
            except Exception:
                swilog.debug("Interface not ready. Wait for 5 s")
                time.sleep(5)
                count += 5
        assert count < timeout, "The expected interface %s was not mounted" % itf

    def get_ip_addr(self, itf):
        """Get the IP address of the interface (from ifconfig).

        Args:
                itf: interface of ifconfig (eth0, usb0, ...)

        Returns:
            IP address
        """
        self.target.sendline(
            "/sbin/ifconfig %s | awk '/inet addr/{print substr($2,6)}'" % itf
        )
        try:
            self.target.expect(r"\w+\.\w+\.\w+\.\w+\r", 2)
            swilog.debug(
                "Get ip address: \n %s \n %s" % (self.target.before, self.target.after)
            )
            return self.target.after.strip()
        except Exception:
            return ""

    @staticmethod
    def get_version_obj():
        """Return versions obj."""
        return LinuxVersions()

    def run_at_cmd(self, at_cmd, timeout=20, expect_rsp=None, check=True, eol="\r"):
        """Run and check AT commands."""
        if self.links[2].info.is_used() and self.link2:
            return super().run_at_cmd(at_cmd, timeout, expect_rsp, check, eol)

        cmd = "/usr/bin/microcom /dev/ttyAT"
        self.sendline(cmd)
        time.sleep(1)
        try:
            rsp = com.run_at_cmd_and_check(
                self, at_cmd, timeout, expect_rsp, check, eol
            )
        except Exception as e:
            # Exit from microcom if exception
            self.sendcontrol("x")
            raise TargetException(e)
        try:
            self.sendcontrol("x")
            self.prompt()
        except pexpect.EOF:
            swilog.debug("pexpect eof")
        return rsp

    def read_module_name(self):
        """Return the module name, as read from the device."""
        rsp = self.target.run("cm info device")
        device = re.search(r"(.+)", rsp).group(1)
        return device

    @property
    def imei(self):
        """Return the IMEI of the module."""
        rsp = self.target.run("cm info imei")
        imei = re.search(r"(\d+)", rsp).group(1)
        return imei

    @property
    def fsn(self):
        """Return the Serial Number of the module."""
        rsp = self.target.run("cm info fsn")
        fsn = re.search(r"([A-Z0-9]+)", rsp).group(1)
        return fsn

    @property
    def sim_iccid(self):
        """Return the SIM ICCID."""
        if self.sim_ready():
            if self.target:
                rsp = self.target.run("cm sim iccid", 10)
                return re.search(r"ICCID:\s*(?P<iccid>[0-9]+)", rsp).group("iccid")
            return super().sim_iccid

        return None

    @property
    def sim_imsi(self):
        """Return the SIM IMSI."""
        if self.sim_ready():
            if self.target:
                rsp = self.target.run("cm sim imsi", 10)
                return re.search(r"IMSI:\s*(?P<imsi>[0-9]+)", rsp).group("imsi")
            return super().sim_imsi

        return None

    def sim_absent(self):
        """Is SIM absent.

        Returns:
            True if absent

        Deprecated. Please use is_sim_absent()
        """
        return self.is_sim_absent()

    def is_sim_absent(self):
        """Is SIM absent.

        Returns:
            True if absent
        """
        rsp = self.target.run("/legato/systems/current/bin/cm sim", 5)
        return "LE_SIM_ABSENT" in rsp

    def sim_ready(self):
        """Is SIM ready.

        Returns:
            True if ready

        Deprecated. Please use is_sim_ready()
        """
        return self.is_sim_ready()

    def is_sim_ready(self):
        """Get if SIM ready.

        Return:
            True if ready
        """
        if not self.target:
            return False
        rsp = self.target.run("/legato/systems/current/bin/cm sim", 5)
        return "LE_SIM_READY" in rsp

    def open_port(self, port_nb, type_prot="tcp"):
        """Open a port on target."""
        if type_prot == "tcp":
            extra = "-m conntrack --ctstate NEW,ESTABLISHED"
        else:
            extra = "-m udp"

        self.target.run(
            "iptables -A OUTPUT -p %s --dport %d %s  -j ACCEPT"
            % (type_prot, port_nb, extra)
        )
        self.target.run(
            "iptables -A INPUT -p %s --sport %d %s -j ACCEPT"
            % (type_prot, port_nb, extra)
        )

    def set_mac(self, mac_addr):
        """Set the ethernet MAC address.

        If mac_addr is "auto", set a mac address based on the FSN.
        """
        if mac_addr is None or mac_addr == "":
            # Do nothing
            return
        elif mac_addr == "auto":
            # Mac address based on FSN
            # Get Device FSN number
            fsn = self.target.run("/legato/systems/current/bin/cm info fsn")
            fsn = fsn.replace("\r", "").replace("\n", "")
            rsplen = len(fsn)
            if rsplen and fsn.find("Invalid") == -1:
                # Build the unique MAC address
                mac_bytes_list = [
                    "EE",
                    fsn[2:4],
                    fsn[4:6],
                    fsn[6:8],
                    fsn[8:10],
                    fsn[10:12],
                ]
                mac_new_addr = ":".join(mac_bytes_list)
            else:
                swilog.error("No FSN defined. Can't set auto mac address!")
                return
        else:
            mac_new_addr = mac_addr
        swilog.debug("New Addr: %s" % mac_new_addr.upper())

        # Check MAC address not already set
        mac_old_addr = self.target.run("cat /sys/class/net/eth0/address")
        mac_old_addr = mac_old_addr.replace("\n", "").replace("\r", "")
        swilog.debug("Old Addr: %s" % mac_old_addr.upper())

        if mac_old_addr.upper().strip("\n") == mac_new_addr.upper():
            swilog.debug("MAC already updated. Nothing to do")
        else:
            setnet_cmd = "/legato/systems/current/bin/setNet mac %s" % (mac_new_addr)
            self.target.run(setnet_cmd)
            self.target.reboot()

    def is_autoconf(self):
        """Get if the ssh is autoconf."""
        return self.config_target.find("%s/ssh" % self.inst_name).get("autoconf", "1")

    def configure_board_for_ssh(self, request=None):
        """Use uart to configure SSH."""
        if self.configure_ssh(request):
            return
        elif self.is_autoconf():
            swilog.debug("configure_board_for_ssh: skipping config")
            return
        swilog.debug("configure_board_for_ssh")
        # Change default link to serial link
        self.target = self.slink1
        self.login()
        if self.config_target.findtext("%s/ssh/ip_method" % self.inst_name) == "fixed":
            ip_addr = self.config_target.findtext("%s/ssh/ip_address" % self.inst_name)
        else:
            ip_addr = ""
        if (
            self.config_target.findtext(self.ssh_cmd["network_if"] % self.inst_name)
            == "eth0"
        ):
            # Set the mac address if needed
            target_mac_addr = self.config_target.findtext(
                "%s/target/mac_add" % self.inst_name
            )
            if target_mac_addr is not None:
                self.set_mac(target_mac_addr)
            # Wait a little. It seems that udhcpc does not work sometimes
            # if configure_eth is done just after reboot
            time.sleep(10)
            self.configure_eth(ip_addr)
            # Open ssh port
            self.open_port(22)
        else:
            self.configure_ecm(ip_addr)
            # Open ssh port
            self.open_port(22)
            # Open DHCP ports
            self.open_port(67, "udp")
            self.open_port(68, "udp")
            host_ip = self.config_target.findtext("host/ip_address")
            split_target_ip = self.ssh.target_ip.split(".")
            self.slink1.sendline(
                "ifconfig %s"
                % self.config_target.findtext(
                    self.ssh_cmd["network_if"] % self.inst_name
                )
            )
            slink_id = self.slink1.expect(
                [pexpect.TIMEOUT, r"Mask:(\d*\.\d*\.\d*\.\d*)"], 5
            )
            # Set the default count to 1. Only the upper
            # part of the IP address will be checked
            count = 1
            if slink_id == 1:
                # Ignore if timeout in case the response from ifconfig change
                mask = self.slink1.match.group(1)
                # Set count to the number of part to check in the IP address
                count = mask.count("255")
            self.slink1.prompt()
            if (
                host_ip is not None
                and host_ip != ""
                and host_ip.split(".")[0:count] != split_target_ip[0:count]
            ):
                swilog.warning(
                    "host ip %s and target ip %s in xml not in the same subnet!"
                    % (host_ip, self.ssh.target_ip)
                )
        self.slink1.run("iptables -I INPUT -j ACCEPT")
        itf = self.config_target.findtext(self.ssh_cmd["network_if"] % self.inst_name)
        self.wait_for_itf(itf, 20)
        self.new_target_ip = self.get_ip_addr(itf)
        # Restore default link
        self.target = self.ssh
        if self.new_target_ip != self.ssh.target_ip:
            swilog.debug("Old target ip address %s" % self.ssh.target_ip)
            self.ssh.target_ip = self.new_target_ip
            self.target.target_ip = self.new_target_ip
            os.environ["TARGET_IP"] = self.new_target_ip

        self.ssh.reinit()
        # Reconfigure the other ssh links
        if hasattr(self, "ssh2") and self.ssh2:
            self.ssh2.target_ip = self.ssh.target_ip
            self.ssh2.reinit()
        if hasattr(self, "ssh_logread") and self.ssh_logread:
            self.ssh_logread.target_ip = self.ssh.target_ip
            self.ssh_logread.reinit()

    def get_info(self):
        """Get target info by sending commands."""
        self.run("cm info")
        self.run("cm sim")
        self.run("cm sim info || true")
        self.run("legato version")
        self.run("cat /etc/legato/version")

    def get_mtd_name(self, mtd_logical_name):
        """Get the targets mtd name."""
        rsp = self.run("cat /proc/mtd")
        match = re.search(r"(mtd\d+):.+%s" % mtd_logical_name, rsp)
        if match:
            mtd_nb = match.group(1)
            swilog.debug("mtd name: %s, mtd nb: %s" % (mtd_logical_name, mtd_nb))
            return mtd_nb
        else:
            raise TargetException("Mtd number was not found for %s" % mtd_logical_name)

    def configure_eth(self, addr=""):
        """Configure the eth0 port."""
        if addr != "":
            self.target.run(self.ssh_cmd["config_eth0"] % addr)

    def configure_ecm(self, addr=""):
        """Configure the ecm0 port."""
        if addr != "":
            self.target.run(self.ssh_cmd["config_ecm0"] % addr)

    @staticmethod
    def get_legato_partition():
        """Get legato partition."""
        return "lefwkro"

    @staticmethod
    def get_data_partition():
        """Get data partition."""
        return "userapp"

    def wipe_partition(self, logical_name):
        """Wipe target partition."""
        mtd = self.get_mtd_name(logical_name)
        self.run("flash_erase /dev/%s 0 0" % mtd)

    def erase_legato_partition(self):
        """Erase legato partition (aka /mnt/legato)."""
        logical_name = self.get_legato_partition()
        self.wipe_partition(logical_name)

    def _get_file_line(self, file, i, check_pattern=None):
        """Get line from file on target at line i.

        Return line if matching check_pattern else None.
        """
        line = self.run('sed "%dq;d" %s' % (i, file), check=False, local_echo=False)
        if not check_pattern or len(line) == 0:
            return line.split()[-1] if len(line) > 0 else None
        match = re.search(check_pattern, line.split()[-1])
        return match.group(1) if match else None

    def _remove_dirs(self):
        """Remove directories from target."""
        remove_list = set(
            [
                "/mnt/flash/legato/systems/*",
                "/mnt/flash/legato/apps/*",
                "/mnt/flash/home/root/*",
            ]
        )
        for entry in remove_list:
            self.run("rm -rf %s" % entry, check=False)

    def _remove_file(self):
        """Remove files from target."""
        flash_pattern = r"(\/mnt\/flash\/.*)"
        rm_file = "/mnt/flash/home/root/file.tmp"
        # Remove most files, but keep "permanent" files such as /legato/meta.
        keep_list = set(["/mnt/flash/legato/meta", rm_file])
        self.run(r"/usr/bin/find /mnt/flash \( -type f -o -type l \) > %s" % rm_file)
        lines = int(self.run("wc -l < %s" % rm_file))
        for line in range(lines):
            entry = self._get_file_line(rm_file, line + 1, flash_pattern)
            if entry and entry not in keep_list:
                self.run("rm %s" % entry, check=False)
        self.run("rm %s" % rm_file, check=False)

    def erase_data_partition(self, full=False):
        """Erase data partition (aka /mnt/flash)."""
        if full:
            logical_name = self.get_data_partition()
            self.wipe_partition(logical_name)
            return True
        try:
            app.legato_stop(self)
        except Exception as e:
            swilog.debug("Unable to stop legato: %s" % e)
            return False
        self._remove_dirs()
        self._remove_file()
        self.reboot(timeout=300)
        return True

    def configure_ssh(self, request=None):
        """Config ssh board with IP get from system environment."""
        if request:
            target_ip = (
                self.config_read(request=request).findtext("module/ssh/ip_address")
            )
            test_host_ip = self.config_read(request).findtext("host/ip_address")
            octave_capability = (
                self.config_read(request).find("capabilities/octave").get("used")
            )
            if not target_ip or not test_host_ip:
                swilog.warning(
                    "Cannot configure target ecm, missing target ip or test host ip"
                )
                return False
            if octave_capability == "1":
                swilog.debug("Skipping configure ecm0 on Octave device")
                return True
            self.slink1.login()
            if self.is_autoconf() and target_ip in self.slink1.run("configEcm show"):
                swilog.debug("configure_board_for_ssh: skipping config")
            else:
                swilog.debug("configure_board_for_ssh")
                swilog.info(
                    "Configuring target ecm to: "
                    f"target={target_ip}, host={test_host_ip}"
                )
                cmd = (
                    "configEcm off;"
                    "configEcm on target"
                    f" {target_ip} host {test_host_ip} netmask 255.255.255.0"
                )
                self.slink1.run(cmd)
                if target_ip in self.slink1.run("configEcm show"):
                    swilog.info("ecm is configured correctly")
            return True
        else:
            swilog.warning("Cannot read the default configuration information")
            return False

    @staticmethod
    def config_read(request=None):
        """Read the default xml configuration for the whole session."""
        session = request.node.session
        default_cfg = session.config._store[TEST_CONFIG_KEY]
        return default_cfg.get()


# =====================================================================================
# Linux Specific Modules
# =====================================================================================
class WP85(ModuleLinux):
    """Qualcomm based WP85 module."""

    def get_legato_partition(self):
        """Get the legato partition."""
        return "user0"

    def get_data_partition(self):
        """Get the data partition."""
        return "user1"


class WP750X(ModuleLinux):
    """Qualcomm based WP750x module."""

    def get_data_partition(self):
        """Get data partition."""
        return "customer2"


class WP76XX(ModuleLinux):
    """Qualcomm based WP76xx module."""


class WP77XX(ModuleLinux):
    """Qualcomm based WP77xx module."""


class Virt(ModuleLinux):
    """Qemu virtual module."""

    def get_legato_partition(self):
        """Get legato partition."""
        part = self.target.run(
            "grep '/mnt/legato ' /proc/mounts | "
            "awk '{print $1}' | sed 's#/dev/##' || true"
        )
        if part == "":
            part = "sdb"
        return part

    def get_data_partition(self):
        """Get data partition."""
        part = self.target.run(
            "grep '/mnt/flash ' /proc/mounts | "
            "awk '{print $1}' | sed 's#/dev/##' || true"
        )
        return part

    def erase_partition(self, partition):
        """Erase partition on device."""
        self.run("dd if=/dev/zero of=/dev/%s count=10 bs=1M || true" % partition)

    def erase_legato_partition(self):
        """Erase Legato partition on device."""
        partition = self.get_legato_partition()
        self.erase_partition(partition)

    def erase_data_partition(self, full=False):
        """Erase data partition."""
        partition = self.get_data_partition()
        self.erase_partition(partition)


class VirtX86(Virt):
    """Virtual platform virt-x86."""


class VirtArm(Virt):
    """Virtual platform virt-arm."""


class AR758X(ModuleLinux):
    """Qualcomm based AR758x module."""

    def configure_eth(self, addr=""):
        """Configure the eth0 port."""
        self.target.run(
            "/etc/init.d/start_QCMAP_ConnectionManager_le stop", check=False
        )
        time.sleep(5)
        self.target.run("killall QCMAP_ConnectionManager", check=False)
        time.sleep(5)
        if addr == "":
            try:
                rsp = self.target.run("udhcpc -i eth0")
                assert "obtained" in rsp
            except Exception:
                self.target.sendcontrol("c")
                self.target.reboot()
                raise TargetException("No address given by the dhcp")
        else:
            self.target.run(self.ssh_cmd["config_eth0"] % addr)

    def get_data_partition(self):
        """Get data partition."""
        return "customer2"


class AR759X(ModuleLinux):
    """Qualcomm based AR759x module."""

    def configure_eth(self, addr=""):
        """Configure the eth0 port."""
        self.target.run(
            "/etc/init.d/start_QCMAP_ConnectionManager_le stop", check=False
        )
        time.sleep(5)
        self.target.run("killall QCMAP_ConnectionManager", check=False)
        time.sleep(5)
        if addr == "":
            try:
                rsp = self.target.run("udhcpc -i eth0")
                assert "obtained" in rsp
            except Exception:
                self.target.sendcontrol("c")
                self.target.reboot()
                raise TargetException("No address given by the dhcp")
        else:
            self.target.run(self.ssh_cmd["config_eth0"] % addr)

    def get_data_partition(self):
        """Get data partition."""
        return "customer2"
