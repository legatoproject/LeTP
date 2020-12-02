"""Integration tests with pytest options.

LeTP uses pytest options directly.

References:
https://docs.pytest.org/en/stable/usage.html
"""

import pytest
import testlib.util as util
from testlib import run_letp_with_failed_tests


def _test_letp_pytest_command(
    letp_cmd, letp_option, expected_msg: list, pytest_option="", log_file_option=""
):
    """Test letp command with specific option."""
    cmd = "{} run {} {} {}".format(
        letp_cmd, log_file_option, letp_option, pytest_option
    )
    print("Start command:\n%s" % cmd)

    output = run_letp_with_failed_tests(cmd)

    if log_file_option:
        log_options = log_file_option.split()
        log_filename = log_options[1]
    else:
        log_filename = util.get_log_file_name(output)
    util.validate_test_messages_sequence(expected_msg, log_filename)


@pytest.mark.parametrize(
    "pytest_option, expected_msg",
    [
        # show a summary with failed cases.
        pytest.param("-r f", ["ERRORS", "FAILURES"], id="short_test_summary_fail"),
        # # show a summary with passed cases.
        pytest.param("-r P", ["PASSES"], id="short_test_summary_pass"),
        # show a summary with failed and passed cases.
        pytest.param(
            "-r fp", ["ERRORS", "FAILURES"], id="short_test_summary_fail_pass"
        ),
        # show a summary with failed and error cases.
        pytest.param(
            "-r fE", ["ERRORS", "FAILURES"], id="short_test_summary_fail_error"
        ),
        # show a summary with fail/pass/error cases.
        pytest.param(
            "-r fPE",
            ["ERRORS", "FAILURES", "PASSES"],
            id="short_test_summary_fail_pass_error",
        ),
    ],
)
def test_pytest_summary_option(letp_cmd, pytest_option, expected_msg, log_file_option):
    """Run the tests and show the result."""
    test_name = "scenario/test_pytest_option_stub.py"
    _test_letp_pytest_command(
        letp_cmd,
        test_name,
        expected_msg,
        pytest_option=pytest_option,
        log_file_option=log_file_option,
    )


@pytest.mark.parametrize(
    "pytest_option, expected_msg",
    [
        pytest.param(
            "--collect-only",
            ["collecting ...", "collected", "test_collected", "no tests ran"],
            id="collect_only",
        ),
        pytest.param(
            "--junit-xml ./junit_test.xml", ["generated xml file"], id="junit_xml"
        ),
    ],
)
def test_pytest_customized_option(
    letp_cmd, pytest_option, expected_msg, log_file_option
):
    """Only collect the tests in the folder.

    Don't run the tests.
    """
    test_name = "scenario/test_pytest_option_stub.py"
    _test_letp_pytest_command(
        letp_cmd,
        test_name,
        expected_msg,
        pytest_option=pytest_option,
        log_file_option=log_file_option,
    )


@pytest.mark.parametrize(
    "pytest_option, expected_msg",
    [
        # show the failed tests' shorter traceback
        pytest.param("--tb=short", ["E   assert False"], id="traceback_short"),
        # show the failed tests' exhaustive, informative traceback formatting
        pytest.param(
            "--tb=long",
            """request = <FixtureRequest for <Function test_failing_case>>
    def test_failing_case(request):
        swilog.info("Test %s" % request.node.name)
>       assert False""".split(),
            id="traceback_long",
        ),
        # show the failed tests' only one line per failure
        pytest.param("--tb=line", ["assert False"], id="traceback_line"),
        # show the failed tests' Python standard library formatting
        pytest.param(
            "--tb=native",
            """assert False
AssertionError: assert False""".split(),
            id="traceback_native",
        ),
        # show the failed tests' (default) 'long' tracebacks for the first and last
        pytest.param(
            "--tb=auto",
            """
    @pytest.fixture
    def error_fixture():
>       assert 0
""".split(),
            id="traceback_auto",
        ),
    ],
)
def test_pytest_trackback_option(
    letp_cmd, pytest_option, expected_msg, log_file_option
):
    """Test the pytest tb options."""
    test_name = "scenario/test_pytest_option_stub.py"
    _test_letp_pytest_command(
        letp_cmd,
        test_name,
        expected_msg,
        pytest_option=pytest_option,
        log_file_option=log_file_option,
    )
