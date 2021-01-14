"""File copy or transfer (scp, adb, wget...)."""
import time
import os
import pexpect
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def scp(file_list, dest, target):
    """Copy files to target with scp.

    Args:
        file_list: file name or python list of files/folder to copy
        dest: destination folder or file
        target: fixture of the target to copy files onto

    LeTP add some flags and the SSH port can be different from 22.
    """
    if isinstance(target, str):
        # Legacy call, target is target_ip
        target_ip = target
        ssh_opts = os.getenv("LETP_SSH_OPTS")
        ssh_port = os.getenv("LETP_SSH_PORT")
    else:
        target_ip = target.target_ip
        ssh_opts = target.ssh_opts
        ssh_port = target.ssh_port
    if isinstance(file_list, str):
        file_list = [file_list]
    # To fix manage folders with -r
    cmd = "scp -r %s -P %s %s root@%s:%s" % (
        ssh_opts,
        ssh_port,
        " ".join(file_list),
        target_ip,
        dest,
    )
    swilog.info(cmd)
    rsp, _exit = pexpect.run(cmd, withexitstatus=1)
    swilog.info(rsp)
    assert _exit == 0, "Impossible to copy"


def adb_transfer(file_list, dest):
    """Copy files to target with adb.

    Args:
        file_list: python list of files/folder to copy
        dest: destination folder or file
    """
    time.sleep(5)
    exit_status = -1
    count = 20
    # Wait for a device
    while exit_status != 0:
        output, exit_status = pexpect.run("adb devices", withexitstatus=1)
        time.sleep(1)
        count -= 1
        assert count != 0
    cmd = '/bin/bash -c "%s"' % (
        "/usr/bin/adb push %s %s" % (" ".join(file_list), dest)
    )
    swilog.info(cmd)
    output, exit_status = pexpect.run(cmd, withexitstatus=1)
    swilog.info(output)
    assert exit_status == 0
    time.sleep(1)


def fetch_binary(file_location, file_output):
    """Get a file by HTTP.

    Args:
        file_location: URL of the file
        file_output: output path
    """
    pexpect.run("mkdir -p %s" % file_location)
    swilog.info("wget -q -N -P %s %s" % (file_output, file_location))
    rsp, _exit = pexpect.run(
        "wget -q -N -P %s %s" % (file_output, file_location),
        timeout=600,
        withexitstatus=1,
    )
    swilog.info(rsp)
    assert _exit == 0, "Impossible to get %s" % file_location


def find_in_host(fileName, path):
    """Find a file in a folder recursively.

    Args:
        fileName: name of the file to find
        path: path to scan

    Returns:
        Found path or None
    """
    for root, _, files in os.walk(path):
        if fileName in files:
            return os.path.join(root, fileName)
    return None
