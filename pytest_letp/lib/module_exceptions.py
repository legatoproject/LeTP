"""Module exceptions for modules classes."""
from pytest_letp.lib import swilog


class SlinkException(Exception):
    """Generic exception for Target definition."""

    def __init__(self, msg=None):
        error_msg = "SlinkException"
        if msg:
            error_msg += ": {}".format(msg)
        swilog.error(error_msg)
        super().__init__(error_msg)


class TargetException(Exception):
    """Generic exception for Target."""

    def __init__(self, msg=None):
        error_msg = "TargetException"
        if msg:
            error_msg += ": {}".format(msg)
        swilog.error(error_msg)
        super().__init__(error_msg)
