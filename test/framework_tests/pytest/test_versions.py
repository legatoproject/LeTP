"""Test versions.py."""
import re
from unittest.mock import patch
import pytest

from pytest_letp.lib.modules import SwiModule, get_swi_module
from pytest_letp.lib.modules_linux import ModuleLinux
from pytest_letp.lib.versions_linux import LinuxVersions
from pytest_letp.lib.versions import TargetVersions
from testlib.shared_steps import validate_legato_pattern

__copyright__ = "Copyright (C) Sierra Wireless Inc."

LINUX_MODULES = "wp76xx", "wp77xx", "wp85", "ar759x", "ar758x"
VERSION_ATTR = "legato_version", "modem_version", "linux_version"


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_create_versions_obj(module_name):
    """Test version obj creation."""
    module = get_swi_module(module_name.upper())
    assert module.get_version_obj()
    assert isinstance(module.get_version_obj(), LinuxVersions)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
@pytest.mark.parametrize("version_attr", VERSION_ATTR)
def test_version_attr(module_name, version_attr):
    """Test version class supported versions."""
    module = get_swi_module(module_name.upper())
    assert hasattr(module, version_attr)


def test_legato_version_pattern():
    """Test legato version pattern."""
    version = "20.04.0"
    invalid_version = "2.4.abcd"

    pattern = SwiModule.legato_pattern["full"]
    assert (
        re.match(pattern, version) is not None
    ), "{} doesn't match the pattern: {}".format(version, pattern)
    assert re.match(pattern, invalid_version) is None, "{} shouldn't be matched".format(
        version
    )

    version = "OTVFX3.2.0"

    pattern = SwiModule.legato_pattern["full"]
    assert (
        re.match(pattern, version) is not None
    ), "{} doesn't match the pattern: {}".format(version, pattern)
    assert re.match(pattern, invalid_version) is None, "{} shouldn't be matched".format(
        version
    )


def test_modem_version_pattern():
    """Test modem version pattern."""
    version = "SWI9X07H_00.02.21.00"
    invalid_version = "SWI9X07H00.02.21.0"

    pattern = SwiModule.modem_pattern["full"]
    assert (
        re.match(pattern, version) is not None
    ), "{} doesn't match the pattern: {}".format(version, pattern)
    assert re.match(pattern, invalid_version) is None, "{} shouldn't be matched".format(
        version
    )


def test_linux_version_pattern():
    """Test linux version pattern."""
    version = "LXSWI2.5-13.0"
    invalid_version = "LXSWI2513.0"

    pattern = ModuleLinux.linux_pattern["full"]
    assert (
        re.match(pattern, version) is not None
    ), "{} doesn't match the pattern: {}".format(version, pattern)
    assert re.match(pattern, invalid_version) is None, "{} shouldn't be matched".format(
        version
    )


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_legato_version(module_name):
    """Test get_legato_version."""
    with patch("pytest_letp.lib.versions_linux.LinuxVersions.get_version") as mock:
        exp_ver = "20.04.0"
        instance = mock.return_value
        instance.method.return_value = exp_ver
        module = get_swi_module(module_name.upper())
        ret_ver = LinuxVersions().get_legato_version(target=module).method()
        assert ret_ver == exp_ver, "Exp: {} but ret: {}".format(exp_ver, ret_ver)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_modem_version(module_name):
    """Test get_modem_version."""
    exp_ver = "SWI9X07H_00.02.21.00"

    with patch("pytest_letp.lib.versions_linux.LinuxVersions.get_version") as mock:
        instance = mock.return_value
        instance.method.return_value = exp_ver
        module = get_swi_module(module_name.upper())
        ret_ver = LinuxVersions().get_modem_version(target=module).method()
        assert ret_ver == exp_ver, "Exp: {} but ret: {}".format(exp_ver, ret_ver)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_linux_version(module_name):
    """Test get_linux_version."""
    exp_ver = "LXSWI2.5-13.0"

    with patch("pytest_letp.lib.versions_linux.LinuxVersions.get_version") as mock:
        instance = mock.return_value
        instance.method.return_value = exp_ver
        module = get_swi_module(module_name.upper())
        ret_ver = LinuxVersions().get_linux_version(target=module).method()
        assert ret_ver == exp_ver, "Exp: {} but ret: {}".format(exp_ver, ret_ver)


@pytest.mark.parametrize("module_name", LINUX_MODULES)
def test_fw_mismatch(module_name):
    """Test is_fw_matched."""
    with patch("pytest_letp.lib.versions_linux.TargetVersions.get_version") as mock:
        instance = mock.return_value
        instance.method.return_value = "SWI9X07H_00.02.21.00"
        module = get_swi_module(module_name.upper())
        assert TargetVersions().is_fw_matched(target=module)


def test_parsed_legato_version_pattern():
    """Test parsed legato version pattern."""
    version_dict = {
        "20.08.0.rc1": "20.08.0.rc1",
        "20.08.0.rc10": "20.08.0.rc10",
        "20.08.0.m2.rc1": "20.08.0.m2.rc1",
        "20.11.0.rc1_91190a17": "20.11.0.rc1",
        "20.08.0": "20.08.0",
        "20.08.0-123456": "20.08.0",
        "20.08.0_123456": "20.08.0",
        "20.08.0.rc1custom_d123456": "20.08.0.rc1custom",
        "20.08.0.rc1custom-d123456": "20.08.0.rc1custom",
        "20.08.0.rc1custom_d123456_modified": "20.08.0.rc1custom",
        "20.08.0.rc1custom-d123456_modified": "20.08.0.rc1custom",
        "OTVFX3.2.0.pre21Dec20": "OTVFX3.2.0.pre21Dec20",
        "OTVFX3.2.0.pre21Dec20_653d8": "OTVFX3.2.0.pre21Dec20",
        "OTVFX3.2.0.pre21Dec20_653d8_modified": "OTVFX3.2.0.pre21Dec20",
    }
    validate_legato_pattern(version_dict)
