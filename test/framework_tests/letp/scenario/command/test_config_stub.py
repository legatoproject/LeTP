"""Test LETP config stub.

Use read_config fixture to validate it's expected.

The stub will be used by LETP unit tests.
"""

import pytest
from pytest_letp.lib import swilog
from pytest_letp.lib.modules import SlinkInfo

__copyright__ = "Copyright (C) Sierra Wireless Inc."


COUNT = 0


def validate_config(expected_iter, read_config):
    """Validate configured values are set correctly in read_config."""
    for cur_path, cur_val in expected_iter:
        swilog.info("path %s expected value %s" % (cur_path, cur_val))
        if "(" in cur_path:
            # It is an attribute
            attr_path = cur_path.split("(")[0]
            attr = cur_path.split("(")[1].replace(")", "")
            res = read_config.find(attr_path).get(attr)
        else:
            # It is a text
            res = read_config.findtext(cur_path)
            swilog.info("Found %s: %s" % (cur_path, res))
        assert str(res) == str(cur_val), (
            "Expected value not found for %s: expected %s found %s"
            % (cur_path, cur_val, res)
        )


def check_config(request, read_config):
    """Check request's path and expected values."""
    path = request.config.getoption("--path")
    expected_value = request.config.getoption("--expected_value")

    if path and expected_value:
        expected_iter = zip(path, expected_value)
        validate_config(expected_iter, read_config)


def test_cmd_config_set(request, read_config):
    """Test config set from command line."""
    check_config(request, read_config)


@pytest.mark.timeout(5)
def test_config_value(request, test_config):
    """Check a parameter or an attribute value.

    The value can be feed by --path and --expected_value in the command
    line.
    """
    test_config_xml = test_config.get()
    check_config(request, test_config_xml)
    main_config_list = test_config.get_main_config()
    valid_configs = [
        tuple(config.split("="))
        for config in main_config_list
        if "=" in config and not config.endswith("=")
    ]
    validate_config(iter(valid_configs), test_config_xml)


def test_config_same_test_with_2_cfg(read_config):
    """Test should be called twice.

    The same test has different xml configuration in the json file.
    """
    global COUNT
    # First time,
    expected_value = "test" if COUNT == 0 else "test2"
    val = read_config.findtext("foo/bar")
    swilog.info("Found value: %s" % val)
    assert val == expected_value


def test_config_two_xml_with_json_file(read_config):
    """Two tests with different xml configuration in the json file."""
    expected_value = "test"
    val = read_config.findtext("foo/bar")
    swilog.info("Found value: %s" % val)
    assert val == expected_value


def test_config_two_xml_with_json_file_2(read_config):
    """Test should be called twice."""
    expected_value = "test2"
    val = read_config.findtext("foo2/bar")
    swilog.info("Found value: %s" % val)
    assert val == expected_value


@pytest.mark.config("$LETP_TESTS/scenario/config/target_wp750x.xml")
def test_config_value_xml(request, read_config):
    """Test with xml file associated within test."""
    check_config(request, read_config)


@pytest.mark.config(
    "$LETP_TESTS/scenario/config/target_wp750x.xml,$LETP_TESTS/scenario/config/foo.xml"
)
def test_config_value_multi_xml(request, read_config):
    """Test with multiple xml file associated within test."""
    check_config(request, read_config)


def test_config_value_with_json_env_vari(request, read_config):
    """Test environment variable in json file.

    If this function gets called that means,
    the system was able to get $LETP_TESTS path and call
    this function from json file,

    $LETP_TESTS is the env variable used in json file.
    """
    assert request
    assert read_config
    swilog.info("env variable was found")


def test_custom_config_tag_with_attri(read_config):
    """Test custom config arguments tag with attribute."""
    assert read_config.findtext("module/slink3/name") == "/dev/ttyUSB6"
    assert read_config.findtext("module/slink1/name/new_tag") == "new_val"
    assert read_config.find("module/slink3").get("used") == "1"
    assert read_config.findtext("module/slink3/desc") == "mcu"
    assert read_config.findtext("custom/new/tag") == "foo"
    assert (
        read_config.find("module/slink1/name/new_tag").get("new_attri")
        == "new_attri_val"
    )


def test_custom_config_attri_only(read_config):
    """Test custom config arguments attribute only."""
    assert read_config.find("module/slink3").get("used") == "1"
    assert read_config.find("capability/avc").get("used") == "1"
    assert read_config.find("custom/new/tag").get("attri") == "1"


def test_custom_config_tag_only(read_config):
    """Test custom config arguments tag only."""
    assert read_config.findtext("module/slink3/name") == "/dev/ttyUSB6"
    assert read_config.findtext("module/slink1/name/new_tag") == "new_val"
    assert read_config.findtext("module/slink3/desc") == "mcu"
    assert read_config.findtext("custom/new/tag") == "foo"


def test_slink_default_val(read_config):
    """Test default slink config val."""
    assert SlinkInfo.get_num_links(read_config) == 3
    link = SlinkInfo(read_config, "module/slink3")

    assert link.desc().lower() == "cli"
    assert link.speed() == 115200
    assert not link.rtscts()
    assert not link.is_used()
