"""Test letp.py."""
from testlib import run_python_with_command

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def test_letp_new_log_folder(letp_cmd):
    """Test new log folder can be created correctly."""
    new_folder_name = "log/new_folder/new_folder"
    cmd = (
        "{} run --dbg-lvl 0 ".format(letp_cmd)
        + "--log-file {new_folder}/test_json_report.log "
        "scenario/command/test.py "
        "--capture=sys "
        "--json-report "
        "--json-report-file={new_folder}/json_report.json "
        "--junitxml {new_folder}/test_results_letp.qa.xml "
        "--html "
        "--html-file {new_folder}/test_report.html ".format(new_folder=new_folder_name)
    )
    assert run_python_with_command(cmd + " --ci")


def test_letp_test_folder_arg(letp_cmd):
    """Test letp with a test folder as the argument."""
    cmd = (
        "{} run --dbg-lvl 0 ".format(letp_cmd)
        + "--log-file log/test_letp_test_folder_arg.log "
        ". "
    )
    assert run_python_with_command(cmd + " --ci")
