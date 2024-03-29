"""Script to manage qTest's API.

reference to: https://qtest.dev.tricentis.com/
"""
import sys
import xml.etree.ElementTree as ET
import json
import time
import requests


# ====================================================================================
# Global variables
# ====================================================================================
SERVER_URL = "https://sierrawireless.qtestnet.com/"
API_V3 = SERVER_URL + "api/v3/projects"


# ====================================================================================
# Functions
# ====================================================================================
class QTestAPI:
    """Class for qTest manager using REST API."""

    def __init__(self, accessToken, project_id=None, parent_id=0, parent_type="root"):
        self.access_token = accessToken
        self.project_id = project_id
        self.parent_id = parent_id
        self.parent_type = parent_type

    def get_projects(self):
        """Retrieve all Projects that the qTest account can access.

        API: /api/v3/projects
        """
        params = {"access_token": self.access_token}
        response_json = self.get_qTest_info(API_V3, params)
        return response_json

    def get_cycles(self, parentId, parentType):
        """Retrieve Test Cycles.

        API: /api/v3/projects/{Project_ID}/test-cycles
        """
        api_url = API_V3 + f"/{self.project_id}/test-cycles"
        params = {
            "access_token": self.access_token,
            "parentId": parentId,
            "parentType": parentType,
        }
        response_json = self.get_qTest_info(api_url, params)
        return response_json

    def get_releases(self):
        """Retrieve Releases in a project.

        API: /api/v3/projects/{Project_ID}/releases
        """
        api_url = API_V3 + f"/{self.project_id}/releases"
        params = {"access_token": self.access_token}
        response_json = self.get_qTest_info(api_url, params)
        return response_json

    def get_suites(self, parentId, parentType):
        """Retrieve Test Suites.

        which located under a parent Release, Test Cycle or root.

        API: /api/v3/projects/{Project_ID}/test-suites
        """
        api_url = API_V3 + f"/{self.project_id}/test-suites"
        params = {
            "access_token": self.access_token,
            "parentId": parentId,
            "parentType": parentType,
        }
        response_json = self.get_qTest_info(api_url, params)
        return response_json

    def get_test_runs(self, parentId, parentType):
        """Retrieve all Test Runs.

        Test Runs under root or under a container (Release, Test Cycle or Test Suite).

        API: /api/v3/projects/{Project_ID}/test-runs
        """
        api_url = API_V3 + f"/{self.project_id}/test-runs"
        params = {
            "access_token": self.access_token,
            "parentId": parentId,
            "parentType": parentType,
            "pageSize": 1000,
        }
        response_json = self.get_qTest_info(api_url, params)
        return response_json

    def get_test_cases(self, test_case_id):
        """Retrieve a Test Case.

        API: /api/v3/projects/{Project_ID}/test-cases/{testCaseId}
        """
        api_url = API_V3 + f"/{self.project_id}/test-cases/{test_case_id}"
        params = {"access_token": self.access_token}
        response_json = self.get_qTest_info(api_url, params)
        return response_json

    def get_data_from_id(self, parent_id, parent_type):
        """Retrieve a Release, Test Cycle.

        API: /api/v3/projects/{Project_ID}/{type}/{id}
        """
        api_url = API_V3 + f"/{self.project_id}/{parent_type}/{parent_id}"
        params = {"access_token": self.access_token}
        response_json = self.get_qTest_info(api_url, params)
        return response_json

    def update_cycle_name(self, testCycleId, data):
        """Update a test cycle.

        API: /api/v3/projects/{Project_ID}/test-cycles/{testCycleId}
        """
        api_url = API_V3 + f"/{self.project_id}/test-cycles/{testCycleId}"
        params = {"access_token": self.access_token}
        # Retry 6 times if the 'put' operation is unsuccessful,
        # with cumulative waiting time gradually increases to 30 minutes.
        for i in range(6):
            time.sleep(i * 60 * 2)
            response = requests.put(api_url, params=params, json=data)
            if response.status_code == 200:
                break
        assert response.status_code == 200, f"{response.status_code} - {response.text}"

    def get_cycle_id(self, cycle_name):
        """Get Test Cycles ID which are located directly under root."""
        cycle_under_root = self.get_cycles(0, "root")
        for test_cycle in cycle_under_root:
            if test_cycle["name"] == cycle_name:
                cycle_id = test_cycle["id"]
                break
        else:
            print(f"PROBLEM: Could not find {cycle_name} cycle")
            sys.exit(False)
        return cycle_id

    def check_cycle(self, string):
        """Check if string is the name of a test cycle."""
        cycle_data = self.get_cycles(self.parent_id, self.parent_type)
        for cycle in cycle_data:
            if cycle["name"] == string:
                print(f"{string} is test cycle")
                self.parent_id = cycle["id"]
                self.parent_type = "test-cycle"
                return True
        print(f"Warning: Could not find {string} as test cycle")
        return False

    def check_suite(self, string):
        """Check if string is the name of a test suite."""
        suite_data = self.get_suites(self.parent_id, self.parent_type)
        for test_suite in suite_data:
            if test_suite["name"] == string:
                print(f"{string} is test suite")
                self.parent_id = test_suite["id"]
                self.parent_type = "test-suite"
                return True
        print(f"Warning: Could not find {string} as test suite")
        return False

    def check_release(self, string):
        """Check if string is the name of a test release."""
        release_data = self.get_releases()
        for release in release_data:
            if release["name"] == string:
                print(f"{string} is release")
                self.parent_id = release["id"]
                self.parent_type = "release"
                return True
        print(f"Warning: Could not find {string} as release")
        return False

    def get_id(self, qtest_info):
        """Get the id of root or Release/Test Cycle/Test Suite.

        which contains the test cases to execute
        """
        print(f"Project: {qtest_info[0]}")
        json_data = self.get_projects()
        for project in json_data:
            if project["name"] == qtest_info[0]:
                self.project_id = project["id"]
                break
        else:
            print(f"PROBLEM: Could not find the expected project {qtest_info[0]}")
            sys.exit(False)

        if len(qtest_info) == 1:
            return
        else:
            for info in qtest_info[1:]:
                if (
                    self.check_cycle(info)
                    or self.check_suite(info)
                    or (info == qtest_info[1] and self.check_release(info))
                ):
                    if info == qtest_info[-1]:
                        print(f"campaign_id: {self.parent_id}")
                    continue
                print(f"PROBLEM: Could not find {info}")
                sys.exit(False)

    def get_campaign_name(self):
        """Create a test campaign name based on the test case container."""
        parent_id = self.parent_id
        parent_type = self.parent_type + "s"
        json_data = self.get_data_from_id(parent_id, parent_type)
        test_campaign_name = json_data["name"] + ".json"

        return test_campaign_name

    def get_test_script(self):
        """Get test cases and their test scripts."""
        test_run_data = self.get_test_runs(self.parent_id, self.parent_type)
        dict_test_cases = {}
        empty_list = []
        for test_run in test_run_data["items"]:
            # L_ReinitTest will be run separately when preparing testbed
            if test_run["name"] == "L_ReinitTest":
                continue
            test_id = test_run["testCaseId"]
            tc_data = self.get_test_cases(test_id)
            test_script = ""
            for field in tc_data["properties"]:
                if field["field_name"] == "Script Name":
                    if field["field_value"]:
                        test_script = field["field_value"]
                    else:
                        empty_list.append(test_run["name"])
                    break
            dict_test_cases[test_run["name"]] = test_script
        if empty_list:
            print(f"PROBLEM: {len(empty_list)} test cases without test script")
            print(*empty_list, sep="\n")
            sys.exit()

        return dict_test_cases

    def save_qtest_info(self, xml_file_path):
        """Save qTest information."""
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        for element in root.iter("qTest"):
            element.find("token").text = self.access_token
            element.find("project_id").text = str(self.project_id)
            element.find("campaign_id").text = str(self.parent_id)
            element.find("campaign_type").text = self.parent_type
        tree.write(xml_file_path)

    @staticmethod
    def get_qTest_info(url, params):
        """Retrieve information from qTest, if the process fails, retry it 6 times.

        With the cumulative waiting time gradually increasing to 30 minutes
        """
        for i in range(6):
            if i != 0:
                print(
                    f"Try again after {i*2} mins when "
                    + "retrieving information from qTest fails."
                )
            time.sleep(i * 60 * 2)
            response = requests.get(url, params=params)
            if response.status_code == 200:
                break
        assert response.status_code == 200, f"{response.status_code} - {response.text}"
        return response.json()


def gen_json_file(input_dict, file_path):
    """Generate JSON file with preset data structure."""
    # Create a data structure for the JSON file
    output_data = {
        "letp": {
            "tests": [
                {"name": value} for value in input_dict.values()
            ]
        }
    }

    # Write structured data to a JSON file
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(output_data, json_file, indent=4)
        print(f"Generating JSON file: {file_path}")
