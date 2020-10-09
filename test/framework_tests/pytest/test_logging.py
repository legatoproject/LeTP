"""Test letp logging options."""
import pytest

from testlib import run_python_with_command
from testlib.util import (
    get_log_file_name,
    validate_expected_message_in_str,
    validate_no_messages_in_str,
)

__copyright__ = "Copyright (C) Sierra Wireless Inc."


@pytest.mark.parametrize(
    "debug_level, expected_msg_sequences, not_expected",
    [
        pytest.param(
            0,
            [
                "debug level",
                "info level",
                "warning level",
                "error level",
                "critical level",
            ],
            [],
            id="level debug",
        ),
        pytest.param(
            1,
            ["info level", "warning level", "error level", "critical level"],
            ["debug level"],
            id="level info",
        ),
        pytest.param(
            2,
            ["warning level", "error level", "critical level"],
            ["debug level", "info level"],
            id="level warning",
        ),
        pytest.param(
            3,
            ["error level", "critical level"],
            ["debug level", "info level", "warning level"],
            id="level error",
        ),
        pytest.param(
            4,
            ["critical level"],
            ["debug level", "info level", "warning level", "error level"],
            id="level critical",
        ),
    ],
)
def test_debug_level_function(
    letp_cmd, debug_level, expected_msg_sequences, not_expected
):
    """Test debug level.

    No capture is done. The log file will include the log printings.
    """
    cmd = (
        "{} -o run -d {} "
        "scenario/command/test_logging_stub.py::test_debug_level -s".format(
            letp_cmd, debug_level
        )
    )
    print("Start command:\n%s" % cmd)
    output = run_python_with_command(cmd)
    print("*After pexpect ****")
    log_file_name = get_log_file_name(output)
    print("Found log file: %s ", log_file_name)
    with open(log_file_name, "r") as myfile:
        content = myfile.read()
        assert validate_expected_message_in_str(expected_msg_sequences, content)
        assert validate_no_messages_in_str(not_expected, content)


def test_log_capture_function(letp_cmd):
    """Test logging capture=sys works.

    log file has test running summary only while detailed logs are
    stored in junit.xml.
    """
    junit_xml_file = "log/test_log_capture.qa.xml"
    cmd = (
        "{} -o run -d 0 "
        "scenario/command/test_logging_stub.py::test_log_capture "
        "--capture=sys --junitxml {} ".format(letp_cmd, junit_xml_file)
    )
    expected_msg_sequences = [
        "test capture starts",
        "critical level message",
        "test capture ends",
    ]
    print("Start command:\n%s" % cmd)
    output = run_python_with_command(cmd)
    assert validate_no_messages_in_str(expected_msg_sequences, output)
    print(f"Validate messages in {junit_xml_file}")
    with open(junit_xml_file, "r") as junit_file:
        content = junit_file.read()
        assert validate_expected_message_in_str(expected_msg_sequences, content)
