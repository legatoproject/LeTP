"""Test av_lib.py."""
from unittest.mock import patch
import pytest
from pytest_letp.lib import av_lib
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class TestTarget:
    """!Test target class."""

    def __init__(self):
        self.generic_name = "wp76xx"
        self.module_name = "wp7603"
        self.imei = "000000000000000"


@pytest.mark.config("$LETP_TESTS/config/av_server.xml")
def test_av_create(read_config):
    """!Create av_lib instance."""
    target = TestTarget()
    swilog.info("Creating av handler")
    with patch("pytest_letp.lib.av_server.AVServer._request"):
        assert av_lib.AVManager(target, read_config), "Failed to create av handler"
        swilog.info("av handler created")


@pytest.mark.config("$LETP_TESTS/config/av_server.xml")
def test_av_sync(read_config):
    """!Test sync job on server."""
    target = TestTarget()
    with patch("pytest_letp.lib.av_server.AVServer._request"):
        swilog.info("Creating av handler")
        av_handler = av_lib.AVManager(target, read_config)
        assert av_handler, "Failed to create av handler"
        swilog.info("av handler created")

        av_handler.uid = "0000"
        swilog.info("Creating sync job")
        sync_job = av_handler.sync()
        assert sync_job, "Failed to create sync job"
        swilog.info("sync job created")

        swilog.info("Cancelling sync job")
        assert av_handler.server.cancel_operation(sync_job), "Failed to cancel sync job"
        swilog.info("sync job Cancelled")
