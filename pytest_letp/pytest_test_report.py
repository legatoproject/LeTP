"""Test report manager.

It generates intermediate junit.xml test report. It also generates the
human friendly HTML test report.
"""
import os
import random
import re
import urllib.request
from xml.etree.ElementTree import Element, parse
import pytest
from _pytest import junitxml
from pytest_letp.tools.html_report import test_report
from pytest_letp.tools.html_report.build_configuration import JsonExtender
from pytest_letp.pytest_test_config import TEST_CONFIG_KEY

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class LogXMLAdapter:
    """Log XML adapter to modify junit xml report.

    Reference: junitxml.LogXML
    """

    def __init__(self, log_xml):
        self._log_xml = log_xml
        self._xml_node_map = self._build_node_reporter_map()

    def _build_node_reporter_map(self):
        xml_node_map = {}
        for node_reporter in self._log_xml.node_reporters_ordered:
            assert isinstance(node_reporter, junitxml._NodeReporter)
            xml_obj = node_reporter.to_xml()
            assert isinstance(xml_obj, Element), "Not valid xml object from junixml."
            node_id = xml_obj.attrib["file"] + "::" + xml_obj.attrib["name"]
            xml_node_map[node_id] = node_reporter
        return xml_node_map

    def _find_xml_node(self, collected_test_name):
        for key, node_reporter in self._xml_node_map.items():
            if key.endswith(collected_test_name):
                return node_reporter
        print(
            "{} was not found in junit xml report. "
            "Use the test running order for test report! ".format(collected_test_name)
        )
        return None

    def reorder_tests_junit_results(self, original_ordered_tests):
        """To reorder junit test results stored in LogXML."""
        if not self._xml_node_map:
            # not captured any junit xml results. e.g. capture=no
            return
        # reorder the junit xml node report according to collected tests
        original_ordered_node_reporters = []
        for test_name in original_ordered_tests:
            node_reporter = self._find_xml_node(test_name)
            original_ordered_node_reporters.append(node_reporter)
        if original_ordered_node_reporters:
            self._log_xml.node_reporters_ordered = original_ordered_node_reporters
        else:
            print("Did not restore the order of {}".format(original_ordered_tests))


def _get_log_xml(config):
    """Get junit xml object from junitxml plugin.

    This depends on junitxml. If pytest version upgrade, this code may
    need to change.
    """
    if hasattr(config, "_store"):
        log_xml = config._store.get(junitxml.xml_key, None)
        assert isinstance(log_xml, junitxml.LogXML)
        return log_xml
    return None


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items, session):
    """Modify the collected items.

    Will be called after collection has been performed.

    It may filter or re-order the items in-place.

    We shuffle the test running order here to avoid tests logic coupled together.

    :param List[_pytest.nodes.Item] items: list of item objects
    :param session:  Current session
    """
    default_cfg = session.config._store[TEST_CONFIG_KEY]
    randomize = "true" in default_cfg.is_random().lower()
    group_execute = default_cfg.get().getroot().find("test_run/group_execute").text
    if randomize:
        random.shuffle(items)
    if group_execute:
        if "http" in group_execute:
            group_file_path = "/tmp/group.xml"
            urllib.request.urlretrieve(group_execute, group_file_path)
        else:
            group_file_path = group_execute
        session.items = group_test_executed(items, group_file_path)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session):
    """Modify the report when the session finishes.

    We shuffled the test running order in pytest_collection_modifyitems.
    We will restore the order here.
    """
    junit_file = session.config.getoption("--junitxml")
    if not junit_file:
        return
    default_cfg = session.config._store[TEST_CONFIG_KEY]
    if "true" not in default_cfg.is_random().lower():
        return
    _log_xml = _get_log_xml(session.config)
    if _log_xml:
        LogXMLAdapter(_log_xml).reorder_tests_junit_results(default_cfg.collected_tests)


class TestReporter:
    """Test reporter ."""

    def __init__(self, test_config, html_file, junit_file, json_file):
        """Have a LETP test reporter.

        Keyword Arguments:
        :param test_config: TestConfig object
        :param html_file: The output html file.
        :param junit_file: The Junit format result from junitxml plugin.
        :param json_file: The json file extra test configs
                          and environment setup,
                          pytest result(including xpass, xfail)
        """
        self._html_file = html_file
        self._junit_file = junit_file
        self._json_file = json_file
        self._test_config = test_config

    def build(self):
        """Build test report into HTML and JSON format."""
        if not os.path.exists(self._junit_file):
            print("Need to have {}".format(self._junit_file))
            return
        if not os.path.exists(self._json_file):
            print("Need to have {}".format(self._json_file))
            return
        if not self._html_file:
            print("Need to have html file setup: {}".format(self._html_file))
            return
        jenkins_job = self._test_config.get_jenkins_job()
        target_name = self._test_config.get_target_name()
        test_campaign = self._test_config.get_test_campaign()
        title = "{}  {} {}".format(jenkins_job, target_name, test_campaign)

        json_extender = JsonExtender(self._json_file)
        json_input = "{}:{}".format(test_campaign, self._junit_file)
        json_extender.extend([json_input], self._test_config)

        test_report.TestReportHTMLBuilder().build(
            title, [self._json_file], self._html_file
        )


def group_test_executed(items, group_file_path):
    """Pre-order test execution with groups.

    Keyword Arguments:
    :param List[_pytest.nodes.Item] items: list of item objects
    :group_file_path: contains group file information
    """
    def sort_key(item):
        count = count_dict[item[1]]
        return (-count, item[1])

    root = (parse(group_file_path)).getroot()
    impor_group = []
    normal_group = []
    testcases = [testcase.text for testcase in root.findall('.//testcase')]
    temp_group = {testcase: [] for testcase in testcases}
    for item in items:
        for testcase in testcases:
            if testcase.lower() in item.nodeid.lower():
                temp_group[testcase].append(item)
                break

    impor_group = [
        item for sublist in temp_group.values() for item in sublist if sublist
    ]
    normal_group = [item for item in items if item not in impor_group]

    filtered_items = []
    for item in normal_group:
        match = re.search(r'[^/]+/([^/]+)\.py', item.nodeid)
        if match:
            a = match.group(1)
            a = re.sub(r'^(test_|le_)', '', a)
            filtered_items.append((item, a))

    count_dict = {}
    for _, a in filtered_items:
        count_dict[a] = count_dict.get(a, 0) + 1
    filtered_items.sort(key=sort_key)
    normal_group = [item for item, _ in filtered_items]

    items = impor_group + normal_group
    return items
