"""APIs to use for uploading a bulk of qTest results.

reference to: https://api.qasymphony.com/.
"""
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import requests

SERVER_URL = "https://sierrawireless.qtestnet.com/"
CONFIG_PATH = "$PWD/test_data.xml"


def read_test_config(path_dir):
    """Get test result config."""
    test_config = ET.parse(os.path.expandvars(CONFIG_PATH)).getroot()
    return test_config.findtext(path_dir)


def write_config(path, value):
    """Set value result config."""
    tree = ET.parse(os.path.expandvars(CONFIG_PATH))
    tree.getroot().find(path).text = value
    tree.write(os.path.expandvars(CONFIG_PATH))


class QTestAPI:
    """Class for upload the result by REST API."""

    def __init__(self, accessToken, project_name, release_name):
        # Get accesstoken with login
        self.access_token = accessToken
        self.project_name = project_name
        self.release_name = release_name
        self.project_id = self.get_project_ID()
        self.release_id = self.get_release_ID()
        self.test_suite_names = self.get_testsuite_name()

    def get_project_ID(self):
        """Get project ID assigned to user.

        Description:
            API: /api/v3/projects
        Returns:
            Project ID (int)  project ID assigned to user
            0 if otherwise
        """
        api_url = SERVER_URL + "/api/v3/projects"
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for project in responsejson:
            if project["name"] == self.project_name:
                print(f'Project ID: {project["id"]}')
                return project["id"]
        return 0

    def get_release_ID(self):
        """Get release ID with release name.

        Description:
            API: /api/v3/projects/{Project_ID}/releases
        Returns:
            release ID (int) release ID with release name
            0 if otherwise
        """
        api_url = SERVER_URL + f"/api/v3/projects/{self.project_id}/releases"
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for release in responsejson:
            if release["name"] == self.release_name:
                print(f'Release ID: {release["id"]}')
                return release["id"]
        return 0

    def get_testSuite_ID(self, test_suite_name):
        """Get test suite ID with test suite name on releaseName .

        Description:
            API: /api/v3/projects/{Project_ID}/test-suites
        Returns:
            test suite ID (int) test suite ID with test suite name
            0 if otherwise
        """
        api_url = SERVER_URL + f"/api/v3/projects/{self.project_id}/test-suites"
        params = {"access_token": self.access_token}
        if self.release_id != 0:
            params["parentType"] = "release"
            params["parentId"] = self.release_id
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for testSuite in responsejson:
            if testSuite["name"] == test_suite_name:
                print(f'Test suite ID: {testSuite["id"]}')
                return testSuite["id"]
        return 0

    def get_testRun_ID(self, TEST_SUITE_ID):
        """Get test run ID by test name on the test suite.

        Description:
            API: /api/v3/projects/{Project_ID}/test-runs
        Returns:
            test run ID (int) test run ID by the testcase name
            0 if otherwise
        """
        api_url = SERVER_URL + f"/api/v3/projects/{self.project_id}/test-runs"
        params = {
            "access_token": self.access_token,
            "parentType": "test-suite",
            "parentId": TEST_SUITE_ID,
            "pageSize": 1000,
        }
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        dict_test_cases = {}
        for testRun in responsejson["items"]:
            dict_test_cases[testRun["name"]] = testRun["id"]
        return dict_test_cases

    def get_testsuite_name(self):
        """Get all test suite in a release.

        Description:
            API: /api/v3/projects/{Project_ID}/test-suites
        Returns:
            all test suite in a release
            0 if otherwise
        """
        api_url = SERVER_URL + f"/api/v3/projects/{self.project_id}/test-suites"
        params = {
            "access_token": self.access_token,
            "parentType": "release",
            "parentId": self.release_id,
            "pageSize": 100,
        }
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        test_suite_names = []
        for i in responsejson:
            test_suite_names.append(i["name"])
        return test_suite_names

    def get_field_ID(self, field_name, testRun_id):
        """Get test field ID by filed name of testcase.

        Description:
            API: /api/v3/projects/{Project_ID}/test-runs/{Test_Run_ID}/properties
        Returns:
            test field ID (int) test field ID by filed name of testcase
            0 if otherwise
        """
        api_url = (
            SERVER_URL
            + f"/api/v3/projects/{self.project_id}/test-runs/{testRun_id}/properties"
        )
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        for field_count in responsejson:
            if field_count["name"] == field_name:
                return field_count["id"]
        return 0

    def get_properties_info(self, testRun_id):
        """Get all properties of test run on test suite.

        Description:
            API: /api/v3/projects/{Project_ID}/test-runs/{test_run_ID}/properties-info
        Returns:
            all properties info (json) properties of test run if successfully
            1 if this failed
        """
        # Get properties info
        api_url = (
            SERVER_URL
            + f"/api/v3/projects/{self.project_id}"
            + f"/test-runs/{testRun_id}/properties-info"
        )
        params = {"access_token": self.access_token}
        headers = {}
        response = requests.request("GET", api_url, params=params, headers=headers)
        responsejson = response.json()
        if "200" in str(response):
            return responsejson["metadata"]
        else:
            return 1

    def fill_field_ID(self, properties, test_run_id):
        """Get all field of a test case."""
        # Get test field ID
        for field in (
            ET.parse(os.path.expandvars(CONFIG_PATH))
            .getroot()
            .findall(".//*[@Type='field']")
        ):
            if field.find("id").text is None:
                write_config(
                    f"{field.tag}/id",
                    str(self.get_field_ID(field.find("name").text, test_run_id)),
                )
                assert (
                    read_test_config(f"{field.tag}/id") is not None
                ), f'Cannot get ID of Field: {read_test_config(f"{field.tag}/id")}'
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

    def post_result_qtest(self, test_run_id):
        """Post a result of test case to qTest.

        Returns:
        0 if uploading successfully
        1 if this failed.
        """
        api_url = (
            SERVER_URL
            + f"/api/v3/projects/{self.project_id}/test-runs/{test_run_id}/test-logs"
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
                "field_id": read_test_config("LXSWI_Version/id"),
                "field_name": read_test_config("LXSWI_Version/name"),
                "field_value": read_test_config("LXSWI_Version/value_id"),
                "field_value_name": read_test_config("LXSWI_Version/value"),
            },
            {
                "field_id": read_test_config("FW_Version_WP76/id"),
                "field_name": read_test_config("FW_Version_WP76/name"),
                "field_value": read_test_config("FW_Version_WP76/value_id"),
                "field_value_name": read_test_config("FW_Version_WP76/value"),
            },
            {
                "field_id": read_test_config("FW_Version_WP77/id"),
                "field_name": read_test_config("FW_Version_WP77/name"),
                "field_value": read_test_config("FW_Version_WP77/value_id"),
                "field_value_name": read_test_config("FW_Version_WP77/value"),
            },
            {
                "field_id": read_test_config("FW_Version_HL78/id"),
                "field_name": read_test_config("FW_Version_HL78/name"),
                "field_value": read_test_config("FW_Version_HL78/value_id"),
                "field_value_name": read_test_config("FW_Version_HL78/value"),
            },
            {
                "field_id": read_test_config("FW_Version_RC76/id"),
                "field_name": read_test_config("FW_Version_RC76/name"),
                "field_value": read_test_config("FW_Version_RC76/value_id"),
                "field_value_name": read_test_config("FW_Version_RC76/value"),
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
        if "201" in str(response):
            return True
        return False
