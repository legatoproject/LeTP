"""Test pytest fields in the config file."""
import testlib.util as util
from testlib import run_python_with_command

import pytest

__copyright__ = "Copyright (C) Sierra Wireless Inc."


@pytest.fixture(scope="session")
def default_command(letp_cmd):
    """Have a default command."""
    return (
        "{} run --dbg-lvl 0 ".format(letp_cmd)
        + "scenario/command/test_config_stub.py::test_config_value"
    )


def test_default_value(default_command):
    """Ensure the default value used in the tests."""
    # list with the following: [parameter, value]
    checklist = [
        ["module/slink1/name", "/dev/ttyUSB0"],
        ["module/ssh/ip_address", "192.168.2.2"],
        ["module/ssh/network_if", "ecm0"],
    ]
    for path, expected_value in checklist:
        # Check that default value is 0
        cmd = "{} --path {} --expected_value {}".format(
            default_command, path, expected_value
        )
        print("Start command:\n%s" % cmd)
        run_python_with_command(cmd)


@pytest.mark.parametrize("module_name", ["wp76xx", "ar758x"])
def test_config_module(default_command, module_name):
    """Change the value of a parameter."""
    path = "module/name"
    expected_value = module_name
    cmd = (
        "%s --config %s=%s"
        " --path %s --expected_value %s --path %s --expected_value %s"
        % (
            default_command,
            path,
            expected_value,
            path,
            expected_value,
            "module/generic_name",
            expected_value,
        )
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


def test_config_ssh_key_value(default_command):
    """Override specific value key="value"."""
    path = "module/ssh(used)"
    # Override key with --config
    expected_value = "1"
    cmd = (
        "%s "
        "--config %s=%s"
        " --path %s --expected_value %s"
        % (default_command, path, expected_value, path, expected_value)
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


@pytest.mark.parametrize(
    "set_value, config, expected_value",
    [
        pytest.param(
            "module/ssh(used)=1",
            "scenario/config/foo.xml",
            [["module/ssh(used)", "1"], ["foo/bar", "test"]],
            id="set_ssh_and_xml",
        ),
        pytest.param(
            "module/ssh(used)=1",
            "module/slink1(used)=1,module/ssh/port=23,scenario/config/foo.xml",
            [["module/ssh(used)", "1"], ["module/ssh/port", "23"], ["foo/bar", "test"]],
            id="set_ssh_slink1_and_xml",
        ),
        # Parameter change
        pytest.param(
            "module/name=ar7594",
            "scenario/config/foo.xml",
            [["module/name", "ar7594"], ["foo/bar", "test"]],
            id="set_module_name_and_xml",
        ),
        pytest.param(
            "module/slink1/name=/dev/ttyUSB50",
            "scenario/config/foo.xml",
            [["module/slink1/name", "/dev/ttyUSB50"], ["foo/bar", "test"]],
            id="set_slink_name_and_xml",
        ),
        pytest.param(
            "module/name=ar7594",
            "scenario/config/target_ar759x.xml",
            [
                ["module/name", "ar7594"],
                ["module/ssh/ip_address", "192.168.0.100"],
                ["module/ssh/network_if", "ecm1"],
            ],
            id="set_module_name_ar7594_and_xml",
        ),
        pytest.param(
            "scenario/config/foo.xml",
            "scenario/config/target_ar759x.xml,module/slink1/name=/dev/ttyUSB60",
            [
                ["module/name", "ar7594"],
                ["foo/bar", "test"],
                ["module/slink1/name", "/dev/ttyUSB60"],
            ],
            id="set_slink_and_xmls",
        ),
    ],
)
def test_config_value(default_command, set_value, config, expected_value):
    """Override specific value with key="value", xml files or param=value with.

    --config The 3 kinds of values (key, xml file and param) can be at the
    beginning, in the middle or at the end of --config, separated with comma Or
    --config can be used several times.
    """
    full_path_value_list = [
        "--path %s --expected_value %s" % (value[0], value[1])
        for value in expected_value
    ]
    check_values = " ".join(full_path_value_list)
    # Check with value at the beginning of --config
    cmd = (
        "%s "
        "--config %s,%s"
        " %s" % (default_command, set_value, config, check_values)
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)

    # Check with value at the end of --config
    cmd = (
        "%s "
        "--config %s,%s"
        " %s" % (default_command, config, set_value, check_values)
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)

    # Check with multiple --config before value
    split_config = " --config ".join(config.split(","))
    cmd = (
        "%s "
        "--config %s --config %s"
        " %s" % (default_command, split_config, set_value, check_values)
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)

    # Check with multiple --config after value
    cmd = (
        "%s "
        "scenario/command/test_config_stub.py::test_config_value "
        "--config %s --config %s"
        " %s" % (default_command, set_value, split_config, check_values)
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)

    # Check with value not at the start or at the beginning of the --config
    cfg = config.split(",")
    cfg.insert(1, set_value)
    split_config = " --config ".join(cfg)
    cmd = "%s " "--config %s %s" % (default_command, split_config, check_values)
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


def test_config_create_new_param(default_command):
    """Create a new config value with --config should not be possible."""
    path = "module/ssh/key"
    expected_value = "uKp3jN"
    cmd = "%s --config %s=%s --path %s --expected_value %s" % (
        default_command,
        path,
        expected_value,
        path,
        None,
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


@pytest.mark.parametrize(
    "json_file, expected_value",
    [
        # With config in the test (config section)
        (
            "scenario/command/runtest/target_wp750x.json",
            [
                ("module/name", "wp750x"),
                ("module/ssh(used)", "1"),
                ("module/ssh/ip_address", "192.168.2.102"),
                ("module/slink1/name", "/dev/ttyUSB40"),
            ],
        ),
        # with main_config at the beginning of the json file (main_config section)
        (
            "scenario/command/runtest/target_ar7594.json",
            [
                ("module/name", "ar7594"),
                ("module/ssh(used)", "0"),
                ("module/ssh/ip_address", "192.168.0.100"),
                ("module/slink1/name", "/dev/ttyUSB70"),
            ],
        ),
    ],
)
def test_config_xml_with_json_file(letp_cmd, json_file, expected_value):
    """Test configs in "config" or "main_config" section of the json."""
    full_path_value_list = [
        "--path %s --expected_value %s" % (value[0], value[1])
        for value in expected_value
    ]
    check_values = " ".join(full_path_value_list)
    cmd = "%s run %s %s" % (letp_cmd, json_file, check_values)
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


def test_config_two_xml_with_json_file(letp_cmd):
    """Execute one json file with two different .xml configs."""
    expected_tests = 2
    json_file = "scenario/command/runtest/targets_test.json"
    cmd = "%s run %s " % (letp_cmd, json_file)
    output = run_python_with_command(cmd)
    util.check_letp_nb_tests(output, expected_tests)


@pytest.mark.xfail(
    reason="The same test can't be called several times in a json: LETP-xxx"
)
@pytest.mark.parametrize(
    "json_file",
    [
        "scenario/command/runtest/same_test_with_2_cfg.json",
        "scenario/command/runtest/same_test_with_2_cfg_in_2_json.json",
    ],
)
def test_config_same_test_with_2_cfg(letp_cmd, json_file):
    """Test two xml file with json file."""
    expected_tests = 2
    cmd = "{} run {}".format(letp_cmd, json_file)
    print("Start command:\n%s" % cmd)
    output = run_python_with_command(cmd)
    util.check_letp_nb_tests(output, expected_tests)


@pytest.mark.parametrize(
    "path, expected_value",
    [
        ("module/name", "wp750x"),
        ("module/ssh(used)", "1"),
        ("module/ssh/ip_address", "192.168.2.102"),
    ],
)
def test_config_with_json_file_included_by_another_json_file(
    letp_cmd, path, expected_value
):
    """Test xml file with  inclusion of json into another json."""
    json_file = "scenario/command/runtest/target_json.json"
    cmd = "%s run %s --path %s --expected_value %s" % (
        letp_cmd,
        json_file,
        path,
        expected_value,
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


def test_config_with_xml_associated_in_test(letp_cmd):
    """Test xml file associated in the test."""
    path = "module/slink1/name"
    expected_value = "/dev/ttyUSB40"
    path2 = "module/name"
    expected_value2 = "wp750x"
    cmd = (
        "%s run scenario/command/test_config_stub.py::test_config_value_xml"
        " --path %s --expected_value %s --path %s --expected_value %s"
        % (letp_cmd, path, expected_value, path2, expected_value2)
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


def test_config_with_multi_xml_associated_in_test(letp_cmd):
    """Test xml file associated in the test."""
    path = "module/name"
    expected_value = "wp750x"
    path2 = "foo/bar"
    expected_value2 = "test"
    cmd = (
        "%s run "
        "scenario/command/test_config_stub.py::test_config_value_multi_xml"
        " --path %s --expected_value %s --path %s --expected_value %s "
        % (letp_cmd, path, expected_value, path2, expected_value2)
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


def test_config_xml_associated_in_test_module_scope(letp_cmd):
    """Test xml file associated with entire file."""
    path = "module/name"
    expected_value = "wp750x"
    path2 = "foo/bar"
    expected_value2 = "test"
    cmd = (
        "%s run"
        " scenario/command/test_config_associated.py::test_config_xml_module_scope"
        " --path %s --expected_value %s --path %s --expected_value %s "
        % (letp_cmd, path, expected_value, path2, expected_value2)
    )
    print("Start command:\n%s" % cmd)
    assert run_python_with_command(cmd)


def test_config_with_json_env_vari(letp_cmd):
    """Test json file having environment variables."""
    json_file = "scenario/command/runtest/env_variable.json"
    cmd = "%s run %s" % (letp_cmd, json_file)
    print("Start command:\n%s" % cmd)
    output = run_python_with_command(cmd)
    log_filename = util.get_log_file_name(output)
    with open(log_filename, "r") as f:
        content = f.read()
        assert (
            "env variable was found" in content
        ), "The target function was not executed"
