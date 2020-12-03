"""!@package swilog The Sierra-Wireless colored log module.

Use the swilog module to print information instead of "print" statement.
It is equivalent to the logging python module with colors.

The debug level can be set thanks to the -d option. See @ref letp_options

@section cologLogs Examples

~~~~~~~~~~~~~{.python}
    from pytest_letp.lib import swilog

    swilog.debug("debug message")
    swilog.info("info message")
    swilog.step("step message") to indicate a particular step in the test
    swilog.warning("warning message")
    swilog.error("error message")
    swilog.critical("critical message")
~~~~~~~~~~~~~

Output:

@image html swilog.png
@image latex swilog.eps

@section memo Errors memorization

swilog.error() memorizes all the error messages in a list.
It can be used to log all the errors of the test if they are non blocking errors.
At the end of the test, you can use swilog.get_error_list() to
get all errors and check if the test is passed.

~~~~~~~~~~~~~{.python}
    failed_testcases_list = swilog.get_error_list()
    if failed_testcases_list != []:
        assert 0, "Some tests failed:\n%s"% "\n".join(failed_testcases_list)
~~~~~~~~~~~~~
"""
import sys

try:
    import logging
    import colorlog
except:
    import logging as colorlog

    colorlog.warning("install colorlog to have colors: pip install colorlog")

__copyright__ = "Copyright (C) Sierra Wireless Inc."

DELIMITER = "===================="

LOG_FORMAT = "\n%(log_color)s%(asctime)s %(levelname)s %(message)s"
DATE_FORMAT = "%H:%M:%S"
default_log_colors = {
    "NOTSET": "white",
    "DEBUG": "blue",
    "INFO": "green",
    "STEP": "bold_blank",
    "WARNING": "bold_yellow",
    "ERROR": "bold_red",
    "CRITICAL": "bold_red",
}

error_list = []

SYS_OUT_HANDLER = None
logger = logging.getLogger("swilog")


class LoggingFilter(logging.Filter):
    """Filter for ignoring logs."""

    _ignored_record_names = (
        "reportportal_client",
        "pytest_reportportal",
        "urllib3.connectionpool",
    )

    def filter(self, record):
        """Filter the record from configuration."""
        if record.name.startswith(self._ignored_record_names):
            return False
        return True


def init(debugLevel, log_colors=None):
    """Init color logs as the global logging."""
    # pylint: disable=import-outside-toplevel
    from colorlog.colorlog import ColoredFormatter

    global SYS_OUT_HANDLER
    # override the formatter it creates with colorlog
    logging._acquireLock()
    try:
        root = logging.getLogger()
        root.setLevel(debugLevel)
        SYS_OUT_HANDLER = logging.StreamHandler(sys.stdout)
        logger.addHandler(SYS_OUT_HANDLER)
        handler = SYS_OUT_HANDLER
        # Workaround logging disabled for level 0
        print("Current logging.level: {}".format(handler.level))
        if handler.level == 0:
            logging.disable(-1)
        if isinstance(handler, logging.StreamHandler):
            print("Set logging.level: {}".format(debugLevel))
            handler.setLevel(debugLevel)
            handler.addFilter(LoggingFilter())
            handler.setFormatter(
                ColoredFormatter(
                    fmt=LOG_FORMAT,
                    datefmt=DATE_FORMAT,
                    log_colors=log_colors if log_colors is None else default_log_colors,
                )
            )
    finally:
        logging._releaseLock()


def shutdown():
    """Shutdown loggings."""
    logger.removeHandler(SYS_OUT_HANDLER)


def get_color_codes():
    """Get a list of available colors + bold, thin, bg, fg."""
    return colorlog.escape_codes


def trace(msg):
    """Print a colored message with TRACE level."""
    logging.root.log(0, msg)


def debug(*args, **kwargs):
    """Print a colored message with DEBUG level."""
    logger.debug(*args, **kwargs)


def info(*args, **kwargs):
    """Print a colored message with INFO level."""
    logger.info(*args, **kwargs)


def step(msg, *args, **kwargs):
    """Print a colored message with INFO level surrounded by a DELIMITER."""
    new_msg = "%s %s%s%s %s" % (
        DELIMITER,
        colorlog.escape_codes["bold"],
        msg,
        colorlog.escape_codes["thin"],
        DELIMITER,
    )
    # colorlog.log(5, new_msg, *args, **kwargs)
    logger.info(new_msg, *args, **kwargs)


def warning(*args, **kwargs):
    """Print a colored message with WARNING level."""
    logger.warning(*args, **kwargs)


def error(*args, **kwargs):
    """Print a colored message with ERROR level."""
    global error_list
    error_list.append(args[0])
    logger.error(*args, **kwargs)


def critical(*args, **kwargs):
    """Print a colored message with CRITICAL level."""
    global error_list
    error_list.append(args[0])
    logger.critical(*args, **kwargs)


def get_error_list():
    """Get the list of errors reported."""
    global error_list
    return error_list
