"""Communication exceptions for modules classes."""
from pytest_letp.lib import swilog


class ComException(Exception):
    """Generic exception for Communication."""

    def __init__(self, msg=None):
        error_msg = "ComException"
        if msg:
            error_msg += ": {}".format(msg)
        swilog.error(error_msg)
        super().__init__(error_msg)
