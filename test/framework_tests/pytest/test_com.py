"""Test com module.

Using mock module to simulate com connections.
"""
from unittest.mock import Mock, patch

from pytest_letp.lib import com
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def test_run_at_cmd_and_check():
    """Test run_at_cmd_and_check method.

    It should return the buffer in the correct order when we have
    several regexes to be matched.
    """
    with patch("pytest_letp.lib.com.clear_buffer"):
        target = Mock()
        target.expect = Mock(return_value="OK")
        target.before = "ATI"
        target.after = "OK"
        rsp = com.run_at_cmd_and_check(target, "ATI", 1, [r"once", r"twice"])
        swilog.info(repr(list(rsp)))
        assert rsp == "ATIOKATIOK"
