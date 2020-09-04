"""!@package pytest_letp LeTP main fixture.

Pytest fixtures for letp test session.
"""
import logging
import os
import random
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

import socket_server
import swilog
from pytest_test_campaign import TestsCampaignJson
from pytest_test_config import TestConfig
from pytest_test_report import TestReporter

__copyright__ = "Copyright (C) Sierra Wireless Inc."

pytest_plugins = [
    "pytest_target",
    "pytest_legato",
    "pytest_hardware",
    "pytest_test_report",
]

# List containing tuples of all the tests and their configuration
test_list = []

# Add path to lib folder and build the target file list to exclude
excluded_list = []
if "LETP_TESTS" in os.environ:
    for path in os.walk(os.environ["LETP_TESTS"]):
        folder = path[0]
        if "lib" in folder and not folder.endswith("/target"):
            sys.path.insert(0, os.path.abspath(folder))
        if folder.endswith("/target"):
            for f in path[1:]:
                if len(f) != 0 and "test_" in f[0] and ".py" in f[0]:
                    excluded_test = os.path.join(path[0], f[0])
                    excluded_list.append(excluded_test)


def pytest_addoption(parser):
    """!Parse the option for this plugin."""
    parser.addoption("--config", action="append", help="xml configuration file")
    parser.addoption(
        "--use_uart",
        action="store_true",
        default=False,
        help="Use serial link instead of SSH",
    )
    parser.addoption(
        "--ci",
        action="store_true",
        default=False,
        help="For Jenkins CI, create a json file jenkins.json '\
            'corresponding to the xml parameters",
    )
    parser.addoption(
        "--html",
        action="store",
        help="Create a html report. Indicate the name of the html file",
    )
    parser.addoption(
        "--dbg-lvl",
        action="store",
        type=int,
        default=1,
        help="""legato debug level as an integer
                                                    0 = DEBUG,
                                                    1 = INFO (default),
                                                    2 = WARN,
                                                    3 = ERR,
                                                    4 = CRIT,
                                                    5 = EMERG""",
    )


def get_version():
    """!Get LeTP version from its git repo.

    Need to merge this one with the one in letp.py in refactoring.
    """
    _letp_repo_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        os.path.pardir,
        os.path.pardir,
        os.path.pardir,
        ".git",
    )
    version = subprocess.check_output(
        "git --git-dir={} describe --tags --always 2> /dev/null".format(
            _letp_repo_path
        ),
        shell=True,
    )
    version_str = version.decode("utf-8")
    return version_str


@pytest.hookimpl()
def pytest_report_header():
    """!Put LeTP version in the report header."""
    return "LeTP version: {}".format(get_version())


@pytest.mark.tryfirst
def pytest_load_initial_conftests(early_config, args):
    """!Load initial conftest setups."""
    newArgs = []
    junitxml = html = False

    if os.environ.get("LETP_TEST_SET") is None:
        # Set a default value for LETP_TEST_SET (set of public tests)
        os.environ["LETP_TEST_SET"] = "public"

    early_config.test_list = []
    for arg in args:
        # To Refactor:
        # Add test_dummy.py to have at least one test in the workspace.
        # This fake file is removed from the arguments after.
        # The reason is that json test campaigns can be outside a pytest workspace
        # and pytest finds the conftest.py based on the first test file
        if arg == "test_dummy.py":
            continue
        if arg.endswith(".json") and os.path.isfile(arg):
            test_list = TestsCampaignJson(arg).get_tests()
            early_config.test_list.extend(test_list)
            for test in test_list[0]:
                newArgs.append(test[0])
            # add the configuration from the json if any
            if len(test_list[2]) != 0:
                newArgs.append("--config")
                newArgs.append("%s" % ",".join(test_list[2]))
        else:
            newArgs.append(arg)
        if arg == "--ci":
            # Use collect-only option to generate json format.
            newArgs.append("--collect-only")
        if arg == "--junitxml":
            junitxml = True
        if arg == "--html":
            html = True
        if arg == "--json-report":
            # Set default output for json report.
            json_report_config = (
                "--json-report-omit warnings log --json-report-indent 4 ".split()
            )
            newArgs.extend(json_report_config)
    # Add automatically --junitxml if it is not set when using --html
    if html and not junitxml:
        newArgs.append("--junitxml=%s" % "test.xml")
    args[:] = newArgs
    args[:] = ["--ignore=%s" % folder for folder in excluded_list] + args
    print("Use default config: %s" % TestConfig.default_cfg_file)


def pytest_configure(config):
    """!Add customized hooks definition for pytest_json_modifyreport."""
    if hasattr(config.option, "json_report") and config.option.json_report:
        # pytest_jsonreport will register the hook.
        return
    import pytest_jsonreport  # pylint: disable=import-outside-toplevel

    config.pluginmanager.add_hookspecs(pytest_jsonreport.plugin.Hooks)


def pytest_json_modifyreport(json_report):
    """!Merge test_base_reports configs into json report."""
    test_base_reports = pytest.default_cfg.test_base_reports
    json_report.update(test_base_reports)


@pytest.hookimpl()
def pytest_itemcollected(item):
    """!Store the collect items and tests."""
    item.session.default_cfg.store_tests(item)
    if not item.config.getoption("--ci"):
        return
    # Currently CI main_config store one test configs.
    TestConfig.last_test_cfg = TestConfig.build(item)


@pytest.hookimpl()
def pytest_collection_finish(session):
    """!Genereate config cache JSON."""
    # Report the main config of the last test is not good enough.
    default_cfg = session.default_cfg
    default_cfg.collect_test_configs()
    default_cfg.save_test_report_cache()


@pytest.hookimpl()
@pytest.mark.trylast
def pytest_collection_modifyitems(items):
    """!Modify the collected items.

    Will be called after collection has been performed.

    It may filter or re-order the items in-place.

    We shuffle the test running order here to avoid tests logic coupled together.

    @param List[_pytest.nodes.Item] items: list of item objects
    """
    random.shuffle(items)


def pytest_sessionstart(session):
    """!Read default config when session starts."""
    TestConfig.test_list = session.config.test_list
    default_cfg = TestConfig.read_default_config(session)
    default_cfg.save_test_cfg_cache()
    pytest.default_cfg = default_cfg
    session.default_cfg = default_cfg
    # Class variable will be valid for multiple sessions.
    # Try to use the above session default_cfg if possible.
    TestConfig.default_cfg = default_cfg


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session):
    """!Generate a html report."""
    TestConfig.test_list = []
    html_file = session.config.getoption("--html")
    junit_file = session.config.getoption("--junitxml")
    if session.config.getoption("--json-report", default=None):
        json_report = session.config.getoption("--json-report-file")
    else:
        # contains test result.
        json_report = TestConfig.test_base_report_cache
    if html_file and junit_file and json_report:
        test_reporter = TestReporter(
            session.default_cfg, html_file, junit_file, json_report
        )
        test_reporter.build()


def get_default_cfg():
    """!Get the default configuration for the test."""
    return TestConfig.default_cfg.get()


## @defgroup letpFixtureGroup The fixtures related to letp global.
# @{
@pytest.fixture(autouse=True, scope="session")
def init_log(request):
    """!Initialize logging for the session.

    pytest log capture happens after pytest_sessionstart.
    We need to init log here as a session fixture after capture.

    Before this function, there should be no swilog calls.
    Otherwise, the swilog will be broken.
    """
    debugLevel = request.config.getoption("--dbg-lvl")
    print("Init dbg-lvl %s" % str(debugLevel))
    lvl_dict = {
        -1: logging.NOTSET,
        0: logging.DEBUG,
        1: logging.INFO,
        2: logging.WARNING,
        3: logging.ERROR,
        4: logging.CRITICAL,
    }
    swilog.init(lvl_dict[debugLevel])
    yield
    swilog.shutdown()


@pytest.fixture(scope="function")
def test_config(request):
    """!Build a test configuration object."""
    target_config = TestConfig.build(request.node)
    assert isinstance(target_config, TestConfig)
    target_config.save_test_cfg_cache(TestConfig.last_test_config)
    return target_config


@pytest.fixture(scope="function")
def read_config(test_config):
    """!Read the xml configuration file for a test.

    A particular test can have some extra config files declared in the
    json file or with the config marker.

    Get the values of the xml configuration file.
    read_config returns an elementTree object. <br>
    To access to the value of an element,
    use read_config.findtext(“path/of/the/element”), such as:

    ~~~~~~~~~~~~~{.py}
    def test_read_0001(target, read_config):
        nfs_dir = read_config.findtext(“host/nfs_mount”)
    ~~~~~~~~~~~~~

    To find a node, use read_config.find. <br>
    For the available APIs, see
    <A HREF="https://docs.python.org/2/library/
    xml.etree.elementtree.html#module-xml.etree.ElementTree">
    Element Tree</A>

    @warning Do not use "module/ssh/ip_address" :
    target_ip = read_config.findtext(“module/ssh/ip_address”)
    use target.target_ip instead. Indeed, the IP address can change
    between reboot.
    If you use also uart, LeTP will use the uart commands to get the
    new IP address after reboot. Moreover, TARGET_IP environment variable
    has more priority than the value in the xml file.
    """
    return test_config.get()


@pytest.fixture(scope="session")
def read_config_default(request):
    """!Read the default xml configuration for the whole session."""
    session = request.node.session
    return session.default_cfg.get()


@pytest.fixture(autouse=True, scope="function")
def reset_error_list():
    """!Reset the log error list before each test."""
    swilog.error_list = []


@pytest.fixture(autouse=True, scope="session")
def set_locale():
    """!All messages in english."""
    os.environ["LC_ALL"] = "C"


@pytest.fixture(autouse=True, scope="function")
def banner(request):
    """!Print Test banner."""
    test_name = request.node.name
    begin_msg = "========== Begin of %s ==========" % test_name
    equal_nb = 2 * 21
    line = "=" * (equal_nb + len(begin_msg))
    swilog.info(line)
    swilog.info(line)
    swilog.step(begin_msg)
    swilog.info(line)
    swilog.info(line)
    yield
    end_msg = "========== End of %s ==========" % test_name
    line = "=" * (equal_nb + len(end_msg))
    swilog.info(line)
    swilog.info(line)
    swilog.step(end_msg)
    swilog.info(line)
    swilog.info(line)


@pytest.fixture(scope="session")
def tcp_server(read_config_default):
    """!Create up to 4 TCP servers.

    It is possible to create up to 4 UDP and 4 TCP servers with LeTP.
    The servers will be created at startup and deleted at the end of
    the LeTP session.

    In host.xml, fill the port and IP address of each servers and
    indicates used="1". The IP address is optional because by default
    it takes "host/ip_address".

    Use the fixture tcp_server or udp_server in your test to get the
    list of the TCP/UDP servers you declared.

    ~~~~~~~~~~~~~{.py}
    def test_tcp_server(tcp_server, read_config):

        for i, serv in enumerate(tcp_server):
            swilog.step("server %d" % i)
            ip = read_config.findtext(
                "host/socket_server/tcp_%d/addr" % (i+1))
            port = int(read_config.findtext(
                "host/socket_server/tcp_%d/port" % (i+1)))
    ~~~~~~~~~~~~~
    """
    # Fixture based on default configuration
    # Do not use read_config which is function scope
    assert isinstance(read_config_default, ET.ElementTree)
    serv_list = []
    swilog.debug("start TCP servers")
    for i in range(1, 5):
        if read_config_default.find("host/socket_server/tcp_%d" % i).get("used") == "1":
            ip = read_config_default.findtext("host/socket_server/tcp_%d/addr" % i)
            if ip == "":
                # Take the Ip address of the host
                ip = read_config_default.findtext("host/ip_address")
                if ip == "":
                    assert 0, "Set the ip address of your host or of your server"
            port = int(
                read_config_default.findtext("host/socket_server/tcp_%d/port" % i)
            )
            assert port != "", "TCP/UDP IP server is set but no port"
            serv = socket_server.get_tcp_server(
                ip, port, responder=True, max_size=1000000
            )
            serv_list.append(serv)
    if len(serv_list) == 0:
        assert 0, (
            "Set the ip address of your host or of "
            "your server or set the used attribute to 1"
        )

    yield serv_list
    swilog.debug("TCP servers shutdown!")
    for serv in serv_list:
        serv.shutdown()
        serv.server_close()


@pytest.fixture(scope="session")
def udp_server(read_config_default):
    """!Create up to 4 UDP servers.

    Similar to pytest_letp.tcp_server.
    """
    # Fixture based on default configuration
    # Do not use read_config which is function scope
    swilog.debug("start UDP servers")
    assert isinstance(read_config_default, ET.ElementTree)
    serv_list = []
    for i in range(1, 5):
        if read_config_default.find("host/socket_server/udp_%d" % i).get("used") == "1":
            ip = read_config_default.findtext("host/socket_server/udp_%d/addr" % i)
            if ip == "":
                # Take the Ip address of the host
                ip = read_config_default.findtext("host/ip_address")
                if ip == "":
                    assert 0, "Set the ip address of your host or of your server"
            port = int(
                read_config_default.findtext("host/socket_server/udp_%d/port" % i)
            )
            assert port != "", "TCP/UDP IP server is set but no port"
            serv = socket_server.get_udp_server(
                ip, port, responder=True, max_size=1000000
            )
            serv_list.append(serv)
    if len(serv_list) == 0:
        assert (
            0
        ), "Set the ip address of your host or of your server \
            or set the used attribute to 1"

    yield serv_list
    swilog.debug("UDP servers shutdown!")
    for serv in serv_list:
        serv.shutdown()
        serv.server_close()


@pytest.fixture(scope="function")
def metrics(request, read_config):
    """!Fixture to collect and export fine grained metrics data.

    Users need to define metrics module to upload the performance data.
    e.g. elasticsearch.
    """
    try:
        # pylint: disable=import-outside-toplevel
        from metrics import Metrics
    except ModuleNotFoundError:
        swilog.error("metrics module was not implemented.")
        return

    collector = Metrics(request)
    yield collector
    collector.export(read_config)


# @}
