#!/usr/bin/env python3
"""!@package differential_report Generate the differential test report.

The differential test report to compare current results with previous
results.
"""
import json
import os
import argparse
from report_template import HTMLRender

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class LegatoQaJSONParser:
    """Test report Json parser."""

    def __init__(self, result_data, pre_result_data):
        self.result_data = result_data
        self.pre_result_data = pre_result_data
        self.target_list = self.get_target()

    def get_target(self):
        """Get all the targets in the report."""
        target_list = list(self.result_data["stats"].keys())
        target_list.remove("global")
        print(target_list)
        return target_list

    def get_test(self, status):
        """Get test cases with new status."""
        test_list = {}
        print(f"========== List of New {status} tests ==========")
        for index in range(len(self.result_data["tests"])):
            test = self.result_data["tests"][index]["name"]
            data = self.check_result(status, index, test)
            if status in data:
                test_list[test] = data
        print(test_list)
        return test_list

    def check_result(self, status, index, test):
        """Check if state of test case is new."""
        data = []
        for target in self.target_list:
            if target in self.result_data["tests"][index]:
                result = self.result_data["tests"][index][target]["result"]
                if status == result:
                    check_result = self.check_target_result(test, target, result)
                    data.append(check_result)
                else:
                    data.append("N/A")
            else:
                data.append("N/A")
        return data

    def check_target_result(self, test, target, result):
        """Check if the state of the test case on the target is new."""
        for index in range(len(self.pre_result_data["tests"])):
            if self.pre_result_data["tests"][index]["name"] == test:
                if target in self.pre_result_data["tests"][index]:
                    pre_result = self.pre_result_data["tests"][index][target]["result"]
                    return "N/A" if pre_result == result else result
                else:
                    return f"new-{result}"
        return f"new-{result}"

    def get_miss_tests(self):
        """Get missing test cases.

        The missing test case is the one present in the previous result
        but not in the current result.
        """
        miss_tests = {}
        for index in range(len(self.pre_result_data["tests"])):
            test = self.pre_result_data["tests"][index]["name"]
            run_target = list(self.pre_result_data["tests"][index])
            run_target.remove("name")
            miss_on_target = []
            for target in self.target_list:
                status = "N/A"
                if target in run_target:
                    check_miss = self.check_miss(test, target)
                    if check_miss:
                        status = "miss"
                miss_on_target.append(status)
            if "miss" in miss_on_target:
                miss_tests[test] = miss_on_target
        return miss_tests

    def check_miss(self, test, target):
        """Check if state of test case is missing."""
        for index in range(len(self.result_data["tests"])):
            if self.result_data["tests"][index]["name"] == test:
                return target not in self.result_data["tests"][index]
        return True


class CPJSONParser:
    """Test report Json parser."""

    def __init__(self, result_data, pre_result_data):
        self.result_data = result_data
        self.pre_result_data = pre_result_data

    def get_target(self):
        """Get the target in the report."""
        target = [self.result_data["target_name"]]
        print(target)
        return target

    def get_test(self, status):
        """Get test cases with new status."""
        test_list = {}
        print(f"========== List of New_{status} tests ==========")
        for index in range(len(self.result_data["tests"])):
            test = self.result_data["tests"][index]["nodeid"]
            result = self.result_data["tests"][index]["outcome"]
            if status == result:
                check_result = self.check_result(test, result)
                if check_result:
                    test_list[test] = [result]
        print(test_list)
        return test_list

    def check_result(self, test, result):
        """Check if state of test case is new."""
        for index in range(len(self.pre_result_data["tests"])):
            if self.pre_result_data["tests"][index]["nodeid"] == test:
                pre_result = self.pre_result_data["tests"][index]["outcome"]
                return pre_result != result
        return True

    def get_miss_tests(self):
        """Get missing test cases.

        The missing test case is the one present in the previous result
        but not in the current result.
        """
        miss_tests = {}
        for index in range(len(self.pre_result_data["tests"])):
            test = self.pre_result_data["tests"][index]["nodeid"]
            miss_on_target = []
            status = "N/A"
            check_miss = self.check_miss(test)
            if check_miss:
                status = "miss"
            miss_on_target.append(status)
            if "miss" in miss_on_target:
                miss_tests[test] = miss_on_target
        return miss_tests

    def check_miss(self, test):
        """Check if state of test case is missing."""
        for index in range(len(self.result_data["tests"])):
            if self.result_data["tests"][index]["nodeid"] == test:
                return False
        return True


def parse_args():
    """!Parse all arguments for test_report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-path", required=True, help="Path to result files")
    parser.add_argument(
        "--pre-result-path", required=True, help="Path to previous result files"
    )
    parser.add_argument(
        "--output", default="differential_report.html", help="Output file path"
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    assert os.path.exists(
        args.result_path
    ), f"{args.result_path}: Could not find JSON file"
    assert os.path.exists(
        args.pre_result_path
    ), f"{args.pre_result_path}: Could not find JSON file"

    with open(args.result_path, encoding="utf8") as f:
        result_data = json.load(f)
    with open(args.pre_result_path, encoding="utf8") as f:
        pre_result_data = json.load(f)

    status_list = ["failed", "error", "skipped", "xfailed", "passed"]
    TestSummary = {}
    Differential_result = {}
    status_len = {}
    if "target_name" in result_data.keys():
        JsonParser = CPJSONParser(result_data, pre_result_data)
    elif "stats" in result_data.keys():
        JsonParser = LegatoQaJSONParser(result_data, pre_result_data)
    target_list = JsonParser.get_target()
    for status in status_list:
        test = JsonParser.get_test(status)
        if test:
            TestSummary[status] = test

    # Get missing test cases
    miss_tests = JsonParser.get_miss_tests()
    TestSummary["Miss Tests"] = miss_tests

    for status, tests in TestSummary.items():
        status_len[status] = len(tests)
    print("========== Summary of new status ==========")
    print(status_len)

    html_render = HTMLRender("differential_report_template.html")
    html_render.contents = {
        "data": TestSummary,
        "target_list": target_list,
        "status_len": status_len,
    }
    output = html_render.diff()
    if args.output:
        with open(args.output, "w", encoding="utf8") as f:
            f.write(output)
        print(f"Generating report in {args.output}")
