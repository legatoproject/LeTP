"""Library for the unit test."""
import io
import os
from contextlib import redirect_stdout
from pytest_letp.lib.runpy_adapter import run_python_with_command, exec_command
from testlib import util

__copyright__ = "Copyright (C) Sierra Wireless Inc."

__all__ = ["run_python_with_command", "util"]


def run_letp_with_failed_tests(command):
    """Run expected failed tests and return captured output."""
    output = io.StringIO()
    expected_fail = False
    with redirect_stdout(output):
        try:
            exec_command(command)
        except SystemExit:
            expected_fail = True
    if expected_fail:
        print("Expected system failure was hit")
    return output.getvalue()


def list_files_tree(startpath):
    """List files tree in the path."""
    if not (startpath and os.path.exists(startpath)):
        print("No valid path {}".format(startpath))
        return
    for root, _, files in os.walk(str(startpath)):
        level = root.replace(startpath, "").count(os.sep)
        indent = " " * 4 * (level)
        print("{}{}/".format(indent, os.path.basename(root)))
        subindent = " " * 4 * (level + 1)
        for f in files:
            print("{}{}".format(subindent, f))
