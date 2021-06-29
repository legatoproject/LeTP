#!/usr/bin/env python3
"""!@package test_report Generate the final HTML test report.

Test Report is based on build configuration json results.
"""
import datetime
import json
import os
import sys
import re
import argparse
from collections import OrderedDict
import requests
from build_configuration import PytestResult, Components, Environment
from report_template import HTMLRender

__copyright__ = "Copyright (C) Sierra Wireless Inc."

ALL_COMPONENTS = [x.name for x in Components]
ALL_ENVIRONMENT_TYPES = list(Environment)


# pylint: disable=too-many-instance-attributes
class TestSummary:
    """!Test summary section in the table."""

    @classmethod
    def stat_keys(cls):
        """Summary stats keys."""
        return [
            "CollectedTests",
            "TestcasesRun",
            "Passed",
            "Skipped",
            "Failures",
            "Errors",
        ]

    def __init__(self, cfg="global", collected=0, tcs=0, failures=0, errors=0):
        self.cfg = cfg
        self.__status = None
        self.collected_tests_num = collected
        self.stat_tcs = tcs
        self.stat_passed = 0
        self.stat_skipped = 0
        self.stat_failures = failures
        self.stat_errors = errors
        self.sub_summary = {}

    def add_summary(self, name, summary):
        """Add summary for all tests.."""
        self.sub_summary[name] = summary

    def total_collected(self):
        """Total collected cases."""
        if self.cfg == "global":
            return self.collected_tests_num + sum(
                [s.total_collected() for s in self.sub_summary.values()]
            )
        else:
            if self.collected_tests_num != 0:
                return self.collected_tests_num
            return self.total_tcs()

    def total_tcs(self):
        """Get total test cases."""
        return self.stat_tcs + sum([s.total_tcs() for s in self.sub_summary.values()])

    def total_passed(self):
        """Get passed test cases."""
        return self.stat_passed + sum(
            [s.total_passed() for s in self.sub_summary.values()]
        )

    def total_skipped(self):
        """Get skipped test cases."""
        return self.stat_skipped + sum(
            [s.total_skipped() for s in self.sub_summary.values()]
        )

    def total_failures(self):
        """Get total failed test cases."""
        return self.stat_failures + sum(
            [s.total_failures() for s in self.sub_summary.values()]
        )

    def total_errors(self):
        """Get total test cases in error state."""
        return self.stat_errors + sum(
            [s.total_errors() for s in self.sub_summary.values()]
        )

    def stats(self):
        """Get Statistics of tests results."""
        # Don't include skipped tests in percentage calculation
        divider = float(self.total_tcs()) / 100
        if divider == 0:
            divider = 1

        return {
            "CollectedTests": {"count": self.total_collected(), "percentage": 100},
            "TestcasesRun": {
                "count": self.total_tcs(),
                "percentage": self.total_tcs() / divider,
            },
            "Passed": {
                "count": self.total_passed(),
                "percentage": self.total_passed() / divider,
            },
            "Skipped": {
                "count": self.total_skipped(),
                "percentage": self.total_skipped() / divider,
            },
            "Failures": {
                "count": self.total_failures(),
                "percentage": self.total_failures() / divider,
            },
            "Errors": {
                "count": self.total_errors(),
                "percentage": self.total_errors() / divider,
            },
        }

    def set_status(self, status):
        """Set the status of the whole test suite."""
        self.__status = status

    def status(self):
        """Get the status of the whole test suite."""
        if self.__status:
            return self.__status

        if self.total_errors() != 0 or self.total_failures() != 0:
            return "FAILED"

        if self.total_collected() and not self.total_passed():
            # collected but not run.
            return "RUNNING"

        for s in self.sub_summary:
            print(
                "Processed test report for %s: %s" % (s, self.sub_summary[s].status())
            )
            if self.sub_summary[s].status() != "PASSED":
                return self.sub_summary[s].status()

        return "PASSED"


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
        call_phase = self.pytest_json_result.get("call")
        crash_reason = call_phase.get("crash")
        if crash_reason:
            # non-passing testcases
            return crash_reason.get("message", "N/A")
        return ""

    @property
    def system_out(self):
        """System out from all xml elements.."""
        return self._system_out

    @system_out.setter
    def system_out(self, logs):
        """Set system out."""
        self._system_out = "{}\n{}".format(self._system_out, logs)

    @property
    def system_err(self):
        """System err from all xml elements."""
        return self._system_err

    @system_err.setter
    def system_err(self, logs):
        """Set system err."""
        self._system_err = "{}\n{}".format(self._system_err, logs)

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

    def get_create_target_result(self, target_name):
        """Get and create test result for the target."""
        if target_name not in self.results:
            self.results[target_name] = TestCaseResult()
        return self.results[target_name]


class TestCaseView:
    """!Test case view for ninja template."""

    def __init__(self, test_name, target_name, test_case: TestCaseResult):
        self.test_name = test_name
        self.target_name = target_name
        if test_case:
            assert isinstance(test_case, TestCaseResult)
        self.test_case = test_case

    @property
    def id(self):
        """Test case identifier/the path."""
        id_str = self.test_name + "_" + self.target_name
        id_str = id_str.replace(".", "_")
        id_str = id_str.replace(":", "_")
        return id_str

    @property
    def result(self):
        """Test result.

        If there is no test on the system, return N/A.
        """
        if not self.test_case:
            return "N/A"

        return self.test_case.pytest_json_result.get("outcome", "N/A")

    @property
    def html_class(self):
        """For Ninja usage."""
        return self.test_case.pytest_json_result.get("outcome", "N/A").lower()


class BuildConfiguration:
    """!Describes a specific build/test configuration."""

    def __init__(self, json_file, name=None):
        with open(json_file) as f:
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
                consolidate_val = "{}:{}".format(name, version)
                env_val = (
                    consolidate_val
                    if not env_val
                    else "{}, {}".format(env_val, consolidate_val)
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
        if test_name not in self.pytest_test_name_array:
            return {}
        idx = self.pytest_test_name_array.index(test_name)
        return self.pytest_results[idx]

    @staticmethod
    def _build_element_name(elmt, prefix):
        """!Build element name with prefix."""
        if elmt.classname:
            basename = "%s.%s" % (elmt.classname, elmt.name)
        else:
            basename = elmt.name
        elmt_name = "%s%s" % (prefix, basename)
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
                pytest_result.update(self.pytest_results[i])
                test_result.update_pytest_logs(pytest_result, update_before_log=True)
                test_result.pytest_json_result.update(pytest_result)
        return res

    def _iter_pytest_report(self, global_test_data, summary):
        """Iterate the test report and collect summary."""
        tests = self.json_data.get("tests", [])
        res = []
        verify_duplicate_tcs = {}
        for elmt in tests:
            test_name = PytestResult(elmt).get_test_name()
            pytest_result = self._lookup_pytest_json_result(test_name)

            if not pytest_result:
                print("Unable to get the test result for {}".format(pytest_result))
                continue

            global_test_case = self._get_create_global_test_case(
                global_test_data, test_name
            )
            test_result = global_test_case.get_create_target_result(self.name)

            if test_name not in verify_duplicate_tcs:
                test_result.add_pytest_json_result(pytest_result)
            else:
                res = self._update_result_of_duplicate_tcs(pytest_result, test_result)

            verify_duplicate_tcs[test_name] = pytest_result.get("outcome")
            self._add_pytest_test_logs(global_test_data, pytest_result)

        summary.collected_tests_num -= len(res)
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
        collected_tests_num = self._get_json("test_collected")
        if collected_tests_num is None:
            collected_tests_num = 0

        new_summary = TestSummary(self.name, collected=collected_tests_num)
        if "state" in self.json_data:
            new_summary.set_status(self.json_data["state"])

        self._iter_pytest_report(global_test_data, new_summary)

        return new_summary


class TestReportBuilder:
    """!Building test report."""

    def __init__(self):
        self.build_cfg_list = []  # List of build configurations
        self.build_number_dict = {}  # build_id: BuildConfiguration instance
        self.build_names = []  # Build cfgs may have the same name.
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

    def set_unique_name(self, build_cfg):
        """!Set build configure name as the build configuration ID.

        One target may have multiple test runs in different env. We use
        build_idx to build the name that it's unique in test report.
        """
        if build_cfg.name in self.build_names:
            build_cfg.name = "{}-{}".format(build_cfg.name, self.build_idx)
            self.build_idx += 1
        self.build_names.append(build_cfg.name)

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
            print("Too many '=' signs in %s" % entry)
            sys.exit(1)
        if os.path.exists(entry_path) is False:
            print("Could not find JSON file for %s" % (entry_path))
            sys.exit(1)
        return entry_name, entry_path

    def _add_build_cfgs(self, json_path):
        for entry in json_path:
            entry_name, entry_path = self._get_entry_path(entry)
            build_cfg = BuildConfiguration(entry_path, entry_name)
            print("[%s] %s %s" % (entry_name, entry_path, build_cfg))
            self.set_unique_name(build_cfg)
            registered_cfg = self.register_new_build_configuration(build_cfg)
            if registered_cfg == build_cfg:
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
            new_summary = build_cfg.process_test_data(self.global_test_data)
            self.test_summary.add_summary(build_cfg.name, new_summary)

    def _add_env_global_list(self, global_env, global_env_path):
        # From args
        if global_env:
            for e in global_env:
                kv = e.split("=")
                if len(kv) < 2:
                    raise Exception("Invalid key value '%s', format should be k=v" % e)

                k = kv.pop(0)
                v = "=".join(kv)
                self.env_global_list[k] = {"text": v}
        # From file
        if global_env_path:
            with open(global_env_path) as f:
                j = json.load(f)
                self.env_global_list.update(j)

    def _add_summary_section(self):
        summary_global = {"Config": self.test_summary.cfg}
        summary_global["Status"] = self.test_summary.status()
        summary_global.update(self.test_summary.stats())
        self.summary[self.test_summary.cfg] = summary_global

        for k in sorted(self.test_summary.sub_summary.keys()):
            sub_s = self.test_summary.sub_summary[k]
            s = {"Config": sub_s.cfg}
            s["Status"] = sub_s.status()
            s.update(sub_s.stats())
            self.summary[sub_s.cfg] = s

        status = self.test_summary.status()
        return status

    def gen_results_table(self, filter_fn=None):
        """!Get results table with filtering."""
        results = []

        for test_name, global_test_case in self.global_test_data.items():

            if filter_fn:
                if not filter_fn(global_test_case):
                    continue

            c_res = []
            all_targets = self.results_headers[1:]
            for target_name in all_targets:
                if target_name in global_test_case.results:
                    test_case = global_test_case.results[target_name]
                else:
                    test_case = None
                test_case_view = TestCaseView(test_name, target_name, test_case)
                c_res.append(test_case_view)

            results.append(c_res)
        return results

    def generate_report(self, results_all, status, other_contents: dict):
        """!Generate the test report."""
        raise NotImplementedError

    def _add_results_headers(self):
        """Add the result header.

        e.g.Testcases | HL7800 | WP76.
        """
        results_headers = ["Testcases"]
        build_cfg_names = [c.name for c in self.build_cfg_list]
        results_headers.extend(build_cfg_names)
        self.results_headers = results_headers

    def run(self, args):
        """!Run the builder to generate report."""
        self._add_build_cfgs(args.json_path)
        self._add_env_list_header()
        self._process_all_build_cfgs()
        self._add_env_global_list(args.global_env, args.global_env_path)
        self._add_results_headers()
        status = self._add_summary_section()
        results_all = self.gen_results_table()
        other_contents = {
            "title": args.title,
            "basic": args.basic,
            "section": args.html_section,
        }
        output = self.generate_report(results_all, status, other_contents)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print("Generating report in {}".format(args.output))


class TestReportHTMLBuilder(TestReportBuilder):
    """!Test report HTML format builder."""

    def generate_report(self, results_all, status, other_contents: dict):
        """!Generate report in HTML."""
        html_render = HTMLRender("report_template.html")
        results_failed = self.gen_results_table(lambda x: not x.is_passed())
        summary_headers = ["Config", "Status"]
        summary_headers.extend(TestSummary.stat_keys())

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
            "results_all": results_all,
            "test_data": self.global_test_data,
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
            with open(output_name, "w") as f:
                f.write(output)


class TestReportJSONBuilder(TestReportBuilder):
    """!Test report JSON format builder."""

    def __init__(self):
        super(TestReportJSONBuilder, self).__init__()
        self.content = None

    def generate_report(self, results_all, status, other_contents: dict):
        """!Generate report in JSON format."""
        print("Generating JSON")
        tests = []
        for row in results_all:
            tc1 = row[0]
            t = {"name": tc1.target_name}
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
        print("Publishing to %s" % url)
        self.content["@timestamp"] = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(self.content["@timestamp"])
        self.content["type"] = "report"
        r = requests.post(url, json=self.content)
        if r.status_code != 200 and r.status_code != 201:
            print("[%s] Error while publishing to elasticsearch:" % r.status_code)
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
        with open(json_file_path, "w") as file:
            json.dump(json_data, file, indent=4)


class TestReportJSONParser:
    """Test report Json parser."""

    def __init__(self, json_path):
        assert os.path.exists(json_path), "Could not find JSON file"
        with open(json_path) as f:
            self.json_parser_data = json.load(f)

    def get_test(self, status="failed"):
        """Get test cases base on the returned status."""
        test_list = []
        print("========== List of {} tests ==========".format(status))
        for index in range(len(self.json_parser_data["tests"])):
            if status in self.json_parser_data["tests"][index]["outcome"]:
                test = self.json_parser_data["tests"][index]["nodeid"]
                test_list.append(test)
                print(test)
        return test_list


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
        "--title",
        default="Legato-QA-NightlyTest Results",
        help="Path to build_configuration.json files",
    )
    parser.add_argument("--output", default="test_report.html", help="Output file path")
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
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
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
            print("Unknown format %s" % args.output_format)
            sys.exit(1)
