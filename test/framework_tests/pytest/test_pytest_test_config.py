"""Test pytest_test_config.py."""
import os
import pytest

from pytest_test_config import TestConfig, LeTPConfigPath

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def test_two_targets_config():
    """Test two targets test configuration."""
    cmd_line_cfgs = ["config/target.xml", "config/target2.xml"]
    test_config = TestConfig().build_default_config(cmd_line_cfgs)
    assert test_config
    test_config.save_test_cfg_cache()


def test_one_target_config():
    """Test one target xml test configuration."""
    default_cfg_file = "config/target.xml"
    test_config = TestConfig()
    test_config.create_cfg_xml([default_cfg_file])
    test_config.save_test_cfg_cache()


@pytest.mark.parametrize(
    "module_name", ["ar7582", "ar7594", "virt", "wp7502", "wp7601", "wp7702", "wp8548"]
)
def test_find_matched_module_config(module_name):
    """Test the module config can be find correctly.

    e.g. ar7582 -> ar758x.xml
    """
    config = "config/module/{}.xml".format(module_name)
    xml_file = LeTPConfigPath(config).resolve_xml()
    assert os.path.exists(xml_file)
