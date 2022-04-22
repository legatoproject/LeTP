"""APIs to use for uploading a bulk of qTest results.

reference to: https://api.qasymphony.com/.
"""
import json
import os
import enum
import xml.etree.ElementTree as ET
from datetime import datetime
import pprint
import requests

server_url = "https://sierrawireless.qtestnet.com"
config_path = "$PWD/test_data.xml"


class StatusID(enum.Enum):
    """Class for status ID."""

    Passed = 601
    Failed = 602
    Incomplete = 603
    Blocked = 604


def read_test_config(path_dir):
    """Get test result config."""
    test_config = ET.parse(os.path.expandvars(config_path)).getroot()
    return test_config.findtext(path_dir)


def write_config(path, value):
    """Set value result config."""
    tree = ET.parse(os.path.expandvars(config_path))
    tree.getroot().find(path).text = value
    tree.write(os.path.expandvars(config_path))


class QTestAPI:
    """Class for upload the result by REST API."""

    def __init__(self, accessToken):
        # Get accesstoken with login
        self.access_token = accessToken

    def get_project_ID(self, project_name="Legato"):
        """Get project ID assigned to user.

        Description:
            API: /api/v3/projects
        Returns:
            Project ID (int)  project ID assigned to user
            0 if otherwise
        """
        api_url = server_url + "/api/v3/projects"
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for project in responsejson:
            if project["name"] == project_name:
                print(f'Project ID: {project["id"]}')
                return project["id"]
        return 0

    def get_release_ID(self, release_name, project_id=0):
        """Get release ID with release name.

        Description:
            API: /api/v3/projects/{Project_ID}/releases
        Returns:
            release ID (int) release ID with release name
            0 if otherwise
        """
        api_url = server_url + f"/api/v3/projects/{project_id}/releases"
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for release in responsejson:
            if release["name"] == release_name:
                print(f'Release ID: {release["id"]}')
                return release["id"]
        return 0

    def get_cycle_ID(self, cycle_name, project_id=0):
        """Get test cycle ID with test cycle name.

        Description:
            API: /api/v3/projects/{Project_ID}/test-cycles
        Returns:
            testcycle ID (int) test cycle ID with test cycle name
            0 if otherwise
        """
        api_url = server_url + f"/api/v3/projects/{project_id}/test-cycles"
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for cycle in responsejson:
            if cycle["name"] == cycle_name:
                print(f'Test Cycle ID: {cycle["id"]}')
                return cycle["id"]
        return 0

    def get_testSuite_ID(self, test_suite_name, project_id, release_id):
        """Get test suite ID with test suite name on releaseName .

        Description:
            API: /api/v3/projects/{Project_ID}/test-suites
        Returns:
            test suite ID (int) test suite ID with test suite name
            0 if otherwise
        """
        api_url = server_url + f"/api/v3/projects/{project_id}/test-suites"
        params = {"access_token": self.access_token}
        if release_id != 0:
            params["parentType"] = "release"
            params["parentId"] = release_id
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for testSuite in responsejson:
            if testSuite["name"] == test_suite_name:
                print(f'Test suite ID: {testSuite["id"]}')
                return testSuite["id"]
        return 0

    def get_testRun_ID(self, test_case_name, test_case_PID, project_id, testSuite_id):
        """Get test run ID by test name or test case PID on the test suite.

        Description:
            API: /api/v3/projects/{Project_ID}/test-runs
        Returns:
            test run ID (int) test run ID by the testcase name or PID of test case
            0 if otherwise
        """
        api_url = server_url + f"/api/v3/projects/{project_id}/test-runs"
        params = {
            "access_token": self.access_token,
            "parentType": "test-suite",
            "parentId": testSuite_id,
            "pageSize": 1000,
        }
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for testRun in responsejson["items"]:
            if test_case_PID != "":
                if testRun["pid"] == test_case_PID:
                    return testRun["id"]
            else:
                if testRun["name"] == test_case_name:
                    return testRun["id"]
        return 0

    def get_field_ID(self, field_name, project_id, testRun_id):
        """Get test field ID by filed name of testcase.

        Description:
            API: /api/v3/projects/{Project_ID}/test-runs/{Test_Run_ID}/properties
        Returns:
            test field ID (int) test field ID by filed name of testcase
            0 if otherwise
        """
        api_url = (
            server_url
            + f"/api/v3/projects/{project_id}/test-runs/{testRun_id}/properties"
        )
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for field_count in responsejson:
            if field_count["name"] == field_name:
                return field_count["id"]
        return 0

    def get_properties_info(self, project_id, testSuite_id, test_name):
        """Get all properties of test run on test suite.

        Description:
            API: /api/v3/projects/{Project_ID}/test-runs/{test_run_ID}/properties-info
        Returns:
            all properties info (json) properties of test run if successfully
            1 if this failed
        """
        # Get test run ID
        test_run_id = self.get_testRun_ID(
            test_name, read_test_config("PID"), project_id, testSuite_id
        )
        api_url = (
            server_url
            + f"/api/v3/projects/{project_id}/test-runs/{test_run_id}/properties-info"
        )
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        if "200" in str(response):
            return responsejson["metadata"], test_run_id
        else:
            return 1, 0

    def post_result_qtest(self, project_id, properties, test_run_id):
        """Post a result of test case to qTest.

        Returns:
        0 if uploading successfully
        1 if this failed.
        """
        # Get test field ID
        for field in (
            ET.parse(os.path.expandvars(config_path))
            .getroot()
            .findall(".//*[@Type='field']")
        ):
            if field.find("id").text is None:
                write_config(
                    f"{field.tag}/id",
                    str(
                        self.get_field_ID(
                            field.find("name").text, project_id, test_run_id
                        )
                    ),
                )
                assert (
                    read_test_config(f"{field.tag}/id") is not None
                ), f'Cannot get ID of Field: {read_test_config(f"{field.tag}/id")}'
            print(
                f'Field ID of {field.find("name").text}: \
                    {read_test_config(f"{field.tag}/id")}'
            )
            for field_count in properties:
                if (
                    field_count["id"] == int(read_test_config(f"{field.tag}/id"))
                    and field_count["allowed_values"] != []
                ):
                    for allowed_value in field_count["allowed_values"]:
                        if allowed_value["value_text"] == read_test_config(
                            f"{field.tag}/value"
                        ):
                            write_config(
                                f"{field.tag}/value_id", str(allowed_value["id"])
                            )
                    assert (
                        read_test_config(f"{field.tag}/value_id") is not None
                    ), f'Cannot get ID of Field: {field.find("name").text}'
            print(
                f'Field Value ID of {read_test_config(f"{field.tag}/value")}:\
                    {read_test_config(f"{field.tag}/value_id")}'
            )
        api_url = (
            server_url
            + f"/api/v3/projects/{project_id}/test-runs/{test_run_id}/test-logs"
        )
        params = {"access_token": self.access_token}
        headers = {"Content-Type": "application/json"}
        payload = {
            "exe_start_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "exe_end_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": {"id": 601, "name": "Passed"},
        }
        payload["properties"] = [
            {
                "field_id": read_test_config("Legato_Version/id"),
                "field_name": read_test_config("Legato_Version/name"),
                "field_value": read_test_config("Legato_Version/value_id"),
                "field_value_name": read_test_config("Legato_Version/value"),
            },
            {
                "field_id": read_test_config("Module_Ref/id"),
                "field_name": read_test_config("Module_Ref/name"),
                "field_value": read_test_config("Module_Ref/value_id"),
                "field_value_name": read_test_config("Module_Ref/value"),
            },
            {
                "field_id": read_test_config("Comment/id"),
                "field_name": read_test_config("Comment/name"),
                "field_value": read_test_config("Comment/value"),
                "field_value_name": read_test_config("Comment/value_id"),
            },
        ]
        response = requests.request(
            "POST",
            url=api_url,
            params=params,
            headers=headers,
            data=json.dumps(payload),
        )
        responsejson = response.json()
        pprint.pprint(responsejson)
