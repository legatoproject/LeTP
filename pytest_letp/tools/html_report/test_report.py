#!/usr/bin/env python3
"""!@package test_report Generate the final HTML test report.

Test Report is based on build configuration json results.
"""
import copy
import datetime
import json
import os
import sys
import re
import argparse
from collections import OrderedDict, Counter
import xml.etree.ElementTree as ET
import requests
from requests.auth import HTTPBasicAuth
from build_configuration import PytestResult, Components, Environment
from report_template import HTMLRender

__copyright__ = "Copyright (C) Sierra Wireless Inc."

ALL_COMPONENTS = [x.name for x in Components]
ALL_ENVIRONMENT_TYPES = list(Environment)
MERGE_REPORT = False
JIRA_SERVER = True
JIRA_USERNAME = ""
JIRA_PASSWORD = ""
GROUP_CONFIG_PATH = ""
REPORT_DATE = ""
THRESHOLD = ""


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-lines
class TestSummary:
    """!Test summary section in the table."""

    @classmethod
    def stat_keys(cls):
        """Summary stats keys."""
        return [
            "CollectedTests",
            "TestcasesRun",
            "Passed",
            "Failed",
            "xFailed",
            "Errors",
            "Skipped",
            "NoRun",
        ]

    def __init__(
        self, cfg="global", collected=0, tcs=0, failures=0, errors=0, tests_num=0
    ):
        self.cfg = cfg
        self.__status = None
        self.collected_tests_num = collected
        self.stat_tcs = tcs
        self.stat_passed = 0
        self.stat_skipped = 0
        self.stat_xfailed = 0
        self.stat_failures = failures
        self.stat_errors = errors
        self.tests_num_of_each_campaign = tests_num
        self.sub_summary = {}

    def add_summary(self, name, summary):
        """Add summary for all tests."""
        self.sub_summary[name] = summary

    def total_tcs(self):
        """Get total test cases."""
        return self.stat_tcs + sum([s.total_tcs() for s in self.sub_summary.values()])

    def total_tcs_of_each_campaign(self):
        """Get total test cases of each campaign."""
        if self.tests_num_of_each_campaign == 0:
            return self.total_tcs()
        return self.tests_num_of_each_campaign + sum(
            [s.total_tcs_of_each_campaign() for s in self.sub_summary.values()]
        )

    def total_passed(self):
        """Get total passed test cases."""
        return self.stat_passed + sum(
            [s.total_passed() for s in self.sub_summary.values()]
        )

    def total_xfailed(self):
        """Get total failed test cases with known issue."""
        return self.stat_xfailed + sum(
            [s.total_xfailed() for s in self.sub_summary.values()]
        )

    def total_failures(self):
        """Get total failed test cases without knowing issue."""
        return self.stat_failures + sum(
            [s.total_failures() for s in self.sub_summary.values()]
        )

    def total_errors(self):
        """Get total test cases in error state."""
        return self.stat_errors + sum(
            [s.total_errors() for s in self.sub_summary.values()]
        )

    def total_skipped(self):
        """Get total skipped test cases - run but have skipped status."""
        return self.stat_skipped + sum(
            [s.total_skipped() for s in self.sub_summary.values()]
        )

    def total_tcs_run(self):
        """Get total ran test cases."""
        return (
            self.total_passed()
            + self.total_failures()
            + self.total_xfailed()
            + self.total_errors()
        )

    def merge_total_collected(self):
        """Total cases collected for Nightly master."""
        path = (
            "/storage/artifacts/legato-qa/nightly/"
            + f"nightly_{REPORT_DATE}_master/collected_total.json"
        )
        if os.path.exists(path):
            with open(path, encoding="utf8") as f:
                exp_tests_for_targets = json.load(f)
            return sum(list(exp_tests_for_targets.values()))
        else:
            total = {}
            for key, value in self.sub_summary.items():
                sys_type = str(key).split("_")
                sys_type = sys_type[0]
                if sys_type not in total:
                    total[sys_type] = value.total_collected()
            return self.collected_tests_num + sum(list(total.values()))

    def total_collected(self):
        """Total collected cases in JSON input."""
        if self.cfg == "global":
            if MERGE_REPORT:
                return self.merge_total_collected()
            else:
                return self.collected_tests_num + sum(
                    [s.total_collected() for s in self.sub_summary.values()]
                )
        else:
            if self.collected_tests_num != 0:
                return self.collected_tests_num
            return self.total_tcs()

    def total_norun(self):
        """Get total norun test cases."""
        return self.total_collected() - self.total_tcs_run() - self.total_skipped()

    def total_compare(self):
        """Get total test cases to compare for report status."""
        if self.cfg != "global" and MERGE_REPORT:
            collected = self.total_tcs_of_each_campaign()
        else:
            collected = self.total_collected()

        return collected

    def stats(self):
        """Get Statistics of tests results."""
        divider = float(self.total_collected()) / 100
        if divider == 0:
            divider = 1

        return {
            "CollectedTests": {
                "count": self.total_collected(),
                "percentage": self.total_collected() / divider,
            },
            "TestcasesRun": {
                "count": self.total_tcs_run(),
                "percentage": self.total_tcs_run() / divider,
            },
            "Passed": {
                "count": self.total_passed(),
                "percentage": self.total_passed() / divider,
            },
            "xFailed": {
                "count": self.total_xfailed(),
                "percentage": self.total_xfailed() / divider,
            },
            "Failed": {
                "count": self.total_failures(),
                "percentage": self.total_failures() / divider,
            },
            "Errors": {
                "count": self.total_errors(),
                "percentage": self.total_errors() / divider,
            },
            "Skipped": {
                "count": self.total_skipped(),
                "percentage": self.total_skipped() / divider,
            },
            "NoRun": {
                "count": self.total_norun(),
                "percentage": self.total_norun() / divider,
            },
        }

    def set_status(self, status):
        """Set the status of the whole test suite."""
        self.__status = status

    def status(self):
        """Get the status of the whole test suite."""
        if self.__status:
            return self.__status

        collected = self.total_compare()

        total_exc = self.total_passed() + self.total_xfailed() + self.total_skipped()

        if total_exc != collected or total_exc == 0:
            return "FAILED"

        if self.total_collected() and not self.total_passed():
            # collected but not run.
            return "RUNNING"

        for key, value in self.sub_summary.items():
            print(f"Processed test report for {key}: {value.status()}")
            if value.status() != "PASSED":
                return value.status()

        return "PASSED"

    @staticmethod
    def merge_status(list_status: list):
        """Merge all status in the list."""
        final_status = "PASSED"
        for status in list_status:
            if status == "FAILED":
                return status
            if status != "PASSED":
                final_status = status
        return final_status

    def merge_summary(self, update_system, duplicated_system):
        """Merge the status with the same system type."""
        duplicated_sys_summary = self.sub_summary[duplicated_system]

        update_sumary = {"Config": update_system["Config"]}
        list_status = [update_system["Status"], duplicated_sys_summary.status()]
        update_sumary["Status"] = self.merge_status(list_status)

        for key in duplicated_sys_summary.stats().keys():
            if key == "CollectedTests":
                update_sumary[key] = update_system[key]
            else:
                duplicated_count = Counter(duplicated_sys_summary.stats()[key])
                update_count = Counter(update_system[key])
                update_count.update(duplicated_count)
                update_sumary[key] = dict(update_count)
            if key == "NoRun":
                update_sumary[key]["count"] = (
                    update_sumary["CollectedTests"]["count"]
                    - update_sumary["TestcasesRun"]["count"]
                    - update_sumary["Skipped"]["count"]
                )
            if "percentage" in update_sumary[key].keys():
                divider = float(update_sumary["CollectedTests"]["count"]) / 100
                if divider == 0:
                    divider = 1
                update_sumary[key]["percentage"] = float(
                    update_sumary[key]["count"] / divider
                )
        return update_sumary


class TestCaseResult:
    """!Result for one test case."""

    def __init__(self):
        """One test case result."""
        self.pytest_json_result = None
        self._system_out = ""
        self._system_err = ""

    def add_pytest_json_result(self, pytest_result):
        """Add pytest json result."""
        assert self.pytest_json_result is None, "Pytest already exists."
        self.pytest_json_result = pytest_result

    @property
    def message(self):
        """Property mesage."""
        exit_phase = None
        if "call" in self.pytest_json_result:
            exit_phase = self.pytest_json_result.get("call").get("crash")
        elif "setup" in self.pytest_json_result:
            exit_phase = self.pytest_json_result.get("setup").get("crash")
        if exit_phase:
            return exit_phase.get("message", "N/A")

        # Cover the case non-passing on the teardown
        if "teardown" in self.pytest_json_result:
            exit_phase = self.pytest_json_result.get("teardown").get("crash")
            if exit_phase:
                return exit_phase.get("message", "N/A")
        return ""

    @property
    def system_out(self):
        """System out from all xml elements.."""
        return self._system_out

    @system_out.setter
    def system_out(self, logs):
        """Set system out."""
        self._system_out = f"{self._system_out}\n{logs}"

    @property
    def system_err(self):
        """System err from all xml elements."""
        return self._system_err

    @system_err.setter
    def system_err(self, logs):
        """Set system err."""
        self._system_err = f"{self._system_err}\n{logs}"

    def update_pytest_logs(self, pytest_result, update_before_log=False):
        """Update tcs pytest log."""
        for run_phase in ["setup", "call", "teardown"]:
            if pytest_result.get(run_phase):
                pytest_log = [
                    pytest_result[run_phase].get("stdout", ""),
                    pytest_result[run_phase].get("stderr", ""),
                ]
                if update_before_log:
                    self._system_out = pytest_log[0]
                    self._system_err = pytest_log[1]
                else:
                    self.system_out = pytest_log[0]
                    self.system_err = pytest_log[1]


class GlobalTestCase:
    """!Test case for multiple systems.

    If the system did not have this test case, it will mark as N/A.
    """

    def __init__(self, name):
        self.name = name
        self.results = {}
        self.reinit_status = {}

    def is_passed(self):
        """Is this test case passed.

        Only qualify as success if there is at least one result, and all
        the results are successful.
        """
        if len(self.results) == 0:
            return False

        for res in self.results.values():
            test_result = res.pytest_json_result.get("outcome", "").lower()
            if "fail" in test_result or "error" in test_result:
                return False
        return True

    def _check_reinit_status(self, test_name, target_name, elmt):
        """Check status of Re_init test case.

        Return:
            True: Status of Reinit test case eligible for get flash time
            False: Status of Reinit test case not eligible for get flash time
            None: That is not a Reinit test case
        """
        if "L_ReinitTest" in test_name:
            logs = elmt.get("call", [])
            stdout_content = logs.get("stdout", "")
            list_target = ["wp76", "wp77", "rc76"]
            if "hl78" in target_name.lower():
                pattern = "Download Start"
                return self._check_warning(stdout_content, pattern)
            for target in list_target:
                if target in target_name.lower():
                    pattern = "INFO swiflash cmd"
                    return self._check_warning(stdout_content, pattern)
        return None

    @staticmethod
    def _check_warning(log, pattern):
        """Check the status of flash action in Reinit test case."""
        warnings = ["Device may be at some bad state", "Reboot failed"]
        start_log = log.rfind(pattern)
        end_log = log.rfind("Flash Finish") + len("Flash Finish")
        flash_log = log[start_log:end_log]
        for warning in warnings:
            if warning in flash_log:
                return False
        return True

    def get_create_target_result(self, target_name, test_name, elmt):
        """Get and create test result for the target."""
        origin_target_name = TestReportBuilder._parse_sys_type_name(target_name)
        list_target_name = list(self.results.keys())
        for target in list_target_name:
            if origin_target_name in target:
                if self.reinit_status[target] is False:
                    del self.results[target]
                    del self.reinit_status[target]
                else:
                    if target_name not in self.results:
                        self.results[target_name] = TestCaseResult()
                    return self.results[target_name]
        if target_name not in self.results:
            self.results[target_name] = TestCaseResult()
            self.reinit_status[target_name] = self._check_reinit_status(
                test_name, target_name, elmt
            )
        return self.results[target_name]


class TestCaseView:
    """!Test case view for ninja template."""

    def __init__(
        self, test_name, target_name, test_case: TestCaseResult, xfailed_ID=None
    ):
        self.test_name = test_name
        self.target_name = target_name
        self.xfailed_ID = xfailed_ID
        if test_case:
            assert isinstance(test_case, TestCaseResult)
        self.test_case = test_case

    @property
    def id(self):
        """Test case identifier/the path."""
        id_str = self.test_name + "_" + self.target_name
        id_str = id_str.replace(".", "_")
        id_str = id_str.replace(":", "_")
        id_str = re.sub("[^a-zA-Z0-9-_.:]", "_", id_str)
        return id_str

    def crash_status(self, phase, pytest_result=None):
        """Check crash for test case."""
        if pytest_result is not None:
            pytest_json_result = pytest_result
        else:
            pytest_json_result = self.test_case.pytest_json_result
        exit_phase = pytest_json_result.get(phase)
        if "crash" in exit_phase:
            result = exit_phase.get("outcome")
            if result == "skipped":
                return "xfailed"
            else:
                if phase in ["setup", "teardown"]:
                    return "error"
                else:
                    return result
        return None

    def first_crash(self, pytest_result=None):
        """Get the first non-passing status received."""
        result = None
        if pytest_result is not None:
            pytest_json_result = pytest_result
        else:
            pytest_json_result = self.test_case.pytest_json_result
            pytest_result = None
        if "call" in pytest_json_result:
            result = self.crash_status("call", pytest_result=pytest_result)
        elif "setup" in pytest_json_result:
            result = self.crash_status("setup", pytest_result=pytest_result)
        if result:
            return result

        if "teardown" in pytest_json_result:
            result = self.crash_status("teardown", pytest_result=pytest_result)
        return result

    @property
    def result(self):
        """Test result.

        If there is no test on the system, return N/A.
        """
        if not self.test_case:
            if self.xfailed_ID:
                return self.xfailed_ID
            return "N/A"

        result = self.first_crash()
        if result:
            if result == "xfailed":
                xfailed_mes = self.test_case.message
                if JIRA_USERNAME and not JiraServer().check_jira_ticket(xfailed_mes):
                    result = "failed"
            return result
        return self.test_case.pytest_json_result.get("outcome", "N/A")

    @property
    def html_class(self):
        """For Ninja usage."""
        return self.test_case.pytest_json_result.get("outcome", "N/A").lower()


class BuildConfiguration:
    """!Describes a specific build/test configuration."""

    def __init__(self, json_file, name=None):
        with open(json_file, encoding="utf8") as f:
            self.json_data = json.load(f)

        self.error = False

        self.flags = []
        if name:
            self.flags = name.split(":")
            self.flags.pop(0)
        self.pytest_results = {}
        self.pytest_test_name_array = []
        self.build_pytest_results()
        self.name = name or self.json_data.get("target_name", "N/A")
        self.name = self.name.replace(":wip", "")
        self.jenkins_build_number = self.get_jenkins_build_number()

    def consolidate_test_results(self, another_cfg):
        """!Consolidate test results."""
        self.pytest_results += another_cfg.pytest_results
        self.pytest_test_name_array += another_cfg.pytest_test_name_array

    def consolidate_summary(self, another_cfg):
        """!Consolidate summary statistics."""
        if "test_collected" in self.json_data:
            self.json_data["test_collected"] += another_cfg.json_data["test_collected"]
        if "summary" not in self.json_data:
            return
        current_summary = self.json_data["summary"]
        another_summary = another_cfg.json_data["summary"]
        for k, value in another_summary.items():
            current_summary.setdefault(k, 0)
            current_summary[k] += value

    def consolidate_target_components(self, another_cfg):
        """!Consolidate target components."""
        this_components = self.json_data.get("components")
        new_components = another_cfg.json_data.get("components")

        if new_components and not this_components:
            self.json_data["components"] = new_components

    def consolidate(self, another_cfg):
        """!Consolidate two build configurations.

        If they are in the same build number, share the same
        environment, consolidate it.
        """
        self.consolidate_summary(another_cfg)
        self.consolidate_test_results(another_cfg)
        self.consolidate_target_components(another_cfg)

    def build_pytest_results(self):
        """!Build pytest results if any."""
        if "tests" in self.json_data:
            self.pytest_results = self.json_data["tests"]
            self.pytest_test_name_array = [
                PytestResult(x).get_test_name() for x in self.pytest_results
            ]

    def _get_json(self, key):
        if key in self.json_data:
            return self.json_data[key]
        return None

    def get_collected_tests(self) -> list:
        """!Get Collected test case from initial json.

        Format example:
        {'name': ''scenario/command/test.py::test_command_by_filename''}
        """
        if "letp" in self.json_data and "tests" in self.json_data["letp"]:
            return [
                entry for entry in self.json_data["letp"]["tests"] if "name" in entry
            ]
        return []

    def get_info_keys(self):
        """Get info keys for this build."""
        if "info" not in self.json_data:
            return None
        return self.json_data["info"].keys()

    def get_env_dict(self):
        """Get environment dictionary based on info."""
        env_dict = {}
        env_dict["Config"] = self.name

        for comp in ALL_COMPONENTS:
            if "components" not in self.json_data:
                continue

            if comp in self.json_data["components"]:
                comp_version = self.json_data["components"][comp]
                env_dict[comp.replace("_", " ")] = comp_version

        info_keys = self.get_info_keys()
        if info_keys:
            env_dict.update(self.json_data["info"])

        for env_type in ALL_ENVIRONMENT_TYPES:
            env_dict = self.consolidate_runtime_env_info(
                env_dict, environment_type=env_type
            )

        return env_dict

    def consolidate_runtime_env_info(
        self, env_dict, environment_type=Environment.Plugins
    ):
        """Consolidate runtime environment information."""
        env_name = self.get_runtime_env_name(environment_type)
        if env_name:
            env_val = None
            for name, version in self.json_data["environment"][env_name].items():
                consolidate_val = f"{name}:{version}"
                env_val = (
                    consolidate_val if not env_val else f"{env_val}, {consolidate_val}"
                )

            env_dict.update({environment_type.name: env_val})

        return env_dict

    def get_runtime_env_name(self, environment_type=Environment.Plugins):
        """!Get runtime environment name from the metadata."""
        if (
            "environment" in self.json_data
            and environment_type.name in self.json_data["environment"]
        ):
            return environment_type.name
        return None

    def get_jenkins_build_number(self):
        """!Get jenkins build number."""
        if (
            "info" in self.json_data
            and "jenkins.build_number" in self.json_data["info"]
        ):
            return self.json_data["info"]["jenkins.build_number"]
        if (
            "environment" in self.json_data
            and "BUILD_NUMBER" in self.json_data["environment"]
        ):
            return self.json_data["environment"]["BUILD_NUMBER"]
        return "None"

    def _lookup_pytest_json_result(self, test_name) -> dict:
        """!Look up pytest json result dictionary."""
        if not test_name or test_name not in self.pytest_test_name_array:
            return {}
        idx = self.pytest_test_name_array.index(test_name)
        return self.pytest_results[idx]

    @staticmethod
    def _build_element_name(elmt, prefix):
        """!Build element name with prefix."""
        if elmt.classname:
            basename = f"{elmt.classname}.{elmt.name}"
        else:
            basename = elmt.name
        elmt_name = f"{prefix}{basename}"
        return elmt_name

    @staticmethod
    def _get_create_global_test_case(global_test_data, elmt_name):
        """!Create a global test case container."""
        if elmt_name in global_test_data:
            global_test_case = global_test_data[elmt_name]
        else:
            global_test_case = GlobalTestCase(elmt_name)
            global_test_data[elmt_name] = global_test_case
        return global_test_case

    @staticmethod
    def _convert_result_to_summary(test_result, summary):
        """Convert result into summary."""
        for value in test_result.items():
            if "pass" in value[1]:
                summary.stat_passed += 1
            elif "skip" in value[1]:
                summary.stat_skipped += 1
            elif "xfailed" in value[1]:
                summary.stat_xfailed += 1
            elif "fail" in value[1]:
                summary.stat_failures += 1
            elif "error" in value[1]:
                summary.stat_errors += 1
        summary.stat_tcs = len(test_result)

    @staticmethod
    def _get_duplicate_element_indices(test_list):
        """Get the value of duplicate element indices in list."""
        res = [idx for idx, val in enumerate(test_list) if val in test_list[:idx]]
        return res

    def _update_result_of_duplicate_tcs(self, pytest_result, test_result):
        """Update results of duplicate tcs in final report."""
        res = self._get_duplicate_element_indices(self.pytest_test_name_array)
        test_name = PytestResult(pytest_result).get_test_name()
        for i in res:
            if self.pytest_test_name_array[i] == test_name:
                if pytest_result.get("outcome") == "passed":
                    break
                pytest_result = self.pytest_results[i]
                test_result.update_pytest_logs(pytest_result, update_before_log=True)
                test_result.pytest_json_result = pytest_result
        return pytest_result

    @staticmethod
    def get_xfailed_mes(pytest_result):
        """Get a text message explaining why xfailed."""
        exit_phase = None
        if "call" in pytest_result:
            exit_phase = pytest_result.get("call").get("crash")
        elif "setup" in pytest_result:
            exit_phase = pytest_result.get("setup").get("crash")
        if exit_phase:
            return exit_phase.get("message", "N/A")

        if "teardown" in pytest_result:
            exit_phase = pytest_result.get("teardown").get("crash")
            if exit_phase:
                return exit_phase.get("message", "N/A")
        return ""

    @staticmethod
    def get_final_status(pytest_result):
        """Get the first non-passing status received.

        To convert result into summary.
        """
        if pytest_result.get("outcome") in ["skipped", "passed"]:
            return pytest_result.get("outcome")
        else:
            test_case_view = TestCaseView(None, None, None)
            result = test_case_view.first_crash(pytest_result=pytest_result)
            # cover xpassed status
            if result is None:
                result = "passed"
            return result

    def _iter_pytest_report(self, global_test_data, summary):
        """Iterate the test report and collect summary."""
        tests = self.json_data.get("tests", [])
        verify_duplicate_tcs = {}
        for elmt in tests:
            test_name = PytestResult(elmt).get_test_name()
            pytest_result = self._lookup_pytest_json_result(test_name)
            if not pytest_result:
                print(f"Unable to get the test result for {pytest_result}")
                continue
            global_test_case = self._get_create_global_test_case(
                global_test_data, test_name
            )
            test_result = global_test_case.get_create_target_result(
                self.name, test_name, elmt
            )

            if test_name not in verify_duplicate_tcs:
                test_result.add_pytest_json_result(pytest_result)
            else:
                pytest_result = self._update_result_of_duplicate_tcs(
                    pytest_result, test_result
                )

            outcome = self.get_final_status(pytest_result)
            verify_duplicate_tcs[test_name] = outcome
            if verify_duplicate_tcs[test_name] == "xfailed":
                xfailed_mes = self.get_xfailed_mes(pytest_result)
                if JIRA_USERNAME and not JiraServer().check_jira_ticket(xfailed_mes):
                    verify_duplicate_tcs[test_name] = "failed"
            self._add_pytest_test_logs(global_test_data, pytest_result)

        self._convert_result_to_summary(verify_duplicate_tcs, summary)

    def _add_pytest_test_logs(self, global_test_data, pytest_result):
        """Try to recover the test logs using pytest results."""
        if pytest_result:
            for test_name, global_test_case in global_test_data.items():
                test_result_to_recover = global_test_case.results.get(self.name)
                if (
                    PytestResult(pytest_result).get_test_name() == test_name
                    and test_result_to_recover
                ):
                    test_result_to_recover.update_pytest_logs(pytest_result)

    def process_test_data(self, global_test_data):
        """!Build test summary."""
        collected_tests_num = self._get_json("test_collected_total")
        tests_num_of_each_campaign = collected_tests_num
        if MERGE_REPORT:
            system_test_num = self._get_json("system_test_num")
            collected_tests_num = system_test_num
        elif "test_collected_total" not in self.json_data:
            test_collected = self._get_json("test_collected")
            tests_num_of_each_campaign = test_collected
        if collected_tests_num is None:
            collected_tests_num = 0
        if tests_num_of_each_campaign is None:
            tests_num_of_each_campaign = 0
        new_summary = TestSummary(
            self.name,
            collected=collected_tests_num,
            tests_num=tests_num_of_each_campaign,
        )
        if "state" in self.json_data:
            new_summary.set_status(self.json_data["state"])

        self._iter_pytest_report(global_test_data, new_summary)

        return new_summary


class TestReportBuilder:
    """!Building test report."""

    def __init__(self):
        self.build_cfg_list = []  # List of build configurations
        self.build_number_dict = {}  # build_id: BuildConfiguration instance
        self.build_names = {}  # Build cfgs may have the same name.
        # Build to differentiate the same name.
        self.build_idx = 1
        self.environment_dict = OrderedDict()  # List of env. info
        self.target_components = []
        self.testing_env_infos = []
        self.info_keys = []
        self.env_global_list = OrderedDict()
        self.summary = OrderedDict()
        self.test_summary = TestSummary()
        self.global_test_data = OrderedDict()
        self.results_headers = None
        self.groups = {}
        self.platform = {}
        self.group_summary = {}
        self.group_len = {}
        self.collected_test = {}
        self.summary_log = {
            "test_memory_size": {},
            "test_idle_memory": {},
            "test_idle_atip": {},
            "test_cpu_load_idle": {},
            "test_startup": {},
            "L_ReinitTest": {},
        }
        self.min_list = [
            "Device Up",
            "Used",
            "Legato Used",
            "Base Heap",
            "Base Static",
            "Legato Heap",
            "Legato Static",
        ]
        self.max_list = ["Free", "Total Idle", "Idle Percentage"]
        self.mem_cpu_boottime_tcs_list = [
            "test_memory_size",
            "test_idle_memory",
            "test_idle_atip",
            "test_cpu_load_idle",
            "test_startup_rtos",
            "test_startup_linux",
            "L_ReinitTest",
        ]
        self.key_memory = [
            "Base Heap",
            "Base Static",
            "Legato Heap",
            "Legato Static",
            "Legato Used",
            "Used",
            "Free",
            "Total",
        ]

    def set_unique_name(self, build_cfg):
        """!Set build configure name as the build configuration ID.

        One target may have multiple test runs in different env. We use
        build_idx to build the name that it's unique in test report.
        """
        list_name_build_cfg = [key[0] for key in self.build_names.items()]
        if build_cfg.name in list_name_build_cfg:
            temp_build_cfg_name = build_cfg.name
            # Name of new build configuration
            build_cfg.name = (
                f"{temp_build_cfg_name}_{self.build_names[temp_build_cfg_name]}"
            )
            self.build_names[temp_build_cfg_name] += 1
        self.build_names[build_cfg.name] = self.build_idx

    def register_new_build_configuration(self, build_cfg):
        """!Register a build configuration for the report."""
        build_id = build_cfg.jenkins_build_number
        if build_id == "None":
            build_id = build_cfg.name
        if build_id not in self.build_number_dict:
            self.build_number_dict[build_id] = build_cfg
            return build_cfg
        else:
            existing_build_cfg = self.build_number_dict[build_id]
            return existing_build_cfg

    @staticmethod
    def _get_entry_path(entry):
        entry_split = entry.split("=")
        if len(entry_split) == 2:
            entry_path = entry_split[1]
            entry_name = entry_split[0]
        elif len(entry_split) == 1:
            entry_path = entry_split[0]
            entry_name = None
        else:
            print(f"Too many '=' signs in {entry}")
            sys.exit(1)
        if os.path.exists(entry_path) is False:
            print(f"Could not find JSON file for {entry_path}")
            sys.exit(1)
        return entry_name, entry_path

    @staticmethod
    def _parse_sys_type_name(sys_name):
        """Return the type of system."""
        if re.search(r"_", sys_name):
            sys_type = re.search(r"(?P<sys_type>.*?)_", sys_name).group("sys_type")
        else:
            sys_type = sys_name
        return sys_type

    @staticmethod
    def _add_xfailedJira_ID(target_name, test_name, test_case, xfailed_element: dict):
        if target_name == "Jira ID" and xfailed_element["is_xfailed"]:
            test_case_view = TestCaseView(
                test_name,
                target_name,
                test_case,
                xfailed_ID=xfailed_element["xfailed_ID"],
            )
        else:
            test_case_view = TestCaseView(test_name, target_name, test_case)
            if test_case_view.result.lower() == "xfailed":
                xFailed_mes = test_case.message
                xfailed_reg = re.search(
                    r"XFailed:\s(?P<xfailed_ticket>.*)", xFailed_mes
                )
                if xfailed_reg:
                    xfailed_element["xfailed_ID"] = xfailed_reg.group("xfailed_ticket")
                xfailed_element["is_xfailed"] = True
        return test_case_view, xfailed_element

    def sort_file_by_times(self, json_path):
        """Sort json file by time."""
        list_build_cfg = []
        cre_time = ""
        for entry in json_path:
            dt_obj = {}
            entry_name, entry_path = self._get_entry_path(entry)
            build_cfg = BuildConfiguration(entry_path, entry_name)
            if "created" in build_cfg.json_data:
                cre_time = build_cfg.json_data["created"]
            else:
                cre_time = os.path.getctime(entry_path)
            cre_time = datetime.datetime.fromtimestamp(cre_time)
            dt_obj["time"] = cre_time
            dt_obj["entry_name"] = entry_name
            dt_obj["entry_path"] = entry_path
            list_build_cfg.append(dt_obj)

        list_build_cfg.sort(key=lambda item: item.get("time"))
        return list_build_cfg

    def _add_build_cfgs(self, json_path):
        list_build_cfg = self.sort_file_by_times(json_path)
        temp_list_build_cfg = {}
        for entry in list_build_cfg:
            build_cfg = BuildConfiguration(entry["entry_path"], entry["entry_name"])
            self.set_unique_name(build_cfg)
            print(f'[{build_cfg.name}] {entry["entry_path"]} {entry["time"]}')
            registered_cfg = self.register_new_build_configuration(build_cfg)
            if registered_cfg == build_cfg:
                # Update the name of the build configuration in the report
                if re.match(r"\w+\d+\_\d+", build_cfg.name):
                    module_name = re.search(
                        r"(?P<module_name>.*)_\d*", build_cfg.name
                    ).group("module_name")
                    # Check if module_name is in temp_list_build_cfg
                    # to update build configuration name in report
                    if module_name in temp_list_build_cfg:
                        build_cfg.name = (
                            f"{module_name}_{temp_list_build_cfg[module_name]}"
                        )
                        temp_list_build_cfg[module_name] += 1
                temp_list_build_cfg[build_cfg.name] = 1
                self.build_cfg_list.append(build_cfg)
            else:
                registered_cfg.consolidate(build_cfg)

    def _add_env_list_header(self):
        # Environment parts
        self._add_target_components()
        self._add_test_env_infos()

    def _add_target_components(self):
        self.target_components.append("Config")

        for comp in ALL_COMPONENTS:
            self.target_components.append(comp.replace("_", " "))

    def _add_test_env_infos(self):
        self.testing_env_infos.append("Config")
        self.testing_env_infos.append("Execution_time")
        info_keys = set()
        for build_cfg in self.build_cfg_list:
            assert isinstance(build_cfg, BuildConfiguration)
            current_info_keys = build_cfg.get_info_keys()

            if current_info_keys:
                info_keys.update(current_info_keys)

            for env_type in ALL_ENVIRONMENT_TYPES:
                current_env_name = build_cfg.get_runtime_env_name(env_type)
                if current_env_name:
                    info_keys.update([current_env_name])

        self.info_keys = list(info_keys)
        self.info_keys.sort()
        for key in self.info_keys:
            self.testing_env_infos.append(key)

    def _process_all_build_cfgs(self):
        """Add test summary section."""
        for build_cfg in self.build_cfg_list:
            self.environment_dict[build_cfg.name] = build_cfg.get_env_dict()
            if "jenkins.build_url" in self.environment_dict[build_cfg.name].keys():
                build_url = self.environment_dict[build_cfg.name]["jenkins.build_url"]
                exe_time = self.get_execution_time(build_url)
                self.environment_dict[build_cfg.name]["Execution_time"] = exe_time
            else:
                self.environment_dict[build_cfg.name]["Execution_time"] = "N/A"
            new_summary = build_cfg.process_test_data(self.global_test_data)
            self.test_summary.add_summary(build_cfg.name, new_summary)

    def _add_env_global_list(self, global_env, global_env_path):
        # From args
        if global_env:
            for e in global_env:
                kv = e.split("=")
                if len(kv) < 2:
                    raise Exception(f"Invalid key value '{e}', format should be k=v")

                k = kv.pop(0)
                v = "=".join(kv)
                self.env_global_list[k] = {"text": v}
        # From file
        if global_env_path:
            with open(global_env_path, encoding="utf8") as f:
                j = json.load(f)
                self.env_global_list.update(j)

    def simulator_data(self, not_run_sys_type_list):
        """Simulate results for non-running targets."""
        path = (
            "/storage/artifacts/legato-qa/nightly/"
            + f"nightly_{REPORT_DATE}_master/collected_total.json"
        )
        if not_run_sys_type_list and os.path.exists(path):
            keys = [
                "CollectedTests",
                "TestcasesRun",
                "Passed",
                "Failed",
                "xFailed",
                "Errors",
                "Skipped",
                "NoRun",
            ]
            with open(path, encoding="utf8") as f:
                exp_tests_for_targets = json.load(f)

            for item in not_run_sys_type_list:
                total_testcases = exp_tests_for_targets[item.upper()]
                cache_summary = {"Config": item}
                cache_summary["Status"] = "FAILED"
                status = {key: {"count": 0, "percentage": 0.0} for key in keys}
                status.update(
                    {
                        "CollectedTests": {
                            "count": total_testcases,
                            "percentage": 100.0,
                        },
                        "NoRun": {"count": total_testcases, "percentage": 100.0},
                    }
                )
                cache_summary.update(status)
                self.summary[item] = cache_summary

    def check_status_platform(self, sub_systems_names):
        """Check the status of platform."""
        exp_sys_type_list = [
            "wp76xx",
            "wp76xx-onlycap",
            "wp77xx",
            "hl7812",
            "rc76",
            "em92xx",
            "hl7900",
        ]
        run_sys_type_list = []
        # platforms with multi campaigns
        # {platform: [number of campaigns run, expected quantity], ...}
        count_campaigns = {
            "wp76xx": [0, 2],
            "wp77xx": [0, 2],
            "hl7812": [0, 4],
            "rc76": [0, 2],
        }
        for sys_name in sub_systems_names:
            sys_type = self._parse_sys_type_name(sys_name)
            if sys_type in count_campaigns:
                count_campaigns[sys_type][0] += 1
            if sys_type not in run_sys_type_list:
                run_sys_type_list.append(sys_type)
                sub_summary = self.test_summary.sub_summary[sys_name]
                sub_summary.cfg = sys_type
                cache_summary = {"Config": sub_summary.cfg}
                cache_summary["Status"] = sub_summary.status()
                cache_summary.update(sub_summary.stats())
                self.summary[sub_summary.cfg] = cache_summary
            else:
                update_summary = self.test_summary.merge_summary(
                    self.summary[sys_type], sys_name
                )
                self.summary[sys_type] = update_summary
        for sys_type, count in count_campaigns.items():
            if count[0] not in [0, count[1]]:
                self.summary[sys_type]["Status"] = "FAILED"
        not_run_sys_type_list = [
            item for item in exp_sys_type_list if item not in run_sys_type_list
        ]

        self.simulator_data(not_run_sys_type_list)

    def _update_percentage(self, entry_name, count):
        self.summary[entry_name]["Passed"]["count"] += count
        self.summary[entry_name]["CollectedTests"]["count"] += count
        self.summary[entry_name]["TestcasesRun"]["count"] += count
        divider = float(self.summary[entry_name]["CollectedTests"]["count"]) / 100
        for key, value in self.summary[entry_name].items():
            if key not in ("Config", "Status"):
                value["percentage"] = float(value["count"] / divider)

    def _add_collected_test(self, paths):
        all_targets = self.results_headers[1:]
        total = 0
        for entry in paths:
            count = 0
            entry_name, entry_path = self._get_entry_path(entry)
            if entry_name:
                entry_name = entry_name.split(":")[0]
            try:
                with open(entry_path, "r", encoding="utf8") as file:
                    for line in file:
                        line = line.strip()
                        name, result = line.split()
                        if name not in self.collected_test:
                            self.collected_test[name] = {
                                target: "N/A" for target in all_targets
                            }
                        self.collected_test[name][entry_name] = result.lower()
                        # Add passed tcs to report
                        if result == "PASSED":
                            count += 1
                    self._update_percentage(entry_name, count)
                    total += count
            except:
                print(f"[ERROR]: {Exception}")
        self._update_percentage("global", total)

    def _add_summary_section(self, txt_paths=""):
        summary_global = {"Config": self.test_summary.cfg}
        summary_global["Status"] = self.test_summary.status()
        summary_global.update(self.test_summary.stats())
        self.summary[self.test_summary.cfg] = summary_global

        sub_systems_names = sorted(self.test_summary.sub_summary.keys())

        if MERGE_REPORT:
            self.check_status_platform(sub_systems_names)
        else:
            for sys_name in sub_systems_names:
                sub_summary = self.test_summary.sub_summary[sys_name]
                cache_summary = {"Config": sub_summary.cfg}
                cache_summary["Status"] = sub_summary.status()
                cache_summary.update(sub_summary.stats())
                self.summary[sub_summary.cfg] = cache_summary
        if txt_paths:
            self._add_collected_test(txt_paths)

        status = self.test_summary.status()
        return status

    @staticmethod
    def get_execution_time(jenkins_build_url):
        """Get the execution time of the Jenkins job."""
        url = f"{jenkins_build_url}/api/json"
        print(f"url: {url}")
        response = requests.get(url, verify=False).content.decode("utf-8")
        result = re.search(r'"duration":(?P<time>\d+)', response)
        if result:
            milli_time = result.group("time")
            time = str(datetime.timedelta(seconds=int(milli_time) // 1000))
            duration = time.split(":")
            if "day" in time:
                execution_time = f"{duration[0]} hr"
            elif duration[0] == "0":
                execution_time = f"{duration[1]} min, {duration[2]} s"
            else:
                execution_time = f"{duration[0]} hr, {duration[1]} min"
        else:
            execution_time = "N/A"
        return execution_time

    @staticmethod
    def get_test_case(target_name, original_name, global_test_case):
        """Get test case if it is run for target."""
        test_case = None
        if MERGE_REPORT and original_name != "wp76xx-onlycap":
            if target_name in original_name:
                test_case = global_test_case.results[original_name]
        elif not MERGE_REPORT or original_name == "wp76xx-onlycap":
            if target_name == original_name:
                test_case = global_test_case.results[original_name]
        return test_case

    def collect_test_result(self, global_test_case, test_name):
        """Collect test result from the test data."""
        xfailed_element = {"is_xfailed": False, "xfailed_ID": None}
        result = []
        all_targets = self.results_headers[1:]

        for target_name in all_targets:
            for original_name in global_test_case.results.keys():
                test_case = self.get_test_case(
                    target_name, original_name, global_test_case
                )
                test_case_view, xfailed_element = self._add_xfailedJira_ID(
                    target_name, test_name, test_case, xfailed_element
                )
                final_test_case_view = test_case_view
                if test_case_view.result != "N/A":
                    break
            result.append(final_test_case_view)
        return result

    def get_result_groups(self, filter_fn):
        """Get table of result groups with filter filtering."""
        results = []
        group_status = {}

        test_group = TestGroups(
            GROUP_CONFIG_PATH, self.global_test_data, self.results_headers
        )
        self.groups = test_group.gen_groups()

        for group, test_cases in self.groups.items():
            self.group_len[group] = len(test_cases)
            group_status = test_group.gen_group_table(group_status, group)
            for test_name, global_test_case in test_cases.items():
                if filter_fn and not filter_fn(global_test_case):
                    continue
                result = self.collect_test_result(global_test_case, test_name)
                results.append(result)
                if not filter_fn:
                    self.group_summary = test_group._summarize_group(
                        group, result, group_status
                    )
        if not filter_fn and MERGE_REPORT:
            self.platform = test_group.gen_result_platforms()

        return results

    def gen_results_table(self, filter_fn=None):
        """!Get results table with filtering."""
        results = []

        if GROUP_CONFIG_PATH:
            results = self.get_result_groups(filter_fn)
        else:
            for test_name, global_test_case in self.global_test_data.items():
                if filter_fn and not filter_fn(global_test_case):
                    continue

                result = self.collect_test_result(global_test_case, test_name)
                results.append(result)
        return results

    def generate_report(self, results_all, status, other_contents: dict, data=None):
        """!Generate the test report."""
        raise NotImplementedError

    def _add_results_headers(self):
        """Add the result header.

        e.g.Testcases | HL7800 | WP76.
        """
        fixed_order = ["wp76xx", "wp76xx-onlycap", "wp77xx", "hl7812", "rc76"]
        results_headers = ["Testcases"]
        if MERGE_REPORT:
            build_cfg_names = []
            sys_type_dict = {}
            for build_cfg in self.build_cfg_list:
                sys_type = self._parse_sys_type_name(build_cfg.name)

                if sys_type not in sys_type_dict:
                    sys_type_dict[sys_type] = build_cfg.name
                    build_cfg_names.append(sys_type)
        else:
            build_cfg_names = [build_cfg.name for build_cfg in self.build_cfg_list]
        for name in fixed_order:
            if name in build_cfg_names:
                results_headers.append(name)
                build_cfg_names.remove(name)

        build_cfg_names.append("Jira ID")
        results_headers.extend(build_cfg_names)

        self.results_headers = results_headers

    @staticmethod
    def _get_target_name(tc):
        """Get target name to support collect data of memory, cpu, boot, flash.

        time.
        """
        if "hl78" in tc.target_name.lower():
            target_name = "RTOS"
        elif "rc76" in tc.target_name.lower():
            target_name = "ThreadX"
        elif "wp76" in tc.target_name.lower():
            target_name = "Linux(WP76xx)"
        elif "wp77" in tc.target_name.lower():
            target_name = "Linux(WP77xx)"
        return target_name

    def _data_of_test_idle_memory(self, memory, test_log, platforms, target_name):
        """Collect data of test_idle_memory."""
        value_free = re.search(r"Final Free:\s+(?P<free>\d+\.\d+)", test_log).group(
            "free"
        )
        value_used = re.search(r"Final Used:\s+(?P<used>\d+\.\d+)", test_log).group(
            "used"
        )
        value_total = re.search(r"Final Total:\s+(?P<total>\d+\.\d+)", test_log).group(
            "total"
        )
        for target in platforms:
            if target == target_name:
                self.summary_log["test_idle_memory"][target_name] = test_log
                memory["Free"][target_name] = round(float(value_free), 2)
                memory["Used"][target_name] = round(float(value_used), 2)
                memory["Total"][target_name] = round(float(value_total), 2)
        return memory

    def _data_of_test_memory_size(self, memory, test_log, platforms, target_name):
        """Collect data of test_memory_size."""
        legato_used = re.search(r"'legato':\s\[(?P<used>\d+)", test_log).group("used")
        for target in platforms:
            if target == target_name:
                self.summary_log["test_memory_size"][target_name] = test_log
                memory["Legato Used"][target_name] = round(float(legato_used), 2)
        return memory

    def _data_of_test_idle_atip(self, memory, test_log, platforms, target_name):
        """Collect data of test_idle_atip test case."""
        value_free = re.search(r"Total Free:\s+(?P<free>\d+)", test_log).group("free")
        max_used = re.search(r"Max Used:\s+(?P<max_used>\d+)", test_log).group(
            "max_used"
        )
        base_heap = re.search(r"Base Heap max:\s+(?P<base_heap>\d+)", test_log).group(
            "base_heap"
        )
        base_static = re.search(r"Base Static:\s+(?P<base_static>\d+)", test_log).group(
            "base_static"
        )
        legato_heap = re.search(r"Legato Heap:\s+(?P<legato_heap>\d+)", test_log).group(
            "legato_heap"
        )
        legato_static = re.search(
            r"Legato Static:\s+(?P<legato_static>\d+)", test_log
        ).group("legato_static")
        for target in platforms:
            if target == target_name:
                self.summary_log["test_idle_atip"][target_name] = test_log
                memory["Base Heap"][target_name] = round(float(base_heap), 2)
                memory["Base Static"][target_name] = round(float(base_static), 2)
                memory["Legato Heap"][target_name] = round(float(legato_heap), 2)
                memory["Legato Static"][target_name] = round(float(legato_static), 2)
                memory["Used"][target_name] = round(float(max_used), 2)
                memory["Free"][target_name] = round(float(value_free), 2)
        return memory

    def _collect_data_of_memory(self, memory, tc, platforms):
        """Collect data of memory on all target."""
        test_log = None
        target_name = self._get_target_name(tc)
        tc_log = tc.test_case.pytest_json_result["call"]
        for key in tc_log.keys():
            if key == "stdout":
                test_log = tc_log["stdout"]
        if tc.test_name.split(".")[-1] == "test_idle_memory" and test_log is not None:
            memory = self._data_of_test_idle_memory(
                memory, test_log, platforms, target_name
            )
        elif tc.test_name.split(".")[-1] == "test_idle_atip" and test_log is not None:
            memory = self._data_of_test_idle_atip(
                memory, test_log, platforms, target_name
            )
        elif tc.test_name.split(".")[-1] == "test_memory_size" and test_log is not None:
            memory = self._data_of_test_memory_size(
                memory, test_log, platforms, target_name
            )
        return memory

    def _collect_data_of_cpu(self, cpu, tc):
        """Collect data of cpu on all target."""
        test_log = None
        target_name = self._get_target_name(tc)
        tc_log = tc.test_case.pytest_json_result["call"]
        for key in tc_log.keys():
            if key == "stdout":
                test_log = tc_log["stdout"]
        if tc.test_name.split(".")[-1] == "test_cpu_load_idle" and test_log is not None:
            if target_name == "RTOS":
                idle_percen = re.search(
                    r"'Total':\s\[(?P<idle_percen>\d+)", test_log
                ).group("idle_percen")
                self.summary_log["test_cpu_load_idle"][target_name] = test_log
                cpu["Idle Percentage"][target_name] = round(float(idle_percen), 2)
            elif "Linux" in target_name:
                total_idle = re.search(
                    r"'Total Idle':\s\[(?P<total_idle>\d+\.\d)", test_log
                ).group("total_idle")
                idle_percen = re.search(
                    r"'Total':\s\[(?P<idle_percen>\d+\.\d)", test_log
                ).group("idle_percen")
                self.summary_log["test_cpu_load_idle"][target_name] = test_log
                cpu["Total Idle"][target_name] = round(float(total_idle), 2)
                cpu["Idle Percentage"][target_name] = round(float(idle_percen), 2)
        return cpu

    def _collect_data_of_boot_time(self, boot_time, tc, platforms):
        """Collect data of boot time on all target."""
        test_log = None
        target_name = self._get_target_name(tc)
        tc_log = tc.test_case.pytest_json_result["teardown"]
        for key in tc_log.keys():
            if key == "stdout":
                test_log = tc_log["stdout"]
        if "test_startup" in tc.test_name.split(".")[-1] and test_log is not None:
            device_up = re.search(
                r'"device_up":\s(?P<time>\d+\.\d{5})', test_log
            ).group("time")
            stdout_call_log = tc.test_case.pytest_json_result["call"]["stdout"]
            for target in platforms:
                if target == target_name:
                    self.summary_log["test_startup"][target_name] = stdout_call_log
                    boot_time["Device Up"][target_name] = round(float(device_up), 2)
        return boot_time

    def _collect_data_of_flash_time(self, flash_time, tc, platforms):
        """Collect data of flash time on all target."""
        test_log = None
        target_name = self._get_target_name(tc)
        target = tc.target_name.lower()
        if target != "wp76xx-onlycap":
            tc_log = tc.test_case.pytest_json_result["call"]
            for key in tc_log.keys():
                if key == "stdout":
                    test_log = tc_log["stdout"]
            if tc.test_name.split(".")[-1] == "L_ReinitTest" and test_log is not None:

                flash_time = self._get_flash_time(
                    tc, flash_time, test_log, target_name, platforms
                )
        return flash_time

    @staticmethod
    def _check_warning(log, target_name):
        """Check the status of Reinit test case."""
        if target_name == "RTOS":
            pattern = "Download Start"
        else:
            # ThreadX and Linux
            pattern = "INFO swiflash cmd"
        warnings = ["Device may be at some bad state", "Reboot failed"]
        start_log = log.rfind(pattern)
        end_log = log.rfind("Flash Finish") + len("Flash Finish")
        flash_log = log[start_log:end_log]
        for warning in warnings:
            if warning in flash_log:
                return False
        return True

    def _get_flash_time(self, tc, flash_time, test_log, target_name, platforms):
        """Get flash time from Reinit test case."""
        if self._check_warning(test_log, target_name) is False:
            return flash_time
        start_time = self.convert_time_to_seconds(
            self._collect_start_time(test_log, target_name)
        )
        end_time = self.convert_time_to_seconds(self._collect_end_time(test_log))
        flash_time_1 = self.convert_time_to_minutes(end_time - start_time)
        stdout_call_log = tc.test_case.pytest_json_result["call"]["stdout"]
        for target in platforms:
            if target == target_name:
                self.summary_log["L_ReinitTest"][target_name] = stdout_call_log
                flash_time["Flash Time"][target_name] = flash_time_1
        return flash_time

    @staticmethod
    def _collect_start_time(test_log, target_name):
        """Get start time of flash action on all target."""
        all_time = []
        if target_name == "RTOS":
            for line in test_log.split("\n"):
                start_time = re.search(
                    r"Download Start \("
                    r"\w{3} \w{3}\s+\d{1,2} "
                    r"(?P<time>\d{2}:\d{2}:\d{2})",
                    line,
                )
                if start_time:
                    start_time = start_time.group("time")
                    all_time.append(start_time)
        elif "Linux" in target_name or "ThreadX" in target_name:
            for line in test_log.split("\n"):
                start_time = re.search(
                    r"(?P<start_time>\d{2}:\d{2}:\d{2}) INFO swiflash cmd", line
                )
                if start_time:
                    start_time = start_time.group("start_time")
                    all_time.append(start_time)
        return all_time[-1]

    @staticmethod
    def _collect_end_time(test_log):
        """Get end time of flash action on all target."""
        end_time = re.search(
            r"Flash Finish: (\d{4}-\d{2}-\d{2} (?P<end_time>\d{2}:\d{2}:\d{2}))",
            test_log,
        ).group("end_time")
        return end_time

    @staticmethod
    def convert_time_to_minutes(time_str):
        """Convert seconds to minutes."""
        minutes = time_str // 60
        seconds = time_str % 60
        total = f"{minutes}:{seconds:02}"
        return total

    @staticmethod
    def convert_time_to_seconds(time_str):
        """Convert hours:minutes:seconds to seconds."""
        hours, minutes, seconds = map(int, time_str.split(":"))
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds

    def create_data_file(self, results_all, pre_data: dict):
        """Create today's data and reference data.

        Returns:
            The json data includes today's data and reference data.
        """
        today_data = self.get_today_data(results_all)
        if not pre_data:
            refer_data = copy.deepcopy(today_data)
        else:
            refer_data = self.get_refer_data(pre_data)
        data = {"Data": today_data, "Reference Data": refer_data}
        data = self.set_default_value(data)
        return data

    @staticmethod
    def set_default_value(data):
        """Set reference data to 'N/A' for targets that don't need comparison.

        Targets like 'Flash Time' and 'Total' do not require comparison
        with today's data.
        """
        targets = ["RTOS", "ThreadX", "Linux(WP76xx)", "Linux(WP77xx)"]
        for target in targets:
            data["Reference Data"]["Flash Time"]["Flash Time"][target] = "N/A"
            data["Reference Data"]["Memory"]["Total"][target] = "N/A"
        return data

    def get_today_data(self, results_all):
        """Get today's data of memory, cpu, boot and flash time on all target.

        Returns:
            Today's data json file.
        """
        memory = {}
        cpu = {}
        boot_time = {}
        flash_time = {}
        infor = ["Memory", "CPU", "Boot Time", "Flash Time"]
        platforms = ["RTOS", "ThreadX", "Linux(WP76xx)", "Linux(WP77xx)"]
        val = ["N/A"] * len(platforms)
        for data_name in self.key_memory:
            memory[data_name] = dict(zip(platforms, val))
        cpu["Total Idle"] = dict(zip(platforms, val))
        cpu["Idle Percentage"] = dict(zip(platforms, val))
        boot_time["Device Up"] = dict(zip(platforms, val))
        flash_time["Flash Time"] = dict(zip(platforms, val))
        for tcs in results_all:
            for tc in tcs:
                if (
                    tc.test_name.split(".")[-1] in self.mem_cpu_boottime_tcs_list
                    and tc.test_case is not None
                    and tc.result.lower() == "passed"
                    and tc.target_name != "em92xx"
                ):
                    memory = self._collect_data_of_memory(memory, tc, platforms)
                    cpu = self._collect_data_of_cpu(cpu, tc)
                    boot_time = self._collect_data_of_boot_time(
                        boot_time, tc, platforms
                    )
                    flash_time = self._collect_data_of_flash_time(
                        flash_time, tc, platforms
                    )
        today_data = dict(zip(infor, [memory, cpu, boot_time, flash_time]))
        return today_data

    def check_data(self, data: dict):
        """Check the status of today's data against reference data."""
        for infor, infor_value in data["Data"].items():
            for data_name, data_value in infor_value.items():
                if data_name in self.min_list:
                    data_1 = data["Reference Data"][infor][data_name]
                    data["Data"][infor][data_name] = self._check_min_data_status(
                        data_value, data_1, infor, data_name
                    )
                elif data_name in self.max_list:
                    data_2 = data["Reference Data"][infor][data_name]
                    data["Data"][infor][data_name] = self._check_max_data_status(
                        data_value, data_2, infor, data_name
                    )
                else:
                    for target, value in data_value.items():
                        data["Data"][infor][data_name][target] = [value, "None"]
        return data

    def _check_min_data_status(
        self, data_value, data_check, infor, data_name, percent_check=1.05
    ):
        """Check the status of today's data with min list of data.

        Status:
            "passed" if the value of today's data does not exceed '5%' of the
                reference value.
            "failed" if the value of today's data exceeds '5%' of the reference value.
            "None" if either value is N/A or both are N/A.
        """
        global THRESHOLD
        # If the data is boot time then the difference check percentage is 10%
        if data_name == "Device Up":
            percent_check = 1.1
        for target, value in data_value.items():
            if value == "N/A" or data_check[target] == "N/A":
                data_value[target] = [value, "None"]
            else:
                if value > percent_check * data_check[target]:
                    percent = (value - data_check[target]) * 100 / data_check[target]
                    percent = round(percent, 2)
                    THRESHOLD = "min"
                    jira_ticket = JiraServer().search_jira_ticket(
                        value,
                        data_check[target],
                        percent,
                        infor,
                        data_name,
                        target,
                        self.summary_log,
                    )
                    data_value[target] = [value, "failed", percent, jira_ticket]
                else:
                    data_value[target] = [value, "passed"]

        return data_value

    def _check_max_data_status(self, data_value, data_check, infor, data_name):
        """Check the status of today's data with max list of data.

        Status:
            "passed" if the value of today's data does not exceed '5%' of the
                reference value.
            "failed" if the value of today's data exceeds '5%' of the reference value.
            "None" if either value is N/A or both are N/A.
        """
        global THRESHOLD
        for target, value in data_value.items():
            if value == "N/A" or data_check[target] == "N/A":
                data_value[target] = [value, "None"]
            else:
                if value < 0.95 * data_check[target]:
                    percent = (data_check[target] - value) * 100 / data_check[target]
                    percent = round(percent, 2)
                    THRESHOLD = "max"
                    jira_ticket = JiraServer().search_jira_ticket(
                        value,
                        data_check[target],
                        percent,
                        infor,
                        data_name,
                        target,
                        self.summary_log,
                    )
                    data_value[target] = [value, "failed", percent, jira_ticket]
                else:
                    data_value[target] = [value, "passed"]

        return data_value

    def get_refer_data(self, data):
        """Get Reference Data of memory, cpu & boot time to compare.

        with today's data.
        """
        # Reference Data is returned from the memory_data.json file.
        # of the previous most recent date.
        refer_data = data["Reference Data"]
        for infor, infor_value in data["Reference Data"].items():
            for data_name, data_value in infor_value.items():
                if data_name in self.min_list:
                    data1 = data["Data"][infor][data_name]
                    refer_data[infor][data_name] = self._get_min_max_data(
                        data_value, data1
                    )
                elif data_name in self.max_list:
                    data2 = data["Data"][infor][data_name]
                    refer_data[infor][data_name] = self._get_min_max_data(
                        data_value, data2, check_min=False
                    )

        return refer_data

    @staticmethod
    def _get_min_max_data(data_value, compare_value, check_min=True):
        """Get the min/max value from today's data."""
        for target, value in data_value.items():
            if value != "N/A" and compare_value[target] != "N/A":
                if check_min:
                    data_value[target] = min(value, compare_value[target])
                else:
                    data_value[target] = max(value, compare_value[target])
            elif value == "N/A" and compare_value[target] == "N/A":
                data_value[target] = "N/A"
            else:
                data_value[target] = value if value != "N/A" else compare_value[target]

        return data_value

    @staticmethod
    def get_all_data(mem_data_json_path, all_data, sum_data):
        """Get all data from memory_data.json to generate report."""
        date = []
        i = 0
        platforms = ["RTOS", "ThreadX", "Linux(WP76xx)", "Linux(WP77xx)"]
        for path in mem_data_json_path:
            assert os.path.exists(path), "Could not find JSON file"
            date.append(path.split("_")[1].split(".", 1)[1].replace(".", "/"))
            with open(path, encoding="utf8") as f:
                sum_data[i] = json.load(f)
                # Create a temporary dictionary of flash time.
                if "Flash Time" not in sum_data[i]["Data"]:
                    sum_data[i]["Data"]["Flash Time"] = {
                        "Flash Time": {target: "N/A" for target in platforms}
                    }
                if "Flash Time" not in sum_data[i]["Reference Data"]:
                    sum_data[i]["Reference Data"]["Flash Time"] = {
                        "Flash Time": {target: "N/A" for target in platforms}
                    }
                all_data[date[i]] = sum_data[i]["Data"]
            i += 1

        return all_data, sum_data

    def run(self, args):
        """!Run the builder to generate report."""
        json_paths = [file_path for file_path in args.json_path
                      if os.path.splitext(file_path)[1][1:] == "json"]
        txt_paths = [file_path for file_path in args.json_path
                     if os.path.splitext(file_path)[1][1:] == "txt"]
        self._add_build_cfgs(json_paths)
        self._add_env_list_header()
        self._process_all_build_cfgs()
        self._add_env_global_list(args.global_env, args.global_env_path)
        self._add_results_headers()
        status = self._add_summary_section(txt_paths)
        results_all = self.gen_results_table()
        other_contents = {
            "title": args.title,
            "basic": args.basic,
            "section": args.html_section,
        }
        all_data = {}
        if args.output_format == "HTML":
            sum_data = {}
            if args.pre_mem_path:
                all_data, sum_data = self.get_all_data(
                    args.pre_mem_path, all_data=all_data, sum_data=sum_data
                )
            if args.output_mem_data:
                if len(all_data) > 0:
                    data = self.create_data_file(
                        results_all, list(sum_data.values())[-1]
                    )
                else:
                    data = self.create_data_file(results_all, sum_data)
                output = json.dumps(data, indent=2, separators=(",", ": "))
                with open(args.output_mem_data, "w", encoding="utf8") as f:
                    f.write(output)
                print(f"Generating memory data in {args.output_mem_data}")
                data_check = self.check_data(data=data)
                all_data.update(
                    {
                        "Reference Data": data_check["Reference Data"],
                        "Today": data_check["Data"],
                    }
                )
        output = self.generate_report(
            results_all, status, other_contents, data=all_data
        )
        if args.output:
            with open(args.output, "w", encoding="utf8") as f:
                f.write(output)
            print(f"Generating report in {args.output}")


class TestReportHTMLBuilder(TestReportBuilder):
    """!Test report HTML format builder."""

    def __init__(self):
        super().__init__()
        self.failure = None

    def get_failure(self):
        """Get failure reasons from Json file."""
        path = (
            "/storage/artifacts/legato-qa/nightly/"
            + f"nightly_{REPORT_DATE}_master/failureCauses.json"
        )
        if MERGE_REPORT and os.path.exists(path):
            with open(path, encoding="utf8") as f:
                failures = json.load(f)
                if failures:
                    for config in list(failures.keys()):
                        if self.summary[config]["NoRun"]["count"] == 0:
                            del failures[config]
                return failures
        else:
            return ""

    def generate_report(self, results_all, status, other_contents: dict, data=None):
        """!Generate report in HTML."""
        html_render = HTMLRender("report_template.html")
        results_failed = self.gen_results_table(lambda x: not x.is_passed())
        summary_headers = ["Config", "Status"]
        targets = ["RTOS", "ThreadX", "Linux(WP76xx)", "Linux(WP77xx)"]
        summary_headers.extend(TestSummary.stat_keys())
        if data is None or data == {}:
            len_data = None
            len_date = None
        else:
            len_data = {}
            len_date = len(data)
            for _, infor in data.items():
                for key, data_name in infor.items():
                    len_data[key] = len(data_name)
        self.failure = self.get_failure()
        html_render.contents = {
            "title": other_contents.get("title"),
            "basic": other_contents.get("basic"),
            "online_link": other_contents.get("online_link"),
            "section": other_contents.get("section"),
            "summary_headers": summary_headers,
            "summary": self.summary,
            "env_global_list": self.env_global_list,
            "target_components": self.target_components,
            "testing_env_infos": self.testing_env_infos,
            "environment_dict": self.environment_dict,
            "results_headers": self.results_headers,
            "results_failed": results_failed,
            "test_groups": self.groups,
            "group_len": self.group_len,
            "platform_info": self.platform,
            "group_summary": self.group_summary,
            "results_all": results_all,
            "test_data": self.global_test_data,
            "all_data": data,
            "len_data": len_data,
            "len_date": len_date,
            "targets": targets,
            "failure": self.failure,
            "extend_tcs": self.collected_test,
        }
        return html_render.render()

    def build(self, title, input_json_file, output_name):
        """!Build the html report."""
        self._add_build_cfgs(input_json_file)
        self._process_all_build_cfgs()
        self._add_results_headers()
        status = self._add_summary_section()
        self._add_env_list_header()
        results_all = self.gen_results_table()
        other_contents = {"title": title, "section": "all"}
        output = self.generate_report(results_all, status, other_contents)
        if output_name:
            with open(output_name, "w", encoding="utf8") as f:
                f.write(output)


class TestReportJSONBuilder(TestReportBuilder):
    """!Test report JSON format builder."""

    def __init__(self):
        super().__init__()
        self.content = None

    def generate_report(self, results_all, status, other_contents: dict, data=None):
        """!Generate report in JSON format."""
        print("Generating JSON")
        tests = []
        for row in results_all:
            tc1 = row[0]
            t = {"name": tc1.test_name}
            for cell in row:
                if isinstance(cell, TestCaseView):
                    if cell.test_case:
                        t[cell.target_name] = {"result": cell.result}
            tests.append(t)

        self.content = {
            "status": status,
            "env": {"common": self.env_global_list, "per_env": self.environment_dict},
            "stats": self.summary,
            "tests": tests,
        }
        output = json.dumps(self.content, indent=2, separators=(",", ": "))
        return output

    def upload(self, url):
        """!Upload the content to remote URL."""
        print(f"Publishing to {url}")
        self.content["@timestamp"] = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(self.content["@timestamp"])
        self.content["type"] = "report"
        r = requests.post(url, json=self.content)
        if r.status_code not in (200, 201):
            print(f"[{r.status_code}] Error while publishing to elasticsearch:")
            print(r.content)
            sys.exit(1)
        print("OK")

    @staticmethod
    def convert_list_to_json(list_tcs, json_file_path):
        """Convert test case list to json file."""
        json_data = []
        for test_name in list_tcs:
            temp = {"name": test_name}
            json_data.append(temp)
        with open(json_file_path, "w", encoding="utf8") as file:
            json.dump(json_data, file, indent=4)


class TestReportJSONParser:
    """Test report Json parser."""

    def __init__(self, json_path):
        assert os.path.exists(json_path), "Could not find JSON file"
        with open(json_path, encoding="utf8") as f:
            self.json_parser_data = json.load(f)

    def get_test(self, status="failed"):
        """Get test cases base on the returned status."""
        test_list = []
        print(f"========== List of {status} tests ==========")
        for index in range(len(self.json_parser_data["tests"])):
            if status == self.json_parser_data["tests"][index]["outcome"]:
                test = self.json_parser_data["tests"][index]["nodeid"]
                test_list.append(test)
                print(test)
        return test_list


class TestGroups:
    """Group of test cases."""

    def __init__(self, xmlfile, global_test_data, results_headers):
        """Parse group.xml."""
        tree = ET.parse(xmlfile)
        self.root = tree.getroot()
        self.groups = "test_groups"
        self.global_test_data = global_test_data
        self.results_headers = results_headers
        self.condition = {}
        self.test_groups = {}
        self.platform_info = {}
        self.group_summary = {}

    def _get_keyword(self, group_name):
        """Get keywords of group."""
        detail_path_in_xml = "/".join((self.groups, group_name, "testcase"))
        return self.root.findall(detail_path_in_xml)

    def _get_groups_condition(self):
        """Get conditions to create groups."""
        group_elements = self.root.find("test_groups")
        for element in group_elements:
            group_name = element.tag
            keywords = self._get_keyword(group_name)
            list_keyword = []
            for keyword in keywords:
                list_keyword.append(keyword.text)
            self.condition[group_name] = list_keyword
        return self.condition

    def gen_groups(self):
        """!Create groups of test cases."""
        colected_tcs = []
        min_len = 2

        for test_name, result in self.global_test_data.items():
            colected_tcs = self._group_condition(test_name, result, colected_tcs)

        temp_group = self._temp_group(colected_tcs)

        other_testcases = {}
        for group, test_cases in temp_group.items():
            if len(test_cases) >= min_len:
                self.test_groups[group] = test_cases
            else:
                other_testcases.update(test_cases)
        if len(other_testcases) > 0:
            self.test_groups["Other"] = other_testcases

        return self.test_groups

    def _group_condition(self, test_name, result, colected_tcs):
        """Create groups of test cases with conditions."""
        group_condition = self._get_groups_condition()
        is_colected = False

        for group, conditions in group_condition.items():
            for condition in conditions:
                if condition.lower() in test_name.lower():
                    if group not in self.test_groups:
                        self.test_groups[group] = {test_name: result}
                    else:
                        self.test_groups[group][test_name] = result
                    colected_tcs.append(test_name)
                    is_colected = True
                    break
            if is_colected:
                break
        return colected_tcs

    def _temp_group(self, colected_tcs):
        """Create temporary group of test cases by filename."""
        temp_group = {}

        for test_name, result in self.global_test_data.items():
            if test_name not in colected_tcs:
                group = test_name.split(".")
                if len(group) > 1:
                    group = group[-2]
                    group = group.replace("test_", "")
                    group = group.replace("le_", "")
                    group = group.title()

                if group not in temp_group:
                    temp_group[group] = {test_name: result}
                else:
                    temp_group[group][test_name] = result
        return temp_group

    def _summarize_group(self, group, result, group_status):
        """Summarize groups by status."""
        for sys_name, status in group_status[group].items():
            for test_case_view in result:
                pattern = sys_name + "$"
                if re.search(pattern, test_case_view.id):
                    test_case_view_result = test_case_view.result
                    if test_case_view_result in status.keys():
                        status[test_case_view_result] += 1
                    elif test_case_view_result == "xpassed":
                        status["passed"] += 1
                    if (
                        test_case_view_result != "N/A"
                        and sys_name not in group_status[group]["on_sys"]
                    ):
                        group_status[group]["on_sys"].append(sys_name)
        self.group_summary = group_status
        return self.group_summary

    def gen_result_platforms(self):
        """Get platform information."""
        platforms = {
            "Reinit": {},
            "Common_RTOS": {},
            "FreeRTOS": {},
            "ThreadX": {},
            "Linux": {},
            "Common_all_platforms": {},
        }
        temp = {}
        for group, status in self.group_summary.items():
            platforms = self._align_group(platforms, group, status)

        for platform, groups in platforms.items():
            self.platform_info[platform] = [{}, len(groups)]
            for group, test_cases in groups.items():
                self.platform_info[platform][0][group] = len(test_cases)
            temp.update(groups)
        self.test_groups = temp
        return self.platform_info

    def _align_group(self, platforms, group, status):
        """Align groups together by platform."""
        if group == "Reinit":
            platforms["Reinit"][group] = self.test_groups[group]
            return platforms
        if len(status["on_sys"]) == 2 and ("hl7812" and "rc76") in status["on_sys"]:
            platforms["Common_RTOS"][group] = self.test_groups[group]
        elif status["on_sys"] == ["hl7812"]:
            platforms["FreeRTOS"][group] = self.test_groups[group]
        elif status["on_sys"] == ["rc76"]:
            platforms["ThreadX"][group] = self.test_groups[group]
        elif ("hl7812" and "rc76") not in status["on_sys"]:
            platforms["Linux"][group] = self.test_groups[group]
        else:
            platforms["Common_all_platforms"][group] = self.test_groups[group]
        return platforms

    def gen_group_table(self, group_status, group):
        """Create status tables of groups."""
        status = ["passed", "failed", "xfailed", "error", "skipped"]
        group_status[group] = {}
        for sys_name in self.results_headers:
            if sys_name not in ("Testcases", "Jira ID"):
                group_status[group][sys_name] = {s: 0 for s in status}
        group_status[group]["on_sys"] = []
        return group_status


class JiraServer:
    """!Work with the JIRA server."""

    def __init__(self):
        self.jira_url = "https://issues.sierrawireless.com"
        self.jira_api_path = self.jira_url + "/rest/api/2"
        self.auth = HTTPBasicAuth(JIRA_USERNAME, JIRA_PASSWORD)

    def _add_watchers(self, ticket):
        """Add users to an issue's watcher list."""
        watchers = ["XLe", "TNguyenHuu", "NKha", "JNorthway", "HOu"]
        url = self.jira_api_path + f"/issue/{ticket}/watchers"
        for watcher in watchers:
            response = requests.post(url, auth=self.auth, json=watcher)
            if response.status_code == 204:
                print(f"Add watcher {watcher} to {ticket} successfully")
            else:
                print(f"{response.status_code} - {response.text}")

    def _create_jira_ticket(
        self, value, data_check, percent, infor, data_name, title, platform
    ):
        """Create a new ticket."""
        print(f"Start create a new ticket for the {data_name} issue.")
        date_obj = datetime.datetime.strptime(REPORT_DATE, "%Y.%m.%d")
        jira_ticket = ""
        url = self.jira_api_path + "/issue"
        # The default unit is kB, with a few exceptions:
        # Idle Percentage and Device Up
        exception_unit = {"Idle Percentage": "%", "Device Up": "s"}
        if data_name in exception_unit:
            data_check = str(data_check) + " " + exception_unit[data_name]
            value = str(value) + " " + exception_unit[data_name]
        else:
            data_check = str(data_check) + " kB"
            value = str(value) + " kB"
        description = (
            f"Nightly report {date_obj.strftime('%B %d, %Y')}: https://get.central/"
            + f"legato-qa/nightly/nightly_{REPORT_DATE}_master/test_report.html"
            + f"\n{title.replace('more than 5', str(percent))}"
            + f"\nReference value: {data_check}"
            + f"\nToday value: {value}"
        )

        data = {
            "fields": {
                "project": {"key": "LE"},
                "summary": f"[Nightly][{platform.split('(')[0]}][{infor}] {title}",
                "description": description,
                "issuetype": {"name": "Bug"},
                "versions": [{"name": "master"}],
                "customfield_11562": title,
                "customfield_11554": {"value": "1-Systematic(100%)"},
                "customfield_11010": {"value": "3-Moderate"},
                "customfield_11542": [
                    "nightly-master",
                    infor.replace(" ", "-"),
                    data_name.replace(" ", "-"),
                    platform.split("(")[0],
                ],
            }
        }
        response = requests.post(url, auth=self.auth, json=data)
        if response.status_code == 201:
            jira_ticket = response.json().get("key")
            print(
                "A ticket has just been created "
                + f"for the {data_name} issue: {jira_ticket}"
            )
            self._add_watchers(jira_ticket)
        else:
            print(f"Error creating issue: {response.status_code} - {response.text}")

        return jira_ticket

    def _add_comments(
        self, ticket, data_name, value, data_check, percent, title, file_name
    ):
        """Add comment to Jira ticket."""
        url = self.jira_api_path + f"/issue/{ticket}/comment"
        date_obj = datetime.datetime.strptime(REPORT_DATE, "%Y.%m.%d")
        exception_unit = {"Idle Percentage": "%", "Device Up": "s"}
        if data_name in exception_unit:
            data_check = str(data_check) + " " + exception_unit[data_name]
            value = str(value) + " " + exception_unit[data_name]
        else:
            data_check = str(data_check) + " kB"
            value = str(value) + " kB"
        comment = (
            f"This issue happened again on Nightly on "
            f"{date_obj.strftime('%B %d, %Y')}"
            + "\nNightly report : https://get.central/"
            + f"legato-qa/nightly/nightly_{REPORT_DATE}_master/test_report.html"
            + f"\n{title.replace('more than 5', str(percent))}"
            + f"\nReference value: {data_check}"
            + f"\nToday value: {value}"
        )
        if file_name:
            comment = comment + f"\nReference log: [^{file_name}]"
        data = {"body": comment}
        response = requests.post(url, auth=self.auth, json=data)
        if response.status_code == 201:
            print(f"Added a new comment to the ticket: {ticket}")
            json_cmt = response.json()
            print(f"Comment ID: {json_cmt['self']}")
        else:
            print(f"Error adding comment: {response.status_code} - {response.text}")

    @staticmethod
    def _get_attachments(data_name, platform, summary_log):
        """Get attachments from log of memory data."""
        refer_log = ""
        tc_name = ""
        data_in_tcs = {
            "test_cpu_load_idle": ["Total Idle", "Idle Percentage"],
            "test_memory_size": ["Legato Used"],
            "test_startup": ["Device Up"],
            "test_idle_atip": [
                "Base Heap",
                "Base Static",
                "Legato Heap",
                "Legato Static",
            ],
        }
        if data_name in ("Free", "Used"):
            if platform == "RTOS":
                refer_log = summary_log["test_idle_atip"][platform]
                tc_name = "test_idle_atip"
            else:
                refer_log = summary_log["test_idle_memory"][platform]
                tc_name = "test_idle_memory"
        for tc, value in data_in_tcs.items():
            if data_name in value:
                refer_log = summary_log[tc][platform]
                tc_name = tc
        file_name = f"{tc_name}_{data_name.replace(' ', '-')}_{REPORT_DATE}.log"
        with open(file_name, "w", encoding="utf8") as f:
            f.write(refer_log)
        print(f"Generating log file related to the issue {data_name} in {file_name}")

        return file_name

    def _add_attachments(self, ticket, data_name, platform, summary_log):
        """Add attachments to Jira tickets."""
        url = self.jira_api_path + f"/issue/{ticket}/attachments"
        headers = {"X-Atlassian-Token": "no-check"}
        file_name = self._get_attachments(data_name, platform, summary_log)

        if not os.path.exists(file_name):
            print("Attachment could not be found")
            return None

        with open(file_name, encoding="utf8") as file:
            files = {"file": file}
            response = requests.post(url, files=files, headers=headers, auth=self.auth)

        if response.status_code == 200:
            print(f"Successful attachment to ticket: {ticket}")
            return file_name
        else:
            print("File attachment failed. Status code:", response.status_code)
            print(response.text)
            return None

    def _search_comments(self, ticket, ticket_detail):
        """Check if there have been comments regarding the issue before.

        Returns:
            True: if there was a previous comment related to the issue
                or the ticket has just been created.
            False: if no comment has been added before.
        """
        url = self.jira_api_path + f"/issue/{ticket}/comment"
        date_obj = datetime.datetime.strptime(REPORT_DATE, "%Y.%m.%d")
        text = (
            "This issue happened again on Nightly on "
            + f"{date_obj.strftime('%B %d, %Y')}"
            + "\nNightly report : https://get.central/"
            + f"legato-qa/nightly/nightly_{REPORT_DATE}_master/test_report.html"
        )
        print(
            "Check comments before attaching log & add comments "
            + f"to avoid duplicates in the ticket: {ticket}"
        )
        response = requests.get(url, auth=self.auth)
        if response.status_code == 200:
            json_data = response.json()
            if int(json_data.get("total")) > 0:
                for i in range(int(json_data.get("total"))):
                    if text in json_data.get("comments")[i].get("body"):
                        comment_id = json_data.get("comments")[i].get("self")
                        print(
                            "There have been comments regarding the issue "
                            + f"reported in the ticket {ticket} before"
                        )
                        print(f"Comment ID: {comment_id}")
                        return True
            elif REPORT_DATE in ticket_detail.get("fields").get("description"):
                return True
        else:
            print(f"{response.status_code} - {response.text}")

        return False

    @staticmethod
    def _get_params(data_name, infor, platform):
        """Get parameters and title to search Jira tickets."""
        if THRESHOLD == "min":
            title = f"{data_name} increased by more than 5%"
        elif THRESHOLD == "max":
            title = f"{data_name} reduced by more than 5%"
        params = {
            "jql": (
                f'summary ~ "{title}" AND Keywords  = nightly-master '
                + f'AND Keywords = {infor.replace(" ","-")} '
                + f'AND Keywords = {data_name.replace(" ","-")} '
                + f'AND Keywords = {platform.split("(")[0]} '
                + "AND status not in (Closed, Resolved)"
                + " ORDER BY createdDate ASC"
            )
        }

        return params, title

    def search_jira_ticket(
        self, value, data_check, percent, infor, data_name, platform, summary_log
    ):
        """Check if the problem has been generated ticket before.

        Create a new ticket if you haven't found one yet
        """
        jira_ticket = ""

        if JIRA_SERVER:
            print(f"Check if the problem with {data_name} has been generated before")
            params, title = self._get_params(data_name, infor, platform)
            response = requests.get(
                f"{self.jira_api_path}/search", params=params, auth=self.auth
            )
            if response.status_code == 200:
                json_data = response.json()
                # Check the number of jira tickets 'json_data.get("total")'
                if int(json_data.get("total")) > 0:
                    ticket_list = [
                        json_data.get("issues")[i].get("key")
                        for i in range(int(json_data.get("total")))
                    ]
                    print(
                        f"Tickets have been created for the {data_name} issue: "
                        + ", ".join(map(str, ticket_list))
                    )
                    jira_ticket = ticket_list[0]
                    if not self._search_comments(
                        jira_ticket, json_data.get("issues")[0]
                    ):
                        file_name = self._add_attachments(
                            jira_ticket, data_name, platform, summary_log
                        )
                        self._add_comments(
                            jira_ticket,
                            data_name,
                            value,
                            data_check,
                            percent,
                            title,
                            file_name,
                        )
                else:
                    print("No tickets have been generated before")
                    jira_ticket = self._create_jira_ticket(
                        value, data_check, percent, infor, data_name, title, platform
                    )
            else:
                print(f"{response.status_code} - {response.text}")

        return jira_ticket

    def get_ticket_status(self, ticket):
        """Get Jira ticket status."""
        url = self.jira_api_path + f"/issue/{ticket}"

        response = requests.get(url, auth=self.auth)
        if response.status_code == 200:
            json_data = response.json()
            status = json_data.get("fields").get("status").get("name")
            return status
        else:
            print(f"{response.status_code} - {response.text}")
            return None

    def check_jira_ticket(self, xfailed_mes):
        """Check if the ticket is still valid.

        Returns "True" if ticket status is different from "resolved" and
        "closed".
        """
        is_valid = True
        jira_status = None
        xfailed_reg = re.search(r"XFailed:\s(?P<xfailed_ticket>.*)", xfailed_mes)
        if xfailed_reg:
            xfailed_ticket = xfailed_reg.group("xfailed_ticket")
            jira_status = self.get_ticket_status(xfailed_ticket)
            if jira_status:
                if jira_status.lower() in ("resolved", "closed"):
                    is_valid = False
            else:
                print(f"Cannot get the status of the ticket {xfailed_ticket}")
        return is_valid


def parse_args():
    """!Parse all arguments for test_report."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-path",
        action="append",
        required=True,
        help="Path to build_configuration.json files",
    )
    parser.add_argument(
        "--pre-mem-path", action="append", help="Path to memory_data.json files"
    )
    parser.add_argument("--jira-user", help="Account to get the status of Jira ticket")
    parser.add_argument("--jira-password", help="Jira account password")
    parser.add_argument(
        "--html-section",
        action="store",
        default="all",
        help="""
        Included section(s) in the final html report.\n
        Supported sections (All, Summary).\n""",
    )
    parser.add_argument(
        "--global-env",
        nargs="*",
        help="List of key=value to list in the global environment section",
    )
    parser.add_argument(
        "--global-env-path", help="Path to a global environment JSON file"
    )
    parser.add_argument(
        "--title", default="Test Report", help="Path to build_configuration.json files"
    )
    parser.add_argument("--output", default="test_report.html", help="Output file path")
    parser.add_argument("--output-mem-data", help="Output file path")
    parser.add_argument(
        "--output-format", default="HTML", help="Output format (HTML, JSON)"
    )
    parser.add_argument(
        "--elasticsearch-url", help="Elasticsearch URL to publish JSON data"
    )
    parser.add_argument("--elasticsearch-username", help="Username for Elasticsearch")
    parser.add_argument("--elasticsearch-password", help="Password for Elasticsearch")
    parser.add_argument(
        "--basic",
        action="store_true",
        help="Generate a basic version of the HTML report (for email)",
    )
    parser.add_argument("--online-link", help="URL to the online report")
    parser.add_argument(
        "--get-tc",
        action="append",
        dest="status",
        help="""
        Dump the list of based on the value of the status to a json file.\n
        Usage: --get-tc <status>; \n
        status can be "failed", "passed", "error", "xfailed", "skipped" \n""",
    )
    parser.add_argument("--report-groups", help="Path to group config")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    # Enable merge report for nightly master
    for path in args.json_path:
        rsp = re.search(r"nightly_(?P<date>\d+\.\d+\.\d+)_master", path)
        if rsp:
            REPORT_DATE = rsp.group("date")
            print("Enable merge report.")
            MERGE_REPORT = True
            break
    if args.basic:
        JIRA_SERVER = False

    JIRA_USERNAME = args.jira_user
    JIRA_PASSWORD = args.jira_password
    GROUP_CONFIG_PATH = args.report_groups

    if args.status:
        test_list = []
        for status in args.status:
            test_list.extend(
                TestReportJSONParser(args.json_path[0]).get_test(status=status)
            )
        if re.search(".json", args.output):
            TestReportJSONBuilder().convert_list_to_json(test_list, args.output)
    else:
        if args.output_format == "HTML":
            TestReportHTMLBuilder().run(args)
        elif args.output_format == "JSON":
            test_report_builder = TestReportJSONBuilder()
            test_report_builder.run(args)
            if args.elasticsearch_url:
                test_report_builder.upload(args.elasticsearch_url)
        else:
            print(f"Unknown format {args.output_format}")
            sys.exit(1)
