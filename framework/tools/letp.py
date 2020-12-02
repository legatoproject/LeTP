#!/usr/bin/env python3
"""!@package letpCmd Command-liner launcher for LeTP.

Run with -h flag to see usage.
"""

from __future__ import print_function

import argparse
import json
import os
import subprocess
import sys
import traceback

import pytest

__copyright__ = "Copyright (C) Sierra Wireless Inc."

script_dir = os.path.dirname(os.path.realpath(__file__))

sys.path.insert(0, os.path.join(script_dir, "../module/pytest_plugin"))
sys.path.insert(0, os.path.join(script_dir, "../module/pytest_plugin/lib"))
sys.path.insert(0, os.path.join(script_dir, "host", "htmlReport"))
sys.path.insert(0, os.path.join(script_dir, "../../letp-internal/internal_lib"))


def _config_debug_level(args):
    """Configure the debug level for pytest."""
    args_host_pytest_args = args.pytest_args
    args_host_pytest_args.append("--dbg-lvl")
    args_host_pytest_args.append("%s" % args.dbglvl)
    return args_host_pytest_args


def _collect_tests(args):
    if ".json" in args.testpath:
        tests = _json_collect_tests(args.testpath)
        print("Number of tests collected in %s: %d" % (args.testpath, len(tests[0])))


def _setup_letp_tests(args_host_testpath, pytest_config_file):
    if os.path.isdir(args_host_testpath):
        print("IS DIRECTORY: ", args_host_testpath)
        # User specified folder may have pytest.ini.
        # It takes precedence over LETP_TESTS.
        pytest_config = os.path.join(args_host_testpath, pytest_config_file)
        if os.path.exists(pytest_config):
            print("IS CONF: ", pytest_config_file)
            pytest_root = args_host_testpath
            os.environ["$LETP_TESTS"] = os.path.abspath(pytest_root)
    pytest_root = os.path.expandvars("$LETP_TESTS")
    print("$LETP_TESTS={}".format(pytest_root))
    return pytest_root


def _get_version():
    """Get the version of LeTP."""
    version = subprocess.check_output(
        "git -C {} describe --tag 2> /dev/null".format(script_dir), shell=True
    )
    return version.decode("utf-8")


def _json_collect_tests(json_file):
    """Collect all the LeTP tests in a Json file.

    Search recursively if a jsonfile is referenced.

    Args:
        json_file: path of Json test file
    Returns:
        tuple composed of the list of the host tests and the list of the target tests
    """
    with open(json_file, "r") as fp:
        js = json.load(fp)
        # Find the letp section
        letp_json = _search_item("letp", js)
        if letp_json != {}:
            # letp token found. Expect the same format
            # as the json used in validation campaign
            # ("letp" followed by "test" section)
            test_entries = _search_item("tests", letp_json)
            test_list = [
                os.path.expandvars(test["name"])
                for test in test_entries
                if "name" in test
            ]
        else:
            # Expect only a list of tests
            test_list = [
                os.path.expandvars(test["name"]) for test in js if "name" in test
            ]
        # Find if a json file is referenced
        for test in test_list:
            if ".json" in test:
                # Collect also the tests for this file
                tests_host, test_target = _json_collect_tests(
                    os.path.join(os.environ["LETP_TESTS"], test)
                )
                test_list += tests_host
                test_list += test_target
        # Returned a tuple with the host and target tests without the json files
        return (
            [
                os.path.join(os.environ["LETP_TESTS"], test)
                for test in test_list
                if ".json" not in test and "/target/" not in test
            ],
            [test for test in test_list if ".json" not in test and "/target/" in test],
        )


def _search_item(pattern, obj):
    """Search for a pattern in a Json python representation."""
    if isinstance(obj, dict):
        if pattern in obj:
            return obj[pattern]
        else:
            for item in obj:
                ret = _search_item(pattern, obj[item])
                if ret != {}:
                    return ret
    return {}


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
    run_parser = subparsers.add_parser("run", help="run a test")

    # Debug level
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
    # Test path
    run_parser.add_argument(
        "testpath", help="which test file to run (relative to test/scenario/)"
    )
    # Pytest args
    run_parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments after the test path are directly passed on to pytest. "
        "Use pytest --help to see those options",
    )
    # Create group for Pytest arguments
    pytest_arguments = run_parser.add_argument_group("Pytest Extention Arguments")
    # Pytest argument "--collect-only"
    pytest_arguments.add_argument(
        "--collect-only",
        help="""Do not execute tests.
                                                Simply see all the available tests.""",
    )
    # Pytest argument "--junit-xml" to generate .xml file
    pytest_arguments.add_argument(
        "--junit-xml",
        help="""Generate a xml file.
                                                        Input a file name.
                                                        Add '--capture=sys' to
                                                        also put the stdout
                                                        inside the report""",
    )
    # Specify log file
    run_parser.add_argument(
        "--log-file",
        dest="log_file",
        default="",
        help="path and name of the log file, "
        "such as /tmp/letp.log."
        "A timestamp will be added to the name. "
        "Default is log/<timestamp>_<testname>.log",
    )

    # Generate HTML output
    run_parser.add_argument("--html", action="store_true", help="Generate html output")
    # Path/Name to HTML file
    run_parser.add_argument(
        "--html-file",
        dest="html_file",
        help="path and name of the html file, "
        "such as /tmp/letp.log. "
        "A timestamp will be added to the name. "
        "Default is log/<timestamp>_<testname>.html",
    )

    return parser.parse_args()


def run(args):
    """!Run the the tests when the run argument is used."""
    _collect_tests(args)

    args_host_testpath = args.testpath
    args_host_pytest_args = _config_debug_level(args)

    _pytest_config_file = "pytest.ini"
    pytest_root = _setup_letp_tests(args_host_testpath, _pytest_config_file)
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
                "-v",
                "--rootdir",
                pytest_root,
                "-c",
                os.path.join(pytest_root, _pytest_config_file),
                "-p",
                "pytest_letp",
                "--log-file",
                args.log_file,
            ]
            + ["test_dummy.py", args_host_testpath]
            + args_host_pytest_args
        )
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)

    if _rc != pytest.ExitCode.OK:
        sys.exit(_rc)


def main():
    """!Entry point of LeTP."""
    args = _get_arguments()
    command = args.command_name

    if not os.environ.get("LETP_TEST_SET"):
        # Set a default value for LETP_TEST_SET (set of public tests)
        os.environ["LETP_TEST_SET"] = "public"

    if command == "run":
        run(args)
    elif command == "version":
        print(_get_version())
    else:
        print("Invalid command:", args.command_name)


if __name__ == "__main__":
    main()
