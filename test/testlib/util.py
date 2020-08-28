"""Unit tests utility."""

import re

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def get_log_file_name(output, file_type="log"):
    """Grep the log file name from stdout."""
    log_file = re.findall(r"log/[0-9_0-9a-z]*\.{}".format(file_type), str(output))
    # Two prints:
    # e.g.
    # Create the log file log/20200413_120544_test_debug_value.log
    # Logs can be found here log/20200413_120544_test_debug_value.log
    assert len(log_file) == 2
    assert log_file[0] == log_file[1]
    return log_file[0]


def check_letp_nb_tests_from_file(
    log_filename, number_of_passed, message_sequences=None
):
    """Check the number of tests executed by LeTP.

    Args:
        log_filename: LeTP log file name
        number_of_passed: expected passed LeTP tests
        message_sequences: optional. List of string (e.g. test names) to
            check in the order of the list in the log

    Raises
        AssertionError if nb of executed tests is different from nb_tests
    """
    with open(log_filename, "r") as f:
        content = f.read()
        if int(number_of_passed) == 0:
            msg = "no tests ran"
        else:
            msg = "{} passed".format(number_of_passed)
        assert msg in content
        assert "error in" not in content, "No tests in error should be present"
        assert "failed" not in content, "No failed tests should be present"

    if message_sequences is not None:
        validate_test_messages_sequence(message_sequences, log_filename)


def check_letp_nb_tests(output, number_of_passed, message_sequences=None):
    """Read the log file from LeTP output and validate it.

    Check number of tests executed and expected message sequences.

    Args:
        output: stdout from LeTP call
        number_of_passed: expected passed LeTP tests
        message_sequences: optional. List of string (e.g. test names) to
            check in the order of the list in the log
    """
    log_filename = get_log_file_name(output)
    check_letp_nb_tests_from_file(log_filename, number_of_passed, message_sequences)


def validate_test_messages_sequence(test_msg_sequences: list, log_file_name):
    """Validate the test message were print sequentially in the log file."""
    with open(log_file_name, "r") as myfile:
        content = myfile.read()
        # print("Read log content:")
        # print(pprint.pformat(content))
        return validate_expected_message_in_str(test_msg_sequences, content)


def validate_expected_message_in_str(expected_msg_sequences: list, content: str):
    """Validate the expected message were sequentially in the string."""
    message_idx = 0
    all_lines = content.split("\n")
    for each_line in all_lines:
        test_msg_name = expected_msg_sequences[message_idx]
        if test_msg_name in each_line:
            message_idx += 1
            print("Expected {} executed".format(test_msg_name))
        if message_idx == len(expected_msg_sequences):
            break
    return message_idx == len(expected_msg_sequences)


def validate_no_messages_in_str(not_expected: list, content: str):
    """Validate no messages in the string."""
    for each in not_expected:
        if each in content:
            return False
    return True


def validate_no_messages(not_expected: list, log_file_name):
    """Validate the test messages are not present in the log file."""
    if not not_expected:
        return True
    with open(log_file_name, "r") as myfile:
        content = myfile.read()
        return validate_no_messages_in_str(not_expected, content)
