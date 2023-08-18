"""Script get test cases from qTest.

reference to: https://qtest.dev.tricentis.com/
"""

import json
import requests


# ====================================================================================
# Global variables
# ====================================================================================
SERVER_URL = "https://sierrawireless.qtestnet.com"


# ====================================================================================
# Functions
# ====================================================================================
def get_test_cases(qtest_info):
    """Get test cases from test suite on the qTest.

    Description:
        API: /api/v3/projects/{Project_ID}/test-runs
    Returns:
        test cases and their test scripts
    """
    api_url = SERVER_URL + f"/api/v3/projects/{qtest_info['projectId']}/test-runs"
    params = {
        "access_token": qtest_info["token"],
        "parentType": "test-suite",
        "parentId": qtest_info["testSuiteId"],
        "pageSize": 1000,
    }
    headers = {}
    response = requests.request("GET", api_url, params=params, headers=headers)
    responsejson = response.json()
    dict_test_cases = {}
    for testRun in responsejson["items"]:
        test_id = testRun["testCaseId"]
        test_script = get_test_script(qtest_info, test_id)
        dict_test_cases[testRun["name"]] = test_script

    return dict_test_cases


def get_test_script(qtest_info, testCaseId):
    """Get test script of test case.

    Description:
        API: /api/v3/projects/{Project_ID}/test-cases/{testCaseId}

    Returns:
        test script
    """
    api_url = (SERVER_URL
               + f"/api/v3/projects/{qtest_info['projectId']}/test-cases/{testCaseId}")
    params = {
        "access_token": qtest_info["token"]
    }
    headers = {}
    response = requests.request("GET", api_url, params=params, headers=headers)
    responsejson = response.json()
    testScript = ""
    for field in responsejson["properties"]:
        if field["field_name"] == "Script Name":
            testScript = field["field_value"]
    return testScript


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
