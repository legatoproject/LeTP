"""Test swilog module."""
import time
import pytest
from pytest_letp.lib import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


@pytest.mark.parametrize(
    "swilog_call",
    [
        swilog.debug,
        swilog.info,
        swilog.step,
        swilog.warning,
        swilog.error,
        swilog.critical,
    ],
)
def test_swilog_call(swilog_call):
    """Test swilog calls."""
    swilog_call("TEST MESSAGE")


def test_swilog_image():
    """Test swilog image."""
    swilog.image("$LETP_PATH/test/resources/images/test_img.png")


@pytest.mark.parametrize("image_time", ["start", "middle", "end"])
def test_swilog_image_between_messages(image_time):
    """Test swilog image between other messages."""
    if image_time in ("middle", "end"):
        swilog.info("Start section of test")
        time.sleep(1)
    swilog.image("$LETP_PATH/test/resources/images/test_img.png")
    time.sleep(1)
    if image_time in ("start", "middle"):
        swilog.info("End section of test")
