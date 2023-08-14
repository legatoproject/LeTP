#!/usr/bin/env python3
"""!@package gen_json Generate the Json file.

Json file is based on raw results.
"""
import os
import json
import re
import argparse
from datetime import datetime, timedelta


class Informations:
    """!Get information from the running system."""

    def __init__(self):
        """!Define information format."""
        self.test_json_data = {}
        self.module_info = self._get_module_info()
        self.test_json_data["Execution"] = {
            "Build ID": os.environ.get("BUILD_NUMBER"),
            "scripts": "Python_HL78xx",
            "test_set_id": "N/A",
            "test_set_name": "N/A",
            "project_name": "HL78xx",
            "Module Type": self.module_info["type"],
            "SIM Ref": self.module_info["sim"],
            "Test Bed": self.module_info["tb_id"],
            "FW Version": "N/A",
            "Legato Version": "N/A",
            "Operating System": "N/A",
            "Python Version": "N/A",
            "Tool Version": "N/A",
        }

    @staticmethod
    def _get_module_info():
        """Get module information used for testing."""
        return {
            "type": os.environ.get("TB_MODULE"),
            "sim": os.environ.get("TB_CARRIER"),
            "tb_id": os.environ.get("TB_ID"),
        }

    @staticmethod
    def _get_FW_ver(test_log):
        """Get Firmware & Legato version from test log."""
        firmware_ver = "N/A"
        firmware = re.search(r"(?P<fw>HL78\d{2}\..+?)(\n|<CR>)", test_log)
        if firmware:
            firmware_ver = firmware.group("fw")

        return firmware_ver

    @staticmethod
    def _get_Legato_ver(test_log):
        """Get Firmware & Legato version from test log."""
        legato_ver = "N/A"
        legato = re.search(r"Legato RTOS:\s+(?P<legato>[^ ]*)", test_log)
        if legato:
            legato_ver = legato.group("legato")

        return legato_ver


class AutoTestPlus(Informations):
    """!Test case information with Json format."""

    def __init__(self, data):
        """!Generate test case information with Json format."""
        super().__init__()

        self.test_json_data["Tests"] = []
        self.data = data
        self.test_json_data["Execution"]["test_set_id"] = "6481304"
        self.test_json_data["Execution"]["test_set_name"] = "AutoTestPlus_Sample_test"

    @staticmethod
    def _get_test(log):
        """Get test cases name from data."""
        test = re.search(r"FILE:\s+(?P<name>\w+)\.py", log)
        test_name = test.group("name")

        return test_name

    @staticmethod
    def _get_status(test_name, log):
        """Get test cases status from data."""
        status = re.search(rf"Status\s+{test_name}:\s+(?P<status>\w+)", log)
        if status is None:
            test_status = "N/A"
        else:
            test_status = status.group("status").title()

        return test_status

    @staticmethod
    def _get_duration(log):
        """Calculate the test case running time."""
        start_time = re.search(r"Start Time: (\d|-)+ (?P<time>\d{2}:\d{2}:\d{2})", log)
        start_time = str(start_time.group("time"))

        times = re.findall(r"\d{2}:\d{2}:\d{2}:\d+", log)
        end_time = times[-1][:8]
        start_time = datetime.strptime(start_time, "%H:%M:%S")
        end_time = datetime.strptime(end_time, "%H:%M:%S")
        if end_time < start_time:
            end_time += timedelta(days=1)
        duration = end_time - start_time

        return duration.total_seconds()

    @staticmethod
    def _get_sys_info(test_log):
        """Get module information used for testing."""
        system_info = re.search(r"OS info\s+:\s+(?P<sys>.*)\n", test_log).group("sys")
        python_ver = re.search(r"Python ver\.\s+:\s+(?P<py_ver>.+)", test_log).group(
            "py_ver"
        )
        tool_ver = re.search(
            r"AutoTestPlus version\s+:\s+(?P<swi_ver>.+)", test_log
        ).group("swi_ver")

        return {
            "Operating System": system_info,
            "Python Version": python_ver,
            "Tool Version": f"AutoTestPlus: {tool_ver}",
        }

    def run(self):
        """Generate the test log with Json format."""
        pattern = "Start the Test"
        test_case_logs = self.data.split(pattern)[1:]
        env_info = self._get_sys_info(test_case_logs[0])
        self.test_json_data["Execution"].update(env_info)

        for log in test_case_logs:
            test_case_info = {}
            if self.test_json_data["Execution"]["FW Version"] == "N/A":
                self.test_json_data["Execution"]["FW Version"] = self._get_FW_ver(log)
            if self.test_json_data["Execution"]["Legato Version"] == "N/A":
                self.test_json_data["Execution"][
                    "Legato Version"
                ] = self._get_Legato_ver(log)
            test_name = self._get_test(log)
            test_case_info["Test Name"] = test_name
            test_case_info["Result"] = self._get_status(test_name, log)
            test_case_info["Duration(secs)"] = self._get_duration(log)
            test_case_info["raw_log"] = pattern + log
            test_case_info["raw_log"] = test_case_info["raw_log"].replace("<", '&lt;')
            test_case_info["raw_log"] = test_case_info["raw_log"].replace(">", '&gt;')
            test_case_info["raw_log"] = test_case_info["raw_log"].replace("\n", '<br/>')
            self.test_json_data["Tests"].append(test_case_info)

        return self.test_json_data


class Swilib(Informations):
    """!Test case information with Json format."""

    def __init__(self, data):
        """!Generate test case information with Json format."""
        super().__init__()

        self.test_json_data["Tests"] = []
        self.data = data
        self.test_json_data["Execution"]["test_set_id"] = "6481308"
        self.test_json_data["Execution"]["test_set_name"] = "SWILIB_Sample_Test"

    @staticmethod
    def _get_sys_info(test_log):
        """Get module information used for testing."""
        python_ver = "N/A"
        system_info = re.search(r"Operating System:\s+(?P<sys>.*)\n", test_log).group(
            "sys"
        )
        python_info = re.search(
            r"Python Version:\s+(?P<py_ver>Python\s\d+\.\d+\.\d+)\n", test_log
        )
        if python_info is not None:
            python_ver = python_info.group("py_ver")
        swilib_ver = re.search(
            r"Tool Version:\s+(?P<swi_ver>\d+\.\d+)\n", test_log
        ).group("swi_ver")

        return {
            "Operating System": system_info,
            "Python Version": python_ver,
            "Tool Version": f"Swilib: {swilib_ver}"
        }

    @staticmethod
    def _get_test(test_log):
        """Get test cases name from test log."""
        test = re.search(r"Running Test Name:\s+(?P<name>\w+)\s+", test_log)
        test_name = test.group("name")

        return test_name

    @staticmethod
    def _get_duration(test_log):
        """Get the execution time of each test case."""
        first_line = test_log.splitlines()[0]
        last_line = test_log.splitlines()[-1]
        start_time_str = re.search(
            r"\s+(?P<start_time>\d+\:\d+\:\d+)\s+", first_line
        ).group("start_time")
        end_time_str = re.search(r"\s+(?P<end_time>\d+\:\d+\:\d+)\s+", last_line).group(
            "end_time"
        )

        start_time = datetime.strptime(start_time_str, "%H:%M:%S")
        end_time = datetime.strptime(end_time_str, "%H:%M:%S")

        if end_time < start_time:
            end_time += timedelta(days=1)

        duration = end_time - start_time

        return duration.total_seconds()

    @staticmethod
    def _get_status(test_name, test_log):
        """Get test cases status from test log."""
        status = re.search(rf"\s+{test_name}:(?P<status>\w+)", test_log)
        if status is None:
            test_status = "N/A"
        else:
            test_status = status.group("status").title()

        return test_status

    def run(self):
        """Generate the Json file."""
        env_info = self._get_sys_info(self.data["Test_log"][0])
        self.test_json_data["Execution"].update(env_info)
        for log in self.data["Test_log"]:
            test_case_info = {}
            if self.test_json_data["Execution"]["FW Version"] == "N/A":
                self.test_json_data["Execution"]["FW Version"] = self._get_FW_ver(log)
            if self.test_json_data["Execution"]["Legato Version"] == "N/A":
                self.test_json_data["Execution"][
                    "Legato Version"
                ] = self._get_Legato_ver(log)
            test_name = self._get_test(log)
            test_case_info["Test Name"] = test_name
            test_case_info["Result"] = self._get_status(test_name, log)
            test_case_info["Duration(secs)"] = self._get_duration(log)
            test_case_info["raw_log"] = log
            test_case_info["raw_log"] = test_case_info["raw_log"].replace("<", '&lt;')
            test_case_info["raw_log"] = test_case_info["raw_log"].replace(">", '&gt;')
            test_case_info["raw_log"] = test_case_info["raw_log"].replace("\n", '<br/>')
            self.test_json_data["Tests"].append(test_case_info)

        return self.test_json_data


def parse_args():
    """!Parse all arguments for gen_json."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-data", required=True, help="Path to raw data file")

    parser.add_argument("--output", default="json_data.json", help="Output file path")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    log_path = args.raw_data

    assert os.path.exists(args.raw_data), f"{args.raw_data}: Could not find file"

    if ".json" in log_path:
        with open(log_path, encoding="utf8") as f:
            raw_data = json.load(f)
        test = Swilib(raw_data)
    else:
        with open(log_path, encoding="utf8") as f:
            raw_data = f.read()
        test = AutoTestPlus(raw_data)
    json_data = test.run()
    output = json.dumps(json_data, indent=2, separators=(",", ": "))

    if args.output:
        with open(args.output, "w", encoding="utf8") as f:
            f.write(output)
        print(f"Generating Json file in {args.output}")
