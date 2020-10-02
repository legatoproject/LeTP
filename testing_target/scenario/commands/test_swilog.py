"""! Swilog test sample.

Set of tests showing how to use the swilog library

@package sampleSwilog
"""
import pytest

# Log module
import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."

# ===============================================================
# Test functions
# ===============================================================


def test_swilog_call():
    """!Activate the debug level to see all the messages.

    letp run -d 0 test/host/scenario/test_swilog.py.
    """
    swilog.debug("debug message")
    swilog.info("info message")
    # to highlight a particular step in the test
    swilog.step("step message")
    swilog.warning("warning message")
    swilog.error("error message")
    swilog.critical("critical message")


# This test is expected to fail. It is just a demo.
@pytest.mark.xfail
def test_swilog_error_memorization(target):
    """!Execute several tests and capture swilog errors.

    Use swilog.error to log all the encountered errors.
    The final verdict will be passed if there is no stored errors.

    @param target: fixture to communicate with the target
    """
    if " legato " not in target.run("ls /"):
        swilog.error("/legato is not present")

    if " tmp " not in target.run("ls /"):
        swilog.error("/tmp is not present")

    if " my_test_folder " not in target.run("ls /tmp"):
        swilog.error("/tmp/my_test_folder is not present")

    # Test is PASS if only /legato, /tmp and /tmp/my_test_folder are present
    failed_testcases_list = swilog.get_error_list()
    if failed_testcases_list != []:
        assert 0, "Some tests failed:\n%s" % "\n".join(failed_testcases_list)
