# pylint: disable=missing-function-docstring
"""Test legato fixture in pytest_legato.py."""
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_target():
    with patch("pytest_letp.lib.com.target_serial_at", autospec=True), patch(
        "pytest_letp.lib.com.ComPortDevice", autospec=True
    ):
        yield


def test_wait_for_log_msg_value(legato):
    """Test wait for a pattern in the target logs."""
    with patch("pytest_letp.lib.app.ssh_to_target", return_value=0):
        rsp = legato.wait_for_log_msg("write", 10)
        assert rsp, "wait for log msg fails"


def test_get_legato_version_value(legato):
    legato_version = "20.12.0.RC1"
    with patch("pytest_letp.lib.com.target_qct.run_main", return_value=legato_version):
        rsp = legato.get_legato_version()
        assert legato_version == rsp

    octave_legato_version = "OTVFX3.2.0.pre21Dec20"
    with patch(
        "pytest_letp.lib.com.target_qct.run_main", return_value=octave_legato_version
    ):
        rsp = legato.get_legato_version()
        assert octave_legato_version == rsp


def test_get_legato_status_value(legato):
    legato_status = """Systems installed:
        0 [good] <-- current
        Legato framework is running."""
    with patch("pytest_letp.lib.com.target_qct.run_main", return_value=legato_status):
        rsp = legato.get_legato_status()
        assert legato_status == rsp


def test_get_app_info_value(legato):
    app_name = "gpioService"
    app_info = "{} installed".format(app_name)
    with patch("pytest_letp.lib.com.target_qct.run_main", return_value=app_info):
        rsp = legato.get_app_info(app_name)
        assert rsp == app_info


def test_get_app_status_value(legato):
    app_name = "wifi"
    app_status = "[running] {}".format(app_name)
    with patch("pytest_letp.lib.com.target_qct.run_main", return_value=app_status):
        rsp = legato.get_app_status(app_name)
        assert rsp == app_status, "%s is not running" % app_name


def test_check_current_system_info_value(legato):
    legato_version = "20.12.0.RC1"
    with patch("pytest_letp.lib.com.target_qct.run_main", return_value=legato_version):
        rsp = legato.check_current_system_info(legato_version)
        assert rsp == 0, "current system info fails"


def test_find_in_target_log_value(legato):
    with patch("pytest_letp.lib.app.ssh_to_target", return_value=0):
        rsp = legato.find_in_target_log("Client session")
        assert rsp, "Finding a pattern in the target logs fails"


def test_restore_golden_legato_value(legato):
    with patch(
        "pytest_letp.lib.com.target_qct.run_main", side_effect=["OK", 0, 0]
    ), patch("pytest_letp.lib.modules_linux.ModuleLinux.reboot", return_value=0):
        rsp = legato.restore_golden_legato()
        print("rsp value= %s" % rsp)
        assert rsp, "restore golden legato fails"


@pytest.fixture
def mock_run():
    cmd_return = (0, "")
    with patch(
        "pytest_letp.lib.com.target_qct.run_main", return_value=cmd_return
    ), patch("time.sleep"):
        yield


@pytest.mark.usefixtures("mock_run")
def test_full_legato_restart_value(legato):
    rsp = legato.full_legato_restart()
    assert rsp == 0, "full legato restart fails"


@pytest.mark.usefixtures("mock_run")
def test_set_probation_timer_value(legato):
    rsp = legato.set_probation_timer(10)
    assert rsp == 0, "set probation timer fails"


@pytest.mark.usefixtures("mock_run")
def test_reset_probation_timer(legato):
    rsp = legato.reset_probation_timer()
    assert rsp == 0, "reset timer fails"


def test_is_app_running(legato):
    print("test_app_running command:\n")
    with patch(
        "pytest_letp.lib.com.target_qct.run_main",
        return_value=(0, "[running] APP_NAME"),
    ):
        assert legato.is_app_running("secStore") is True
    with patch(
        "pytest_letp.lib.com.target_qct.run_main",
        return_value=(0, "[stopped] APP_NAME"),
    ):
        assert legato.is_app_running("wifi") is False
        assert legato.is_app_running("secStore2") is False


def test_are_apps_running(legato):
    app_status_result = """\r
    [running] secStore\r
    [running] powerMgr\r
    [stopped] wifi\r
    """
    with patch(
        "pytest_letp.lib.com.target_qct.run_main", return_value=(0, app_status_result)
    ):
        assert legato.are_apps_running(["secStore", "powerMgr"]) is True
        assert legato.are_apps_running(["wifi"]) is False


def test_app_installed(legato):
    app_list_return = """secStore"""
    with patch(
        "pytest_letp.lib.com.target_qct.run_main", return_value=(0, app_list_return)
    ):
        assert legato.is_app_exist("secStore") is True
        assert legato.is_app_exist("secStore2") is False


def test_app_installed_with_version(legato):
    wifi_version = "19.02.0.rc2"
    bad_wifi_version = "19.02.0.rc2-3"
    app_list_return = """wifi"""
    with patch(
        "pytest_letp.lib.com.target_qct.run_main",
        side_effect=[
            (0, app_list_return),
            (0, "wifi " + wifi_version),
            (0, app_list_return),
            (0, "wifi " + wifi_version),
        ],
    ):
        assert legato.is_app_exist("wifi", wifi_version) is True
        assert legato.is_app_exist("wifi", bad_wifi_version) is False


def test_apps_installed_with_version(legato):
    wifi_version = "19.02.0.rc2"
    app_list_return = """wifi\r\nsecStore\r\n"""
    with patch(
        "pytest_letp.lib.com.target_qct.run_main",
        side_effect=[
            (0, app_list_return),
            (0, "wifi " + wifi_version),
            (0, "secStore  x"),
        ],
    ):
        assert (
            legato.are_apps_installed({"wifi": wifi_version, "secStore": None}) is True
        )
