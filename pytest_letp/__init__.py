"""LeTP main fixture.

Pytest fixtures for letp test session.
"""
import logging
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import pytest

import _pytest.config
from pytest_letp.lib import socket_server
from pytest_letp.lib import swilog
from pytest_letp.pytest_test_campaign import TestsCampaignJson
from pytest_letp.pytest_test_config import TestConfig, TEST_CONFIG_KEY
from pytest_letp.pytest_test_report import TestReporter

internal_repo = os.path.expandvars("$LETP_INTERNAL_PATH")
if internal_repo:
    sys.path.insert(0, internal_repo)

# Expose the following pytest_* plugins to pytest for collection.
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(script_dir))


pytest_plugins = [
    "pytest_letp",
    "pytest_target",
    "pytest_legato",
    "pytest_hardware",
    "pytest_session_timeout",
    "pytest_letp_log",
    "pytest_test_report",
]


__copyright__ = "Copyright (C) Sierra Wireless Inc."


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


@pytest.hookimpl
def pytest_addoption(parser):
    """Parse the option for this plugin."""
    group = parser.getgroup("letp", "Sierra Wireless Legato Test Project(LETP)")
    group.addoption("--config", action="append", help="xml configuration file")
    group.addoption(
        "--use_uart",
        action="store_true",
        default=False,
        help="Use serial link instead of SSH",
    )
    group.addoption(
        "--ci",
        action="store_true",
        default=False,
        help="For Jenkins CI, create a json file jenkins.json "
        "corresponding to the xml parameters",
    )
    group.addoption("--html", action="store_true", help="Enable html report generation")

    # Path/Name to HTML file
    group.addoption(
        "--html-file",
        action="store",
        help="Create a html report. "
        "Indicate the name of the html file"
        "Default is log/<timestamp>_<testname>.html",
    )

    group.addoption(
        "--dbg-lvl",
        action="store",
        type=int,
        default=1,
        help="""legato or swilog debug level as an integer
                                                    0 = DEBUG,
                                                    1 = INFO (default),
                                                    2 = WARN,
                                                    3 = ERR,
                                                    4 = CRIT,
                                                    5 = EMERG""",
    )


def get_git_info(git_repo_path):
    """Get git name and version from its git repo.

    Return: git remote name and its version.
    """
    name_str = ""
    cmd_remote_url = ""
    if not os.path.exists(git_repo_path):
        return "", ""
    curr_path = os.getcwd()
    os.chdir(git_repo_path)

    if os.name == "nt":
        cmd_remote_url = "git remote get-url origin"
        cmd_ver = "git describe --tags --always"
    else:
        cmd_remote_url = (
            "basename $(git remote get-url origin 2> /dev/null) 2> /dev/null"
        )
        cmd_ver = "git describe --tags --always 2> /dev/null"

    try:
        name = subprocess.check_output(cmd_remote_url, shell=True)
    except subprocess.CalledProcessError:
        return "", ""

    if os.name == "nt":
        name_str = os.path.basename(os.path.normpath(name))
    else:
        name_str = name.decode("utf-8").strip("\n")

    version = subprocess.check_output(cmd_ver, shell=True)
    version_str = version.decode("utf-8").strip("\n")
    os.chdir(curr_path)
    return name_str, version_str


class ConfigAdapter:
    """Adapt config to letp needs."""

    def __init__(self, config):
        assert isinstance(config, _pytest.config.Config)
        self._config = config

    def set_ini_value(self, name, value):
        """Set pytest.ini value.

        We may need to change the default ini value for all letp tests.
        """
        ini_config = self._config.getini(name)
        if isinstance(ini_config, list):
            self._config.addinivalue_line(name, value)
        else:
            original_type = type(ini_config)
            new_value_type = type(value)
            assert (
                original_type == new_value_type
            ), "Cannot set different ini config type from {} to {}".format(
                original_type, new_value_type
            )
            self._config._inicache[name] = value


def _is_junitxml_configured(args):
    # --junitxml is documented in pytest docs
    # --junit-xml is supported in pytest help page
    return "--junitxml" in args or "--junit-xml" in args


def _cmdline_preparse(args, known_args):
    """Parse customized arguments before passing to pytest."""
    html_file = None

    if "--ci" in args:
        # Use collect-only option to generate json format.
        args.append("--collect-only")

    if "--json-report" in args:
        # Set default output for json report.
        json_report_config = (
            "--json-report-omit warnings log --json-report-indent 4 ".split()
        )
        args.extend(json_report_config)

    if "--html" in args:
        if "--html-file" in args:
            html_file = args[args.index("--html-file") + 1]
        else:
            log_file = known_args.log_file
            html_file = log_file.replace(".log", ".html")
            args.append("--html-file")
            args.append(html_file)

        if not _is_junitxml_configured(args):
            # Add automatically --junitxml if it is not
            # set when using --html
            # because html report uses junitxml data.
            junit_file = html_file.replace(".html", ".xml")
            args.append("--junitxml")
            args.append(junit_file)

    # We use swilog with sys.stdout, disable the logging.
    # Otherwise, the logging will be captured in both stdout
    # and logging plugin
    if "no:logging" not in args:
        args.append("-p")
        args.append("no:logging")


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, args):
    """Load initial conftest setups."""
    newArgs = []

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
        if arg and arg.endswith(".json") and os.path.isfile(arg):
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

    args[:] = newArgs
    args[:] = ["--ignore=%s" % folder for folder in excluded_list] + args
    _cmdline_preparse(args, early_config.known_args_namespace)
    print("Use default config: %s" % TestConfig.default_cfg_file)
    if _is_junitxml_configured(args):
        # Change the default value for junitxml plugin.
        adapter = ConfigAdapter(early_config)
        adapter.set_ini_value("junit_logging", "all")
        adapter.set_ini_value("junit_family", "legacy")


@pytest.mark.optionalhook
def pytest_metadata(metadata):
    """Put repo versions in metadata."""
    git_repo_path = os.path.join(os.path.abspath(os.path.dirname(__file__)))
    repo_paths = [git_repo_path]
    # If LeTP_TESTS has git control, add the path.
    if "LETP_TESTS" in os.environ:
        repo_paths.append(os.environ["LETP_TESTS"])
    for git_repo_path in repo_paths:
        repo_name, repo_version = get_git_info(git_repo_path)
        if repo_name and repo_name not in metadata:
            metadata[repo_name] = repo_version


@pytest.hookimpl()
def pytest_configure(config):
    """Add customized hooks definition for pytest_json_modifyreport."""
    if hasattr(config.option, "json_report") and config.option.json_report:
        # pytest_jsonreport will register the hook.
        return
    import pytest_jsonreport  # pylint: disable=import-outside-toplevel

    config.pluginmanager.add_hookspecs(pytest_jsonreport.plugin.Hooks)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Read default config when session starts."""
    TestConfig.test_list = (
        session.config.test_list if hasattr(session.config, "test_list") else []
    )
    default_cfg = TestConfig.read_default_config(session)
    default_cfg.save_test_cfg_cache()
    session.default_cfg = default_cfg
    session.config._store[TEST_CONFIG_KEY] = default_cfg
    # Class variable will be valid for multiple sessions.
    # Try to use the above session default_cfg if possible.
    TestConfig.default_cfg = default_cfg


@pytest.hookimpl()
def pytest_json_modifyreport(json_report):
    """Merge test_base_reports configs into json report."""
    test_base_reports = TestConfig.default_cfg.test_base_reports
    json_report.update(test_base_reports)


@pytest.hookimpl()
def pytest_itemcollected(item):
    """Store the collect items and tests."""
    default_cfg = item.session.config._store[TEST_CONFIG_KEY]
    default_cfg.store_tests(item)
    if not item.config.getoption("--ci"):
        return
    # Currently CI main_config store one test configs.
    TestConfig.last_test_cfg = TestConfig.build(item)


@pytest.hookimpl()
def pytest_collection_finish(session):
    """Generate config cache JSON."""
    # Report the main config of the last test is not good enough.
    default_cfg = session.config._store[TEST_CONFIG_KEY]
    default_cfg.collect_test_configs()
    default_cfg.save_test_report_cache()


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session):
    """Generate a html report.

    This needs to be the last because it depends on junit xml file
    generation.
    """
    TestConfig.test_list = []
    html_file = session.config.getoption("--html-file")
    junit_file = session.config.getoption("--junitxml")

    if not junit_file:
        # --junitxml is documented in pytest docs
        # --junit-xml is supported in pytest help page
        junit_file = session.config.getoption("--junit-xml")

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

        print("!!!!! Html report can be found here {}!!!!!".format(html_file))


def get_default_cfg():
    """Get the default configuration for the test."""
    return TestConfig.default_cfg.get()


@pytest.fixture(autouse=True, scope="session")
def init_log(request):
    """Initialize logging for the session.

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
    """Build a test configuration object."""
    target_config = TestConfig.build(request.node)
    assert isinstance(target_config, TestConfig)
    target_config.save_test_cfg_cache(TestConfig.last_test_config_file)
    return target_config


@pytest.fixture(scope="function")
def read_config(test_config):
    """Read the xml configuration file for a test.

    A particular test can have some extra config files declared in the
    json file or with the config marker.

    Get the values of the xml configuration file.
    read_config returns an elementTree object.
    To access to the value of an element,
    use read_config.findtext(“path/of/the/element”), such as:

    .. code-block:: python

        def test_read_0001(target, read_config):
            nfs_dir = read_config.findtext("host/nfs_mount")

    To find a node, use read_config.find.
    For the available APIs, see
    `Element Tree <https://docs.python.org/2/library/
    xml.etree.elementtree.html#module-xml.etree.ElementTree>`_

    .. warning::

        | Do not use "module/ssh/ip_address" :
        | target_ip = read_config.findtext(“module/ssh/ip_address”)
        | use target.target_ip instead. Indeed, the IP address can change
        | between reboot.
        | If you use also uart, LeTP will use the uart commands to get the
        | new IP address after reboot. Moreover, TARGET_IP environment variable
        | has more priority than the value in the xml file.
    """
    return test_config.get()


@pytest.fixture(scope="session")
def read_config_default(request):
    """Read the default xml configuration for the whole session."""
    session = request.node.session
    default_cfg = session.config._store[TEST_CONFIG_KEY]
    return default_cfg.get()


@pytest.fixture(autouse=True, scope="function")
def reset_error_list():
    """Reset the log error list before each test."""
    swilog.error_list = []


@pytest.fixture(autouse=True, scope="session")
def set_locale():
    """All messages in english."""
    os.environ["LC_ALL"] = "C"


@pytest.fixture(autouse=True, scope="function")
def banner(request):
    """Print Test banner."""
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
    """Create up to 4 TCP servers.

    It is possible to create up to 4 UDP and 4 TCP servers with LeTP.
    The servers will be created at startup and deleted at the end of
    the LeTP session.

    In host.xml, fill the port and IP address of each servers and
    indicates used="1". The IP address is optional because by default
    it takes "host/ip_address".

    Use the fixture tcp_server or udp_server in your test to get the
    list of the TCP/UDP servers you declared.

    .. code-block:: python

        def test_tcp_server(tcp_server, read_config):
            for i, serv in enumerate(tcp_server):
                swilog.step("server %d" % i)
                ip = read_config.findtext(
                    "host/socket_server/tcp_%d/addr" % (i+1))
                port = int(read_config.findtext(
                    "host/socket_server/tcp_%d/port" % (i+1)))
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
    """Create up to 4 UDP servers.

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
    """Fixture to collect and export fine grained metrics data.

    Users need to define metrics module to upload the performance data.
    e.g. elasticsearch.
    """
    try:
        # pylint: disable=import-outside-toplevel
        from letp_internal.metrics import Metrics
    except ModuleNotFoundError:
        swilog.error("metrics module was not implemented.")
        return

    collector = Metrics(request)
    yield collector
    collector.export(read_config)


# @}
