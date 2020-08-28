"""Test different debug levels of LETP."""
import swilog

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def test_debug_level():
    """Test debug values in different levels."""
    print("test debug starts")
    swilog.debug("debug level message")
    swilog.info("info level message")
    swilog.warning("warning level message")
    swilog.error("error level message")
    swilog.critical("critical level message")
    print("test debug ends")


def test_html_value():
    """Test heml value stub."""
    print("I am html here")


def test_log_capture():
    """Test logging capture."""
    print("test capture starts")
    swilog.critical("critical level message")
    print("test capture ends")
