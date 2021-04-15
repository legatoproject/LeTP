#!/usr/bin/env python3
"""Build a test running result report in json format.

We may run several test campaigns in the same environment.

The package here is to build a configuration json report.
Input:
junit.xml test results.
CI environment infos:
e.g.
- Test campaign name
- Testbed.id;
- test binaries info.

Output:
A json file contains the above environment and junit test results.
"""
import enum
import re
import argparse
import json
import os
import sys

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class Components(enum.Enum):
    """!Components of the system."""

    legato = enum.auto()
    legato_built = enum.auto()
    linux = enum.auto()
    modem = enum.auto()


class Environment(enum.Enum):
    """!Metadata of testing environment."""

    Plugins = enum.auto()
    Packages = enum.auto()


class PytestResult(dict):
    """!Pytest result genereate from pytest_jsonreport."""

    @staticmethod
    def build_test_id(test_path):
        """Build test id from test path.

        Make 'scenario/command/test.py::test_json_report_stub'
        into scenario.command.test.test_json_report_stub

        Key: classname and name.
        """
        python_file_patten = r"(?P<file_name>.+\.py)"
        match = re.search(python_file_patten, test_path)

        if match:
            python_file = os.path.basename(match.group("file_name"))
            test_path = test_path.replace(python_file, python_file.replace(".py", ""))
            module_name, test_name = test_path.split("::")
            module_name = module_name.replace("/", ".")
            return "{}.{}".format(module_name, test_name)
        return ""

    def get_test_name(self):
        """Align test id with junitparser.TestCase."""
        test_path = self.get("nodeid")
        return self.build_test_id(test_path)


class JsonBuilder:
    """To build build configuration json file from the arguments."""

    def __init__(self):
        self._data = {}

    @staticmethod
    def _parse_args_with_colon(entry):
        """Parse the entry with : as the separator.

        Entry sample:
        linux:'Ubuntu 16.04.6 LTS'
        legato:'18.09.5.ALT1250.rc3 2020/05/29 19:39:14'
        """
        assert ":" in entry, "Need to provide : as separator"
        separate_idx = entry.find(":")
        key = entry[:separate_idx]
        value_start_idx = separate_idx + 1
        value = entry[value_start_idx:]
        return key, value

    @staticmethod
    def _parse_args_with_equal(entry):
        """Parse the entry with = as the separator.

        Entry sample:
        tb.id=carmd-020
        """
        assert "=" in entry, "Need to provide = as separator"
        separate_idx = entry.find("=")
        key = entry[:separate_idx]
        value_start_idx = separate_idx + 1
        value = entry[value_start_idx:]
        return key, value

    def get_dict(self):
        """Get JSON dictionary."""
        return self._data

    def _add_target_name(self, target_name):
        # target_name used to differentiate between different json files
        # for different targets, eg wp76xx vs wp76xx_onlycap.
        self._data["target_name"] = target_name

    def _add_test_campaign(self, test_campaign):
        self._data["test_campaign"] = test_campaign

    def _add_info_entries(self, info_args):
        # info uses key=value format, while all others use key:value
        if info_args is None:
            return
        self._data["info"] = {}
        for entry in args.info:
            info_key, info_value = self._parse_args_with_equal(entry)
            self._data["info"][info_key] = info_value

    def _add_component_entries(self, components: list):
        if components is None:
            return
        self._data["components"] = {}
        for entry in components:
            component_name, component_version = self._parse_args_with_colon(entry)
            self._data["components"][component_name] = component_version

    def _add_state(self, state):
        if state is None:
            return
        valid_states = ["PASSED", "FAILED", "ERROR"]
        if state not in valid_states:
            print("Invalid state, should be either %s" % " or ".join(valid_states))
            sys.exit(1)
        self._data["state"] = state

    def _finalize(self, file_name):
        with open(file_name, "w") as outfile:
            json.dump(self._data, outfile, indent=4)

    def run(self, args):
        """Run the builder for json file.

        Add data sequentially from arguments.
        """
        self._add_target_name(args.target_name)
        self._add_test_campaign(args.test_campaign)
        self._add_info_entries(args.info)
        self._add_component_entries(args.components)
        self._add_state(args.state)
        self._finalize(args.output)


class JsonExtender(JsonBuilder):
    """Extend json file with test results."""

    def __init__(self, base_json_file):
        super(JsonExtender, self).__init__()
        self._base_json_file = base_json_file
        with open(self._base_json_file, "r") as base_f:
            self._data = json.load(base_f)

    def _add_info_entries_from_config(self, test_config):
        """Add info entries from test config.

        e.g. --config test_run/context(jenkins.job)=Legato-QA-TestEngine
        """
        context_config = test_config.get_context_configs()
        if "info" in self._data and self._data["info"]:
            self._data["info"].update(context_config)
        else:
            self._data["info"] = context_config

    def extend(self, test_results: list, test_config):
        """Extend the base json file with test results."""
        if not (self._base_json_file and os.path.exists(self._base_json_file)):
            return

        assert isinstance(test_results, list)
        target_name = test_config.get_target_name()
        self._add_target_name(target_name)
        test_compaign = test_config.get_test_campaign()
        self._add_test_campaign(test_compaign)
        self._add_info_entries_from_config(test_config)
        test_components = test_config.get_test_components()
        self._add_component_entries(test_components)
        self._finalize(self._base_json_file)


def parse_args():
    """Parse all arguments."""
    parser = argparse.ArgumentParser()
    # components can be provided by init_versions.xml as well.
    parser.add_argument(
        "--components",
        nargs="*",
        help="Tested software Components. FORMAT - Component name: Component Version."
        "e.g. linux:'Ubuntu 16.04.6 LTS' ",
    )
    parser.add_argument(
        "--test-results",
        nargs="+",
        help="junit xml file(s). FORMAT - test result type: test result file."
        "e.g. letp-qa:test_results_letp.qa.xml",
    )
    parser.add_argument(
        "--test-campaign", required=True, help="Test Campaign that was run"
    )
    parser.add_argument("--target-name", required=True, help="Name of the target")
    parser.add_argument("--state", help="State of the test (PASSED, FAILED)")
    parser.add_argument("--info", nargs="*", help="Info about target")
    parser.add_argument("--output", required=True, help="Output file")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    JsonBuilder().run(args)
