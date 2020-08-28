"""Test LETP command letp.py."""
import testlib.util as util

from testlib import run_python_with_command

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def _test_letp_command(letp_cmd, letp_option, expected_test_nb, test_names=None):
    """Test letp command with specific option."""
    cmd = "{} run {}".format(letp_cmd, letp_option)
    print("Start command:\n%s" % cmd)
    output = run_python_with_command(cmd)
    print(output)
    util.check_letp_nb_tests(output, expected_test_nb, test_names)


def test_command_filename(letp_cmd):
    """Run all test case which is passed in filename."""
    expected_test_nb = 3
    filename = "scenario/command/test_logging_stub.py"
    _test_letp_command(letp_cmd, filename, expected_test_nb)


def test_command_folder(letp_cmd):
    """Run all the test inside folder.

    The folder needs to have pytest.ini.
    """
    expected_test_nb = 10
    folder_path = "scenario/command/folder"
    _test_letp_command(letp_cmd, folder_path, expected_test_nb)


def test_command_json(letp_cmd):
    """Run all the test inside a json file."""
    expected_test_nb = 10
    json_file = "scenario/command/runtest/command/test_command.json"
    _test_letp_command(letp_cmd, json_file, expected_test_nb)


def test_command_json_call_another_json(letp_cmd):
    """Run all the test inside a json file.

    Call also a json file inside this json
    """
    expected_test_nb = 11
    json_file = "scenario/command/runtest/command/test_command_call.json"
    test_list = (
        ["test_folder_010"]
        + ["test_folder_0%02d" % nb for nb in range(1, 10)]
        + ["test_command_by_filename"]
    )
    _test_letp_command(letp_cmd, json_file, expected_test_nb, test_list)


def test_command_json_call_another_json_multiple(letp_cmd):
    """Run all the test inside a json file.

    Call also json files inside this json
    """
    expected_test_nb = 11
    json_file = "scenario/command/runtest/command/test_command_call_multiple.json"
    test_list = [
        "test_folder_003",
        "test_folder_004",
        "test_folder_001",
        "test_folder_002",
        "test_command_by_filename",
        "test_folder_009",
        "test_folder_010",
        "test_folder_007",
        "test_folder_008",
        "test_folder_005",
        "test_folder_006",
    ]
    _test_letp_command(letp_cmd, json_file, expected_test_nb, test_list)
