#!/usr/bin/env python3
"""Command-liner launcher for LeTP.

Run with -h flag to see usage.
"""

from __future__ import print_function

import argparse
import os
import subprocess
import sys
import traceback
import pytest

__copyright__ = "Copyright (C) Sierra Wireless Inc."

script_dir = os.path.dirname(os.path.realpath(__file__))

# Keep the following for the backward compatability, to be removed later
pytest_lib = os.path.abspath(os.path.join(script_dir, "../lib"))
letp_internal_lib = os.path.abspath(
    os.path.join(script_dir, "../../letp-internal/letp_internal")
)
html_report_lib = os.path.abspath(os.path.join(script_dir, "html_report"))
LIB_PATHS = [pytest_lib, letp_internal_lib, html_report_lib]


def _register_library():
    for each_lib in LIB_PATHS:
        if each_lib not in sys.path:
            sys.path.insert(0, each_lib)


_register_library()


def _unregister_library():
    for each_lib in LIB_PATHS:
        if each_lib in sys.path:
            sys.path.remove(each_lib)


def _get_version():
    """Get the version of LeTP."""
    version = subprocess.check_output(
        "git -C {} describe --tag 2> /dev/null".format(script_dir), shell=True
    )
    return version.decode("utf-8")


def _get_arguments():
    """Parse command line arguments.

    Returns:
        named tuple with the args
    """
    parser = argparse.ArgumentParser(
        description="Connect to the target and start a test."
    )

    if sys.version_info > (3, 7):
        subparsers = parser.add_subparsers(dest="command_name", required=True)
    else:
        subparsers = parser.add_subparsers(dest="command_name")

    # # subparser for version
    subparsers.add_parser("version", help="get the LeTP version")

    # subparser for running tests
    run_parser = subparsers.add_parser("run", help="run test with pytest parameters.")

    # Debug level
    # Simple option like -d is reserved by pytest. This is obsolete.
    # Please always use --dbg-lvl which is supported in pytest_letp plugin.
    run_parser.add_argument(
        "-d",
        "--dbg-lvl",
        metavar="N",
        type=int,
        dest="dbglvl",
        help="""legato or swilog debug level as an integer
                                                    0 = DEBUG,
                                                    1 = INFO (default),
                                                    2 = WARN,
                                                    3 = ERR,
                                                    4 = CRIT,
                                                    5 = EMERG""",
        default="1",
    )
    return parser.parse_known_args()


def run(args, pytest_args):
    """Run the the tests when the run argument is used."""
    _pytest_config_file = "pytest.ini"
    pytest_root = os.path.expandvars("$LETP_TESTS")
    print("$LETP_TESTS={}".format(pytest_root))

    # Set rootdir, pytest.ini and the plugin pytest-letp
    # in case the json test set is outside of the workspace
    # There is also a fake file test_dummy.py because the conftest.py
    # is found thanks to the first test name,
    # so pytest-letp must be called to process the json file
    # into LeTP tests (pytest_load_initial_conftests hook)
    _rc = pytest.ExitCode.INTERNAL_ERROR
    try:
        _rc = pytest.main(
            [
                "-r a",  # (a)ll except passed (p/P) extra summary info
                "--color=yes",
                "--dbg-lvl",
                str(args.dbglvl),
                "-v",
                "--rootdir",
                pytest_root,
                "-c",
                os.path.join(pytest_root, _pytest_config_file),
                "-p",
                "pytest_letp",
            ]
            + pytest_args
        )
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)

    _unregister_library()
    if _rc != pytest.ExitCode.OK:
        sys.exit(_rc)


def main():
    """Entry point of LeTP."""
    args, pytest_args = _get_arguments()
    command = args.command_name

    if not os.environ.get("LETP_TEST_SET"):
        # Set a default value for LETP_TEST_SET (set of public tests)
        os.environ["LETP_TEST_SET"] = "public"

    if command == "run":
        run(args, pytest_args)
    elif command == "version":
        print(_get_version())
    else:
        print("Invalid command:", args.command_name)


if __name__ == "__main__":
    main()
