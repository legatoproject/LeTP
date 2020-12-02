"""Test pytest_letp_log plugin."""
import os
import pytest

import testlib.util as util
from testlib import list_files_tree
from pytest_letp_log import LogFileNameBuilder


def test_pytest_letp_log_file(testdir_stub):
    """Test letp log file can be generated."""
    log_file = "log/test_pytest_letp_log_file.log"
    result = testdir_stub.runpytest("-p", "pytest_letp_log", "--log-file", log_file)
    result.assert_outcomes(passed=1)
    list_files_tree(str(testdir_stub.tmpdir))
    assert os.path.exists(os.path.join(testdir_stub.tmpdir, log_file))
    log_file_name = util.get_log_file_name("".join(result.outlines))
    assert log_file_name == log_file


def test_pytest_letp_log_default_name(testdir_stub):
    """Test letp log file name includes test case name."""
    test_id = test_pytest_letp_log_default_name.__name__
    result = testdir_stub.runpytest("-p", "pytest_letp_log", "{}.py".format(test_id))
    result.assert_outcomes(passed=1)
    list_files_tree(str(testdir_stub.tmpdir))
    log_file_name = util.get_log_file_name("".join(result.outlines))
    assert log_file_name.endswith(test_id + "_py.log")


@pytest.mark.parametrize(
    "file_or_dir, log_file_keyword",
    [
        (["test_file.py"], "test_file"),
        (["test_file.py::method1"], "test_file_py"),
        (["test_campaign.json"], "test_campaign_json"),
        (
            ["test_campaign.json", "test_campaign2.json"],
            "test_campaign_json_test_campaign2_json",
        ),
        (["test_folder1", "test_folder2"], "letp"),
        (["test_file.py", "test_folder"], "letp"),
    ],
)
def test_log_file_name_builder(file_or_dir, log_file_keyword):
    """Test log file name build the expected log file name."""
    test_log_file_name_builder = LogFileNameBuilder(file_or_dir)
    log_file = test_log_file_name_builder.build()
    assert log_file_keyword in log_file
