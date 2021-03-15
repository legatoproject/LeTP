"""Test target fixture stub.

It validates the function calls in target fixture(objects in modules.py)
"""
from unittest.mock import MagicMock

import pexpect
from pytest_letp.lib import com
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


_TIMEOUT = 120


def _validate_func_call(func, command):
    """Validate function was called."""
    if command:
        expected_call = ((command,),)
    else:
        expected_call = ()
    assert func.call_args == expected_call, "{}({}) Failed to execute".format(
        func.__name__, command
    )


def _validate_cmd_call(func, command):
    """Validate function is called with command."""
    assert isinstance(func, MagicMock), "Did you mock {}?".format(func.__name__)
    if command:
        func(command)
    else:
        func()
    _validate_func_call(func, command)


def test_target_run(target):
    """To test target.run fixture."""
    swilog.info("test target.run")
    cmd = "/bin/uname -a"
    _validate_cmd_call(target.run, cmd)


def test_target_send(target):
    """To test target.send fixture."""
    swilog.info("test target.send")
    _validate_cmd_call(target.send, "logread -f &\r")


def test_target_sendline(target):
    """To test target.sendline fixture."""
    swilog.info("test target.sendline")
    _validate_cmd_call(target.sendline, "cat /etc/hosts")


def test_target_expect(target):
    """To test target.expect fixture."""
    swilog.info("test target.expect")
    _validate_cmd_call(target.expect, (r"Yocto build version: ([\w\d\.-]+)\r\n", 3))


def test_target_expect_exact(target):
    """To test target.expect_exact fixture."""
    swilog.info("test target.expect_exact")
    _validate_cmd_call(target.send, "\r\n")
    expected_prompt = com.PROMPT_swi_qct
    _validate_cmd_call(target.expect_exact, ([pexpect.TIMEOUT, expected_prompt], 3))


def test_target_sendcontrol(target):
    """To test target.sendcontrol fixture."""
    swilog.info("test target.sendcontrol")
    _validate_cmd_call(target.sendcontrol, "c")


def test_target_prompt(target):
    """To test target.wait_for_reboot fixture."""
    swilog.info("test target_wait_for_reboot")
    _validate_cmd_call(target.run, "/sbin/reboot")
    swilog.info("Rebooting.....")
    _validate_cmd_call(target.prompt, ())


def test_target_wait_for_device_up(target):
    """To test target.wait_for_device_up fixture."""
    swilog.info("test target_wait_for_device_up")

    target.wait_for_device_up(_TIMEOUT)
    _validate_func_call(target.slink1.wait_for_device_up, _TIMEOUT)


def test_target_wait_for_device_down(target):
    """To test target.wait_for_device_down fixture."""
    swilog.info("test target_wait_for_device_down")
    _validate_cmd_call(target.run, "/sbin/reboot")
    target.wait_for_device_down(_TIMEOUT)
    _validate_func_call(target.slink1.wait_for_device_down, _TIMEOUT)


def test_target_reinit(target):
    """To test target.reinit fixture."""
    swilog.info("test target.reinit")
    target.wait_for_device_up(_TIMEOUT)
    _validate_func_call(target.slink1.wait_for_device_up, _TIMEOUT)
    _validate_cmd_call(target.close, ())
    _validate_cmd_call(target.reinit, ())


def test_target_login(target):
    """To test target.login fixture."""
    swilog.info("test target_lgin")
    _validate_cmd_call(target.sendcontrol, "c")
    target.login()
    _validate_func_call(target.slink1.login, ())


def test_define_target_with_one_slink(target):
    """Test the target only used one link: slink1."""
    assert target.link1, " slink1 should be used"
    assert target.link2 is None, " slink2 should not be used."
    assert "ssh" not in target.links, " ssh was not enabled."


def test_define_target_with_two_slinks(target):
    """Test the target only used one link: slink1."""
    assert target.link1, " slink1 should be used"
    assert target.link2, " slink2 should be used."
    assert "ssh" not in target.links, " ssh was not enabled."


def test_define_target_with_two_slinks_and_ssh(target):
    """Test the target only used one link: slink1."""
    assert target.link1, " slink1 should be used"
    assert target.link2, " slink2 should be used."
    assert "ssh" in target.links, " ssh was enabled."


def test_define_target_with_only_at(target):
    """Test the target only used one link: slink2."""
    assert target.link1 is None, " slink1 should not be used"
    assert target.link2, " slink2 should be used."
    assert "ssh" not in target.links, " ssh was not enabled."
