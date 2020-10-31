"""Test html report functionality via LeTP."""

import os
import re
from testlib import run_python_with_command
from testlib.util import get_log_file_name

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def get_html_change_file_name(output):
    """Fetch the html file name from log folder."""
    html_file_change = re.findall(r"log/my_html_report.html", output)
    return bool(html_file_change)


def test_debug_html(letp_cmd):
    """Run test and generate html based report."""
    cmd = "{} run ../letp/scenario/command/test_logging_stub.py --html".format(letp_cmd)
    output = run_python_with_command(cmd)
    res = get_log_file_name(output, file_type="html")
    assert res, "html file is not found %s" % res


def test_debug_changefilename_html(letp_cmd):
    """Run test and generate a new html based report."""
    expect_html_file = "log/my_html_report.html"
    cmd = "{} run ../letp/scenario/command/test_logging_stub.py ".format(
        letp_cmd
    ) + "--html --html-file {} --capture=sys".format(expect_html_file)
    print("Start command:\n%s" % cmd)
    output = run_python_with_command(cmd)

    res = get_html_change_file_name(output)

    assert res, "new html file is not found %s" % res
    assert os.path.isfile(expect_html_file), "{} file does not exists".format(
        expect_html_file
    )


def test_debug_log(letp_cmd):
    """Run test and generate a new letp based report."""
    temp_log = "log/letp.log"
    cmd = (
        "{} run --log-file {} ".format(letp_cmd, temp_log)
        + "../letp/scenario/command/test_logging_stub.py "
        "--config config/module/wp85.xml "
        "--capture=sys"
    )
    assert run_python_with_command(cmd)
    assert os.path.isfile(temp_log), "{} file does not exists".format(temp_log)
