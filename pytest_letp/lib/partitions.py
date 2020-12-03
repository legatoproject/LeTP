"""!@package partitions Utility functions to flash partitions."""
import os
import time

from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def erase(target, partition_name, root_password=None):
    """!Erase a partition with fastboot.

    @param target: target fixture
    @param partition_name: partition to erase
    @param root_password: optional host root password
    """
    target.sendline("sys_reboot bootloader")
    swilog.info("wait for bootloader")
    time.sleep(20)
    sudo = 'echo "%s" | sudo -S ' % root_password if root_password else ""
    cmd = "%s fastboot erase %s" % (sudo, partition_name)
    swilog.info(cmd)
    # Pexpect does not support "|" in command
    os.system(cmd)
    # Reboot
    cmd = "%s fastboot reboot" % sudo
    os.system(cmd)
    # rsp = pexpect.run(cmd)
    # swilog.info(rsp)
    # Check exit after reboot to not be in fastboot if exit == 1
    # assert exit == 0, "Partition not erased"
    target.wait_for_reboot()
