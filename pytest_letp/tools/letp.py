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
import re
import pytest
from pytest_letp.lib import pytest_qTest

__copyright__ = "Copyright (C) Sierra Wireless Inc."

script_dir = os.path.dirname(os.path.realpath(__file__))
pytest_root = os.path.expandvars("$LETP_TESTS")

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
    version = "unknown"
    try:
        with open(os.path.join(script_dir, '.version'), 'r', encoding="utf-8") as f:
            version = f.readline()
    except:
        try:
            if os.name == "nt":
                version = subprocess.check_output(
                    f"git -C {script_dir} describe --tag", shell=True
                ).decode('utf-8')
            else:
                version = subprocess.check_output(
                    f"git -C {script_dir} describe --tag 2> /dev/null",
                    shell=True
                ).decode('utf-8')
        except subprocess.CalledProcessError:
            pass
    return version


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

    # subparser for version
    subparsers.add_parser("version", help="get the LeTP version")

    # subparser for running test from the qTest
    qtest_parser = subparsers.add_parser(
        "runqTest",
        help="run test with config from qTest.xml file and pytest parameters.")
    qtest_parser.add_argument("--path",
                              dest="path",
                              help="Determine a campaign on qTest based on path")
    qtest_parser.add_argument("--project-id",
                              dest="project_id",
                              help="Project ID")
    qtest_parser.add_argument("--campaign",
                              dest="campaign",
                              help="Determine a campaign on qTest based on type/ID.\n"
                              "such as test-suite:111111")

    # subparser for running tests
    run_parser = subparsers.add_parser("run", help="run test with pytest parameters.")

    # Debug level
    # Simple option like -d is reserved by pytest. This is obsolete.
    # Please always use --dbg-lvl which is supported in pytest_letp plugin.
    qtest_parser.add_argument(
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
    print(f"$LETP_TESTS={pytest_root}")

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


def run_qtest(args, pytest_args):
    """Get and run the tests from qTest."""
    xmlpath = os.path.join(
        os.environ.get("LETP_PATH"),
        "pytest_letp",
        "config",
        "qTest.xml")
    access_token = os.getenv("ACCESS_TOKEN")
    pattern = r"(Bearer\s)?(?P<token>.*)"
    access_token = re.search(pattern, access_token).group("token")

    if args.path:
        qtest_path = args.path.split("/")
        qtest = pytest_qTest.QTestAPI(access_token)
        qtest.get_id(qtest_path)
        test_campaign_name = qtest_path[-1] + ".json"
    elif args.project_id and args.campaign:
        campaign = args.campaign
        project_id = args.project_id
        print(f"Project ID: {project_id}")
        assert project_id.isdigit(), "Project ID must be a numeric string"

        campaign_type, campaign_id = campaign.split(":")
        # Test Runs under root or under a container (Release, Test Cycle or Test Suite)
        container = ("root", "release", "test-cycle", "test-suite")
        print(f"{campaign_type}: {campaign_id}")
        assert (campaign_type in container
                ), "Campaign type must be " + " or ".join(container)
        assert campaign_id.isdigit(), "Campaign ID must be a numeric string"

        qtest = pytest_qTest.QTestAPI(access_token,
                                      int(project_id),
                                      parent_id=int(campaign_id),
                                      parent_type=campaign_type)
        test_campaign_name = qtest.get_campaign_name()
    else:
        print("Invalid command: Please check the qTest information provided")

    test_cases = qtest.get_test_script()
    file_path = os.path.join(pytest_root, test_campaign_name)
    pytest_qTest.gen_json_file(test_cases, file_path)

    pytest_args = [test_campaign_name] + pytest_args
    print(f"Run the test cases in the {test_campaign_name} file")
    run(args, pytest_args)

    # Save qTest information for post-processing
    # when test case results are available
    qtest.save_qtest_info(xmlpath)


def main():
    """Entry point of LeTP."""
    args, pytest_args = _get_arguments()
    command = args.command_name

    if not os.environ.get("LETP_TEST_SET"):
        # Set a default value for LETP_TEST_SET (set of public tests)
        os.environ["LETP_TEST_SET"] = "public"

    if command == "runqTest":
        run_qtest(args, pytest_args)
    elif command == "run":
        run(args, pytest_args)
    elif command == "version":
        print(_get_version())
    else:
        print("Invalid command:", args.command_name)


if __name__ == "__main__":
    main()
