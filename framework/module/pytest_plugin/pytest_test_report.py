"""!@package pytest_test_report Test report manager.

It generates intermediate junit.xml test report. It also generates the
human friendly HTML test report.
"""
import os
import swilog
from build_configuration import JsonExtender
import test_report
import pytest
from _pytest import junitxml
from junitparser import TestCase

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def _get_log_xml(config):
    """Get junit xml object from junitxml plugin.

    This depends on junitxml. If pytest version upgrade, this code may
    need to change.
    """
    if hasattr(config, "_xml"):
        log_xml = config._xml
        assert isinstance(log_xml, junitxml.LogXML)
        return log_xml
    return None


def _build_node_reporter_map(log_xml):
    xml_node_map = {}
    for node_reporter in log_xml.node_reporters_ordered:
        assert isinstance(node_reporter, junitxml._NodeReporter)
        raw_xml = node_reporter.to_xml()
        if not hasattr(raw_xml, "uniobj"):
            continue
        xml_obj = TestCase.fromstring(raw_xml.uniobj)
        node_id = xml_obj._elem.attrib["file"] + "::" + xml_obj.name
        xml_node_map[node_id] = node_reporter
    return xml_node_map


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session):
    """!Modify the report when the session finishes.

    We shuffled the test running order in pytest_collection_modifyitems.
    We will restore the order here.
    """
    junit_file = session.config.getoption("--junitxml")
    if not junit_file:
        return

    log_xml = _get_log_xml(session.config)
    xml_node_map = _build_node_reporter_map(log_xml)

    if not xml_node_map:
        # not captured any junit xml results. e.g. capture=no
        return
    # reorder the junit xml node report according to collected tests
    original_ordered_tests = session.default_cfg.collected_tests
    original_ordered_node_reporters = []
    for test_name in original_ordered_tests:
        if test_name not in xml_node_map:
            swilog.warning(
                "{} was not found in junit xml report. "
                "Use the test running order for test report! ".format(test_name)
            )
            return
        node_reporter = xml_node_map[test_name]
        original_ordered_node_reporters.append(node_reporter)
    log_xml.node_reporters_ordered = original_ordered_node_reporters


class TestReporter:
    """!Test reporter ."""

    def __init__(self, test_config, html_file, junit_file, json_file):
        """!Have a LETP test reporter.

        Keyword Arguments:
        test_config -- TestConfig object
        html_file -- The output html file.
        junit_file -- The Junit format result from junitxml plugin.
        json_file -- The json file extra test configs
            and environment setup, pytest result(including xpass, xfail)
        """
        self._html_file = html_file
        self._junit_file = junit_file
        self._json_file = json_file
        self._test_config = test_config

    def build(self):
        """!Build test report into HTML and JSON format."""
        if not (
            os.path.exists(self._junit_file)
            and os.path.exists(self._json_file)
            and self._html_file
        ):
            return
        jenkins_job = self._test_config.get_jenkins_job()
        target_name = self._test_config.get_target_name()
        test_campaign = self._test_config.get_test_campaign()
        title = "{}  {} {}".format(jenkins_job, target_name, test_campaign)
        swilog.step("\nGenerating HTML report")
        json_extender = JsonExtender(self._json_file)
        json_input = "{}:{}".format(test_campaign, self._junit_file)
        json_extender.extend([json_input], self._test_config)

        test_report.TestReportHTMLBuilder().build(
            title, [self._json_file], self._html_file
        )

        swilog.debug("%s file created" % self._html_file)
