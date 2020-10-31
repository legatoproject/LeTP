"""Library for the unit test."""
import io
from contextlib import redirect_stdout
from runpy_adapter import run_python_with_command, exec_command
from testlib import util

__copyright__ = "Copyright (C) Sierra Wireless Inc."

__all__ = ["run_python_with_command", "util"]


def run_letp_with_failed_tests(command):
    """Run expected failed tests and return captured output."""
    output = io.StringIO()
    with redirect_stdout(output):
        try:
            exec_command(command)
        except SystemExit:
            print("Expected failed tests.")
    return output.getvalue()
