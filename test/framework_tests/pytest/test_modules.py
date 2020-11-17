# pylint: disable=missing-function-docstring
"""Test letp target fixture and modules.py.

Using mock module to simulate com connections.
"""
import os
import sys
import re
from unittest.mock import patch

import pytest

import swilog
from modules import SwiModule, get_swi_module, get_swi_module_files
from testlib import run_python_with_command
from testlib.util import check_letp_nb_tests, get_log_file_name
from versions import TargetVersions

__copyright__ = "Copyright (C) Sierra Wireless Inc."

LINUX_MODULES = "wp76xx", "wp77xx", "wp85", "ar759x", "ar758x"


@pytest.mark.parametrize(
    "test_case",
    [
        "test_target_run",
        "test_target_sendline",
        "test_target_send",
        "test_target_expect",
        "test_target_expect_exact",
        "test_target_sendcontrol",
        "test_target_prompt",
        "test_target_wait_for_device_up",
        "test_target_wait_for_device_down",
        "test_target_reinit",
        "test_target_login",
    ],
)
def test_module_init(letp_cmd, test_case):
    with patch("com.target_serial_qct", autospec=True), patch(
        "com.ComPortDevice", autospec=True
    ):
        cmd = (
            "{} run -d 0 "
            "scenario/command/test_target_fixtures_stub.py::"
            "{} ".format(letp_cmd, test_case) + "--config module/slink1(used)=1"
        )
        print("Start command:\n%s" % cmd)
        output = run_python_with_command(cmd)
        print("*After pexpect ****")
        log_file_name = get_log_file_name(output)
        print("Found log file: %s ", log_file_name)


def _run_test_define_target_with_one_slink(letp_cmd, module_name):
    cmd = (
        "{} run -d 0 ".format(letp_cmd)
        + "scenario/command/test_target_fixtures_stub.py::"
        "test_define_target_with_one_slink "
        "--config module/slink1(used)=1 "
        "--config host/ip_address=10.1.4.59 "
        "--config module/ssh(used)=0 "
        "--config module/name={} ".format(module_name)
    )
    output = run_python_with_command(cmd)
    swilog.debug(output)
    check_letp_nb_tests(output, number_of_passed=1)


def _run_test_define_target_with_two_slinks(letp_cmd, module_name):
    cmd = (
        "{} run -d 0 ".format(letp_cmd)
        + "scenario/command/test_target_fixtures_stub.py::"
        "test_define_target_with_two_slinks "
        "--config module/slink1(used)=1 "
        "--config module/slink2(used)=1 "
        "--config host/ip_address=10.1.4.59 "
        "--config module/ssh(used)=0 "
        "--config module/name={} ".format(module_name)
    )
    output = run_python_with_command(cmd)
    swilog.debug(output)
    check_letp_nb_tests(output, number_of_passed=1)


def _run_test_define_target_with_only_at(letp_cmd, module_name):
    cmd = (
        "{} run -d 0 ".format(letp_cmd)
        + "scenario/command/test_target_fixtures_stub.py::"
        "test_define_target_with_only_at "
        "--config module/slink2(used)=1 "
        "--config host/ip_address=10.1.4.59 "
        "--config module/ssh(used)=0 "
        "--config module/name={} ".format(module_name)
    )
    output = run_python_with_command(cmd)
    swilog.debug(output)
    check_letp_nb_tests(output, number_of_passed=1)


def _run_test_define_target_with_two_slinks_and_ssh(letp_cmd, module_name):
    cmd = (
        "{} run -d 0 ".format(letp_cmd)
        + "scenario/command/test_target_fixtures_stub.py::"
        "test_define_target_with_two_slinks_and_ssh "
        "--config module/slink1(used)=1 "
        "--config module/slink2(used)=1 "
        "--config host/ip_address=10.1.4.59 "
        "--config module/ssh(used)=1 "
        "--config module/name={} ".format(module_name)
    )
    output = run_python_with_command(cmd)
    swilog.debug(output)
    check_letp_nb_tests(output, number_of_passed=1)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_define_target_linux_cli_only(letp_cmd, module_name):
    with patch("com.target_serial_qct", autospec=True), patch(
        "com.ComPortDevice", autospec=True
    ):
        _run_test_define_target_with_one_slink(letp_cmd, module_name)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_define_target_linux_at_only(letp_cmd, module_name):
    with patch("com.target_serial_at", autospec=True), patch(
        "com.ComPortDevice", autospec=True
    ):
        _run_test_define_target_with_only_at(letp_cmd, module_name)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_define_target_linux_two_links(letp_cmd, module_name):
    with patch("com.target_serial_at", autospec=True), patch(
        "com.target_serial_qct", autospec=True
    ), patch("com.ComPortDevice", autospec=True):
        _run_test_define_target_with_two_slinks(letp_cmd, module_name)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_define_target_linux_two_links_and_ssh(letp_cmd, module_name):
    with patch("com.target_serial_at", autospec=True), patch(
        "com.target_serial_qct", autospec=True
    ), patch("com.target_ssh_qct", autospec=True), patch(
        "com.ComPortDevice", autospec=True
    ):
        _run_test_define_target_with_two_slinks_and_ssh(letp_cmd, module_name)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_get_swi_module(module_name):
    get_swi_module(module_name.upper())


def test_get_swi_module_files():
    """Test the messed up sys.path."""
    current_path = os.path.abspath(__file__)
    if current_path not in sys.path:
        sys.path.append(current_path)
    assert get_swi_module_files()
    if current_path in sys.path:
        sys.path.remove(current_path)


def test_parsed_legato_version_pattern():
    """Test parsed legato version pattern."""
    pattern = SwiModule.legato_pattern["parsed"]

    version_dict = {
        "20.08.0.rc1": "20.08.0.rc1",
        "20.08.0.ThreadX.rc1": "20.08.0.ThreadX.rc1",
        "20.08.0.rc10": "20.08.0.rc10",
        "20.08.0.m2.rc1": "20.08.0.m2.rc1",
        "20.10.0.FreeRTOS.rc1-6-gdd343458f3_5fe8799e5": "20.10.0.FreeRTOS.rc1",
        "20.11.0.rc1_91190a17": "20.11.0.rc1",
        "20.08.0.RTOS.rc1_123456": "20.08.0.RTOS.rc1",
        "20.08.0": "20.08.0",
        "20.08.0.RTOS.rc1-123456": "20.08.0.RTOS.rc1",
        "20.08.0-123456": "20.08.0",
        "20.08.0_123456": "20.08.0",
        "20.08.0.ThreadX.rc1-123456": "20.08.0.ThreadX.rc1",
        "20.08.0.ThreadX.rc1_123456": "20.08.0.ThreadX.rc1",
        "20.08.0.rc1custom_d123456": "20.08.0.rc1custom",
        "20.08.0.rc1custom-d123456": "20.08.0.rc1custom",
        "20.08.0.rc1custom_d123456_modified": "20.08.0.rc1custom",
        "20.08.0.rc1custom-d123456_modified": "20.08.0.rc1custom",
    }

    for version_str, expected_version in version_dict.items():
        match_obj = re.search(pattern, version_str)
        version = TargetVersions._match_version(match_obj)
        assert (
            version == expected_version
        ), "{} doesn't match the expected version: {}".format(version, expected_version)
