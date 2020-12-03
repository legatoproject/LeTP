"""Test command stub module."""
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def test_command(request, read_config):
    """Test command stub.

    Check a parameter or an attribute value given by --path and
    --expected value in the command line are same in the default config
    file.
    """
    assert request
    path = "module/name"
    expected_value = "wp750x"
    swilog.info("path %s\n expected value %s" % (path, expected_value))
    res = read_config.findtext(path)
    swilog.info("Found %s: %s" % (path, res))
    assert res == expected_value, (
        "Expected value not found for %s: expected %s found %s"
        % (path, expected_value, res)
    )


def test_command_json(request, read_config):
    """Test command json stub."""
    test_command(request, read_config)
