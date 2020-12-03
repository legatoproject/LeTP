"""!@package app Legato application library.

Module related to the Legato application (build, install, verification, ...)
@note Use the legato fixture instead of calling directly the library.
It is easier as the interface is simplified.
"""
# pylint: skip-file
# Reenable pylint after error fixes.
import os
import re
import subprocess
import time

import pexpect

from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."

##@defgroup legatoBuild Legato build, installation and clean
# It goes to LEGATO_ROOT, build, install the binary, clean it after tests.
# @{
def make(target_type, app_name, app_path="", should_fail=False, option="", timeout=600):
    """!Make a Legato application.

    @param target_type: type of target (wp85, ar759x, ...)
    @param app_name: name of the application
    @param app_path: path of the application
    @param should_fail: make is expected to fail
    @param option: extra mkapp options
    @param timeout: timeout

    @return make stdout if success

    @exception AssertionError: If make not accorded to should_fail param

    @ingroup legatoGroup
    """
    _service_names = [
        "audio",
        "cellNetService",
        "dataConnectionService",
        "modemServices",
        "positioning",
        "voiceCallService",
        "powerMgr",
        "airVantage",
        "secureStorage",
    ]

    # Check environment variable existence
    check_legato_env()

    search_path = [
        "-i %s/interfaces/%s" % (os.environ["LEGATO_ROOT"], serv)
        for serv in _service_names
    ]

    if r".adef" not in app_path:
        adef_path = os.path.join(app_path, app_name) + ".adef"
    else:
        adef_path = app_path

    cmd = "mkapp %s %s -t %s %s" % (
        adef_path,
        " ".join(search_path),
        target_type,
        option,
    )
    swilog.info(cmd)
    rsp, _exit = pexpect.run(cmd, encoding="utf-8", timeout=timeout, withexitstatus=1)
    swilog.info(rsp)

    if should_fail is False:
        assert _exit == 0
    else:
        assert _exit != 0
    return rsp


def install(
    target_type,
    target_ip,
    app_name,
    app_path="",
    signed=False,
    should_fail=False,
    timeout=120,
):
    """!Install a Legato application.

    @param target_type: type of target (wp85, ar759x, ...)
    @param target_ip: ip address of the target
    @param app_name: name of the application
    @param signed: set to 1 if installing signed app, 0 otherwise
    @param app_path: path of the application
    @param timeout: allowed time to install the app

    @return None

    @exception AssertionError: if installation error

    @ingroup legatoGroup
    """
    sign = ".signed" if signed is True else ""
    cmd = "app install %s.%s%s.update %s" % (
        os.path.join(app_path, app_name),
        target_type,
        sign,
        target_ip,
    )
    swilog.info(cmd)
    rsp, _exit = pexpect.run(cmd, encoding="utf-8", timeout=timeout, withexitstatus=1)
    swilog.info(rsp)
    if should_fail is False:
        assert _exit == 0
    else:
        assert _exit != 0


def install_legato(target_type, target_ip):
    """!Install a legato system (.update) on target.

    @param target_type: type of target (wp85, ar759x, ...)
    @param target_ip: ip address of the target

    @return: None

    @exception AssertionError: if installation error

    @ingroup legatoGroup
    """
    # Check environment variable existence
    check_legato_env()

    cmd = "app install %s/build/%s/system.%s.update %s" % (
        os.environ["LEGATO_ROOT"],
        target_type,
        target_type,
        target_ip,
    )
    swilog.info(cmd)
    rsp, _exit = pexpect.run(cmd, encoding="utf-8", withexitstatus=1)
    swilog.info(rsp)
    assert _exit == 0


def make_sys(
    target_type,
    sys_name,
    sys_path="",
    append_to_version="",
    should_fail=False,
    option="",
    quiet=False,
):
    """!Make a system.

    @param target_type: type of target (wp85, ar759x, ...)
    @param sys_name: name of the system definition file
    @param sys_path: path of the  system definition file
    @param append_to_version: string to append to version
    @param should_fail: make is expected to fail
    @param option: extra mksys options
    @param quiet: if True, do not produce logs

    @return stdout of mksys

    @exception AssertionError

    @ingroup legatoGroup
    """
    _service_names = [
        "audio",
        "cellNetService",
        "dataConnectionService",
        "modemServices",
        "positioning",
        "voiceCallService",
        "powerMgr",
        "airVantage",
        "secureStorage",
    ]

    # Check environment variable existence
    check_legato_env()

    search_path = [
        "-i %s/interfaces/%s" % (os.environ["LEGATO_ROOT"], serv)
        for serv in _service_names
    ]

    if r".sdef" not in sys_path:
        sdef_path = os.path.join(sys_path, sys_name) + ".sdef"
    else:
        sdef_path = sys_path

    if append_to_version == "":
        cmd = "mksys %s %s -t %s %s" % (
            sdef_path,
            " ".join(search_path),
            target_type,
            option,
        )
    else:
        swilog.info("appending..")
        cmd = "mksys %s -t %s --append-to-version=%s %s" % (
            sdef_path,
            target_type,
            append_to_version,
            option,
        )
    if not quiet:
        swilog.info(cmd)
    rsp, _exit = pexpect.run(cmd, encoding="utf-8", timeout=600, withexitstatus=1)
    if not quiet:
        swilog.info(rsp)
    if should_fail is False:
        assert _exit == 0
    else:
        assert _exit != 0
    return rsp


def install_sys(target_type, target_ip, sys_name, sys_path="", quiet=False, timeout=60):
    """!Install a system.

    @param target_type: type of target (wp85, ar759x, ...)
    @param target_ip: ip address of the target
    @param sys_name: name of the system definition file
    @param sys_path: path of the system definition file
    @param quiet: if True, do not produce logs
    @param timeout: timeout for the command.

    @return None

    @exception AssertionError

    @ingroup legatoGroup
    """
    cmd = "app install %s.%s.update %s" % (
        os.path.join(sys_path, sys_name),
        target_type,
        target_ip,
    )
    if not quiet:
        swilog.info(cmd)
    rsp, _exit = pexpect.run(cmd, timeout=timeout, encoding="utf-8", withexitstatus=1)
    if not quiet:
        swilog.info(rsp)
    assert _exit == 0


def make_install_sys(
    target_type, target_ip, sys_name, sys_path="", quiet=False, timeout=60
):
    """!Make and install a Legato system.

    @param target_type: type of target (wp85, ar759x, ...)
    @param target_ip: ip address of the target
    @param sys_name: name of the system definition file
    @param sys_path: path of the system definition file
    @param quiet: if True, do not produce logs
    @param timeout: in seconds

    @return None

    @exception AssertionError

    @ingroup legatoGroup
    """
    make_sys(target_type, sys_name, sys_path, "", False, "", quiet)
    install_sys(target_type, target_ip, sys_name, "", quiet, timeout)


def make_install(target_type, target_ip, app_name, app_path="", option=""):
    """!Make and install a Legato application.

    @param target_type: type of target (wp85, ar759x, ...)
    @param target_ip: ip address of the target
    @param app_name: name of the application
    @param app_path: path of the application
    @param option: extra mkapp options

    @return: None

    @exception AssertionError: if error

    @ingroup legatoGroup
    """
    make(target_type, app_name, app_path, False, option=option)
    install(target_type, target_ip, app_name)


def version_validity(ver):
    """!Check if version string is md5.

    @param ver: version to check

    @return 1 if version found, 0 instead
    """
    output = re.search(r"\b[0-9a-fA-F]{32}\b", ver)
    if output == "None":
        return 0
    else:
        return 1


## @}


##@defgroup legatoApp Legato applications
# Check the legato related apps. e.g. /legato/systems
# @{
def is_app_exist(target, app_name, ver=None):
    """!Check if the application exists.

    @param target: fixture to communicate with the target
    @param app_name: name of the application
    @param ver: version of the application

    @return True if the application exists

    @ingroup legatoGroup
    """
    return is_app_installed(target, app_name, ver)


def is_app_installed(target, app_name, ver=None):
    """!Check if an app with the given name exists (and optional version).

    @param target: fixture to communicate with the target
    @param app_name: name of the application
    @param ver: version of the application

    @return True if the application exists

    @ingroup legatoGroup
    """
    apps = {app_name: ver}
    return are_apps_installed(target, apps)


def are_apps_installed(target, apps):
    """!Check if apps with the given name exists.

    The format is either {app_name: version, ...} or [app_name, ...]

    @ingroup legatoGroup
    """
    _exit, rsp = target.run("app list", withexitstatus=True)
    if _exit != 0:
        swilog.error("Unable to list the apps installed")
        return None

    app_list = rsp.strip().split("\r\n")

    for app in app_list:
        if app in apps:
            swilog.info("Application %s exists. Now checking the version" % app)
            if isinstance(apps, dict):
                expected_version = apps[app]
                if expected_version and expected_version != "":
                    ver_check = version_validity(expected_version)
                    if ver_check == 0:
                        swilog.info("%s has no version" % app)
                    else:
                        _exit, rsp = target.run(
                            "app version %s" % app, withexitstatus=1
                        )
                        found_version = rsp.strip().split(" ")[1]
                        if found_version == expected_version:
                            apps.pop(app)
                else:
                    # No version to check
                    apps.pop(app)
            else:
                # No version to check
                apps.remove(app)
    return len(apps) == 0


def is_app_running(target, app_name):
    """!Check the application is running.

    @param target: fixture to communicate with the target
    @param app_name: name of the application

    @return True if the application is running, False instead and
            None if it was not possible to determine the status.

    @ingroup legatoGroup
    """
    _exit, rsp = target.run("app status %s" % (app_name), withexitstatus=True)
    if _exit != 0:
        swilog.error("Unable to determine if app %s is running or not" % app_name)
        return None

    return "[running]" in rsp


def are_apps_running(target, app_names):
    """!Check the applications are running.

    @param target: target fixture to communicate with the module
    @param app_name: names of the application

    @return True if all applications are running, False instead and
            None if it was not possible to determine the status.

    @ingroup legatoGroup
    """
    _exit, rsp = target.run("app status", withexitstatus=True)
    if _exit != 0:
        swilog.error("Unable to get apps status")
        return None

    app_list = rsp.strip().split("\r\n")
    for app in app_list:
        status, app_name = app.split(" ")
        if app_name not in app_names:
            continue
        if status != "[running]":
            swilog.info("%s is not running" % app_name)
            return False
        app_names.remove(app_name)

    if len(app_names) != 0:
        swilog.info("The following apps have not been found: %s" % ",".join(app_names))
        return False

    return True


def get_app_list(target):
    """!Get a list of the applications on the target."""
    apps = target.run("/legato/systems/current/bin/app list")
    return apps.splitlines()


def start(target, app_name):
    """!Start the application.

    @param target: target fixture to communicate with the module
    @param app_name: name of the application

    @return AssertionError

    @ingroup legatoGroup
    """
    rsp = target.run("/legato/systems/current/bin/app start " + str(app_name))
    assert "not installed" not in rsp


def stop(target, app_name):
    """!Stop the application.

    @param target: fixture to communicate with the target
    @param app_name: name of the application

    @ingroup legatoGroup
    """
    target.run("/legato/systems/current/bin/app stop " + str(app_name))


def runProc(target, app_name, proc, *args):
    """!Run an app proc."""
    cmd = "/legato/systems/current/bin/app runProc %s %s -- %s &" % (
        app_name,
        proc,
        " ".join(args),
    )
    target.run(cmd, 10)


def restart(target, app_name):
    """!Restart the application."""
    rsp = target.run("/legato/systems/current/bin/app restart " + str(app_name))
    assert "not installed" not in rsp


def verify_app_version(app_name, target, expected_version):
    """!Check the application version."""
    rsp = target.run("/legato/systems/current/bin/app version %s" % (app_name))
    assert expected_version in rsp, "Application version not as expected"


def remove(target, app_name):
    """!Remove the application.

    @param target: fixture to communicate with the target
    @param app_name: application name

    @return None

    @exception AssertionError

    @ingroup legatoGroup
    """
    _exit, rsp = target.run(
        "/legato/systems/current/bin/app remove %s" % (app_name),
        check=False,
        withexitstatus=1,
    )
    assert _exit == 0, "Impossible to remove the application: %s" % rsp


def remove_all(target):
    """!Remove all the application.

    @param target: fixture to communicate with the target

    @return None

    @exception AssertionError

    @ingroup legatoGroup
    """
    app_list = get_app_list(target)
    for i in app_list:
        remove(target, i)
        rsp = is_app_exist(target, i)
        assert rsp is False


def clean(target, app_name, remove_file=True, remove_app=True):
    """!Clean the application on target and the build on host.

    @param target: fixture to communicate with the target.
    @param app_name: name of the application.
    @param remove_file: clean the build directory or not.
    @param remove_app: remove the application or not.
    @return None

    @exception AssertionError

    @ingroup legatoGroup
    """
    if remove_file:
        swilog.info("Clean build")
        os.system(
            r"rm -rf _build_%s %s\.%s\.update"
            % (app_name, app_name, target.target_name)
        )

    if remove_app:
        remove(target, app_name)


def ssh_to_target(target, cmd, output=False):
    """!SSH command to the target.

    legato.ssh_to_target (if the legato fixture is used) or
    "app.ssh_to_target" (if app.py is imported).
    """
    complete_cmd = '/bin/bash -c "ssh %s -p %s root@%s %s"' % (
        target.ssh_opts,
        target.ssh_port,
        target.target_ip,
        cmd,
    )
    swilog.info("Execute: %s" % complete_cmd)
    if output is False:
        _exit = subprocess.call(complete_cmd, shell=True)
        swilog.info("Exit: %s" % _exit)
        return int(_exit)
    else:
        rsp = subprocess.check_output(complete_cmd, shell=True).decode("utf-8")
        swilog.info("Response: %s" % rsp)
        return rsp


## @}

##@defgroup legatoLogs Legato logs
# Handle on target legato logs.
# @{
def find_in_target_log(target, pattern, grep_options=""):
    """!Find a pattern in the target logs."""
    rsp = ssh_to_target(
        target, '/sbin/logread | grep %s \\"%s\\"' % (grep_options, pattern)
    )
    return rsp == 0


def get_from_target_log(target, pattern):
    """!Get the target logs matched a pattern."""
    rsp = target.run("/sbin/logread")
    result_regexp = re.search(pattern, rsp)
    return result_regexp


def clear_target_log(target):
    """!Clear the target logs."""
    cmd = (
        "PATH=/legato/systems/current/bin:/usr/local/bin:"
        "/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin /etc/init.d/syslog restart"
    )
    target.run(cmd)
    if hasattr(target, "ssh_logread") and target.ssh_logread:
        # restart syslog could kill the logread -f
        # Init again the logread
        target.ssh_logread.close()
        target.ssh_logread.reinit()
        target.ssh_logread.sendline("logread -f")


def display_target_log(target):
    """!Display the target logs."""
    ssh_to_target(target, "/sbin/logread | cut -d '|' -f 3-")


def wait_for_log_msg(target, pattern, timeout, grep_options=""):
    """!Wait for a pattern in the target logs."""
    found = False
    count = timeout
    while count > 0:
        found = find_in_target_log(target, pattern, grep_options)
        if found is True:
            break
        count -= 1
        time.sleep(1)
    return found


## @}

##@defgroup legatoSystems Legato systems commands.
# Issue legato system commands.
# @{
def get_current_system_index(target):
    """!Get the Current system index."""
    index = target.run("/bin/cat /legato/systems/current/index")
    swilog.info("Current system index:%s " % index)
    return int(index)


def get_current_system_status(target):
    """!Get the Current system index."""
    status = target.run("/bin/cat /legato/systems/current/status")
    swilog.info("Current system status:%s " % status)
    return status


def legato_start(target, timeout=40):
    """!Start Legato."""
    rsp = target.run("/legato/systems/current/bin/legato start", timeout)
    return rsp


def legato_restart(target, timeout=40):
    """!Restart Legato."""
    rsp = target.run("/legato/systems/current/bin/legato restart", timeout)
    return rsp


def legato_stop(target, timeout=60):
    """!Stop Legato."""
    rsp = target.run("/legato/systems/current/bin/legato stop", timeout)
    return rsp


def get_legato_status(target):
    """!Get Legato status."""
    rsp = target.run("/legato/systems/current/bin/legato status", check=False)
    return rsp


def get_legato_version(target):
    """!!Get Legato version."""
    rsp = target.run("/legato/systems/current/bin/legato version", check=False)
    return rsp


def restore_golden_legato(target, timeout=60):
    """!Restore the stable legato."""
    legato_stop(target)
    target.run("/bin/rm -rf /legato/apps /legato/systems")
    target.reboot(timeout)
    current_system_index = get_current_system_index(target)
    swilog.info("Current system index is %s" % current_system_index)
    assert current_system_index == 0


def get_app_status(target, app_name):
    """!Get the app status."""
    rsp = target.run("/legato/systems/current/bin/app status %s" % (app_name))
    return rsp


def get_app_info(target, app_name):
    """!Get App information."""
    rsp = target.run("/legato/systems/current/bin/app info %s" % (app_name))
    return rsp


def set_probation_timer(target, ptimer):
    """!Set Legato app probation timer.

    @param target: fixture to communicate with the target
    @param ptimer: number of seconds
    """
    timer = ptimer * 1000
    cmd = (
        "export LE_PROBATION_MS=%s; " % str(timer)
        + "/legato/systems/current/bin/legato stop; "
        + "/legato/systems/current/bin/legato start"
    )
    cmd_exit, _ = target.run(cmd, withexitstatus=1)
    time.sleep(5)
    return cmd_exit


def reset_probation_timer(target):
    """!Reset Legato app probation timer."""
    cmd = (
        "unset LE_PROBATION_MS; /legato/systems/current/bin/legato stop; "
        "/legato/systems/current/bin/legato start"
    )
    cmd_exit, _ = target.run(cmd, withexitstatus=1)
    time.sleep(5)
    return cmd_exit


def full_legato_restart(target):
    """!Restart legato framework."""
    cmd = "/legato/systems/current/bin/legato stop"
    target.run(cmd, withexitstatus=1)
    cmd = "/legato/systems/current/bin/legato start"
    target.run(cmd, withexitstatus=1)
    time.sleep(10)  # give time for framework to start


def check_current_system_info(target, version="", status="", index=""):
    """!Check current Legato system status."""
    _exit_code = 0
    if version != "":
        current_version = get_legato_version(target)

        # If version does not contains md5 string.
        # Need to get the current_version without md5 string also.
        search_md5 = re.search(r"(.*)_([\d\w]{20,})", version)
        if not search_md5:
            search_current_md5 = re.search(r"(.*)_([\d\w]{20,})", current_version)
            if search_current_md5:
                current_version = search_current_md5.group(1)

        if current_version.strip() != version.strip():
            swilog.error(
                "[FAILED] Mismatch system version [Expected: %s, Actual: %s]."
                % (version, current_version)
            )
            _exit_code = 1
    if status != "":
        current_status = get_current_system_status(target)
        if current_status != status:
            swilog.error(
                "[FAILED] Mismatch system status [Expected: %s, Actual: %s]."
                % (status, current_status)
            )
            _exit_code = 1
    if status != "":
        current_index = get_current_system_index(target)
        if current_index != index:
            swilog.error(
                "[FAILED] Mismatch system index [Expected: %s, Actual: %s]."
                % (str(index), str(current_index))
            )
            _exit_code = 1
    return _exit_code


def wait_for_system_to_start(target, indx, time_wait=100):
    """!Wait for System to start."""
    swilog.info("Waiting for System to start")
    time_past = 0
    while time_wait > time_past:
        if get_current_system_index(target) == indx:
            return 0
        time_past += 1
        time.sleep(1)
    return 1


def reboot_target(target):
    """!Wait for target to reboot."""
    swilog.info("Reboot the target, be sure that UART is released ... ")
    target.reboot()


## @}


##@defgroup legatoHostTools Legato host tools
# Legato tools on the host.
# @{
def _wait_for_legato_start():
    time.sleep(10)


def update_legato_cwe(target, file_path, timeout=120):
    """!Install a cwe file with fwupdate.

    @param target: fixture to communicate with the target
    @param file_path: path of the file to install
    @param timeout: in second

    @return None

    @exception AssertionError

    @ingroup legatoGroup
    """
    cmd = "fwupdate download %s %s" % (file_path, target.target_ip)
    swilog.info(cmd)
    rsp_update, _exit = pexpect.run(
        cmd, encoding="utf-8", timeout=120, withexitstatus=1
    )
    swilog.info(rsp_update)
    assert (
        "Download successful" in rsp_update
    ), "[FAILED] Failed to update legato binary"
    swilog.info("[PASSED] Update legato binary.")
    target.wait_for_reboot(timeout=timeout)
    _wait_for_legato_start()


def check_legato_env():
    """!Check environment variable existence."""
    assert os.environ.get("LEGATO_ROOT") is not None, (
        "LEGATO_ROOT variable "
        "does not exist. "
        "Please configure your"
        " legato environment"
    )


## @}


class LegatoManager:
    """!Manage the legato app related commands."""

    def __init__(self, target):
        self.target = target

    def make(self, app_name, app_path="", should_fail=False, option="", timeout=600):
        """!Make a Legato application.

        @param app_name: name of the application
        @param app_path: path of the application
        @param should_fail: make is expected to fail
        @param option: extra mkapp options
        @param timeout: timeout

        @return make stdout if success

        @exception AssertionError: If make not accorded to should_fail param

        @ingroup legatofixGroup
        """
        return make(
            self.target.target_name, app_name, app_path, should_fail, option, timeout
        )

    def install(self, app_name, app_path="", signed=False, should_fail=False):
        """!Install a Legato application.

        @param app_name: name of the application
        @param signed: set to 1 if installing signed app, 0 otherwise
        @param app_path: path of the application
        @param timeout: allowed time to install the app

        @return: None

        @exception AssertionError: if installation error

        @ingroup legatofixGroup
        """
        install(
            self.target.target_name,
            self.target.target_ip,
            app_name,
            app_path,
            signed,
            should_fail,
        )

    def install_legato(self):
        """!Install a legato system (.update) on target.

        @return: None

        @exception AssertionError: if installation error

        @ingroup legatofixGroup
        """
        install_legato(self.target.target_name, self.target.target_ip)

    def make_install(self, app_name, app_path="", option=""):
        """!Make and install a Legato application.

        @param app_name: name of the application
        @param app_path: path of the application
        @param option: extra mkapp options

        @return: None

        @exception AssertionError: if error

        @ingroup legatofixGroup
        """
        make_install(
            self.target.target_name, self.target.target_ip, app_name, app_path, option
        )

    def version_validity(self, ver):
        """!Check if version string is md5.

        @param ver: version to check

        @return 1 if version found, 0 instead
        """
        version_validity(ver)

    def is_app_exist(self, app_name, ver=""):
        """!Check if the application exists.

        @param app_name: name of the application
        @param ver: version of the application

        @return True if the application exists

        @ingroup legatofixGroup
        """
        return is_app_exist(self.target, app_name, ver)

    def is_app_installed(self, app_name, ver=""):
        """!Check if an app with the given name exists (and optional version).

        @param app_name: name of the application
        @param ver: version of the application

        @return True if the application exists

        @ingroup legatofixGroup
        """
        return is_app_installed(self.target, app_name, ver)

    def are_apps_installed(self, apps):
        """!Check if apps with the given name exists.

        The format is either {app_name: version, ...} or [app_name, ...]

        @ingroup legatofixGroup
        """
        return are_apps_installed(self.target, apps)

    def is_app_running(self, app_name):
        """!Check the application is running.

        @param app_name: name of the application

        @return True if the application is running, False instead and
                None if it was not possible to determine the status.

        @ingroup legatofixGroup
        """
        return is_app_running(self.target, app_name)

    def are_apps_running(self, app_names):
        """!Check the applications are running.

        @param app_name: Application names on legato

        @return True if all applications are running, False instead and
            None if it was not possible to determine the status.

        @ingroup legatofixGroup
        """
        return are_apps_running(self.target, app_names)

    def get_app_list(self):
        """!Get a list of the applications on the target."""
        return get_app_list(self.target)

    def start(self, app_name):
        """!Start the application.

        @param app_name: Application names on legato

        @exception AssertionError

        @ingroup legatofixGroup
        """
        return start(self.target, app_name)

    def stop(self, app_name):
        """Stop the application.

        Args:
            app_name: name of the application

        @ingroup legatofixGroup
        """
        return stop(self.target, app_name)

    def runProc(self, app_name, proc, *args):
        """!Run an app proc."""
        return runProc(self.target, app_name, proc, *args)

    def restart(self, app_name):
        """!Restart the application."""
        return restart(self.target, app_name)

    def verify_app_version(self, app_name, expected_version):
        """!Check the application version."""
        return verify_app_version(app_name, self.target, expected_version)

    def remove(self, app_name):
        """!Remove the application.

        @param app_name: application name

        @return None

        @exception AssertionError

        @ingroup legatofixGroup
        """
        return remove(self.target, app_name)

    def remove_all(self):
        """Remove all the application.

        @return None

        @exception AssertionError

        @ingroup legatofixGroup
        """
        return remove_all(self.target)

    def clean(self, app_name, remove_file=True, remove_app=True):
        """Clean the application on target and the build on host.

        @param app_name: name of the application
        @param remove_only: only remove the application. Do not clean the build directory

        @return None

        @exception AssertionError

        @ingroup legatofixGroup
        """
        return clean(self.target, app_name, remove_file, remove_app)

    def ssh_to_target(self, cmd, output=False):
        """!SSH command to the target."""
        return ssh_to_target(self.target, cmd, output)

    def find_in_target_log(self, pattern, grep_options=""):
        """!Find a pattern in the target logs."""
        return find_in_target_log(self.target, pattern, grep_options)

    def get_from_target_log(self, pattern):
        """!Get the target logs matched a pattern."""
        return get_from_target_log(self.target, pattern)

    def clear_target_log(self):
        """!Clear the target logs."""
        return clear_target_log(self.target)

    def display_target_log(self):
        """!Display the target logs."""
        return display_target_log(self.target)

    def wait_for_log_msg(self, pattern, timeout, grep_options=""):
        """!Wait for a pattern in the target logs."""
        return wait_for_log_msg(self.target, pattern, timeout, grep_options)

    def wait_for_system_to_start(self, indx, time_wait=100):
        """!Wait for System to start."""
        return wait_for_system_to_start(self.target, indx, time_wait)

    def reboot_target(self):
        """!Wait for target to reboot."""
        return reboot_target(self.target)

    def get_current_system_index(self):
        """!Get the Current system index."""
        return get_current_system_index(self.target)

    def get_current_system_status(self):
        """!Get the Current system index."""
        return get_current_system_status(self.target)

    def legato_start(self, timeout=40):
        """!Start Legato."""
        return legato_start(self.target, timeout)

    def legato_restart(self, timeout=40):
        """!Restart Legato."""
        return legato_restart(self.target, timeout)

    def legato_stop(self, timeout=60):
        """!Stop Legato."""
        return legato_stop(self.target, timeout)

    def get_legato_status(self):
        """!Get Legato status."""
        return get_legato_status(self.target)

    def get_legato_version(self):
        """!Get Legato version."""
        return get_legato_version(self.target)

    def restore_golden_legato(self, timeout=120):
        """!Restore the stable legato."""
        return restore_golden_legato(self.target, timeout)

    def get_app_status(self, app_name):
        """!Get the app status."""
        return get_app_status(self.target, app_name)

    def get_app_info(self, app_name):
        """!Get App information."""
        return get_app_info(self.target, app_name)

    def make_sys(
        self,
        sys_name,
        sys_path="",
        append_to_version="",
        should_fail=False,
        option="",
        quiet=False,
    ):
        """!Make a system.

        @param sys_name: name of the system definition file
        @param sys_path: path of the  system definition file
        @param append_to_version: string to append to version
        @param should_fail: make is expected to fail
        @param option: extra mksys options
        @param quiet: if True, do not produce logs

        @return stdout of mksys

        @exception AssertionError

        @ingroup legatofixGroup
        """
        return make_sys(
            self.target.target_name,
            sys_name,
            sys_path,
            append_to_version,
            should_fail,
            option,
            quiet,
        )

    def install_sys(self, sys_name, sys_path="", quiet=False, timeout=60):
        """!Install a system.

        @param sys_name: name of the system definition file
        @param sys_path: path of the system definition file
        @param quiet: if True, do not produce logs
        @param timeout: timeout for the command.

        @return stdout of mksys

        @exception AssertionError

        @ingroup legatofixGroup
        """
        return install_sys(
            self.target.target_name,
            self.target.target_ip,
            sys_name,
            sys_path,
            quiet,
            timeout,
        )

    def make_install_sys(self, sys_name, sys_path="", quiet=False, timeout=60):
        """!Make and install a Legato system.

        @param sys_name: name of the system definition file
        @param sys_path: path of the system definition file
        @param quiet: if True, do not produce logs
        @param timeout: in seconds

        @return stdout of mksys

        @exception AssertionError

        @ingroup legatofixGroup
        """
        return make_install_sys(
            self.target.target_name,
            self.target.target_ip,
            sys_name,
            sys_path,
            quiet,
            timeout,
        )

    def set_probation_timer(self, ptimer):
        """!Set Legato app probation timer.

        @param ptimer: number of seconds.
        """
        return set_probation_timer(self.target, ptimer)

    def reset_probation_timer(self):
        """!Reset Legato app probation timer."""
        return reset_probation_timer(self.target)

    def full_legato_restart(self):
        """!Restart legato framework."""
        return full_legato_restart(self.target)

    def check_current_system_info(self, version="", status="", index=""):
        """!Check current Legato system status."""
        return check_current_system_info(self.target, version, status, index)

    def update_legato_cwe(self, file_path, timeout=120):
        """!Install a cwe file with fwupdate.

        @param file_path: path of the file to install
        @param timeout: in second


        @Returns None

        @exception AssertionError

        @ingroup legatofixGroup
        """
        return update_legato_cwe(self.target, file_path, timeout)


## Obsolete: will be removed after references cleaning up.
legato_functions = LegatoManager
