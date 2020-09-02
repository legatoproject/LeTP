"""!@package com_exceptions communication exceptions for modules classes."""
import swilog


class ComException(Exception):
    """!Generic exception for Communication."""

    def __init__(self, msg=None):
        error_msg = "ComException"
        if msg:
            error_msg += ": {}".format(msg)
        swilog.error(error_msg)
        super().__init__(error_msg)
