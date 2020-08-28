"""!@package misc Miscellaneous for testing."""
import select
import sys

import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def input_timeout(msg, timeout):
    """!Read a user entry in stdin with timeout.

    @param msg: Message to display
    @param timeout: in second

    @Returns Read input

    ~~~~~~~~~~~~~{.py}
    msg = misc.input_timeout("Please manually power cycle your target", 30)
    ~~~~~~~~~~~~~
    """
    swilog.info(msg)
    i, _, _ = select.select([sys.stdin], [], [], timeout)
    assert len(i) != 0, "Nothing read on input"

    rsp = sys.stdin.readline()
    swilog.debug("Read input:%s" % rsp)
    return rsp
